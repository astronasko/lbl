#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# CODE NAME HERE

# CODE DESCRIPTION HERE

Created on 2021-10-18

@author: artigau
"""
from lbl import compil
from lbl import compute

# =============================================================================
# Define variables
# =============================================================================
# define working directory
working = '/data/lbl/data/harps/'
# create keyword argument dictionary
keyword_args = dict()
# add keyword arguments
keyword_args['INSTRUMENT'] = 'HARPS'
keyword_args['DATA_DIR'] = working
keyword_args['TEMPLATE_SUBDIR'] = 'templates'
keyword_args['BLAZE_FILE'] = 'HARPS.2014-09-02T21_06_48.529_blaze_A.fits'
keyword_args['TEMPLATE_FILE'] = 'Template_Proxima-tc_HARPS.fits'
keyword_args['PLOT'] = False
keyword_args['PLOT_COMPUTE_CCF'] = keyword_args['PLOT']
keyword_args['PLOT_COMPUTE_LINES'] = keyword_args['PLOT']
keyword_args['PLOT_COMPIL_CUMUL'] = keyword_args['PLOT']
keyword_args['PLOT_COMPIL_BINNED'] = keyword_args['PLOT']
keyword_args['SKIP_DONE'] = False
keyword_args['MASK_SUBDIR'] = working + 'masks'
keyword_args['INPUT_FILE'] = working + 'science/Proxima-tc/HARPS*_e2ds_A.fits'
# add objects
objs = ['Proxima-tc']
templates = ['Proxima-tc']
# set which object to run
num = 0


# =============================================================================
# Start of code
# =============================================================================
if __name__ == "__main__":

    # TODO: add template test

    # TODO: add mask test

    # run compile
    tbl1 = compute(object_science=objs[num], object_template=templates[num],
                   **keyword_args)

    tbl2 = compil(object_science=objs[num], object_template=templates[num],
                  **keyword_args)

# =============================================================================
# End of code
# =============================================================================