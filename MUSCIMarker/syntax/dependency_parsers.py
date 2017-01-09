"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import logging

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


class SimpleDeterministicDependencyParser(object):
    """This dependency parser just adds all possible edges,
    as defined by the given grammar."""
    def __init__(self, grammar):
        """Initialize the parser.

        :type grammar: DependencyGrammar
        :param grammar: A DependencyGrammar.
        """
        logging.info('SimpleDeterministicDependencyParser: Initializing parser.')
        self.grammar = grammar

    def parse(self, symbol_names):
        """Adds all edges allowed by the grammar, given the list
        of symbols. The edges are (i, j) tuples of indices into the
        supplied list of symbol names.
        """
        return self.get_all_possible_edges(symbol_names)

    def get_all_possible_edges(self, symbol_names):
        """Collects all symbol edges that are permissible, using the grammar.

        :rtype: list
        :returns: A list of ``(i, j)`` tuples, where ``i`` and ``j``
            are indices into the list of symbol names (so that whoever
            provided the names can track down the specific objects
            from which the symbol names were collected - there is no
            requirement that the names must be unique).
        """
        edges = []

        for i, s1, in enumerate(symbol_names):
            for j, s2 in enumerate(symbol_names):
                if self.grammar.is_head(s1, s2):
                    # No loops!
                    if i != j:
                        edges.append((i, j))

        return edges

    def set_grammar(self, grammar):
        # More complex parsers might need to reset some internal states
        self.grammar = grammar