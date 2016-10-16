"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import codecs
import logging

# import cv2
# import matplotlib.pyplot as plt

from kivy.properties import ObjectProperty, DictProperty, NumericProperty, ListProperty
from kivy.uix.widget import Widget

import muscimarker_io
from utils import compute_connected_components
from tracker import Tracker

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


class CropObjectAnnotatorModel(Widget):
    """This model describes the conceptual interface of the annotation
    app: there is an annotator performing some actions, and this model
    has support for these actions. It operates with finished CropObjects
    and MLClasses.

    The annotator is working with three sets of objects:

    * The image that is being annotated,
    * the CropObjects that have already been marked,
    * the set of object types that can be marked.

    """
    image = ObjectProperty()

    # Connected component precomputing
    _cc = NumericProperty(-1)
    _labels = ObjectProperty(None, allownone=True)
    _bboxes = ObjectProperty(None, allownone=True)

    cropobjects = DictProperty()
    mlclasses = DictProperty()
    mlclasses_by_name = DictProperty()

    attachments = DictProperty()
    '''Attachments among symbols are dependency relationships, such as
    between a notehead and a stem. We store attachments as oriented
    edges.

    An attachment is represented as a ``(objid_1, objid_2)`` key with
    a value of ``True``.
    '''

    attachment_outlinks = DictProperty()
    '''Automatically computed dict of all CropObjects attached to a given
    CropObject.'''

    attachment_inlinks = DictProperty()
    '''Automatically computed dict of all CropObjects that the given
    CropObject is attached to.'''

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

    def load_image(self, image, compute_cc=False):
        self._invalidate_cc_cache()
        self.image = image
        if compute_cc:
            self._compute_cc_cache()

    @Tracker(track_names=['cropobject'],
             transformations={'cropobject': [lambda c: ('objid', c.objid),
                                             lambda c: ('clsid', c.clsid)]},
             fn_name='model.add_cropobject',
             tracker_name='model')
    def add_cropobject(self, cropobject):
        self.cropobjects[cropobject.objid] = cropobject

    @Tracker(track_names=['key'],
             transformations={'key': [lambda key: ('objid', key)]},
             fn_name='model.remove_cropobject',
             tracker_name='model')
    def remove_cropobject(self, key):
        self.remove_obj_from_attachment(key)
        del self.cropobjects[key]

    @Tracker(track_names=['cropobjects'],
             transformations={'cropobjects': [lambda c: ('n_cropobjects', len(c)),
                                              lambda cs: ('objids', [c.objid for c in cs])]},
             fn_name='model.import_cropobjects',
             tracker_name='model')
    def import_cropobjects(self, cropobjects):
        logging.info('Model: Importing {0} cropobjects.'.format(len(cropobjects)))
        # Batch processing is more efficient, since rendering the CropObjectList
        # is tied to any change of self.cropobjects
        self.clear_attachments()
        self.cropobjects = {c.objid: c for c in cropobjects}
        self.sync_cropobjects_to_attachments()

    @Tracker(track_names=[],
             fn_name='model.export_cropobjects_string',
             tracker_name='model')
    def export_cropobjects_string(self, **kwargs):
        self.sync_attachments_to_cropobjects()
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
        self.clear_attachments()

    def import_classes_definition(self, mlclasses):
        """Overwrites previous mlclasses definition -- there can only be
        one active at the same time."""
        self.mlclasses = {m.clsid: m for m in mlclasses}
        self.mlclasses_by_name = {m.name: m for m in mlclasses}

    def get_next_cropobject_id(self):
        if len(self.cropobjects) == 0:
            return 0
        return max(self.cropobjects.keys()) + 1

    ##########################################################################
    # Managing the attachment tree
    # TODO: Refactor into a separate CropObjectGraph?
    def ensure_add_attachment(self, attachment):
        logging.info('Model: ensuring attachment {0}'.format(attachment))
        if attachment not in self.attachments:
            self.add_attachment(attachment)

    def add_attachment(self, attachment):
        '''Attachment is an ``(a1, a2)`` pair such that ``a1`` is the head
        and ``a2`` is the child CropObject. Our (attachment) dependency edges
        lead from the root down, at least in the model.'''
        logging.info('Model: adding attachment {0}'.format(attachment))
        a1 = attachment[0]
        a2 = attachment[1]
        if a1 not in self.cropobjects:
            raise ValueError('Invalid attachment {0}: member {1} not in cropobjects.'
                             ''.format(attachment, a1))
        if a2 not in self.cropobjects:
            raise ValueError('Invalid attachment {0}: member {1} not in cropobjects.'
                             ''.format(attachment, a2))

        self.attachments[attachment] = True
        self.add_to_attachments_index(a1, a2)

    def add_to_attachments_index(self, a1, a2):
        if a1 not in self.attachment_outlinks:
            self.attachment_outlinks[a1] = set()
        if a2 not in self.attachment_inlinks:
            self.attachment_inlinks[a2] = set()

        if a2 not in self.attachment_outlinks[a1]:
            self.attachment_outlinks[a1].add(a2)
        else:
            logging.warn('Trying to re-add outlink from {0} to {1}'
                         ''.format(a1, a2))
        if a1 not in self.attachment_inlinks[a2]:
            self.attachment_inlinks[a2].add(a1)
        else:
            logging.warn('Trying to re-add inlink from {0} to {1}'
                         ''.format(a1, a2))

    def compute_attachment_index(self, attachments):
        '''Adds to the attachment indexes all the given
        attachments ``(a1, a2)``.'''
        for a1, a2 in attachments:
            self.add_to_attachments_index((a1, a2))

    def ensure_remove_attachment(self, a1, a2):
        """If there was an edge from a1 to a2, remove it."""
        logging.info('Model: ensuring detaching edge from {0} to {1}'
                     ''.format(a1, a2))
        if (a1, a2) in self.attachments:
            self.remove_attachment(a1, a2)

    def remove_attachment(self, a1, a2):
        """Object a1 will no longer point at object a2."""
        self.attachment_inlinks[a2].remove(a1)
        self.attachment_outlinks[a1].remove(a2)
        del self.attachments[a1, a2]

    def remove_obj_from_attachment(self, objid):
        """Clears out the given CropObject from the attachments
        graph."""
        if objid in self.attachment_inlinks:
            inlinks = self.attachment_inlinks[objid]
            for a in inlinks:
                del self.attachments[a, objid]

        if objid in self.attachment_outlinks:
            outlinks = self.attachment_outlinks[objid]
            for a in outlinks:
                del self.attachments[objid, a]

        self._remove_obj_from_attachment_index(objid)

    def _remove_obj_from_attachment_index(self, objid):
        """Remove all of this node's inlinks and outlinks,
        and remove its record from the attachment index.
        DO NOT USE THIS directly, use :meth:`remove_obj_from_attachment`!"""
        if objid in self.attachment_outlinks:
            self.clear_obj_outlinks(objid)
            del self.attachment_outlinks[objid]
        if objid in self.attachment_inlinks:
            self.clear_obj_inlinks(objid)
            del self.attachment_inlinks[objid]

    def clear_obj_outlinks(self, objid):
        """Remove the node's outlinks, and remove it from the inlinks
        of the notdes it outlinks to."""
        if objid in self.attachment_outlinks:
            outlinks = self.attachment_outlinks[objid]
            for o in outlinks:
                if objid in self.attachment_inlinks[o]:
                    self.attachment_inlinks[o].remove(objid)
            self.attachment_outlinks[objid] = set()

    def clear_obj_inlinks(self, objid):
        """Remove the node's inlinks, and remove it from the outlinks
        of the nodes from which it has inlinks"""
        if objid in self.attachment_inlinks:
            inlinks = self.attachment_inlinks[objid]
            for i in inlinks:
                if objid in self.attachment_outlinks[i]:
                    self.attachment_outlinks[i].remove(objid)
            self.attachment_inlinks[objid] = set()

    def clear_attachments(self):
        self.attachments = []
        self.attachment_inlinks = dict()
        self.attachment_outlinks = dict()

    def sync_attachments_to_cropobjects(self):
        """Ensures that the attachments are accurately reflected
        among the CropObjects. The attachments are build separately
        in the app, so they need to be written to the CropObjects
        explicitly."""
        logging.info('Model: Syncing {0} attachments to CropObjects.'
                     ''.format(len(self.attachments)))
        for objid in self.attachment_inlinks:
            c = self.cropobjects[objid]
            c.inlinks = list(self.attachment_inlinks[objid])
        for objid in self.attachment_outlinks:
            c = self.cropobjects[objid]
            c.outlinks = list(self.attachment_outlinks[objid])
        # raise NotImplementedError()

    def sync_cropobjects_to_attachments(self):
        """Ensures that the attachment structure in CropObjects
        is accurately reflected in the attachments data structure
        of the model. (Typically, you want to call this on importing
        a new set of CropObjects, to make sure their inlinks and outlinks
        are correctly represented in the attachment structures."""
        edges = []
        for c in self.cropobjects.values():
            for o in c.outlinks:
                edges.append((c, o))
        self.clear_attachments()
        for e in edges:
            self.add_attachment(e)

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

    ##########################################################################
    # Connected components: a useful thing to have
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


