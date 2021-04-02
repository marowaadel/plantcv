# Help visualize histograms for hyperspectral images

import os
import cv2
import numpy as np
import pandas as pd
from plantcv.plantcv._debug import _debug
from plantcv.plantcv import fatal_error, params, outputs, color_palette
from plotnine import ggplot, aes, geom_line, geom_errorbar, scale_x_continuous, scale_color_manual
from plantcv.plantcv.visualize import histogram
from plantcv.plantcv.hyperspectral import _find_closest


'''
    == A few notes about color ==

    Color   Wavelength(nm) Frequency(THz)
    Red     620-750        484-400
    Orange  590-620        508-484
    Yellow  570-590        526-508
    Green   495-570        606-526
    Blue    450-495        668-606
    Violet  380-450        789-668

    f is frequency (cycles per second)
    l (lambda) is wavelength (meters per cycle)
    e is energy (Joules)
    h (Plank's constant) = 6.6260695729 x 10^-34 Joule*seconds
                         = 6.6260695729 x 10^-34 m^2*kg/seconds
    c = 299792458 meters per second
    f = c/l
    l = c/f
    e = h*f
    e = c*h/l

    List of peak frequency responses for each type of 
    photoreceptor cell in the human eye:
        S cone: 437 nm
        M cone: 533 nm
        L cone: 564 nm
        rod:    550 nm in bright daylight, 498 nm when dark adapted. 
                Rods adapt to low light conditions by becoming more sensitive.
                Peak frequency response shifts to 498 nm.
'''


def _wavelength_to_rgb(wavelength, gamma=0.8):
    """
    # reference: "Wavelength to RGB in Python." Noah.org, . 20 Sep 2014, 06:38 UTC. 1 Apr 2021, 19:06 <https://www.noah.org/mediawiki-1.34.2/index.php?title=Wavelength_to_RGB_in_Python&oldid=7665>.
    # http://www.noah.org/wiki/Wavelength_to_RGB_in_Python

    This converts a given wavelength of light to an approximate RGB color value. The wavelength must be given in nanometers in the range from 380 nm through 750 nm
    (789 THz through 400 THz).

    Based on code by Dan Bruton
    http://www.physics.sfasu.edu/astro/color/spectra.html

    Inputs:
    wavelength: wavelength of a visible wavelength in nanometers range: (380, 750)
    gamma: (optional) gamma correction. default value = 0.8

    Returns
    :param wavelength: float
    :param gamma: (optional) float
    :return: tuple
    """

    wavelength = float(wavelength)
    if 380 <= wavelength <= 440:
        attenuation = 0.3 + 0.7 * (wavelength - 380) / (440 - 380)
        R, G, B = ((-(wavelength - 440) / (440 - 380)) * attenuation) ** gamma, 0.0, (1.0 * attenuation) ** gamma
    elif 440 <= wavelength <= 490:
        R, G, B = 0.0, ((wavelength - 440) / (490 - 440)) ** gamma, 1.0
    elif 490 <= wavelength <= 510:
        R, G, B = 0.0, 1.0, (-(wavelength - 510) / (510 - 490)) ** gamma
    elif 510 <= wavelength <= 580:
        R, G, B = ((wavelength - 510) / (580 - 510)) ** gamma, 1.0, 0.0
    elif 580 <= wavelength <= 645:
        R, G, B = 1.0, (-(wavelength - 645) / (645 - 580)) ** gamma, 0.0
    elif 645 <= wavelength <= 750:
        attenuation = 0.3 + 0.7 * (750 - wavelength) / (750 - 645)
        R, G, B = (1.0 * attenuation) ** gamma, 0.0, 0.0
    else:
        R, G, B = 0.0, 0.0, 0.0
    R *= 255
    G *= 255
    B *= 255
    return (int(R), int(G), int(B))


def _RGB_to_webcode(RGB_values):
    """
    RGB_value: a tuple of RGB values (0~255, uint8)
    """
    webcode = "#"
    for value in RGB_values:
        code_ = hex(value).replace('0x', '')
        code = code_.upper() if len(code_) > 1 else '0{}'.format(code_.upper())
        webcode += code
    return webcode


