#!/usr/bin/python
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
#

import os
import popen2
import string

xdriverlist = "/usr/lib/X11/xdriverlist"
MonitorsDB = "/usr/lib/X11/MonitorsDB"
xorg_conf = "/etc/X11/xorg.conf"

### templates ###
template_videocard = """
Section "Device"
    Screen %(N)s
    Identifier "VideoCard%(N)s"
    Driver     "%(DRIVER)s"
    VendorName "%(VENDORNAME)s"
    BoardName  "%(BOARDNAME)s"
    # BusID      "%(BUSID)s"
    Option     "RenderAccel" "true"
    # Option     "AccelMethod" "exa"
EndSection
"""

template_monitor = """
Section "Monitor"
    Identifier  "Monitor%(N)s"
    VendorName  "%(VENDOR)s"
    ModelName   "%(MODEL)s"
    HorizSync    %(HSYNC)s
    VertRefresh  %(VREF)s

%(MODELINES)s
EndSection
"""

template_synaptics = """
Section "InputDevice"
    Identifier "Mouse1"
    Driver     "synaptics"
    Option     "Protocol" "auto-dev"
    Option     "Device" "/dev/input/mouse0"
    Option     "ZAxisMapping" "4 5"
    Option     "Buttons" "5"
    Option     "SHMConfig" "true"
    # "Option    "AccelFactor" "0.04"
EndSection
"""

template_alps = """
Section "InputDevice"
    Identifier "Mouse1"
    Driver     "synaptics"
    Option     "Protocol" "auto-dev"
    Option     "Device" "/dev/input/mouse1"
    Option     "SHMConfig" "true"
    Option     "MinSpeed" "0.50"
    Option     "MaxSpeed" "1.00"
    # "Option    "AccelFactor" "0.04"
EndSection
"""

template_screen = """
Section "Screen"
    Identifier "Screen%(N)s"
    Device     "VideoCard%(N)s"
    Monitor    "Monitor%(N)s"
    DefaultDepth %(DEPTH)s
    Subsection "Display"
        Depth    %(DEPTH)s
        Modes    %(MODES)s
    EndSubsection
EndSection
"""

template_probe_display = """
Section "ServerLayout"
    Identifier "COMAR Configured Layout"
    Screen   0 "Screen0" 0 0
EndSection

Section "Monitor"
    Identifier "Monitor0"
EndSection

Section "Screen"
    Identifier "Screen0"
    Device     "Card0"
EndSection

Section "Device"
    Identifier "Card0"
    Driver     "%(PROBE_DRIVER)s"
EndSection
"""

template_main = """
Section "Module"
    Load "dbe"      # Double buffer extension
    SubSection "extmod"
        Option "omit xfree86-dga"   # don't initialise the DGA extension
    EndSubSection
    Load "type1"
    Load "freetype"
    Load "glx"
    Load "dri"
    Load "v4l"
    %(SYNAPTICS_MOD)s
EndSection

Section "Extensions"
#    Option "Composite" "enable"
EndSection

Section "dri"
    Mode 0666
EndSection

Section "Files"
    RgbPath  "/usr/lib/X11/rgb"
    FontPath "/usr/share/fonts/dejavu/"
    FontPath "/usr/share/fonts/misc/"
    FontPath "/usr/share/fonts/TTF/"
    FontPath "/usr/share/fonts/encodings/"
    FontPath "/usr/share/fonts/freefont/"
    FontPath "/usr/share/fonts/TrueType/"
    FontPath "/usr/share/fonts/corefonts"
    FontPath "/usr/share/fonts/Speedo/"
    FontPath "/usr/share/fonts/Type1/"
    FontPath "/usr/share/fonts/100dpi/"
    FontPath "/usr/share/fonts/75dpi/"
EndSection

Section "ServerFlags"
    Option     "AllowMouseOpenFail" "True"
    Option     "BlankTime" "0"
    Option     "StandbyTime" "0"
    Option     "SuspendTime" "0"
    Option     "OffTime" "0"
EndSection

Section "InputDevice"
    Identifier "Keyboard0"
    Driver     "kbd"
    Option     "AutoRepeat" "500 30"
    Option     "XkbModel" "pc105"
    Option     "XkbLayout" "%(KEYMAP)s"
EndSection

Section "InputDevice"
    Identifier "Mouse0"
    Driver     "mouse"
    Option     "Protocol" "ExplorerPS/2"
    Option     "Device" "/dev/input/mice"
    Option     "ZAxisMapping" "4 5"
    Option     "Buttons" "5"
EndSection

%(SEC_SYNAPTICS)s
%(SEC_VIDEOCARD)s
%(SEC_MONITOR)s
%(SEC_SCREEN)s

Section "ServerLayout"
    Identifier  "Simple Layout"
    Screen      "Screen0"
    InputDevice "Mouse0" "CorePointer"
    %(SYNAPTICS_LAY)s
    InputDevice "Keyboard0" "CoreKeyboard"
    # Multihead stuff
    # Screen      0  "Screen0" LeftOf "Screen1"
    # Screen      1  "Screen1" 0 0
    Option      "Xinerama" "off"
    Option      "Clone" "off"
EndSection
"""


