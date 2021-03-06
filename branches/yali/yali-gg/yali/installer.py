# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2010 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#
import os
import dbus
import time
import shutil
import gettext

__trans = gettext.translation('yali', fallback=True)
_ = __trans.ugettext

from PyQt4 import QtGui
from PyQt4.QtCore import *

import pisi.ui
import yali.util
import yali.pisiiface
import yali.localeutils
import yali.context as ctx
from yali.installdata import YALI_DVDINSTALL, YALI_INSTALL, YALI_OEMINSTALL, YALI_FIRSTBOOT, YALI_PARTITIONER, YALI_RESCUE, YALI_PLUGIN
from yali.gui.YaliDialog import InformationWindow
from yali.storage.formats.filesystem import FilesystemResizeError, FilesystemMigrateError

# screens
import yali.gui.ScrKahyaCheck
import yali.gui.ScrWelcome
import yali.gui.ScrCheckCD
import yali.gui.ScrKeyboard
import yali.gui.ScrDateTime
import yali.gui.ScrAdmin
import yali.gui.ScrUsers
import yali.gui.ScrDriveSelection
import yali.gui.ScrPartitionAuto
import yali.gui.ScrPartitionManual
import yali.gui.ScrBootloader
import yali.gui.ScrInstallationAuto
import yali.gui.ScrInstall
import yali.gui.ScrSummary
import yali.gui.ScrGoodbye
import yali.gui.ScrRescue
import yali.gui.ScrRescueGrub
import yali.gui.ScrRescuePisi
import yali.gui.ScrRescuePassword
import yali.gui.ScrRescueFinish

