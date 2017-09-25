"""This module implements a class that..."""
from __future__ import print_function, unicode_literals

import logging
import os
import pickle
import socket
import uuid

import numpy
import time
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.widget import Widget

from muscima.io import parse_cropobject_list, export_cropobject_list

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


HOST = None   # TODO: replace by config values
PORT = 33555       # TODO: replace by config values


class ObjectDetectionHandler(Widget):
    """The ObjectDetectionHandler class is the interface between MUSCIMarker
    and its CropObjectAnnotatorModel and the ``mhr.omrapp`` client-server
    musical symbol detection setup."""
    input = ObjectProperty(None, allownone=True)
    '''The input of the remote OMR engine should be stored
    here to trigger detection call.'''

    input_bounding_box = ObjectProperty(None, allownone=True)
    '''Remembers the bounding box of the current input, so that
    the positions of detected CropObjects with respect to the input
    image can be derived from it.'''

    result = ObjectProperty(None, allownone=True)
    '''The output of the remote OMR engine is stored here. An external
    method should be bound to this property. The result is a list
    of CropObjects.'''

    tmp_dir = StringProperty()

    def __init__(self, tmp_dir, port=33555, **kwargs):
        super(ObjectDetectionHandler, self).__init__(**kwargs)

        self.tmp_dir = tmp_dir
        self.port = port

        # Load the symbol detection configuration:
        #  - target host
        #  - target port
        #  - temp directory for received raw data

    def on_input(self, instance, pos):
        if pos is not None:
            self.call(pos)

    def call(self, request):

        # Format request for client
        #  (=pickle it, plus pickle-within-pickle for image array)
        f_request = self._format_request(request)

        _rstring = str(uuid.uuid4())
        temp_basename = 'MUSCIMarker.omrapp-request.' + _rstring + '.pkl'
        request_fname = os.path.join(self.tmp_dir, temp_basename)
        with open(request_fname, 'w') as fh:
            pickle.dump(f_request, fh, protocol=0)

        # Send to ObjectDetectionOMRAppClient
        # We didn't want to introduce "mhr" as a dependency,
        # so we wrote our own client for omrapp.

        response_basename = 'MUSCIMarker.omrapp-response.' + _rstring + '.xml'
        response_fname = os.path.join(self.tmp_dir, response_basename)

        client = ObjectDetectionOMRAppClient(host=HOST, port=self.port,
                                             request_file=request_fname,
                                             response_file=response_fname)
        client.call()
        #   ...this happens in ObjectDetectionOMRAppClient...
        # Open socket according to conf
        # Send request to server
        # Collect raw result
        # Close connection

        # Convert raw result (XML) to output representation (CropObjects)
        if not os.path.isfile(response_fname):
            raise OSError('ObjectDetectionHandler: Did not receive'
                          ' response file {0}'.format(response_fname))

        try:
            cropobjects = parse_cropobject_list(response_fname)
            print(export_cropobject_list(cropobjects))
            # Verify that result is valid (re-request on failure?)

        except:
            raise
        finally:
            # Cleanup files.
            logging.info('Cleaning up files.')
            if os.path.isfile(request_fname):
                os.unlink(request_fname)
            if os.path.isfile(response_fname):
                os.unlink(response_fname)

        # Bind output representation to self.result to fire bindings
        #  - Subsequent processing means adding the CropObjects
        #    into the current annotation, in this case.
        #  - This can also trigger auto-parse.
        self.result = cropobjects


    def reset(self):
        self.result = None
        self.input = None
        self.input_bounding_box = None


    def _format_request(self, request):
        f_request = dict()
        for k in request:
            if k == 'image???':
                f_request[k] = self._format_request_image(request[k])
            else:
                f_request[k] = request[k]
        return f_request

    def _format_request_image(self, image):
        return numpy.ndarray.dumps(image)




class ObjectDetectionOMRAppClient(object):
    """Handles the client-side networking for object
    detection. Not a widget!"""
    def __init__(self, host, port, request_file, response_file):
        self.host = host
        self.port = port
        self.request_file = request_file
        self.response_file = response_file

        self.BUFFER_SIZE = 1024

    def call(self):
        logging.info('MUSCIMarker.ObjectDetectionOMRAppClient.run(): starting')
        _start_time = time.clock()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = socket.gethostname()

        s.connect((host, self.port))
        logging.info('ObjectDetectionOMRAppClient.run(): connected to'
                     ' host {0}, port {1}'.format(host, self.port))

        with open(self.request_file, 'rb') as fh:
            data = fh.read(self.BUFFER_SIZE)
            while data:
                s.send(data)
                data = fh.read(self.BUFFER_SIZE)

        # s.send(b"Hello server!")
        s.shutdown(socket.SHUT_WR)

        # Server does its thing now. We wait at s.recv()

        # TODO: Change this to StringIO...
        with open(self.response_file, 'wb') as f:
            logging.info('file opened: {0}'.format(self.response_file))
            while True:
                data = s.recv(self.BUFFER_SIZE)

                if not data:
                    break
                f.write(data)
        f.close()

        logging.info('Successfully got the file')

        s.close()
        logging.info('connection closed')

        del s

        _end_time = time.clock()
        logging.info('MUSCIMarker.ObjectDetectionOMRAppClient.run():'
                     ' done in {0:.3f} s'.format(_end_time - _start_time))
