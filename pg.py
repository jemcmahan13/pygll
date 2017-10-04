import re, sys

# log = True
log = False

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


class Parser(object):

    class ScanError(Exception):
        pass
    class ParseError(Exception):
        pass
    def parsefail(self, expected, found, val=None):
        raise Parser.ParseError("Parse Error, line {}: Expected token {}, but found token {}:{}".\
            format(self.line, expected, found, val))
    def scanfail(self):
        raise Parser.ScanError("Lexer Error, line {}: No matching token found. Remaining input: {} ...."\
            .format(self.line, self.remaining[:50]))


    def __init__(self, lexerMap, s):
        # Intialize with an ordered list containint tuples (name, regex) defining
        # the language's tokens, and a string s to parse.
        # Tokenization occurs in the order given: the most specific tokens (keywords)
        # should be earlier in the list.
        lex = [('whitespace', '\s+'),] + [ x for x in lexerMap ]
        rules = [ (regex, self.makeHandler(tokenName)) for tokenName, regex in lex ]
        self.scanner = re.Scanner(rules)
        self.s = s
        self.line = 1
        self.log = log

        self.toks, self.remaining = self.scanner.scan(self.s)
        self.trim()

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

    def parse(self, nonterminal):
        # Parse input according to a given Nonterminal object.
        # nonterminal: [ (tokens, Production) ]
        if log:
            print("Parsing nonterminal ", nonterminal)
        epsilon = False
        for rule in nonterminal.rules:
            if log:
                print("checking ", rule[1])
            epsilon |= None in rule[0]
            firsts = rule[0].difference(set((None,)))
            for tok in firsts:
                #print("checking token", tok)
                if tok(self.next()):  # match
                    if log:
                        print("Match")
                    #self.consume(tok.name)
                    production = rule[1]
                    terms = []
                    for term in production.prod:
                        # NTS - make production iterable
                        if isinstance(term, Terminal):
                            terms.append(self.consume(term.name))
                        else:
                            terms.append(self.parse(term))
                    if rule[1].pclass:  # there's a name binding for this production
                        binding = rule[1].pclass
                        return GrammarObj(binding[0], *zip(binding[1:], terms))
                    else:
                        return [rule[1],] + terms
        if epsilon:
            if log:
                print("Taking epsilon")
            return []
        else:
            self.parsefail(' or '.join([str([ x.name for x in r[0] if x]) for r in nonterminal.rules]), self.next())


        # rules = rule.rules  # get the list of tuples
        # firstlist = [ x[0] for x in rules ]  # list of firsts for each production
        #
        # while True:
        #     common = rules[0][0]  # find if all rules have something in common
        #     _ = [ common.intersection_update(x) for x in  ]
        #     if common:  # there are some tokens in common with all remaining rules
        #         # parse the common tokens
        #         for tok in common:
        #             if tok(self.next()):
        #                 self.consume(tok.name)
        #                 break  # now loop
        #     else:  # there are no tokens common to all rules; eliminate some
        #         for rule in rules:
        #             if rule[0]()



from header import HEADER

class Emitter(object):
    def __init__(self, tree, start):#, grammar):
        # self.head = grammar;
        self.s = HEADER
        self.tree = tree  # parse tree made of lists
        self.start = start  # root grammar nonterminal
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

class GrammarObj(object):
    def __init__(self, *args):
        self.name = args[0]
        i = 0
        for k,v in args[1:]:
            if k == "_":
                setattr(self, "_anon{}".format(i), v)
                i += 1
            else:
                setattr(self, k, v)
        self.attrs = args[1:]
    def __str__(self):
        return self.name
    def __repr__(self):
        s = self.name + '['
        for k,v in self.attrs:
            s += "{}:{}, ".format(k,v)
        s += ']'
        return s

def fname(name):
    return "parse{}".format(name)

