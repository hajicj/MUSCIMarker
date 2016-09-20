"""This module implements tools for loading the CVC-MUSCIMA and MUSCIMA++
datasets."""
from __future__ import print_function, unicode_literals
import base64
import logging
import os
from os.path import dirname

import cv2
import numpy
from lxml import etree

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

if not 'MFF_MUSCIMA_ROOT' in os.environ:
    MFF_MUSCIMA_ROOT = os.path.join('/Users', 'hajicj', 'mhr', 'MFF-MUSCIMA')
else:
    MFF_MUSCIMA_ROOT = os.environ['MFF_MUSCIMA_ROOT']

MFF_MUSCIMA_SYMBOLIC = os.path.join(MFF_MUSCIMA_ROOT, 'Symbolic')
MFF_MUSCIMA_XML = os.path.join(MFF_MUSCIMA_ROOT, 'XML')


##############################################################################
# Annotations lookup

def available_mlclass_lists(symbolic_root=MFF_MUSCIMA_SYMBOLIC):
    """For simplicity assumes anything in Symbolic/specification
    that ends in *.xml is a mlclasslist.
    """
    spec_dir = os.path.join(symbolic_root, 'specification')
    xml_files = [f for f in os.listdir(spec_dir) if f.endswith('.xml')]
    return xml_files


def available_annotations(symbolic_root=MFF_MUSCIMA_SYMBOLIC):
    """Check which MUSCIMA images have annotations. Currently
    assumes each xml file has a corresponding png file and vice
    versa."""
    data_dir = os.path.join(symbolic_root, 'data')
    xml_files = sorted([f for f in os.listdir(data_dir)
                        if f.endswith('.xml')])
    png_files = sorted([f for f in os.listdir(data_dir)
                        if f.endswith('.png')])

    if len(xml_files) != len(png_files):
        raise ValueError('MFF-MUSCIMA symbolic data: xml and png'
                         ' files do not match.\n\tXML:'
                         ' {0}\n\tPNG: {1}'
                         ''.format(xml_files, png_files))
    return xml_files, png_files


######################################################
# Utility functions for name/writer conversions
_hex_tr = {
    '0': 0,
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
    '8': 8, '9': 9,
    'a': 10, 'b': 11, 'c': 12, 'd': 13, 'e': 14, 'f': 15,
    'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15,
}
def parse_hex(hstr):
    """Convert a hexadecimal number string to integer.

    >>> parse_hex('33')
    51
    >>> parse_hex('abe8')
    44008

    """
    out = 0
    for i, l in enumerate(reversed(hstr)):
        out += (16**i) * _hex_tr[l]
    return out


def hex2rgb(hstr):
    """Parse a hex-coded color like '#AA0202' into a floating-point representation."""
    if hstr.startswith('#'):
        hstr = hstr[1:]
    rs, gs, bs = hstr[:2], hstr[2:4], hstr[4:]
    r, g, b = parse_hex(rs), parse_hex(gs), parse_hex(bs)
    return r / 255.0, g / 255.0, b / 255.0


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


##############################################################################

# Goal: render annotations on the page (in their original color).

# Representing symbolic annotations from MUSCIMA++:


