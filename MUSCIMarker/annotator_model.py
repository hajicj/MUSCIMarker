"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import codecs
import logging

# import cv2
# import matplotlib.pyplot as plt
import itertools
from kivy.app import App
from kivy.properties import ObjectProperty, DictProperty, NumericProperty, ListProperty
from kivy.uix.widget import Widget

import muscimarker_io
from syntax.dependency_parsers import SimpleDeterministicDependencyParser
from utils import compute_connected_components
from tracker import Tracker

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


class ObjectGraph(Widget):
    """This class describes how the CropObjects from
    a CropObjectAnnotatorModel are attached to each other,
    forming an oriented graph.

    The Graph model never actually interacts with the CropObjects
    that form its nodes. It is only aware of their ``objid``s.
    The interaction with CropObjects is only necessary during rendering.
    """

    # cropobject_model = ObjectProperty()
    # '''Reference to the CropObjcetAnnotatorModel holding CropObject
    # information.'''
    vertices = DictProperty()
    '''List of valid vertex indices.'''

    edges = DictProperty()
    '''Attachments among symbols are dependency relationships, such as
    between a notehead and a stem. We store attachments as oriented
    edges.

    An attachment is represented as a ``(objid_1, objid_2)`` key with
    a value of ``True``.
    '''

    _outlinks = DictProperty()
    '''Automatically computed dict of all CropObjects attached to a given
    CropObject. Internal.'''

    _inlinks = DictProperty()
    '''Automatically computed dict of all CropObjects that the given
    CropObject is attached to. Internal.'''

    # def __init__(self, model, **kwargs):
    #     super(ObjectGraph, self).__init__(**kwargs)
    #     # self.cropobject_model = model
    #     # model.sync_cropobjects_to_graph()

    ##########################################################################
    # Managing the attachments

    def add_vertex(self, v):
        self.vertices[v] = True

    def remove_vertex(self, v):
        if v in self.vertices:
            self.remove_obj_from_graph(v)

    def ensure_add_edge(self, edge, label='Attachment'):
        logging.info('Graph: ensuring edge {0}'.format(edge))
        if edge not in self.edges:
            self.add_edge(edge, label=label)

    def add_edge(self, edge, label='Attachment'):
        '''Edge is an ``(a1, a2)`` pair such that ``a1`` is the head
        and ``a2`` is the child CropObject. Our (attachment) dependency edges
        lead from the root down, at least in the model.'''
        logging.info('Graph: adding edge {0} with label {1}'.format(edge, label))
        a1 = edge[0]
        a2 = edge[1]
        if a1 not in self.vertices:
            raise ValueError('Invalid attachment {0}: member {1} not in cropobjects.'
                             ''.format(edge, a1))
        if a2 not in self.vertices:
            raise ValueError('Invalid attachment {0}: member {1} not in cropobjects.'
                             ''.format(edge, a2))

        self.edges[edge] = label
        self.add_to_edges_index(a1, a2)

    def ensure_add_edges(self, edges, label='Attachment'):
        logging.info('Graph: ensuring edges {0}'.format(edges))
        edges_to_add = [e for e in edges if e not in self.edges]
        self.add_edges(edges_to_add, label=label)

    def add_edges(self, edges, label='Attachment'):
        logging.info('Graph: adding {0} edges with label {1}'
                     ''.format(len(edges), label))

        # First add to edges index
        for a1, a2 in edges:
            if a1 not in self.vertices:
                raise ValueError('Invalid attachment {0}: member {1} not in cropobjects.'
                                 ''.format((a1, a2), a1))
            if a2 not in self.vertices:
                raise ValueError('Invalid attachment {0}: member {1} not in cropobjects.'
                                 ''.format((a1, a2), a2))
            self.add_to_edges_index(a1, a2)

        edge_dict = {e: label for e in edges}
        self.edges.update(edge_dict)

    def add_to_edges_index(self, a1, a2):
        if a1 not in self._outlinks:
            self._outlinks[a1] = set()
        if a2 not in self._inlinks:
            self._inlinks[a2] = set()

        if a2 not in self._outlinks[a1]:
            self._outlinks[a1].add(a2)
        else:
            logging.warn('Trying to re-add outlink from {0} to {1}'
                         ''.format(a1, a2))
        if a1 not in self._inlinks[a2]:
            self._inlinks[a2].add(a1)
        else:
            logging.warn('Trying to re-add inlink from {0} to {1}'
                         ''.format(a1, a2))

    def compute_edges_index(self, attachments):
        '''Adds to the attachment indexes all the given
        attachments ``(a1, a2)``.'''
        for a1, a2 in attachments:
            self.add_to_edges_index((a1, a2))

    def ensure_remove_edge(self, a1, a2):
        """If there was an edge from a1 to a2, remove it."""
        logging.info('Model: ensuring detaching edge from {0} to {1}'
                     ''.format(a1, a2))
        if (a1, a2) in self.edges:
            self.remove_edge(a1, a2)

    def remove_edge(self, a1, a2):
        """Object a1 will no longer point at object a2."""
        self._inlinks[a2].remove(a1)
        self._outlinks[a1].remove(a2)
        del self.edges[a1, a2]

    def remove_obj_from_graph(self, objid):
        """Clears out the given CropObject from the attachments
        graph.

        DO NOT USE THIS if you only want to clear out the object's
        edges. This is used when the object disappears from the
        vertices as well.
        """
        self.remove_obj_edges(objid)
        del self.vertices[objid]

    def remove_obj_edges(self, objid):
        """Clears all edges in which the object participates."""
        if objid in self._inlinks:
            inlinks = self._inlinks[objid]
            for a in inlinks:
                del self.edges[a, objid]

        if objid in self._outlinks:
            outlinks = self._outlinks[objid]
            for a in outlinks:
                del self.edges[objid, a]

        self._remove_obj_from_edges_index(objid)

    def _remove_obj_from_edges_index(self, objid):
        """Remove all of this node's inlinks and outlinks,
        and remove its record from the attachment index.
        DO NOT USE THIS directly, use :meth:`remove_obj_from_attachment`!"""
        if objid in self._outlinks:
            self._clear_obj_outlinks(objid)
            del self._outlinks[objid]
        if objid in self._inlinks:
            self._clear_obj_inlinks(objid)
            del self._inlinks[objid]

    def _clear_obj_outlinks(self, objid):
        """Remove the node's outlinks, and remove it from the inlinks
        of the nodes it outlinks to."""
        if objid in self._outlinks:
            outlinks = self._outlinks[objid]
            for o in outlinks:
                if objid in self._inlinks[o]:
                    self._inlinks[o].remove(objid)
            self._outlinks[objid] = set()

    def _clear_obj_inlinks(self, objid):
        """Remove the node's inlinks, and remove it from the outlinks
        of the nodes from which it has inlinks"""
        if objid in self._inlinks:
            inlinks = self._inlinks[objid]
            for i in inlinks:
                if objid in self._outlinks[i]:
                    self._outlinks[i].remove(objid)
            self._inlinks[objid] = set()

    def clear(self):
        self.vertices = []
        self.clear_edges()

    def clear_edges(self):
        self.edges = {}
        self._inlinks = dict()
        self._outlinks = dict()

