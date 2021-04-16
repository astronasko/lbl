#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# CODE NAME HERE

# CODE DESCRIPTION HERE

Created on 2021-03-23

@author: cook
"""
import os
from pathlib import Path
import shutil
from typing import List, Union

from lbl.core import base
from lbl.core import io
from lbl.core import logger
from lbl.core import base_classes


# =============================================================================
# Define variables
# =============================================================================
__NAME__ = 'resources.misc.py'
__version__ = base.__version__
__date__ = base.__date__
__authors__ = base.__authors__
# get classes
log = base_classes.log

# =============================================================================
# Define functions
# =============================================================================
def copy_readme(data_dir: str):
    """
    Copies the data structure read me to here

    :param data_dir: str, the data directory

    :return:
    """
    # get the path to this directory
    python_filename = __file__
    # get in directory
    inpath = Path(python_filename).parent
    # get out directory
    outpath = Path(data_dir)
    # check / make the outpath
    io.make_dir(outpath, '', 'Data', verbose=False)
    # construct path to read me
    input_path = inpath.joinpath('data_str_readme.md')
    # construct new path to read me
    output_path = outpath.joinpath('README.md')
    # check for output path
    if output_path.exists():
        return
    # else copy the file
    shutil.copy(str(input_path), str(output_path))


def move_log(data_dir: str, recipe: str):
    """
    Move the log file to the data directory

    :param data_dir: str, the data directory
    :param recipe: str, the name of the code used
    :return:
    """
    # check that log dir exists
    log_path = io.make_dir(data_dir, 'log', 'log')
    # make log file
    timenow = base.Time.now().fits
    datenow = str(timenow).split('T')[0]
    # clean recipe name
    recipe = recipe.replace('.py', '').replace(' ', '_')
    # construct log file name
    logfile = 'LOG-{0}-{1}.log'.format(datenow, recipe)
    # construct aboslute path
    log_path = os.path.join(log_path, logfile)
    # move log file
    log = logger.Log(filename=log_path)
    # update global call
    base_classes.log = log


def splash(name: str, instrument: str, cmdargs: Union[List[str], None] = None):
    # print splash
    msgs = ['']
    msgs += ['*' * 79]
    msgs += ['\t{0}']
    msgs += ['\t\tVERSION: {1}']
    msgs += ['\t\tINSTRUMENT: {2}']
    msgs += ['*' * 79]
    msgs += ['']
    margs = [name, __version__, instrument]
    # loop through messages
    for msg in msgs:
        log.info(msg.format(*margs))
    # add command line arguments (if not None)
    if cmdargs is not None:
        log.info('Command line arguments:')
        # loop around arguments and add
        for cmdmsg in cmdargs:
            log.info(cmdmsg)


def end(recipe: str):
    """
    print and end statement

    :param recipe: str, the recipe name

    :return: None - prints to screen / log
    """
    # print splash
    msgs = ['']
    msgs += ['*' * 79]
    msgs += ['{0} finished successfully']
    msgs += ['*' * 79]
    msgs += ['']
    margs = [recipe]
    # loop through messages
    for msg in msgs:
        log.info(msg.format(*margs))


# =============================================================================
# Start of code
# =============================================================================
if __name__ == "__main__":
    # print hello world
    print('Hello World')

# =============================================================================
# End of code
# =============================================================================