### api ###
def unlink(path):
    try:
        os.unlink(path)
    except:
        pass

def capture(cmd):
    out = []
    a = popen2.Popen4(cmd)
    while 1:
        b = a.fromchild.readline()
        if b == None or b == "":
            break
        out.append(b)
    return (a.wait(), out)

def grepini(lines, sect, key):
    flag = 0
    for line in lines:
        if flag == 0:
            if line.find(sect) != -1:
                flag = 1
        else:
            if line.find(key) != -1:
                return line.split()[-1].strip('"')
    return None

def atoi(s):
    # python'da bunu yapacak fonksiyon bulamadım
    # int() sayı olmayan karaktere rastladığında pörtlüyor
    t = ""
    for c in s.lstrip():
        if c in "0123456789":
            t += c
        else:
            break
    try:
        ret = int(t)
    except:
        ret = 0
    return ret

def write_tmpl(tmpl, keys, fname):
    f = file(fname, "w")
    f.write(tmpl % keys)
    f.close()

def sysValue(path, dir, file_):
    f = file(os.path.join(path, dir, file_))
    data = f.read().rstrip('\n')
    f.close()
    return data

def lremove(str, pre):
    if str.startswith(pre):
        return str[len(pre):]
    return str

### modeline calc ###

def GetInt(name, dict, default=0):
    str = dict.get(name , default)
    try:
        return int(str)
    except:
        return default

# _ GetFloat ___________________________________________________________
def GetFloat(name, dict, default=0.0):
    str = dict.get(name , default)
    try:
        return float(str)
    except:
        return default


