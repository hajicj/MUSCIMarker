"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import codecs
import logging

import cv2
import matplotlib.pyplot as plt

from kivy.properties import ObjectProperty, DictProperty
from kivy.uix.widget import Widget

import mhr.muscima as mm

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

    def load_image(self, image):
        self.image = image

    def add_cropobject(self, cropobject):
        self.cropobjects[cropobject.objid] = cropobject

    def remove_cropobject(self, key):
        del self.cropobjects[key]

    def import_cropobjects(self, cropobjects):
        logging.info('Model: Importing {0} cropobjects.'.format(len(cropobjects)))
        # Batch processing is more efficient, since rendering the CropObjectList
        # is tied to any change of self.cropobjects
        self.cropobjects = {c.objid: c for c in cropobjects}

    def export_cropobjects_string(self, **kwargs):
        return mm.export_cropobject_list(self.cropobjects.values(), **kwargs)

    def export_cropobjects(self, output, **kwargs):
        with codecs.open(output, 'w', 'utf-8') as hdl:
            hdl.write(self.export_cropobjects_string(**kwargs))
            hdl.write('\n')

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

    def plot_annotations(self):
        """Plot the current animation using Matplotlib."""
        rgb_img = cv2.cvtColor(self.image, cv2.COLOR_GRAY2RGB)
        annot_img = mm.render_annotations(rgb_img,
                                          self.cropobjects.values(),
                                          self.mlclasses.values())

        logging.info('Plotting annotation, image shape: {0}'.format(annot_img.shape))
        plt.imshow(annot_img)
        plt.show()


