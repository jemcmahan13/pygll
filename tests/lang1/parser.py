
import re, sys

class GrammarObj(object):
    def __str__(self):
        return self.name
    def __repr__(self):
        s = self.name + '['
        for k,v in self.attrs:
            s += "{}:{}, ".format(k,repr(v))
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

class Assignment(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Assignment"

class Condition(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Condition"

class Print(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Print"

class Else(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "Else"

class ExpR(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "ExpR"

class ExpMath(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "ExpMath"

class ExpMath(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "ExpMath"

class ExpMult(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "ExpMult"

class ExpMultR(GrammarObj):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "ExpMultR"

LEXMAP = [('if', 'if'), ('then', 'then'), ('else', 'else'), ('print', 'print'), ('lt', '<'), ('gt', '>'), ('leq', '<='), ('geq', '>='), ('equal', '=='), ('plus', '\+'), ('minus', '\-'), ('mult', '\*'), ('divide', '\/'), ('number', '[0-9]+'), ('name', '\w+'), ('=', '='), (';', ';'), ('{', '{'), ('}', '}'), ('\(', '\('), ('\)', '\)')]


class Parser(object):

    class ScanError(Exception):
        pass
    class ParseError(Exception):
        pass
    def parsefail(self, expected, found, val=None):
        raise Parser.ParseError("Parse Error, line {}: Expected token {}, but found token {}:{}".format(self.line, expected, found, val))
    def scanfail(self):
        raise Parser.ScanError("Lexer Error, line {}: No matching token found. Remaining input: {} ....".format(self.line, self.remaining[:50]))


    def __init__(self, log=False):
        lex = [('whitespace', '\s+'),] + [ x for x in LEXMAP ]
        rules = [ (regex, self.makeHandler(tokenName)) for tokenName, regex in lex ]
        self.scanner = re.Scanner(rules)
        self.line = 1
        self.log = log

    def parse(self, s):
        self.toks, self.remaining = self.scanner.scan(s)
        self.trim()
        res = self._parseRoot()
        if self.toks:
            raise Parser.ParseError("Couldn't parse all of input. Next token: ", self.toks[0])
        return res

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
        token,match = self.toks.pop(0)
        if self.log:
            print("consuming {}:{}".format(tok, match))
        if tok != token:
            self.parsefail(tok, token, match)
        self.trim()
        return match

    def pop(self):
        return self.consume(self.next())

    def parseProgram(self):
        if self.log:
            print("Program")
        if self.next() in ("print", "if", "name",):
            var0_Statements = self.parseStatements()
            return var0_Statements
        self.parsefail(("print", "if", "name",), self.next())

    def parseStatements(self):
        if self.log:
            print("Statements")
        if self.next() in ("print", "if", "name",):
            var0_Statement = self.parseStatement()
            var1__anon_Repeat0 = self.parse_anon_Repeat0()
            return var0_Statement, var1__anon_Repeat0
        self.parsefail(("print", "if", "name",), self.next())

    def parseStatement(self):
        if self.log:
            print("Statement")
        if self.next() in ("name",):
            var0_name = self.consume("name")
            var1_ = self.consume("=")
            var2_Expression = self.parseExpression()
            var3_ = self.consume(";")
            return Assignment(('name', var0_name),('_', var1_),('expr', var2_Expression),('_', var3_),)
        if self.next() in ("if",):
            var0_if = self.consume("if")
            var1_Expression = self.parseExpression()
            var2_then = self.consume("then")
            var3_ = self.consume("{")
            var4_Statements = self.parseStatements()
            var5_ = self.consume("}")
            var6_OptionalElse = self.parseOptionalElse()
            return Condition(('_', var0_if),('cond', var1_Expression),('_', var2_then),('_', var3_),('truebranch', var4_Statements),('_', var5_),('elsebranch', var6_OptionalElse),)
        if self.next() in ("print",):
            var0_print = self.consume("print")
            var1_Expression = self.parseExpression()
            var2_ = self.consume(";")
            return Print(('_', var0_print),('name', var1_Expression),('_', var2_),)
        self.parsefail(("print", "if", "name",), self.next())

    def parse_anon_Repeat0(self):
        if self.log:
            print("_anon_Repeat0")
        if self.next() in ("print", "if", "name",):
            var0_Statement = []
            while self.next() in ("print", "if", "name",):
                var0_Statement.append(self.parseStatement())
            return var0_Statement
        return  # epsilon case

    def parseExpression(self):
        if self.log:
            print("Expression")
        if self.next() in ("\(", "number", "name",):
            var0_ExpMath = self.parseExpMath()
            var1_ExpressionR = self.parseExpressionR()
            return var0_ExpMath, var1_ExpressionR
        self.parsefail(("\(", "number", "name",), self.next())

    def parseOptionalElse(self):
        if self.log:
            print("OptionalElse")
        if self.next() in ("else",):
            var0_else = self.consume("else")
            var1_ = self.consume("{")
            var2_Statements = self.parseStatements()
            var3_ = self.consume("}")
            return Else(('_', var0_else),('_', var1_),('stmts', var2_Statements),('_', var3_),)
        return  # epsilon case

    def parseExpMath(self):
        if self.log:
            print("ExpMath")
        if self.next() in ("\(", "number", "name",):
            var0_ExpMult = self.parseExpMult()
            var1_ExpMathR = self.parseExpMathR()
            return ExpMath(('left', var0_ExpMult),('right', var1_ExpMathR),)
        self.parsefail(("\(", "number", "name",), self.next())

    def parseExpressionR(self):
        if self.log:
            print("ExpressionR")
        if self.next() in ("gt", "geq", "equal", "leq", "lt",):
            var0__anon_Set1 = self.parse_anon_Set1()
            var1_Expression = self.parseExpression()
            return ExpR(('op', var0__anon_Set1),('exp', var1_Expression),)
        return  # epsilon case

    def parseExpMult(self):
        if self.log:
            print("ExpMult")
        if self.next() in ("\(", "number", "name",):
            var0_ExpEnd = self.parseExpEnd()
            var1_ExpMultR = self.parseExpMultR()
            return ExpMult(('left', var0_ExpEnd),('right', var1_ExpMultR),)
        self.parsefail(("\(", "number", "name",), self.next())

    def parseExpMathR(self):
        if self.log:
            print("ExpMathR")
        if self.next() in ("minus", "plus",):
            var0__anon_Set2 = self.parse_anon_Set2()
            var1_ExpMath = self.parseExpMath()
            return ExpMath(('op', var0__anon_Set2),('rest', var1_ExpMath),)
        return  # epsilon case

    def parse_anon_Set1(self):
        if self.log:
            print("_anon_Set1")
        if self.next() in ("lt",):
            return self.consume("lt")
        if self.next() in ("gt",):
            return self.consume("gt")
        if self.next() in ("leq",):
            return self.consume("leq")
        if self.next() in ("geq",):
            return self.consume("geq")
        if self.next() in ("equal",):
            return self.consume("equal")
        self.parsefail(("gt", "geq", "leq", "lt", "equal",), self.next())

    def parseExpEnd(self):
        if self.log:
            print("ExpEnd")
        if self.next() in ("\(",):
            var0_ = self.consume("\(")
            var1_Expression = self.parseExpression()
            var2_ = self.consume("\)")
            return var0_, var1_Expression, var2_
        if self.next() in ("number",):
            var0_number = self.consume("number")
            return var0_number
        if self.next() in ("name",):
            var0_name = self.consume("name")
            return var0_name
        self.parsefail(("\(", "number", "name",), self.next())

    def parseExpMultR(self):
        if self.log:
            print("ExpMultR")
        if self.next() in ("divide", "mult",):
            var0__anon_Set3 = self.parse_anon_Set3()
            var1_ExpMult = self.parseExpMult()
            return ExpMultR(('op', var0__anon_Set3),('rest', var1_ExpMult),)
        return  # epsilon case

    def parse_anon_Set2(self):
        if self.log:
            print("_anon_Set2")
        if self.next() in ("plus",):
            return self.consume("plus")
        if self.next() in ("minus",):
            return self.consume("minus")
        self.parsefail(("minus", "plus",), self.next())

    def parse_anon_Set3(self):
        if self.log:
            print("_anon_Set3")
        if self.next() in ("mult",):
            return self.consume("mult")
        if self.next() in ("divide",):
            return self.consume("divide")
        self.parsefail(("divide", "mult",), self.next())

    def _parseRoot(self):
        return self.parseProgram()


def main():
    log = False
    if len(sys.argv) < 2:
        raise ValueError("Specify input file to parse")
    elif len(sys.argv) > 2:
        if sys.argv[2] == "-v":
            log = True
    with open(sys.argv[1]) as f:
        s = f.read()
    p = Parser(log)
    ast = p.parse(s)
    print(repr(ast))

if __name__ == "__main__":
    main()

