
A python-based RDP parser generator.








Grammar and Parser classes enitrely separate. Grammar manages the grammar rules/productions, computes first/follow sets, etc.; Parser handles the run-time parsing of text. With some sort of save feature, may not need grammar class to exist after init.

Parser invokes a nonterminal, which calls a function in the Grammar class; passes back the appropriate list of productions. Parser can call first() on each production to decide which to follow. Invokin a terminal with a token checks for a match (wrap in consume(tok, term) function so parserrrors can be thrown from the right place).