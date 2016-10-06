"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import logging
from math import sqrt
from random import random

import numpy
from kivy.app import App
from kivy.graphics import Color, Rectangle, Point, GraphicException, Line
from kivy.properties import ListProperty, DictProperty, NumericProperty, ObjectProperty, BooleanProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

# import cv2
import skimage.measure

from utils import connected_components2bboxes

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."

##############################################################################
#
# Adapted touch tracing from:
# https://kivy.org/docs/examples/gen__demo__touchtracer__main__py.html


def calculate_points(x1, y1, x2, y2, steps=5):
    dx = x2 - x1
    dy = y2 - y1
    dist = sqrt(dx * dx + dy * dy)
    if dist < steps:
        return None
    o = []
    m = dist / steps
    for i in range(1, int(m)):
        mi = i / m
        lastx = x1 + dx * mi
        lasty = y1 + dy * mi
        o.extend([lastx, lasty])
    return o


class BoundingBoxTracer(FloatLayout):
    """View for drawing bounding boxes."""

    allow_zerosize_selection = BooleanProperty(False)
    '''Whether to record bounding boxes with a zero width or height.'''

    current_selected_bbox = DictProperty()
    '''The bounding box tracer will deposit the tracking output here.'''

    #: The tool that uses the tracer should bind something to this property.
    current_finished_bbox = DictProperty()
    '''The tool that uses the tracer should bind something to this property.'''

    def recompute_bbox_limits(self, start, stop):
        x_start, y_start = start
        x_stop, y_stop = stop
        top = max(y_start, y_stop)
        bottom = min(y_start, y_stop)
        left = min(x_start, x_stop)
        right = max(x_start, x_stop)
        return top, bottom, left, right

    def on_touch_down(self, touch):
        win = self.get_parent_window()
        ud = touch.ud
        ud['group'] = g = str(touch.uid)
        ud['color'] = random()

        with self.canvas:
            Color(ud['color'], 0.1, 1, 0.3, mode='hsv', group=g)
            ud['start'] = (touch.x, touch.y)
            ud['stop'] = (touch.x, touch.y)
            # Feedback for user
            t, b, l, r = self.recompute_bbox_limits(ud['start'], ud['stop'])
            width = r - l
            height = t - b
            ud['bbox'] = Rectangle(pos=(l, b), size=(width, height), group=ud['group'])

            # Maybe add vertical + horizontal line, to help with alignment?
            # But: the bounding box edges are already taking care of that.

        # ud['label'] = Label(size_hint=(None, None))
        # self.update_touch_label(ud['label'], touch)
        # self.add_widget(ud['label'])
        touch.grab(self)
        return True     # Touch does not propagate.

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return
        ud = touch.ud

        with self.canvas:
            ud['stop'] = (touch.x, touch.y)
            t, b, l, r = self.recompute_bbox_limits(ud['start'], ud['stop'])
            width = r - l
            height = t - b
            ud['bbox'].pos = (l, b)
            ud['bbox'].size = (width, height)

        # ud['label'].pos = touch.pos
        import time
        t = int(time.time())
        if t not in ud:
            ud[t] = 1
        else:
            ud[t] += 1
        # self.update_touch_label(ud['label'], touch)

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return
        touch.ungrab(self)
        ud = touch.ud

        # One last update
        with self.canvas:
            ud['stop'] = (touch.x, touch.y)
            t, b, l, r = self.recompute_bbox_limits(ud['start'], ud['stop'])
            width = r - l
            height = t - b
            ud['bbox'].pos = (l, b)
            ud['bbox'].size = (width, height)

        # self.canvas.remove_group(ud['group'])
        # self.remove_widget(ud['label'])

        # Export finished bbox tuple
        t, b, l, r = self.recompute_bbox_limits(ud['start'], ud['stop'])
        bbox = {'top': float(t),
                'bottom': float(b),
                'left': float(l),
                'right': float(r)}

        # Only add bbox if it has nonzero width and height.
        if (bbox['top'] - bbox['bottom'] > 0) and (bbox['right'] - bbox['left'] > 0):
            self.current_selected_bbox = bbox
        elif self.allow_zerosize_selection:
            self.current_selected_bbox = bbox

    def update_touch_label(self, label, touch):
        label.text = 'ID: %s\nPos: (%d, %d)\nClass: %s' % (
            touch.id, touch.x, touch.y, touch.__class__.__name__)
        label.texture_update()
        label.pos = touch.pos
        label.size = label.texture_size[0] + 20, label.texture_size[1] + 20

    def clear(self, *args, **kwargs):
        self.canvas.clear()

    def on_current_selected_bbox(self, instance, pos):
        """In this base bounding box tracker class, only copies
        the literal input."""
        self.current_finished_bbox = pos


