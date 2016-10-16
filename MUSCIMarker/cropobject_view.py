"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import logging
from time import time

from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Mesh
from kivy.properties import ListProperty, BooleanProperty, NumericProperty
from kivy.properties import ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.bubble import Bubble
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.listview import SelectableView, CompositeListItem
from kivy.uix.scatter import Scatter
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton

import tracker as tr

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


# Should behave like a ToggleButton.
# Important difference from ListItemButton:
#
# * Colors defined at initialization time,
# * Text is empty
class CropObjectView(SelectableView, ToggleButton):
    """The view to an individual CropObject. Implements interface for CropObject
    manipulation.

    Selection
    ---------

    The ``CropObjectView`` is selectable by clicking. Keyboard shortcuts only work
    when the button is selected.

    Mouse interaction
    -----------------

    Once selected, the CropObject can be dragged around [NOT IMPLEMENTED].

    Keyboard shortcuts
    ------------------

    If the CropObjectView handles a key press event, it will not propagate.

    The available keyboard shortcuts are:

    * Backspace: Remove the CropObject
    * Escape: Unselect
    * Arrow keys: move the CropObject by 1 editor-scale pixel.
    * Arrow keys + alt: move the CropObject by 1 display pixel. (Finest.)
    * Arrow keys + shift: stretch the CropObject by 1 editor-scale pixel.
    * Arrow keys + alt + shift: stretch the CropObject by 1 display pixel. (Finest.)
    * i: toggle info label
    * c: change class selection

    Export
    ------

    Note that upon export, it is necessary to somehow recompute the display
    pixels into the best model pixel bounding box. The priority is to contain
    the entire symbol; it's not a large problem if the box is slightly larger
    than the symbol. [NOT IMPLEMENTED]
    """
    selected_color = ListProperty([1., 0., 0., 0.5])
    deselected_color = ListProperty([1., 0., 0., 0.3])

    cropobject = ObjectProperty()

    _info_label_shown = BooleanProperty(False)
    info_label = ObjectProperty(None, allownone=True)

    _mlclass_selection_spinner_shown = BooleanProperty(False)
    mlclass_selection_spinner = ObjectProperty(None, allownone=True)

    _height_scaling_factor = NumericProperty(1.0)
    _width_scaling_factor = NumericProperty(1.0)

    _editor_scale = NumericProperty(1.0)

    def __init__(self, selectable_cropobject, rgb, alpha=0.3, **kwargs):
        """
        :param selectable_cropobject: The intermediate-level CropObject represnetation,
            with recomputed dimension.
        :param rgb:
        :param alpha: Works for deselected color, when selected, multiplied by 1.5
        :param kwargs:
        :return:
        """
        logging.debug('Render: Initializing CropObjectView with args: c={0},'
                      ' rgb={1}, alpha={2}'.format(selectable_cropobject, rgb, alpha))
        super(CropObjectView, self).__init__(**kwargs)

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

        # Overriding default release
        self.always_release = False

        self.cropobject = selectable_cropobject
        self.is_selected = selectable_cropobject.is_selected

        # If the underlying cropobject has a mask, render that mask
        if self._model_counterpart.mask is not None:
            self.render_mask()

        self.size = self.cropobject.width, self.cropobject.height
        self.size_hint = (None, None)
        self.pos = self.cropobject.y, self.cropobject.x

        self._height_scaling_factor = self.height / float(self._model_counterpart.height)
        self._width_scaling_factor = self.width / float(self._model_counterpart.width)
        # self.pos_hint = {'x': self.cropobject.x, 'y': self.cropobject.y }
        # self.pos_hint = {'x': 0, 'y': 0 }

        # self.group = self.cropobject.objid

        self._editor_scale = App.get_running_app().editor_scale

        self.register_event_type('on_key_captured')
        self.create_bindings()

    def create_bindings(self):
        # logging.info('Creating bindings for COV {0}'.format(self))
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)
        self.bind(pos=self.update_info_label)
        self.bind(size=self.update_info_label)
        self.bind(height=self.update_info_label)
        self.bind(width=self.update_info_label)

        App.get_running_app().bind(editor_scale=self.setter('_editor_scale'))

    def remove_bindings(self):
        # logging.info('Removing bindings for COV {0}'.format(self))
        Window.unbind(on_key_down=self.on_key_down)
        Window.unbind(on_key_up=self.on_key_up)
        self.unbind(pos=self.update_info_label)
        self.unbind(size=self.update_info_label)
        self.unbind(height=self.update_info_label)
        self.unbind(width=self.update_info_label)

        App.get_running_app().unbind(editor_scale=self.setter('_editor_scale'))

    def update_color(self, rgb):
        r, g, b = rgb
        self.selected_color = r, g, b, min([1.0, self.alpha * 1.8])
        self.deselected_color = r, g, b, self.alpha
        if self.is_selected:
            self.background_color = self.selected_color
        else:
            self.background_color = self.deselected_color

    def render_mask(self):
        """NOT IMPLEMENTED

        Rendering a mask in Kivy is difficult. (Can Mesh do nonconvex?)"""
        pass

    ##########################################################################
    # Keyboard event processing: the core UI of the CropObjectView
    def on_key_down(self, window, key, scancode, codepoint, modifier):
        """This method is one of the primary User Interfaces: keyboard
        shortcuts to manipulate a selected CropObject.

        :param window:
        :param key:
        :param scancode:
        :param codepoint:
        :param modifier:
        :return:
        """
        # if self.cropobject.objid < 50:
        #     logging.info('CropObjectView: Key caught by CropObjectView {0}: {1}'
        #                  ''.format(self,
        #                            (key, scancode, codepoint, modifier)))

        # At most one CropObject may be selected.
        if not self.is_selected:
            return False

        # Key dispatch
        # ------------
        dispatch_key = self.keypress_to_dispatch_key(key, scancode, codepoint, modifier)

        logging.info('CropObjectView: Handling key {0}, self.is_selected={1}.'
                     '\nself.cropobject={2}'
                     ''.format(dispatch_key, self.is_selected, str(self.cropobject.objid)))

        # Deletion
        if dispatch_key == '8':  # Delete
            self.remove_from_model()

        # Unselect
        elif dispatch_key == '27':  # Escape
            logging.info('CropObjectView: handling deselect + state to \'normal\'')
            # Simple deselection is not enough because of the adapter handle_selection()
            # method.
            self.dispatch('on_release')
            self.deselect()  # ...called from the adapter's handle_selection()

        # Moving around
        elif dispatch_key == '273':  # Up arrow
            logging.info('CropObjectView: handling move up')
            self.move(vertical=1)
        elif dispatch_key == '274':  # Down arrow
            logging.info('CropObjectView: handling move down')
            self.move(vertical=-1)
        elif dispatch_key == '275':  # Right arrow
            logging.info('CropObjectView: handling move right')
            self.move(horizontal=1)
        elif dispatch_key == '276':  # Left arrow
            logging.info('CropObjectView: handling move left')
            self.move(horizontal=-1)

        # Fine-grained moving around
        elif dispatch_key == '273+alt':  # Up arrow
            logging.info('CropObjectView: handling move_fine up: DISABLED')
            #self.move_fine(vertical=1)
        elif dispatch_key == '274+alt':  # Down arrow
            logging.info('CropObjectView: handling move_fine down: DISABLED')
            #self.move_fine(vertical=-1)
        elif dispatch_key == '275+alt':  # Right arrow
            logging.info('CropObjectView: handling move_fine right: DISABLED')
            #self.move_fine(horizontal=1)
        elif dispatch_key == '276+alt':  # Left arrow
            logging.info('CropObjectView: handling move_fine left: DISABLED')
            #self.move_fine(horizontal=-1)

        # Coarse-grained stretching
        elif dispatch_key == '273+shift':  # Up arrow
            logging.info('CropObjectView: handling stretch up')
            self.stretch(vertical=1)
        elif dispatch_key == '274+shift':  # Down arrow
            logging.info('CropObjectView: handling stretch down')
            self.stretch(vertical=-1)
        elif dispatch_key == '275+shift':  # Right arrow
            logging.info('CropObjectView: handling stretch right')
            self.stretch(horizontal=1)
        elif dispatch_key == '276+shift':  # Left arrow
            logging.info('CropObjectView: handling stretch left')
            self.stretch(horizontal=-1)

        # Fine-grained stretching
        elif dispatch_key == '273+alt,shift':  # Up arrow
            logging.info('CropObjectView: handling stretch_fine up: DISABLED')
            #self.stretch_fine(vertical=1)
        elif dispatch_key == '274+alt,shift':  # Down arrow
            logging.info('CropObjectView: handling stretch_fine down: DISABLED')
            #self.stretch_fine(vertical=-1)
        elif dispatch_key == '275+alt,shift':  # Right arrow
            logging.info('CropObjectView: handling stretch_fine right: DISABLED')
            #self.stretch_fine(horizontal=1)
        elif dispatch_key == '276+alt,shift':  # Left arrow
            logging.info('CropObjectView: handling stretch_fine left: DISABLED')
            #self.stretch_fine(horizontal=-1)

        # Change class
        elif dispatch_key == '99':  # c
            logging.info('CropObjectView: handling mlclass selection')
            self.toggle_class_selection()

        # Show/hide info panel
        elif dispatch_key == '105':  # i
            logging.info('CropObjectView: handling info panel')
            self.toggle_info_panel()

        elif dispatch_key == '120':
            logging.info('CropObjectView: handling split')
            self.split()

        else:
            # The key is not recognized by the CropObjectView, try others.
            return False

        # If we got here, the key has been caught and processed.
        # However, maybe we want to do the operation with other selected objects
        # as well.
        # On the other hand: this makes things propagate past the CropObjectViews,
        # so for example Escape unselects all CropObjects *and* quits the application.
        # Therefore, the CropObjectListView should "block" these signals
        # from propagating further.
        # Current policy: if any CropObjectView captures a key signal, it will propagate
        # past the CropObjectListView.
        self.dispatch('on_key_captured')
        return False

    def on_key_up(self, window, key, scancode):
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

    ##########################################################################
    # Accessing the model & the cropobject in the model, so that the user
    # can manipulate the underlying data through the CropObjectView.
    @property
    def _model(self):
        return App.get_running_app().annot_model

    @property
    def _model_counterpart(self):
        return self._model.cropobjects[self.cropobject.objid]

    ##########################################################################
    # Class selection
    @tr.Tracker(track_names=['self'],
                transformations={'self': [lambda s: ('objid', s._model_counterpart.objid),
                                          lambda s: ('clsid', s._model_counterpart.clsid)]},
                fn_name='CropObjectView.toggle_class_selection',
                tracker_name='editing')
    def toggle_class_selection(self):
        if self._mlclass_selection_spinner_shown:
            self.destroy_mlclass_selection_spinner()
        else:
            self.create_class_selection()

    def create_class_selection(self):
        logging.info('CropObjectView\t{0}: show_class_selection() fired.'
                     ''.format(self.cropobject.objid))
        self.mlclass_selection_spinner = Spinner(
            id='mlclass_cropobject_selection_spinner_{0}'.format(self.cropobject.objid),
            pos=self.pos,
            text='{0}'.format(self._model.mlclasses[self.cropobject.clsid].name),
            font_size=15,
            values=sorted(self._model.mlclasses_by_name.keys(),
                          key=lambda k: self._model.mlclasses_by_name[k].clsid),
            width=300 / self._editor_scale,
            height=50 / self._editor_scale,
            size_hint=(None, None),
            # is_open=True,
        )
        self.mlclass_selection_spinner.bind(text=self.do_class_selection)
        # self.mlclass_selection_spinner.option_cls.height = 37

        self.add_widget(self.mlclass_selection_spinner)
        self._mlclass_selection_spinner_shown = True

    @tr.Tracker(track_names=['self', 'text'],
                transformations={'self': [lambda s: ('objid', s._model_counterpart.objid),
                                          lambda s: ('clsid', s._model_counterpart.clsid)]},
                fn_name='CropObjectView.do_class_selection',
                tracker_name='editing')
    def do_class_selection(self, spinner_widget, text):
        logging.info('CropObjectView\t{0}: do_class_selection() fired.'
                     ''.format(self.cropobject.objid))
        clsid = self._model.mlclasses_by_name[text].clsid

        if clsid != self.cropobject.clsid:
            self._model_counterpart.clsid = clsid
            self.cropobject.clsid = clsid
            self.update_info_label()

            # Update color
            rgb = tuple([float(x) for x in self._model.mlclasses[clsid].color])
            self.update_color(rgb)

        self.destroy_mlclass_selection_spinner()

    def destroy_mlclass_selection_spinner(self, *args, **kwargs):
        self.remove_widget(self.mlclass_selection_spinner)
        self.mlclass_selection_spinner = None
        self._mlclass_selection_spinner_shown = False

    ##########################################################################
    # Info panel: displaying information about the view in the info palette

    def toggle_info_panel(self):
        # Info panel!
        if self._info_label_shown:
            self.destroy_info_label()
        else:
            self.create_info_label()

    def create_info_label(self):
        info_label = Label(text=self.get_info_label_text())
        info_label.size_hint = (1.0, 1.0)

        self.info_label = info_label
        App.get_running_app()._get_tool_info_palette().add_widget(self.info_label)
        self._info_label_shown = True

    def destroy_info_label(self, *args, **kwargs):
        App.get_running_app()._get_tool_info_palette().remove_widget(self.info_label)
        self._info_label_shown = False

    def get_info_label_text(self):
        e_cropobject = self.cropobject
        output_lines = list()
        output_lines.append('objid:            {0}'.format(e_cropobject.objid))
        output_lines.append('cls:                {0}'.format(e_cropobject.clsname))
        #output_lines.append('cls:                {0}'.format(self._model.mlclasses[e_cropobject.clsid].name))
        output_lines.append('M.x, M.y:      {0:.2f}, {1:.2f}'
                            ''.format(self._model_counterpart.x,
                                      self._model_counterpart.y))
        output_lines.append('M.w, M.h:      {0:.2f}, {1:.2f}'
                            ''.format(self._model_counterpart.width,
                                      self._model_counterpart.height))
        if self._model_counterpart.mask is None:
            output_lines.append('Mask.nnz: None')
        else:
            output_lines.append('Mask.nnz: {0}'.format(self._model_counterpart.mask.sum()))

        output_lines.append('E.x, E.y:        {0:.2f}, {1:.2f}'.format(self.x, self.y))
        output_lines.append('E.w, E.h:        {0:.2f}, {1:.2f}'.format(self.width,
                                                                       self.height))

        output_lines.append('S.V, S.H:       {0:.2f}, {1:.2f}'
                            ''.format(self._height_scaling_factor,
                                      self._width_scaling_factor))
        return '\n'.join(output_lines)

    def update_info_label(self, *args):
        if self.info_label is not None:
            self.info_label.text = self.get_info_label_text()

    ##########################################################################

    def remove_from_model(self):
        logging.info('CropObjectView.remove_from_model(): called on objid {0}'
                     ''.format(self.cropobject.objid))

        # Problem here: the cropobject gets deleted, but the widget stays
        # alive, so it keeps capturing events. This is (a) a memory leak,
        # (b) causes crashes.
        # Easy workaround: unselect self first. This does not fix the memory
        # leak, but at least the 'invisible' CropObjectView will not
        # capture any events.
        self.deselect()
        # Another workaround: schedule self-deletion for slightly later,
        # after the widget gets removed from the call stack.

        # The problem persists also with widget deletion...
        # After clear()-ing the current CropObjectList, the CropObjectView
        # widgets stay alive!

        # What if the bindings to Window are keeping the widget alive?
        self.remove_bindings()

        # Let's at least deactivate it, so it doesn't do anything.
        # This, however, won't help upon clearing the widgets...
        self.disabled = True
        self._model.remove_cropobject(self.cropobject.objid)

    ##########################################################################
    # Movement & scaling

    @tr.Tracker(track_names=['self', 'vertical', 'horizontal'],
                transformations={'self': [lambda s: ('objid', s._model_counterpart.objid),
                                          lambda s: ('clsid', s._model_counterpart.clsid)]},
                fn_name='CropObjectView.move',
                tracker_name='editing')
    def move(self, vertical=0, horizontal=0):
        """Move the underlying CropObject.

        NOTE: How to deal with CropObjects that have a mask? Roll it?

        In the current implementation, there is no listener inside the model
        for individual CropObjects, so there is no propagation of the change
        to the view. We currently work around this by simply moving the view
        as well, but this will not work when the underlying CropObject is moved
        by some other means.
        """
        logging.info('CropObjectView {0}: moving vertical={1}, horizontal={2}'
                     ''.format(self.cropobject.objid, vertical, horizontal))
        c = self._model_counterpart
        # The CropObjects in the model are kept in the Numpy world.
        c.x += vertical #* self._height_scaling_factor
        c.y += horizontal #* self._height_scaling_factor
        if c.mask is not None:
            logging.warn('CropObjectView {0}: Moving a CropObject invalidates its mask!')
        self._model.add_cropobject(c)

        self.move_view(vertical=vertical, horizontal=horizontal)

    def move_view(self, vertical=0, horizontal=0):
        logging.info('CropObjectView {0}: moving view vertical={1}, horizontal={2}'
                     ''.format(self.cropobject.objid, vertical, horizontal))
        self.pos = (self.pos[0] + horizontal * self._width_scaling_factor,
                    self.pos[1] + vertical * self._width_scaling_factor)

    def move_fine(self, vertical=0, horizontal=0):
        """Move the underlying CropObject.

        In the current implementation, there is no listener inside the model
        for individual CropObjects, so there is no propagation of the change
        to the view. We currently work around this by simply moving the view
        as well, but this will not work when the underlying CropObject is moved
        by some other means.
        """
        logging.info('CropObjectView {0}: moving vertical={1}, horizontal={2}'
                     ''.format(self.cropobject.objid, vertical, horizontal))
        c = self._model_counterpart
        # The CropObjects in the model are kept in the Numpy world.
        c.x += vertical * self._height_scaling_factor / self._editor_scale
        c.y += horizontal * self._height_scaling_factor / self._editor_scale
        self._model.add_cropobject(c)

        self.move_view_fine(vertical=vertical, horizontal=horizontal)

    def move_view_fine(self, vertical=0, horizontal=0):
        logging.info('CropObjectView {0}: moving view vertical={1}, horizontal={2}'
                     ''.format(self.cropobject.objid, vertical, horizontal))
        self.pos = (self.pos[0] + horizontal / self._editor_scale,# / self._width_scaling_factor),
                    self.pos[1] + vertical / self._editor_scale)# / self._width_scaling_factor))

    @tr.Tracker(track_names=['self', 'vertical', 'horizontal'],
                transformations={'self': [lambda s: ('objid', s._model_counterpart.objid),
                                          lambda s: ('clsid', s._model_counterpart.clsid)]},
                fn_name='CropObjectView.stretch',
                tracker_name='editing')
    def stretch(self, vertical=0, horizontal=0):
        """Stretch the underlying CropObject. Does NOT change its position.
        Cannot make the CropObject smaller than 1 in either dimension.

        See :meth:`move` for a discussion on linking the model action and view."""
        logging.info('CropObjectView {0}: stretching vertical={1}, horizontal={2}'
                     ''.format(self.cropobject.objid, vertical, horizontal))
        c = self._model_counterpart
        if c.width + horizontal > 0:
            c.width += horizontal #* self._width_scaling_factor
        if c.height + vertical > 0:
            c.height += vertical #* self._height_scaling_factor
        self._model.add_cropobject(c)

        self.stretch_view(vertical=vertical, horizontal=horizontal)

    def stretch_view(self, vertical=0, horizontal=0):
        logging.info('CropObjectView {0}: stretching view vertical={1}, horizontal={2}'
                     ''.format(self.cropobject.objid, vertical, horizontal))
        if self.width + horizontal > 0:
            self.width += horizontal * self._width_scaling_factor
        if self.height + vertical > 0:
            self.height += vertical * self._height_scaling_factor

    def stretch_fine(self, vertical=0, horizontal=0):
        """Stretch the underlying CropObject. Does NOT change its position.
        Cannot make the CropObject smaller than 1 in either dimension.

        See :meth:`move` for a discussion on linking the model action and view."""
        logging.info('CropObjectView {0}: stretching vertical={1}, horizontal={2}'
                     ''.format(self.cropobject.objid, vertical, horizontal))
        c = self._model_counterpart
        if c.width + horizontal > 0:
            c.width += horizontal * self._width_scaling_factor / self._editor_scale
        if c.height + vertical > 0:
            c.height += vertical * self._height_scaling_factor / self._editor_scale
        self._model.add_cropobject(c)

        self.stretch_view_fine(vertical=vertical, horizontal=horizontal)

    def stretch_view_fine(self, vertical=0, horizontal=0):
        logging.info('CropObjectView {0}: stretching view vertical={1}, horizontal={2}'
                     ''.format(self.cropobject.objid, vertical, horizontal))
        if self.width + horizontal > 0:
            self.width += horizontal / self._editor_scale# / self._width_scaling_factor)
        if self.height + vertical > 0:
            self.height += vertical / self._editor_scale# / self._height_scaling_factor)

    ##########################################################################
    # Split
    @tr.Tracker(track_names=['self', 'ratio'],
                transformations={'self': [lambda s: ('objid', s._model_counterpart.objid),
                                          lambda s: ('clsid', s._model_counterpart.clsid)]},
                fn_name='CropObjectView.split',
                tracker_name='editing')
    def split(self, ratio=0.5):
        """Split the CropObject into two. If it is taller than wide, the split
        will lead horizontally (so the new CropObjects will be one above the
        other), if the CropObject is rather wide than tall, the split leads
        vertically. Both the generated CropObjects will have the original
        object's ``clsid``.

        :param ratio: Controls how far to the top/right the split will
            occurr. Keep between 0 and 1.
        """
        c = self.cropobject
        if c.width > c.height:
            # split along width
            t1 = t2 = c.x + c.height
            b1 = b2 = c.x
            l1 = c.y
            r1 = l2 = c.y + (c.width * ratio)
            r2 = c.y + c.width
            # Make a small gap between the two new objects
            r1 -= 0.3
            l2 += 0.3
        else:
            # split along height
            b1 = c.x
            t1 = b2 = c.x + (c.height * ratio)
            t2 = c.x + c.height
            l1 = l2 = c.y
            r1 = r2 = c.y + c.width
            t1 -= 0.3
            b2 += 0.3
        coords_1 = {'top': t1, 'bottom': b1, 'left': l1, 'right': r1}
        coords_2 = {'top': t2, 'bottom': b2, 'left': l2, 'right': r2}

        clsid = self.cropobject.clsid
        App.get_running_app().add_cropobject_from_selection(coords_1, clsid=clsid)
        App.get_running_app().add_cropobject_from_selection(coords_2, clsid=clsid)

        self.remove_from_model()

    ##########################################################################
    # Copied over from ListItemButton
    @tr.Tracker(track_names=['self'],
                transformations={'self': [lambda s: ('objid', s._model_counterpart.objid),
                                          lambda s: ('clsid', s._model_counterpart.clsid)]},
                fn_name='CropObjectView.select',
                tracker_name='editing')
    def select(self, *args):
        self.background_color = self.selected_color
        if not self._info_label_shown:
            self.create_info_label()

        if isinstance(self.parent, CompositeListItem):
            self.parent.select_from_child(self, *args)
        super(CropObjectView, self).select(*args)

    @tr.Tracker(track_names=['self'],
                transformations={'self': [lambda s: ('objid', s._model_counterpart.objid),
                                          lambda s: ('clsid', s._model_counterpart.clsid)]},
                fn_name='CropObjectView.deselect',
                tracker_name='editing')
    def deselect(self, *args):
        logging.info('CropObjectView\t{0}: called deselection with args {1}'
                     ''.format(self.cropobject.objid, args))
        if self._info_label_shown:
            self.destroy_info_label()
        if self._mlclass_selection_spinner_shown:
            self.destroy_mlclass_selection_spinner()

        self.background_color = self.deselected_color

        if isinstance(self.parent, CompositeListItem):
            self.parent.deselect_from_child(self, *args)
        super(CropObjectView, self).deselect(*args)

    def select_from_composite(self, *args):
        self.background_color = self.selected_color

    def deselect_from_composite(self, *args):
        self.background_color = self.deselected_color

    # For logging/debugging multi-selection only.
    #
    # def on_is_selected(self, instance, pos):
    #     logging.info('CropObjectView\t{0}: is_selected changed to {1}'
    #                  ''.format(self.cropobject.objid, self.is_selected))
    #
    # def on_press(self):
    #     logging.info('CropObjectView.on_press()\t{0}: Fired'
    #                  ''.format(self.cropobject.objid))
    #     return super(CropObjectView, self).on_press()
    #
    # def on_release(self):
    #     logging.info('CropObjectView.on_release()\t{0}: Fired'
    #                  ''.format(self.cropobject.objid))
    #     return super(CropObjectView, self).on_release()
    #
    # def on_touch_up(self, touch):
    #     if touch.grab_current is not self:
    #         logging.info('CropObjectView.on_touch_up()\t{0}: touch {1} is FOREIGN'
    #                      ''.format(self.cropobject.objid, touch))
    #     else:
    #         logging.info('CropObjectView.on_touch_up()\t{0}: touch {1} is MINE'
    #                      ''.format(self.cropobject.objid, touch))
    #     return super(CropObjectView, self).on_touch_up(touch)
