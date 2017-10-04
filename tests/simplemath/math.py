
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
class Exp(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Exp"

class Plus(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Plus"

class Term(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Term"

class Mult(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Mult"

class Paren(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Paren"

class Num(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Num"

LEXMAP = [('plus', '\\+'), ('mult', '\\*'), ('lparen', '\\('), ('rparen', '\\)'), ('num', '[0-9]+'), ('name', '\\w+')]


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

    def parseE(self):
        if self.next() in ("lparen", "num",):
            var0_T = self.parseT()
            var1_Ep = self.parseEp()
            return Exp(('op', var0_T),('rhs', var1_Ep),)
        self.parsefail(['("lparen", "num",)'], self.next())

    def parseT(self):
        if self.next() in ("lparen", "num",):
            var0_F = self.parseF()
            var1_Tp = self.parseTp()
            return Term(('op', var0_F),('rhs', var1_Tp),)
        self.parsefail(['("lparen", "num",)'], self.next())

    def parseEp(self):
        if self.next() in ("plus",):
            var0_plus = self.consume("plus")
            var1_T = self.parseT()
            var2_Ep = self.parseEp()
            return Plus(('_', var0_plus),('op', var1_T),('rest', var2_Ep),)
        return  # epsilon case

    def parseF(self):
        if self.next() in ("lparen",):
            var0_lparen = self.consume("lparen")
            var1_E = self.parseE()
            var2_rparen = self.consume("rparen")
            return Paren(('_', var0_lparen),('exp', var1_E),('_', var2_rparen),)
        if self.next() in ("num",):
            var0_num = self.consume("num")
            return Num(('val', var0_num),)
        self.parsefail(['("lparen",)', '("num",)'], self.next())

    def parseTp(self):
        if self.next() in ("mult",):
            var0_mult = self.consume("mult")
            var1_F = self.parseF()
            var2_Tp = self.parseTp()
            return Mult(('_', var0_mult),('op', var1_F),('rest', var2_Tp),)
        return  # epsilon case

    def _parseRoot(self):
        return self.parseE()


def main():
    with open(sys.argv[1]) as f:
        s = f.read()
    p = Parser()
    ast = p.parse(s)
    print(repr(ast))

if __name__ == "__main__":
    main()

