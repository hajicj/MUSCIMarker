"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import copy
import logging

# import gc

from kivy.adapters.dictadapter import DictAdapter
from kivy.adapters.simplelistadapter import SimpleListAdapter
from kivy.app import App
from kivy.compat import PY2
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import DictProperty, ObjectProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.listview import ListItemButton, ListView, SelectableView, ListItemReprMixin, CompositeListItem
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

from cropobject_view import CropObjectView
from muscimarker_io import cropobjects_merge_bbox, cropobjects_merge_mask

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."

Builder.load_string('''
<CropObjectListView@ListView>:
    container: container
    # RelativeLayout:
    FloatLayout:
        id: container
        pos: root.pos
        size_hint: 1, 1
''')


class CropObjectListView(ListView):
    """Container for the CropObjectViews of the annotated CropObjects.

    Important behaivors:

    Selection
    ---------

    The adapter initialized in CropObjectRenderer has selection behavior
    set to ``multiple``.

    Keyboard event trapping
    ------------------------

    Because of multiple selection, keyboard shortcuts may affect multiple
    CropObjectViews and therefore should not get trapped by the individual
    views. However, if the keyboard event is handled by a CropObjectView,
    it should not propagate beyond the CropObjectListView -- the event
    has already been handled. (For instance, if the CropObjectListView
    did not catch the 'escape' key, the application shuts down.) Therefore,
    CropObjectListView implements keyboard event trapping, shielding
    the rest of the application from keyboard events handled by
    CropObjectViews.

    The CropObjectViews implement a ``on_key_captured`` event that fires
    when the View handles to a keyboard shortcut. In :meth:`populate()`,
    the CropObjectListView binds its ``_key_trap`` setter to this event.
    Whenever a child CropObjectView fires a key, the ``_key_trap`` property
    of the CropObjectListView is set to ``True``.

    Then, the CropObjectListView implements its own :meth:`on_key_down`
    and :meth:`on_key_up` methods, which check the value of ``_key_trap``
    (through :meth:`_handle_key_trap`) and if the trap is set, unset it
    and return ``True`` to stop the keyboard event from propagating further.

    Because the keyboard events are first handled in all the CropObjectViews
    and only then in their containing CropObjectListView, when multiple
    CropObjectViews are selected, the trap will be set many times through
    all the ``on_key_captured`` events, but only sprung once, when the
    event bubbles to the CropObjectListView.
    """
    # This will be the difficult part...

    _rendered_objids = DictProperty()
    '''Keep track of which CropObjects have already been rendered.
    [NOT IMPLEMENTED]'''

    _trap_key = BooleanProperty(False)

    render_new_to_back = BooleanProperty(False)
    '''If True, will send new CropObjectsViews to the back of the container
    instead of on top when populating.'''

    @property
    def _model(self):
        return App.get_running_app().annot_model

    def populate(self, istart=None, iend=None):

        logging.info('CropObjectListView.populate(): started')
        container = self.container

        widgets_rendered = {}
        # Index widgets for removal. Removal is scheduled from the current
        # widgets (CropObjectViews), which are at this point out of sync
        # with the adapter data.
        widgets_for_removal = {}
        for w in container.children:
            w_objid = w.cropobject.objid
            widgets_rendered[w_objid] = w
            if w_objid not in self.adapter.data:
                widgets_for_removal[w_objid] = w

        logging.info('CropObjectListView.populate(): will remove {0} widgets'
                     ''.format(len(widgets_for_removal)))

        # Remove widgets for removal.
        for w_objid, w in widgets_for_removal.iteritems():
            # Deactivate bindings, to prevent widget immortality
            w.remove_bindings()
            # Also remove widget from adapter cache.
            # If they are in the cache, it means either:
            #  - They are stale and need to be removed; in case the incoming
            #    CropObjects have the same objid as one of the removed
            #    cropobjects, it would cause the cache to retrieve the already
            #    deleted CropObjectView.
            #  - The new data in the adapter with these objids has already
            #    been converted to a CropObjectView from somewhere. In that
            #    case, removing it from the cache is slightly inefficient,
            #    but does not hurt correctness.
            w_idx = self._adapter_key2index(w_objid)
            if (w_idx is not None) and (w_idx in self.adapter.cached_views):
                del self.adapter.cached_views[w_idx]
            container.remove_widget(w)
            self._count -= 1

        # Index cropobjects to add.
        # These are drawn from the adapter data, which are at this point
        # out of sync with the container widgets (CropObjectViews).
        cropobjects_to_add = {}
        for c_objid, c in self.adapter.data.iteritems():
            if c_objid not in widgets_rendered:
                cropobjects_to_add[c_objid] = c

        logging.info('CropObjectListView.populate(): will add {0} widgets'
                     ''.format(len(cropobjects_to_add)))

        # Add cropobjects to add.
        for c_objid, c in cropobjects_to_add.iteritems():
            c_idx = self._adapter_key2index(c_objid)
            # Because the cropobjects_to_add are derived from current adapter data,
            # the corresponding keys should definitely be there. But just in case,
            # we check.
            if c_idx is None:
                raise ValueError('CropObjectListView.populate(): Adapter sorted_keys'
                                 ' out of sync with data.')
            item_view = self.adapter.get_view(c_idx)
            logging.info('Populating with view that has color {0}'
                         ''.format(item_view.selected_color))
            # See CropObjectListView key trapping below.
            item_view.bind(on_key_captured=self.set_key_trap)

            # Do new objects go into the back, or into the front?
            if self.render_new_to_back:
                ins_index = len(container.children)
            else:
                ins_index = 0
            container.add_widget(item_view, index=ins_index)
            self._count += 1

        logging.info('CropObjectListView.populate(): finished, available'
                     ' CropObjects: {0}'.format([c.objid for c in self.rendered_views]))

    @property
    def rendered_views(self):
        """The list of actual rendered CropObjectViews that
        the CropObjectListView holds."""
        return [cv for cv in self.container.children[:]]

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

    def unselect_all(self):
        container = self.container
        for w in container.children:
            if hasattr(w, 'is_selected'):
                w.is_selected = False

    ##########################################################################
    # Keyboard event trapping
    #  - If a child view captures an on_key_down (event on_key_captured),
    #    will set a trap for on_key_down events bubbling up.
    #    All children will react to the event before the ListView,
    #    so the trap will simply be set many times.
    #  - Then, when the CropObjectViews have finished handling the
    #    on_key_down event and it bubbles up to the ListView, if the trap
    #    is set, the event is captured and doesn't bubble further up.
    # This strategy means one keystroke applies to all selected CropObjects.
    def handle_key_trap(self, *args):
        logging.info('CropObjectListView: handling key trap in state {0}'
                     ''.format(self._trap_key))
        if self._trap_key:
            self._trap_key = False
            logging.info('CropObjectListView: trapped key event {0}'
                         ''.format(args))
            return True
        return False

    def set_key_trap(self, *largs):
        logging.info('CropObjectListView.set_key_trap(): Got args {0}'
                     ''.format(largs))
        self._trap_key = True

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        logging.info('CropObjectListView.on_key_down(): trap {0}'
                     ''.format(self._trap_key))
        if self.handle_key_trap(window, key, scancode, codepoint, modifier):
            logging.info('CropObjectListView: NOT propagating keypress')
            return True

        # Keyboard shortcuts that affect the current selection:
        dispatch_key = CropObjectView.keypress_to_dispatch_key(key, scancode,
                                                               codepoint, modifier)

        # M for merge
        if dispatch_key == '109':
            logging.info('CropObjectListView: handling merge')
            self.merge_current_selection(destructive=True)
        # M+shift for non-destrcutive merge
        if dispatch_key == '109+shift':
            logging.info('CropObjectListView: handling non-destructive merge')
            self.merge_current_selection(destructive=False)
        # B for sending selection to back (for clickability)
        if dispatch_key == '98':
            logging.info('CropObjectListView: sending selected CropObjects'
                         ' to the back of the view stack.')
            self.send_current_selection_back()
        # A for attaching
        if dispatch_key == '97':
            logging.info('CropObjectListView: attaching selected CropObjects.')
            self.process_attach()
        # D for detaching
        if dispatch_key == '100':
            logging.info('CropObjectListView: detaching selected CropObjects.')
            self.process_detach()

        # P for actual parsing
        if dispatch_key == '112':
            logging.info('CropObjectListView: handling parse')
            self.parse_selection()

        else:
            logging.info('CropObjectListView: propagating keypress')
            return False

        # Things caught in the CropObjectListView do not propagate.
        #logging.info('CropObjectListView: NOT propagating keypress')
        return True

    def on_key_up(self, window, key, scancode):
        logging.info('CropObjectListView.on_key_up(): trap {0}'
                     ''.format(self._trap_key))
        if self.handle_key_trap(window, key, scancode):
            logging.info('CropObjectListView: NOT propagating keypress')
            return True

    ##########################################################################
    # Operations on lists of selected CropObjects
    def process_attach(self):
        cropobjects = [s._model_counterpart for s in self.adapter.selection]
        if len(cropobjects) != 2:
            logging.warn('Currently cannot process attachment for a different'
                         ' number of selected CropObjects than 2.')
            return

        a1, a2 = cropobjects[0].objid, cropobjects[1].objid
        self._model.graph.ensure_add_edge((a1, a2))

    def process_detach(self):
        cropobjects = [s._model_counterpart for s in self.adapter.selection]
        if len(cropobjects) != 2:
            logging.warn('Currently cannot process attachment for a different'
                         ' number of selected CropObjects than 2.')
            return

        a1, a2 = cropobjects[0].objid, cropobjects[1].objid
        self._model.graph.ensure_remove_edge(a1, a2)

    def send_current_selection_back(self):
        """Moves the selected items back in the rendering order,
        so that if they obscure other items, these obscured items
        will become clickable."""
        logging.info('CropObjectListView.back(): selection {0}'
                     ''.format(self.adapter.selection))
        if len(self.adapter.selection) == 0:
            logging.warn('CropObjectListView.back(): trying to send back empty'
                         ' selection.')
            return

        # How to achieve sending them back?
        # The selected CropObjectView needs to become a new child.
        #cropobjects = [s._model_counterpart for s in self.adapter.selection]

        for s in self.adapter.selection:
            # Remove from children and add to children end
            self.container.remove_widget(s)
            self.container.add_widget(s, index=len(self.container.children[:]))
            #s.remove_from_model()

        #self.render_new_to_back = True
        #for c in cropobjects:
        #    App.get_running_app().annot_model.add_cropobject(c)
        #self.render_new_to_back = False

    def merge_current_selection(self, destructive=True):
        """Take all the selected items and merge them into one.
        Uses the current MLClass.

        :param destructive: If set to True, will remove the selected
            CropObjects from the model. If False, will only unselect
            them.
        """
        logging.info('CropObjectListView.merge(): selection {0}'
                     ''.format(self.adapter.selection))
        if len(self.adapter.selection) == 0:
            logging.warn('CropObjectListView.merge(): trying to merge empty selection.')
            return

        model_cropobjects = [c._model_counterpart for c in self.adapter.selection]
        t, l, b, r = cropobjects_merge_bbox(model_cropobjects)
        mask = cropobjects_merge_mask(model_cropobjects)

        # Remove the merged CropObjects
        logging.info('CropObjectListView.merge(): Removing selection {0}'
                     ''.format(self.adapter.selection))
        if destructive:
            for s in self.adapter.selection:
                s.remove_from_model()
        else:
            for s in self.adapter.selection:
                s.deselect()

        model_cropobjects = None  # Release refs

        self.render_new_to_back = True
        App.get_running_app().add_cropobject_from_model_selection({'top': t,
                                                                   'left': l,
                                                                   'bottom': b,
                                                                   'right': r},
                                                                  mask=mask)
        self.render_new_to_back = False

    def parse_selection(self):
        """Adds edges among the current selection according to the model's
        grammar and parser."""
        cropobjects = [s._model_counterpart for s in self.adapter.selection]
        parser = self._model.parser
        if parser is None:
            return

        names = [c.clsname for c in cropobjects]
        edges_idxs = parser.parse(names)
        edges = [(cropobjects[i].objid, cropobjects[j].objid)
                 for i, j in edges_idxs]

        for e in edges:
            self._model.graph.ensure_add_edge(e)


