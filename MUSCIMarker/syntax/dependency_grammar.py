"""This module implements Grammars.

A Grammar is a set of rules about how objects form relationships.


"""
from __future__ import print_function, unicode_literals

import codecs
import logging
import pprint
import re

import itertools

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


class DependencyGrammarParseError(Exception):
    pass


class DependencyGrammar(object):
    """The DependencyGrammar class implements rules about valid graphs above
    objects from a set of recognized classes.

    The Grammar complements a Parser. It defines rules, and the Parser
    implements algorithms to apply these rules to some input.

    A grammar has an **Alphabet** and **Rules**. The alphabet is a list
    of symbols that the grammar recognizes. Rules are constraints on
    the structures that can be induced among these symbols.

    There are two kinds of grammars according to what kinds of rules
    they use: **dependency** rules, and **constituency** rules. Dependency
    rules specify which symbols are governing, and which symbols are governed::

      notehead_full | stem

    There can be multiple left-hand side and right-hand side symbols,
    as a shortcut for a list of rules::

        notehead_full | stem beam
        notehead_full notehead_empty | ledger_line duration-dot tie grace_note

    The asterisk works as a wildcard. Currently, only one wildcard per symbol
    is allowed::

      time_signature | numeral_*

    Lines starting with a ``#`` are regarded as comments and ignored.
    Empty lines are also ignored.


    Constituency grammars consist of *rewriting rules*, such as::

      Note -> notehead stem | notehead stem duration-dot

    Constituency grammars also distinguish between *terminal* symbols, which
    can only occur on the right-hand side of the rules, and *non-terminal*
    symbols, which can also occur on the left-hand side. They are implemented
    in the class ``ConstituencyGrammar``.

    Interface
    ---------

    The basic role of the dependency grammar is to provide the list of rules:

    >>> g = DependencyGrammar(grammar_filename=f, mlclasses=mlclass_dict)
    >>> g.rules

    Given a pair of alphabet symbols, a dependency grammar can also determine
    whether ``s1`` can be the head of ``s2``:

    >>> g.is_head(s1, s2)
    False

    Grammar I/O
    -----------

    The alphabet is stored by means of the already-familiar MLClassList.

    The rules are stored in *rule files*. For the grammars included
    in MUSCIMarker, rule files are stored in the ``data/grammars/``
    directory.


    """
    WILDCARD = '*'

    def __init__(self, grammar_filename, mlclasses):
        """Initialize the Grammar: fill in alphabet and parse rules."""
        self.alphabet = {m.name: m for m in mlclasses.values()}
        logging.info('DependencyGrammar: got alphabet:\n{0}'
                     ''.format(pprint.pformat(self.alphabet)))
        self.rules = []

        rules = self.parse_dependency_grammar_rules(grammar_filename)
        if self._validate_rules(rules):
            self.rules = rules
            logging.info('DependencyGrammar: Imported {0} rules'
                         ''.format(len(self.rules)))
        else:
            raise ValueError('Not able to parse dependency grammar file {0}.'
                             ''.format(grammar_filename))

    def validate_edge(self, head_name, child_name):
        return (head_name, child_name) in self.rules

    def parse_dependency_grammar_rules(self, filename):
        """Returns the Rules stored in the given rule file."""
        rules = []
        _invalid_lines = []
        with codecs.open(filename, 'r', 'utf-8') as hdl:
            for line_no, line in enumerate(hdl):
                l_rules = self.parse_dependency_grammar_line(line)

                if not self._validate_rules(l_rules):
                    _invalid_lines.append((line_no, line))

                rules.extend(l_rules)
        if len(_invalid_lines) > 0:
            logging.warning('DependencyGrammar.parse_rules(): Invalid lines'
                            ' {0}'.format(pprint.pformat(_invalid_lines)))
        return rules

    def parse_dependency_grammar_line(self, line):
        """Parse one dependency grammar line. See DependencyGrammar
        I/O documentation for the format."""
        if line.strip().startswith('#'):
            return []
        if len(line.strip()) == 0:
            return []

        if '|' not in line:
            return []

        # logging.info('DependencyGrammar: parsing rule line:\n\t\t{0}'
        #              ''.format(line.rstrip('\n')))
        lhs, rhs = line.split('|', 1)
        lhs_tokens = lhs.strip().split()
        rhs_tokens = rhs.strip().split()

        # logging.info('DependencyGrammar: tokens lhs={0}, rhs={1}'
        #              ''.format(lhs_tokens, rhs_tokens))

        lhs_symbols = []
        for l in lhs_tokens:
            lhs_symbols.extend(self._matching_names(l))

        rhs_symbols = []
        for r in rhs_tokens:
            rhs_symbols.extend(self._matching_names(r))

        # logging.info('DependencyGrammar: symbols lhs={0}, rhs={1}'
        #              ''.format(lhs_symbols, rhs_symbols))

        rules = []
        for l in lhs_symbols:
            for r in rhs_symbols:
                rules.append((l, r))

        # logging.info('DependencyGramamr: got rules:\n{0}'
        #              ''.format(pprint.pformat(rules)))
        return rules

    def _matching_names(self, token):
        """Returns the list of alphabet symbols that match the given
        name (regex, currently can process one '*' wildcard).

        :type token: str
        :param token: The symbol name (pattern) to expand.

        :rtype: list
        :returns: A list of matching names. Empty list if no name matches.
        """
        if not self._has_wildcard(token):
            return [token]

        wildcard_idx = token.index(self.WILDCARD)
        prefix = token[:wildcard_idx]
        if wildcard_idx < len(token) - 1:
            suffix = token[wildcard_idx+1:]
        else:
            suffix = ''

        # logging.info('DependencyGrammar._matching_names: token {0}, pref={1}, suff={2}'
        #              ''.format(token, prefix, suffix))

        matching_names = self.alphabet.keys()
        if len(prefix) > 0:
            matching_names = [n for n in matching_names if n.startswith(prefix)]
        if len(suffix) > 0:
            matching_names = [n for n in matching_names if n.endswith(suffix)]

        return matching_names

    def _validate_rules(self, rules):
        """Check that all the rules are valid under the current alphabet."""
        missing_heads = set()
        missing_children = set()
        for h, ch in rules:
            if h not in self.alphabet:
                missing_heads.add(h)
            if ch not in self.alphabet:
                missing_children.add(ch)

        if (len(missing_heads) + len(missing_children)) > 0:
            logging.warning('DependencyGrammar.validate_rules: missing heads '
                            '{0}, children {1}'
                            ''.format(missing_heads, missing_children))
            return False
        else:
            return True

    def _has_wildcard(self, name):
        return self.WILDCARD in name

    def is_head(self, head, child):
        return (head, child) in self.rules


##############################################################################

