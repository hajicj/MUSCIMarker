"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import collections
import logging

import numpy
import time
from skimage.draw import polygon, line

# DEBUG
# simport matplotlib.pyplot as plt

from kivy.core.window import Window
from kivy.properties import ObjectProperty, DictProperty, BooleanProperty, StringProperty, ListProperty
from kivy.uix.button import Button
from kivy.uix.widget import Widget

from editor import BoundingBoxTracer, ConnectedComponentBoundingBoxTracer, TrimmedBoundingBoxTracer, LineTracer
from utils import bbox_to_integer_bounds, image_mask_overlaps_cropobject

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."




class MUSCIMarkerTool(Widget):
    """A MUSCIMarkerTool defines a set of available actions.
    For instance the viewing tool enables the user to freely scale and move
    the image around; the selection tool provides a click & drag bounding box drawing
    interface to create new CropObjects, etc.

    The tools define a set of Widgets that get added to the editor Layout, and a set
    of shortcuts that are made available through the Command Palette.
    [TODO] A third part of the tool definition is a set of keyboard shortcuts.
    This defines the possible interactions while a tool is active.

    During initialization, the new tool retains a reference to the MUSCIMarkerApp
    that created it. This way, it can translate user actions into model operations:
    e.g. the ManualSelectTool can call an "add CropObject" controller method.
    """
    def __init__(self, app, editor_widget, command_widget, **kwargs):
        super(MUSCIMarkerTool, self).__init__(**kwargs)

        self.editor_widget_ref = editor_widget
        self.command_palette_ref = command_widget
        self.app_ref = app

        self.editor_widgets = self.create_editor_widgets()
        self.command_palette_widgets = self.create_command_widgets()
        self.keyboard_shortcuts = self.create_keyboard_shortcuts()

        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)

    def init_editor_widgets(self):
        for w in self.editor_widgets.values():
            self.editor_widget_ref.add_widget(w)

    def init_command_palette(self):
        for c in self.command_palette_widgets.values():
            self.command_palette_ref.add_widget(c)

    def init_keyboard_shortcuts(self):
        for k, action in self.keyboard_shortcuts.iteritems():
            self.app_ref.keyboard_dispatch[k] = action

    def deactivate(self):
        for w in self.editor_widgets.values():
            self.editor_widget_ref.remove_widget(w)
        for c in self.command_palette_widgets.values():
            self.command_palette_ref.remove_widget(c)

        for k in self.keyboard_shortcuts:
            del self.app_ref.keyboard_dispatch[k]

    # Override these two to make the tool do something.
    def create_editor_widgets(self):
        return collections.OrderedDict()

    def create_command_widgets(self):
        return collections.OrderedDict()

    def create_keyboard_shortcuts(self):
        return collections.OrderedDict()

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        # logging.info('ToolKeyboard: Down {0}'.format((key, scancode, codepoint, modifier)))
        # return True
        pass

    def on_key_up(self, window, key, scancode):
        # logging.info('ToolKeyboard: Up {0}'.format((key, scancode)))
        # return True
        pass

    def model_to_editor_bbox(self, m_t, m_l, m_b, m_r):
        """Use this method to convert a bounding box in the model
        world to the editor world."""
        ed_t, ed_l, ed_b, ed_r = self.app_ref.image_scaler.bbox_model2widget(m_t, m_l, m_b, m_r)
        return ed_t, ed_l, ed_b, ed_r

    def editor_to_model_bbox(self, ed_t, ed_l, ed_b, ed_r):
        """Use this method to convert a bounding box in the editor
        world to the model world."""
        m_t, m_l, m_b, m_r = self.app_ref.image_scaler.bbox_widget2model(ed_t, ed_l, ed_b, ed_r)
        return m_t, m_l, m_b, m_r

    def editor_to_model_points(self, points):
        """Converts a list of points such as from a LineTracer into a list
        of (x, y) points in the model world."""
        point_set_as_tuples = [p for i, p in enumerate(zip(points[:-1], points[1:]))
                               if i % 2 == 0]
        m_points = [self.app_ref.image_scaler.point_widget2model(wX, wY)
                    for wX, wY in point_set_as_tuples]
        m_points = [(int(x), int(y)) for x, y in m_points]
        return m_points

    def model_mask_from_points(self, m_points):
        mask = numpy.zeros(self._model_image.shape, dtype='uint8')
        m_points_x, m_points_y = zip(*m_points)
        chi = polygon(m_points_x, m_points_y)
        mask[chi] = 1.0
        return mask

    @property
    def _model(self):
        return self.app_ref.annot_model

    @property
    def _model_image(self):
        return self._model.image