##############################################################################


class CropObjectRenderer(FloatLayout):
    """The CropObjectRenderer class is responsible for listening to
    the cropobject dict in the model and rendering it upon itself.
    Its place is attached as an overlay of the editor widget (the image)
    with the same size and position.

    In order to force rendering the annotations, add 1 to the
    ``rendnerer.redraw`` property, which fires redrawing.
    """
    # Maybe the ObjectGraphRenderer could be folded into this?
    # To work above the selectable_cropobjects?

    selectable_cropobjects = DictProperty()

    adapter = ObjectProperty()
    view = ObjectProperty()
    editor_widget = ObjectProperty()

    cropobject_keys = ListProperty()
    cropobject_keys_mask = DictProperty(None)

    mlclasses_colors = DictProperty()

    # The following properties are used to correctly resize
    # the intermediate CropObject structures.
    model_image_height = NumericProperty()
    model_image_width = NumericProperty()

    height_ratio_in = NumericProperty(1)
    old_height_ratio_in = NumericProperty(1)
    width_ratio_in = NumericProperty(1)
    old_width_ratio_in = NumericProperty(1)

    redraw = NumericProperty(0)
    '''Signals that the CropObjects need to be redrawn.'''

    def __init__(self, annot_model, editor_widget, **kwargs):
        super(CropObjectRenderer, self).__init__(**kwargs)

        # Bindings for model changes.
        # These bindings are what causes changes in the model to propagate
        # to the view. However, the DictProperty in the model does not
        # signal changes to the dicts it contains, only insert/delete states.
        # This implies that e.g. moving a CropObject does not trigger the
        # self.update_cropobject_data() binding.
        annot_model.bind(cropobjects=self.update_cropobject_data)

        # This is just a misc operation, to keep the renderer
        # in a valid state when the user loads a different MLClassList.
        annot_model.bind(mlclasses=self.recompute_mlclasses_color_dict)

        # Bindings for view changes
        editor_widget.bind(height=self.editor_height_changed)
        editor_widget.bind(width=self.editor_width_changed)

        self.size = editor_widget.size
        self.pos = editor_widget.pos

        # The self.selectable_cropobjects level of indirection only
        # handles numpy to kivy world conversion. This can be handled
        # in the adapter conversion method, maybe?
        self.adapter = DictAdapter(
            data=self.selectable_cropobjects,
            args_converter=self.selectable_cropobject_converter,
            selection_mode='multiple',
            cls=CropObjectView,
        )

        self.view = CropObjectListView(adapter=self.adapter,
                                       size_hint=(None, None),
                                       size=self.size, #(self.size[0] / 2, self.size[1] / 2),
                                       pos=self.pos)

        # Keyboard event trapping implemented there.
        Window.bind(on_key_down=self.view.on_key_down)
        Window.bind(on_key_up=self.view.on_key_up)

        self.model_image_height = annot_model.image.shape[0]
        self.height_ratio_in = float(editor_widget.height) / annot_model.image.shape[0]
        self.model_image_width = annot_model.image.shape[1]
        self.width_ratio_in = float(editor_widget.width) / annot_model.image.shape[1]

        annot_model.bind(image=self.update_image_size)

        # self.view = ListView(item_strings=map(str, range(100)))
        self.add_widget(self.view)
        # The Renderer gets added to the editor externally, though, during
        # app build. That enables us to add or remove the renderer from
        # the active widget tree.

        self.redraw += 1
        logging.info('Render: Initialized CropObjectRenderer, with size {0}'
                     ' and position {1}, ratios {2}. Total keys: {3}'
                     ''.format(self.size, self.pos,
                               (self.height_ratio_in, self.width_ratio_in),
                               len(self.cropobject_keys)))

    def on_redraw(self, instance, pos):
        """This signals that the CropObjects need to be re-drawn. For example,
        adding a CropObject necessitates this, or resizing the window."""
        self.view.adapter.cached_views = dict()
        if self.cropobject_keys_mask is None:
            self.view.adapter.data = self.selectable_cropobjects
        else:
            self.view.adapter.data = {objid: c for objid, c in self.selectable_cropobjects.iteritems()
                                      if self.cropobject_keys_mask[objid]}
            logging.info('Render: After masking: {0} of {1} cropobjects remaining.'
                         ''.format(len(self.view.adapter.data), len(self.selectable_cropobjects)))

        # self.view.slow_populate()
        self.view.populate()
        logging.info('Render: Redrawn {0} times'.format(self.redraw))

    def update_image_size(self, instance, pos):
        prev_editor_height = self.height_ratio_in * self.model_image_height
        self.model_image_height = pos.shape[0]
        self.height_ratio_in = prev_editor_height / self.model_image_height

        prev_editor_width = self.width_ratio_in * self.model_image_width
        self.model_image_width = pos.shape[1]
        self.width_ratio_in = prev_editor_width / self.model_image_width

    def on_height_ratio_in(self, instance, pos):
        _n_items_changed = 0
        if self.height_ratio_in == 0:
            return
        for objid, c in self.selectable_cropobjects.iteritems():
            orig_c = copy.deepcopy(c)
            c.height *= self.height_ratio_in / self.old_height_ratio_in
            c.x *= self.height_ratio_in / self.old_height_ratio_in
            self.selectable_cropobjects[objid] = c
            if _n_items_changed < 0:
                logging.info('Render: resizing\n{0}\nto\n{1}'
                             ''.format(' | '.join(str(orig_c).replace('\t', '').split('\n')[1:-1]),
                                       ' | '.join(str(c).replace('\t', '').split('\n')[1:-1])))
            _n_items_changed += 1
        logging.info('Render: Redraw from on_height_ratio_in: ratio {0}, changed {1} items'
                     ''.format(self.height_ratio_in / self.old_height_ratio_in,
                               _n_items_changed))
        self.old_height_ratio_in = self.height_ratio_in
        self.redraw += 1

    def on_width_ratio_in(self, instance, pos):
        _n_items_changed = 0
        if self.width_ratio_in == 0:
            return
        for objid, c in self.selectable_cropobjects.iteritems():
            orig_c = copy.deepcopy(c)
            c.width *= self.width_ratio_in / self.old_width_ratio_in
            c.y *= self.width_ratio_in / self.old_width_ratio_in
            self.selectable_cropobjects[objid] = c
            if _n_items_changed < 0:
                logging.info('Render: resizing\n{0}\nto\n{1}'
                             ''.format(' | '.join(str(orig_c).replace('\t', '').split('\n')[1:-1]),
                                       ' | '.join(str(c).replace('\t', '').split('\n')[1:-1])))
            _n_items_changed += 1
        logging.info('Render: Redraw from on_width_ratio_in: ratio {0}, changed {1} items'
                     ''.format(self.width_ratio_in / self.old_width_ratio_in,
                               _n_items_changed))
        self.old_width_ratio_in = self.width_ratio_in
        self.redraw += 1

    def editor_height_changed(self, instance, pos):
        logging.info('Render: Editor height changed to {0}'.format(pos))
        self.height_ratio_in = float(pos) / self.model_image_height

    def editor_width_changed(self, instance, pos):
        logging.info('Render: Editor width changed to {0}'.format(pos))
        self.width_ratio_in = float(pos) / self.model_image_width

    def update_cropobject_data(self, instance, pos):
        """Fired on change in the current CropObject list: make sure
        the data structures underlying the CropObjectViews are in sync
        with the model.

        This is where the positioning magic happens. Once we fit
        the original CropObject to the widget, we're done.

        However, in the future, we need to re-do the positioning magic
        on CropObjectList import. Let's do it here now for testing
        the concepts...
        """
        # Placeholder operation: just copy this for now.
        logging.info('Render: Updating CropObject data, {0} cropobjects'
                     ' and {1} currently selectable.'
                     ''.format(len(pos), len(self.selectable_cropobjects)))

        # Clear current cropobjects. Since ``pos`` is the entire
        # CropObject dictionary from the model and the CropObjects
        # will all be re-drawn anyway, we want selectable_cropobjects
        # to match it exactly.
        self.selectable_cropobjects = {}

        for objid in pos:

            corrected_position_cropobject = copy.deepcopy(pos[objid])
            # X is vertical, Y is horizontal.
            # X is the upper left corner relative to the image. We need the
            # bottom left corner to be X. We first need to get the top-down
            # coordinate for the bottom corner (x + height), then flip it
            # around relative to the current editor height
            # (self.model_image_height - ...) then scale it down
            # (* self.height_ratio_in).
            corrected_position_cropobject.x = (self.model_image_height -
                                               (pos[objid].x + pos[objid].height)) *\
                                              self.height_ratio_in
            corrected_position_cropobject.y = pos[objid].y * self.width_ratio_in
            corrected_position_cropobject.height = corrected_position_cropobject.height *\
                                                   self.height_ratio_in
            corrected_position_cropobject.width = corrected_position_cropobject.width *\
                                                  self.width_ratio_in

            self.selectable_cropobjects[objid] = corrected_position_cropobject
            # Inversion!
            # self.selectable_cropobjects[objid].y = self.height - pos[objid].y
            self.cropobject_keys_mask[objid] = True

        self.cropobject_keys = map(str, self.selectable_cropobjects.keys())

        # The adapter data doesn't change automagically
        # when the DictProperty it was bound to changes.
        # Force redraw.
        logging.info('Render: Redrawing from update_cropobject_data')
        self.redraw += 1

    def model_coords_to_editor_coords(self, x, y, height, width):
        """Converts coordinates of a model CropObject into the corresponding
        CropObjectView coordinates."""
        x_out = (self.model_image_height - (x + height)) * self.height_ratio_in
        y_out = y * self.width_ratio_in
        height_out = height * self.height_ratio_in
        width_out = width * self.width_ratio_in
        return x_out, y_out, height_out, width_out

    def recompute_mlclasses_color_dict(self, instance, pos):
        """On MLClassList change, the color dictionary needs to be updated."""
        logging.info('Render: Recomputing mlclasses color dict...')
        for clsid in pos:
            self.mlclasses_colors[clsid] = pos[clsid].color

    def selectable_cropobject_converter(self, row_index, rec):
        """Interfacing the CropObjectView and the intermediate data structure.
        Note that as it currently stands, this intermediate structure is
        also a CropObject, although the position params X and Y have been
        switched around."""
        if max(self.mlclasses_colors[rec.clsid]) > 1.0:
            rgb = tuple([float(x) / 255.0 for x in self.mlclasses_colors[rec.clsid]])
        else:
            rgb = tuple([float(x) for x in self.mlclasses_colors[rec.clsid]])
        output = {
            #'text': str(rec.objid),
            #'size_hint': (None, None),
            'is_selected': False,
            'selectable_cropobject': rec,
            'rgb': rgb,
        }
        logging.debug('Render: Converter fired, input object {0}/{1}, with output:\n{2}'
                      ''.format(row_index, rec, output))
        return output

    def clear(self, instance, pos):
        logging.info('Render: clear() called with instance {0}, pos {1}'
                     ''.format(instance, pos))
        self.selectable_cropobjects = {}
        self.cropobject_keys = []
        self.cropobject_keys_mask = {}

        self.redraw += 1

    def mask_all(self):
        logging.info('Render: mask() called')
        self.view.unselect_all()  # ...but they disappear anyway?
        self.cropobject_keys_mask = {objid: False
                                     for objid in self.selectable_cropobjects}
        self.redraw += 1

    def unmask_all(self):
        logging.info('Render: mask() called')
        self.cropobject_keys_mask = {objid: True
                                     for objid in self.selectable_cropobjects}
        self.redraw += 1

    def on_adapter(self, instance, pos):
        # logging.info('Render: Selectable cropobjects changed, populating view.')
        logging.info('Render: Something changed in the adapter!')
