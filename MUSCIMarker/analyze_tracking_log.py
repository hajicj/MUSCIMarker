#!/usr/bin/env python
"""This is a script that performs a quick and dirty analysis
of a MUSCIMarker event log.

What we want to know:

* Number of hours worked
* Speed: how much was done in total?
* Densities: frequency of events (calls) per minute/hour

* Clearly distinguish between user actions and internal tracked actions.

Visualizations:

* Timing visualization

Also, convert to CSV, to make it grep-able? First: fixed-name cols,
then: args dict, formatted as key=value,key=value

"""
from __future__ import print_function, unicode_literals
import argparse
import codecs
import collections
import json
import logging

import itertools
import os

import io
import numpy
import time

import matplotlib.pyplot as plt
import operator

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."



def freqdict(l, sort=True):
    out = collections.defaultdict(int)
    for item in l:
        out[item] += 1
    if sort:
        s_out = collections.OrderedDict()
        for k, v in sorted(out.items(), key=operator.itemgetter(1), reverse=True):
            s_out[k] = v
        out = s_out
    return out


##############################################################################


def logs_from_package(package):
    """Collects all log file names (with complete paths) from the given package.

    :param package: Path to the annotations package.

    :return: List of filenames (full paths).
    """
    logging.info('Collecting log files from package {0}'.format(package))
    if not os.path.isdir(package):
        raise OSError('Package {0} not found!'.format(package))
    log_path = os.path.join(package, 'annotation_logs')
    if not os.path.isdir(log_path):
        raise ValueError('Package {0}: annotation_logs not found, probably not a package.'
                         ''.format(package))
    # Collect all log days
    log_days = os.listdir(log_path)
    log_files = []
    for day in log_days:
        if day.startswith('.'):
            continue
        day_log_path = os.path.join(log_path, day)
        day_log_files = [os.path.join(day_log_path, l)
                         for l in os.listdir(day_log_path)]
        log_files += day_log_files
    logging.info('In package {0}: found {1} log files.'
                 ''.format(package, len(log_files)))
    return log_files


def try_correct_crashed_json(fname):
    """Attempts to correct an incomplete JSON list file: if MUSCIMarker
    crashed, the items list would not get correctly closed. We attempt
    to remove the last comma and add a closing bracket (`]`) on a new
    line instead, and return the object as a (unicode) string.

    >>> json = '''
    ... [
    ...   {'something': 'this', 'something': 'that'},'''

    """
    with open(fname, 'r') as hdl:
        lines = [l.rstrip() for l in hdl]
    if lines[-1][-1] == ',':
        logging.info('Correcting JSON: found hanging comma!')
        lines[-1] = lines[-1][:-1]
        lines.append(']')
        return '\n'.join(lines)

    else:
        logging.info('No hanging comma, cannot deal with this situation.')
        return None


def unique_logs(event_logs):
    """Checks that the event logs are unique using the start event
    timestamp. Returns a list of unique event logs. If two have the same
    timestamp, the first one is used."""
    unique = collections.OrderedDict()
    for l in event_logs:
        init_event = l[0]
        if '-time-' not in init_event:
            raise ValueError('Got a non-event log JSON list! Supposed init event: {0}'
                             ''.format(init_event))
        init_time  = init_event['-time-']
        if init_time in unique:
            logging.warn('Found non-unique event log with timestamp {0} ({1} events)!'
                         ' Using first ({2} events).'
                         ''.format(init_time, len(l), len(unique[init_time])))
        else:
            unique[init_time] = l
    return unique.values()


##############################################################################
# Visualization

def events_by_time_units(events, seconds_per_unit=60):
    """Puts the events into bins that correspond to equally spaced
    intervals of time. The length of time covered by one bin is
    given by seconds_per_unit."""
    # Get first event time
    start_time = min([float(e['-time-']) for e in events])

    # The events do not have to come in-order
    bins = collections.defaultdict(list)
    for e in events:
        t = float(e['-time-'])
        n_bin = int(t - start_time) / int(seconds_per_unit)
        bins[n_bin].append(e)

    return bins


def plot_events_by_time(events, type_key='-fn-'):
    """Simple scatterplot visualization.

    All events are expected to have a -fn- component."""
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


