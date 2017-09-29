
class Grammar(object):
    # This class directly models the grammar.
    # Each nonterminal in the grammar has one nonterminal object here.
    
    class Terminal(object):
        def __init__(self, name):
            self.name = name

        def first(self):
            return self  # the terminal is a first token
            
            
    class Nonterminal(object):
        def __init__(self, name):
            self.name = name


    class Production(object):
        def __init__(self, *args):
            # args should be a sequence of Nonterminals and Terminals
            # Null production represents epsilon
            self.prod = args
            self.first = None
            self.followers = set()  # set of nonterm and terms that follow
            self.follows = set()  # set of terminals that follow

            for i,arg in enumerate(args):
                if i < len(args):
                    arg.addfollower(args[i+1])
                    
        def addfollower(self, item):
            self.followers.add(item)
                    
        def first(self):
            if self.first:
                return self.first
            # otherwise, compute first set
            if not self.prod:  # epsilon
                return None  
            return self.prod[0].first()

        def follow(self):
            # Call only after grammar is finished and all followers have been added
            for f in self.followers:
                self.follows.add(f.first())
