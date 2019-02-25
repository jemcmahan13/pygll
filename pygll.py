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

class exprepeat(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "exprepeat"

class expset(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "expset"

class eopt(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "eopt"

class Expr(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Expr"

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

LEXMAP = [('pound', '#'), ('bar', '\|'), ('epsilon', '\$'), ('lrepeat', '\['), ('rrepeat', '\]'), ('lset', '{'), ('rset', '}'), ('lopt', '<'), ('ropt', '>'), ('string', '(\\\'|\\").*?[^\\\\]\\1'), ('name', '\w+'), ('%root', '%root'), ('%tokens', '%tokens'), ('%grammar', '%grammar'), (':=', ':='), (';', ';')]


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
        if not self.toks and self.remaining:
            self.scanfail()
        if len(self.toks) == 0:
            self.parsefail(tok, 'EOF')
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
            return var0_RootDecl, var1_TokenDecl, var2_GrammarDecl
        self.parsefail(['("%root",)'], self.next())

    def parseRootDecl(self):
        if self.next() in ("%root",):
            var0_root = self.consume("%root")
            var1_name = self.consume("name")
            return var0_root, var1_name
        self.parsefail(['("%root",)'], self.next())

    def parseTokenDecl(self):
        if self.next() in ("%tokens",):
            var0_tokens = self.consume("%tokens")
            var1_TokenPairs = self.parseTokenPairs()
            return var0_tokens, var1_TokenPairs
        self.parsefail(['("%tokens",)'], self.next())

    def parseGrammarDecl(self):
        if self.next() in ("%grammar",):
            var0_grammar = self.consume("%grammar")
            var1_Decls = self.parseDecls()
            return var0_grammar, var1_Decls
        self.parsefail(['("%grammar",)'], self.next())

    def parseTokenPairs(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            var1_string = self.consume("string")
            var2_TokenPairs = self.parseTokenPairs()
            return var0_name, var1_string, var2_TokenPairs
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
        if self.next() in ("string", "lopt", "lrepeat", "lset", "name",):
            var0_Exp = self.parseExp()
            var1_Exps = self.parseExps()
            var2_Binding = self.parseBinding()
            return Alternative(('exp', var0_Exp),('exps', var1_Exps),('bind', var2_Binding),)
        if self.next() in ("epsilon",):
            var0_epsilon = self.consume("epsilon")
            return  # production suppressed
        self.parsefail(['("string", "lopt", "lrepeat", "lset", "name",)', '("epsilon",)'], self.next())

    def parseAlts(self):
        if self.next() in ("bar",):
            var0_bar = self.consume("bar")
            var1_Alt = self.parseAlt()
            var2_Alts = self.parseAlts()
            return Alternatives(('_', var0_bar),('alt', var1_Alt),('alts', var2_Alts),)
        return  # epsilon case

    def parseExp(self):
        if self.next() in ("lrepeat",):
            var0_lrepeat = self.consume("lrepeat")
            var1_Exps = self.parseExps()
            var2_rrepeat = self.consume("rrepeat")
            return exprepeat(('_', var0_lrepeat),('exps', var1_Exps),('_', var2_rrepeat),)
        if self.next() in ("lset",):
            var0_lset = self.consume("lset")
            var1_Exps = self.parseExps()
            var2_rset = self.consume("rset")
            return expset(('_', var0_lset),('exps', var1_Exps),('_', var2_rset),)
        if self.next() in ("lopt",):
            var0_lopt = self.consume("lopt")
            var1_Exps = self.parseExps()
            var2_ropt = self.consume("ropt")
            return eopt(('_', var0_lopt),('exps', var1_Exps),('_', var2_ropt),)
        if self.next() in ("string", "name",):
            var0_Term = self.parseTerm()
            return var0_Term
        self.parsefail(['("lrepeat",)', '("lset",)', '("lopt",)', '("string", "name",)'], self.next())

    def parseExps(self):
        if self.next() in ("string", "lopt", "lrepeat", "lset", "name",):
            var0_Exp = self.parseExp()
            var1_Exps = self.parseExps()
            return Expr(('exp', var0_Exp),('exps', var1_Exps),)
        return  # epsilon case

    def parseBinding(self):
        if self.next() in ("pound",):
            var0_pound = self.consume("pound")
            var1_name = self.consume("name")
            var2_Names = self.parseNames()
            return Binding(('_', var0_pound),('bname', var1_name),('names', var2_Names),)
        return  # epsilon case

    def parseTerm(self):
        if self.next() in ("name",):
            var0_name = self.consume("name")
            return Name(('val', var0_name),)
        if self.next() in ("string",):
            var0_string = self.consume("string")
            return String(('val', var0_string),)
        self.parsefail(['("name",)', '("string",)'], self.next())

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
