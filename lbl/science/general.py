#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# CODE NAME HERE

# CODE DESCRIPTION HERE

Created on 2021-03-16

@author: cook
"""
from astropy.io import fits
from astropy import constants
from astropy import units as uu
from astropy.table import Table
import numpy as np
from scipy import stats
from scipy.optimize import curve_fit
from typing import Any, Dict, List, Tuple, Union
import warnings

from lbl.core import base
from lbl.core import base_classes
from lbl.core import io
from lbl.core import math as mp
from lbl.instruments import default
from lbl.science import plot

# =============================================================================
# Define variables
# =============================================================================
__NAME__ = 'science.general.py'
__version__ = base.__version__
__date__ = base.__date__
__authors__ = base.__authors__
# get time from base
Time = base.AstropyTime
TimeDelta = base.AstropyTimeDelta
# get classes
Instrument = default.Instrument
ParamDict = base_classes.ParamDict
LblException = base_classes.LblException
log = base_classes.log
# get speed of light
speed_of_light_ms = constants.c.value


# =============================================================================
# Define functions
# =============================================================================
def make_ref_dict(inst: Instrument, reftable_file: str,
                  reftable_exists: bool, science_files: List[str],
                  mask_file: str) -> Dict[str, np.ndarray]:
    """
    Make the reference table dictionary

    :param inst: Instrument instance
    :param reftable_file: str, the ref table filename
    :param reftable_exists: bool, if True file exists and we load it
                            otherwise we create it
    :param science_files: list of absolute paths to science files
    :param mask_file: absolute path to mask file

    :return:
    """
    # get parameter dictionary of constants
    params = inst.params
    # storage for ref dictionary
    ref_dict = dict()
    # load the mask
    mask_table = inst.load_mask(mask_file)
    # -------------------------------------------------------------------------
    # deal with loading from file
    if reftable_exists:
        # load ref table from disk
        table = Table.read(reftable_file, format=params['REF_TABLE_FMT'])
        # copy columns
        ref_dict['ORDER'] = np.array(table['ORDER'])
        ref_dict['WAVE_START'] = np.array(table['WAVE_START'])
        ref_dict['WAVE_END'] = np.array(table['WAVE_END'])
        ref_dict['WEIGHT_LINE'] = np.array(table['WEIGHT_LINE'])
        ref_dict['XPIX'] = np.array(table['XPIX'])
        # ratio of expected VS actual RMS in difference of model vs line
        ref_dict['RMSRATIO'] = np.array(table['RMSRATIO'])
        # effective number of pixels in line
        ref_dict['NPIXLINE'] = np.array(table['NPIXLINE'])
        # mean line position in pixel space
        ref_dict['MEANXPIX'] = np.array(table['MEANXPIX'])
        # blaze value compared to peak for that order
        ref_dict['MEANBLAZE'] = np.array(table['MEANBLAZE'])
        # amp continuum
        ref_dict['AMP_CONTINUUM'] = np.array(table['AMP_CONTINUUM'])
        # Considering the number of pixels, expected and actual RMS,
        #     this is the likelihood that the line is acually valid from a
        #     Chi2 test point of view
        ref_dict['CHI2'] = np.array(table['CHI2'])
        # probability of valid considering the chi2 CDF for the number of DOF
        ref_dict['CHI2_VALID_CDF'] = np.array(table['CHI2_VALID_CDF'])
        # close table
        del table
    # -------------------------------------------------------------------------
    # deal with creating table
    else:
        # Question: always the same wave length solution ?
        # Question: Should this wave solution come from calib ?
        # load wave solution from first science file
        wavegrid = inst.get_wave_solution(science_files[0])
        # storage for vectors
        order, wave_start, wave_end, weight_line, xpix = [], [], [], [], []
        # loop around orders
        for order_num in range(wavegrid.shape[0]):
            # get the min max wavelengths for this order
            min_wave = np.min(wavegrid[order_num])
            max_wave = np.max(wavegrid[order_num])
            # build a mask for mask lines in this order
            good = mask_table['ll_mask_s'] > min_wave
            good &= mask_table['ll_mask_s'] < max_wave
            # if we have values then add to arrays
            if np.sum(good) > 0:
                # add an order flag
                order += list(np.repeat(order_num, np.sum(good) - 1))
                # get the wave starts
                wave_start += list(mask_table['ll_mask_s'][good][:-1])
                # get the wave ends
                wave_end += list(mask_table['ll_mask_s'][good][1:])
                # get the weights of the lines (only used to get systemic
                # velocity as a starting point)
                weight_line += list(mask_table['w_mask'][good][:-1])
                # spline x pixels using wave grid
                xgrid = np.arange(len(wavegrid[order_num]))
                xspline = mp.iuv_spline(wavegrid[order_num], xgrid)
                # get the x pixel vector for mask
                xpix += list(xspline(mask_table['ll_mask_s'][good][:-1]))
        # make xpix a numpy array
        xpix = np.array(xpix)
        # add to reference dictionary
        ref_dict['ORDER'] = np.array(order)
        ref_dict['WAVE_START'] = np.array(wave_start)
        ref_dict['WAVE_END'] = np.array(wave_end)
        ref_dict['WEIGHT_LINE'] = np.array(weight_line)
        ref_dict['XPIX'] = xpix
        # ratio of expected VS actual RMS in difference of model vs line
        ref_dict['RMSRATIO'] = np.zeros_like(xpix, dtype=float)
        # effective number of pixels in line
        ref_dict['NPIXLINE'] = np.zeros_like(xpix, dtype=int)
        # mean line position in pixel space
        ref_dict['MEANXPIX'] = np.zeros_like(xpix, dtype=float)
        # blaze value compared to peak for that order
        ref_dict['MEANBLAZE'] = np.zeros_like(xpix, dtype=float)
        # amp continuum
        ref_dict['AMP_CONTINUUM'] = np.zeros_like(xpix, dtype=float)
        # Considering the number of pixels, expected and actual RMS,
        #     this is the likelihood that the line is acually valid from a
        #     Chi2 test point of view
        ref_dict['CHI2'] = np.zeros_like(xpix, dtype=float)
        # probability of valid considering the chi2 CDF for the number of DOF
        ref_dict['CHI2_VALID_CDF'] = np.zeros_like(xpix, dtype=float)

        # ---------------------------------------------------------------------
        # convert ref_dict to table (for saving to disk
        ref_table = Table()
        for key in ref_dict.keys():
            ref_table[key] = np.array(ref_dict[key])
        # log writing
        log.logger.info('Writing ref table {0}'.format(reftable_file))
        # write to file
        io.write_table(reftable_file, ref_table,
                       fmt=inst.params['REF_TABLE_FMT'])

    # -------------------------------------------------------------------------
    # return table (either loaded from file or constructed from mask +
    #               wave solution)
    return ref_dict


def get_velo_scale(wave_vector: np.ndarray, hp_width: float) -> int:
    """
    Calculate the velocity scale give a wave vector and a hp width

    :param wave_vector: np.ndarray, the wave vector
    :param hp_width: float, the hp width

    :return: int, the velocity scale in pixels
    """
    # work out the velocity scale
    dwave = np.gradient(wave_vector)
    dvelo = 1 / mp.nanmedian((wave_vector / dwave) / speed_of_light_ms)
    # velocity pixel scale (to nearest pixel)
    width = int(hp_width / dvelo)
    # make sure pixel width is odd
    if width % 2 == 0:
        width += 1
    # return  velocity scale
    return width


def spline_template(inst: Instrument, template_file: str,
                    systemic_vel: float) -> Dict[str, mp.IUVSpline]:
    """
    Calculate all the template splines (for later use)

    :param inst: Instrument instance
    :param template_file: str, the absolute path to the template file
    :param systemic_vel: float, the systemic velocity
    :return:
    """
    # log that we are producing all template splines
    msg = 'Defining all the template splines required later'
    log.logger.info(msg)
    # get the pixel hp_width [needs to be in m/s]
    hp_width = inst.params['HP_WIDTH'] * 1000
    # load the template
    template_table = inst.load_template(template_file)
    # get properties from template table
    twave = np.array(template_table['wavelength'])
    tflux = np.array(template_table['flux'])
    tflux0 = np.array(template_table['flux'])
    # -------------------------------------------------------------------------
    # work out the velocity scale
    width = get_velo_scale(twave, hp_width)
    # -------------------------------------------------------------------------
    # we high-pass on a scale of ~101 pixels in the e2ds
    tflux -= mp.lowpassfilter(tflux, width=width)
    # -------------------------------------------------------------------------
    # get the gradient of the log of the wave
    grad_log_wave = np.gradient(np.log(twave))
    # get the derivative of the flux
    dflux = np.gradient(tflux) / grad_log_wave / speed_of_light_ms
    # get the 2nd derivative of the flux
    ddflux = np.gradient(dflux) / grad_log_wave / speed_of_light_ms
    # get the 3rd derivative of the flux
    dddflux = np.gradient(ddflux) / grad_log_wave / speed_of_light_ms
    # -------------------------------------------------------------------------
    # we create the spline of the template to be used everywhere later
    valid = np.isfinite(tflux) & np.isfinite(dflux)
    valid &= np.isfinite(ddflux) & np.isfinite(dddflux)
    # -------------------------------------------------------------------------
    # doppler shift wave grid with respect to systemic velocity
    ntwave = mp.doppler_shift(twave[valid], -systemic_vel)
    # -------------------------------------------------------------------------
    # storage for splines
    sps = dict()
    # template removed from its systemic velocity, the spline is redefined
    #   for good
    k_order = 5
    # flux, 1st and 2nd derivatives
    sps['spline0'] = mp.iuv_spline(ntwave, tflux0[valid], k=k_order, ext=1)
    sps['spline'] = mp.iuv_spline(ntwave, tflux[valid], k=k_order, ext=1)
    sps['dspline'] = mp.iuv_spline(ntwave, dflux[valid], k=k_order, ext=1)
    sps['ddspline'] = mp.iuv_spline(ntwave, ddflux[valid], k=k_order, ext=1)
    sps['dddspline'] = mp.iuv_spline(ntwave, dddflux[valid], k=k_order, ext=1)
    # -------------------------------------------------------------------------
    # we create a mask to know if the splined point  is valid
    tmask = np.isfinite(tflux).astype(float)
    # Question: Should this be template['wavelength'][valid] or not?
    sps['spline_mask'] = mp.iuv_spline(ntwave, tmask[valid], k=1, ext=1)
    # -------------------------------------------------------------------------
    # return splines
    return sps


def rough_ccf_rv(inst: Instrument, wavegrid: np.ndarray,
                 sci_data: np.ndarray, wave_mask: np.ndarray,
                 weight_line: np.ndarray) -> Tuple[float, float]:
    """
    Perform a rough CCF calculation of the science data

    :param inst: Instrument instance
    :param wavegrid: wave grid (shape shape as sci_data)
    :param sci_data: spectrum
    :param wave_mask: list of wavelength centers of mask lines
    :param weight_line: list of weights for each mask line

    :return: tuple, 1. systemic velocity estimate, 2. ccf ewidth
    """
    # -------------------------------------------------------------------------
    # get parameters
    rv_min = inst.params['ROUGH_CCF_MIN_RV']
    rv_max = inst.params['ROUGH_CCF_MAX_RV']
    rv_step = inst.params['ROUGH_CCF_RV_STEP']
    rv_ewid_guess = inst.params['ROUGH_CCF_EWIDTH_GUESS']
    # -------------------------------------------------------------------------
    # if we have a 2D array make it 1D (but ignore overlapping regions)
    if wavegrid.shape[0] > 1:
        # 2D mask for making 2D --> 1D
        mask = np.ones_like(wavegrid, dtype=bool)
        # only include wavelengths for this order that don't overlap with
        #   the previous order
        for order_num in range(1, wavegrid.shape[0]):
            # elements where wavegrid doesn't overlap with previous
            porder = wavegrid[order_num] > wavegrid[order_num - 1, ::-1]
            # add to mask
            mask[order_num] &= porder
        # only include wavelengths for this order that don't overlap with the
        #   next order
        for order_num in range(0, wavegrid.shape[0] - 1):
            # elements where wavegrid doesn't overlap with next order
            norder = wavegrid[order_num] < wavegrid[order_num + 1, ::-1]
            # add to mask
            mask[order_num] &= norder
        # make sure no NaNs present
        mask &= np.isfinite(sci_data)
        # make the sci_data and wave grid are 1d
        wavegrid2 = wavegrid[mask]
        sci_data2 = sci_data[mask]
    # else we have a 1D array so just need to make sure no NaNs present
    else:
        # make sure no NaNs present
        mask = np.isfinite(sci_data)
        # apply mask to wavegrid and sci data
        wavegrid2 = wavegrid[mask]
        sci_data2 = sci_data[mask]
    # -------------------------------------------------------------------------
    # spline the science data
    spline_sp = mp.iuv_spline(wavegrid2, sci_data2, k=1, ext=1)
    # -------------------------------------------------------------------------
    # perform the CCF
    # -------------------------------------------------------------------------
    # define a delta velocity grid - in m/s for the CCF
    dvgrid = np.arange(rv_min, rv_max, rv_step)
    # set up the ccf vector
    ccf_vector = np.zeros_like(dvgrid)
    # log the we are computing the CCF
    log.logger.info('\t\tComputing CCF')
    # loop around dv elements
    for dv_element in range(len(dvgrid)):
        # calculate the spline on to the doppler shifted dv value
        shift = spline_sp(mp.doppler_shift(wave_mask, dvgrid[dv_element]))
        # ccf is the sum of these shifts
        ccf_vector[dv_element] = mp.nansum(weight_line * shift)
    # -------------------------------------------------------------------------
    # fit the CCF
    # -------------------------------------------------------------------------
    # get the position of the maximum CCF
    ccfmax = np.argmax(ccf_vector)
    # guess the amplitude (minus the dc level)
    ccf_dc = mp.nanmedian(ccf_vector)
    ccf_amp = ccf_vector[ccfmax] - ccf_dc
    # construct a guess of a guassian fit to the CCF
    #    guess[0]: float, the mean position
    #    guess[1]: float, the ewidth
    #    guess[2]: float, the amplitude
    #    guess[3]: float, the dc level
    #    guess[4]: float, the float (x-x0) * slope
    guess = [dvgrid[ccfmax], rv_ewid_guess, ccf_amp, ccf_dc, 0.0]
    # push into curve fit
    # TODO: catch bad and skip this observation
    with warnings.catch_warnings(record=True) as _:
        gcoeffs, pcov = curve_fit(mp.gauss_fit_s, dvgrid, ccf_vector, p0=guess)
    # record the systemic velocity and the FWHM
    systemic_velocity = gcoeffs[0]
    ccf_ewidth = gcoeffs[1]
    # fit ccf
    ccf_fit = mp.gauss_fit_s(dvgrid, *gcoeffs)
    # -------------------------------------------------------------------------
    # debug plot
    # -------------------------------------------------------------------------
    plot.plot_ccf(inst, dvgrid, ccf_vector, ccf_fit, gcoeffs)
    # -------------------------------------------------------------------------
    # return the systemic velocity and the ewidth
    return systemic_velocity, ccf_ewidth


def get_scaling_ratio(spectrum1: np.ndarray,
                      spectrum2: np.ndarray) -> float:
    """
    Get the scaling ratio that minimizes least-square between two spectra
    with a

    :param spectrum1: np.ndarray, the first spectrum
    :param spectrum2: np.ndarray, the second spectrum

    :return: float, the scaling ratio between spectrum 1 and 2
    """
    # calculate the spectra squared (used a few times)
    spectrum1_2 = spectrum1 ** 2
    spectrum2_2 = spectrum2 ** 2

    # find good values (non NaN)
    good = np.isfinite(spectrum1) & np.isfinite(spectrum2)
    # do not include points 5 sigma away from spectrum 1
    good &= np.abs(spectrum1) < mp.estimate_sigma(spectrum1) * 5
    # do not include points 5 sigma away from spectrum 2
    good &= np.abs(spectrum2) < mp.estimate_sigma(spectrum2) * 5
    # first estimate of amplitude sqrt(ratio of squares)
    ratio = mp.nansum(spectrum1_2[good]) / mp.nansum(spectrum2_2[good])
    amp = np.sqrt(ratio)
    # loop around iteratively
    for iteration in range(5):
        # get residuals between spectrum 1 and spectrum 2 * amplitude
        residuals = spectrum1 - (amp * spectrum2)
        # get the sigma of the residuals
        sigma_res = mp.estimate_sigma(residuals)
        # re-calculate good mask
        good = np.isfinite(spectrum1) & np.isfinite(spectrum2)
        good &= np.abs(residuals / sigma_res) < 3
        # calculate amp scale
        part1 = mp.nansum(residuals[good])
        part2 = mp.nansum(spectrum1_2[good])
        part3 = mp.nansum(spectrum2_2[good])
        scale = part1 / np.sqrt(part2 * part3)
        # ratio this off the amplitude
        amp = amp / (1 - scale)
    # return the scaling ratio (amp)
    return amp


def estimate_noise_model(spectrum: np.ndarray, model: np.ndarray,
                         npoints: int = 100) -> np.ndarray:
    """
    Estimate the noise on spectrum given the model

    :param spectrum: np.ndarray, the spectrum
    :param model: np.ndarray, the model
    :param npoints: int, the number of points to spline across

    :return: np.ndarray, the rms vector for this spectrum give the model
    """
    # storage for output rms
    rms = np.zeros_like(spectrum)
    # loop around each order and estimate noise model
    for order_num in range(spectrum.shape[0]):
        # get the residuals between science and model
        residuals = spectrum[order_num] - model[order_num]
        # get the pixels along the model to spline at (box centers)
        indices = np.arange(0, model.shape[1], npoints)
        # store the sigmas
        sigma = np.zeros_like(indices, dtype=float)
        # loop around each pixel and work out sigma value
        for it in range(len(indices)):
            # get start and end values for this box
            istart = indices[it] - npoints
            iend = indices[it] + npoints
            # fix boundary problems
            if istart < 0:
                istart = 0
            if iend > model.shape[1]:
                iend = model.shape[1]
            # work out the sigma of this box
            sigma[it] = mp.estimate_sigma(residuals[istart: iend])
            # set any zero values to NaN
            sigma[sigma == 0] = np.nan
        # Question: this was inside the loop - probably should be outside?
        # mask all NaN values
        good = np.isfinite(sigma)
        # if we have enough points calculate the rms
        if np.sum(good) > 2:
            # get the spline across all indices
            rms_spline = mp.iuv_spline(indices[good], sigma[good], k=1, ext=3)
            # apply the spline to the model positions
            rms[order_num] = rms_spline(np.arange(model.shape[1]))
        # else we don't have a noise model
        else:
            # we fill the rms with NaNs for each pixel
            rms[order_num] = np.full(model.shape[1], fill_value=np.nan)
    # return rms
    return rms


def bouchy_equation_line(vector: np.ndarray, diff_vector: np.ndarray,
                         mean_rms: np.ndarray) -> Tuple[float, float]:
    """
    Apply the Bouchy 2001 equation to a vector for the diff

    :param vector: np.ndarray, the vector
    :param diff_vector: np.ndarray, the difference between model and vector
                             i.e. diff = (vector - model) * weights
    :param mean_rms: np.ndarray, the mean rms for this line

    :return: tuple, 1. float, the Bouchy line value, 2. float, the rms of the
             Bouchy line value
    """
    with warnings.catch_warnings(record=True) as _:
        # work out the rms
        rms_pix = mean_rms / vector
        # work out the RV error
        rms_value = 1 / np.sqrt(np.sum(1 / rms_pix ** 2))
        # feed the line
        value = mp.nansum(diff_vector * vector) / mp.nansum(vector ** 2)
    # return the value and rms of the value
    return value, rms_value


def compute_rv(inst: Instrument, sci_iteration: int,
               sci_data: np.ndarray, sci_hdr: fits.Header,
               splines: Dict[str, Any], ref_table: Dict[str, Any],
               blaze: np.ndarray, systemic_all: np.ndarray,
               mjdate_all: np.ndarray, ccf_ewidth: Union[float, None] = None,
               reset_rv: bool = True) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Compute the RV using a line-by-line analysis

    :param inst: Instrument instance
    :param sci_iteration: int, the science files iteration number
    :param sci_data: np.ndarray, the science data
    :param sci_hdr: fits.Header, the science header
    :param splines: Dict, the dictionary of template splines
    :param ref_table: Dict, the reference table
    :param blaze: np.ndarray, the blaze to correct the science data
    :param systemic_all: np.ndarray, the systemic velocity storage for all
                         science file (filled in function for this iteration)
    :param mjdate_all: np.ndarray, the mid exposure time in mjd for all
                       science files (filled in function for this iteration)
    :param ccf_ewidth: None or float, the ccf_ewidth to use (if set)
    :param reset_rv: bool, whether convergence failed in previous
                               iteration (first iteration always False)

    :return: tuple, 1. the reference table dict, 2. the output dictionary
    """

    # -------------------------------------------------------------------------
    # get parameters from inst.params
    # -------------------------------------------------------------------------
    # get the noise model switch
    use_noise_model = inst.params['USE_NOISE_MODEL']
    # get the pixel hp_width [needs to be in m/s]
    hp_width = inst.params['HP_WIDTH'] * 1000
    # get the object science name
    object_science = inst.params['OBJECT_SCIENCE']
    # get the mid exposure header key
    mid_exp_time_key = inst.params['KW_MID_EXP_TIME']
    # get the number of iterations to do to compute the rv
    compute_rv_n_iters = inst.params['COMPUTE_RV_N_ITERATIONS']
    # get plot order
    model_plot_orders = inst.params['COMPUTE_MODEL_PLOT_ORDERS']
    # get the minimum line width (in pixels) to consider line valid
    min_line_width = inst.params['COMPUTE_LINE_MIN_PIX_WIDTH']
    # get the threshold in sigma on nsig (dv / dvrms) to keep valid
    nsig_threshold = inst.params['COMPUTE_LINE_NSIG_THRES']
    # define the fraction of the bulk error the rv mean must be above
    #    for compute rv to have converged
    converge_thres = inst.params['COMPUTE_RV_BULK_ERROR_CONVERGENCE']
    # define the maximum number of iterations deemed to lead to a good RV
    max_good_num_iters = inst.params['COMPUTE_RV_MAX_N_GOOD_ITERS']
    # -------------------------------------------------------------------------
    # deal with noise model
    if use_noise_model:
        # Question: where is this noise model function?
        # rms = get_noise_model(science_files)
        rms = np.zeros_like(sci_data)
    else:
        rms = np.zeros_like(sci_data)
    # -------------------------------------------------------------------------
    # copy science data
    sci_data0 = np.array(sci_data)
    # get the mid exposure time in MJD
    mjdate = io.get_hkey(sci_hdr, mid_exp_time_key)
    # -------------------------------------------------------------------------
    # get the wave grid for this science data
    # -------------------------------------------------------------------------
    # instrument specific wave solution --> use instrument method
    wavegrid = inst.get_wave_solution(data=sci_data, header=sci_hdr)
    # loop around orders
    for order_num in range(sci_data.shape[0]):
        # work out the velocity scale
        width = get_velo_scale(wavegrid[order_num], hp_width)
        # we high-pass on a scale of ~101 pixels in the e2ds
        sci_data[order_num] -= mp.lowpassfilter(wavegrid[order_num],
                                                width=width)
    # -------------------------------------------------------------------------
    # get BERV
    # -------------------------------------------------------------------------
    # instrument specific berv --> use instrument method
    berv = inst.get_berv(sci_hdr)
    # -------------------------------------------------------------------------
    # Systemic velocity estimate
    # -------------------------------------------------------------------------
    # deal with first estimate of RV / CCF equivalent width
    if reset_rv:
        # if we are not using FP file
        if 'FP' not in object_science:
            # calculate the rough CCF RV estimate
            sys_rv, ewidth = rough_ccf_rv(inst, wavegrid, sci_data,
                                          ref_table['WAVE_START'],
                                          ref_table['WEIGHT_LINE'])
            # if ccf width is not set then set it and log message
            if ccf_ewidth is None:
                ccf_ewidth = float(ewidth)
                # log ccf ewidth
                msg = '\t\tCCF e-width = {0:.2f} m/s'
                margs = [ccf_ewidth]
                log.logger.info(msg.format(*margs))
        else:
            sys_rv, ccf_ewidth = 0, 0
    # for FP files
    else:
        # use the systemic velocity from closest date
        closest = np.argmin(mjdate - mjdate_all)
        # get the closest system rv to this observation
        sys_rv = systemic_all[closest]
    # -------------------------------------------------------------------------
    # iteration loop
    # -------------------------------------------------------------------------
    # a keep mask - for keep good mask lines
    mask_keep = np.ones_like(ref_table['ORDER'], dtype=bool)
    # store number of iterations required to converge
    num_to_converge = 0
    # set up models to spline onto
    model = np.zeros_like(sci_data)
    model0 = np.zeros_like(sci_data)
    dmodel = np.zeros_like(sci_data)
    ddmodel = np.zeros_like(sci_data)
    dddmodel = np.zeros_like(sci_data)
    # get the splines out of the spline dictionary
    spline0 = splines['spline0']
    spline = splines['spline']
    dspline = splines['dspline']
    ddspline = splines['ddspline']
    dddspline = splines['dddspline']
    spline_mask = splines['spline_mask']
    # set up storage for the dv, ddv, ddv and corresponding rms values
    #    fill with NaNs
    dv = np.full(len(ref_table['WAVE_START']), np.nan)
    ddv = np.full(len(ref_table['WAVE_START']), np.nan)
    dddv = np.full(len(ref_table['WAVE_START']), np.nan)
    dvrms = np.full(len(ref_table['WAVE_START']), np.nan)
    ddvrms = np.full(len(ref_table['WAVE_START']), np.nan)
    dddvrms = np.full(len(ref_table['WAVE_START']), np.nan)
    # stoarge for final rv values
    rv_final = np.full(len(ref_table['WAVE_START']), np.nan)
    # storage for plotting
    plot_dict = dict()
    # get zero time
    zero_time = Time.now()
    # storage of rmsratio
    stddev_nsig = np.nan
    # loop around iterations
    for iteration in range(compute_rv_n_iters):
        # add to the number of iterations used to converge
        num_to_converge += 1
        # get start time
        start_time = Time.now()
        # ---------------------------------------------------------------------
        # update model, dmodel, ddmodel, dddmodel
        # ---------------------------------------------------------------------
        # loop around each order and update model, dmodel, ddmodel, dddmodel
        for order_num in range(sci_data.shape[0]):
            # doppler shifted wave grid for this order
            wave_ord = mp.doppler_shift(wavegrid[order_num], -sys_rv)
            # get the blaze for this order
            blaze_ord = blaze[order_num]
            # get the low-frequency component out
            model_mask = np.ones_like(model[order_num])
            # add the spline mask values to model_mask (spline mask is 0 or 1)
            smask = spline_mask(wave_ord) < 0.99
            # set spline mask splined values to NaN
            model_mask[smask] = np.nan
            # RV shift the spline and correct for blaze and add model mask
            model[order_num] = spline(wave_ord) * blaze_ord * model_mask
            # work out the ratio between spectrum and model
            amp = get_scaling_ratio(sci_data[order_num], model[order_num])
            # apply this scaling ratio to the model
            model[order_num] = model[order_num] * amp
            # if this is the first iteration update model0
            if iteration == 0:
                # spline the original template and apply blaze
                model0[order_num] = spline0(wave_ord) * blaze_ord
                # get the median for the model and original spectrum
                med_model0 = mp.nanmedian(model0[order_num])
                med_sci_data_0 = mp.nanmedian(sci_data0)
                # normalize by the median
                model0[order_num] = model0[order_num] / med_model0
                # multiply by the median of the original spectrum
                model0[order_num] = model0[order_num] * med_sci_data_0
            # update the other splines
            dmodel[order_num] = dspline(wave_ord) * blaze_ord * amp
            ddmodel[order_num] = ddspline(wave_ord) * blaze_ord * amp
            dddmodel[order_num] = dddspline(wave_ord) * blaze_ord * amp
        # ---------------------------------------------------------------------
        # estimate rms
        # ---------------------------------------------------------------------
        # if we are not using a noise model - estimate the noise
        if not use_noise_model:
            rms = estimate_noise_model(sci_data, model)
        # ---------------------------------------------------------------------
        # work out dv line-by-line
        # ---------------------------------------------------------------------
        # get orders
        orders = ref_table['ORDER']
        # keep track of which order we are looking at
        current_order = None
        # set these for use/update later
        nwavegrid = mp.doppler_shift(wavegrid, -sys_rv)
        # get splines between shifted wave grid and pixel grid
        wave2pixlist = []
        xpix = np.arange(model.shape[1])
        for order_num in range(wavegrid.shape[0]):
            wave2pixlist.append(mp.iuv_spline(nwavegrid[order_num], xpix))
        # ---------------------------------------------------------------------
        # debug plot dictionary for plotting later
        if iteration == 1:
            plot_dict['WAVEGRID'] = nwavegrid
            plot_dict['MODEL'] = model
            plot_dict['PLOT_ORDERS'] = model_plot_orders
            plot_dict['LINE_ORDERS'] = []
            plot_dict['WW_ORD_LINE'] = []
            plot_dict['SPEC_ORD_LINE'] = []
        # ---------------------------------------------------------------------
        # loop through all lines
        for line_it in range(0, len(orders)):
            # get the order number for this line
            order_num = orders[line_it]
            # -----------------------------------------------------------------
            # if line has been flagged as bad (in all but the first iteration)
            #   skip this line
            if (iteration != 1) and not (mask_keep[line_it]):
                continue
            # -----------------------------------------------------------------
            # if this is a new order the get residuals for this order
            if order_num != current_order:
                # update current order
                current_order = int(order_num)
            # get this orders values
            ww_ord = nwavegrid[order_num]
            sci_ord = sci_data[order_num]
            wave2pix = wave2pixlist[order_num]
            rms_ord = rms[order_num]
            model_ord = model[order_num]
            dmodel_ord = dmodel[order_num]
            ddmodel_ord = ddmodel[order_num]
            dddmodel_ord = dddmodel[order_num]
            blaze_ord = blaze[order_num]
            # -----------------------------------------------------------------
            # get the start and end wavelengths and pixels for this line
            wave_start = ref_table['WAVE_START'][line_it]
            wave_end = ref_table['WAVE_END'][line_it]
            x_start, x_end = wave2pix([wave_start, wave_end])
            # round pixel positions to nearest pixel
            x_start, x_end = int(np.floor(x_start)), int(np.ceil(x_end))
            # -----------------------------------------------------------------
            # boundary conditions
            if (x_end - x_start) < min_line_width:
                mask_keep[line_it] = False
            # Question: Why not add these to the keep mask?
            if x_start < 0:
                continue
            # Question: Why is this shape[0] ?
            if x_end > ww_ord.shape[0] - 2:
                continue
            # -----------------------------------------------------------------
            # get weights at the edge of the domain. Pixels inside have a
            # weight of 1, at the edge, it's proportional to the overlap
            weight_mask = np.ones(x_end - x_start + 1)
            # deal with overlapping pixels (before start)
            if ww_ord[x_start] < wave_start:
                refdiff = ww_ord[x_start + 1] - wave_start
                wavediff = ww_ord[x_start + 1] = ww_ord[x_start]
                weight_mask[0] = refdiff / wavediff
            # deal with overlapping pixels (after end)
            if ww_ord[x_end + 1] > wave_end:
                refdiff = ww_ord[x_end] - wave_end
                wavediff = ww_ord[x_end + 1] - ww_ord[x_end]
                weight_mask[0] = 1 - (refdiff / wavediff)
            # get the x pixels
            xpix = np.arange(x_start, len(weight_mask) + x_start)
            # get mean xpix and mean blaze for line
            mean_xpix = mp.nansum(weight_mask * xpix) / mp.nansum(weight_mask)
            mean_blaze = blaze_ord[(x_start + x_end) // 2]
            # push mean xpix and mean blaze into ref table
            ref_table['MEANXPIX'][line_it] = mean_xpix
            ref_table['MEANBLAZE'][line_it] = mean_blaze
            # -----------------------------------------------------------------
            # add to the plots dictionary (for plotting later)
            if iteration == 1:
                plot_dict['LINE_ORDERS'] = [order_num]
                plot_dict['WW_ORD_LINE'] = [ww_ord[x_start:x_end + 1]]
                plot_dict['SPEC_ORD_LINE'] = [sci_ord[x_start:x_end + 1]]
            # -----------------------------------------------------------------
            # derivative of the segment
            d_seg = dmodel_ord[x_start: x_end + 1] * weight_mask
            # keep track of second and third derivatives
            dd_seg = ddmodel_ord[x_start: x_end + 1] * weight_mask
            ddd_seg = dddmodel_ord[x_start: x_end + 1] * weight_mask
            # residual of the segment
            sci_seg = sci_ord[x_start:x_end + 1]
            model_seg = model_ord[x_start:x_end + 1]
            diff_seg = (sci_seg - model_seg) * weight_mask
            # work out the sum of the weights of the weight mask
            sum_weight_mask = mp.nansum(weight_mask)
            # work out the sum of the rms
            sum_rms = mp.nansum(rms_ord[x_start: x_end + 1] * weight_mask)
            # work out the mean rms
            mean_rms = sum_rms / sum_weight_mask
            # -----------------------------------------------------------------
            # work out the 1st derivative
            #    From bouchy 2001 equation, RV error for each pixel
            # -----------------------------------------------------------------
            bout = bouchy_equation_line(d_seg, diff_seg, mean_rms)
            dv[line_it], dvrms[line_it] = bout
            # -----------------------------------------------------------------
            # work out the 2nd derivative
            #    From bouchy 2001 equation, RV error for each pixel
            # -----------------------------------------------------------------
            bout = bouchy_equation_line(dd_seg, diff_seg, mean_rms)
            ddv[line_it], ddvrms[line_it] = bout
            # -----------------------------------------------------------------
            # work out the 3rd derivative
            #    From bouchy 2001 equation, RV error for each pixel
            # -----------------------------------------------------------------
            bout = bouchy_equation_line(ddd_seg, diff_seg, mean_rms)
            ddv[line_it], ddvrms[line_it] = bout
            # -----------------------------------------------------------------
            # ratio of expected VS actual RMS in difference of model vs line
            ref_table['RMSRATIO'][line_it] = mp.nanstd(diff_seg) / mean_rms
            # effective number of pixels in line
            ref_table['NPIXLINE'][line_it] = len(diff_seg)
            # Considering the number of pixels, expected and actual RMS, this
            #   is the likelihood that the line is actually valid from chi2
            #   point of view
            ref_table['CHI2'][line_it] = mp.nansum((diff_seg / mean_rms) ** 2)
        # ---------------------------------------------------------------------
        # calculate the number of sigmas measured vs predicted
        nsig = dv / dvrms
        # remove nans
        nsig = nsig[np.isfinite(nsig)]
        # remove sigma outliers
        nsig = nsig[np.abs(nsig) < nsig_threshold]
        # get the sigma of nsig
        stddev_nsig = mp.estimate_sigma(nsig)
        # log the value
        msg = '\t\tstdev_meas/stdev_pred = {0:.2f}'
        margs = [stddev_nsig]
        log.logger.info(msg.format(*margs))
        # ---------------------------------------------------------------------
        # get the best etimate of the velocity and update sline
        rv_mean, bulk_error = mp.odd_ratio_mean(dv, dvrms)
        # get final rv value
        rv_final = np.array(dv + sys_rv - berv)
        # add mean rv to sys_rv
        sys_rv = sys_rv + rv_mean
        # get end time
        end_time = Time.now()
        # get duration
        duration = (end_time - start_time).to(uu.s).value
        # log stats to screen
        msgs = []
        msgs += ['Iteration {0}: bulk error: {1:.2f} m/s rv = {2:.2f} m/s']
        msgs += ['Iteration duration: {3:.4f}']
        msgs += ['RV = {4:.2f} m/s, sigma = {1:.2f} m/s']
        margs = [iteration, bulk_error, -sys_rv, duration, rv_mean,
                 bulk_error]
        # loop around messages and add to log
        for msg in msgs:
            log.logger.info('\t\t' + msg.format(*margs))
        # ---------------------------------------------------------------------
        # do a convergence check
        if np.abs(rv_mean) < (converge_thres * bulk_error):
            # break here
            break
    # -------------------------------------------------------------------------
    # update reference table
    # -------------------------------------------------------------------------
    # express to have sign fine relative to convention
    ref_table['RV'] = -rv_final
    ref_table['DVRMS'] = dvrms
    # adding to the fits table the 2nd derivative projection
    ref_table['DDV'] = ddv
    ref_table['DDVRMS'] = ddvrms
    # adding to the fits table the 3rd derivative projection
    ref_table['DDDV'] = dddv
    ref_table['DDDVRMS'] = dddvrms
    # calculate the chi2 cdf
    chi2_cdf = 1 - stats.chi2.cdf(ref_table['CHI2'], ref_table['NPIXLINE'])
    ref_table['CHI2_VALID_CDF'] = chi2_cdf
    # -------------------------------------------------------------------------
    # update _all arrays
    # -------------------------------------------------------------------------
    # update the systemic velocity array
    systemic_all[sci_iteration] = sys_rv - berv
    # update the mjd date array
    mjdate_all[sci_iteration] = mjdate
    # -------------------------------------------------------------------------
    # Update convergence
    # -------------------------------------------------------------------------
    if num_to_converge >= max_good_num_iters:
        # flag that we need to take a completely new rv measurement
        reset_rv = True
        # log that rv did not converge
        wmsg = ('This RV is (probably) bed (iterations = {0}). '
                'Next step we will measure it with a CCF')
        wargs = [num_to_converge]
        log.logger.warning(wmsg.format(*wargs))

    else:
        # make sure we are not taking a completely new rv measurement
        reset_rv = False
        # log that rv converged
        msg = 'Compute RV converged in {0} steps'
        margs = [num_to_converge]
        log.logger.info(msg.format(*margs))
    # -------------------------------------------------------------------------
    # Log total time
    total_time = (Time.now() - zero_time).to(uu.s).value
    # -------------------------------------------------------------------------
    # save outputs to dictionary
    outputs = dict()
    outputs['SYSTEMIC_ALL'] = systemic_all
    outputs['MJDATE_ALL'] = mjdate_all
    outputs['RESET_RV'] = reset_rv
    outputs['NUM_ITERATIONS'] = num_to_converge
    outputs['SYSTEMIC_VELOCITY'] = sys_rv
    outputs['RMSRATIO'] = stddev_nsig
    outputs['CCF_EW'] = ccf_ewidth
    outputs['HP_WIDTH'] = hp_width
    outputs['TOTAL_DURATION'] = total_time
    # -------------------------------------------------------------------------
    # return reference table and outputs
    return ref_table, outputs


def smart_timing(durations: List[float], left: int) -> Tuple[float, float, str]:
    """
    Calculate the mean time taken per iteration, the standard deviation in
    time taken per iteration and a time left string (smart)

    :param durations: List of floats, the durations we already have
    :param left: int, the number of iterations left

    :return: tuple, 1. the mean time of iterations, 2. the std of the iterations
             3. an estimate of the time left as a string (HH:MM:SS)
    """
    # deal with not enough stats to work out values
    if len(durations) < 2:
        return np.nan, np.nan, ''
    # work out the mean time
    mean_time = mp.nanmean(durations)
    # work out the std time
    std_time = mp.nanmean(durations)
    # get time delta
    timedelta = TimeDelta(mean_time * left * uu.s)
    # get in hh:mm:ss format
    time_left = timedelta.to_datatime.__str__()
    # return values
    return mean_time, std_time, time_left


# =============================================================================
# Start of code
# =============================================================================
if __name__ == "__main__":
    # print hello world
    print('Hello World')

# =============================================================================
# End of code
# =============================================================================