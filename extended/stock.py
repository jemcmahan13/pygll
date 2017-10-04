PCLASS = '''
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
        self.log = False

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
                self.line += match.count('\\n')
                self.toks.pop(0)
                self.trim()

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

'''

GOBJ='''
import re, sys

class GrammarObj(object):
    def __str__(self):
        return self.name
    def __repr__(self):
        s = self.name + '['
        for k,v in self.attrs:
            s += \"{}:{}, \".format(k,v)
        s += ']'
        return s
    def __init__(self, *args):
        i = 0
        for k,v in args:
            if k == \"_\":
                setattr(self, \"_anon{{}}\".format(i), v)
                i += 1
            else:
                setattr(self, k, v)
        self.attrs = args

'''

MAIN='''
def main():
    with open(sys.argv[1]) as f:
        s = f.read()
    p = Parser()
    ast = p.parse(s)
    print(repr(ast))

if __name__ == "__main__":
    main()
'''