# _ ModeLine ___________________________________________________________
def ModeLine(dict={}):
    '''
    This routine will calculate XF86Config Modeline entries.
    The Parameters are supplies as a dictionary due to the large number.
    The Calculated values are also returned in dictionary form.

    The parameter dictionary entries are:
    hPix       Horizontal displayed pixels    Default: 1280)
    hSync      Horizontal sync in uSec        Default: 1)
    hBlank     Horizontal blanking in uSec    Default: 3)
    vPix       Vertical displayed pixels      Default: 960)
    vFreq      Vertical scan frequency in Hz  Default: 75)
    vSync      Vertical sync in uSec          Default: 0)
    vBlank     Vertical blanking in uSec      Default: 500)
    v4x3       Constrain h/v to 4/3           Default: 0 (not constrained)

    hRatio1    Horizontal front poarch ratio  Default: 1)
    hRatio2    Horizontal sync ratio          Default: 4)
    hRatio3    Horizontal back poarch ratio   Default: 7)
    vRatio1    Vertical front poarch ratio    Default: 1)
    vRatio2    Vertical sync ratio            Default: 1)
    vRatio3    Vertical back poarch ratio     Default: 10)

    If v4x3="1" vPix is ignored.

    If any of the following:hSync, hBlanking, vSync, vBlanking
    are not specified then they are set based on the ratios,
    at a minimum is is best to specify either sync or blanking.

    The return dictionary entries are:
    The "entry" value is really all that is needed
    entry     Modeline entry string

    These are the values that make up the modeline entry
    dotClock    Dot clock in MHz
    hPix        Horizontal displayed pixels
    hFreq       Horizontal scan frequency in Hz.
    hTim1       Horizontal front poarch pixels
    hTim2       Horizontal sync pixels
    hTim3       Horizontal back poarch pixels
    vPix        Vertical displayed pixels
    vFreq       Vertical scan frequency in Hz.
    vTim1       Vertical front poarch pixels
    vTim2       Vertical sync pixels
    vTim3       Vertical back poarch pixels
    '''
    results = {}
    hPix    = GetInt(  "hPix"    , dict, 1280)
    hSync   = GetFloat("hSync"   , dict, 1)
    hBlank  = GetFloat("hBlank"  , dict, 3)
    hRatio1 = GetFloat("hRatio1" , dict, 1)
    hRatio2 = GetFloat("hRatio2" , dict, 4)
    hRatio3 = GetFloat("hRatio3" , dict, 7)
    vPix    = GetInt(  "vPix"    , dict, 960)
    vFreq   = GetFloat("vFreq"   , dict, 75)
    vSync   = GetFloat("vSync"   , dict, 0)
    vBlank  = GetFloat("vBlank"  , dict, 500)
    vRatio1 = GetFloat("vRatio1" , dict, 1)
    vRatio2 = GetFloat("vRatio2" , dict, 1)
    vRatio3 = GetFloat("vRatio3" , dict, 10)
    if (dict.has_key("v4x3")    == 0):
        v4x3        = ""
    else:
        v4x3        = "checked"
        vPix        = int(hPix) / 4 * 3

    vSyncUs = vSync / 1000000.0
    vBlankUs = vBlank / 1000000.0

    vRatioT = vRatio1 + vRatio2 + vRatio3
    if   ((vSyncUs > 0.0) and (vBlankUs > 0.0)):
        vRatio2 = (vRatio1 + vRatio3) * (vSyncUs / (vBlankUs - vSyncUs))
        vRatioT = vRatio1 + vRatio2 + vRatio3
    elif ((vSyncUs > 0.0) and (vBlankUs <= 0.0)):
        vBlankUs = vSyncUs * (vRatioT / vRatio2)
    elif ((vSyncUs <= 0.0) and (vBlankUs > 0.0)):
        vSyncUs = vBlankUs * (vRatio2 / vRatioT)

    vBase = 1.0 / vFreq
    vBase = (vPix / (vBase - vBlankUs)) * vBase
    vBase = (vBase - vPix) / vRatioT

    vTim1 = vPix  + int((vBase * vRatio1) + 1.0)
    vTim2 = vTim1 + int((vBase * vRatio2) + 1.0)
    vTim3 = vTim2 + int((vBase * vRatio3) + 1.0)

    hFreq    = (vTim3 * vFreq)

    hSyncUs  = hSync / 1000000.0
    hBlankUs = hBlank / 1000000.0

    hPix    = ((hPix + 7) / 8) * 8

    hRatioT = hRatio1 + hRatio2 + hRatio3
    if   ((hSyncUs > 0.0) and (hBlankUs > 0.0)):
        hRatio2 = (hRatio1 + hRatio3) * (hSyncUs / (hBlankUs - hSyncUs))
        hRatioT = hRatio1 + hRatio2 + hRatio3
    elif ((hSyncUs > 0.0) and (hBlankUs <= 0.0)):
        hBlankUs = hSyncUs * (hRatioT / hRatio2)
    elif ((hSyncUs <= 0.0) and (hBlankUs > 0.0)):
        hSyncUshBlankUs = hBlankUs * (hRatio2 / hRatioT)

    hBase = 1.0 / hFreq
    hBase = (hPix / (hBase - hBlankUs)) * hBase
    hBase = (hBase - hPix) / hRatioT

    hTim1 = hPix  + ((int((hBase * hRatio1)+8.0) / 8) * 8)
    hTim2 = hTim1 + ((int((hBase * hRatio2)+8.0) / 8) * 8)
    hTim3 = hTim2 + ((int((hBase * hRatio3)+8.0) / 8) * 8)

    dotClock = (hTim3 * vTim3 * vFreq) / 1000000.0
    
    hFreqKHz = hFreq / 1000.0

    results = {}
    results["entry"]    = '''\
# %(hPix)dx%(vPix)d @ %(vFreq)dHz, %(hFreqKHz)6.2f kHz hsync
    Mode "%(hPix)dx%(vPix)d"
        DotClock  %(dotClock)8.2f
        HTimings  %(hPix)d %(hTim1)d %(hTim2)d %(hTim3)d
        VTimings  %(vPix)d %(vTim1)d %(vTim2)d %(vTim3)d
    EndMode\
    ''' % vars()
    results["hPix"]     = hPix
    results["vPix"]     = vPix
    results["vFreq"]    = vFreq
    results["hFreq"]    = hFreq
    results["dotClock"] = dotClock
    results["hTim1"]    = hTim1
    results["hTim2"]    = hTim2
    results["hTim3"]    = hTim3
    results["vTim1"]    = vTim1
    results["vTim2"]    = vTim2
    results["vTim3"]    = vTim3

    return results

