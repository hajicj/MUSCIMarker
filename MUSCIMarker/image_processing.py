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
                 stretch_intensity=False,
                 warp_registration=False):

        logging.warn('ImageProcessing: Initializing with params'
                     ' do_image_processing={0},'
                     ' auto_invert={1},'
                     ' stretch_intensity={2},'
                     ''.format(do_image_processing, auto_invert, stretch_intensity))

        self.do_image_processing = do_image_processing

        self.auto_invert = auto_invert
        self.stretch_intensity = stretch_intensity
        self.otsu_background = False # otsu_background
        self.warp_registration = warp_registration

    def process(self, image):
        """The wrapper method. Based on the ImageProcessing settings,
        applies the desired image transformations."""
        if not self.do_image_processing:
            logging.info('ImageProcessing: no processing requested.')
            return image

        if _is_binary(image):
            return image

        if self.warp_registration:
            image = PerspectiveRegistrationProcessor().process(image)

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




class PerspectiveRegistrationProcessor():
    """Computes Perspective Projection rectangular sheet image space.

    By:

    Matthias Dorfer
    matthias.dorfer@jku.at
    """

    def __init__(self,
                 target_width=2500,
                 min_area=10000,
                 polygon_length_threshold=4000):
        """ Constructor """

        # set target width of image
        self.w = target_width

        # minimum area of sheet candidate
        self.min_area = min_area

        self.polygon_length_threshold = polygon_length_threshold


    def process(self, image, verbosity=0):
        """ warp image """
        img = image * 1  # Work on a copy
        import cv2   # Local import, so that people can live without OpenCV

        # resize image to target size
        h = int(numpy.float(self.w) / img.shape[1] * img.shape[0])
        img = cv2.resize(img, (self.w, h))

        # pre-process image
        img = cv2.bilateralFilter(img, 1, 10, 120)

        # stretch image intensities
        img = _stretch_intensity(img)

        # compute gradient image
        sobel_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=5)
        sobel_y = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=5)
        sobel = numpy.sqrt(sobel_x**2 + sobel_y**2)
        sobel = _stretch_intensity(sobel)

        # binarize gradient image using Otsu
        _, binary = cv2.threshold(sobel.copy(), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # find contours in binary edge image
        _, contours, _ = cv2.findContours(binary, mode=1, method=2)

        # select contours by area
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) > self.min_area]

        polygons = []
        grad_mags = []
        for cnt in contours:

            # compute convex hull
            hull = cv2.convexHull(cnt)

            # approximate polygon
            epsilon = 0.1 * cv2.arcLength(hull, True)
            poly_approx = cv2.approxPolyDP(hull, epsilon, True)

            # sanity check
            if poly_approx.shape[0] != 4:
                continue

            # compute mean gradient magnitude allong contour
            contour_mask = numpy.zeros_like(img)
            cv2.drawContours(contour_mask, [poly_approx], 0, 1, 2)
            grad_mag = numpy.mean(sobel[contour_mask > 0])

            # keep stuff
            polygons.append(poly_approx.squeeze())
            grad_mags.append(grad_mag)

        # sort contours by gradient magnitude
        sorted_idx = numpy.argsort(grad_mags)[::-1]
        polygons = [polygons[idx] for idx in sorted_idx]

        # Gets the largest polygon
        polygon = polygons[0].astype(numpy.float32)

        # Check that the largest polygon is large enough
        logging.info('Found largest polygon {0}'.format(polygon))
        polygon_length = self.polygon_length(polygon)
        logging.info('Polygon size: {0}'.format(polygon_length))
        if polygon_length < self.polygon_length_threshold:
            logging.info('Largest detected polygon is too small,'
                         ' assuming the image does not follow the assumptions'
                         ' of the perspective warp preprocessor.')
            return image

        # define registration reference points
        ref_points = numpy.array([[self.w - 1, h - 1],
                                  [0, h - 1],
                                  [0, 0],
                                  [self.w - 1, 0]], dtype="float32")


        # fix order of contour points for homography computation
        polygon = polygons[0].astype(numpy.float32)

        # from scipy.spatial.distance import cdist
        # distances = cdist(numpy.asarray([self.w, h])[numpy.newaxis], polygon)
        # closest_idx = numpy.argmin(distances)
        # new_order = [numpy.mod(closest_idx + i, len(polygon)) for i in xrange(len(polygon))]
        # polygon = polygon[new_order]

        # The polygon points should be rotated so that they match
        # the orientation of the ref_points.
        polygon = self.orient_polygon(img, polygon, ref_points,
                                      shape=(self.w, h))

        # compute homography to reference A4 image
        H, status = cv2.findHomography(polygon, ref_points,
                                       method=1, ransacReprojThreshold=3.0)

        # apply homography
        warped_img = cv2.warpPerspective(img, H, (self.w, h))

        if not self.are_stafflines_horizontal(warped_img):
            logging.info('Detected that staffs might be vertical,'
                         ' rotating image CCW...')
            warped_img = numpy.rot90(warped_img, k=1)

        return warped_img


    def orient_polygon(self, img, polygon, ref_points, shape):
        """Guesses how to align the polygon points and ref points,
        so that the warp orients the sheet correctly."""
        from scipy.spatial.distance import cdist
        distances = cdist(numpy.asarray(shape)[numpy.newaxis], polygon)
        closest_idx = numpy.argmin(distances)
        new_order = [numpy.mod(closest_idx + i, len(polygon)) for i in xrange(len(polygon))]
        polygon = polygon[new_order]
        return polygon


    def are_stafflines_horizontal(self, warped_img):
        """Guesses whether the image is oriented correctly (portrait
        or landscape). Based on the assumption that stafflines are responsible
        for most of the Sobel gradients in the direction perpendicular to
        them. Therefore, if the vertical Sobel gradient magnitudes
        are smaller than the horizontal ones, the stafflines are currently
        vertical, and the image should be rotated (although the width
        and height should stay)."""
        import cv2
        _, warped_binary = cv2.threshold(warped_img, 0, maxval=255, type=cv2.THRESH_OTSU)
        sobel_horz = cv2.Sobel(warped_binary, cv2.CV_64F, 1, 0, ksize=5)
        sobel_vert = cv2.Sobel(warped_binary, cv2.CV_64F, 0, 1, ksize=5)

        sobel_horz_mag = (sobel_horz ** 2).sum()
        sobel_vert_mag = (sobel_vert ** 2).sum()

        if sobel_horz_mag > sobel_vert_mag:
            return False
        else:
            return True

    def __ptdist(self, x, y):
        return numpy.sqrt(((x - y) ** 2.).sum())

    def polygon_length(self, polygon):
        if len(polygon) < 2:
            return 0

        l = 0
        for x, y in zip(polygon[:-1], polygon[1:]):
            l += self.__ptdist(x, y)
        l += self.__ptdist(polygon[-1], polygon[0])

        return l