"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import logging

from muscima.cropobject import cropobject_distance
from sklearn.feature_extraction import DictVectorizer

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

    def parse(self, cropobjects):
        """Adds all edges allowed by the grammar, given the list
        of symbols. The edges are (i, j) tuples of indices into the
        supplied list of symbol names.
        """
        symbol_names = [c.clsname for c in cropobjects]
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


class PairwiseClassificationParser(object):
    """This parser applies a simple classifier that takes the bounding
    boxes of two CropObjects and their classes and returns whether there
    is an edge or not."""
    def __init__(self, clf, cropobject_feature_extractor):
        self.clf = clf
        self.extractor = cropobject_feature_extractor

        raise NotImplementedError()


    def is_edge(self, c_from, c_to):
        features = self.extractor(c_from, c_to)
        result = self.clf.predict(features)
        return result


##############################################################################
# Feature extraction

class PairwiseClfFeatureExtractor():
    def __init__(self, vectorizer=None):
        """Initialize the feature extractor.

        :param vectorizer: A DictVectorizer() from scikit-learn.
            Used to convert feature dicts to the vectors that
            the edge classifier of the parser will expect.
            If None, will create a new DictVectorizer. (This is useful
            for training; you can then pickle the entire extractor
            and make sure the feature extraction works for the classifier
            at runtime.)
        """
        if vectorizer is None:
            vectorizer = DictVectorizer()
        self.vectorizer = vectorizer

    def __call__(self, *args, **kwargs):
        """The call is per item (in this case, CropObject pair)."""
        fd = self.get_features_relative_bbox_and_clsname(*args, **kwargs)
        item_features = self.vectorizer.transform(fd).toarray()
        return item_features

    def get_features_relative_bbox_and_clsname(self, c_from, c_to):
        """Extract a feature vector from the given pair of CropObjects.
        Does *NOT* convert the class names to integers.

        Features: bbox(c_to) - bbox(c_from), clsname(c_from), clsname(c_to)
        Target: 1 if there is a link from u to v

        Returns a dict that works as input to ``self.vectorizer``.
        """
        target = 0
        if c_from.doc == c_to.doc:
            if c_to.objid in c_from.outlinks:
                target = 1
        features = (c_to.top - c_from.top,
                    c_to.left - c_from.left,
                    c_to.bottom - c_from.bottom,
                    c_to.right - c_from.right,
                    c_from.clsname,
                    c_to.clsname,
                    target)
        dt, dl, db, dr, cu, cv, tgt = features
        feature_dict = {'dt': dt,
                        'dl': dl,
                        'db': db,
                        'dr': dr,
                        'cls_from': cu,
                        'cls_to': cv,
                        'target': tgt}
        return feature_dict

    def get_features_distance_relative_bbox_and_clsname(self, c_from, c_to):
        """Extract a feature vector from the given pair of CropObjects.
        Does *NOT* convert the class names to integers.

        Features: bbox(c_to) - bbox(c_from), clsname(c_from), clsname(c_to)
        Target: 1 if there is a link from u to v

        Returns a tuple.
        """
        target = 0
        if c_from.doc == c_to.doc:
            if c_to.objid in c_from.outlinks:
                target = 1
        distance = cropobject_distance(c_from, c_to)
        features = (distance,
                    c_to.top - c_from.top,
                    c_to.left - c_from.left,
                    c_to.bottom - c_from.bottom,
                    c_to.right - c_from.right,
                    c_from.clsname,
                    c_to.clsname,
                    target)
        return features

