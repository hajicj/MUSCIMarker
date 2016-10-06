"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import codecs
import logging

# import cv2
# import matplotlib.pyplot as plt

from kivy.properties import ObjectProperty, DictProperty, NumericProperty
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
        self.cropobjects = {c.objid: c for c in cropobjects}

    def export_cropobjects_string(self, **kwargs):
        return muscimarker_io.export_cropobject_list(self.cropobjects.values(), **kwargs)

    @Tracker(track_names=['output'],
             fn_name='model.export_cropobjects',
             tracker_name='model')
    def export_cropobjects(self, output, **kwargs):
        with codecs.open(output, 'w', 'utf-8') as hdl:
            hdl.write(self.export_cropobjects_string(**kwargs))
            hdl.write('\n')

    @Tracker(track_names=[],
             fn_name='model.clear_cropobjects',
             tracker_name='model')
    def clear_cropobjects(self):
        logging.info('Model: Clearing all {0} cropobjects.'.format(len(self.cropobjects)))
        self.cropobjects = {}

    def import_classes_definition(self, mlclasses):
        """Overwrites previous mlclasses definition -- there can only be
        one active at the same time."""
        self.mlclasses = {m.clsid: m for m in mlclasses}
        self.mlclasses_by_name = {m.name: m for m in mlclasses}

    def get_next_cropobject_id(self):
        if len(self.cropobjects) == 0:
            return 0
        return max(self.cropobjects.keys()) + 1

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


