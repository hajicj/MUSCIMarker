"""This module implements tracking annotator activity.
It is separate from Kivy's logging, because logging is meant
for the actions of the app, debugging, etc. -- tracking will
be cleaner to implement separately.

The basic way of tracking is just to decorate a function or method
with a ``@track`` decorator:

>>> @track
>>> def my_fun(arg1, arg2, kwarg1='something'):
...     print(arg1, arg2, kwarg1)
>>> my_fun('foo', 'bar', kwarg1='baz')

"""
from __future__ import print_function, unicode_literals

import codecs
import collections
import datetime
import inspect
import json
import logging
import sys
import time

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


class DefaultTracker(object):
    """...
    Tracker is a class. Set the class attribute `output_file`
    to point tracking to the given location. If None, logs to stdout.
    """
    output_file = None
    _hdl = None

    FUNCTION_NAME_KEY = '-fn-'
    COMMENT_KEY = '-comment-'

    @classmethod
    def get_initial_message_data(cls):
        d = cls.get_default_message_data()
        d['is_start'] = True
        return d

    @classmethod
    def get_final_message_data(cls):
        d = cls.get_default_message_data()
        d['is_end'] = True
        return d

    @classmethod
    def get_default_message_data(cls):
        """The message data that always gets tracked;
        timestamp, etc."""
        t = time.time()
        dt = datetime.datetime.fromtimestamp(t)
        human_time = cls.format_timestamp(dt)
        d = collections.OrderedDict()
        d['time'] = t,
        d['human_time'] = human_time
        return d

    @staticmethod
    def format_timestamp(now):
        return '{:%Y-%m-%d__%H:%M:%S}'.format(now)


    @staticmethod
    def format_message_data(message_data):
        """Converts the given dictionary into a string representation
        that will get written into the tracker file."""
        return json.dumps(message_data) + '\n'

    @classmethod
    def is_open(cls):
        return cls._hdl is not None

    @classmethod
    def open(cls):
        if cls.output_file is not None:
            cls._hdl = codecs.open(cls.output_file, 'a', 'utf-8')
        else:
            cls._hdl = sys.stdout
        cls.write_message_data(cls.get_initial_message_data())

    @classmethod
    def ensure_open(cls):
        if not cls.is_open():
            cls.open()

    @classmethod
    def close(cls):
        cls.write_message_data(cls.get_final_message_data())
        cls._hdl.close()

    @classmethod
    def ensure_closed(cls):
        if cls.is_open():
            cls.close()

    @classmethod
    def write_message_data(cls, message_data):
        # msg_string = cls.format_message_data(message_data)
        cls.ensure_open()
        message = cls.format_message_data(message_data=message_data)
        cls._hdl.write(message)


def track(the_fn, track_names=None, fn_name=None, comment=None,
          tclass=DefaultTracker):
    """Decorator for events that should be tracked.

    :type track_names: list
    :param track_names: The names of arguments to the function
        that will be included in the tracking message. If this
        list is None, then all arguments will be tracked. (If
        you do not want to track any argument, supply an empty list.)
    """
    # Unnamed args are a bit tricky.
    _fn_args, _, _, _ = inspect.getargspec(the_fn)
    if track_names is None:
        track_names = _fn_args

    def _tracking_wrapper(*args, **kwargs):
        message_data = collections.OrderedDict()
        message_data.update(tclass.get_default_message_data())

        # Add function name to message data
        fn_key = tclass.FUNCTION_NAME_KEY
        if fn_name is None:
            message_data[fn_key] = the_fn.__name__
        else:
            message_data[fn_key] = fn_name

        # Unnamed args are a bit tricky.
        _args, _varargs, _keywords, _defaults = inspect.getargspec(the_fn)

        # Defaults are for the last D _args
        _defaults_argvalues = {a: d
                               for a, d in zip(_args[-len(_defaults):], _defaults)}
        # *args automatically gets bound to the first A _args
        _supplied_argvalues = {a: v for a, v in zip(_args[:len(args)], args)}
        for key in track_names:
            # Named args are easy to get
            if key in kwargs:
                message_data[key] = kwargs[key]

            # Unnamed args are a bit trickier
            # Maybe we got the arg
            elif key in _supplied_argvalues:
                message_data[key] = _supplied_argvalues[key]
            # There may be a default value
            elif key in _defaults_argvalues:
                message_data[key] = _defaults_argvalues[key]

        # Add comment, if applicable
        if comment is not None:
            message_data[tclass.COMMENT_KEY] = comment

        tclass.write_message_data(message_data)
        retval = the_fn(*args, **kwargs)
        return retval

    return _tracking_wrapper


