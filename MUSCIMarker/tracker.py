"""This module implements tracking annotator activity.
It is separate from Kivy's logging, because logging is meant
for the actions of the app, debugging, etc. -- tracking will
be cleaner to implement separately.

The basic way of tracking is just to decorate a function or method
with a ``@Tracker`` decorator:


>>> @Tracker()
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


class DefaultTrackerHandler(object):
    """...
    Tracker is a class. Set the class attribute `output_file`
    to point tracking to the given location. If None, logs to stdout.
    """
    output_file = None
    _hdl = None

    TIME_KEY = '-time-'
    TIME_HUMAN_KEY = '-time-human-'
    FUNCTION_NAME_KEY = '-fn-'
    COMMENT_KEY = '-comment-'
    TRACKER_NAME_KEY = '-tracker-'

    MISSING_VALUE = '=MISSING='

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
        d[cls.TIME_KEY] = t
        d[cls.TIME_HUMAN_KEY] = human_time
        return d

    @staticmethod
    def format_timestamp(now):
        return '{:%Y-%m-%d__%H:%M:%S}'.format(now)


    @staticmethod
    def format_message_data(message_data, final=False):
        """Converts the given dictionary into a string representation
        that will get written into the tracker file."""
        _unicode_message_data = {unicode(k): unicode(v)
                                 for k, v in message_data.iteritems()}
        if final is True:
            return json.dumps(_unicode_message_data) + '\n'
        else:
            return json.dumps(_unicode_message_data) + ',\n'

    @classmethod
    def is_open(cls):
        return cls._hdl is not None

    @classmethod
    def open(cls):
        if cls.output_file is not None:
            cls._hdl = codecs.open(cls.output_file, 'a', 'utf-8')
        else:
            cls._hdl = sys.stdout
        cls._hdl.write('[\n')  # List of events
        cls.write_message_data(cls.get_initial_message_data())

    @classmethod
    def ensure_open(cls):
        if not cls.is_open():
            cls.open()

    @classmethod
    def close(cls):
        cls.write_message_data(cls.get_final_message_data(), final=True)
        cls._hdl.write(']\n')
        cls._hdl.close()

    @classmethod
    def ensure_closed(cls):
        if cls.is_open():
            cls.close()

    @classmethod
    def write_message_data(cls, message_data, final=False):
        # msg_string = cls.format_message_data(message_data)
        cls.ensure_open()
        message = cls.format_message_data(message_data=message_data, final=final)
        cls._hdl.write('\t' + message)


class Tracker(object):
    def __init__(self, track_names=None, transformations=None,
                 fn_name=None, comment=None, tracker_name=None,
                 handler=DefaultTrackerHandler):
        """Decorator for events that should be tracked.

        Make sure that whatever data you track is JSON-serializable.

        :type track_names: list
        :param track_names: The names of arguments to the function
            that will be included in the tracking message. If this
            list is None, then all arguments will be tracked. (If
            you do not want to track any argument, supply an empty list.)

            Ignores `self` by default unless you add it explicitly. However,
            in Kivy, no Widget or anything derived from an EventDispatcher
            is serializable, so you should really provide a transformer
            for `self`.

        :type transformations: dict
        :param transformations: A dict of lists of callables. Keys are
            names (present in track_names), values are lists of callables
            that get called with the given tracked entity as the first
            argument. (Use functools.partial for fancier input.)
            This serves to enable things like extracting a property
            of an object. The transformer is expected to return
            a `(key, value)` pair that gets then used in the message
            data. For example, you can make an `add_cropobject` Tracker with
            `transformations={'cropobject': lambda c: ('objid', c.objid)}`.

            If transformations are supplied for an argument to the tracked
            function, the argument itself is *not* logged. To do that,
            supply a `lambda x: ('name', x)` transform.

        :type fn_name: str
        :param fn_name: How the decorated function should be named
            in the tracking log. Uses the key from
            `handler.FUNCTION_NAME_KEY`.

        :type comment: str
        :param comment: Add this value to each call as a comment. Will
            be the same comment for each decorated function call.

        :type tracker_name: str
        :param tracker_name: Add this value to each call under the
            `handler.TRACKER_NAME_KEY` key. Allows differentiating
            e.g. tool usage trackers from recovery trackers.

        :type handler: class
        :param class: A TrackerHandler class that is responsible for
            writing the messages.
        """
        self.track_names = track_names
        self.transformations = dict()
        if transformations is not None:
            self.transformations = transformations

        self.fn_name = fn_name
        self.comment = comment
        self.tracker_name = tracker_name

        self.handler = handler

    def __call__(self, the_fn):
        """Construct the actual decorated function.
        """
        # Unnamed args are a bit tricky.
        _fn_args, _, _, _ = inspect.getargspec(the_fn)
        if self.track_names is None:
            # We need to keep 'self' away from tracked names unless
            # the tracker is explicitly asked to track self.
            track_names = [a for a in _fn_args if a != 'self']
        else:
            track_names = self.track_names

        def _tracking_wrapper(*args, **kwargs):
            message_data = collections.OrderedDict()
            message_data.update(self.handler.get_default_message_data())

            # Add function name to message data
            fn_key = self.handler.FUNCTION_NAME_KEY
            if self.fn_name is None:
                message_data[fn_key] = the_fn.__name__
            else:
                message_data[fn_key] = self.fn_name

            # if self.tracker_name is not None:
            tracker_name_key = self.handler.TRACKER_NAME_KEY
            message_data[tracker_name_key] = self.tracker_name

            # Unnamed args are a bit tricky.
            _args, _varargs, _keywords, _defaults = inspect.getargspec(the_fn)

            # Defaults are for the last D _args
            _defaults_argvalues = {}
            if _defaults is not None:
                _defaults_argvalues = {a: d
                                       for a, d in zip(_args[-len(_defaults):], _defaults)}
            # *args automatically gets bound to the first A _args
            _supplied_argvalues = {a: v for a, v in zip(_args[:len(args)], args)}
            for key in track_names:

                value = self.handler.MISSING_VALUE

                # In case we are tracking a method
                if key == 'self':
                    if 'self' in track_names:
                        value = _supplied_argvalues[key]
                    else:
                        continue

                # Named args are easy to get
                if key in kwargs:
                    value = kwargs[key]

                # Unnamed args are a bit trickier
                # Maybe we got the arg
                elif key in _supplied_argvalues:
                    value = _supplied_argvalues[key]
                # There may be a default value
                elif key in _defaults_argvalues:
                    value = _defaults_argvalues[key]

                if (key in self.transformations) and (value != self.handler.MISSING_VALUE):
                    for transform in self.transformations[key]:
                        t_key, t_value = transform(value)
                        message_data[t_key] = t_value
                else:
                    message_data[key] = value

            # Add comment, if applicable
            if self.comment is not None:
                message_data[self.handler.COMMENT_KEY] = self.comment

            self.handler.write_message_data(message_data)
            retval = the_fn(*args, **kwargs)
            return retval

        return _tracking_wrapper


