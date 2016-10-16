"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

from kivy.app import App
from kivy.graphics import Color, Line
from kivy.properties import ObjectProperty, NumericProperty, BooleanProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.listview import SelectableView, ListView
from kivy.uix.widget import Widget

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


class EdgeView(SelectableView, Widget):
    """The EdgeView class represents a CropObject attachment edge.

    Currently: only a very simple """
    x_start = NumericProperty()
    y_start = NumericProperty()

    x_end = NumericProperty()
    y_end = NumericProperty()

    ready_to_draw = BooleanProperty(False)
    redraw = NumericProperty(0)

    def __init__(self, cropobj_from, cropobj_to, rgb=(1, 0, 0), **kwargs):
        """Initialize EdgeView: draw a red line from the middle
        of ``obj_from`` to the middle of ``obj_to``.

        Currently does NOT do the conversion from model-world to editor-world.
        Which it should, because these should be rendered directly from
        the model.
        """
        super(EdgeView, self).__init__(**kwargs)

        self.start_objid = cropobj_from.objid
        self.end_objid = cropobj_to.objid

        self.x_start = cropobj_from.x + (cropobj_from.height / 2)
        self.y_start = cropobj_from.y + (cropobj_from.width / 2)

        self.x_end = cropobj_to.x + (cropobj_to.height / 2)
        self.y_end = cropobj_to.y + (cropobj_to.width / 2)

        self.ready_to_draw = True

        # Must disappear if object disappears.
        # Also should bind to changes in the cropobjects' positions.
        self.create_bindings()

        self.redraw += 1

    @property
    def model(self):
        return App.get_running_app().annot_model

    def create_bindings(self):
        pass

    def remove_bindings(self):
        pass

    def remove_from_model(self):
        self.remove_bindings()
        self.deselect()
        self.model.ensure_remove_edge(self.start_objid, self.end_objid)

    def on_redraw(self, instance, pos):
        if not self.ready_to_draw:
            return

        points = [self.x_start, self.y_start, self.x_end, self.y_end]
        with self.canvas:
            self.canvas.clear()
            Color(*self.rgb)
            Line(points=points)


class ObjectGraphRenderer(FloatLayout):
    pass


class EdgeListView(ListView):
    pass