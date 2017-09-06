"""This module implements functions for manipulating the annotated image,
in order to make annotation more efficient."""
from __future__ import print_function, unicode_literals, division

import logging

import numpy
from skimage.filters import gaussian, threshold_otsu, rank

__version__ = "0.0.1"
__author__ = "Jan Hajic jr."


def build_image_processing_params(config):
    """Extracts the boolean values for configuring """


class ImageProcessing(object):
    """This class holds the definitions of how the input image
    should be manipulated upon loading it into the model.

    Only processes grayscale images.
    """
    def __init__(self,
                 do_image_processing=False,
                 auto_invert=False,
                 stretch_intensity=False):

        logging.warn('ImageProcessing: Initializing with params'
                     ' do_image_processing={0},'
                     ' auto_invert={1},'
                     ' stretch_intensity={2},'
                     ''.format(do_image_processing, auto_invert, stretch_intensity))

        self.do_image_processing = do_image_processing

        self.auto_invert = auto_invert
        self.stretch_intensity = stretch_intensity
        self.otsu_background = False # otsu_background

    def process(self, image):
        """The wrapper method. Based on the ImageProcessing settings,
        applies the desired image transformations."""
        if not self.do_image_processing:
            logging.info('ImageProcessing: no processing requested.')
            return image

        if _is_binary(image):
            return image

        if self.auto_invert:
            logging.info('ImageProcessing: auto-invert set to {0}, type {1},'
                         'auto-inverting'
                         ''.format(self.auto_invert, type(self.auto_invert)))
            image = _auto_invert(image)

        if self.stretch_intensity:
            image = _stretch_intensity(image)

        if self.otsu_background:
            image = _binarize_and_apply_background(image)

        return image



def _is_binary(image):
    values = set(image.flatten())
    if len(values) == 2:
        return True
    else:
        return False


def _auto_invert(image, smoothing_sigma=2.0):
    """Attempts to make sure that foreground is white and background
    is black.

    Assumes that the background has many more pixels than the foreground.

    * Finds maximum and minimum intensities (after some smoothing, to
      minimize speckles/salt and pepper noise)
    * Finds median intensity
    * If the median is closer to maximum, then assumes the image
      has a light background and should be inverted.
    * If the median is closer to minimum, then assumes the image
      has a dark background and should NOT be inverted.
    """
    output = image * 1
    blurred = gaussian(output, sigma=smoothing_sigma)

    i_max = blurred.max()
    i_min = blurred.min()
    i_med = numpy.median(blurred)

    if (i_max - i_med) < (i_med - i_min):
        output = numpy.invert(output)

    return output


def _stretch_intensity(image, smoothing_sigma=2.0):
    """Stretches the intensity range of the image to (0, 255)."""
    output = image * 1
    blurred = (gaussian(output, sigma=smoothing_sigma) * 255).astype('uint8')

    i_max = blurred.max()
    i_min = blurred.min()

    logging.info('Stretching image intensity: min={0}, max={1}'
                 ''.format(i_min, i_max))

    output[output > i_max] = i_max
    output[output < i_min] = i_min

    output -= i_min
    output = (output * (255 / i_max)).astype('uint8')

    return output


def _binarize_and_apply_background(image):
    """Performs plain Otsu binarization to get threshold,
    but only sets the background to 0, retains all the foreground
    intensities."""
    selem = numpy.ones((80, 80), dtype='uint8')
    local_otsu = rank.otsu(image, selem)
    # thr = threshold_otsu(image, nbins=256)
    output = image * 1
    output[output < local_otsu] = 0
    return output