class Yali:
    def __init__(self, install_type=YALI_INSTALL, install_plugin=None):

        self._screens = {}

        # Normal Installation process
        self._screens[YALI_INSTALL] = [                                  # Numbers can be used with -s paramter
                                       yali.gui.ScrKahyaCheck,          # 00
                                       yali.gui.ScrWelcome,             # 01
                                       yali.gui.ScrCheckCD,             # 02
                                       yali.gui.ScrKeyboard,            # 03
                                       yali.gui.ScrDateTime,            # 04
                                       yali.gui.ScrUsers,               # 05
                                       yali.gui.ScrAdmin,               # 06
                                       yali.gui.ScrDriveSelection,
                                       yali.gui.ScrPartitionAuto,       # 07
                                       yali.gui.ScrPartitionManual,     # 08
                                       yali.gui.ScrBootloader,          # 09
                                       yali.gui.ScrSummary,             # 10
                                       yali.gui.ScrInstall,             # 11
                                       yali.gui.ScrGoodbye              # 12
                                      ]

        self._screens[YALI_DVDINSTALL] = [                              # Numbers can be used with -s paramter
                                       yali.gui.ScrKahyaCheck,          # 00
                                       yali.gui.ScrWelcome,             # 01
                                       yali.gui.ScrCheckCD,             # 02
                                       yali.gui.ScrKeyboard,            # 03
                                       yali.gui.ScrDateTime,            # 04
                                       yali.gui.ScrUsers,               # 05
                                       yali.gui.ScrAdmin,               # 06
                                       yali.gui.ScrDriveSelection,
                                       yali.gui.ScrPartitionAuto,       # 07
                                       yali.gui.ScrPartitionManual,     # 08
                                       yali.gui.ScrBootloader,          # 09
                                       yali.gui.ScrInstallationAuto,    # 10
                                       yali.gui.ScrSummary,             # 11
                                       yali.gui.ScrInstall,             # 12
                                       yali.gui.ScrGoodbye              # 13
                                      ]

        # FirstBoot Installation process
        self._screens[YALI_FIRSTBOOT] = [                                # Numbers can be used with -s paramter
                                         yali.gui.ScrWelcome,           # 00
                                         yali.gui.ScrKeyboard,          # 01
                                         yali.gui.ScrDateTime,          # 02
                                         yali.gui.ScrUsers,             # 03
                                         yali.gui.ScrAdmin,             # 04
                                         yali.gui.ScrGoodbye            # 05
                                        ]

        # Oem Installation process
        self._screens[YALI_OEMINSTALL] = [                                  # Numbers can be used with -s paramter
                                          yali.gui.ScrWelcome,             # 00
                                          yali.gui.ScrCheckCD,             # 01
                                          yali.gui.ScrPartitionAuto,       # 02
                                          yali.gui.ScrPartitionManual,     # 03
                                          yali.gui.ScrBootloader,          # 04
                                          yali.gui.ScrSummary,             # 05
                                          yali.gui.ScrInstall,             # 06
                                          yali.gui.ScrGoodbye              # 07
                                         ]

        # Use YALI just for partitioning
        self._screens[YALI_PARTITIONER] = [
                                           yali.gui.ScrPartitionManual  # Manual Partitioning
                                          ]

        # Rescue Mode
        self._screens[YALI_RESCUE] = [
                                      yali.gui.ScrRescue,            # Rescue Mode
                                      yali.gui.ScrRescueGrub,        # Grub Rescue
                                      yali.gui.ScrRescuePisi,        # Pisi HS Rescue
                                      yali.gui.ScrRescuePassword,    # Password Rescue
                                      yali.gui.ScrRescueFinish       # Final step for rescue
                                     ]

        self.plugin = None

        # mutual exclusion
        self.mutex = QMutex()
        self.waitCondition = QWaitCondition()
        self.retryAnswer = False

        # Let the show begin..
        if install_type == YALI_PLUGIN:
            self.plugin  = self.getPlugin(install_plugin)
            if self.plugin:
                self.screens = self.plugin.config.screens
                # run plugins setup
                self.plugin.config.setup()
            else:
                install_type = YALI_INSTALL
                ctx.interface.messageWindow(_("Warning"),
                                            _("Plugin '%s' could not be loaded or found, switching to"
                                              "normal installation process." % install_plugin),
                                            type="warning", customIcon="error")

        if not self.plugin:
            self.screens = self._screens[install_type]

        self.install_type = install_type
        self.checkCDStop = True

    def getPlugin(self, p):
        try:
            _p = __import__("yali.plugins.%s.config" % p)
        except ImportError:
            return False
        plugin = getattr(_p.plugins,p)
        return plugin

    def checkCD(self, rootWidget):
        ctx.mainScreen.disableNext()
        ctx.mainScreen.disableBack()

        rootWidget.validationSucceedBox.hide()
        rootWidget.validationFailBox.hide()
        rootWidget.validationBox.show()
        #ctx.interface.informationWindow.update(_("Starting validation"))
        class PisiUI(pisi.ui.UI):
            def notify(self, event, **keywords):
                pass
            def display_progress(self, operation, percent, info, **keywords):
                pass

        yali.pisiiface.initialize(ui = PisiUI(), with_comar = False, nodestDir = True)
        yali.pisiiface.addCdRepo()
        ctx.mainScreen.processEvents()
        pkg_names = yali.pisiiface.getAvailablePackages()

        rootWidget.progressBar.setMaximum(len(pkg_names))

        cur = 0
        self.flag = 0
        for pkg_name in pkg_names:
            cur += 1
            ctx.logger.debug("Validating %s " % pkg_name)
            #ctx.interface.informationWindow.update(_("Validating %s") % pkg_name)
            if self.checkCDStop:
                continue
            try:
                yali.pisiiface.checkPackageHash(pkg_name)
                rootWidget.progressBar.setValue(cur)
            except:
                rc  = ctx.interface.messageWindow(_("Warning"),
                                                  _("Validation of %s package failed."
                                                    "Please remaster your installation medium and"
                                                    "reboot.") % pkg_name,
                                                  type="custom", customIcon="error",
                                                  customButtons=[_("Skip Validation"), _("Skip Package"), _("Reboot")],
                                                  default=0)
                self.flag = 1
                if not rc:
                    rootWidget.validationBox.hide()
                    rootWidget.validationFailBox.show()
                    ctx.mainScreen.enableNext()
                    break
                elif rc ==1:
                    continue
                else:
                    yali.util.reboot()


        if not self.checkCDStop and self.flag == 0:
            ctx.interface.informationWindow.update(_('<font color="#FFF"><b>Validation succeeded. You can proceed with the installation.</b></font>'))
            rootWidget.validationSucceedBox.show()
            rootWidget.validationBox.hide()
        else:
            ctx.interface.informationWindow.hide()
            rootWidget.progressBar.setValue(0)

        yali.pisiiface.removeRepo(ctx.consts.cd_repo_name)

        ctx.mainScreen.enableNext()
        ctx.mainScreen.enableBack()

        ctx.interface.informationWindow.hide()

    def storageComplete(self):
        title = None
        message = None
        details = None
        try:
            ctx.storage.doIt()
        except FilesystemResizeError as (msg, device):
            title = _("Resizing Failed")
            message = _("There was an error encountered while "
                        "resizing the device %s.") % (device,)
            details = "%s" %(msg,)

        except FilesystemMigrateError as (msg, device):
            title = _("Migration Failed")
            message = _("An error was encountered while "
                        "migrating filesystem on device %s.") % (device,)
            details = msg
        else:
            ctx.storage.turnOnSwap()
            ctx.storage.mountFilesystems(readOnly=False, skipRoot=False)
        finally:
            if title:
                rc = self.detailedMessageWindow(title, message, details,
                                                type = "custom",
                                                customButtons = [_("File Bug"), _("Exit installer")])

                if rc == 0:
                    raise
                elif rc == 1:
                    sys.exit(1)

    def fillFstab(self):
        ctx.storage.storageset.write(ctx.consts.target_dir)

    def backupInstallData(self):
        import piksemel

        def insert(root,tag,data):
            _ = root.insertTag(tag)
            _.insertData(str(data))

        # let create a yali piksemel..
        yali = piksemel.newDocument("yali")

        # let store keymap and language options
        # yali.insertTag("language").insertData(str(ctx.consts.lang))
        insert(yali,"language",ctx.consts.lang)
        insert(yali,"keymap",ctx.installData.keyData["xkblayout"])
        insert(yali,"variant",ctx.installData.keyData["xkbvariant"])

        # we will store passwords as shadowed..
        insert(yali,"root_password",yali.sysutils.getShadowed(ctx.installData.rootPassword or ""))

        # time zone..
        insert(yali,"timezone",ctx.installData.timezone)

        # hostname ..
        insert(yali,"hostname",ctx.installData.hostName)

        # users ..
        if len(yali.users.pending_users) > 0:
            users = yali.insertTag("users")
        for u in yali.users.pending_users:
            user = users.insertTag("user")
            insert(user,"username",u.username)
            insert(user,"realname",u.realname)
            insert(user,"password",yali.sysutils.getShadowed(u.passwd))
            insert(user,"groups",",".join(u.groups))

        # partitioning ..
        devices = []
        for dev in yali.storage.devices:
            if dev.getTotalMB() >= ctx.consts.min_root_size:
                devices.append(dev.getPath())

        partitioning = yali.insertTag("partitioning")
        partitioning.setAttribute("partition_type",
                                 {methodEraseAll:"auto",
                                  methodUseAvail:"smartAuto",
                                  methodManual:"manual"}[ctx.installData.autoPartMethod])
        if not ctx.installData.autoPartMethod == methodManual:
            try:
                partitioning.insertData("disk%d" % devices.index(ctx.installData.autoPartDev.getPath()))
            except:
                partitioning.insertData(ctx.installData.autoPartDev.getPath())

        ctx.installData.sessionLog = yali.toPrettyString()
        # ctx.logger.debug(yali.toPrettyString())

    def processPendingActions(self, rootWidget):
        rootWidget.steps.setOperations([{"text":_("Connecting to D-Bus..."),"operation":yali.postinstall.connectToDBus}])

        steps = [{"text":_("Setting hostname..."),"operation":yali.postinstall.setHostName},
                 {"text":_("Setting timezone..."),"operation":yali.postinstall.setTimeZone},
                 {"text":_("Setting root password..."),"operation":yali.postinstall.setRootPassword},
                 {"text":_("Adding users..."),"operation":yali.postinstall.addUsers},
                 {"text":_("Setting console keymap..."),"operation":yali.postinstall.writeConsoleData},
                 {"text":_("Migrating Xorg configuration..."),"operation":yali.postinstall.setKeymap}]

        stepsBase = [{"text":_("Copying repository index..."),"operation":yali.postinstall.copyPisiIndex},
                     {"text":_("Configuring other packages..."),"operation":yali.postinstall.setPackages},
                     {"text":_("Setup bootloader..."),"operation":self.setupBootLooder},
                     {"text":_("Writing bootloader..."),"operation":self.writeBootLooder},
                     {"text":_("Stopping to D-Bus..."),"operation":yali.util.stop_dbus}]

        if ctx.bootloader.device:
            stepsBase.append({"text":_("Installing Bootloader..."),"operation":self.installBootloader})

        if self.install_type in [YALI_INSTALL, YALI_DVDINSTALL, YALI_FIRSTBOOT]:
            rootWidget.steps.setOperations(steps)
        elif self.install_type == YALI_PLUGIN:
            rootWidget.steps.setOperations(self.plugin.config.steps)

        rootWidget.steps.setOperations(stepsBase)

    def setupBootLooder(self):
        ctx.bootloader.setup()
        ctx.logger.debug("Setup bootloader")

    def writeBootLooder(self):
        ctx.bootloader.write()
        ctx.logger.debug("Writing grub.conf and devicemap")

    def installBootloader(self, pardusPart = None):
        #FIXME:Rewrite this to re-fix with new storage api
        # BUG:#11255 normal user doesn't mount /mnt/archive directory. 
        # We set new formatted partition priveleges as user=root group=disk and change mod as 0770
        # Check archive partition type
        #archiveRequest = partrequests.searchPartTypeAndReqType(parttype.archive, request.mountRequestType)
        #if archiveRequest:
        #    ctx.logger.debug("Archive type request found!")
        #    yali.postinstall.setPartitionPrivileges(archiveRequest, 0770, 0, 6)

        # Umount system paths
        ctx.storage.storageset.umountFilesystems()
        ctx.logger.debug("Unmount system paths")
        rc = ctx.bootloader.install()
        if rc:
            ctx.logger.debug("Bootloader installation failed!")
        else:
            ctx.logger.debug("Bootloader installed")

