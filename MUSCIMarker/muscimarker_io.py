"""This module implements tools for loading the MUSCIMA++ dataset
symbolic layer: CropObject and MLClass lists.

Only the function `position_cropobject_list_by_muscimage()`
requires a `MUSCImage` instance as an argument.
"""
from __future__ import print_function, unicode_literals
import logging
import os

import numpy
from lxml import etree

logger = logging.getLogger(__name__)

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."

if not 'MFF_MUSCIMA_ROOT' in os.environ:
    MFF_MUSCIMA_ROOT = os.path.join('/Users', 'hajicj', 'mhr', 'MFF-MUSCIMA')
else:
    MFF_MUSCIMA_ROOT = os.environ['MFF_MUSCIMA_ROOT']

MFF_MUSCIMA_SYMBOLIC = os.path.join(MFF_MUSCIMA_ROOT, 'Symbolic')
MFF_MUSCIMA_XML = os.path.join(MFF_MUSCIMA_ROOT, 'XML')

CROPOBJECT_MASK_ORDER = 'C'

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


##############################################################################

# Representing symbolic annotations from MUSCIMA++:


class CropObject(object):
    """One annotated object.

    The CropObject represents one instance of an annotation. It implements
    the following attributes:

    * `objid`: the unique number of the given annotation instance in the set
      of annotations encoded in the containing `CropObjectList`.
    * `clsid`: the identifier of the label that was given to the annotation.
    * `clsname`: the name of the label that was given to the annotation
      (this is the human-readable string such as ``notehead-full``).
    * `x`: the vertical dimension (row) of the upper left corner pixel.
    * `y`: the horizontal dimension (column) of the upper left corner pixel.
    * `width`: the amount of rows that the CropObject spans.
    * `height`: the amount of columns that the CropObject spans.
    * `mask`: a binary (0/1) numpy array that denotes the area within the
      CropObject's bounding box (specified by `x`, `y`, `height` and `width`)
      that the CropObject actually occupies. If the mask is `None`, the
      object occupies the entire bounding box.

    CropObjects can also form graphs, using the following attributes:

    * `outlinks`: Outgoing edges. A list of integers; it is assumed they are
      valid `objid`s.
    * `inlinks`: Incoming edges. A list of integers; it is assumed they are
      valid `objid`s.

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
    >>> plt.imshow(img); plt.show()

    However, `CropObject.render()` currently does not support rendering
    the mask.

    XML representation
    ------------------

    The ``CropObject`` string representation is a XML object::

        <CropObject>
          <Id>25</Id>
          <MLClassId>7</MLClassId>
          <MLClassName>PRIM__beam</MLClassName>
          <X>413</X>
          <Y>119</Y>
          <Width>16</Width>
          <Height>6</Height>
          <Selected>false</Selected>
          <Mask>1:5 0:11 (...) 1:4 0:6 1:5 0:1</Mask>
          <Outlinks>12 24 26</Outlinks>
          <Inlinks>13</Inlinks>
        </CropObject>

    The CropObjects are themselves kept as a list::

        <CropObjectList>
          <Classes>
            <URL> ... </URL>
            <md5> ... <md5>
          </Classes>
          <CropObjects>
            <CropObject> ... </CropObject>
            <CropObject> ... </CropObject>
          </CropObjects>
        </CropObjectList>

    The ``<Classes>`` element keeps a reference to the list of classes
    that were used to label the CropObjects. The CropObjects themselves
    are inside the ``<CropObjects>`` element.

    The ``<Classes>`` element *might not be present*. In that case,
    it is necessary to match the list of classes document to the
    CropObjects manually. However, since the class names are present
    through the ``clsname`` attribute (``<MLClassName>`` element),
    matching the list is no longer necessary for general understanding
    of the file. The MLClassList file serves as a disambiguation tool:
    there may be multiple annotation projects that use the same names
    but maybe define them differently and use different guidelines,
    and their respective MLClassLists allow you to interpret the symbol
    names correctly, in light of the corresponding set of definitions.

    .. note::

        In MUSCIMarker, the MLClassList is currently necessary to define
        how CropObjects are displayed: their color. (All noteheads are red,
        all barlines are green, etc.) The other function, matching names
        to ``clsid``s, has been superseeded by the ``clsname`` CropObject
        attribute.

    Merging CropObjects
    -------------------

    To merge a list of CropObjects into a new one, you need to:

    * Compute the new object's bounding box: ``croobjects_merge_bbox()``
    * Compute the new object's mask: ``cropobjects_merge_mask()``
    * Determine the clsid and objid of the new object.

    Since objid and clsid of merges may depend on external settings
    and generally cannot be reliably determined from the merged
    objects themselves (e.g. the merge of a notehead and a stem
    should be a new note symbol), you need to supply them externally.
    However, the bounding box and mask can be determined. The bounding
    box is computed simply as the smallest bounding box that
    encompasses all the CropObjects, and the mask is an OR operation
    over the individual masks (or None, if the CropObjects don't
    have masks). Note that the merge cannot deal with a situation
    where only some of the objects have a mask.

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
    def __init__(self, objid, clsid, clsname, x, y, width, height,
                 outlinks=[], inlinks=[],
                 mask=None):
        logging.info('Initializing CropObject with objid {0}, x={1}, '
                     'y={2}, h={3}, w={4}'.format(objid, x, y, height, width))
        self.objid = objid
        self.clsid = clsid
        self.clsname = clsname
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.to_integer_bounds()

        # The mask presupposes integer bounds.
        # Applied relative to CropObject bounds, not the whole image.
        self.mask = None
        self.set_mask(mask)

        self.inlinks = inlinks
        self.outlinks = outlinks

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
                logging.debug('CropObject.set_mask(): Supplied non-integer mask'
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

    @property
    def middle(self):
        """Returns the integer representation of where the middle
        of the CropObject lies, as a ``(m_vert, m_horz)`` tuple.

        The integers just get rounded down.
        """
        vmid = self.top + (self.bottom - self.top) / 2
        hmid = self.left + (self.right - self.left) / 2
        return int(vmid), int(hmid)

    @property
    def is_empty(self):
        """A CropObject is empty if it is composed of zero pixels.
        This is measured through the mask. CropObjects without
        a mask are assumed to be non-empty."""
        if self.mask is None:
            return False

        return self.mask.sum() == 0

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

    def overlaps(self, bounding_box):
        """Check whether this CropObject overlaps the given bounding box."""
        t, l, b, r = bounding_box
        # Does it overlap vertically? Includes situations where the CropObject is
        # inside the bounding box.
        # Note that the bottom is +1 (fencepost), so the checks bottom vs. top need to be "less than",
        # not leq. If one object's top would be equal to the other's bottom, they would be touching,
        # not overlapping.
        if max(t, self.top) < min(b, self.bottom):
            if max(l, self.left) < min(r, self.right):
                return True
        return False

    def bbox_intersection(self, bounding_box):
        """Returns the sub-bounding box of this CropObject, relative to its size (so: 0,0
        is the CropObject's upper left corner), that intersects the given bounding box.
        If the intersection is empty, returns None.

        >>> c = CropObject(0, 0, 'test', 10, 100, height=20, width=10)
        >>> c.bounding_box
        (10, 100, 30, 110)
        >>> other_bbox = 20, 100, 40, 105
        >>> c.bbox_intersection(other_bbox)
        (10, 0, 20, 5)
        >>> containing_bbox = 4, 55, 44, 115
        >>> c.bbox_intersection(containing_bbox)
        (0, 0, 20, 10)
        >>> contained_bbox = 12, 102, 22, 108
        >>> c.bbox_intersection(contained_bbox)
        (2, 2, 12, 8)
        >>> non_overlapping_bbox = 0, 0, 3, 3
        >>> c.bbox_intersection(non_overlapping_bbox) is None
        True

        """
        t, l, b, r = bounding_box

        out_top = max(t, self.top)
        out_bottom = min(b, self.bottom)
        out_left = max(l, self.left)
        out_right = min(r, self.right)

        if (out_top < out_bottom) and (out_left < out_right):
            return out_top - self.top, \
                   out_left - self.left, \
                   out_bottom - self.top, \
                   out_right - self.left
        else:
            return None

    def crop_to_mask(self):
        """Crops itself to the minimum bounding box that contains all
        its pixels, as determined by its mask.

        If the mask is all zeros, does not do anything, because
        at this point, the is_empty check should be invoked anyway
        in any situation where you care whether the object is empty
        or not (e.g. delete it after trimming).

        >>> mask = numpy.zeros((20, 10))
        >>> mask[5:15, 3:8] = 1
        >>> c = CropObject(0, 0, 'test', 10, 100, width=10, height=20, mask=mask)
        >>> c.bounding_box
        (10, 100, 30, 110)
        >>> c.crop_to_mask()
        >>> c.bounding_box
        (15, 103, 25, 108)
        >>> c.height, c.width
        (10, 5)

        Assumes integer bounds, which is ensured during CropObject initialization.
        """
        if self.mask is None:
            return

        if self.is_empty:
            return

        # We know the object is not empty.

        # How many rows/columns to trim from top, bottom, etc.
        trim_top = -1
        for i in xrange(self.mask.shape[0]):
            if self.mask[i,:].sum() != 0:
                trim_top = i
                break

        trim_left = -1
        for j in xrange(self.mask.shape[1]):
            if self.mask[:,j].sum() != 0:
                trim_left = j
                break

        trim_bottom = -1
        for k in xrange(self.mask.shape[0]):
            if self.mask[-(k+1),:].sum() != 0:
                trim_bottom = k
                break

        trim_right = -1
        for l in xrange(self.mask.shape[1]):
            if self.mask[:,-(l+1)].sum() != 0:
                trim_right = l
                break

        logging.info('Cropobject.crop: Trimming top={0}, left={1},'
                     'bottom={2}, right={3}'
                     ''.format(trim_top, trim_left, trim_bottom, trim_right))

        # new bounding box relative to the current bounding box -- used to trim
        # the mask
        rel_t = trim_top
        rel_l = trim_left
        rel_b = self.height - trim_bottom
        rel_r = self.width - trim_right

        new_mask = self.mask[rel_t:rel_b, rel_l:rel_r] * 1

        logging.info('Cropobject.crop: Old mask shape {0}, new mask shape {1}'
                     ''.format(self.mask.shape, new_mask.shape))

        # new bounding box, relative to image -- used to compute the CropObject's
        # new position and size
        abs_t = self.top + trim_top
        abs_l = self.left + trim_left
        abs_b = self.bottom - trim_bottom
        abs_r = self.right - trim_right

        self.x = abs_t
        self.y = abs_l
        self.height = abs_b - abs_t
        self.width = abs_r - abs_l

        self.set_mask(new_mask)

    def __str__(self):
        lines = []
        lines.append('<CropObject>')
        lines.append('\t<Id>{0}</Id>'.format(self.objid))
        lines.append('\t<MLClassId>{0}</MLClassId>'.format(self.clsid))
        lines.append('\t<MLClassName>{0}</MLClassName>'.format(self.clsname))
        lines.append('\t<X>{0}</X>'.format(self.y))
        lines.append('\t<Y>{0}</Y>'.format(self.x))
        lines.append('\t<Width>{0}</Width>'.format(self.width))
        lines.append('\t<Height>{0}</Height>'.format(self.height))
        lines.append('\t<Selected>false</Selected>')

        mask_string = self.encode_mask(self.mask)
        lines.append('\t<Mask>{0}</Mask>'.format(mask_string))

        if len(self.inlinks) > 0:
            inlinks_string = ' '.join(map(unicode, self.inlinks))
            lines.append('\t<Inlinks>{0}</Inlinks>'.format(inlinks_string))
        if len(self.outlinks) > 0:
            outlinks_string = ' '.join(map(unicode, self.outlinks))
            lines.append('\t<Outlinks>{0}</Outlinks>'.format(outlinks_string))

        lines.append('</CropObject>')
        return '\n'.join(lines)

    def encode_mask(self, mask, compress=False, mode='rle'):
        if mode == 'rle':
            return self.encode_mask_rle(mask, compress=compress)
        elif mode == 'bitmap':
            return self.encode_mask_bitmap(mask, compress=compress)

    @staticmethod
    def encode_mask_bitmap(mask, compress=False):
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
        # By default works in row-major order.
        # So we can just prescribe 'C' without losing data.
        mask_flat = mask.flatten(order=CROPOBJECT_MASK_ORDER)
        output = ' '.join(map(str, mask_flat))
        return output

    @staticmethod
    def encode_mask_rle(mask, compress=False):
        """Encodes the mask array in Run-Length Encoding. Instead of
        having the bitmap ``0 0 1 1 1 0 0 0 1 1``, the RLE encodes
        the mask as ``0:2 1:3 0:3 1:2``. This is much more compact.

        Currently, the rows of the mask are not treated in any special
        way. The mask just gets flattened and then encoded.

        Implementation:
        """
        if mask is None:
            return 'None'
        mask_flat = mask.flatten(order=CROPOBJECT_MASK_ORDER)

        output_strings = []
        current_run_type = 0
        current_run_length = 0
        for i in mask_flat:
            if i == current_run_type:
                current_run_length += 1
            else:
                s = '{0}:{1}'.format(current_run_type, current_run_length)
                output_strings.append(s)
                current_run_type = i
                current_run_length = 1
        s = '{0}:{1}'.format(current_run_type, current_run_length)
        output_strings.append(s)
        output = ' '.join(output_strings)
        return output

    def decode_mask(self, mask_string, shape):
        mode = self._determine_mask_mode(mask_string)
        if mode == 'rle':
            return self.decode_mask_rle(mask_string, shape=shape)
        elif mode == 'bitmap':
            return self.decode_mask_bitmap(mask_string, shape=shape)

    def _determine_mask_mode(self, mask_string):
        """If the mask string starts with '0:' or '1:', or generally
        if it contains a non-0 or 1 symbol, assume it is RLE."""
        mode = 'bitmap'
        if len(mask_string) < 3:
            mode = 'bitmap'
        elif ':' in mask_string[:3]:
            mode = 'rle'
        return mode

    @staticmethod
    def decode_mask_bitmap(mask_string, shape):
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

    @staticmethod
    def decode_mask_rle(mask_string, shape):
        """Decodes the mask array from the RLE-encoded form
        to the 2D numpy array."""
        if mask_string == 'None':
            return None

        values = []
        for kv in mask_string.split(' '):
            k_string, v_string = kv.split(':')
            k, v = int(k_string), int(v_string)
            vs = [k for _ in xrange(v)]
            values.extend(vs)

        mask = numpy.array(values).reshape(shape)
        return mask

    def join(self, other):
        """CropObject "addition": performs an OR on this
        and the ``other`` CropObjects' masks and bounding boxes,
        and assigns to this CropObject the result.

        The ``clsname`` of the ``other`` is ignored.
        """
        # Get combined bounding box
        nt = min(self.top, other.top)
        nl = min(self.left, other.left)
        nb = max(self.bottom, other.bottom)
        nr = max(self.right, other.right)

        nh = nb - nt
        nw = nr - nl

        # Create mask of corresponding size
        new_mask = numpy.zeros((nh, nw), dtype=self.mask.dtype)

        # Find coordinates where to paste the masks
        spt = self.top - nt  # spt = self_paste_top
        spl = self.left - nl
        opt = other.top - nt
        opl = other.left - nl

        # Paste the masks into these places
        new_mask[spt:spt+self.height, spl:spl+self.width] += self.mask
        new_mask[opt:opt+other.height, opl:opl+other.width] += other.mask

        # Normalize mask value
        new_mask[new_mask != 0] = 1

        # Assign the new variables to this CropObject
        self.x = nt
        self.y = nl
        self.height = nh
        self.width = nw
        self.mask = new_mask

        # Add inlinks and outlinks
        for o in other.outlinks:
            if o not in self.outlinks:
                self.outlinks.append(o)
        for i in other.inlinks:
            if i not in self.inlinks:
                self.inlinks.append(i)


class MLClass(object):
    """Information about the annotation class. We're using it
    mostly to get the color of rendered CropObjects."""
    def __init__(self, clsid, name, folder, color):
        self.clsid = clsid
        self.name = name
        self.folder = folder
        # Parse the string into a RGB spec.
        r, g, b = hex2rgb(color)
        logging.debug('MLClass {0}: color {1}'.format(name, (r, g, b)))
        self.color = (r, g, b)


##############################################################################

# I/O operations (parsing/export)


def parse_cropobject_list(filename, with_refs=False, tolerate_ref_absence=True,
                          integer_bounds=False,
                          fill_mlclass_names=False,
                          mlclass_dict={}):
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

    :param fill_mlclass_names: If True, will attempt to fill in the ``clsname``
        attribute by looking it up in the ``mlclasslist`` when it is missing
        from the ``CropObject``s. This is a feature for transitioning from
        old CropObjects that did not include symbol names to new CropObjects
        that do include this, so that old files aren't lost.

    :param mlclass_dict: If ``fill_mlclass_names`` is requested, you have to
        also supply the dict of MLClasses that have names for the ``clsid``s
        in the parsed CropObjectList. Keys are ``clsid``s, values are the
        MLClass objects.
    """
    logging.info('Parsing CropObjectList, with_refs={0}, tolerate={1}.'
                 ''.format(with_refs, tolerate_ref_absence))
    tree = etree.parse(filename)
    root = tree.getroot()
    logging.info('XML parsed.')
    cropobject_list = []

    for i, cropobject in enumerate(root.iter('CropObject')):
        logging.info('Parsing CropObject {0}'.format(i))

        objid = int(float(cropobject.findall('Id')[0].text))

        # Class ID
        clsid = int(float(cropobject.findall('MLClassId')[0].text))

        # Dealing with clsname transition
        clsname=None
        _has_clsname = False
        if len(cropobject.findall('MLClassName')) > 0:
            clsname = cropobject.findall('MLClassName')[0].text
        elif fill_mlclass_names:
            if clsid in mlclass_dict:
                clsname = mlclass_dict[clsid].name
            else:
                raise ValueError('Requested MLClass names filled in from'
                                 ' MLClassList, but the list does not contain'
                                 ' id {0}'.format(clsid))

        # NOTE THE SWAP OF COORDINATES
        x = float(cropobject.findall('Y')[0].text)
        y = float(cropobject.findall('X')[0].text)
        width = float(cropobject.findall('Width')[0].text)
        height = float(cropobject.findall('Height')[0].text)

        # Parsing the graph structure (Can deal with missing Inlinks/Outlinks)
        inlinks = []
        i_s = cropobject.findall('Inlinks')
        if len(i_s) > 0:
            i_s_text = cropobject.findall('Inlinks')[0].text
            if i_s_text is not None:  # Zero-length links
                inlinks = map(int, i_s_text.split(' '))

        outlinks = []
        o_s = cropobject.findall('Outlinks')
        if len(o_s) > 0:
            o_s_text = cropobject.findall('Outlinks')[0].text
            if o_s_text is not None:
                outlinks = map(int, o_s_text.split(' '))

        obj = CropObject(objid=objid,
                         clsid=clsid,
                         clsname=clsname,
                         x=x,
                         y=y,
                         width=width,
                         height=height,
                         inlinks=inlinks,
                         outlinks=outlinks)

        mask = None
        m = cropobject.findall('Mask')
        if len(m) > 0:
            mask = obj.decode_mask(cropobject.findall('Mask')[0].text,
                                   shape=(obj.height, obj.width))
        obj.set_mask(mask)
        logging.info('Created CropObject with ID {0}'.format(obj.objid))
        if integer_bounds is True:
            obj.to_integer_bounds()
        cropobject_list.append(obj)

    logging.info('CropObjectList loaded.')

    validate_cropobjects_graph_structure(cropobject_list)

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


def validate_cropobjects_graph_structure(cropobjects):
    # Verify graph structure
    objids = frozenset([c.objid for c in cropobjects])
    for c in cropobjects:
        inlinks = c.inlinks
        for i in inlinks:
            if i not in objids:
                raise ValueError('Invalid graph structure in CropObjectList:'
                                 ' object {0} has inlink from non-existent'
                                 ' object {1}'.format(c, i))
        outlinks = c.outlinks
        for o in outlinks:
            if o not in objids:
                raise ValueError('Invalid graph structure in CropObjectList:'
                                 ' object {0} has outlink to non-existent'
                                 ' object {1}'.format(c, o))


def export_cropobject_list(cropobjects, mlclasslist_file=None, image_file=None, ref_root=None):
    # This is the data string, the rest is formalities
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
            c_out = CropObject(objid=c.objid,
                               clsid=c.clsid, clsname=c.clsname,
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


##############################################################################

# Operations on CropObjects: merge

def cropobjects_merge_bbox(cropobjects):
    """Computes the bounding box of a CropObject that would
    result from merging the given list of CropObjects."""
    # Find extremes. This will define the output cropobject.
    t, l, b, r = numpy.inf, numpy.inf, -1, -1
    for c in cropobjects:
        t = min(t, c.top)
        l = min(l, c.left)
        b = max(b, c.bottom)
        r = max(r, c.right)

    return t, l, b, r


def cropobjects_merge_mask(cropobjects):
    """Merges the given list of cropobjects into one. Masks are combined
    by an OR operation.

    >>> c1 = CropObject(0, 1, 'name', 10, 10, 4, 1, mask=numpy.ones((1, 4), dtype='uint8'))
    >>> c2 = CropObject(1, 1, 'name', 11, 10, 6, 1, mask=numpy.ones((1, 6), dtype='uint8'))
    >>> c3 = CropObject(2, 1, 'name', 9, 14,  2, 4, mask=numpy.ones((4, 2), dtype='uint8'))
    >>> c = [c1, c2, c3]
    >>> m1 = cropobjects_merge_mask(c)
    >>> m1.shape
    (4, 6)
    >>> print(m1)
    [[0 0 0 0 1 1]
     [1 1 1 1 1 1]
     [1 1 1 1 1 1]
     [0 0 0 0 1 1]]

    Mask behavior: if at least one of the cropobjects has a mask, then
    masking behavior is activated. The masks are combined using OR: any
    pixel of the resulting merged cropobject that corresponds to a True
    mask pixel in one of the input cropobjects will get a True mask value,
    all others (ie. including all intermediate areas) will get a False.

    If no input cropobject has a mask, then the resulting cropobject
    also will not have a mask.

    If some cropobjects have masks and some don't, fails.
    """
    # No mask
    if len([c for c in cropobjects if c.mask is not None]) == 0:
        return None

    # Some masked, some not
    for c in cropobjects:
        if c.mask is None:
            raise ValueError('Cannot deal with a mix of masked and non-masked cropobjects.')

    # Now we know all have masks.
    t, l, b, r = cropobjects_merge_bbox(cropobjects)
    h = b - t
    w = r - l
    output_mask = numpy.zeros((h, w), dtype=cropobjects[0].mask.dtype)
    logging.warn('Output mask shape: {0}'.format(output_mask.shape))
    for c in cropobjects:
        logging.debug('C. shape: {0}'.format(c.bounding_box))
        logging.debug('TLBR: {0}'.format((t, l, b, r)))
        ct, cl, cb, cr = c.top - t, c.left - l, h - (b - c.bottom), w - (r - c.right)
        logging.debug('Mask shape: {0}, curr. shape: {1}'.format(c.mask.shape, (cb - ct, cr - cl)))
        output_mask[ct:cb, cl:cr] += c.mask

    output_mask[output_mask > 0] = 1
    return output_mask
