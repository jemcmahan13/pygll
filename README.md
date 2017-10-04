
A python-based RDP parser generator.

basegenerator: Files for generating ll.py (the parser-generator).
Uses a primitive implementation to parse an EBNF spec, then generates a parser
from that (ll.py).

parsergenerator: The files to use the parser generator.
ll.py contains the parser that parser ebnf grammar files.
stock.py contains boilerplate code for an emitted parser.
emitter.py contains the code to emit a parser from an AST.
