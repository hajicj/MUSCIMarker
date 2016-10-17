"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import copy
import logging
import pprint

import math
from kivy.adapters.dictadapter import DictAdapter
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.properties import ObjectProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.listview import SelectableView, ListView, CompositeListItem
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


class EdgeView(SelectableView, ToggleButton):
    """The EdgeView class represents a CropObject attachment edge.

    Currently: only a very simple """
    selected_color = ListProperty([1., 0., 0., 0.5])
    deselected_color = ListProperty([1., 0., 0., 0.3])

    vert_start = NumericProperty()
    horz_start = NumericProperty()

    vert_end = NumericProperty()
    horz_end = NumericProperty()

    _collide_threshold = NumericProperty(2.0)

    def __init__(self,
                 cropobject_from, cropobject_to, edge_label=None,
                 rgb=(1, 0, 0), **kwargs):
        """Initialize EdgeView: draw a red line from the middle
        of ``obj_from`` to the middle of ``obj_to``.

        Currently does NOT do the conversion from model-world to editor-world.
        It expects the cropobj_from and cropobj_to to already be editor-world.
        """
        super(EdgeView, self).__init__(**kwargs)

        self.start_objid = cropobject_from.objid
        self.end_objid = cropobject_to.objid
        self.label = edge_label
        self.rgb = rgb

        # Another shitty, shitty x/y switch. Why can't people use
        # (top, left, bottom, right) names???
        self.vert_start = cropobject_from.x + (cropobject_from.height / 2)
        self.horz_start = cropobject_from.y + (cropobject_from.width / 2)

        self.vert_end = cropobject_to.x + (cropobject_to.height / 2)
        self.horz_end = cropobject_to.y + (cropobject_to.width / 2)

        self._line_width = 1
        self._selected_line_width = 2

        ##### Handling the button stuff -- temporary...
        alpha = 0.3
        self.text = ''   # We don't want any text showing up

        r, g, b = rgb
        self.selected_color = r, g, b, min([1.0, alpha * 1.8])
        self.deselected_color = r, g, b, alpha
        self.alpha = alpha  # Recorded for future color changes on class change

        # Overriding the default button color and border behavior
        self.background_color = self.deselected_color
        self.background_normal = ''
        self.background_down = ''
        self.border = 0, 0, 0, 0

        #######

        # We have drawn the line to our own canvas, but where
        # is *this* widget? Where are this widget's canvas w.r.t.
        # the editor? We need to position ourselves!
        #  -- this is a bit tricky, though, because this widget is not
        #     a rectangle. It should not react to touches outside
        #     the diagonal. So, we should override collide_point().
        h = max(max(self.horz_start, self.horz_end) - min(self.horz_start, self.horz_end),
                self._line_width)
        w = max(max(self.vert_start, self.vert_end) - min(self.vert_start, self.vert_end),
                self._line_width)
        self.size = h, w
        self.size_hint = (None, None)
        self.pos = min(self.horz_start, self.horz_end), min(self.vert_start, self.vert_end)

        # Overriding default release
        self.always_release = False

        logging.info('EdgeView: Initialized for edge {0}'
                     #', with pos={1}, size={2}'
                     ''.format(self.edge, self.pos, self.size))
        self.do_render()

        self.register_event_type('on_key_captured')
        self.create_bindings()

    @property
    def edge(self):
        return self.start_objid, self.end_objid

    @property
    def graph(self):
        return App.get_running_app().annot_model.graph

    @property
    def bottom(self):
        return self.y

    @property
    def left(self):
        return self.x

    def create_bindings(self):
        logging.info('EdgeView\t{0}: Creating bindings'.format(self.edge))
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)
        #logging.info('EdgeView\t{0}: Current on_key_down total observers: {1}, obs:\n{2}'
        #             ''.format(self.edge, len(Window.get_property_observers('on_key_down')),
        #                       pprint.pformat(Window.get_property_observers('on_key_down'))))

    def remove_bindings(self):
        logging.info('EdgeView\t{0}: Removing bindings'.format(self.edge))
        Window.unbind(on_key_down=self.on_key_down)
        Window.unbind(on_key_up=self.on_key_up)

    def on_key_down(self, window, key, scancode, codepoint, modifier):

        dispatch_key = self.keypress_to_dispatch_key(key, scancode, codepoint, modifier)
        logging.info('EdgeView\t{0}: Handling key {1}, self.is_selected={2}'
                     ''.format(self.edge, dispatch_key, self.is_selected))

        if not self.is_selected:
            return False

        if dispatch_key == '8':
            self.remove_from_model()
        elif dispatch_key == '27':
            self.dispatch('on_release')
            self.deselect()
        else:
            return False

        self.dispatch('on_key_captured')
        return False

    def on_key_up(self, window, key, scancode):
        logging.info('EdgeView\t{0}: Handling key_up {1}'.format(self.edge, key))
        return False

    def on_key_captured(self, *largs):
        """Default handler for on_key_captured event."""
        pass

    @staticmethod
    def keypress_to_dispatch_key(key, scancode, codepoint, modifiers):
        """Converts the key_down event data into a single string for more convenient
        keyboard shortcut dispatch."""
        if modifiers:
            return '{0}+{1}'.format(key, ','.join(sorted(modifiers)))
        else:
            return '{0}'.format(key)

    def remove_from_model(self):
        self.remove_bindings()
        self.deselect()
        self.graph.ensure_remove_edge(self.start_objid, self.end_objid)

    def select(self, *args):
        logging.info('EdgeView\t{0}: called selection!'.format(self.edge))
        self.background_color = self.selected_color
        if isinstance(self.parent, CompositeListItem):
            self.parent.select_from_child(self, *args)
        super(EdgeView, self).select(*args)
        self.do_render()

    def deselect(self, *args):
        logging.info('EdgeView\t{0}: called deselection!'.format(self.edge))
        self.background_color = self.deselected_color
        if isinstance(self.parent, CompositeListItem):
            self.parent.deselect_from_child(self, *args)
        super(EdgeView, self).deselect(*args)
        self.do_render()

    def collide_point(self, h, v):
        """The edge collides points only along its course, at most
        self._collide_threshold points away from the line."""
        _cthr = self._collide_threshold
        if not ((self.left - _cthr) <= h <= (self.right + _cthr)
                and (self.bottom - _cthr) <= v <= (self.top + _cthr)):
            return False

        hA = self.horz_start
        vA = self.vert_start
        hB = self.horz_end
        vB = self.vert_end

        # Thanks, Wolfram Alpha!
        norm = (hA - hB) ** 2 + (vA - vB) ** 2
        d_square = (((hA - hB) * (vB - v) - (hB - h) * (vA - vB)) ** 2) / norm
        logging.warning('EdgeView\t{0}: collision delta_square {1}'.format(self.edge, d_square))
        output = d_square < (_cthr ** 2)

        return output


    def render(self):
        # We are rendering directly onto the EdgeListView's container
        # FloatLayout
        points = [self.horz_start, self.vert_start,
                  self.horz_end, self.vert_end]
        # logging.debug('EdgeView: Rendering edge {0} with points {1}, selected: {2}'
        #               ''.format(self.edge, points, self.is_selected))
        # logging.info('EdgeView: Derived size {0}, self.size {1}, self.pos {2}'
        #              ''.format((points[0] - points[2], points[1] - points[3]),
        #                        self.size,
        #                        self.pos))
        self.canvas.clear()
        with self.canvas:
            Color(*self.rgb)
            Line(points=points, width=self._line_width)
            if self.is_selected:
                # logging.info('EdgeView\t{0}: Rendering selected!'.format(self.edge))
                Color(*self.background_color)
                Line(points=points, width=self._selected_line_width)
            # Rectangle(pos=self.pos, size=self.size)

    def do_render(self):
        # logging.info('EdgeView: Requested rendering for edge {0}'
        #              ''.format(self.edge))
        self.render()