class TrimmedBoundingBoxTracer(BoundingBoxTracer):
    """Snaps a finished bounding box to bind only the non-zero area
    within the box."""
    def on_current_selected_bbox(self, instance, pos):
        """Trim to the nonnzero area."""

        # This part is just getting the *model* coordinates of the box.

        app = App.get_running_app()
        cropobject = app.generate_cropobject_from_selection(pos)

        img_t = cropobject.x
        img_b = cropobject.x + cropobject.height
        img_l = cropobject.y
        img_r = cropobject.y + cropobject.width
        img_box = (img_t, img_l, img_b, img_r)
        logging.info('CCSelect: Img box {0}'.format(img_box))

        # Processing a single click: converting to single-pixel bbox
        #if (img_t == img_b) and (img_l == img_r):
        img_t = int(img_t)
        img_b = int(img_b) + 1
        img_l = int(img_l)
        img_r = int(img_r) + 1
        img_box = (img_t, img_l, img_b, img_r)
        logging.info('CCSelect: Integer-adjusted '
                     'Img box {0}'.format(img_box))

        out_t, out_b, out_l, out_r = 10000000, 0, 10000000, 0

        # "Intelligent" part goes here

        image = app.annot_model.image
        # Find topmost and bottom-most nonzero row.
        if image[img_t:img_b, img_l:img_r].sum() > 0:
            for i in xrange(img_t, img_b):
                if image[i, img_l:img_r].sum() > 0:
                    out_t = i
                    break
            for j in xrange(img_b, img_t, -1):
                if image[j-1, img_l:img_r].sum() > 0:
                    out_b = j
                    break
            # Find leftmost and rightmost nonzero column.
            for k in xrange(img_l, img_r):
                if image[img_t:img_b, k].sum() > 0:
                    out_l = k
                    break
            for l in xrange(img_r, img_l, -1):
                if image[img_t:img_b, l-1].sum() > 0:
                    out_r = l
                    break

        logging.info('CCselect: found output bbox {0}'
                     ''.format((out_t, out_l, out_b, out_r)))

        # This part is converting the postprocessed box back to editor
        # coordinates.

        # If we found something:
        if (out_b > out_t) and (out_r > out_l):
            # It is in *model* image coordinates, need to resize this
            # back to *editor* coordinates!!!
            renderer = app.cropobject_list_renderer
            # Try compensating for potential fencepost? ...nope
#            model_coords = out_t, out_l, out_b - out_t + 1, out_r - out_l + 1
            model_coords = out_t, out_l, out_b - out_t, out_r - out_l
            # This part should get superseded by the Scaler that we implemented
            # in MMBrowser utils.
            ed_b, ed_l, ed_height, ed_width = \
                renderer.model_coords_to_editor_coords(*model_coords)
            ed_t = ed_b + ed_height
            ed_r = ed_l + ed_width
            logging.info('CCselect: editor-coord output bbox {0}'
                         ''.format((ed_t, ed_l, ed_b, ed_r)))
            self.current_finished_bbox = {'top': ed_t,
                                          'bottom': ed_b,
                                          'left': ed_l,
                                          'right': ed_r}


