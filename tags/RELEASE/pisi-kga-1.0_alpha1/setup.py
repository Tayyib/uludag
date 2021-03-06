#!/usr/bin/env python
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
#
#
# Authors:  İsmail Dönmez <ismail@uludag.org.tr>

import kdedistutils

kdedistutils.setup(
    name="pisi_kga",
    version="1.0_alpha1",
    author="İsmail Dönmez",
    author_email="ismail@uludag.org.tr",
    url="http://www.uludag.org.tr/projects/pisi",
    min_kde_version = "3.4.0",
    min_qt_version = "3.3.0",
    license = "GPL",
    application_data = ['src/PisiKga.py','src/Preferences.py','src/PreferencesWidget.ui',
                        'src/ThreadRunner.py','src/RepoDialog.ui','src/MainWindow.ui',
                        'src/ProgressDialog.ui','src/PisiUi.py'],
    executable_links = [('pisi_kga','PisiKga.py')],
    docbooks = [ ('doc/en','en') ],
    i18n = ('po',['src']),
    kcontrol_modules = [ ('src/pisi_kga.desktop','PisiKga.py')],
    )