def hyper_histogram(array, mask, wvlengths=[480, 550, 670]):
    """This function calculates the histogram of selected wavelengths hyperspectral images
    The color of the histogram is based on the wavelength: if the wavelength is in the range of visible spectrum
    Inputs:
    array        = Hyperspectral data instance
    mask         = Binary mask made from selected contours
    wvlengths    = (optional) list of wavelengths to show histograms. default = [480,550,670]

    Returns:
    fig_hist = histogram figure

    :param array: plantcv.plantcv.classes.Spectral_data
    :param mask: numpy.array
    :param wvlengths: list
    :return: fig_hist: plotnine.ggplot.ggplot
    """

    # always sort desired wavelengths
    wvlengths.sort()

    wl_keys = array.wavelength_dict.keys()
    wls = np.array([float(i) for i in wl_keys])

    # spectral resolution of the spectral data
    diffs = [wls[i] - wls[i - 1] for i in range(1, len(wls))]
    spc_res = sum(diffs) / len(diffs)


    # check if the distance is greater than 2x the spectral resolution
    checks = [array.min_wavelength-wvlengths[i]>2*spc_res or wvlengths[i]-array.max_wavelength>2*spc_res for i in range(0,len(wvlengths))]

    if sum(checks) > 0:
        fatal_error(f"At least one band is too far from the available wavelength range: ({array.min_wavelength},{array.max_wavelength})!")

    # find indices of bands whose wavelengths are closest to desired ones
    match_ids = [_find_closest(wls, wv) for wv in wvlengths]

    # check if in the visible wavelengths range
    ids_vis = [idx for (idx,wv) in enumerate(wvlengths) if 380 <= wv <= 750]
    # invisible wavelengths
    ids_inv = [idx for (idx,wv) in enumerate(wvlengths) if wv < 380 or wv > 750]

    colors = []
    if len(ids_vis) < len(wvlengths):
        print("Warning: at least one of the desired wavelengths is not in the visible spectrum range!")
        if len(ids_inv) == len(wvlengths): # All wavelengths in invisible range
            colors = [tuple(x) for x in color_palette(len(wvlengths))]
    if len(colors) == 0:
        i = 0
        while i < len(wvlengths):
            if i in ids_vis:
                colors.append(_wavelength_to_rgb(wvlengths[i], gamma=0.8))
                i += 1
            else:
                c = tuple(color_palette(1)[0])
                if c not in colors:
                    colors.append(c)
                    i += 1

    array_data = array.array_data

    # List of wavelengths recorded created from parsing the header file will be string, make list of floats
    histograms = dict()
    hist_dataset = pd.DataFrame(columns=['reflectance'])
    debug = params.debug
    params.debug = None
    color_codes = []
    for i_wv, (wv, color) in enumerate(zip(wvlengths,colors)):
        idx = match_ids[i_wv]
        code_c = _RGB_to_webcode(color)
        color_codes.append(code_c)
        _, hist_data = histogram(array_data[:, :, idx], mask=mask, bins=100, hist_data=True)
        histograms[wv] = {"label": wv, "graph_color": code_c, "reflectance": hist_data['pixel intensity'].tolist(),
                          "hist": hist_data['proportion of pixels (%)'].tolist()}
        if i_wv == 0:
            hist_dataset['reflectance'] = hist_data['pixel intensity'].tolist()
        hist_dataset[wv] = hist_data['proportion of pixels (%)'].tolist()

    # Make the histogram figure using plotnine
    df_hist = pd.melt(hist_dataset, id_vars=['reflectance'], value_vars=wvlengths,
                      var_name='Wavelength (' + array.wavelength_units + ')', value_name='proportion of pixels (%)')

    fig_hist = (ggplot(df_hist, aes(x='reflectance', y='proportion of pixels (%)',
                                    color='Wavelength (' + array.wavelength_units + ')'))
                + geom_line()
                + scale_color_manual(color_codes)
                )
    params.debug = debug
    _debug(fig_hist, filename=os.path.join(params.debug_outdir, str(params.device) + '_histogram.png'))

    return fig_hist


