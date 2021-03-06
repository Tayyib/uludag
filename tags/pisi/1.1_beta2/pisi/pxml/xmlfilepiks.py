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

"""
 XmlFile class further abstracts a dom object using the
 high-level dom functions provided in xmlext module (and sorely lacking
 in xml.dom :( )

 function names are mixedCase for compatibility with minidom,
 an 'old library'

 this implementation uses piksemel
"""

import gettext
__trans = gettext.translation('pisi', fallback=True)
_ = __trans.ugettext

import codecs
import exceptions

import piksemel as iks

import pisi
from pisi.file import File
from pisi.util import join_path as join

class Error(pisi.Error):
    pass

class XmlFile(object):
    """A class to help reading and writing an XML file"""

    def __init__(self, tag):
        self.rootTag = tag

    def newDocument(self):
        """clear DOM"""
        self.doc = iks.newDocument(self.rootTag)

    def unlink(self):
        """deallocate DOM structure"""
        pass # piksemel isnt as lame as minidom

    def rootNode(self):
        """returns root document element"""
        return self.doc

    def readxml(self, uri, tmpDir='/tmp', sha1sum=False, compress=None, sign=None):
        uri = File.make_uri(uri)
        localpath = File.download(uri, tmpDir,sha1sum=sha1sum,compress=compress,sign=sign)
        try:
            self.doc = iks.parse(localpath)
            return self.doc
        except Exception, e:
            raise Error(_("File '%s' has invalid XML") % (localpath) )

    def writexml(self, uri, tmpDir = '/tmp', sha1sum=False, compress=None, sign=None):
        f = File(uri, File.write, sha1sum=sha1sum, compress=compress, sign=sign)
        f.write(self.doc.toPrettyString())
        f.close()