class CropObject(object):
    """One annotated object.

    The CropObject represents one instance of an annotation. It implements
    the following attributes:

    * `objid`: the unique number of the given annotation instance in the set
      of annotations encoded in the containing `CropObjectList`.
    * `clsid`: the identifier of the label that was given to the annotation.
    * `x`: the vertical dimension (row) of the upper left corner pixel.
    * `y`: the horizontal dimension (column) of the upper left corner pixel.
    * `width`: the amount of rows that the CropObject spans.
    * `height`: the amount of columns that the CropObject spans.
    * `mask`: a binary (0/1) numpy array that denotes the area within the
      CropObject's bounding box (specified by `x`, `y`, `height` and `width`)
      that the CropObject actually occupies. If the mask is `None`, the
      object occupies the entire bounding box.

    To recover the area corresponding to a CropObject `c`, use:

    >>> crop = img[c.top:c.bottom, c.left:c.right] * c.mask if c.mask is not None
    >>> crop = img[c.top:c.bottom, c.left:c.right] if c.mask is None

    Because this is clunky, we have implemented the following to get the crop:

    >>> crop = c.project_to(img)

    And to get the CropObject projected onto the entire image:

    >>> crop = c.project_on(img)

    Above, note the multiplicative role of the mask: while we typically would
    expect the mask to be binary, in principle, this is not strictly necessary.
    You could supply a different mask interpration, such as probabilistic.
    However, we strongly advise not to misuse this feature unless you have
    a really good reason; remember that the CropObject is supposed to represent
    an annotation of a given image. (One possible use for a non-binary mask
    that we can envision is aggregating multiple annotations of the same
    image.)

    For visualization, there is a more sophisticated method that renders
    the CropObject as a colored transparent rectangle over a RGB image.
    (NOTE: this really changes the input image!)

    >>> c_obj.render(img)
    >>> plt.imshow(c_obj); plt.show()

    However, `CropObject.render()` currently does not support rendering
    the mask.

    Implementation notes on the mask
    --------------------------------

    **DEPRECATED**

    The mask is a numpy array that will be saved as a `base64` string directly.
    This is not ideal for compatibility, as loading is only possible with
    python/numpy. Ideally, we would base64-encode the pattern of 1/0: the width
    and height of the CropObject at the same time give you the dimension
    of the mask, so we don't need to save the mask shape extra.

    (Also, the numpy array needs to be made C-contiguous for that, which
    explains the `order='C'` hack in `set_mask()`.)
    """
    def __init__(self, objid, clsid, x, y, width, height, mask=None):
        logging.info('Initializing CropObject with objid {0}, x={1}, '
                     'y={2}, h={3}, w={4}'.format(objid, x, y, height, width))
        self.objid = objid
        self.clsid = clsid
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.to_integer_bounds()

        # The mask presupposes integer bounds.
        # Applied relative to CropObject bounds, not the whole image.
        self.mask = None
        self.set_mask(mask)

        self.is_selected = False
        logging.info('...done!')

    def set_mask(self, mask):
        if mask is None:
            self.mask = None
        else:
            # Check dimension
            t, l, b, r = self.bbox_to_integer_bounds(self.top,
                                                     self.left,
                                                     self.bottom,
                                                     self.right)#.count()
            if mask.shape != (b - t, r - l):
                raise ValueError('Mask shape {0} does not correspond'
                                 ' to integer shape {1} of CropObject.'
                                 ''.format(mask.shape, (b - t, r - l)))
            if str(mask.dtype) != 'uint8':
                logging.warn('CropObject.set_mask(): Supplied non-integer mask'
                             ' with dtype={0}'.format(mask.dtype))

            self.mask = mask.astype('uint8')

    @property
    def top(self):
        return self.x

    @property
    def bottom(self):
        return self.x + self.height

    @property
    def left(self):
        return self.y

    @property
    def right(self):
        return self.y + self.width

    @property
    def bounding_box(self):
        return self.top, self.left, self.bottom, self.right

    @staticmethod
    def bbox_to_integer_bounds(ftop, fleft, fbottom, fright):
        """Rounds off the CropObject bounds to the nearest integer
        so that no area is lost (e.g. bottom and right bounds are
        rounded up, top and left bounds are rounded down).

        Returns the rounded-off integers (top, left, bottom, right)
        as `int`s.
        """
        logging.info('bbox_to_integer_bounds: inputs {0}'.format((ftop, fleft, fbottom, fright)))

        top = ftop - (ftop % 1.0)
        left = fleft - (fleft % 1.0)
        bottom = fbottom - (fbottom % 1.0)
        if fbottom % 1.0 != 0:
            bottom += 1.0
        right = fright - (fright % 1.0)
        if fright % 1.0 != 0:
            right += 1.0

        if top != ftop:
            logging.info('bbox_to_integer_bounds: rounded top by {0}'.format(top - ftop))
        if left != fleft:
            logging.info('bbox_to_integer_bounds: rounded left by {0}'.format(left - fleft))
        if bottom != fbottom:
            logging.info('bbox_to_integer_bounds: rounded bottom by {0}'.format(bottom - fbottom))
        if right != fright:
            logging.info('bbox_to_integer_bounds: rounded right by {0}'.format(right - fright))

        return int(top), int(left), int(bottom), int(right)

    def to_integer_bounds(self):
        bbox = self.bounding_box
        t, l, b, r = self.bbox_to_integer_bounds(*bbox)
        height = b - t
        width = r - l

        self.x = t
        self.y = l
        self.height = height
        self.width = width

    def project_to(self, img):
        """This function returns the *crop* of the input image
        corresponding to the CropObject (incl. masking).
        Assumes zeros are background."""
        # Make a copy! We don't want to modify the original image by the mask.
        crop = img[self.top:self.bottom, self.left:self.right] * 1
        if self.mask is not None:
            crop *= self.mask
        return crop

    def project_on(self, img):
        """This function returns only those parts of the input image
        that correspond to the CropObject and masks out everything else
        with zeros."""
        output = numpy.zeros(img.shape, img.dtype)
        crop = self.project_to(img)
        output[self.top:self.bottom, self.left:self.right] = crop
        return output

    def render(self, img, alpha=0.3, rgb=(1.0, 0.0, 0.0)):
        """Renders itself upon the given image as a rectangle
        of the given color and transparency.

        :param img: A three-channel image (3-D numpy array,
            with the last dimension being 3)."""
        color = numpy.array(rgb)
        logging.info('Rendering object {0}, clsid {1}, t/b/l/r: {2}'
                      ''.format(self.objid, self.clsid,
                                (self.top, self.bottom, self.left, self.right)))
        # logging.info('Shape: {0}'.format((self.height, self.width, 3)))
        mask = numpy.ones((self.height, self.width, 3)) * color
        crop = img[self.top:self.bottom, self.left:self.right]
        # logging.info('Mask done, creating crop')
        logging.info('Shape: {0}. Got crop. Crop shape: {1}, img shape: {2}'
                      ''.format((self.height, self.width, 3), crop.shape, img.shape))
        mix = (crop + alpha * mask) / (1 + alpha)

        img[self.top:self.bottom, self.left:self.right] = mix
        return img

    def __str__(self):
        lines = []
        lines.append('<CropObject>')
        lines.append('\t<Id>{0}</Id>'.format(self.objid))
        lines.append('\t<MLClassId>{0}</MLClassId>'.format(self.clsid))
        lines.append('\t<X>{0}</X>'.format(self.y))
        lines.append('\t<Y>{0}</Y>'.format(self.x))
        lines.append('\t<Width>{0}</Width>'.format(self.width))
        lines.append('\t<Height>{0}</Height>'.format(self.height))
        lines.append('\t<Selected>false</Selected>')

        mask_string = self.encode_mask(self.mask)
        lines.append('\t<Mask>{0}</Mask>'.format(mask_string))

        lines.append('</CropObject>')
        return '\n'.join(lines)

    @staticmethod
    def encode_mask(mask, compress=False):
        """Encodes the mask array in a compact form. Returns 'None' if mask
        is None. If the mask is not None, uses the following algorithm:

        * Flatten the mask (then use width and height of CropObject for
          reshaping).
        * Record as string, with whitespace separator
        * Compress string using gz2 (if compress=True) NOT IMPLEMENTED
        * Return resulting string
        """
        if mask is None:
            return 'None'
        mask_flat = mask.flatten()
        output = ' '.join(map(str, mask_flat))
        return output

    @staticmethod
    def decode_mask(mask_string, shape):
        """Decodes the mask array from the encoded form to the 2D numpy array."""
        if mask_string == 'None':
            return None
        try:
            values = map(float, mask_string.split())
        except ValueError:
            logging.info('CropObject.decode_mask(): Cannot decode mask values:\n{0}'.format(mask_string))
            raise
        mask = numpy.array(values).reshape(shape)
        #s = base64.decodestring(mask_string)
        #mask = numpy.frombuffer(s)
        #logging.info('CropObject.decode_mask(): shape={0}\nmask={1}'.format(mask.shape, mask))
        return mask


