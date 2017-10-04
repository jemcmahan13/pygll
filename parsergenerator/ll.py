
from stock import PCLASS, MAIN
import re, sys
from emitter import Emitter

class GrammarObj(object):
    def __str__(self):
        return self.name
    def __repr__(self):
        s = self.name + '['
        for k,v in self.attrs:
            s += "{}:{}, ".format(k,v)
        s += ']'
        return s
    def __init__(self, *args):
        i = 0
        for k,v in args:
            if k == "_":
                setattr(self, "_anon{{}}".format(i), v)
                i += 1
            else:
                setattr(self, k, v)
        self.attrs = args

class GrammarTerm(object):
    def __init__(self):
        self.endOf = set()  # productions this term ends (for follow set)
        # Keep track of which Terminals and Nonterminals follow this one;
        # used to compute the follow set
        self.followers = set()

    def findfollows(self):
        follow = set()
        for x in self.endOf:
            if x != self:
                self.followers.update(x.follow)
        for x in self.followers:
            follow.update(set(y for y in x.first if y))
        return follow

class Terminal(GrammarTerm):
    def __init__(self, name, pattern):
        super().__init__()
        self.name = name
        self.pattern = re.compile(pattern)
        self._follow = None
        self.compiled = True

    @property
    def first(self):
        return set((self,))  # the terminal is a first token

    @property
    def follow(self):
        if self._follow:
            return self._follow
        follow = self.findfollows()
        self._follow = follow
        return self._follow

    def compile(self, caller=None):
        return

    def __call__(self, token):
        # See if the given token matches this terminal
        if log:
            print("Checking token ", token, "against ", self.name)
        return self.name == token

    def __str__(self):
        return "{}".format(self.name)

    def __repr__(self):
        return "{}:{}".format(self.name, self.pattern.pattern)

class Nonterminal(GrammarTerm):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.productions = []
        self._first = set()
        self._follow = set()
        self.compiled = False
        self.top = False
        self.rules = []  # will eventually hold tuples of (first-set, production) for parsing

    def addProduction(self, prod):
        self.productions.append(prod)

    @property
    def first(self):
        if self._first:
            return self._first
        first = set()
        for prod in self.productions:
            first.update(prod.first)
        self._first = first
        return first

    @property
    def follow(self):
        if self._follow:
            return self._follow
        if self.top:
            self._follow.add(Terminal('EOF', r'\Z'))  # end of input terminal
        if log:
            print("Follow of ", self, self._follow)
        self._follow.update(self.findfollows())
        if self in self.followers:
            self.followers.remove(self)
        for f in self.followers:
            if log:
                print("Getting first set of {}: {}".format(f, f.first))
            self._follow.update(set(x for x in f.first if x))
        if log:
            print(self._follow, '\n')
        return self._follow

    def root(self):
        # This nonterminal is the top level (start) symbol
        # Add EOF to its follow set
        # print("Root called on ", self)
        try:
            self.compile()
            self.top = True
        except RecursionError as e:
            print("RecursionError: Are you sure your grammar has no left-recursion?")
            sys.exit(1)

    def compile(self, caller=None):
        if self.compiled:
            return
        self.compiled = True
        for prod in self.productions:
            if prod != caller:
                prod.compile()

    def __str__(self):
        return "{}".format(self.name)

    def __repr__(self):
        return "{}: {}".format(self.name, ' | '.join([str(x) for x in self.productions]))