class ConnectedComponentBoundingBoxTracer(BoundingBoxTracer):
    """Snaps a finished bounding box to bound all the connected components
    it touches. Useful for one-click annotation, or slightly inaccurate
    annotation. Works exactly like the BoundingBoxTracer, but adds
    a postprocessing step. For that, it needs a reference to the current
    image, by way of image *data*.

    The usage, however, is different. Instead of the ``current_finished_bbox``
    property, bind to the ``current_postprocessed_bbox``.

    To manipulate the image data, it also needs recomputing the bounding box
    to its Numpy-world counterpart.

    """
    allow_zerosize_selection = BooleanProperty(True)
    '''Overrides the original bbox selector setting to allow single-click
    selection.'''

    current_postprocessed_bbox = DictProperty()

    # Caches.
    _cc = NumericProperty(-1)
    _labels = ObjectProperty(None)
    _bboxes = ObjectProperty(None)

    def on_current_selected_bbox(self, instance, pos):
        """Recompute to snap to connected components within the selection.
        """
        app = App.get_running_app()
        cropobject = app.generate_cropobject_from_selection(pos)

        img_t = cropobject.x
        img_b = cropobject.x + cropobject.height
        img_l = cropobject.y
        img_r = cropobject.y + cropobject.width
        img_box = (img_t, img_l, img_b, img_r)
        logging.info('CCSelect: Img box {0}'.format(img_box))

        # Processing a single click: converting to single-pixel bbox
        if (img_t == img_b) and (img_l == img_r):
            img_t = int(img_t)
            img_b = int(img_b) + 1
            img_l = int(img_l)
            img_r = int(img_r) + 1
            img_box = (img_t, img_l, img_b, img_r)
            logging.info('CCSelect: Processed single click; adjusted '
                         'Img box {0}'.format(img_box))

        # Compute bboxes from the image (unless cached already).
        #if self._bboxes is None:
        self._cc = app.annot_model.cc
        self._labels = app.annot_model.labels
        self._bboxes = app.annot_model.bboxes
            # image = app.annot_model.image
            # logging.info('CCselect: Recomputing bboxes...')
            # if (self._cc < 0) or (self._labels is None):
            #     #self._cc, self._labels = cv2.connectedComponents(image)
            #     self._labels = skimage.measure.label(image, background=0)
            #     logging.warn('CCSelect: found {0} CCs in total. Labels dtype; {1}, cc total type: {2}'
            #                  ''.format(self._labels.max(), self._labels.dtype, type(self._cc)))
            #     self._cc = int(self._labels.max())
            # self._bboxes = connected_components2bboxes(self._labels)

        # Find components that are inside the selection.
        selected_labels = set(self._labels[img_t:img_b, img_l:img_r].flatten())
        logging.info('CCSelect: Selected labels: {0}'.format(selected_labels))
        logging.info('CCSelect: bboxes: {0}'.format(self._bboxes))
        selected_label_bboxes = numpy.array([self._bboxes[l] for l in selected_labels
                                             if l != 0])  # Exclude background CC
        logging.info('CCSelect: Selected bboxes: {0}'.format(selected_label_bboxes))

        out_t, out_b, out_l, out_r = 10000000, 0, 10000000, 0
        # Merge their bounding boxes.
        if selected_label_bboxes.shape[0] > 0:
            out_t = min(selected_label_bboxes[:,0])
            out_b = max(selected_label_bboxes[:,2])
            out_l = min(selected_label_bboxes[:,1])
            out_r = max(selected_label_bboxes[:,3])

        logging.info('CCselect: found output bbox {0}'
                     ''.format((out_t, out_l, out_b, out_r)))

        # If we found something:
        if (out_b > out_t) and (out_r > out_l):
            # This is in *model* image coordinates, need to resize this
            # back to *editor* coordinates!!!
            renderer = app.cropobject_list_renderer
            # Try compensating for potential fencepost? ...Nope
            # model_coords = out_t, out_l, out_b - out_t + 1, out_r - out_l + 1
            model_coords = out_t, out_l, out_b - out_t, out_r - out_l
            ed_b, ed_l, ed_height, ed_width = \
                renderer.model_coords_to_editor_coords(*model_coords)
            ed_t = ed_b + ed_height
            ed_r = ed_l + ed_width
            logging.info('CCselect: editor-coord output bbox {0}'
                         ''.format((ed_t, ed_l, ed_b, ed_r)))
            self.current_finished_bbox = {'top': ed_t,
                                          'bottom': ed_b,
                                          'left': ed_l,
                                          'right': ed_r}

    def _is_bbox_overlap(self, box1, box2):
        """True if the given bounding boxes overlap, False otherwise.

        PROBLEM: If there is a CC that is "contained" by another
            un-connected component (middle-of-the-horseshoe situation).
            One alternative approach to checking bbox overlap is to select
            the merged bounding box of all actual *components* that are
            inside the selection. (That solution got implemented, this
            function is now obsolete.)
        """
        overlap = False
        top_box, bottom_box = box1, box2
        if top_box[0] > box2[0]:
            top_box, bottom_box = box2, box1

        left_box, right_box = box1, box2
        if left_box[1] > box2[1]:
            left_box, right_box = box2, box1

        # Overlap happens:
        if top_box == left_box:
            # Must overlap with upper left corner of bottom box
            if (bottom_box[0] <= top_box[2]) and (bottom_box[1] <= top_box[3]):
                overlap = True
        else:
            if (top_box[1] <= bottom_box[3]) and (top_box[2] >= bottom_box[0]):
                overlap = True

        return overlap

##############################################################################


class LineTracer(FloatLayout):
    """Used for tracing a line."""
    points = ObjectProperty()

    def on_touch_down(self, touch):
        ud = touch.ud
        ud['group'] = g = str(touch.uid)
        ud['color'] = random()

        ud['start'] = (touch.x, touch.y)
        ud['stop'] = (touch.x, touch.y)
        with self.canvas:
            ud['line'] = Line(points=(touch.x, touch.y))

        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        ud = touch.ud
        ud['stop'] = (touch.x, touch.y)
        ud['line'].points += [touch.x, touch.y]

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return
        touch.ungrab(self)

        ud = touch.ud
        ud['stop'] = (touch.x, touch.y)
        ud['line'].points += [touch.x, touch.y]

        self.points = ud['line'].points

    def clear(self, *args, **kwargs):
        self.canvas.clear()