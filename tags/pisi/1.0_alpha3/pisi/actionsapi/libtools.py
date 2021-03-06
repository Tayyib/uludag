#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.

# Standard Python Modules
import os

# Pisi-Core Modules
import pisi.context as ctx

# ActionsAPI Modules
import pisi.actionsapi
from pisi.actionsapi.shelltools import *
import pisi.actionsapi.get as get

class RunTimeError(pisi.actionsapi.Error):
    def __init__(self, Exception):
        ctx.ui.error(Exception)

def preplib(sourceDirectory = '/usr/lib'):
    sourceDirectory = get.installDIR() + sourceDirectory
    if can_access_directory(sourceDirectory):
        if system('/sbin/ldconfig -n -N %s' % sourceDirectory):
            raise RunTimeError('!!! Running ldconfig failed...')

def preplib_so(sourceDirectory):
    pass

def gnuconfig_update():
    ''' copy newest config.* onto source\'s '''
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if file in ['config.sub', 'config.guess']:
                copy('/usr/share/gnuconfig/%s' % file, os.path.join(root, file))
                ctx.ui.info('GNU Config Update Finished.')

def libtoolize(parameters = ''):
    if system('/usr/bin/libtoolize %s' % parameters):
        raise RunTimeError('Running libtoolize failed...')

def gen_usr_ldscript(dynamicLib):

    makedirs('%s/usr/lib' % get.installDIR())

    destinationFile = open('%s/usr/lib/%s' % (get.installDIR(), dynamicLib), 'w')
    content = '''
/* GNU ld script
    Since Pardus has critical dynamic libraries
    in /lib, and the static versions in /usr/lib,
    we need to have a "fake" dynamic lib in /usr/lib,
    otherwise we run into linking problems.
*/
GROUP ( /lib/%s )
''' % dynamicLib

    destinationFile.write(content)
    destinationFile.close()
    chmod('%s/usr/lib/%s' % (get.installDIR(), dynamicLib))
