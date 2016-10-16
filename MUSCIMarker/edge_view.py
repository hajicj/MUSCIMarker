"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import copy
import logging

from kivy.adapters.dictadapter import DictAdapter
from kivy.app import App
from kivy.graphics import Color, Line
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

    x_start = NumericProperty()
    y_start = NumericProperty()

    x_end = NumericProperty()
    y_end = NumericProperty()

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

        self.x_start = cropobject_from.x + (cropobject_from.height / 2)
        self.y_start = cropobject_from.y + (cropobject_from.width / 2)

        self.x_end = cropobject_to.x + (cropobject_to.height / 2)
        self.y_end = cropobject_to.y + (cropobject_to.width / 2)

        self._line_width = 10

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
        h = max(max(self.y_start, self.y_end) - min(self.y_start, self.y_end),
                self._line_width)
        w = max(max(self.x_start, self.x_end) - min(self.x_start, self.x_end),
                self._line_width)
        self.size_hint = (None, None)
        self.size = h, w
        self.pos = min(self.y_start, self.y_end), min(self.x_start, self.x_end)

        # Note: until the edge is added to the widget tree, it does not
        # get rendered..?

        # Overriding default release
        self.always_release = False

        # Must disappear if object disappears.
        # Also should bind to changes in the cropobjects' positions...
        # ...or should that force a redraw on the ListView level?
        self.create_bindings()

        self.is_selected = False

        logging.info('EdgeView: Initialized for edge {0},'
                     ' with pos={1}, size={2}'
                     ''.format(self.edge, self.pos, self.size))
        #self.do_render()

    @property
    def edge(self):
        return self.start_objid, self.end_objid

    @property
    def graph(self):
        return App.get_running_app().annot_model.graph

    def create_bindings(self):
        pass

    def remove_bindings(self):
        pass

    def remove_from_model(self):
        self.remove_bindings()
        self.deselect()
        self.graph.ensure_remove_edge(self.start_objid, self.end_objid)

    @property
    def rel_x_start(self):
        return self.x_start - self.pos[1]

    @property
    def rel_y_start(self):
        return self.y_start - self.pos[0]

    @property
    def rel_x_end(self):
        return self.x_end - self.pos[1]

    @property
    def rel_y_end(self):
        return self.y_end - self.pos[0]

    def render(self):
        points = [self.rel_x_start, self.rel_y_start,
                  self.rel_x_end, self.rel_y_end]
        logging.info('EdgeView: Rendering edge {0} with points {1}'
                     ''.format(self.edge, points))
        self.canvas.clear()
        with self.canvas:
            Color(*self.rgb)
            Line(points=points)

    def do_render(self):
        logging.info('EdgeView: Requested rendering for edge {0}'
                     ''.format(self.edge))
        self.render()

    def select(self, *args):
        self.background_color = self.selected_color
        if isinstance(self.parent, CompositeListItem):
            self.parent.select_from_child(self, *args)
        super(EdgeView, self).select(*args)

    def deselect(self, *args):
        logging.debug('EdgeView\t{0}: called deselection with args {1}'
                      ''.format(self.edge, args))
        self.background_color = self.deselected_color
        if isinstance(self.parent, CompositeListItem):
            self.parent.deselect_from_child(self, *args)
        super(EdgeView, self).deselect(*args)


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

    def edge_converter(self, row_index, rec):
        """Interface between the edge and the EdgeView."""
        logging.info('EdgeRenderer: Requesting EdgeView kwargs for edge: {0}'
                     ''.format(rec))

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
        logging.info('EdgeRenderer: edge_converter fired, output: {0},'
                     ' class: {1}'
                     ''.format(output, self.edge_adapter.get_cls()))
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

    def _update_size(self, instance, pos):
        self.size = pos
        logging.info('ObjectGraphRenderer: setting size to {0}'.format(self.size))

    def _update_pos(self, instance, pos):
        self.pos = pos
        logging.info('ObjectGraphRenderer: setting pos to {0}'.format(self.pos))



class EdgeListView(ListView):
    # Needs to implement:
    #  - populate
    @property
    def _model(self):
        return App.get_running_app().annot_model

    @property
    def _graph(self):
        return self._model.graph

    # Currently a "slow populate": remove everything and then add everything
    def populate(self, istart=None, iend=None):
        logging.info('EdgeListView: populating, with {0}'
                     ' current EdgeViews and {1} edges in adapter.'
                     ''.format(len(self.container.children),
                               len(self.adapter.data)))
        container = self.container

        for w in container.children[:]:
            logging.debug('EdgeListView.populate: Current edges in container: {0}'
                          ''.format([ww.edge for ww in container.children]))
            w_key = w.edge
            w.remove_bindings()
            if (w_key is not None) and (w_key in self.adapter.cached_views):
                del self.adapter.cached_views[w_key]
            # Remove from cache
            logging.debug('EdgeListView.populate: Removing edge {0}'.format(w_key))
            container.remove_widget(w)
            self._count -= 1
            logging.debug('EdgeListView.populate: Finished removing edge {0}'.format(w_key))

        logging.debug('EdgeListView.populate: Edges in container after removal: {0}'
                      ''.format([ww.edge for ww in container.children]))

        # Adapter keys are (from, to), values are True (will be
        # edge classes) -- the adapter is bound to the graph.edges
        # dict.
        for e_key, e in self.adapter.data.iteritems():
            _, e_label = e  # The adapter has items ((from, to), label)
            logging.debug('EdgeListView.populate: Adding edge {0}'.format(e))
            e_idx = self._adapter_key2index(e_key)
            if e_idx is None:
                raise ValueError('EdgeListView.populate(): Adapter sorted_keys'
                                 ' out of sync with data.')
            item_view = self.adapter.get_view(e_idx)

            ins_index = 0
            container.add_widget(item_view, index=ins_index)
            self._count += 1

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