###############################################################################


class ViewingTool(MUSCIMarkerTool):
    pass

###############################################################################


class AddSymbolTool(MUSCIMarkerTool):

    current_cropobject_selection = ObjectProperty(None)
    current_cropobject_model_selection = ObjectProperty(None)
    current_cropobject_mask = ObjectProperty(None)

    automask = BooleanProperty(True)

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['bbox_tracer'] = BoundingBoxTracer()
        editor_widgets['bbox_tracer'].bind(
            current_finished_bbox=self.current_selection_and_mask_from_bbox_tracer)
        return editor_widgets

    def create_command_widgets(self):
        command_widgets = collections.OrderedDict()
        c = Button(
            size_hint=(1.0, 0.1),
            text='Clear bboxes',
            on_release=self.editor_widgets['bbox_tracer'].clear
        )
        command_widgets['clear'] = c
        return command_widgets

    def on_current_cropobject_selection(self, instance, pos):
        # Ask the app to build CropObject from the bbox.
        logging.info('ManualSelectTool: fired on_current_cropobject_selection with pos={0}'
                     ''.format(pos))
        self.app_ref.add_cropobject_from_selection(
            self.current_cropobject_selection,
            mask=self.current_cropobject_mask)

        # Automatically clears the bounding box (it gets rendered as the new symbol
        # gets recorded).
        self.editor_widgets['bbox_tracer'].clear()

    def on_current_cropobject_model_selection(self, instance, pos):
        # Ask the app to build CropObject from the bbox.
        logging.info('AddSymbolTool: fired on_current_cropobject_model_selection with pos={0}'
                     ''.format(pos))
        self.app_ref.add_cropobject_from_model_selection(
            self.current_cropobject_model_selection,
            mask=self.current_cropobject_mask)

        # Automatically clears the bounding box (it gets rendered as the new symbol
        # gets recorded).
        self.editor_widgets['bbox_tracer'].clear()

    def current_selection_from_bbox_tracer(self, instance, pos):
        logging.info('ManualSelectTool: fired current_selection_from_bbox_tracer with pos={0}'
                     ''.format(pos))
        self.current_cropobject_selection = pos

    def current_selection_and_mask_from_bbox_tracer(self, instance, pos):

        # Clear the last mask
        #self.current_cropobject_mask = None
        # ...should not be necessary

        # Get mask
        ed_t, ed_l, ed_b, ed_r = pos['top'], pos['left'], \
                                 pos['bottom'], pos['right']
        m_t, m_l, m_b, m_r = self.editor_to_model_bbox(ed_t, ed_l, ed_b, ed_r)
        m_t, m_l, m_b, m_r = bbox_to_integer_bounds(m_t, m_l, m_b, m_r)

        image = self.app_ref.annot_model.image

        crop = image[m_t:m_b, m_l:m_r]
        mask = numpy.ones(crop.shape, dtype='uint8')
        mask *= crop
        mask[mask != 0] = 1

        self.current_cropobject_mask = mask

        # Now create current selection
        self.current_cropobject_model_selection = {'top': m_t,
                                                   'left': m_l,
                                                   'bottom': m_b,
                                                   'right': m_r}
        # self.current_selection_from_bbox_tracer(instance=instance, pos=pos)


###############################################################################