class MLClass(object):
    """Information about the annotation class. We're using it
    mostly to get the color of rendered CropObjects."""
    def __init__(self, clsid, name, folder, color):
        self.clsid = clsid
        self.name = name
        self.folder = folder
        # Parse the string into a RGB spec.
        r, g, b = hex2rgb(color)
        logging.info('MLClass {0}: color {1}'.format(name, (r, g, b)))
        self.color = (r, g, b)


def parse_cropobject_list(filename, with_refs=False, tolerate_ref_absence=True,
                          integer_bounds=False):
    """From a xml file with a CropObjectList as the top element, parse
    a list of CropObjects.

    Note that what is Y in the data gets translated to cropobj.x (vertical),
    what is X gets translated to cropobj.y (horizontal).

    :param with_refs: If set, will return a triplet (cropobject_list, mlclasslist_file,
        image_file) based on the "Refs" entry in the CropObjectList file.
        The filename is, however, relative to some root which is not
        a part of the file to make MUSCIMA++ portable.

    :param integer_bounds: If set, will round the CropObject bounding box
        to the nearest integer bounding box that covers the entire area (i.e.
        top and left gets rounded down, bottom and right gets rounded up).
    """
    logging.info('Parsing CropObjectList, with_refs={0}, tolerate={1}.'
                 ''.format(with_refs, tolerate_ref_absence))
    tree = etree.parse(filename)
    root = tree.getroot()
    logging.info('XML parsed.')
    cropobject_list = []
    for i, cropobject in enumerate(root.iter('CropObject')):
        logging.info('Parsing CropObject {0}'.format(i))
        obj = CropObject(objid=int(float(cropobject.findall('Id')[0].text)),
                         clsid=int(float(cropobject.findall('MLClassId')[0].text)),
                         x=float(cropobject.findall('Y')[0].text),
                         y=float(cropobject.findall('X')[0].text),
                         width=float(cropobject.findall('Width')[0].text),
                         height=float(cropobject.findall('Height')[0].text))
        mask = None
        m = cropobject.findall('Mask')
        if len(m) > 0:
            mask = CropObject.decode_mask(cropobject.findall('Mask')[0].text,
                                          shape=(obj.height, obj.width))
        obj.set_mask(mask)
        logging.info('Created CropObject with ID {0}'.format(obj.objid))
        if integer_bounds is True:
            obj.to_integer_bounds()
        cropobject_list.append(obj)

    logging.info('CropObjectList loaded.')
    if with_refs:
        logging.info('Parsing CropObjectList refs.')
        # This is pretty bad at this point. We should change it to a regular tag...
        with open(filename) as hdl:
            lines = [l.strip() for l in hdl]
        ref_line = lines[1]

        # If there are no refs in the file:
        if not ref_line.startswith('<!--Refs: MLClassList'):
            if not tolerate_ref_absence:
                raise ValueError('Requested refs from CropObjectList, but none found.'
                                 ' (They have to be on the second line; second line'
                                 ' is intead:\n{0})'.format(ref_line))
            else:
                logging.warn('Requested refs from CropObjectList, but none found.'
                             ' Failure-tolerant mode, so will return None for both refs.')
                mlclasslist_file = None
                image_file = None
                return cropobject_list, mlclasslist_file, image_file

        fields = ref_line.split('"')
        mlclasslist_file = fields[1]
        image_file = fields[3]
        return cropobject_list, mlclasslist_file, image_file

    return cropobject_list