class ObjectGraphRenderer(FloatLayout):

    # So far has no capability to handle window/editor rescaling.
    # Maybe fold into CropObjectRenderer?

    redraw = NumericProperty(0)
    '''Change this property to force redraw.'''

    def __init__(self, annot_model, graph, editor_widget, **kwargs):

        super(ObjectGraphRenderer, self).__init__(**kwargs)
        logging.info('ObjectGraphRenderer: initializing, with {0} edges'
                     ' in the graph.'.format(len(graph.edges)))

        self.model = annot_model
        self.graph = graph

        self.size = editor_widget.size
        self.pos = editor_widget.pos

        editor_widget.bind(size=self._update_size)
        editor_widget.bind(pos=self._update_pos)

        self.edge_adapter = DictAdapter(
            data=self.graph.edges,
            args_converter=self.edge_converter,
            selection_mode='multiple',
            cls=EdgeView,
        )

        self.view = EdgeListView(adapter=self.edge_adapter,
                                 size_hint=(None, None),
                                 size=self.size,
                                 pos=self.pos)

        # Hacking the ListView
        # logging.debug('View children: {0}'.format(self.view.children))
        self.view.remove_widget(self.view.children[0])
        self.view.container = FloatLayout(pos=self.pos, size=self.size)
        self.view.add_widget(self.view.container)

        Window.bind(on_key_down=self.view.on_key_down)
        Window.bind(on_key_up=self.view.on_key_up)

        # Automating the redraw pipeline:
        #  - when edge data changes, fill in adapter data,
        self.graph.bind(edges=self.update_edge_adapter_data)
        #  - once adapter data changes, redraw
        self.edge_adapter.bind(data=self.do_redraw)

        self.add_widget(self.view)

    def update_edge_adapter_data(self, instance, edges):
        """Copy the graph's edges to adapter data."""
        self.edge_adapter.cached_views = dict()
        new_data = {}
        for e, e_class in edges.iteritems():
            # The adapter creates its Views from the *values* of
            # its `data` dict. So, we must supply the edge as a part
            # of the dict value, not just the key.
            new_data[e] = (e, e_class)
        # This fires self.do_redraw():
        self.edge_adapter.data = new_data

    def on_redraw(self, instance, pos):
        self.do_redraw()

    def do_redraw(self, *args, **kwargs):
        # Args and kwargs given so that it can be fired by an on_edges
        # event from the graph.
        logging.info('ObjGraphRenderer: requested do_redraw, renderer'
                     ' size: {0}'
                     ''.format(self.redraw, self.size))
        self.view.populate()
        # self.view.log_rendered_edges()

    def edge_converter(self, row_index, rec):
        """Interface between the edge and the EdgeView."""
        # logging.info('EdgeRenderer: Requesting EdgeView kwargs for edge: {0}'
        #              ''.format(rec))

        e = rec[0]
        e_class = rec[1]

        # Get the connected CropObjects
        obj_from = self.model.cropobjects[e[0]]
        e_obj_from = self._cropobject_to_editor_world(obj_from)

        obj_to = self.model.cropobjects[e[1]]
        e_obj_to = self._cropobject_to_editor_world(obj_to)

        # Return the recomputed objects as kwargs for the EdgeView
        output = {
            'is_selected': False,
            'cropobject_from': e_obj_from,
            'cropobject_to': e_obj_to,
            'edge_label': e_class,
        }
        # logging.info('EdgeRenderer: edge_converter fired, output: {0},'
        #              ' class: {1}'
        #              ''.format(output, self.edge_adapter.get_cls()))
        return output

    def _cropobject_to_editor_world(self, obj):
        """Creates an equivalent of the given CropObject with coordinates
        in the current editor world (uses the App's scaler)."""

        # Recompute a counterpart of theirs to editor world
        mt, ml, mb, mr = obj.bounding_box
        et, el, eb, er = self.scaler.bbox_model2widget(mt, ml, mb, mr)

        obj_updated = copy.deepcopy(obj)
        # Editor world counts X from the *bottom*
        obj_updated.x = eb
        obj_updated.y = el
        obj_updated.width = er - el
        obj_updated.height = et - eb

        return obj_updated

    @property
    def scaler(self):
        return App.get_running_app().image_scaler

    def _update_size(self, instance, size):
        self.size = size
        logging.info('ObjectGraphRenderer: setting size to {0}'.format(self.size))

    def _update_pos(self, instance, pos):
        self.pos = pos
        logging.info('ObjectGraphRenderer: setting pos to {0}'.format(self.pos))