class ConnectedSelectTool(AddSymbolTool):

    current_cropobject_selection = ObjectProperty(None)

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['bbox_tracer'] = ConnectedComponentBoundingBoxTracer()
        editor_widgets['bbox_tracer'].bind(current_finished_bbox=self.current_selection_and_mask_from_bbox_tracer)
        return editor_widgets

###############################################################################


class TrimmedSelectTool(AddSymbolTool):

    current_cropobject_selection = ObjectProperty(None)

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['bbox_tracer'] = TrimmedBoundingBoxTracer()
        editor_widgets['bbox_tracer'].bind(current_finished_bbox=self.current_selection_from_bbox_tracer)
        return editor_widgets


###############################################################################

class LassoBoundingBoxSelectTool(MUSCIMarkerTool):
    """Note: cannot currently deal with nonconvex areas. Use the trimmed lasso
    tool instead (TLasso).

    The Lasso selection tool allows to specify in freehand a region that should
    be assigned a label. All lasso tools assign a mask as well as a bounding
    box to the CropObject.

    Bounding box: editor vs. model
    -------------------------------

    There is an issue with repeated scaling because of rounding errors.
    Generally, once the model-world bbox is computed, it should propagate
    all the way to actually adding the CropObject.

    """
    current_cropobject_selection = ObjectProperty(None)
    current_cropobject_model_selection = ObjectProperty(None)
    current_cropobject_mask = ObjectProperty(None)

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['line_tracer'] = LineTracer()
        editor_widgets['line_tracer'].do_helper_line = True
        editor_widgets['line_tracer'].bind(points=self.current_selection_and_mask_from_points)
        return editor_widgets

    def selection_from_points(self, points):
        """Returns editor coordinates, which means that bottom < top and the coords
        need to be vertically inverted."""
        point_set_as_tuples = [p for i, p in enumerate(zip(points[:-1], points[1:]))
                               if i % 2 == 0]
        # This is the Kivy --> numpy transposition
        p_horizontal, p_vertical = zip(*point_set_as_tuples)

        left = min(p_horizontal)
        right = max(p_horizontal)

        top = max(p_vertical)
        bottom = min(p_vertical)
        selection = {'top': top, 'left': left, 'bottom': bottom, 'right': right}

        return selection

    def model_selection_from_points(self, points):
        e_sel = self.selection_from_points(points)
        wT, wL, wB, wR = e_sel['top'], e_sel['left'], e_sel['bottom'], e_sel['right']
        mT, mL, mB, mR = self.app_ref.image_scaler.bbox_widget2model(wT, wL, wB, wR)
        return {'top': mT, 'left': mL, 'bottom': mB, 'right': mR}

    def mask_uncut_from_points(self, points):
        point_set_as_tuples = [p for i, p in enumerate(zip(points[:-1], points[1:]))
                               if i % 2 == 0]

        m_points = [self.app_ref.image_scaler.point_widget2model(wX, wY)
                    for wX, wY in point_set_as_tuples]

        m_points = [(int(x), int(y)) for x, y in m_points]
        mask = numpy.zeros((self.app_ref.image_scaler.model_height,
                            self.app_ref.image_scaler.model_width), dtype='uint8')
        m_points_x, m_points_y = zip(*m_points)
        chi = polygon(m_points_x, m_points_y)
        mask[chi] = 1.0

        return mask

    def cut_mask_to_selection(self, mask, selection):
        """Given a model-world uncut mask of the whole model image
        and an editor-world selection, cuts the mask to correspond
        to the given editor-world selection.

        Given an editor-world selection, however, the model-world
        coordinates may turn out to be non-integers. We need to mimic
        the model-world procedure for converting these to integers,
        to ensure that the mask's shape will exactly mimic the shape
        of the CropObject's integer bounding box.
        """
        wT, wL, wB, wR = selection['top'], selection['left'], selection['bottom'], selection['right']
        mT, mL, mB, mR = self.app_ref.image_scaler.bbox_widget2model(wT, wL, wB, wR)
        mT, mL, mB, mR = bbox_to_integer_bounds(mT, mL, mB, mR)
        logging.info('LassoBoundingBoxTool.cut_mask_to_selection: cutting to {0}, h={1}, w={2}'
                     ''.format((mT, mL, mB, mR), mB - mT, mR - mL))
        return mask[mT:mB, mL:mR]

    def cut_mask_to_model_selection(self, mask, selection):
        """Like cut_mask_to_selection, but operates on model-world selection."""
        mT, mL, mB, mR = selection['top'], selection['left'], selection['bottom'], selection['right']
        mT, mL, mB, mR = bbox_to_integer_bounds(mT, mL, mB, mR)
        logging.info('LassoBoundingBoxTool.cut_mask_to_model_selection: cutting to {0}, h={1}, w={2}'
                     ''.format((mT, mL, mB, mR), mB - mT, mR - mL))
        return mask[mT:mB, mL:mR]

    def restrict_mask_to_nonzero(self, mask):
        """Given a uncut mask, restricts it to be True only for nonzero pixels
        of the image. Modifies the input mask (doesn't copy)."""
        # TODO: This does not work properly! See AddSymbolTool.
        if mask is None:
            return None
        img = self.app_ref.annot_model.image
        mask[img == 0] = 0
        return mask

    # Not used
    def current_selection_from_points(self, instance, pos):
        selection = self.selection_from_points(pos)
        if selection is not None:
            self.current_cropobject_selection = selection

    # Not used
    def current_mask_from_points(self, instance, pos):
        """Computes the lasso mask in model coordinates."""
        mask_uncut = self.mask_uncut_from_points(pos)
        if self.app_ref.config.get('toolkit', 'cropobject_mask_nonzero_only'):
            mask_uncut = self.restrict_mask_to_nonzero(mask_uncut)
        if mask_uncut is not None:
            selection = self.selection_from_points(pos)
            mask = self.cut_mask_to_selection(mask_uncut, selection)
            self.current_cropobject_mask = mask

    # Used (bound when constructing editor widgets)
    def current_selection_and_mask_from_points(self, instance, pos):
        """Triggers adding a CropObject with both bbox and mask."""
        if pos is None:
            logging.info('LassoBoundingBoxSelect: No points, clearing & skipping.')
            self.editor_widgets['line_tracer'].clear()
            return

        # Returns None if it's not possible to create the mask.
        mask_uncut = self.mask_uncut_from_points(pos)
        if self.app_ref.config.get('toolkit', 'cropobject_mask_nonzero_only'):
            mask_uncut = self.restrict_mask_to_nonzero(mask_uncut)

        if mask_uncut is not None:
            # bbox: stay in the model world once computed & propagate
            model_selection = self.model_selection_from_points(pos)
            if model_selection is None:
                logging.info('LassoBoundingBoxSelect: model selection not generated,'
                             ' clearing & skipping')
                self.editor_widgets['line_tracer'].clear()
                pass
            else:
                logging.info('LassoBoundingBoxSelect: Gpt model_selection {0}'
                             ''.format(model_selection))
                mask = self.cut_mask_to_model_selection(mask_uncut, model_selection)
                logging.info('LassoBoundingBoxSelect: uncut mask shape {0},'
                             ' cut mask shape {1}'.format(mask_uncut.shape, mask.shape))
                self.current_cropobject_mask = mask
                logging.info('LassoBoundingBoxSelect: Recording model selection {0}'
                             ''.format(model_selection))
                self.current_cropobject_model_selection = model_selection

    def on_current_cropobject_selection(self, instance, pos):
        # Ask the app to build CropObject from the bbox.
        logging.info('LassoBoundingBoxSelect: fired on_current_cropobject_selection with pos={0}'
                     ''.format(pos))
        self.app_ref.add_cropobject_from_selection(self.current_cropobject_selection,
                                                   mask=self.current_cropobject_mask)

        # Automatically clears the bounding box (it gets rendered as the new symbol
        # gets recorded).
        self.editor_widgets['line_tracer'].clear()

    def on_current_cropobject_model_selection(self, instance, pos):
        # Ask the app to build CropObject from the bbox.
        logging.info('LassoBoundingBoxSelect: fired on_current_cropobject_model_selection with pos={0}'
                     ''.format(pos))
        self.app_ref.add_cropobject_from_model_selection(
            self.current_cropobject_model_selection,
            mask=self.current_cropobject_mask)

        # Automatically clears the bounding box (it gets rendered as the new symbol
        # gets recorded).
        self.editor_widgets['line_tracer'].clear()

    def model_to_editor_bbox(self, m_t, m_l, m_b, m_r):
        """Use this method to convert the bounding box in the model
        world to the editor world."""
        ed_t, ed_l, ed_b, ed_r = self.app_ref.image_scaler.bbox_model2widget(m_t, m_l, m_b, m_r)
        return ed_t, ed_l, ed_b, ed_r
        #
        # renderer = self.app_ref.cropobject_list_renderer
        # # Top, left, height, width
        # m_coords = m_t, m_l, m_b - m_t, m_r - m_l
        # ed_b, ed_l, ed_height, ed_width = \
        #     renderer.model_coords_to_editor_coords(*m_coords)
        # ed_t = ed_b + ed_height
        # ed_r = ed_l + ed_width
        # return ed_t, ed_l, ed_b, ed_r


