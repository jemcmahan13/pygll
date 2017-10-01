import re, sys

#log = True
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
                    return terms
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

def ebnf():

    # Declare Nonterminals
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
    equals, pound, epsilon, semicolon, bar, string, name = makeTerminals(lex, 'equals', r':=',
                                                                              'pound', r'\#',
                                                                              'epsilon', '\$',
                                                                              'semicolon', r';',
                                                                              'bar', r'\|',
                                                                              'string', r'(\"|\').*?\1',
                                                                              'name', r'\w+')

    # Declare productions
    Decls1 = Production(Decls, Decl, Decls)
    Decls2 = Production(Decls, None)
    Decl1 = Production(Decl, name, equals, Alt, Alts, Binding, semicolon)
    Alt1 = Production(Alt, Term, Terms, Binding)
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

    Decls.root()

    ebnfgrammar='''
    Decls := Decl Decls | '$';
    Decl := Name ':=' Alt Alts ';';
    Alt := Term Terms Binding;
    Alts := '|' Alt Alts | '$';
    Term := name | string;
    Terms := Term Terms | '$';
    Binding := '#' Name Names | '$';
    Names := Name Names | '$';
    '''

    p = Parser(lex, ebnfgrammar)
    # print(p.toks, p.s)
    print(p.parse(Decls))



def simpletest():
    # Test grammar
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
    lparen = Terminal('lapren', r'\(')
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

    # Declare tokens
    tokens = (
    ('plus', r'\+'),
    ('mult', r'\*'),
    ('lapren', r'\('),
    ('rparen', r'\)'),
    ('num', r'[0-9]+'),
    ('name', r'\w+'),
    )

    E.root()  # declare root production

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
    #
    # for x in (E, Ep, T, Tp, F):
    #     print(repr(x))
    #     print(x.first, x.follow)



    def printLists(l, depth=0):
        s = ''
        t = '\t'
        for x in l:
            if isinstance(x, list):
                s += '[' + printLists(x, depth+1) +  ']'
            else:
                s += x
        return "{}\n{}".format(s, t*depth)


    p = Parser(tokens, s)
    #print(p.toks)
    print(printLists(p.parse(E)))

ebnf()
