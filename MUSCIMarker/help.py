"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import collections
import logging

from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


help_kv = '''
<HelpKey@Label>
    font_size: '12dp'
    halign: 'right'
    valign: 'top'
    size_hint_x: None
    width: '94dp'
    bold: True
    # text_size: self.size
    # background_color: [0.2, 0, 0, 0.1]

<HelpValue@Label>
    font_size: '12dp'
    halign: 'left'
    size_hint_y: None
    valign: 'top'
    # text_size: self.size

<HelpGroupHeading@Label>
    height: '32dp'
    size_hint_y: None
    valign: 'bottom'
    halign: 'center'
    text_size: self.size

<Help@Popup>
    size_hint_x: None
    width: app.root.size[0] * 0.7
    size_hint_y: None
    height: app.root.size[1] * 0.85
    pos_hint: {'center_x': 0.5, 'center_y': 0.5}

    title: 'MUSCIMarker Help'

    GridLayout:
        id: content
        cols: 1
        spacing: [0, '12dp']

'''

Builder.load_string(help_kv)
MUSCIMARKER_AVAILABLE_KEYBOARD_SHORTCUTS = [
    ('Tools', {
        '1, 2, 3, ...': 'Select the 1st (2nd, 3rd...) tool.',
        'Esc': 'Unselect current tool. (Only if no objects selected.)',
    }),
    ('With selection', {
        'Esc': 'Cancel current selection.',
        'Backspace': 'Delete all selected things.',
        'Alt+Backspace': 'Delete all relationships of selected objects.',
        'Ctrl+Shift+c': 'Apply current class to selected objects.',
        'Shift+c': 'Set the selected object class as the current class.',
        'm': 'Merge selection destructively, merged object gets current class.',
        'Shift+m': 'Like \'m\', but the merge does not delete the selection.',
        'i': 'Open object inspection window.',
        'c': 'Open class change spinner(s). [Not recommended.]',
        'Alt+c': 'Open class change dialog.',
        'Alt+h': 'Hide/Show the selected objects\' relationships.',
        'a': 'Add relationship from first to second selected object. [Not recommended.]',
        'd': 'Remove relationship from first to second selected object. [Not recommended.]',
        'p': 'Automatically add all possible relationships among selected objects.',
        'Shift+p': 'Infer relationships among selected objects with a probabilistic parser.',
        'n': 'Automatically add precedence relationships, factored per (monophonic only) staff.',
        'Shift+n': 'Automatically add precedence relationships among all selected objects (monophonic only!).',
        'Alt+Shift+n': 'Add simultaneity relationships between objects that have the same onset.',
        'Alt+Ctrl+Shift+n': 'Remove simultaneity relationships.',
    }),
    ('Without selection', {
        'c': 'Open object class selection dialog.',
        'o': 'Open dialog for selecting objects by their objids.',
        'Alt+h': 'Hide/Show all relationships.',
        'Shift+s': 'Process staffs from individual staffline fragments.',
        'f': 'Infer pitches, durations and onsets.',
        'Shift+f': 'Like q, but also play the result.',
    }),
    ('Validation', {
        'v': 'Check notation graph against syntactic constraints.',
        'Shift+v': '[NOT IMPLEMENTED] Check notation graph like \'v\', but incl. staff checks.',
        'Alt+Shift+t': 'Find objects that are suspiciously sparse.',
        'Alt+Shift+r': 'Find objects that have many unmarked pixels in bounding box.',
        'Alt+Shift+d': 'Find objects that have more than 1 connected component.',
        'Alt+Shift+s': 'Like alt+shift+d, but only finds objects without outlinks.',
        'Alt+Shift+o': 'Find objects that have the same bounding box, but are not attached to each other.',
        'Alt+Shift+q': 'Find objects that are suspiciously small. (Mostly for catching auto-detection errors.)',
    }),
    ('Automation', {
        'Alt+Shift+b': 'Add \'measure_separator\' objects from barlines.',
    }),
]



class HelpKey(Label):
    pass

class HelpValue(Label):
    pass

class HelpGroupHeading(Label):
    pass

class Help(Popup):
    """The Help class displays available MUSCIMarker commands.
    It provides no further actions, just displays the helptext."""
    def __init__(self, *args, **kwargs):
        super(Help, self).__init__(*args, **kwargs)

        for group_name, group in MUSCIMARKER_AVAILABLE_KEYBOARD_SHORTCUTS:
            self.content.add_widget(HelpGroupHeading(text=group_name))
            w = GridLayout(cols=2,
                           spacing=['12dp', 0],
                           size_hint_y=None,
                           height='{0}dp'.format(12 * len(group) + 24))
            k_lines = []
            v_lines = []
            for k, v in list(group.items()):
                k_lines.append(k)
                v_lines.append(v)

            logging.warn('K_lines: {0}, V_lines: {1}'
                         ''.format(len(k_lines), len(v_lines)))

            k_text = '\n'.join(k_lines)
            v_text = '\n'.join(v_lines)

            k_label = HelpKey(text=k_text,
                              size_hint_y=None,
                              height='{0}dp'.format(14 * len(k_lines)))
            w.add_widget(k_label)

            v_label = HelpValue(text=v_text)
            w.add_widget(v_label)

            self.content.add_widget(w)