###############################################################################

class TrimmedLassoBoundingBoxSelectTool(LassoBoundingBoxSelectTool):

    current_cropobject_selection = ObjectProperty(None)
    current_cropobject_mask = ObjectProperty(None)

    def model_bbox_from_points(self, pos):
        """The trimming differs from the TrimTool because only points
        inside the convex hull of the lasso count towards trimming.

        ..warning:

            Assumes the lasso region is convex.
        """
        # Algorithm:
        #  - get bounding box of lasso in model coordinates
        #  - get model coordinates of points
        #  - get convex hull mask of these coordinates
        #  - apply mask of convex hull to the bounding box
        #    of the lasso selection
        #  - trim the masked image to get final model-space bounding box
        #  - recompute to editor-space
        #  - set finished box

        # Debug/profiling
        _start_time = time.clock()

        #  - get bounding box of lasso in model coordinates
        #    (we could just get uncut mask, but for trimming, we need
        #    m_points etc. anyway)
        point_set_as_tuples = [p for i, p in enumerate(zip(pos[:-1], pos[1:]))
                               if i % 2 == 0]

        m_points = [self.app_ref.image_scaler.point_widget2model(wX, wY)
                    for wX, wY in point_set_as_tuples]

        m_points = [(int(x), int(y)) for x, y in m_points]
        image = self.app_ref.annot_model.image
        mask = numpy.zeros((self.app_ref.image_scaler.model_height,
                            self.app_ref.image_scaler.model_width),
                           dtype=image.dtype)
        m_points_x, m_points_y = zip(*m_points)
        chi = polygon(m_points_x, m_points_y)
        mask[chi] = 1.0

        m_lasso_bbox = (min(m_points_x), min(m_points_y),
                        max(m_points_x), max(m_points_y))
        m_lasso_int_bbox = bbox_to_integer_bounds(*m_lasso_bbox)

        mask *= image
        mask = mask.astype(image.dtype)
        logging.info('T-Lasso: mask: {0} pxs'.format(mask.sum() / 255))

        # - trim the masked image
        out_t, out_b, out_l, out_r = 1000000, 0, 1000000, 0
        img_t, img_l, img_b, img_r = m_lasso_int_bbox
        logging.info('T-Lasso: trimming with bbox={0}'.format(m_lasso_int_bbox))
        _trim_start_time = time.clock()
        # Find topmost and bottom-most nonzero row.
        for i in xrange(img_t, img_b):
            if mask[i, img_l:img_r].sum() > 0:
                out_t = i
                break
        for j in xrange(img_b, img_t, -1):
            if mask[j-1, img_l:img_r].sum() > 0:
                out_b = j
                break
        # Find leftmost and rightmost nonzero column.
        for k in xrange(img_l, img_r):
            if mask[img_t:img_b, k].sum() > 0:
                out_l = k
                break
        for l in xrange(img_r, img_l, -1):
            if mask[img_t:img_b, l-1].sum() > 0:
                out_r = l
                break
        _trim_end_time = time.clock()
        logging.info('T-Lasso: Trimming took {0:.4f} s'.format(_trim_end_time - _trim_start_time))

        logging.info('T-Lasso: Output={0}'.format((out_t, out_l, out_b, out_r)))

        # Rounding errors when converting m --> w --> m integers!
        #  - Output
        if (out_b > out_t) and (out_r > out_l):
            return out_t, out_l, out_b, out_r

    def model_selection_from_points(self, points):
        # This should go away anyway.
        model_bbox = self.model_bbox_from_points(points)
        if model_bbox is not None:
            t, l, b, r = model_bbox
            return {'top': t, 'left': l, 'bottom': b, 'right': r}
        else:
            return None

    def selection_from_points(self, points):
        model_bbox = self.model_bbox_from_points(points)
        if model_bbox is None:
            return None
        ed_t, ed_l, ed_b, ed_r = self.model_to_editor_bbox(*model_bbox)

        logging.info('T-Lasso: editor-coord output bbox {0}'
                     ''.format((ed_t, ed_l, ed_b, ed_r)))
        output = {'top': ed_t,
                  'bottom': ed_b,
                  'left': ed_l,
                  'right': ed_r}
        return output