def export_cropobject_list(cropobjects, mlclasslist_file=None, image_file=None, ref_root=None):
    cropobj_string = '\n'.join([str(c) for c in cropobjects])
    lines = []
    lines.append('<?xml version="1.0" encoding="utf-8"?>')

    # Refs
    if (mlclasslist_file is not None) and (image_file is not None):
        if ref_root is not None:
            if mlclasslist_file.startswith(ref_root):
                mlclasslist_file = mlclasslist_file[len(ref_root):]
            else:
                logging.warn('Got reference root {0}, but not found in the beginning'
                             ' of mlclasslist_file {1}. Proceeding.'
                             ''.format(ref_root, mlclasslist_file))
            if image_file.startswith(ref_root):
                image_file = image_file[len(ref_root):]
            else:
                logging.warn('Got reference root {0}, but not found in the beginning'
                             ' of image_file {1}. Proceeding.'
                             ''.format(ref_root, image_file))
        lines.append('<!--Refs: MLClassList="{0}" image="{1}" -->'.format(mlclasslist_file, image_file))

    lines.append('<CropObjectList'
                 ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                 ' xmlns:xsd="http://www.w3.org/2001/XMLSchema">')
    lines.append('<CropObjects>')
    lines.append(cropobj_string)
    lines.append('</CropObjects>')
    lines.append('</CropObjectList>')
    return '\n'.join(lines)


