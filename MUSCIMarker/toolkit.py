"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import collections
import logging

import cv2
import numpy
import time
from skimage.draw import polygon, line

# DEBUG
import matplotlib.pyplot as plt

from kivy.core.window import Window
from kivy.properties import ObjectProperty, DictProperty
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from skimage.morphology import convex_hull_image

from editor import BoundingBoxTracer, ConnectedComponentBoundingBoxTracer, TrimmedBoundingBoxTracer, LineTracer
from utils import bbox_to_integer_bounds

import mhr.preprocessing as bb

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


###############################################################################


class ViewingTool(MUSCIMarkerTool):
    pass

###############################################################################


class AddSymbolTool(MUSCIMarkerTool):

    current_cropobject_selection = ObjectProperty(None)

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['bbox_tracer'] = BoundingBoxTracer()
        editor_widgets['bbox_tracer'].bind(current_finished_bbox=self.current_selection_from_bbox_tracer)
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
        self.app_ref.add_cropobject_from_selection(self.current_cropobject_selection)

        # Automatically clears the bounding box (it gets rendered as the new symbol
        # gets recorded).
        self.editor_widgets['bbox_tracer'].clear()

    def current_selection_from_bbox_tracer(self, instance, pos):
        logging.info('ManualSelectTool: fired current_selection_from_bbox_tracer with pos={0}'
                     ''.format(pos))
        self.current_cropobject_selection = pos


###############################################################################


class ConnectedSelectTool(AddSymbolTool):

    current_cropobject_selection = ObjectProperty(None)

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['bbox_tracer'] = ConnectedComponentBoundingBoxTracer()
        editor_widgets['bbox_tracer'].bind(current_finished_bbox=self.current_selection_from_bbox_tracer)
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
    tool instead (TLasso)."""
    current_cropobject_selection = ObjectProperty(None)

    def create_editor_widgets(self):
        editor_widgets = collections.OrderedDict()
        editor_widgets['line_tracer'] = LineTracer()
        editor_widgets['line_tracer'].bind(points=self.current_selection_from_points)
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

    def current_selection_from_points(self, instance, pos):
        selection = self.selection_from_points(pos)
        self.current_cropobject_selection = selection

    def on_current_cropobject_selection(self, instance, pos):
        # Ask the app to build CropObject from the bbox.
        logging.info('ManualSelectTool: fired on_current_cropobject_selection with pos={0}'
                     ''.format(pos))
        self.app_ref.add_cropobject_from_selection(self.current_cropobject_selection)

        # Automatically clears the bounding box (it gets rendered as the new symbol
        # gets recorded).
        self.editor_widgets['line_tracer'].clear()

    def model_to_editor_bbox(self, m_t, m_l, m_b, m_r):
        """Use this method to convert the bounding box in the model
        world to the editor world."""
        renderer = self.app_ref.cropobject_list_renderer
        # Top, left, height, width
        m_coords = m_t, m_l, m_b - m_t + 1, m_r - m_l + 1
        ed_b, ed_l, ed_height, ed_width = \
            renderer.model_coords_to_editor_coords(*m_coords)
        ed_t = ed_b + ed_height
        ed_r = ed_l + ed_width
        return ed_t, ed_l, ed_b, ed_r


###############################################################################

class TrimmedLassoBoundingBoxSelectTool(LassoBoundingBoxSelectTool):

    current_cropobject_selection = ObjectProperty(None)

    def current_selection_from_points(self, instance, pos):
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
        e_lasso_bbox_sel = self.selection_from_points(pos)
        m_lasso_bbox = self.app_ref.generate_model_bbox_from_selection(e_lasso_bbox_sel)
        m_lasso_int_bbox = bbox_to_integer_bounds(*m_lasso_bbox)

        #  - get model coordinates of points
        points = numpy.array([list(p) for i, p in enumerate(zip(pos[:-1], pos[1:]))
                              if i % 2 == 0])
        # logging.info('T-Lasso: Points: {0}'.format(points))
        m_points = numpy.array(list(set([self.app_ref.map_point_from_editor_to_model(*p)
                                         for p in points]))).astype('uint16')
        logging.info('T-Lasso: total M-Points: {0}'.format(len(m_points)))

        #  - get mask for convex hull of these points
        image = self.app_ref.annot_model.image

        mask = numpy.zeros(image.shape, dtype=image.dtype)
        mask[m_points[:, 0], m_points[:, 1]] = 1.0

        _pre_convex_hull_time = time.clock()
        chi = convex_hull_image(mask)
        _post_convex_hull_time = time.clock()
        logging.info('T-Lasso: convex hull took {0:.4f} s'
                     ''.format(_post_convex_hull_time - _pre_convex_hull_time))
        mask[chi] = 1.0

        # - apply mask of convex hull to the bounding box
        #   of the lasso selection
        mask *= image
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
        logging.info('Trimming took {0:.4f} s'.format(_trim_end_time - _trim_start_time))

        logging.info('Output: {0}'.format((out_t, out_l, out_b, out_r)))
        #  - Output
        if (out_b > out_t) and (out_r > out_l):
            ed_t, ed_l, ed_b, ed_r = self.model_to_editor_bbox(out_t, out_l, out_b, out_r)

            logging.info('CCselect: editor-coord output bbox {0}'
                         ''.format((ed_t, ed_l, ed_b, ed_r)))
            self.current_cropobject_selection = {'top': ed_t,
                                                 'bottom': ed_b,
                                                 'left': ed_l,
                                                 'right': ed_r}


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
}