###############################################################################


class GestureSelectTool(LassoBoundingBoxSelectTool):
    """The GestureSelectTool tries to find the best approximation
    to a user gesture, as though the user is writing the score
    instead of annotating it.

    Run bounds
    ----------

    * Top: topmost coordinate of all accepted runs.
    * Bottom: bottom-most coordinate of all accepted runs.
    * Left: leftmost coordinates of all runs over the lower limit.
    * Right: rightmost coordinate of all runs over the lower limit.

    NOTE: Currently only supports horizontal strokes

    NOTE: Not resistant to the gesture leaving and re-entering
        a stroke region.
    """
    current_cropobject_selection = ObjectProperty(None)
    current_cropobject_mask = ObjectProperty(None)

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['line_tracer'] = LineTracer()
        editor_widgets['line_tracer'].bind(points=self.current_selection_from_points)
        return editor_widgets

    def current_selection_from_points(self, instance, pos):

        # Map points to model
        #  - get model coordinates of points
        e_points = numpy.array([list(p) for i, p in enumerate(zip(pos[:-1], pos[1:]))
                                if i % 2 == 0])
        # We don't just need the points, we need their order as well...
        m_points = numpy.array([self.app_ref.map_point_from_editor_to_model(*p)
                                for p in e_points]).astype('uint16')
        # Make them unique
        m_points_uniq = numpy.array([m_points[0]] +
                                    [m_points[i] for i in xrange(1, len(m_points))
                                     if (m_points[i] - m_points[i-1]).sum() == 0.0])

        logging.info('Gesture: total M-Points: {0}, unique: {1}'
                     ''.format(len(m_points), len(m_points_uniq)))

        # Get image
        image = self.app_ref.annot_model.image

        # Now the intelligent part starts.
        #  - If more vertical than horizontal, record horizontal runs.
        e_sel = self.selection_from_points(pos)
        m_bbox = self.app_ref.generate_model_bbox_from_selection(e_sel)
        m_int_bbox = bbox_to_integer_bounds(*m_bbox)

        height = m_int_bbox[2] - m_int_bbox[0]
        width = m_int_bbox[3] - m_int_bbox[1]

        is_vertical = False
        if height >= 2 * width:
            is_vertical = True

        if is_vertical:
            raise NotImplementedError('Sorry, currently only supporting horizontal'
                                      ' strokes.')

        # TODO: make points also unique column-wise

        #  - Get all vertical runs the stroke goes through
        #      - Find stroke mask (approximate with straight lines) and
        #        collect all stroke points
        #      - For each point:
        stroke_mask = numpy.zeros(image.shape, dtype=image.dtype)
        all_points = [[], []]
        for i, (a, b) in enumerate(zip(m_points_uniq[:-1], m_points_uniq[1:])):
            l = line(a[0], a[1], b[0], b[1])
            all_points[0].extend(list(l[0]))
            all_points[1].extend(list(l[1]))
            stroke_mask[l] = 1

        runs = []
        # Each point's run is represented as a [top, bottom] pair,
        # empty runs are represented as (x, x).
        for x, y in zip(*all_points):
            t = x
            while (image[t, y] != 0) and (t >= 0):
                t -= 1
            b = x
            while (image[b, y] != 0) and (b >= 0):
                b += 1
            runs.append([t, b])

        #  - Compute stroke width histograms from connected components.
        run_widths = numpy.array([b - t for t, b in runs])
        nnz_run_widths = numpy.array([w for w in run_widths if w > 0])
        # Average is too high because of crossing strokes, we should use median.
        rw_med = numpy.median(nnz_run_widths)
        logging.info('Gesture: Collected stroke vertical runs, {0} in total,'
                     ' avg. width {1:.2f}'.format(len(runs),
                                                  rw_med))

        #  - Compute run width bounds
        rw_lower = 2
        rw_upper = int(rw_med * 1.1 + 1)

        #  - Sort out which runs are within, under, and over the width range
        runs_mask = [rw_lower <= (b - t) <= rw_upper for t, b in runs]
        runs_under = [(b - t) < rw_lower for t, b in runs]
        runs_over = [(b - t) > rw_upper for t, b in runs]

        runs_accepted = [r for i, r in enumerate(runs) if runs_mask[i]]
        ra_npy = numpy.array(runs_accepted)

        logging.info('Gesture: run bounds [{0}, {1}]'.format(rw_lower, rw_upper))
        logging.info('Gesture: Accepted: {0}, under: {1}, over: {2}'
                     ''.format(len(runs_accepted), sum(runs_under), sum(runs_over)))

        #  - Get run bounds
        out_t = ra_npy[:, 0].min()
        out_b = ra_npy[:, 1].max()
        out_l = min([all_points[1][i] for i, r in enumerate(runs_under) if not r])
        out_r = max([all_points[1][i] for i, r in enumerate(runs_under) if not r])

        logging.info('Gesture: model bounds = {0}'.format((out_t, out_l, out_b, out_r)))

        if (out_b > out_t) and (out_r > out_l):
            ed_t, ed_l, ed_b, ed_r = self.model_to_editor_bbox(out_t,
                                                               out_l,
                                                               out_b,
                                                               out_r)

            logging.info('Gesture: editor-coord output bbox {0}'
                         ''.format((ed_t, ed_l, ed_b, ed_r)))
            self.current_cropobject_selection = {'top': ed_t,
                                                 'bottom': ed_b,
                                                 'left': ed_l,
                                                 'right': ed_r}