def calcModeLine(w, h, vfreq):
    vals = {}
    vals["hPix"] = w
    vals["vPix"] = h
    vals["vFreq"] = vfreq
    m = ModeLine(vals)
    return m["entry"]

### Asıl betik aşağıda ###

class Device:
    def __init__(self):
        self.Driver = None
        self.VendorName = "unknown"
        self.BoardName = "unknown"
        self.BusId = None

class Monitor:
    def __init__(self):
        self.wide = 0
        self.panel_w = 0
        self.panel_h = 0
        self.hsync_min = 0
        self.hsync_max = 0
        self.vref_min = 0
        self.vref_max = 0
        self.modelines = []
        self.res = ""
        self.vendorname = "Unknown"
        self.modelname = "Unknown"
        self.eisaid = ""
        self.depth = "16"

def listAvailableDrivers(driver_path = '/usr/lib/modules/drivers'):
    a = []
    for drv in os.listdir(driver_path):
        if drv.endswith("_drv.so"):
            if drv[:-7] not in a:
                a.append(drv[:-7])
    return a

def queryDriver(vendor, device):
    available_drivers = listAvailableDrivers()
    try:
        f = file(xdriverlist)
    except:
        print "%s not found" % xdriverlist
        return None
    else:
        for line in f:
            if line.startswith(vendor + device):
                drv = line.rstrip("\n").split(" ")[1]
                return drv

    return None

def queryPCI(vendor, device):
    f = file("/usr/share/misc/pci.ids")
    flag = 0
    company = ""
    for line in f.readlines():
        if flag == 0:
            if line.startswith(vendor):
                flag = 1
                company = line[5:].strip()
        else:
            if line.startswith("\t"):
                if line.startswith("\t" + device):
                    return line[6:].strip(), company
            elif not line.startswith("#"):
                flag = 0
    return None, None

def findPciCards():
    cards = []
    for bus in ["pci", "pci_express"]:
        sysDir = os.path.join("/sys/bus", bus, "devices")
        if os.path.isdir(sysDir):
            for _dev in os.listdir(sysDir):
                try:
                    if sysValue(sysDir, _dev, "class").startswith("0x03"):
                        a = Device()
                        vendorId = lremove(sysValue(sysDir, _dev, "vendor"), "0x")
                        deviceId = lremove(sysValue(sysDir, _dev, "device"), "0x")
                        #FIXME: BusID magic to support multiple heads, but breaking pci-e support ?
                        a.BusId = "PCI:%s" % _dev.replace(".",":").split(":", 1)[1]
                        a.BoardName, a.VendorName =  queryPCI(vendorId, deviceId)
                        a.Driver = queryDriver(vendorId, deviceId)
                        cards.append(a)
                except:
                    pass
    return cards

