import unittest
import os

from muscima.grammar import DependencyGrammar
from muscimarker_io import parse_mlclass_list


class DependencyGrammarTest(unittest.TestCase):
    def test_grammar_parsing(self):
        fpath = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'data/grammars/mff-muscima-mlclasses-annot.deprules')
        mlpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data/mff-muscima-mlclasses-annot.xml')
        mlclass_dict = {m.clsid: m for m in parse_mlclass_list(mlpath)}
        g = DependencyGrammar(grammar_filename=fpath, alphabet=mlclass_dict)
        length = len(g.rules)

        self.assertEqual(444, length)


if __name__ == '__main__':
    unittest.main()