class Production(object):
    # A Production is an ordered list of terms (Terminals and Nonterminals).
    # All terms should already exist before declaring Productions.
    # Once all Productions exist, one can compute first then follow sets.


    def __init__(self, head, *args):
        # head is the LHS (deriving Nonterminal)
        # args should be a sequence of Nonterminals and Terminals
        # Null production represents epsilon
        self.prod = args
        self._first = None
        self._follow = set()
        self.head = head
        self.head.addProduction(self)
        self.compiled = False
        self.pclass = None

        #print(head, type(head), args, [type(x) for x in args])

        # Note which terms follow which
        for i,arg in enumerate(args):
            if i < len(args)-1:
                arg.followers.add(args[i+1])
        # Still might have other terms at end of this if last -> epsilon,
        # but we can't check for that until we have the first sets.
        # Do that in function updateEnds()

    @property
    def first(self):
        if self._first:
            return self._first
        # otherwise, compute first set
        if not self.prod[0]:  # epsilon
            return set((None,))
        first = set()
        for term in self.prod:
            fs = term.first
            if None not in fs:  # we can stop here
                first.update(fs)
                self._first = first
                return first
            else:  # nonterminal could be epsilon, so keep going
                first.update(set(x for x in fs if x))  # add everything but epsilon
        self._first = first
        return first

    def updateEnds(self):
        # Call this function after firsts are done, but before follows
        if not self.prod[0]:
            return  # epsilon
        self.prod[-1].endOf.add(self.head)  # tell terms when they end productions
        last = 0
        finding = True  # find term that reflects productions follow set
        for i, arg in enumerate(reversed(self.prod)):
            if None in arg.first and i < len(self.prod)-1:
                # if a term can go to epsilon, then the one before it gets its follow set
                term = self.prod[i+1]
                term.followers.update(arg.followers)
                term.endOf.update(arg.endOf)
                if finding:
                    last += 1
            else:
                finding = False
        self.last = len(self.prod) - last

    def compile(self):
        # Do some booking needed before follow sets can be computed, and build
        # a map of terminal_list -> production
        if self.compiled:
            return
        self.compiled = True

        self.head.rules.append((self.first, self))

        if not self.prod[0]:
            return  # epsilon
        self.updateEnds()
        for t in self.prod:
            t.compile(self)

    @property
    def follow(self):
        # Call only after grammar is finished and all followers have been added
        if self._follow:
            return self._follow
        term = self.prod[self.last]
        self._follow = term.follow


    def __str__(self):
        return "{} => {}".format(self.head, ' '.join(map(str, self.prod)))

