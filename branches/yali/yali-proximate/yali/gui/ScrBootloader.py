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

import yali.context as ctx
from yali.gui.ScreenWidget import ScreenWidget
from yali.gui.Ui.bootloaderwidget import Ui_BootLoaderWidget
from yali.storage.bootloader import BOOT_TYPE_NONE, BOOT_TYPE_PARTITION, BOOT_TYPE_MBR, BOOT_TYPE_RAID, BootLoaderError, boot_type_strings

class Widget(QtGui.QWidget, ScreenWidget):
    title = _("Configure Bootloader")
    icon = "utilities-terminal"
    helpSummary = _("A bootloader is a tiny program that runs when a computer is first powered up.")
    help = _("""
<p>
A bootloader is a tiny program that runs when a computer is first powered up.
It is responsible for loading the operating system into memory and then transferring
the control to it.
</p>
<p>
Pardus uses GRUB (GRand Unified Bootloader) as the default bootloader. GRUB allows you
to boot any supported operating system by presenting the user with a menu.
</p>
<p>
The recommended way to use GRUB is to install it to the beginning of the boot disk.
You can always choose another installation method if you know what you are doing.
</p>
""")

    def __init__(self, *args):
        QtGui.QWidget.__init__(self,None)
        self.ui = Ui_BootLoaderWidget()
        self.ui.setupUi(self)
        self.bootloader = ctx.bootloader
        self.bootloader.storage = ctx.storage
        self.default = None
        self.device = None
        self.bootDisk = None
        self.bootPartition = None

        self.connect(self.ui.noInstall, SIGNAL("toggled(bool)"), self.deactivateBootloader)
        self.connect(self.ui.installPartition, SIGNAL("toggled(bool)"), self.activateInstallPartition)
        self.connect(self.ui.drives, SIGNAL("currentIndexChanged(int)"), self.currentDeviceChanged)

    def fillDrives(self):
        self.ui.drives.clear()
        for drive in self.bootloader.drives:
            device = ctx.storage.devicetree.getDeviceByName(drive)
            item = u"%s" % (device.name)
            self.ui.drives.addItem(item, device)

    def shown(self):
        self.fillDrives()
        self.activateChoices()

    def backCheck(self):
        if ctx.storage.doAutoPart:
            ctx.mainScreen.stepIncrement = 2
        return True

    def execute(self):
        self.bootloader.device = self.device
        if self.ui.noInstall.isChecked():
            self.bootloader.bootType = BOOT_TYPE_NONE
        elif self.ui.installPartition.isChecked():
            self.bootloader.bootType = BOOT_TYPE_PARTITION
        elif self.ui.installMBR.isChecked():
            self.bootloader.bootType = BOOT_TYPE_MBR

        return True

    def activateChoices(self):
        for choice, (device, bootType) in self.bootloader.choices.items():
            if choice == BOOT_TYPE_MBR:
                self.ui.installMBR.setText("The first sector of")
                self.bootDisk = self.bootloader.choices[BOOT_TYPE_MBR][0]
            elif choice == BOOT_TYPE_RAID:
                self.ui.installMBR.setText("The RAID array where Pardus is installed")
                self.bootPartition = self.bootloader.choices[BOOT_TYPE_RAID][0]
            elif choice == BOOT_TYPE_PARTITION:
                self.ui.installPartition.setText("The partition where Pardus is installed")
                self.bootPartition = self.bootloader.choices[BOOT_TYPE_PARTITION][0]

        if self.bootDisk:
            self.default = self.bootDisk
            self.ui.installMBR.setChecked(True)
        else:
            self.default = self.bootPartition
            self.ui.installPartition.setChecked(True)

    def deactivateBootloader(self):
        self.device = None

    def activateInstallPartition(self, state):
        if state:
            self.device =  self.bootPartition

    def currentDeviceChanged(self, index):
        if index != -1:
            self.device = self.ui.drives.itemData(index).toPyObject().name

