"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import logging

import re
from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.popup import Popup

from utils import keypress_to_dispatch_key

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


objid_selection_dialog_kv = '''
<ObjidSelectionDialog@Popup>
    size_hint: None, None
    size: app.root.size[0] * 0.5, app.root.size[1] * 0.2
    pos_hint: {'center_x': 0.5, 'center_y': 0.5}

    title: 'Select CropObjects by typing their objids (whitespace-separated).'

    # on_text: current_name_label.text = self.get_current_name()

    GridLayout:
        id: grid
        cols: 1
        padding: '24dp'

        TextInput:
            id: text_input
            size_hint_y: None
            height: dp(24)
            multiline: False
            focus: True
            text: ''

            on_text: root.text = self.text

        BoxLayout:
            size_hint_y: None
            height: dp(24)

            Button:
                id: cancel
                text: root.cancel_text
                on_release: root.cancel()

            Button:
                id: ok
                text: root.ok_text
                on_release: root.ok()

        Label:
            id: available_names_label
            size_hint_y: None
            height: dp(24)
            text: ''
'''

Builder.load_string(objid_selection_dialog_kv)

class ObjidSelectionDialog(Popup):
    """The ObjidSelectionDialog class enables selecting specific CropObjects
    through typing their `objid`."""
    text = StringProperty('')

    ok_text = StringProperty('OK')
    cancel_text = StringProperty('Cancel')

    __events__ = ('on_ok', 'on_cancel')

    def __init__(self, *args, **kwargs):
        super(ObjidSelectionDialog, self).__init__(*args, **kwargs)
        self.create_bindings()

    def ok(self):
        self.dispatch('on_ok')
        self.dismiss()

    def cancel(self):
        self.dispatch('on_cancel')
        self.dismiss()

    def on_ok(self):
        # This is the "working" method.
        self.do_objid_selection()

    def on_cancel(self):
        self.dismiss()

    def dismiss(self, *largs, **kwargs):
        self.remove_bindings()
        super(ObjidSelectionDialog, self).dismiss()

    def create_bindings(self):
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)

    def remove_bindings(self):
        Window.unbind(on_key_down=self.on_key_down)
        Window.unbind(on_key_up=self.on_key_up)

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        # Should control enter to confirm/escape to cancel
        dispatch_key = keypress_to_dispatch_key(key, scancode, codepoint, modifier)

        logging.info('ObjidSelectionDialog: Handling keypress: {0}'.format(dispatch_key))
        is_handled = self.handle_dispatch_key(dispatch_key)

        # Don't let the event propagate through the dialog.
        return True

    def handle_dispatch_key(self, dispatch_key):
        """Does the "heavy lifting" in keyboard controls: responds to a dispatch key.

        Decoupling this into a separate method facillitates giving commands to
        the ListView programmatically, not just through user input,
        and this way makes automation easier.

        :param dispatch_key: A string of the form e.g. ``109+alt,shift``: the ``key``
            number, ``+``, and comma-separated modifiers.

        :returns: True if the dispatch key got handled, False if there is
            no response defined for the given dispatch key.
        """

        if dispatch_key == '13':  # Enter
            logging.info('Confirming MLClassSelectionDialog!')
            self.ok()

        elif dispatch_key == '27':  # Escape
            logging.info('Cancelling MLClassSelectionDialog!')
            self.cancel()

        #elif dispatch_key == '9':  # Tab
        #    pass

        # Special keys are handled separately in the TextInput, so
        # they would get caught by the "return True". We need to call
        # their operations explicitly.
        elif dispatch_key == '8':  # Backspace
            self.ids['text_input'].do_backspace()

        elif dispatch_key == '9':  # Tab
            # Process common prefix
            lcp = self._longest_common_prefix
            infix = lcp[len(self.text):]
            logging.info('MLClassSelectionDialog: Found LCP {0}, inf {1}'
                         ''.format(lcp, infix))
            self.ids['text_input'].text = self.text + infix

        else:
            return False

        return True

    def on_key_up(self, window, key, scancode, *args, **kwargs):
        return False

    ######################################################
    # The objid selection behavior
    def do_objid_selection(self):
        objids = map(int, re.split('\W+', self.text))
        view = App.get_running_app().cropobject_list_renderer.view
        available_objids = frozenset(App.get_running_app().annot_model.cropobjects.keys())
        cropobject_views = [view.get_cropobject_view(objid) for objid in objids
                            if objid in available_objids]
        view.unselect_all()
        for v in cropobject_views:
            if not v.is_selected:
                v.dispatch('on_release')