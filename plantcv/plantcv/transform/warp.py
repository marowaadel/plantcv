# warp image

import cv2
import skimage
import os
import numpy as np
from plantcv.plantcv import params
from plantcv.plantcv._debug import _debug
from plantcv.plantcv import fatal_error
from plantcv.plantcv import color_palette

from plantcv.plantcv.visualize import overlay_two_imgs


def warp_align(img, refimg, pts, refpts, method='default'):
    """Calculate a projective transform from 4 pairs of the corresponding points between image and reference image,
    then performs the projective transformation on input image to align the input image to reference image

    Inputs:
    img = image data to be warped
    refimg = image data to be used as reference
    pts = 4 coordinates on img
    refpts = 4 coordinates on refimg
    method = robust estimation algorithm when calculating projective transformation. 'default', 'ransac', 'lmeds', 'rho'
    Returns:
    mat = transformation matrix
    warped_img = warped image

    :param img: numpy.ndarray
    :param refimg: numpy.ndarray
    :param pts: list of tuples
    :param refpts: list of tuples
    :param method: str
    :return mat: numpy.ndarray
    :return warped_img: numpy.ndarray
    """

    params.device += 1

    if len(pts) != len(refpts):
        fatal_error('Please provide same number of corresponding coordinates.')

    # convert coordinates to int if not they are not int
    pts = [tuple(map(int, tup)) for tup in pts]
    refpts = [tuple(map(int, tup)) for tup in refpts]

    methods = {
        'default': 0,
        'ransac': cv2.RANSAC,
        'lmeds': cv2.LMEDS,
        'rho': cv2.RHO}

    shape_img = img.shape
    shape_ref = refimg.shape
    rows_ref, cols_ref = shape_ref[0:2]
    rows_img, cols_img = shape_img[0:2]

    # convert list of tuples to array for cv2 functions
    ptsarr = np.array(pts, dtype='float32')
    refptsarr = np.array(refpts, dtype='float32')

    # find tranformation matrix and warp
    mat, status = cv2.findHomography(ptsarr, refptsarr, method=methods.get(method))
    if mat is None:
        fatal_error( "Cannot calculate a robust with given corresponding coordinates and with desired robust estimation algorithm {}!".format(method))
    warped_img = cv2.warpPerspective(src=img, M=mat, dsize=(cols_ref, rows_ref))

    # preserve binary
    if len(np.unique(img)) == 2:
        warped_img[warped_img > 0] = 255

    if params.debug is not None:
        # scale marker_size and line_thickness for different resolutions

        if rows_img > rows_ref:
            res_ratio_i = int(np.ceil(rows_img / rows_ref))  # ratio never smaller than 1 with np.ceil
            res_ratio_r = 1
        else:
            res_ratio_r = int(np.ceil(rows_ref / rows_img))
            res_ratio_i = 1
        # marker colors
        colors = color_palette(len(pts))

        # rgb image for colored markers on img
        img_marked = img.copy()
        # convert to RGB image if not
        if len(shape_img) == 2:
            img_marked = cv2.cvtColor(img_marked, cv2.COLOR_GRAY2RGB)

        for i, pt in enumerate(pts):
            if status[i][0] == 1:
                cv2.drawMarker(img_marked, pt, color=colors[i], markerType=cv2.MARKER_CROSS,
                               markerSize=params.marker_size * res_ratio_i,
                               thickness=params.line_thickness * res_ratio_i)
            else:
                cv2.drawMarker(img_marked, pt, color=colors[i], markerType=cv2.MARKER_TRIANGLE_UP,
                               markerSize=params.marker_size * res_ratio_i,
                               thickness=params.line_thickness * res_ratio_i)

        # rgb image for colored markers on refimg
        refimg_marked = refimg.copy()
        if len(shape_ref) == 2:
            refimg_marked = cv2.cvtColor(refimg_marked, cv2.COLOR_GRAY2RGB)

        for i, pt in enumerate(refpts):
            if status[i][0] == 1:
                print("5")
                cv2.drawMarker(refimg_marked, pt, color=colors[i], markerType=cv2.MARKER_CROSS,
                               markerSize=params.marker_size * res_ratio_r,
                               thickness=params.line_thickness * res_ratio_r)
            else:
                print("6")
                cv2.drawMarker(refimg_marked, pt, color=colors[i], markerType=cv2.MARKER_TRIANGLE_UP,
                               markerSize=params.marker_size * res_ratio_r,
                               thickness=params.line_thickness * res_ratio_r)

        debug_mode = params.debug
        params.debug = None

        img_blend = overlay_two_imgs(warped_img, refimg)
        params.debug = debug_mode

        _debug(visual=img_marked, filename=os.path.join(params.debug_outdir, str(params.device) + "_img-to-warp.png"))
        _debug(visual=refimg_marked, filename=os.path.join(params.debug_outdir, str(params.device) + "_img-ref.png"))
        _debug(visual=img_blend, filename=os.path.join(params.debug_outdir, str(params.device) + "_warp_overlay.png"))

        # if params.debug == "print":
        #     print_image(img_marked, os.path.join(params.debug_outdir, str(params.device) + "_img-to-warp.png"))
        #     print_image(refimg_marked, os.path.join(params.debug_outdir, str(params.device) + "_img-ref.png"))
        #     print_image(img_blend, os.path.join(params.debug_outdir, str(params.device) + "_warp_overlay.png"))
        #
        # elif params.debug == "plot":
        #     plot_image(img_marked)
        #     plot_image(refimg_marked)
        #     plot_image(img_blend)

    return mat, warped_img
