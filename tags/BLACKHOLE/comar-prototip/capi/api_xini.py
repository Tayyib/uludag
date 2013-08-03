#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2004, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

# COMARd
# time related CAPI calls

def	APICLASS():
	return "XINI"

_APICLASS  = "XINI"

def dummycheckPerms(*prm):
	return 1
	
class APICALLS:
	def __init__(self, IAPI, COMARValue):
		self.IAPI = IAPI
		self.cv = COMARValue
		self.objHandlers = {}
	
	def	GetFuncTable(self):
		return { 'xini_change_option':self.xini_change_option, 'xini_change_section': self.xini_change_section, "xini_parse":self.xini_get_all }
		
	def xini_set_devices(self, _name = "", prms = {}, checkPerms=dummycheckPerms, callerInfo=None):
		keylist = prms.keys()
		cfgfile = None
		mouse = None
		monitor = None
		card = None
		resolution = None
		mode = None
		flags = None
		keybd = None
		fonts = None
		for prm in keylist:
			if prm == "cfgfile":
				cfgfile = prms[prm].data.value
			elif prm == "mouse":
				mouse = prms[prm].data.value
			elif prm == "monitor":
				monitor = prms[prm].data.value
			elif prm == "card":
				card = prms[prm].data.value
			elif prm == "resolution":
				resolution = prms[prm].data.value
			elif prm == "defaultmode":
				mode = prms[prm].data.value
			elif prm == "flags":
				flags = prms[prm].data.value
			elif prm == "keyboard":
				keybd = prms[prm].data.value
			elif prm == "fontpath":
				fontpath = prms[prm].data.value
		if cfgfile == None or mouse == None or monitor == None or card == None or resolution == None or mode == None:
			print "xini_change_option called with missing args"
			return self.cv.COMARRetVal( value=None, result=0 )
		lines = []
		lines.append("# Xorg.conf\n# This file generated by COMAR-demo 1.0.\n")
		lines.append("""
Section "Files"\nModulePath	"/usr/X11R6/lib/modules"
		RgbPath      "/usr/X11R6/lib/X11/rgb"
		FontPath     "/usr/share/fonts/misc/"
		FontPath     "/usr/share/fonts/75dpi/:unscaled"
		FontPath     "/usr/share/fonts/100dpi/:unscaled"
		FontPath     "/usr/share/fonts/Type1/"
		FontPath     "/usr/share/fonts/TTF/"
		FontPath     "/usr/share/fonts/CID/"
		FontPath     "/usr/share/fonts/75dpi/"
		FontPath     "/usr/share/fonts/100dpi/"
#	FontPath	"unix/:-1"
EndSection
""")
		lines.append("""
Section "Module"
	Load  "record"
	Load  "extmod"
	Load  "dbe"
	SubSection "extmod"
		Option	    "omit xfree86-dga"
	EndSubSection
	Load  "glx"
	Load  "dri"
	Load  "xtrap"
	Load  "freetype"
	Load  "type1"
#	Load  "v4l"
EndSection
""")
		lines.append('Section "ServerFlags"')
		if flags:
			f = self.cv.array2Dict(flags)
			for i in f:
				lines.append("\t%s %s" % (i, self.cv.CVALget(f[i])))
		lines.append('EndSection')
		
	def xini_get_all(self, _name = "", prms = {}, checkPerms=dummycheckPerms, callerInfo=None):
		keylist = prms.keys()
		cfgfile = None
		for prm in keylist:
			if prm == "cfgfile":
				cfgfile = prms[prm].data.value
			
		if cfgfile == None:
			print "xini_change_option called with missing args"
			return self.cv.COMARRetVal( value=None, result=0 )
		print "XINI_PARSER:", cfgfile
		f = file(cfgfile, "r")
		lines = f.readlines()
		ret = self.cv.array_create()
		node = ret
		nodeStack = []		
		for line in lines:
			l = line.strip()
			x = l.find("#") 
			if x != -1:
				if x == 0:
					l = ""
				else:
					print "rem clean:", l, x, "->", l[0:x-1], 
					l = l[0:l.find("#")-1]
					print l
				
			if len(l):
				#print "Process:", l, l[:7], l[:10], l[:13]				
				if l[:7] == "Section":					
					secName = l[l.find('"')+1:l.rfind('"')]
					#print "\tSection:", secName
					arrItem = self.cv.array_create()
					nodeStack.append(node)
					self.cv.array_additem(array=node, key="S " + secName, instance=0, arrValue=arrItem)
					node = arrItem					
				elif l[:10] == "EndSection":
					#print "\tEnd Section:", secName
					node = nodeStack.pop()
				elif l[:10] == "SubSection":
					secName = l[l.find('"')+1:l.rfind('"')]
					arrItem = self.cv.array_create()
					nodeStack.append(node)
					self.cv.array_additem(array=node, key="SS " + secName, instance=0, arrValue=arrItem)
					node = arrItem
				elif l[:13] == "EndSubSection":
					node = nodeStack.pop()
				else:					
					an = l.split(" ")
					cmd = an.pop(0)
					x = 0
					for i in an:
						if i == "":
							del an[x]
						x += 1
					#print "Add Line", cmd, an
					self.cv.array_additem(array=node, key="V " + cmd, instance=0, arrValue=self.cv.string_create(" ".join(an)))
		
		#self.cv.dump_value_xml(ret)
		f.close()
		return self.cv.COMARRetVal( value=ret, result=0 )
	
	def xini_change_option(self, _name = "", prms = {}, checkPerms=dummycheckPerms, callerInfo=None):
		print "xini_change_option called"
		keylist = prms.keys()
		cfgfile = None
		section = None
		option = None
		value = None
		for prm in keylist:
			if prm == "cfgfile":
				cfgfile = prms[prm].data.value
			elif prm == "section":
				section = prms[prm].data.value
			elif prm == "option":
				option = prms[prm].data.value
			elif prm == "value":
				tmp = prms[prm]
				if tmp.type == "string":
					value = tmp.data.value
				elif tmp.type == "array":
					di = self.cv.array2Dict(tmp)
					keys=di.keys()
					keys.sort()
					value = ""
					for line in keys:
						tek = di[line][0]["value"]
						value += tek
					if value.find("\n") != -1:
						value = value[:value.find("\n")]
					if value == "":
						value = None
		if cfgfile == None or section == None or option == None or value == None:
			print "xini_change_option called with missing args"
			return self.cv.COMARRetVal( value=None, result=0 )
		f = file(cfgfile, "r")
		lines = f.readlines()
		f.close()
		lines2 = []
		mode = 0
		for line in lines:
			if mode == 0:
				lines2.append(line)
				if line[:7] == "Section":
					if line[line.find('"')+1:line.rfind('"')] == section:
						mode = 1
			elif mode == 1:
				if line.find(option) != -1:
					lines2.append('\t' + option + '\t"' + value + '"\n')
				else:
					if line[:10] == "EndSection":
						mode = 2
					lines2.append(line)
			elif mode == 2:
				lines2.append(line)
		f = file(cfgfile, "w")
		f.writelines(lines2)
		f.close()
		return self.cv.COMARRetVal( value=None, result=0 )
	
	def xini_change_section(self, _name = "", prms = {}, checkPerms=dummycheckPerms, callerInfo=None):
		print "xini_change_section called"
		keylist = prms.keys()
		cfgfile = None
		section = None
		content = None
		for prm in keylist:
			if prm == "cfgfile":
				cfgfile = prms[prm].data.value
			elif prm == "section":
				section = prms[prm].data.value
			elif prm == "content":
				tmp = prms[prm]
				if tmp.type == "string":
					content = tmp.data.value
				elif tmp.type == "array":
					di = self.cv.array2Dict(tmp)
					keys=di.keys()
					keys.sort()
					content = ""
					for line in keys:
						tek = di[line][0]["value"]
						if tek[:7] != "Section" and tek[:10] != "EndSection":
							content += tek
					#tmp2 = tmp.data
					#content = ""
					#while tmp2 != None:
					#	content += tmp2.item.data.value
					#	tmp2 = tmp2.next
		if cfgfile == None or section == None or content == None:
			print "xini_change_section called with missing args"
			return self.cv.COMARRetVal( value=None, result=0 )
		f = file(cfgfile, "r")
		lines = f.readlines()
		f.close()
		lines2 = []
		mode = 0
		for line in lines:
			if mode == 0:
				lines2.append(line)
				if line[:7] == "Section":
					if line[line.find('"')+1:line.rfind('"')] == section:
						mode = 1
						lines2.append(content)
			elif mode == 1:
				if line.find("EndSection") != -1:
					lines2.append(line)
					mode = 2
			elif mode == 2:
				lines2.append(line)
		f = file(cfgfile, "w")
		f.writelines(lines2)
		f.close()
		return self.cv.COMARRetVal( value=None, result=0 )

API_MODS = [ APICALLS ]