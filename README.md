
A python-based RDP parser generator.

basegenerator: Files for generating ll.py (the parser-generator).
Uses a primitive implementation to parse an EBNF spec, then generates a parser
from that (ll.py).

parsergenerator: The files to use the parser generator.
ll.py contains the parser that parser ebnf grammar files.
stock.py contains boilerplate code for an emitted parser.
emitter.py contains the code to emit a parser from an AST.


# Grammar format
Grammars are expected in an EBNF file consisting of three directives:
* `%root` specifying which production is the root production;
* `%tokens`, followed by a list of token names and strings;
* `%grammar`, followed by a list of grammar productions.

Comments are single-line, beginning with `#`.


## Tokens

The `%tokens` directive is followed by a list of tokens (terminals). All tokens that will be referred to by name after parsing must be declared in advance. Anonymous tokens can be declared within productions.

Each token declaration consists of a pair `name` `string`, providing the name which grammar productions will use to refer to the token, and then a regular expression for the lexer to use while scanning. Single quotes (`'`) and double quotes (`"`) are both accepted.

Regular expressions use the syntax of the python `re` module.


## Grammar

The `%grammar` directive is followed by a list of grammar nonterminals. Each nonterminal has a unique name, the definition symbol (`:=`), and then a list of productions separated by `|`. The list of productions is terminated by a semicolon (`;`).

Each production consists of a list of terminals and nonterminals

The epsilon production is indicated with a dollar sign (`$`).

### Special operators

The following special characters are used in productions for the indicated functionality.

#### Optional

Angle brackets (`<` and `>`) indicate that the enclosed portion of the production is optional. It can be parsed 0 or 1 times.

#### Set

Curly braces (`{` and `}`) indicate that exactly one of the enclosed list should be parsed. Entries are separated by spaces, so only terminals and nonterminals (rather than a group of either) can be used.

#### Repetition

Square brackets (`[` and `]`) indicate that the enclosed portion of the production should be parsed 0 or more times. Note that this is only for *zero or more*, not one or more. `[name]` will parse 0 or more names, while `name [name]` will parse 1 or more names.


# Example Grammars

## Simple Math

```
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
```

## Simple Math with operators

```
%root E

%tokens
plus "\+"
minus "\-"
mult "\*"
divide "\/"
lparen "\("
rparen "\)"
num "[0-9]+"
name "\w+"

%grammar
E := T [ { plus minus } E ]   # Exp op rest;
T := F [ { mult divide } F ]  # Term op rest;
F := lparen E rparen          # Paren _ exp _
   | < minus > num                      # Num sign val;
```