def queryPanel(mon):
    patterns = [
    "Panel size is",
    "Panel Size is",
    "Panel Size from BIOS:",
    "Detected panel size via",
    "Size of device LFP (local flat panel) is",
    "Size of device LFP",
    "Size of device DFP",
    "Detected LCD/plasma panel ("
    ]
    a = capture("/usr/bin/X -probeonly -allowMouseOpenFail -logfile /var/log/xlog")
    if a[0] != 0:
        print "X -probeonly failed!"
        return
    f = file("/var/log/xlog")
    for line in f.readlines():
        for p in patterns:
            if p in line:
                b = line[line.find(p)+len(p):]
                mon.panel_w = atoi(b)
                b = b[b.find("x")+1:]
                mon.panel_h = atoi(b)
                break
    f.close()
    return None

def queryDDC():
    mon = Monitor()
    eisaid = ""
    ddc = capture("/usr/sbin/ddcxinfos")
    if ddc[0] != 0:
        print "ddcxinfos failed!"
        return mon

    for line in ddc[1]:
        t = line.find("truly")
        if t != -1:
            mon.wide = atoi(line[t+6:])
        t = line.find("EISA ID=")
        if t != -1:
            eisaid = line[line.find("EISA ID=")+8:line.find("\r")].upper().strip()
        t = line.find("kHz HorizSync")
        if t != -1:
            mon.hsync_min = atoi(line)
            mon.hsync_max = atoi(line[line.find("-") + 1:])
        t = line.find("Hz VertRefresh")
        if t != -1:
            mon.vref_min = atoi(line)
            mon.vref_max = atoi(line[line.find("-") + 1:])
        if line[:8] == "ModeLine":
            mon.modelines.append("    " +line)

    if mon.hsync_max == 0 or mon.vref_max == 0:
        # in case those not probed separately, get them from modelines
        freqs = filter(lambda x: x.find("hfreq=") != -1, ddc[1])
        if len(freqs) > 1:
            line = freqs[0]
            mon.hsync_min = atoi(line[line.find("hfreq=") + 6:])
            mon.vref_min = atoi(line[line.find("vfreq=") + 6:])
            line = freqs[-1]
            mon.hsync_max = atoi(line[line.find("hfreq=") + 6:])
            mon.vref_max = atoi(line[line.find("vfreq=") + 6:])

    if eisaid:
        f = file(MonitorsDB)
        for line in f:
            if not line.startswith("#"):
                l = line.split(";")
                if eisaid == string.upper(l[2]).strip():
                    mon.vendorname = l[0].lstrip()
                    mon.modelname = l[1].lstrip()
                    mon.hsync_min, mon.hsync_max = l[3].strip().split("-")
                    mon.vref_min, mon.vref_max = l[4].strip().split("-")

    for m in mon.modelines:
        t = m[m.find("ModeLine"):].split()[1]
        if t not in mon.res:
            mon.res = t + " " + mon.res

    if mon.res == "":
        mon.res = '"800x600" "640x480"'

    return mon

def querySynaptics(keys_main):
    keys_main["SYNAPTICS_MOD"] = ""
    keys_main["SEC_SYNAPTICS"] = ""
    keys_main["SYNAPTICS_LAY"] = ""
    try:
        a = file("/proc/bus/input/devices")
        for line in a.readlines():
            # FIXME: check if kernel does not break anything
            # if "SynPS/2" in line or "AlpsPS/2" in line:
            if "SynPS/2" in line:
                keys_main["SYNAPTICS_MOD"] = 'Load "synaptics"'
                keys_main["SYNAPTICS_LAY"] = 'InputDevice "Mouse1" "SendCoreEvents"'
                keys_main["SEC_SYNAPTICS"] = template_synaptics
            elif "AlpsPS/2" in line:
                keys_main["SYNAPTICS_MOD"] = 'Load "synaptics"'
                keys_main["SYNAPTICS_LAY"] = 'InputDevice "Mouse1" "SendCoreEvents"'
                keys_main["SEC_SYNAPTICS"] = template_alps
        a.close()
    except:
        pass

