#!/usr/bin/env python
"""This is a script that..."""
from __future__ import print_function, unicode_literals
import argparse
import json
import logging
import os
import time

from kivy.app import App
from kivy.uix.label import Label

from MUSCIMarkerApp import MUSCIMarkerApp

import kivy
kivy.require('1.9.1')

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


##############################################################################


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, add_help=True,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Turn on INFO messages.')
    parser.add_argument('--debug', action='store_true',
                        help='Turn on DEBUG messages.')
    #
    # parser.add_argument('--hello', action='store_true',
    #                     help='If set, runs a Hello World mini-app instead.')

    parser.add_argument('-w', '--writer', type=int, default=1,
                        help='Which writer?')
    parser.add_argument('-n', '--number', type=int, default=1,
                        help='Which image?')
    parser.add_argument('-r', '--root',
                        help='CVC-MUSCIMA root dir')

    return parser

class MiniApp(App):
    def build(self):
        return Label(text='hello world')


def main(args):
    logging.info('Starting main...')
    _start_time = time.clock()

    # Your code goes here
    app = MUSCIMarkerApp()
    #app = MiniApp()   ### DEBUGGING RECORDER MODULE
    app.run()

    _end_time = time.clock()
    logging.info('MUSCIMan done in {0:.3f} s'.format(_end_time - _start_time))


if __name__ == '__main__':
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    if args.debug:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

    main(args)