###############################################################################


class BaseListItemViewsOperationTool(MUSCIMarkerTool):
    """This is a base class for tools manipulating ListItemViews.

    Override select_applicable_objects to define how the ListItemViews
    should be selected.

    Override ``@property list_view`` to point to the desired ListView.

    Override ``@property available_views`` if the default
    ``self.list_view.container.children[:]`` is not correct.

    Override the ``apply_operation`` method to get tools that actually do
    something to the CropObjectViews that correspond to CropObjects
    overlapping the lasso-ed area."""
    use_mask_to_determine_selection = BooleanProperty(False)

    line_color = ListProperty([0.6, 0.6, 0.6])

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['line_tracer'] = LineTracer()
        editor_widgets['line_tracer'].line_color = self.line_color
        editor_widgets['line_tracer'].bind(points=self.select_applicable_objects)
        return editor_widgets

    def select_applicable_objects(self, instance, points):
        raise NotImplementedError()

    @property
    def list_view(self):
        raise NotImplementedError()

    @property
    def available_views(self):
        return [c for c in self.list_view.container.children[:]]

    def apply_operation(self, item_view):
        """Override this method in child Tools to make this actually
        do something to the overlapping CropObjectViews."""
        pass


class CropObjectViewsSelectTool(BaseListItemViewsOperationTool):
    """Select the activated CropObjectViews."""

    forgetful = BooleanProperty(True)
    '''If True, will always forget prior selection. If False, will
    be "additive".'''

    line_color = ListProperty([1.0, 0.5, 1.0])

    def select_applicable_objects(self, instance, points):
        # Get the model mask
        m_points = self.editor_to_model_points(points)
        model_mask = self.model_mask_from_points(m_points)

        # Find all CropObjects that overlap
        objids = [objid for objid, c in self._model.cropobjects.iteritems()
                  if image_mask_overlaps_cropobject(model_mask, c,
                    use_cropobject_mask=self.use_mask_to_determine_selection)]

        self.editor_widgets['line_tracer'].clear()

        # Unselect
        if self.forgetful:
            for v in self.available_views:
                if v.is_selected:
                    v.dispatch('on_release')

        # Mark their views as selected
        applicable_views = [v for v in self.available_views
                             if v.objid in objids]
        for c in applicable_views:
            self.apply_operation(c)

    def apply_operation(self, item_view):
        if not item_view.is_selected:
            #item_view.select()
            item_view.dispatch('on_release')

    @property
    def list_view(self):
        return self.app_ref.cropobject_list_renderer.view

    #@property
    #def available_views(self):
    #    return self.list_view.rendered_views


