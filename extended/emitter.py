from stock import GOBJ
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

class Operator(object):
    def __init__(self, exps):
        self.exps = exps

class Repeat(Operator):
    pass
class Set(Operator):
    pass
class Optional(Operator):
    pass

class Emitter(object):
    def __init__(self, tree):#, grammar):
        self.tree = tree  # parse tree made of lists
        self.start = None  # name of root grammar rule
        self.parser = ''  # build up parser classes/functions here
        self.objs = GOBJ  # put named class definitions here
        self.tokenmap = {}  # maps string to Terminal object
        self.namemap = {}  # maps string to Nonterminal object
        self.lexmap = []  # (name, regex) pairs for lexer

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


    def emit(self):
        #print("emit", self.tree)

        tree = self.tree
        rootdecl = tree[0]
        toktree = tree[1]
        grammars = tree[2]
        assert(rootdecl[0] == "%root")
        assert(toktree[0] == "%tokens")
        assert(grammars[0] == "%grammar")
        root = rootdecl[1]
        self.gettokens(toktree)

        tree = grammars[1]
        self.start = tree.decl.dname  # save root rule for parsing

        prods = []
        while tree:
            prods += self.emitdecl(tree.decl)
            tree = tree.rest

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
        self.objs += "LEXMAP = {}\n\n".format(self.lexmap).replace('\\\\','\\')

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

    def emitdecl(self, decl):
        name = decl.dname
        alt = decl.alt
        alts = decl.alts

        if any([x(name) for x in self.tokenmap.values()]):  # see if name is token
            pass
        elif name not in self.namemap:  # otherwise, it's a nonterminal
            self.namemap[name] = Nonterminal(name)

        #print(name, alt)
        prods = [self.emitalt(name, alt),]
        while alts:
            prods.append(self.emitalt(name, alts.alt))
            alts = alts.alts

        return prods

    def emitalt(self, name, alt):
        if not alt:  # epsilon
            binding = None
            exp = None
        else:
            exp = alt.exp
            exps = alt.exps
            binding = alt.bind

        if binding:
            bnames = self.getbinding(binding)
        else:
            bnames = None

        #print (name, term)
        if not exp:
            return (name, [None,], bnames)

        args = [self.emitexp(exp),] +  self.emitexps(exps)

        return (name, args, bnames)

    def emitexps(self, exps):
        ret = []
        while exps:
            ret.append(self.emitexp(exps.exp))
            exps = exps.exps
        return ret

    def emitexp(self, exp):
        if exp.name == "exprepeat":
            exps = self.emitexps(exp.exps)
            res = Repeat(exps)
        elif exp.name == "expset":
            exps = self.emitexps(exp.exps)
            res = Set(exps)
        elif exp.name == "eopt":
            exps = self.emitexps(exp.exps)
            res = Optional(exps)
        else:  # expression was just a term
            res = self.emitterm(exp)
            self.register((res,))
        return res

    def register(self, args):
        # generate Terminals and Nonterminals for strings we haven't seen yet
        for arg in args:
            # print("Argument: ", arg)
            if arg[0] in ("'", "\""):
                val = arg[1:-1]
                # print(arg, val)
                if any([x(val) for x in self.tokenmap.values()]):
                    continue
                else:
                    self.tokenmap[val] = Terminal(val, val)
                    self.tokenmap[arg] = Terminal(val, val)
                    self.lexmap.append((val, val))
            else:  # name
                if any([x(arg) for x in self.tokenmap.values()]):  # see if name is token
                    continue
                if arg not in self.namemap:  # otherwise, it's a nonterminal
                    self.namemap[arg] = Nonterminal(arg)

    def emitterm(self, term):
        obj = term.val
        return obj

    def getbinding(self, binding):
        name = binding.bname
        if binding.names:
            names = self.getnames(binding.names)
        else:
            names = []
        return [name, ] + names

    def getnames(self, names):
        if not names:
            return []
        name = names.termname
        names = names.names
        if names:
            return [name,] + self.getnames(names)
        else:
            return [name, ]

    def gettokens(self, toktree):
        pairs = toktree[1]

        while pairs:
            name = pairs[0]
            regex = pairs[1]
            pairs = pairs[2]
            regex = regex.strip()[1:-1]
            self.tokenmap[name] = Terminal(name, regex)
            self.lexmap.append((name, regex))
            # print("Regex: ", name, regex)

    def emitfunc(self, nonterm):
        s = ''
        s += "    def {}(self):\n".format(fname(nonterm.name))
        epsilon = False
        alltoks = []
        for rule in nonterm.rules:
            epsilon |= None in rule[0]
            firsts = rule[0].difference(set((None,)))
            tokset = "(\"{}\",)".format('\", \"'.join([tok.name for tok in firsts]))
            alltoks.append(tokset)  # get all tokens together for error case
            production = rule[1]
            variables = []
            if not production.prod[0]:
                continue
            s += "        if self.next() in {}:\n".format(tokset)
            for i,term in enumerate(production.prod):
                cleanname = sanitize(term.name)
                variables.append("var{}_{}".format(i, cleanname))
                if isinstance(term, Nonterminal):
                    s += "            var{}_{} = self.{}()\n".format(i, cleanname, fname(cleanname))
                else:
                    s += "            var{}_{} = self.consume(\"{}\")\n".format(i, cleanname, term.name)
            # print(production, dir(production))
            if production.pclass:
                binding = production.pclass
                if binding[0] == "_":  # suppress this production
                    s += "            return  # production suppressed\n"
                    continue
                attrs = zip(binding[1:], variables)
                sargs = ''
                for name, variable in attrs:
                    sargs += "('{}', {}),".format(name, variable)
                s += "            return {}({})\n".format(production.pclass[0], sargs)
            else:
                s += "            return {}\n".format(', '.join(variables))
        if epsilon:
            s += "        return  # epsilon case\n\n"
        else:  # error case
            s += "        self.parsefail({}, self.next())\n\n".format(alltoks)

        self.parser += s

def sanitize(name):
    return re.sub('[^0-9a-zA-Z_]', '', name)

def fname(name):
    return "parse{}".format(name)
