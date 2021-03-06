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


from qt import *

import gettext
__trans = gettext.translation('yali', fallback=True)
_ = __trans.ugettext


import yali.gui.context as ctx
from yali.gui.YaliDialog import Dialog
import GUIRelNotes
import GUINavButton


class RelButton(QWidget):

    def __init__(self, *args):
        apply(QWidget.__init__, (self,) + args)

        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(5)

        self.button = GUINavButton.YaliButton(self)
        self._layout.addWidget(self.button)

        self.label = QLabel(self)
        self._layout.addWidget(self.label)

        self.tw = self.width()
        self.th = self.height()
        self.tx = self.x()
        self.ty = self.y()
        self.fixBackground()

        self.connect(self.button, PYSIGNAL("signalClicked"),
                     PYSIGNAL("signalClicked"))

    def setText(self, text):
        self.label.setText(text)

    def setIcon(self, icon):
        self.button.setIcon(icon)
        self.setFixedHeight(self.button.height())

    def fixBackground(self):
        self.pix = QPixmap(self.tw, self.th)
        self.pix.fill(self.parent(), self.tx, self.ty)
        self.setPaletteBackgroundPixmap(self.pix)

    def resizeEvent(self, event):
        self.tw = event.size().width()
        self.th = event.size().height()
        self.fixBackground()

    def moveEvent(self, event):
        self.tx = event.pos().x()
        self.ty = event.pos().y()
        self.fixBackground()

    def mouseReleaseEvent(self, e):
        self.button.mouseReleaseEvent(e)

    def mousePressEvent(self, e):
        self.button.mousePressEvent(e)

    def enterEvent(self, e):
        self.button.enterEvent(e)

    def leaveEvent(self, e):
        self.button.leaveEvent(e)


##
# Top widget
class Widget(QWidget):

    def __init__(self, *args):
        apply(QWidget.__init__, (self,) + args)

        self.img = ctx.iconfactory.newImage("bottom_image")

        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(20)
        self._layout.setMargin(5)


        self.relNotes = RelButton(self)
        self.relNotes.setIcon("relnotes_button")
        self.relNotes.setText(_("Release Notes"))
        self._layout.addWidget(self.relNotes)
        self._layout.addStretch(1)


        self.nextButton = GUINavButton.nextButton(self)
        self.prevButton = GUINavButton.prevButton(self)

        buttons = QHBoxLayout(self._layout)
        buttons.addWidget(self.prevButton)
        buttons.addWidget(self.nextButton)
        self.buttonSpacer = QSpacerItem(0, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
        buttons.addItem(self.buttonSpacer)


        self.connect(self.relNotes, PYSIGNAL("signalClicked"),
                     self.showReleaseNotes)

        self.connect(self.nextButton, PYSIGNAL("signalClicked"),
                     self.slotNextScreen)
        self.connect(self.prevButton, PYSIGNAL("signalClicked"),
                     self.slotPrevScreen)


    ##
    # resize the widget
    def resizeEvent(self, event):
        w = self.parent().width()/8 - self.prevButton.width() - 10

        self.buttonSpacer.changeSize(w, 20, QSizePolicy.Fixed, QSizePolicy.Fixed)


    def slotResize(self, obj, size):
        img_w = self.img.width()
        img_h = self.img.height()
        width = size.width()
        height = img_h * width / img_w
        self.setFixedHeight(height)

        img = self.img.smoothScale(self.size())
        self.setPaletteBackgroundPixmap(QPixmap(img))


    def showReleaseNotes(self):
        # make a release notes dialog
        r = GUIRelNotes.Widget(self)
        d = Dialog(_("Release Notes"), r, self)
        d.resize(500,400)
        d.show()

    ##
    # Go to the next screen.
    def slotNextScreen(self):
        ctx.screens.next()

    ##
    # Go to the previous screen.
    def slotPrevScreen(self):
        ctx.screens.previous()
