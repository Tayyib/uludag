# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2010 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

import gettext
__trans = gettext.translation('yali', fallback=True)
_ = __trans.ugettext

from PyQt4 import QtGui
from PyQt4.QtCore import *

from yali.gui.ScreenWidget import ScreenWidget
from yali.gui.Ui.rootpasswidget import Ui_RootPassWidget
import yali.users
import yali.sysutils
import yali.context as ctx
import pardus.xorg

##
# Root password widget
class Widget(QtGui.QWidget, ScreenWidget):
    title = _("Choose an Administrator Password and a Hostname")
    icon = "meeting-participant"
    helpSummary = _("""Your password must be easy to remember but strong enough to resist possible attacks.
    You can use capital and lower-case letters, numbers and punctuation marks in your password.""")
    help = _("""
<p>
You need to define a password for the "root" user which is the conventional name
of the user who has all rights and permissions (to all files and programs) in all
modes (single or multi-user).
</p>

<p>
Your password must be easy to remember but strong enough to resist possible attacks.
You can use capital and lower-case letters, numbers and punctuation marks in your password.
</p>

<p>
You can also define a hostname for your computer. A hostname is an identifier assigned to your computer. As your computer will be recognized with this name in the local network, it is recommended to select a descriptive hostname.
</p>
""")

    def __init__(self, *args):
        QtGui.QWidget.__init__(self,None)
        self.ui = Ui_RootPassWidget()
        self.ui.setupUi(self)

        self.host_valid = True
        self.pass_valid = False

        self.connect(self.ui.pass1, SIGNAL("textChanged(const QString &)"),
                     self.slotTextChanged)
        self.connect(self.ui.pass2, SIGNAL("textChanged(const QString &)"),
                     self.slotTextChanged)
        self.connect(self.ui.pass2, SIGNAL("returnPressed()"),
                     self.slotReturnPressed)
        self.connect(self.ui.hostname, SIGNAL("textChanged(const QString &)"),
                     self.slotHostnameChanged)

    def shown(self):
        if ctx.installData.hostName:
            self.ui.hostname.setText(str(ctx.installData.hostName))
        else:
            # Use first added user's name as machine name if its exists
            release=open("/etc/pardus-release").read().split()
            releaseHostName = "".join(release[:2]).lower()
            if self.ui.hostname.text() == '':
                self.ui.hostname.setText(releaseHostName)

        if ctx.installData.rootPassword:
            self.ui.pass1.setText(ctx.installData.rootPassword)
            self.ui.pass2.setText(ctx.installData.rootPassword)

        self.setNext()
        self.checkCapsLock()
        self.ui.pass1.setFocus()

    def execute(self):
        ctx.installData.rootPassword = unicode(self.ui.pass1.text())
        ctx.installData.hostName = unicode(self.ui.hostname.text())
        return True

    def setCapsLockIcon(self, child):
        if type(child) == QtGui.QLineEdit:
            if pardus.xorg.capslock.isOn():
                child.setStyleSheet("""QLineEdit {
                        background-image: url(:/gui/pics/caps.png);
                        background-repeat: no-repeat;
                        background-position: right;
                        padding-right: 35px;
                        }""")
            else:
                child.setStyleSheet("""QLineEdit {
                        background-image: none;
                        padding-right: 0px;
                        }""")

    def checkCapsLock(self):
        for child in self.ui.groupBox.children():
            self.setCapsLockIcon(child)

    def keyReleaseEvent(self, e):
        self.checkCapsLock()

    def showError(self,message):
        ctx.yali.info.updateAndShow(message, type = "error")
        ctx.mainScreen.disableNext()

    def hideError(self):
        ctx.yali.info.hide()

    def slotTextChanged(self):

        p1 = self.ui.pass1.text()
        p2 = self.ui.pass2.text()

        if p1 == p2 and p1:
            if len(p1)<4:
                self.showError(_('Password is too short.'))
                self.pass_valid = False
            else:
                self.hideError()
                self.pass_valid = True
        else:
            self.pass_valid = False
            if p2:
                self.showError(_('Passwords do not match.'))
        if str(p1).lower()=="root" or str(p2).lower()=="root":
            self.pass_valid = False
            if p2:
                self.showError(_('Do not use your username as your password.'))
        if self.pass_valid:
            self.hideError()

        self.setNext()

    ##
    # check hostname validity
    def slotHostnameChanged(self, string):

        if not string.toAscii():
            self.host_valid = False
            self.setNext()
            return

        self.host_valid = yali.sysutils.isTextValid(string.toAscii())

        if not self.host_valid:
            self.showError(_('Hostname contains invalid characters.'))
        else:
            self.hideError()
        self.setNext()

    def setNext(self):
        if self.host_valid and self.pass_valid:
            ctx.mainScreen.enableNext()
        else:
            ctx.mainScreen.disableNext()

    def slotReturnPressed(self):
        if ctx.mainScreen.isNextEnabled():
            ctx.mainScreen.slotNext()