def queryKeymap():
    # Fallback is trq
    kmap = "trq"
    try:
        f = file("/etc/conf.d/mudur")
        for line in f:
            if line.strip().startswith("keymap="):
                kmap = line.split('=')[1].strip().strip('"')
        f.close()
    except:
        pass

    return kmap

def findMonitors(cards):
    monitors = []
    # FIXME: modify ddcxinfos to probe for more monitors
    # probe monitor freqs, for the first monitor for now
    mon = queryDDC()

    # defaults for the case where ddc fails
    if mon.hsync_min == 0 or mon.vref_min == 0:
        mon.hsync_min = 31.5
        mon.hsync_max = 50
        mon.vref_min = 50
        mon.vref_max = 70

    # check lcd panel
    lcd_drivers = [ "nv", "nvidia", "ati", "via", "i810", "sis" ]
    if cards[0].Driver in lcd_drivers:
        write_tmpl(template_probe_display, { "PROBE_DRIVER": cards[0].Driver }, xorg_conf)
        queryPanel(mon)

    monitors.append(mon)
    return monitors

def keysVideoCards(cards):
    sec = ""
    for i in range(len(cards)):
        keys_vc = {}
        keys_vc["N"] = str(i)
        keys_vc["DRIVER"] = cards[i].Driver
        keys_vc["VENDORNAME"] = cards[i].VendorName
        keys_vc["BOARDNAME"] = cards[i].BoardName
        keys_vc["BUSID"] = cards[i].BusId 
        sec += template_videocard % keys_vc
    return sec

def keysMonitors(monitors):
    sec_monitor = ""
    sec_screen = ""
    for i in range(len(monitors)):
        keys_mon = {}
        keys_mon["N"] = str(i)
        keys_mon["VENDOR"] = monitors[i].vendorname
        keys_mon["MODEL"] = monitors[i].modelname
        keys_mon["HSYNC"] = str(monitors[i].hsync_min) + "-" + str(monitors[i].hsync_max)
        keys_mon["VREF"] = str(monitors[i].vref_min) + "-" + str(monitors[i].vref_max)

        if monitors[i].panel_h and monitors[i].panel_w:
            keys_mon["MODELINES"] = calcModeLine(monitors[i].panel_w, monitors[i].panel_h, 60)
            keys_mon["MODES"] = '"%dx%d" "800x600" "640x480" "1024x768"' % (monitors[i].panel_w, monitors[i].panel_h)
        else:
            keys_mon["MODELINES"] = "".join(monitors[i].modelines)
            keys_mon["MODES"] = monitors[i].res

        # FIXME: check for the driver and set depth due to it
        keys_mon["DEPTH"] = "16"

        sec_monitor += template_monitor % keys_mon
        sec_screen += template_screen % keys_mon

    return sec_monitor, sec_screen


# om call

def autoConfigureDisplay():
    # detect graphic card and find monitor of first card, yet
    cards = findPciCards()

    # if could not find driver from driverlist try X -configure
    if not cards[0].Driver:
        print "Trying to probe with X"
        a = capture("/usr/bin/X -configure -logfile /var/log/xlog")
        if a[0] != 0:
            print "X -configure failed!"
            return -1
        home = os.getenv("HOME", "")
        f = file(home + "/xorg.conf.new")
        conf = f.readlines()
        f.close()
        unlink(home + "/xorg.conf.new")
        cards[0].Driver = grepini(conf, 'Section "Device"', "\tDriver")

    # We need card data to check for lcd displays
    monitors = findMonitors(cards)

    # start over and begin to fill the templates
    keys_main = {}

    # with gfx first, we write all cards
    keys_main["SEC_VIDEOCARD"] = keysVideoCards(cards)

    # and then the monitor
    keys_main["SEC_MONITOR"], keys_main["SEC_SCREEN"] = keysMonitors(monitors)

    # input devices
    querySynaptics(keys_main)
    keys_main["KEYMAP"] = queryKeymap()

    write_tmpl(template_main, keys_main, xorg_conf)

# test
autoConfigureDisplay()

