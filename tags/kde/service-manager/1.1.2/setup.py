#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005,2006 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.

import os
import sys
import glob
import shutil

import kdedistutils

version = "1.1.2"

distfiles = """
    AUTHORS
    README
    COPYING
    *.py
    src/*.py
    src/*.ui
    src/*.desktop
    src/*.png
    po/*.po
    po/*.pot
"""

def make_dist():
    distdir = "service-manager-%s" % version
    list = []
    for t in distfiles.split():
        list.extend(glob.glob(t))
    if os.path.exists(distdir):
        shutil.rmtree(distdir)
    os.mkdir(distdir)
    for file_ in list:
        cum = distdir[:]
        for d in os.path.dirname(file_).split('/'):
            dn = os.path.join(cum, d)
            cum = dn[:]
            if not os.path.exists(dn):
                os.mkdir(dn)
        shutil.copy(file_, os.path.join(distdir, file_))
    os.popen("tar -cjf %s %s" % ("service-manager-" + version + ".tar.bz2", distdir))
    shutil.rmtree(distdir)

if "dist" in sys.argv:
    make_dist()
    sys.exit(0)

kdedistutils.setup(
    name="service-manager",
    version="1.1.2",
    author="Bahadır Kandemir",
    author_email="bahadir@pardus.org.tr",
    min_kde_version = "3.5.0",
    min_qt_version = "3.3.5",
    license = "GPL",
    application_data = ['src/mainform.ui', 'src/service-manager.py',
                        ('/usr/kde/3.5/share/icons/hicolor/128x128/apps', ['src/service_manager.png']),
                        'help'],
    executable_links = [('service-manager','service-manager.py')],
    i18n = ('po',['src']),
    kcontrol_modules = [ ('src/service-manager.desktop','src/service-manager.py')],
    )
