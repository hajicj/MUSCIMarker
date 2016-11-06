"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import logging

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.popup import Popup

from utils import keypress_to_dispatch_key

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


mlclass_selection_dialog_kv = '''
<MLClassSelectionDialog@Popup>
    size_hint: None, None
    size: app.root.size[0] * 0.5, app.root.size[1] * 0.2
    pos_hint: {'center_x': 0.5, 'centery_y': 0.5}

    title: 'Select MLClass by typing its name.'

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

Builder.load_string(mlclass_selection_dialog_kv)

class MLClassSelectionDialog(Popup):
    """The MLClassSelectionDialog class allows for keyboard-based
    selection of the current MLClass."""
    text = StringProperty('')

    ok_text = StringProperty('OK')
    cancel_text = StringProperty('Cancel')

    __events__ = ('on_ok', 'on_cancel')

    def __init__(self, *args, **kwargs):
        super(MLClassSelectionDialog, self).__init__(*args, **kwargs)
        self.create_bindings()

    def ok(self):
        self.dispatch('on_ok')
        self.dismiss()

    def cancel(self):
        self.dispatch('on_cancel')
        self.dismiss()

    def on_ok(self):
        #if len(self.available_clsnames) == 0:
        #    return

        name = self.get_current_name()
        if name is None:
            return

        if len(self.available_clsnames) > 1:
            logging.info('MLClassSelectionDialog:'
                         ' More than one name possible: {0},'
                         ' picking: {1}.'
                         ''.format(self.available_clsnames, name))

        App.get_running_app().currently_selected_mlclass_name = name

    def on_cancel(self):
        self.dismiss()

    def dismiss(self, *largs, **kwargs):
        self.remove_bindings()
        super(MLClassSelectionDialog, self).dismiss()

    def on_text(self, instance, pos):
        logging.info('MLClassSelectionDialog: Got an on_text signal!')
        #self.ids['current_name_label'].text = self.get_current_name()
        n = self.get_current_name()
        if n is None:
            pass
            #self.ids['text_input'].suggestion_text = ''
        elif len(pos) >= len(n):
            pass
            # self.ids['text_input'].suggestion_text =
        else:
            self.ids['text_input'].suggestion_text = self.get_current_name()[len(self.text):]

        names = self.currently_available_names
        if len(names) > 5:
            names = names[:5] + ['...']
        name_str = ', '.join(names)
        self.ids['available_names_label'].text = name_str

    ##########################################################################
    # Making it possible to operate the popup with Esc to cancel,
    # Enter to confirm.

    def create_bindings(self):
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)

    def remove_bindings(self):
        Window.unbind(on_key_down=self.on_key_down)
        Window.unbind(on_key_up=self.on_key_up)

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        # Should control enter to confirm/escape to cancel
        dispatch_key = keypress_to_dispatch_key(key, scancode, codepoint, modifier)

        logging.info('MLClassSelectionDialog: Handling keypress: {0}'.format(dispatch_key))

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

        # Do not let the event propagate!
        return True

    def on_key_up(self, window, key, scancode):
        return False

    ##########################################################################
    # The name selection mechanism

    def clsnames_with_prefix(self, prefix):
        return [clsname for clsname in self.available_clsnames
                if clsname.startswith(prefix)]

    @property
    def available_clsnames(self):
        mlclasses_by_name = App.get_running_app().annot_model.mlclasses_by_name
        clsnames = mlclasses_by_name.keys()
        sorted_clsnames = sorted(clsnames, key=lambda n: mlclasses_by_name[n].clsid)
        return sorted_clsnames

    @property
    def currently_available_names(self):
        return self.clsnames_with_prefix(self.text)

    @property
    def _longest_common_prefix(self):
        names = self.currently_available_names
        if len(names) == 0:
            return ''
        if len(names) == 1:
            return names[0]

        pref = ''
        shortest_name_length = min([len(n) for n in names])
        for i in xrange(shortest_name_length):
            pref = names[0][:i+1]
            for n in names[1:]:
                if n[:i+1] != pref:   # Unequal at i-th letter
                    return pref[:-1]

        # Shortest word is at the same time the prefix
        return names[0][:shortest_name_length]

    def get_current_name(self):
        """This is the "clever" part of the name selection mechanism.
        Right now, it just selects the first available name."""
        names = self.currently_available_names
        if len(names) == 0:
            return None

        output = names[0]

        # Exact match has preference
        for n in names:
            if n == self.text:
                output = n

        return output

    ##########################################################################
    # Feedback mechanism

