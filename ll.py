from header import HEADER
import re, sys

class GrammarObj(object):
    def __str__(self):
        return self.name
    def __repr__(self):
        s = self.name + '['
        for k,v in self.attrs:
            s += "{{}}:{{}}, ".format(k,v)
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

LEXMAP = [('name', '\\w+'), ("'%root'", "'%root'"), ("'%tokens'", "'%tokens'"), ("'%grammar'", "'%grammar'"), ("':='", "':='"), ("';'", "';'"), ("'|'", "'|'"), ("'#'", "'#'")]

# log = True
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
        if self.next() in ("'%root'",):
            var0_RootDecl = self.parseRootDecl()
            var1_TokenDecl = self.parseTokenDecl()
            var2_GrammarDecl = self.parseGrammarDecl()
            return (var0_RootDecl, var1_TokenDecl, var2_GrammarDecl,)
        parseerror()

    def parseRootDecl(self):
        if self.next() in ("'%root'",):
            var0_'%root' = self.consume("'%root'")
            var1_name = self.consume("name")
            return (var0_'%root', var1_name,)
        parseerror()

    def parseTokenDecl(self):
        if self.next() in ("'%tokens'",):
            var0_'%tokens' = self.consume("'%tokens'")
            var1_TokenPairs = self.parseTokenPairs()
            return (var0_'%tokens', var1_TokenPairs,)
        parseerror()

    def parseGrammarDecl(self):
        if self.next() in ("'%grammar'",):
            var0_'%grammar' = self.consume("'%grammar'")
            var1_Decls = self.parseDecls()
            return (var0_'%grammar', var1_Decls,)
        parseerror()

    def parseTokenPairs(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            var1_string = self.parsestring()
            var2_TokenPairs = self.parseTokenPairs()
            return (var0_name, var1_string, var2_TokenPairs,)
        return  # epsilon case

    def parseDecls(self):
        if self.next() in ("name",):
            var0_Decl = self.parseDecl()
            var1_Decls = self.parseDecls()
            return Declarations(('decl', 'var0_Decl'), ('rest', 'var1_Decls'))
        return  # epsilon case

    def parsestring(self):
        parseerror()

    def parseDecl(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            var1_':=' = self.consume("':='")
            var2_Alt = self.parseAlt()
            var3_Alts = self.parseAlts()
            var4_';' = self.consume("';'")
            return Declaration(('name', 'var0_name'), ('_', "var1_':='"), ('alt', 'var2_Alt'), ('alts', 'var3_Alts'), ('_', "var4_';'"))
        parseerror()

    def parseAlt(self):
        if self.next() in ("name",):
            var0_Term = self.parseTerm()
            var1_Terms = self.parseTerms()
            var2_Binding = self.parseBinding()
            return Alternative(('term', 'var0_Term'), ('terms', 'var1_Terms'), ('bind', 'var2_Binding'))
        parseerror()

    def parseAlts(self):
        if self.next() in ("'|'",):
            var0_'|' = self.consume("'|'")
            var1_Alt = self.parseAlt()
            var2_Alts = self.parseAlts()
            return Alternatives(('_', "var0_'|'"), ('alt', 'var1_Alt'), ('alts', 'var2_Alts'))
        return  # epsilon case

    def parseTerm(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            return Name(('val', 'var0_name'))
        if self.next() in ("",):
            var0_string = self.parsestring()
            return String(('val', 'var0_string'))
        parseerror()

    def parseTerms(self):
        if self.next() in ("name",):
            var0_Term = self.parseTerm()
            var1_Terms = self.parseTerms()
            return Terms(('term', 'var0_Term'), ('terms', 'var1_Terms'))
        return  # epsilon case

    def parseBinding(self):
        if self.next() in ("'#'",):
            var0_'#' = self.consume("'#'")
            var1_name = self.consume("name")
            var2_Names = self.parseNames()
            return Binding(('_', "var0_'#'"), ('name', 'var1_name'), ('names', 'var2_Names'))
        return  # epsilon case

    def parseNames(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            var1_Names = self.parseNames()
            return Names(('name', 'var0_name'), ('names', 'var1_Names'))
        return  # epsilon case

    def _parseRoot(self):
        return self.parseSpec()

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
    ''' A Production is an ordered list of terms (Terminals and Nonterminals).
        All terms should already exist before declaring Productions.
        Once all Productions exist, one can compute first then follow sets.
    '''

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


class Emitter(object):
    def __init__(self, tree, start):#, grammar):
        # self.head = grammar;
        self.s = HEADER
        self.tree = tree  # parse tree made of lists
        self.start = start  # name of root grammar rule
        self.parser = ''  # build up parser classes/functions here
        self.objs = ''  # put named class definitions here
        self.tokenmap = {}  # maps string to Terminal object
        self.namemap = {}  # maps string to Nonterminal object
        self.lexmap = []  # (name, regex) pairs for lexer

        s = ''
        s += "class GrammarObj(object):\n"
        s += "    def __str__(self):\n"
        s += "        return self.name\n"
        s += "    def __repr__(self):\n"
        s += "        s = self.name + '['\n"
        s += "        for k,v in self.attrs:\n"
        s += "            s += \"{{}}:{{}}, \".format(k,v)\n"
        s += "        s += ']'\n"
        s += "        return s\n\n"
        s += "    def __init__(self, *args):\n"
        s += "        i = 0\n"
        s += "        for k,v in args:\n"
        s += "            if k == \"_\":\n"
        s += "                setattr(self, \"_anon{{}}\".format(i), v)\n"
        s += "                i += 1\n"
        s += "            else:\n"
        s += "                setattr(self, k, v)\n"
        s += "        self.attrs = args\n\n"
        self.objs += s


    def findterms(self, root):
        # Find the terminals, nonterminals, and productions in the grammar
        # Requires root grammar nonterminal
        nonterms = []
        prods = []
        terms = []
        stack = [root, ]
        seen = set()
        while stack:
            term = stack.pop(0)
            if term in seen:
                continue
            seen.add(term)
            nonterms.append(term)
            for prod in term.productions:
                prods.append(prod)
                for item in prod.prod:
                    if isinstance(item, Nonterminal):
                        stack.append(item)
                    elif isinstance(item, Terminal):
                        terms.append(item)
        self.nonterminals = nonterms
        #self.productions = prods
        #self.terminals = terms


    def emitdecl(self, decl):
        name = decl[1]
        rhs = decl[3:]
        #print(name, rhs)
        alt = rhs[0]
        alts = rhs[1]

        if any([x(name) for x in self.tokenmap.values()]):  # see if name is token
            pass
        elif name not in self.namemap:  # otherwise, it's a nonterminal
            self.namemap[name] = Nonterminal(name)

        #print(name, alt)
        prods = [self.emitalt(name, alt),]
        while alts:
            #print("alts", alts)
            rhs = alts[2:]
            alt = rhs[0]
            prods.append(self.emitalt(name, rhs[0]))
            alts = rhs[1]

        return prods

    def emitalt(self, name, alt):
        #print("alt", name, alt, len(alt))

        if alt[1] == "$":  # epsilon
            binding = None
            term = None
        else:
            prod = alt[0]
            term = alt[1]
            terms = alt[2]
            binding = alt[3]

        if binding:
            bnames = self.getbinding(binding)
        else:
            bnames = None

        #print (name, term)
        if not term:
            return (name, [None,], bnames)

        args = [self.emitterm(term),]
        while len(terms) > 1:
            args.append(self.emitterm(terms[1]))
            terms = terms[2]

        for arg in args:
            # print(arg)
            if arg[0] in ("'", "\""):
                if any([x(arg) for x in self.tokenmap.values()]):
                    continue
                else:
                    self.tokenmap[arg] = Terminal(arg, arg)
                    self.lexmap.append((arg, arg))
            else:  # name
                if any([x(arg) for x in self.tokenmap.values()]):  # see if name is token
                    continue
                if arg not in self.namemap:  # otherwise, it's a nonterminal
                    self.namemap[arg] = Nonterminal(arg)

        return (name, args, bnames)

    def emitterm(self, term):
        obj = term[1]
        return obj

        # print(name, names)

        # print("emitting alt ")
        # prod.pclass = names[0]
        # print(prod.pclass)

        # s = ''
        # s += "class {}(object):\n".format(names[0])
        # args = names[1:]
        # s += "\tdef __init__(self, {}):\n".format(', '.join(args))
        # for arg in args:
        #     s += "\t\tself.{} = {}\n".format(arg, arg)
        #
        # s += '\n'
        # self.s += s

    def getbinding(self, binding):
        assert(binding[1] == "#")
        name = binding[2]
        if binding[3]:
            names = self.getnames(binding[3])
        else:
            names = []
        return [name, ] + names

    def getnames(self, names):
        if names[1] == "$":
            return []
        name = names[1]
        names = names[2]
        if names:
            return [name,] + self.getnames(names)
        else:
            return [name, ]

    def gettokens(self, toktree):
        pairs = toktree[2]

        while pairs:
            name = pairs[1]
            regex = pairs[2]
            pairs = pairs[3]
            regex = regex.strip()[1:-1]
            self.tokenmap[name] = Terminal(name, regex)
            self.lexmap.append((name, regex))

    def emit(self):
        #print("emit", self.tree)

        tree = self.tree
        rootdecl = tree[1]
        toktree = tree[2]
        grammars = tree[3]
        assert(rootdecl[1] == "%root")
        assert(toktree[1] == "%tokens")
        assert(grammars[1] == "%grammar")
        root = rootdecl[2]
        self.gettokens(toktree)

        tree = grammars[2]

        prods = []
        while tree:
            # print(tree)
            prods += self.emitdecl(tree[1])
            tree = tree[2]

        # Now that all terminal and nonterminals seen and created, instantiate productions
        allmap = self.namemap.copy()
        allmap.update(self.tokenmap)
        allmap[None] = None  # for epsilon terms
        #print('\n'.join(map(str,prods)))
        for name, args, binding in prods:
            # print("Generating production for", name, "with", args)
            # print(self.namemap)
            x = Production(self.namemap[name], *[allmap[x] for x in args])
            if binding:
                s = ''
                s += "class {}(GrammarObj):\n".format(binding[0])
                s += "    def __init__(self, *args):\n"
                s += "        super().__init__(*args)\n"
                s += "        self.name = \"{}\"\n".format(binding[0])
                # for i,b in enumerate(binding[1:]):
                #     s += "        self.{} = args[{}]\n".format(b, i)
                self.objs += s + '\n'
                x.pclass = binding
            else:
                x.pclass = None

        # Emit lexer map
        self.objs += "LEXMAP = {}\n\n".format(self.lexmap)

        # Find all the nonterminals and make a parse function for each
        root = self.namemap[self.start]
        root.compile()
        self.findterms(self.namemap[self.start])
        for nt in self.nonterminals:
            self.emitfunc(nt)

        s = ''
        s += "    def _parseRoot(self):\n"
        s += "        return self.parse{}()\n\n".format(root)
        self.parser += s

        # def buildandparse(s):
        #     root = self.namemap[self.start]
        #     root.compile()
        #     p = Parser(self.lexmap, s)
        #     #print(p.toks)
        #     return p.parse(self.namemap[self.start])
        #
        #
        # return buildandparse


    def emitfunc(self, nonterm):
        s = ''
        s += "    def {}(self):\n".format(fname(nonterm.name))
        epsilon = False
        for rule in nonterm.rules:
            epsilon |= None in rule[0]
            firsts = rule[0].difference(set((None,)))
            tokset = "(\"{}\",)".format('\", \"'.join([tok.name for tok in firsts]))
            production = rule[1]
            variables = []
            if not production.prod[0]:
                continue
            s += "        if self.next() in {}:\n".format(tokset)
            for i,term in enumerate(production.prod):
                variables.append("var{}_{}".format(i, term.name))
                if isinstance(term, Nonterminal):
                    s += "            var{}_{} = self.{}()\n".format(i, term.name, fname(term.name))
                else:
                    s += "            var{}_{} = self.consume(\"{}\")\n".format(i, term.name, term.name)
            # print(production, dir(production))
            if production.pclass:
                binding = production.pclass
                attrs = map(str, zip(binding[1:], variables))
                s += "            return {}({})\n".format(production.pclass[0], ', '.join(attrs))
            else:
                s += "            return ({},)\n".format(', '.join(variables))
        if epsilon:
            s += "        return  # epsilon case\n\n"
        else:  # error case
            s += "        parseerror()\n\n"

        self.parser += s

    

def main():
    import sys
    with open(sys.argv[1]) as f:
        s = f.read()
    p = Parser()
    ast = p.parse(s)
    #e = Emitter(ast, )
    print(ast)

if __name__ == "__main__":
    main()


