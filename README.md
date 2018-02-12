
A python-based recursive descent parser generator for LL(1) grammars.

I made this because I wanted a parser generator with two characteristics: 1) It takes in an EBNF grammar; 2) It outputs human-readable Python code that one can use. Other than that and a few enhancements for convenience, I wanted it to be as simple as possible. I couldn't find anything to my satisfaction, so here we are.


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

The `%tokens` directive is followed by a list of tokens (terminals). Regex match will be tried in the order of declaration, so be sure to put keywords higher up in the list. Anonymous tokens can be declared within productions.

Each token declaration consists of a pair `name` `string`, providing the name which grammar productions will use to refer to the token, and then a regular expression for the lexer to use while scanning. Single quotes (`'`) and double quotes (`"`) are both accepted for the regular expression.

Regular expressions use the syntax of the python `re` module.


## Grammar

The `%grammar` directive is followed by a list of grammar nonterminals. Each nonterminal has a unique name, the definition symbol (`:=`), and then a list of productions separated by bars (`|`). The list of productions is terminated by a semicolon (`;`).

Each production consists of a list of terminals and nonterminals. Both are referred to by declared name. Terminals can also be defined on-the-fly with a regex in single or doulbe quotes. (See the examples below.)

The epsilon production is indicated with a dollar sign (`$`).

### Accessing Parsed Elements

#### Default

By default, the parser will return nested tuples. Navigating this can get messy, so it's recommended to name the components of your productions.

#### Naming terminals and nonterminals

A list of names can be given for a production, which are applied to parse elements after parsing. This makes the produced AST easier to use, allowing for object-style `name.element` access instead of indexing into tuples repeatedly.

After a production, a pound sign (`#`) indicates a sequence of names to use for the parsed elements. Underscore (`_`) can be used as a "don't care," suppressing the parsed element. The first name gives a name to the derivation; following names are applied in order to the terminals and nonterminals in the derivation.

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

Square brackets (`[` and `]`) indicate that the enclosed portion of the production should be parsed 0 or more times. Note that this is only for *zero or more*, not one or more. `[name]` will parse 0 or more names, while `name [name]` will parse 1 or more names. Only a single terminal or nonterminal can be enclosed.


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

## Simple Language
```
%root Program

%tokens
if	'if'
then	'then'
else	'else'
print	'print'
lt	'<'
gt	'>'
leq	'<='
geq	'>='
equal	'=='
plus	'\+'
minus	'\-'
mult	'\*'
divide	'\/'
number	'[0-9]+'
name	'\w+'

%grammar
Program := Statements
	     ;

Statements := Statement [Statement]
	        ;

Statement := name '=' Expression ';'			                    # Assignment name _ expr _
    	   | if Expression then '{' Statements '}' OptionalElse     # Condition _ cond _ _ truebranch _ elsebranch
	       | print Expression ';'   		  		                # Print _ expr _
	       ;

OptionalElse := else '{' Statements '}'			# Else _ _ stmts _
	          | $
	          ;

Expression := ExpMath ExpressionR               # Exp left right
	        ;

ExpressionR := { lt gt leq geq equal } Expression	# ExpR op exp
	         | $
	         ;

ExpMath := ExpMult ExpMathR				# ExpMath left right
	     ;

ExpMathR := { plus minus } ExpMath			# ExpMath op rest
	      | $
	      ;

ExpMult := ExpEnd ExpMultR				# ExpMult left right
	     ;

ExpMultR := { mult divide } ExpMult			# ExpMultR op rest
	      | $
	      ;

ExpEnd := '\(' Expression '\)'          # Paren _ exp _
	    | number                        # Num num
	    | name                          # Name name
	    ;
```


# Notes

`basic/` contains an older version that does not support the Set, Repeat, and Optional operators.


# FAQ

### Will ambiguities in my grammar be detected?
Not at the moment, no. Productions are checked in the order written, so this might result in certain production never being taken and then later parse errors. Be careful when writing your grammar.
