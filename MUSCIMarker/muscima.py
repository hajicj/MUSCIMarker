"""This module implements tools for loading the CVC-MUSCIMA dataset.
It does NOT work with CropObjects and MLClasses; see `io.py` for these."""
from __future__ import print_function, unicode_literals
import logging
import os

import cv2

logger = logging.getLogger(__name__)

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."

if 'CVC_MUSCIMA_ROOT' in os.environ:
    CVC_MUSCIMA_ROOT = os.environ['CVC_MUSCIMA_ROOT']
else:
    CVC_MUSCIMA_ROOT = os.path.join('/Users', 'hajicj', 'data', 'CVC-MUSCIMA')

CVC_MUSCIMA_PRINTED = os.path.join(CVC_MUSCIMA_ROOT, 'printed')
CVC_MUSCIMA_HANDWRITTEN = os.path.join(CVC_MUSCIMA_ROOT, 'handwritten')

CVC_MUSCIMA_DISTORTIONS = [
    'curvature',
    'ideal',
    'interrupted',
    'kanungo',
    'rotated',
    'staffline-thickness-variation-v1',
    'staffline-thickness-variation-v2',
    'staffline-y-variation-v1',
    'staffline-y-variation-v2',
    'thickness-ratio',
    'typeset-emulation',
    'whitespeckles',
]

CVC_MUSCIMA_STAFFONLY_SUBDIR = 'gt'
CVC_MUSCIMA_SYMBOLS_SUBDIR = 'symbol'
CVC_MUSCIMA_FULL_SUBDIR = 'image'

#####################################################
# Utility functions for name/writer conversions


def cvc_muscima_number2printed(n, suffix='png'):
    if (n < 1) or (n > 20):
        raise ValueError('Invalid MUSCIMA score number {0}.'
                         ' Valid only between 1 and 20.'.format(n))
    if n < 10:
        return 'F' + '0' + str(n) + '.' + suffix
    else:
        return 'F' + str(n) + '.' + suffix


def cvc_muscima_number2handwritten(n):
    if (n < 1) or (n > 20):
        raise ValueError('Invalid MUSCIMA score number {0}.'
                         ' Valid only between 1 and 20.'.format(n))
    if n < 10:
        return 'p0' + '0' + str(n) + '.png'
    else:
        return 'p0' + str(n) + '.png'


def cvc_muscima_number2writer(n):
    if (n < 1) or (n > 50):
        raise ValueError('Invalid MUSCIMA writer number {0}.'
                         ' Valid only between 1 and 50.'.format(n))
    if n < 10:
        return 'w-0' + str(n)
    else:
        return 'w-' + str(n)


########################################################
# Loading MUSCIMA images