def format_as_timeflow_csv(events, delimiter='\t'):
    """There is a cool offline visualization tool caled TimeFlow,
    which has a timeline app. It needs a pretty specific CSV format
    to work, though."""
    # What we need:
    #  - ID
    #  - Date (human?)
    #  - The common fields:
    min_second = int(min([float(e['-time-']) for e in events]))

    def format_date(e):
        # return '-'.join(reversed(time_human.replace(':', '-').split('__')))
        # time_human = e['-time-human-']
        time = float(e['-time-'])
        return unicode(int(time) - min_second)

    # Collect all events that are in the data.
    event_fields = freqdict(list(itertools.chain(*[e.keys() for e in events])))
    output_fields = ['ID', 'Date'] + event_fields.keys()
    n_fields = len(output_fields)

    field2idx = {f: i+2 for i, f in enumerate(event_fields.keys())}
    event_table = [['' for _ in xrange(n_fields)] for _ in events]
    for i, e in enumerate(events):
        event_table[i][0] = unicode(i)
        event_table[i][1] = format_date(e)#format_date(e['-time-human-'])
        for k, v in e.iteritems():
            event_table[i][field2idx[k]] = v

    # Add labels to event table to get the complete data
    # that should be formatted as TSV
    output_data = [output_fields] + event_table
    output_lines = ['\t'.join(row) for row in output_data]
    output_string = '\n'.join(output_lines)
    return output_string


##############################################################################


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, add_help=True,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-i', '--inputs', nargs='+', action='store',
                        help='Log files to be analyzed.')
    parser.add_argument('-p', '--package', action='store',
                        help='Annotation package. If set, will pull'
                             ' all log files in the package.')
    parser.add_argument('-a', '--annotator', action='store',
                        help='Annotator. If set, will pull all log files'
                             ' for the given person.')

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Turn on INFO messages.')
    parser.add_argument('--debug', action='store_true',
                        help='Turn on DEBUG messages.')

    return parser


def main(args):
    logging.info('Starting main...')
    _start_time = time.clock()

    if args.package is not None:
        package = args.package
        log_files = logs_from_package(package)
        args.input = log_files

    log_data_per_file = []
    for input_file in args.input:
        if not os.path.isfile(input_file):
            raise ValueError('Log file {0} not found!'.format(input_file))

        current_log_data = []

        with codecs.open(input_file, 'r', 'utf-8') as hdl:
            try:
                current_log_data = json.load(hdl)

            except ValueError:
                logging.warn('Could not parse JSON file {0}'.format(input_file))
                logging.info('Attempting to correct file.')
                corrected = try_correct_crashed_json(input_file)
                if corrected is not None:
                    logging.warn('Attempting to parse corrected JSON.')
                    try:
                        current_log_data = json.loads(corrected)
                    except ValueError:
                        logging.warn('Could not even parse corrected JSON, skipping file.')
                        raise
                    logging.warn('Success!')
                else:
                    logging.warn('Unable to correct JSON, skipping file.')

        log_data_per_file.append(current_log_data)

    logging.info('Checking logs for uniqueness. Started with {0} log files.'
                 ''.format(len(log_data_per_file)))
    log_data_per_file = unique_logs(log_data_per_file)
    logging.info('After uniqueness check: {0} logs left.'.format(len(log_data_per_file)))

    log_data = [e for e in itertools.chain(*log_data_per_file)]


    logging.info('Parsed {0} data items.'.format(len(log_data)))
    # Your code goes here
    # raise NotImplementedError()

    # Frequency by -fn-:
    freq_by_fn = freqdict([l.get('-fn-', None) for l in log_data])

    by_minute = events_by_time_units(log_data)
    by_minute_freq = {k: len(v) for k, v in by_minute.items()}
    n_minutes = len(by_minute)
    print('# minutes worked: {0}'.format(n_minutes))
    print('Avg. events per minute: {0}'.format(float(len(log_data)) / n_minutes))

    _end_time = time.clock()
    logging.info('analyze_tracking_log.py done in {0:.3f} s'.format(_end_time - _start_time))


##############################################################################


if __name__ == '__main__':
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    if args.debug:
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

    main(args)