class Declarations(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Declarations"

class Declaration(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Declaration"

class Alternative(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Alternative"

class _(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "_"

class Alternatives(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Alternatives"

class Name(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Name"

class String(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "String"

class Terms(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Terms"

class Binding(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Binding"

class Names(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Names"

LEXMAP = [('pound', '#'), ('bar', '\\|'), ('epsilon', '\\$'), ('string', '(\\\'|\\").*?[^\\\\]\\1'), ('name', '\\w+'), ('%root', '%root'), ('%tokens', '%tokens'), ('%grammar', '%grammar'), (':=', ':='), (';', ';')]


import sys, re

log = False

class Parser(object):

    class ScanError(Exception):
        pass
    class ParseError(Exception):
        pass
    def parsefail(self, expected, found, val=None):
        raise Parser.ParseError("Parse Error, line {}: Expected token {}, but found token {}:{}".format(self.line, expected, found, val))
    def scanfail(self):
        raise Parser.ScanError("Lexer Error, line {}: No matching token found. Remaining input: {} ....".format(self.line, self.remaining[:50]))


    def __init__(self):
        lex = [('whitespace', '\s+'),] + [ x for x in LEXMAP ]
        rules = [ (regex, self.makeHandler(tokenName)) for tokenName, regex in lex ]
        self.scanner = re.Scanner(rules)
        self.line = 1
        self.log = log

    def parse(self, s):
        self.toks, self.remaining = self.scanner.scan(s)
        self.trim()
        return self._parseRoot()

    def makeHandler(self, token):
        return lambda scanner, string : (token, string)

    def trim(self):
        if self.toks:
            token, match = self.toks[0]
            if token == "whitespace":
                self.line += match.count('\n')
                self.toks.pop(0)
                self.trim()
            # else:
            #     if log:
            #         print("next token is ", token)

    def next(self):
        if self.toks:
            token,match = self.toks[0]
            return token
        elif self.remaining:
            self.scanfail()

    def consume(self, tok):
        if not self.toks and self.remaining:
            self.scanfail()
        token,match = self.toks.pop(0)
        if self.log:
            print("consuming {}:{}".format(tok, match))
        if tok != token:
            self.parsefail(tok, token, match)
        self.trim()
        return match

    def pop(self):
        return self.consume(self.next())

    def parseSpec(self):
        if self.next() in ("%root",):
            var0_RootDecl = self.parseRootDecl()
            var1_TokenDecl = self.parseTokenDecl()
            var2_GrammarDecl = self.parseGrammarDecl()
            return (var0_RootDecl, var1_TokenDecl, var2_GrammarDecl,)
        self.parsefail(['("%root",)'], self.next())

    def parseRootDecl(self):
        if self.next() in ("%root",):
            var0_root = self.consume("%root")
            var1_name = self.consume("name")
            return (var0_root, var1_name,)
        self.parsefail(['("%root",)'], self.next())

    def parseTokenDecl(self):
        if self.next() in ("%tokens",):
            var0_tokens = self.consume("%tokens")
            var1_TokenPairs = self.parseTokenPairs()
            return (var0_tokens, var1_TokenPairs,)
        self.parsefail(['("%tokens",)'], self.next())

    def parseGrammarDecl(self):
        if self.next() in ("%grammar",):
            var0_grammar = self.consume("%grammar")
            var1_Decls = self.parseDecls()
            return (var0_grammar, var1_Decls,)
        self.parsefail(['("%grammar",)'], self.next())

    def parseTokenPairs(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            var1_string = self.consume("string")
            var2_TokenPairs = self.parseTokenPairs()
            return (var0_name, var1_string, var2_TokenPairs,)
        return  # epsilon case

    def parseDecls(self):
        if self.next() in ("name",):
            var0_Decl = self.parseDecl()
            var1_Decls = self.parseDecls()
            return Declarations(('decl', var0_Decl),('rest', var1_Decls),)
        return  # epsilon case

    def parseDecl(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            var1_ = self.consume(":=")
            var2_Alt = self.parseAlt()
            var3_Alts = self.parseAlts()
            var4_ = self.consume(";")
            return Declaration(('dname', var0_name),('_', var1_),('alt', var2_Alt),('alts', var3_Alts),('_', var4_),)
        self.parsefail(['("name",)'], self.next())

    def parseAlt(self):
        if self.next() in ("string", "name",):
            var0_Term = self.parseTerm()
            var1_Terms = self.parseTerms()
            var2_Binding = self.parseBinding()
            return Alternative(('term', var0_Term),('terms', var1_Terms),('bind', var2_Binding),)
        if self.next() in ("epsilon",):
            var0_epsilon = self.consume("epsilon")
            return  # production suppressed            return _()
        self.parsefail(['("string", "name",)', '("epsilon",)'], self.next())

    def parseAlts(self):
        if self.next() in ("bar",):
            var0_bar = self.consume("bar")
            var1_Alt = self.parseAlt()
            var2_Alts = self.parseAlts()
            return Alternatives(('_', var0_bar),('alt', var1_Alt),('alts', var2_Alts),)
        return  # epsilon case

    def parseTerm(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            return Name(('val', var0_name),)
        if self.next() in ("string",):
            var0_string = self.consume("string")
            return String(('val', var0_string),)
        self.parsefail(['("name",)', '("string",)'], self.next())

    def parseTerms(self):
        if self.next() in ("string", "name",):
            var0_Term = self.parseTerm()
            var1_Terms = self.parseTerms()
            return Terms(('term', var0_Term),('terms', var1_Terms),)
        return  # epsilon case

    def parseBinding(self):
        if self.next() in ("pound",):
            var0_pound = self.consume("pound")
            var1_name = self.consume("name")
            var2_Names = self.parseNames()
            return Binding(('_', var0_pound),('bname', var1_name),('names', var2_Names),)
        return  # epsilon case

    def parseNames(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            var1_Names = self.parseNames()
            return Names(('termname', var0_name),('names', var1_Names),)
        return  # epsilon case

    def _parseRoot(self):
        return self.parseSpec()


def main():
    with open(sys.argv[1]) as f:
        s = f.read()
    p = Parser()
    ast = p.parse(s)
    e = Emitter(ast)
    e.emit()
    text = e.objs + PCLASS + e.parser + MAIN
    print(text)


if __name__ == "__main__":
    main()
