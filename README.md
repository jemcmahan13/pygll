
A python-based recursive-descent-parser parser generator.

I made this because I wanted a parser generator with two characteristics: 1) It takes in an EBNF grammar; 2) It outputs human-readable Python code. Other than that and a few enhancements for convenience, I wanted it to be as simple as possible. I couldn't find anything to my satisfaction, so here we are.


# Usage

`python ll.py ebnf_file > parser.py`

The parser can then be used as follows:

```
from parser import Parser
p = Parser()
ast = p.parse(inputstring)
```

# Grammar format
Grammars are expected in an EBNF file consisting of three directives:
* `%root` specifying which production is the root production;
* `%tokens`, followed by a list of token names and strings;
* `%grammar`, followed by a list of grammar productions.


## Tokens

The `%tokens` directive is followed by a list of tokens (terminals). All tokens that will be referred to by name after parsing must be declared in advance. Anonymous tokens can be declared within productions.

Each token declaration consists of a pair `name` `string`, providing the name which grammar productions will use to refer to the token, and then a regular expression for the lexer to use while scanning. Single quotes (`'`) and double quotes (`"`) are both accepted.

Regular expressions use the syntax of the python `re` module.


## Grammar

The `%grammar` directive is followed by a list of grammar nonterminals. Each nonterminal has a unique name, the definition symbol (`:=`), and then a list of productions separated by `|`. The list of productions is terminated by a semicolon (`;`).

Each production consists of a list of terminals and nonterminals

The epsilon production is indicated with a dollar sign (`$`).

### Accessing Parsed Elements

#### Default

By default, the parser will return nested tuples. Navigating this can get messy, so it's recommended to name the components of your productions.

#### Naming terminals and nonterminals

A list of names can be given for a production, which are applied to parse elements after parsing. This makes the produced AST easier to use, allowing for object-style `name.element` access instead of indexing into tuples repeatedly.

After a production, a pound sign (`#`) indicates a sequence of names to use for the parsed elements. Underscore (`_`) can be used as a "don't care." The first name gives a name to the derivation; following names are applied in order to the terminals and nonterminals in the derivation.

For example,
`E := Term '+' Term Rest  # Plus lhs _ rhs remaining`
will name the production `Plus`, the first term `lhs`, throw away the plus sign, name the second term `rhs`, and name everything under rest `remaining`.

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


# Notes

basegenerator: Files for generating ll.py (the parser-generator).
Uses a primitive implementation to parse an EBNF spec, then generates a parser
from that (ll.py).

parsergenerator: The files to use the parser generator.
ll.py contains the parser that parses ebnf grammar files.
stock.py contains boilerplate code for an emitted parser.
emitter.py contains the code to emit a parser from an AST.

ll.py (extended.py): the parser for EBNF files
emitter.py: generates a parser from an AST


# FAQ

### Will ambiguities in my grammar be detected?
Not at the moment, no. Productions are checked in the order written, so this might result in certain production never being taken and then later parse errors. Be careful when writing your grammar.