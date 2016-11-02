#!/usr/bin/env python
"""This is a script that performs a quick and dirty analysis
of a MUSCIMarker event log.

What we want to know:

* Frequency of events (calls)

Visualizations:

* Timing visualization

Also, convert to CSV, to make it grep-able? First: fixed-name cols,
then: args dict, formatted as key=value,key=value

"""
from __future__ import print_function, unicode_literals
import argparse
import codecs
import json
import logging
import numpy
import time

import matplotlib.pyplot as plt

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


def plot_events_by_time(events, type_key='-fn-'):
    """All events are expected to have a -fn- component."""
    fns = [e['-fn-'] for e in events]
    # Assign numbers to tracked fns
    fns_by_freq = {f: len([e for e in fns if e == f]) for f in set(fns)}
    fn_dict = {f: i for i, f in enumerate(sorted(fns_by_freq.keys(),
                                          reverse=True,
                                          key=lambda k: fns_by_freq[k]))}

    min_time = float(events[0]['-time-'])

    dataset = numpy.zeros((len(events), 2))
    for i, e in enumerate(events):
        dataset[i][0] = float(e['-time-']) - min_time
        dataset[i][1] = fn_dict[e[type_key]]

    # Now visualize
    plt.scatter(dataset[:,0], dataset[:,1])


##############################################################################


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, add_help=True,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-i', '--input', action='store',
                        help='Log file to be analyzed.')

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Turn on INFO messages.')
    parser.add_argument('--debug', action='store_true',
                        help='Turn on DEBUG messages.')

    return parser


def main(args):
    logging.info('Starting main...')
    _start_time = time.clock()

    with codecs.open(args.input, 'r', 'utf-8') as hdl:
        log_data = json.load(hdl)

    logging.info('Parsed {0} data items.'.format(len(log_data)))
    # Your code goes here
    # raise NotImplementedError()

    _end_time = time.clock()
    logging.info('analyze_tracking_log.py done in {0:.3f} s'.format(_end_time - _start_time))


if __name__ == '__main__':
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    if args.debug:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

    main(args)