##############################################################################


class EdgeListView(ListView):
    # Needs to implement:
    #  - populate
    #container = FloatLayout()

    @property
    def _model(self):
        return App.get_running_app().annot_model

    @property
    def _graph(self):
        return self._model.graph

    @property
    def rendered_edges(self):
        return self.container.children

    def log_rendered_edges(self):
        # logging.info('EdgeListView.log_rendered_edges: self.pos = {0},'
        #              ' self.wpos = {1},'
        #              ' self.size = {2}'.format(self.pos, self.to_window(*self.pos),
        #                                        self.size))
        for e in self.rendered_edges:
            logging.info('EdgeListView.log_rendered_edges: edge {0} with'
                         ' pos {1}, wpos {2}, size {3}'.format(e.edge,
                                                               e.pos,
                                                               e.to_window(*e.pos),
                                                               e.size))

    # Currently a "slow populate": remove everything and then add everything
    def populate(self, istart=None, iend=None):
        logging.info('EdgeListView: populating, with {0}'
                     ' current EdgeViews and {1} edges in adapter.'
                     ''.format(len(self.container.children),
                               len(self.adapter.data)))
        container = self.container

        # logging.debug('EdgeListView: populating, container pos={0}, size={1}'
        #               ''.format(container.pos, container.size))

        for w in container.children[:]:
            #logging.debug('EdgeListView.populate: Current edges in container: {0}'
            #              ''.format([ww.edge for ww in container.children]))
            w_key = w.edge
            if w_key in self._graph.edges:
                continue
            # "Clean up" the EdgeView widget
            w.remove_bindings()
            # Remove from cache
            #logging.info('EdgeListView.populate: Adapter cache {0}'
            #             ''.format(self.adapter.cached_views.keys()))
            w_cache_key = self._adapter_key2index(w_key)
            if (w_cache_key is not None) and (w_cache_key in self.adapter.cached_views):
                # logging.info('Removing edge {0} from adapter cache.'.format(w_key))
                del self.adapter.cached_views[w_cache_key]
            # logging.debug('EdgeListView.populate: Removing edge {0}'.format(w_key))
            container.remove_widget(w)
            self._count -= 1
            # logging.debug('EdgeListView.populate: Finished removing edge {0}'.format(w_key))

        logging.info('EdgeListView.populate: Edges in container after removal: {0}'
                     ''.format([ww.edge for ww in container.children]))

        rendered_edges = set([ww.edge for ww in self.container.children[:]])

        # Adapter keys are (from, to), values are True (will be
        # edge classes) -- the adapter is bound to the graph.edges
        # dict.
        for e_key, e in self.adapter.data.iteritems():
            edge, e_label = e  # The adapter has items ((from, to), label)
            if edge in rendered_edges:
                continue
            logging.info('EdgeListView.populate: Adding edge from adapter {0}'.format(e))
            e_idx = self._adapter_key2index(e_key)
            if e_idx is None:
                raise ValueError('EdgeListView.populate(): Adapter sorted_keys'
                                 ' out of sync with data.')
            item_view = self.adapter.get_view(e_idx)
            # logging.info('EdgeListView.populate: generated EdgeView {0}'.format(item_view.edge))
            ins_index = 0
            container.add_widget(item_view, index=ins_index)
            self._count += 1

        logging.info('EdgeListView: finished populating, with {0}'
                     ' current EdgeViews.'
                     ''.format(len(self.container.children)))

    def _adapter_key2index(self, key):
        """Converts a key into an adapter index, so that we can request
        views based on the keys from the adapter. This avoids having to
        iterate over all the children.

        If the key is not in the adapter, returns None.
        """
        sorted_keys = self.adapter.sorted_keys
        for i, k in enumerate(sorted_keys):
            if k == key:
                return i
        return None

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        logging.info('EdgeListView.on_key_down(): got keypress {0}'
                     ''.format(key))

    def on_key_up(self, window, key, scancode):
        logging.info('EdgeListView.on_key_up(): got keypress {0}'
                     ''.format(key))