def ebnf():

    # Declare Nonterminals
    Spec = Nonterminal("Spec")
    RootDecl = Nonterminal("RootDecl")
    TokenDecl = Nonterminal("TokenDecl")
    TokenPairs = Nonterminal("TokenPairs")
    GrammarDecl = Nonterminal("GrammarDecl")
    Decls = Nonterminal("Decls")
    Decl = Nonterminal("Decl")
    Term = Nonterminal("Term")
    Terms = Nonterminal("Terms")
    Alt = Nonterminal("Alt")
    Alts = Nonterminal("Alts")
    Binding = Nonterminal("Binding")
    Names = Nonterminal("Names")

    # make terminals and lex map
    def makeTerminals(lex, *args):
        terms = []
        while args:
            name = args[0]
            regex = args[1]
            args = args[2:]
            terms.append(Terminal(name, regex))
            lex.append((name, regex))
        return terms

    lex = []
    equals, pound, epsilon, semicolon, bar, rootkw, tokenkw, grammarkw, string, name = makeTerminals(
    lex, 'equals', r':=', 'pound', r'\#', 'epsilon', '\$', 'semicolon', r';', 'bar', r'\|',\
    'rootkw', r'\%root', 'tokenkw', r'\%tokens', 'grammarkw', r'\%grammar', 'string', r'(\"|\').*?\1', 'name', r'\w+')

    # Declare productions
    Spec1 = Production(Spec, RootDecl, TokenDecl, GrammarDecl)
    RootDecl1 = Production(RootDecl, rootkw, name)
    TokenDecl1 = Production(TokenDecl, tokenkw, TokenPairs)
    TokenPairs1 = Production(TokenPairs, name, string, TokenPairs)
    TokenPairs2 = Production(TokenPairs, None)
    GrammarDecl1 = Production(GrammarDecl, grammarkw, Decls)
    Decls1 = Production(Decls, Decl, Decls)
    Decls2 = Production(Decls, None)
    Decl1 = Production(Decl, name, equals, Alt, Alts, Binding, semicolon)
    Alt1 = Production(Alt, Term, Terms, Binding)
    Alt2 = Production(Alt, epsilon)
    Alts1 = Production(Alts, bar, Alt, Alts)
    Alts2 = Production(Alts, None)
    Term1 = Production(Term, name)
    Term2 = Production(Term, string)
    Terms1 = Production(Terms, Term, Terms)
    Terms2 = Production(Terms, None)
    Binding1 = Production(Binding, pound, name, Names)
    Binding2 = Production(Binding, None)
    Names1 = Production(Names, name, Names)
    Names2 = Production(Names, None)

    Spec.root()

    ebnfgrammar='''
    %root Spec
    %tokens
    name "\w+"
    %grammar

    Spec := RootDecl TokenDecl GrammarDecl
          ;
    RootDecl := '%root' name
              ;
    TokenDecl := '%tokens' TokenPairs
               ;
    TokenPairs := name string TokenPairs
                | $
                ;
    GrammarDecl := '%grammar' Decls
                 ;
    Decls := Decl Decls              # Declarations decl rest
           | $
           ;
    Decl := name ':=' Alt Alts ';'  # Declaration name _ alt alts _
          ;
    Alt := Term Terms Binding       # Alternative term terms bind
         ;
    Alts := '|' Alt Alts             # Alternatives _ alt alts
          | $
          ;
    Term := name                     # Name val
          | string                  # String val
          ;
    Terms := Term Terms              # Terms term terms
           | $
           ;
    Binding := '#' name Names        # Binding _ name names
             | $
             ;
    Names := name Names              # Names name names
           | $
           ;
    '''

    mathgrammar='''
    %root E

    %tokens
    plus "\+"
    mult "\*"
    lparen "\("
    rparen "\)"
    num "[0-9]+"
    name "\w+"

    %grammar
    E := T Ep           # Exp op rhs ;
    Ep := plus T Ep      # Plus _ op rest
        | $ ;
    T := F Tp           # Term op rhs;
    Tp := mult F Tp      # Mult _ op rest
        | $ ;
    F := lparen E rparen      # Paren _ exp _
       | num           # Num val;
    '''
    mathtokens = (
    ('plus', r'\+'),
    ('mult', r'\*'),
    ('lparen', r'\('),
    ('rparen', r'\)'),
    ('num', r'[0-9]+'),
    ('name', r'\w+'),
    )
    # Declare Nonterminals and Terminals
    E = Nonterminal("E")
    Ep = Nonterminal("E'")
    T = Nonterminal("T")
    Tp = Nonterminal("T'")
    F = Nonterminal("F")
    plus = Terminal('plus', r'\+')
    mult = Terminal('mult', r'\*')
    name = Terminal('name', r'\w')
    num = Terminal('num', r'[0-9]+')
    lparen = Terminal('lparen', r'\(')
    rparen = Terminal('rparen', r'\)')
    # Declare Productions
    E1 = Production(E, T, Ep)
    Ep1 = Production(Ep, plus, T, Ep)
    Ep2 = Production(Ep, None)
    T1 = Production(T, F, Tp)
    Tp1 = Production(Tp, mult, F, Tp)
    Tp2 = Production(Tp, None)
    F1 = Production(F, lparen, E, rparen)
    F2 = Production(F, num)


    # p = Parser(lex, ebnfgrammar)
    p = Parser(lex, ebnfgrammar)
    s = p.parse(Spec)
    #print(s)
    e = Emitter(s, 'Spec')
    s = '''3
    +
    4
    *
    (
    9
    +
    2
    )
    '''

    # s = "3"

    parse = e.emit()

    # for name,prod in e.namemap.items():
    #     print(name, prod.first)

    #print(e.parser)

    #print(parse(s))

    text = e.objs + HEADER.replace("GRAMMARROOT", 'E') + e.parser + pfunc
    print(text)

    return text

pfunc ='''
def main():
    import sys
    with open(sys.argv[1]) as f:
        s = f.read()
    p = Parser()
    p.parse(s)

if __name__ == "__main__":
    main()

'''

ebnf()