##############################################################################


class CropObjectAnnotatorModel(Widget):
    """This model describes the conceptual interface of the annotation
    app: there is an annotator performing some actions, and this model
    has support for these actions. It operates with finished CropObjects
    and MLClasses.

    The annotator is working with three sets of objects:

    * The image that is being annotated,
    * the CropObjects that have already been marked,
    * the set of object types that can be marked.

    The object graph is synced to the CropObject dict in the Model
    on export.

    """
    image = ObjectProperty()

    # Connected component precomputing
    _cc = NumericProperty(-1)
    _labels = ObjectProperty(None, allownone=True)
    _bboxes = ObjectProperty(None, allownone=True)

    cropobjects = DictProperty()
    mlclasses = DictProperty()
    mlclasses_by_name = DictProperty()

    graph = ObjectProperty()

    parser = ObjectProperty(None, allownone=True)
    grammar = ObjectProperty(None, allownone=True)

    def __init__(self, image=None, cropobjects=None, mlclasses=None, **kwargs):
        super(CropObjectAnnotatorModel, self).__init__(**kwargs)

        self.image = image
        self.cropobjects = dict()
        if cropobjects:
            self.import_cropobjects(cropobjects)
        self.mlclasses = dict()
        self.mlclasses_by_name = dict()
        if mlclasses:
            self.import_classes_definition(mlclasses)

        self.graph = ObjectGraph()
        self.sync_cropobjects_to_graph()

    def load_image(self, image, compute_cc=False):
        self._invalidate_cc_cache()
        self.image = image
        if compute_cc:
            self._compute_cc_cache()

    @Tracker(track_names=['cropobject'],
             transformations={'cropobject': [lambda c: ('objid', c.objid),
                                             lambda c: ('clsid', c.clsid),
                                             lambda c: ('mlclass_name', c.clsname),
                                             lambda c: ('tool_used', App.get_running_app().currently_selected_tool_name)]
                              },
             fn_name='model.add_cropobject',
             tracker_name='model')
    def add_cropobject(self, cropobject, perform_checks=True):
        if perform_checks:
            if not self._is_cropobject_valid(cropobject):
                logging.info('Model: Adding cropobject {0}: invalid!'
                             ''.format(cropobject.objid))
                return

        # Sync added cropobject to graph
        self.graph.add_vertex(cropobject.objid)
        # collect edges & add them at once
        edges = []
        for i in cropobject.inlinks:
            edges.append((i, cropobject.objid))
        for o in cropobject.outlinks:
            edges.append((cropobject.objid, o))
        self.graph.add_edges(edges)

        self.cropobjects[cropobject.objid] = cropobject

    def _is_cropobject_valid(self, cropobject):
        t, l, b, r = cropobject.bounding_box
        if (b - t) * (r - l) < 10:
            logging.warn('Model: Trying to add a CropObject that is very small'
                         ' ({0} x {1})'.format(cropobject.height, cropobject.width))
            return False
        return True

    @Tracker(track_names=['key'],
             transformations={'key': [lambda key: ('objid', key)]},
             fn_name='model.remove_cropobject',
             tracker_name='model')
    def remove_cropobject(self, key):
        # Could graph sync be solved by binding?
        self.graph.remove_obj_from_graph(key)
        del self.cropobjects[key]

    @Tracker(track_names=['cropobjects'],
             transformations={'cropobjects': [lambda c: ('n_cropobjects', len(c)),
                                              lambda cs: ('objids', [c.objid for c in cs])]},
             fn_name='model.import_cropobjects',
             tracker_name='model')
    def import_cropobjects(self, cropobjects, clear=True):
        logging.info('Model: Importing {0} cropobjects.'.format(len(cropobjects)))
        if clear:
            self.clear_cropobjects()
        # Batch processing is more efficient, since rendering the CropObjectList
        # is tied to any change of self.cropobjects
        self.cropobjects = {c.objid: c for c in cropobjects}
        self.sync_cropobjects_to_graph()

    @Tracker(track_names=[],
             fn_name='model.export_cropobjects_string',
             tracker_name='model')
    def export_cropobjects_string(self, **kwargs):
        self.sync_graph_to_cropobjects()
        return muscimarker_io.export_cropobject_list(self.cropobjects.values(), **kwargs)

    @Tracker(track_names=['output'],
             fn_name='model.export_cropobjects',
             tracker_name='model')
    def export_cropobjects(self, output, **kwargs):
        logging.info('Model: Exporting CropObjects to {0}'.format(output))
        with codecs.open(output, 'w', 'utf-8') as hdl:
            hdl.write(self.export_cropobjects_string(**kwargs))
            hdl.write('\n')

    @Tracker(track_names=[],
             fn_name='model.clear_cropobjects',
             tracker_name='model')
    def clear_cropobjects(self):
        logging.info('Model: Clearing all {0} cropobjects.'.format(len(self.cropobjects)))
        self.cropobjects = {}
        self.sync_cropobjects_to_graph()

    def import_classes_definition(self, mlclasses):
        """Overwrites previous mlclasses definition -- there can only be
        one active at the same time.

        Note that this may invalidate all of the CropObjects in memory.

        Note that this also invalidates the current grammar.
        """
        self.mlclasses = {m.clsid: m for m in mlclasses}
        self.mlclasses_by_name = {m.name: m for m in mlclasses}

    def get_next_cropobject_id(self):
        if len(self.cropobjects) == 0:
            return 0
        return max(self.cropobjects.keys()) + 1

    ##########################################################################
    # Synchronizing with the graph.
    def sync_graph_to_cropobjects(self, cropobjects=None):
        """Ensures that the attachments are accurately reflected
        among the CropObjects. The attachments are build separately
        in the app, so they need to be written to the CropObjects
        explicitly.

        .. warning::

            Clears all outlinks and inlinks from the CropObjects and replaces
            them with the graph's structure!

        :param cropobjects: A list of CropObjects which should be synced.
            If left to ``None``, will sync everything.
        """
        logging.info('Model: Syncing {0} attachments to CropObjects.'
                     ''.format(len(self.graph.edges)))

        if cropobjects is None:
            cropobjects = self.cropobjects.values()

        for c in cropobjects:
            if c.objid in self.graph._inlinks:
                c.inlinks = list(self.graph._inlinks[c.objid])
            else:
                c.inlinks = []

            if c.objid in self.graph._outlinks:
                c.outlinks = list(self.graph._outlinks[c.objid])
            else:
                c.outlinks = []

    def sync_cropobjects_to_graph(self, cropobjects=None):
        """Ensures that the attachment structure in CropObjects
        is accurately reflected in the attachments data structure
        of the model. (Typically, you want to call this on importing
        a new set of CropObjects, to make sure their inlinks and outlinks
        are correctly represented in the attachment structures.

        .. warning::

            Clears the current graph and replaces it with the edges inferred
            from CropObjects!

        :param cropobjects: A list of CropObjects which should be synced.
            If left to ``None``, will sync everything.
        """
        if cropobjects is None:
            cropobjects = self.cropobjects.values()
            self.graph.clear()
        else:
            for c in cropobjects:
                self.graph.remove_obj_from_graph(c.objid)

        edges = []
        for c in cropobjects:
            for o in c.outlinks:
                edges.append((c.objid, o))
            self.graph.add_vertex(c.objid)

        # Add all edges at once.
        self.graph.add_edges(edges)
        #for e in edges:
        #    self.graph.add_edge(e)

    def ensure_consistent(self):
        """Make sure that the model is in a consistent state.
        (Fires all lazy synchronization routines between model components.)"""
        self.sync_graph_to_cropobjects()

    def ensure_remove_edge(self, from_objid, to_objid):
        """Make sure that the given edge is not in the model.
        If it was there, it gets removed; otherwise, no action is taken.
        As opposed to this operation on the graph, on the model, the
        CropObjects in question have their inlink/outlink arrays
        updated as well.
        """
        self.graph.ensure_remove_edge(from_objid, to_objid)
        self.sync_graph_to_cropobjects(cropobjects=[self.cropobjects[from_objid],
                                                    self.cropobjects[to_objid]])

    def ensure_remove_edges(self, edges):
        _affected_cropobjects = []
        for from_objid, to_objid in edges:
            self.graph.ensure_remove_edge(from_objid, to_objid)
            _affected_cropobjects.append(self.cropobjects[from_objid])
            _affected_cropobjects.append(self.cropobjects[to_objid])
        self.sync_graph_to_cropobjects(cropobjects=_affected_cropobjects)

    def ensure_add_edge(self, edge):
        self.graph.ensure_add_edge(edge)
        self.sync_graph_to_cropobjects(cropobjects=[self.cropobjects[edge[0]],
                                                    self.cropobjects[edge[1]]])

    def ensure_add_edges(self, edges, label='Attachment'):
        self.graph.ensure_add_edges(edges=edges, label=label)
        _affected_objids = set(itertools.chain(*edges))
        _affected_cropobjects = [self.cropobjects[i] for i in _affected_objids]
        self.sync_graph_to_cropobjects(cropobjects=_affected_cropobjects)

    ##########################################################################
    # Integrity
    def validate_cropobjects(self):
        """Check that all current CropObject correspond to a class."""
        if len(self.mlclasses) == 0:
            raise ValueError('Cannot validate cropobjects without mlclasses.')
        if self.image is None:
            raise ValueError('Cannot validate cropobjects without image')
        shape = self.image.shape

        invalid_clsid_objs = []
        oversized_objs = []
        for c in self.cropobjects.values():
            clsid = c.clsid
            if clsid not in self.mlclasses:
                invalid_clsid_objs.append(c)
            if c.top < 0 or c.left < 0:
                oversized_objs.append(c)
            if c.bottom > shape[0] or c.right > shape[1]:
                oversized_objs.append(c)

        if len(invalid_clsid_objs) > 0:
            return False
        if len(oversized_objs) > 0:
            return False
        return True

    def find_grammar_errors(self):
        vertices = {v: self.cropobjects[v].clsname for v in self.graph.vertices}
        edges = self.graph.edges.keys()
        v, i, o, r_v, r_i, r_o = self.grammar.find_invalid_in_graph(vertices, edges,
                                                                    provide_reasons=True)
        return v, i, o, r_v, r_i, r_o

    def find_very_small_objects(self, bbox_threshold=10, mask_threshold=10):
        """Finds CropObjects that are very small.

        "Very small" means that their bounding box area is
        smaller than the given threshold or they consist of less
        than ``mask_threshold`` pixels."""
        very_small_cropobjects = []

        for c in self.cropobjects.values():
            total_masked_area = c.mask.sum()
            total_bbox_area = c.width * c.height
            if total_bbox_area < bbox_threshold:
                very_small_cropobjects.append(c)
            elif total_masked_area < mask_threshold:
                very_small_cropobjects.append(c)

        return list(set([c.objid for c in very_small_cropobjects]))

    def find_wrong_vertices(self, provide_reasons=False):
        v, i, o, r_v, r_i, r_o = self.find_grammar_errors()

        v_small = self.find_very_small_objects()
        # Merge with small objects.
        for objid in v_small:
            if objid not in v:
                v.append(objid)
                r_v[objid] = 'Object {0} is suspiciously small.'.format(objid)

        if provide_reasons:
            return v, r_v
        return v

    ##########################################################################
    # Keeping the model in a consistent state
    def on_grammar(self, instance, g):
        if g is None:
            return

        if self.parser is None:
            self.parser = SimpleDeterministicDependencyParser(grammar=g)
        else:
            self.parser.set_grammar(g)

    def on_mlclasses(self, instance, mlclasses):
        # Invalidate grammar and parser
        logging.warn('Model: MLClasses changed, invalidating grammar & parser!')
        self.parser = None
        self.grammar = None
        logging.warn('Model: MLClasses changed, invalidating objgraph!')
        self.graph.clear()

    ##########################################################################
    # Connected components: a useful thing to keep track of
    def _compute_cc_cache(self):
        logging.info('AnnotModel: Computing connected components...')
        cc, labels, bboxes = compute_connected_components(self.image)
        logging.info('AnnotModel: Got cc: {0}, labels: {1}, bboxes: {2}'
                     ''.format(cc, labels.shape, len(bboxes)))
        self._cc, self._labels, self._bboxes = cc, labels, bboxes
        logging.info('AnnotModel: ...done, there are {0} labels.'.format(cc))

    def _invalidate_cc_cache(self):
        self._cc = -1
        self._labels = None
        self._bboxes = None

    def _ensure_cc_cache(self):
        if self._cc_cache_is_empty:
            self._compute_cc_cache()

    @property
    def _cc_cache_is_empty(self):
        return self._cc < 0

    @property
    def cc(self):
        self._ensure_cc_cache()
        return self._cc

    @property
    def labels(self):
        self._ensure_cc_cache()
        return self._labels

    @property
    def bboxes(self):
        self._ensure_cc_cache()
        return self._bboxes
        # def plot_annotations(self):
        #     """Plot the current animation using Matplotlib."""
        #     rgb_img = cv2.cvtColor(self.image, cv2.COLOR_GRAY2RGB)
        #     annot_img = muscimarker_io.render_annotations(rgb_img,
        #                                                   self.cropobjects.values(),
        #                                                   self.mlclasses.values())
        #
        #     logging.info('Plotting annotation, image shape: {0}'.format(annot_img.shape))
        #     plt.imshow(annot_img)
        #     plt.show()
    very_small_cropobjects = []


