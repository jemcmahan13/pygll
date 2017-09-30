import re

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
        self.top = True

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
        raise Parser.ScanError("Lexer Error, line {}: No matching token found. Remaining input: {}"\
            .format(self.line, self.remaining[:50]))


    def __init__(self, lexerMap, s):
        # Intialize with an ordered list containint tuples (regex, name) defining
        # the language's tokens, and a string s to parse.
        # Tokenization occurs in the order given: the most specific tokens (keywords)
        # should be earlier in the list.
        rules = [ (p, self.makeHandler(t)) for p,t in Parser.rules ]
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

    def next(self):
        if self.toks:
            token,match = self.toks[0]
            return token
        elif self.remaining:
            self.scanfail()

    def consume(self, tok):
        token,match = self.toks.pop(0)
        if tok != token:
            self.parsefail(tok, token, match)
        if self.log:
            print("consuming {}:{}".format(tok, match))
        self.trim()
        return match

    def pop(self):
        return self.consume(self.next())

    def parse(rule):
        # Parse input according to a given Nonterminal object.
        # rule = { Token list : list of terms }
        for rule in rule.rules:
            for tok in rule[0]:
                if tok(self.next()):  # match
                    self.consume(tok.name)
                    production = rule[1]
                    for term in production.prods:
                        # NTS - make production iterable
                        if isinstance(term, Terminal):
                            self.consume(term.name)
                        else:
                            self.parse(term)


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


# Test grammar
# Declare Nonterminals and Terminals
E = Nonterminal("E")
Ep = Nonterminal("E'")
T = Nonterminal("T")
Tp = Nonterminal("T'")
F = Nonterminal("F")
plus = Terminal('plus', r'\+')
mult = Terminal('mult', r'\*')
name = Terminal('name', r'\w+')
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
F2 = Production(F, name)

E.compile()  # must call before doing follow sets
E.root()  # declare root production

for x in (E, Ep, T, Tp, F):
    #print('---->', x, x.endOf, x.followers)
    #print(x, x.follow)
    #print(x.follow)
    print(x, x.first)