class EdgeViewsSelectTool(BaseListItemViewsOperationTool):
    """Selects all edges that lead to/from CropObjects overlapped
    by the selection."""
    line_color = ListProperty([1.0, 0.0, 0.0])

    def select_applicable_objects(self, instance, points):
        # Get the model mask
        m_points = self.editor_to_model_points(points)
        model_mask = self.model_mask_from_points(m_points)

        # Find all CropObjects that overlap
        objids = [objid for objid, c in self._model.cropobjects.iteritems()
                  if image_mask_overlaps_cropobject(model_mask, c,
                    use_cropobject_mask=self.use_mask_to_determine_selection)]

        self.editor_widgets['line_tracer'].clear()

        # Mark their views as selected
        applicable_views = [v for v in self.available_views
                             if (v.edge[0] in objids) or (v.edge[1] in objids)]
        for c in applicable_views:
            self.apply_operation(c)


    def apply_operation(self, item_view):
        if not item_view.is_selected:
            item_view.dispatch('on_release')

    @property
    def list_view(self):
        return self.app_ref.graph_renderer.view

    #@property
    #def available_views(self):
    #    return self.list_view.rendered_views


###############################################################################


# NOT IMPLEMENTED
class NoteSelectTool(AddSymbolTool):
    """Given a bounding box, splits it into a stem and notehead bounding box.

    [NOT IMPLEMENTED]"""
    current_cropobject_selection = ObjectProperty(None)

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['bbox_tracer'] = ConnectedComponentBoundingBoxTracer()
        editor_widgets['bbox_tracer'].bind(current_finished_bbox=self.process_note)

    def process_note(self):
        raise NotImplementedError()

        current_postprocessed_bbox = self.editor_widgets['bbox_tracer'].current_postprocessed_bbox
        self.current_cropobject_selection = current_postprocessed_bbox


##############################################################################
# This is the toolkit's interface to the UI elements.

tool_dispatch = {
    'viewing_tool': ViewingTool,
    'add_symbol_tool': AddSymbolTool,
    'trimmed_select_tool': TrimmedSelectTool,
    'connected_select_tool': ConnectedSelectTool,
    'lasso_select_tool':  LassoBoundingBoxSelectTool,
    'trimmed_lasso_select_tool': TrimmedLassoBoundingBoxSelectTool,
    'gesture_select_tool': GestureSelectTool,
    'cropobject_views_select_tool': CropObjectViewsSelectTool,
    'edge_views_select_tool': EdgeViewsSelectTool,
}