def position_cropobject_list_by_muscimage(cropobject_list, muscimage):
    """Recomputes a new CropObject list, so that only CropObjects within
    the bounding box of the given MUSCImage are retained and their
    coordinates are recomputed relative to the MUSCImage's bounding box.

    :type cropobject_list: list[CropObject]
    :param cropobject_list: A list of CropObjects to be filtered/recomputed.

    :type muscimage: MUSCImage
    :param muscimage: A MUSCImage against which we want to check
        the CropObjects.
    """
    output = []
    for c in cropobject_list:
        if muscimage.contains_bbox(*c.bounding_box):
            new_x = c.x - muscimage.bounding_box[0]
            new_y = c.y - muscimage.bounding_box[1]
            c_out = CropObject(objid=c.objid, clsid=c.clsid,
                               x=new_x, y=new_y,
                               width=c.width, height=c.height)
            output.append(c_out)
    return output


def parse_mlclass_list(filename):
    """From a xml file with a MLClassList as the top element,
    """
    tree = etree.parse(filename)
    root = tree.getroot()
    mlclass_list = []
    for mlclass in root.iter('MLClass'):
        obj = MLClass(clsid=int(mlclass.findall('Id')[0].text),
                      name=mlclass.findall('Name')[0].text,
                      folder=mlclass.findall('Folder')[0].text,
                      color=mlclass.findall('Color')[0].text)
        mlclass_list.append(obj)
    return mlclass_list


def render_annotations(img, cropoboject_list, mlclass_list=None, alpha=1.0,
                       grayscale=False):
    """Render the annotation bounding boxes of the given cropobjects
    onto the img. Take care to load the same image that was annotated,
    and to load the correct MLClassList to get names & colors!

    :type img: numpy.array
    :param img: The image is expected to be in 3-channel RGB mode, floating-point,
        within ``(0.0, 1.0)``. If `grayscale` is set, then expects single-channel
        grayscale image, floating-point, within ``(0.0, 1.0)``.

    :param mlclass_list: If None, will draw bounding boxes of all symbols
        in gray (0.3, 0.3, 0.3).

    :param alpha: Render with this weight of the bounding box colored rectangles.
        Set alpha=1.0 for a 50:50 img/boundingbox color mix. Note that at the end,
        the rendering is averaged with the original image again, to accent
        the actual notation.

    :param grayscale: If set, expects a grayscale image instead of RGB.
    """
    logging.debug('We have {0} cropobjects, {1} mlclasses and image'
                  ' of shape {2}'.format(len(cropoboject_list),
                                         'None' if not mlclass_list else len(mlclass_list),
                                         img.shape))

    mlclass_dict = None
    if mlclass_list is not None:
        mlclass_dict = {m.clsid: m for m in mlclass_list}

    if grayscale:
        reimg = numpy.zeros((img.shape[0], img.shape[1], 3), dtype=img.dtype)
        reimg[:,:,0] += img
        reimg[:,:,1] += img
        reimg[:,:,2] += img
    else:
        reimg = img * 1.0

    output = reimg * 1.0

    for obj in cropoboject_list:
        logging.debug('Rendering cropoobject with x, y, H, W:'
                      ' {0}, {1}, {2}, {3}'.format(obj.x, obj.y, obj.height,
                                                   obj.width))
        if mlclass_dict is not None:
            rgb = mlclass_dict[obj.clsid].color
        else:
            rgb = (0.8, 0.8, 0.8)

        logging.debug('\tObject color: {0}'.format(rgb))
        obj.render(output, alpha=alpha, rgb=rgb)

    return (output + reimg) / 2.0
