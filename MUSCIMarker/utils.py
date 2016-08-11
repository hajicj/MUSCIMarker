"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import codecs
import logging
import os

from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup

import mhr.muscima as mm

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."

##############################################################################
# Useful keyboard key/scancode to string conversions.
#
key2codepoint = {
    8: 'backspace',
    27: 'escape',
}

scancode2codepoint = {
    42: 'backspace',
    41: 'escape',
}

##############################################################################
# File choosing.
# Implementation derived from example at:
# https://kivy.org/docs/api-kivy.uix.filechooser.html


class FileLoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)
    default_path = StringProperty(mm.MFF_MUSCIMA_SYMBOLIC)


class FileNameLoader(FloatLayout):
    """Generic view to use for file loading dialogues.
    Bind to its ``filename`` property to do something useful
    in the controller (App).

    The ``force_change`` property is a workaround for firing
    reload actions even when the file does not change. This is
    by default on, which is useful for debugging but not much more.
    """
    filename = StringProperty('None')

    force_change = BooleanProperty(True)
    '''If set, will change the filename to ``''`` before loading
    the new one, so that all callbacks bound to the filename are fired.
    However, they are fired *twice* this way, which is less than optimal.'''

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self, path=None):
        logging.info('FileNameLoader: Asked for file loading...')
        if path is not None:
            content = FileLoadDialog(load=self.load,
                                     cancel=self.dismiss_popup,
                                     default_path=path)
        else:
            content = FileLoadDialog(load=self.load,
                                     cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.5, 0.8))
        self._popup.open()

    def load(self, path, filename):
        full_filename = os.path.join(path, filename[0])
        if not os.path.exists(full_filename):
            raise ValueError('Selected nonexistent file: {0}'
                             ''.format(full_filename))
        if (self.filename == full_filename) and self.force_change:
            self.filename = ''
        self.filename = full_filename
        self.dismiss_popup()

    def cancel(self):
        self.dismiss_popup()

##############################################################################


class FileSaveDialog(FloatLayout):
    save = ObjectProperty(None)
    cancel = ObjectProperty(None)
    default_path = StringProperty(mm.CVC_MUSCIMA_ROOT)


class FileSaver(FloatLayout):
    to_save = StringProperty()
    overwrite = BooleanProperty(False)
    text_input = StringProperty()

    last_output_path = StringProperty()

    def show_save(self, path=None):
        logging.info('Showing save with path {0}'.format(path))
        if path is not None:
            content = FileSaveDialog(save=self.save,
                                     cancel=self.dismiss_popup,
                                     default_path=path)
        else:
            content = FileSaveDialog(save=self.save,
                                     cancel=self.dismiss_popup)

        self._popup = Popup(title="Save file",
                            content=content,
                            size_hint=(0.5, 0.8))
        self._popup.open()

    def save(self, path, filename):
        output_path = os.path.join(path, filename)
        if os.path.isdir(output_path):
            logging.error('Export: Selected output is a directory! {0}'
                          ''.format(output_path))
            self.dismiss_popup()
        if os.path.isfile(output_path):
            if not self.overwrite:
                logging.error('Export: Selected output exists! {0}'
                              ''.format(output_path))
                self.dismiss_popup()
        with codecs.open(output_path, 'w', 'utf-8') as stream:
            stream.write(str(self.to_save))

        self.last_output_path = output_path
        self.dismiss_popup()

    def dismiss_popup(self):
        self._popup.dismiss()

    def cancel(self):
        self.dismiss_popup()


##############################################################################


def bbox_to_integer_bounds(ftop, fleft, fbottom, fright, to_integer=True):
    """Rounds off the CropObject bounds to the nearest integer
    so that no area is lost (e.g. bottom and right bounds are
    rounded up, top and left bounds are rounded down).

    WARNING: Possible bug?
    """
    top = ftop - (ftop % 1.0)
    left = fleft - (fleft % 1.0)
    bottom = fbottom - (fbottom % 1.0)
    if fbottom % 1.0 != 0:
        bottom += 1.0
    right = fright - (fright % 1.0)
    if fright % 1.0 != 0:
        right += 1.0

    if to_integer:
        top, left, bottom, right = int(top), int(left), int(bottom), int(right)

    return top, left, bottom, right