class MUSCImage(object):
    """The class to access one MUSCIMA score by a writer in its various forms:

    * Full
    * No staves
    * Staves only
    * Printed form (full only)

    >>> img = MUSCImage(number=10, writer=32, distortion='curvature')
    >>> p = img.printed
    >>> f = img.full
    >>> gt = img.staff_only
    >>> s = img.symbols

    Over various writers and the printed version, the MUSCImages are
    aggregated by MUScore.
    """

    def __init__(self, number, writer, root=CVC_MUSCIMA_ROOT,
                 distortion='ideal',
                 bounding_box=None,
                 mask=None):
        """Initialize the image paths.

        :param number: between 1 and 20 (inclusive).

        :param writer: between 1 and 50 (inclusive).

        :param root: The path to the CVC-MUSCIMA root.

        :param distortion: The type of distortion applied. By default,
            use the non-distorted images.

        :param bounding_box: Specifies the crop of the given MUSCImage.
            If None, will return the full image.

        :param mask: False pixels will be set to zero when outputting the image.
            The shape of the mask should be the same as the shape of the image,
            not the bounding box.
        """
        if distortion not in CVC_MUSCIMA_DISTORTIONS:
            raise ValueError('Invalid distortion: {0}'.format(distortion))

        # Printed score: determine whether it has a *.png or *.tiff suffix.
        printed_fname = cvc_muscima_number2printed(number, suffix='png')
        if not os.path.isfile(os.path.join(CVC_MUSCIMA_PRINTED, printed_fname)):
            printed_fname = cvc_muscima_number2printed(number, suffix='tiff')

        self.printed_path = os.path.join(CVC_MUSCIMA_PRINTED, printed_fname)
        self._printed = None

        # Handwritten root
        writer_dirname = cvc_muscima_number2writer(writer)
        hw_fname = cvc_muscima_number2handwritten(number)
        hw_root = os.path.join(CVC_MUSCIMA_HANDWRITTEN, distortion, writer_dirname)

        self._staff_only = None
        self.staff_only_path = os.path.join(hw_root, CVC_MUSCIMA_STAFFONLY_SUBDIR,
                                            hw_fname)

        self._symbols = None
        self.symbols_path = os.path.join(hw_root, CVC_MUSCIMA_SYMBOLS_SUBDIR,
                                         hw_fname)

        self._full = None
        self.full_path = os.path.join(hw_root, CVC_MUSCIMA_FULL_SUBDIR,
                                      hw_fname)

        self._root = root
        self.writer = writer
        self.number = number
        self.distortion = distortion

        self._bounding_box = bounding_box
        self._mask = mask

    def __str__(self):
        return 'CVC-MUSCIMA_{0}.{1}-{2}'.format(self.writer,
                                                self.number,
                                                self.distortion)

    @property
    def printed(self):
        return self._image_getter('printed')

    @property
    def full(self):
        return self._image_getter('full')

    @property
    def staff_only(self):
        return self._image_getter('staff_only')

    @property
    def symbols(self):
        return self._image_getter('symbols')

    def _image_getter(self, varname):
        container_name = '_' + varname
        if not hasattr(self, container_name):
            raise AttributeError('Cannot get image {0}, container variable {1}'
                                 ' not defined.'.format(varname, container_name))
        container = getattr(self, container_name)

        # If the variable has already been set:
        if container is not None:
            if self._mask is not None:
                container = self._mask * container
            if self.bounding_box is None:
                return container
            else:
                t, l, b, r = self.bounding_box
                return container[t:b, l:r]

        path_name = varname + '_path'
        if not hasattr(self, path_name):
            raise AttributeError('Cannot load image {0}, container variable is'
                                 ' not initialized and path variable {1}'
                                 ' is not defined.'.format(varname, path_name))
        path = getattr(self, path_name)
        if path is None:
            raise ValueError('Cannot load image {0} from path, path variable'
                             ' {1} is not initialized.'.format(varname, path_name))
        img = self._load_grayscale_image(path)
        setattr(self, container_name, img)

        return self._image_getter(varname)

    @staticmethod
    def _load_grayscale_image(path):
        img = cv2.imread(path, flags=cv2.IMREAD_UNCHANGED)
        return img

    #####################################
    # MUSCImageCrop functionality

    @property
    def bounding_box(self):
        return self._bounding_box

    @bounding_box.setter
    def bounding_box(self, value):
        raise ValueError('Cannot set bounding box!')

    @property
    def width(self):
        bbox = self.bounding_box
        if bbox is None:
            return self.full.shape[1]
        else:
            return bbox[3] - bbox[1]

    @property
    def height(self):
        bbox = self.bounding_box
        if bbox is None:
            return self.full.shape[0]
        else:
            return bbox[2] - bbox[0]

    @property
    def shape(self):
        if self.bounding_box is None:
            return self.full.shape
        else:
            shape = list(self.full.shape)
            shape[0] = self.bounding_box[2] - self.bounding_box[0]
            shape[1] = self.bounding_box[3] - self.bounding_box[1]
            shape = tuple(shape)
            return shape

    def symbol_bboxes(self, with_labels=False):
        """Extracts bounding boxes from symbols image."""
        cc, labels = cv2.connectedComponents(self.symbols)
        bboxes = {}
        for x, row in enumerate(labels):
            for y, l in enumerate(row):
                if l not in bboxes:
                    bboxes[l] = [x, y, x+1, y+1]
                else:
                    box = bboxes[l]
                    if x < box[0]:
                        box[0] = x
                    elif x + 1 > box[2]:
                        box[2] = x + 1
                    if y < box[1]:
                        box[1] = y
                    elif y + 1 > box[3]:
                        box[3] = y + 1

        if with_labels:
            return bboxes, labels
        else:
            return bboxes

    def symbol_crops(self):
        """Extract the cropped symbols from the symbols image."""
        bboxes = self.symbol_bboxes()
        s = self.symbols
        crops = []
        for t, l, b, r in bboxes.values():
            crops.append(s[t:b,l:r])
        return crops

    def crop(self, top, left, bottom, right, mask=None):
        """Create a MUSCImage with the content of this MUSCImage
        cropped to the specified coordinates.

        Cropping an image that has already been cropped uses
        coordinates relative to the crop: the MUSCImage object truly
        represents the area within the bounding box only, so cropping
        at (10, 10, 100, 200) should be interpreted with respect
        to the top left corner of the current bounding box: 10 down from
        top, 10 right from left, 100 down from top, 200 right from left.
        """
        if self.bounding_box is not None:
            top += self.bounding_box[0]
            left += self.bounding_box[1]
            bottom += self.bounding_box[0]
            right += self.bounding_box[1]

        if mask is None:
            mask = self._mask

        output = MUSCImage(self.number,
                           self.writer,
                           self._root,
                           self.distortion,
                           bounding_box=(top, left, bottom, right),
                           mask=mask)

        return output

    def contains_bbox(self, top, left, bottom, right):
        """Given a bounding box from the original MUSCImage,
        checks whether the given MUSCImage contains the area described by bounding box.
        Use this when verifying that a given CropObject is inside the given MUSCImage.
        """
        if self.bounding_box is None:
            if (top < 0) or (bottom > self.shape[0]):
                return False
            if (left < 0) or (right > self.shape[1]):
                return False
        else:
            t, l, b, r = self.bounding_box
            if (top < t) or (left < l) or (bottom > b) or (right > r):
                return False
        return True

