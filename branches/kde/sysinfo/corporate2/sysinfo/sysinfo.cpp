//////////////////////////////////////////////////////////////////////////
// sysinfo.cpp                                                          //
//                                                                      //
// Copyright (C)  2005  Lukas Tinkl <lukas.tinkl@suse.cz>               //
// Copyright (C)  2007-2008  Pardus Developers <info@pardus.org.tr>     //
//                                                                      //
// This program is free software; you can redistribute it and/or        //
// modify it under the terms of the GNU General Public License          //
// as published by the Free Software Foundation; either version 2       //
// of the License, or (at your option) any later version.               //
//                                                                      //
// This program is distributed in the hope that it will be useful,      //
// but WITHOUT ANY WARRANTY; without even the implied warranty of       //
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the        //
// GNU General Public License for more details.                         //
//                                                                      //
// You should have received a copy of the GNU General Public License    //
// along with this program; if not, write to the Free Software          //
// Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA            //
// 02111-1307, USA.                                                     //
//////////////////////////////////////////////////////////////////////////

#include <config.h>

#include <qfile.h>
#include <qdir.h>
#include <qregexp.h>
#include <qiodevice.h>

#include <stdlib.h>
#include <iostream>
#include <math.h>
#include <unistd.h>
#include <sys/sysinfo.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <stdio.h>
#include <mntent.h>
#include <sys/vfs.h>
#include <string.h>
#include <sys/utsname.h>
#include <hal/libhal.h>

#include <kapplication.h>
#include <kcmdlineargs.h>
#include <kdebug.h>
#include <kinstance.h>
#include <kglobal.h>
#include <kstandarddirs.h>
#include <klocale.h>
#include <dcopref.h>
#include <kprocess.h>
#include <kmimetype.h>
#include <kiconloader.h>
#include <kdeversion.h>
#include <kuser.h>
#include <kglobalsettings.h>
#include <ktempfile.h>

#include "sysinfo.h"

using namespace KIO;
#define BR "<br>"

static QString formattedUnit(unsigned long long value, int post=1)
{
    if (value <= 0)
        return "0";

    if (value > (1024 * 1024))
        if (value > (1024 * 1024 * 1024))
            return i18n("%1 GB").arg(KGlobal::locale()->formatNumber(value / (1024 * 1024 * (post == 0 ? 1024 : 1024.0)), post));
        else
            return i18n("%1 MB").arg(KGlobal::locale()->formatNumber(value / (1024 * (post == 0 ? 1024 : 1024.0)), post));
    else
        return i18n("%1 KB").arg(KGlobal::locale()->formatNumber(value / (post == 0 ? 1024 : 1024.0), post));
}

static QString formatMemory(unsigned long long value)
{
    // value is in kB
    double temp;

    if (value <= 0)
        return "0";

    temp = value / 1024.0; // MB
    if (temp >= 1024) {
        temp /= 1024.0; // GB
        return i18n("%1 GB").arg(KGlobal::locale()->formatNumber(temp));
    }
    return i18n("%1 MB").arg(KGlobal::locale()->formatNumber(temp));
}

void kio_sysinfoProtocol::memoryInfo(void)
{
    QFile file("/proc/meminfo");
    unsigned long long memtotal = 0,
                       memfree = 0,
                       buffers = 0,
                       cached = 0,
                       swaptotal = 0,
                       swapfree = 0;

    // Parse /proc/meminfo for memory usage statistics
    if (file.exists() && file.open(IO_ReadOnly))
    {

        QTextStream stream(&file);
        QString line;

        while (!stream.atEnd())
        {
            line = stream.readLine();
            if (!line.isEmpty())
            {
                if (line.startsWith("MemTotal"))
                    memtotal = line.section(":", 1, 1).replace(" kB", "").stripWhiteSpace().toULongLong();
                else if (line.startsWith("MemFree"))
                    memfree = line.section(":", 1, 1).replace(" kB", "").stripWhiteSpace().toULongLong();
                else if (line.startsWith("Buffers"))
                    buffers = line.section(":", 1, 1).replace(" kB", "").stripWhiteSpace().toULongLong();
                else if (line.startsWith("Cached"))
                    cached = line.section(":", 1, 1).replace(" kB", "").stripWhiteSpace().toULongLong();
                else if (line.startsWith("SwapTotal"))
                    swaptotal = line.section(":", 1, 1).replace(" kB", "").stripWhiteSpace().toULongLong();
                else if (line.startsWith("SwapFree"))
                    swapfree = line.section(":", 1, 1).replace(" kB", "").stripWhiteSpace().toULongLong();
            }
        }
    }

    // Disk cache and buffers are ignored as they will always be available
    // upon request before swapping.
    m_info[MEM_TOTALSWAP] = formatMemory(swaptotal);
    m_info[MEM_FREESWAP] = formatMemory(swapfree);
    m_info[MEM_TOTALRAM] = formatMemory(memtotal);
    m_info[MEM_FREERAM] = formatMemory(memfree+buffers+cached);
}


// Class methods

kio_sysinfoProtocol::kio_sysinfoProtocol(const QCString & pool_socket, const QCString & app_socket)
    : SlaveBase("kio_sysinfo", pool_socket, app_socket), m_dcopClient(new DCOPClient())
{
    if (!m_dcopClient->isAttached())
        m_dcopClient->attach();
}

kio_sysinfoProtocol::~kio_sysinfoProtocol()
{
    m_dcopClient->detach();
    delete m_dcopClient;
}

QString kio_sysinfoProtocol::startStock(const QString title)
{
    QString templator = QString ("<table class=\"stock\">"
                                 "<tr>"
                                 "     <th colspan=3><h2>%1</h2></th>"
                                 "</tr>").arg(title);
    return templator;
}

QString kio_sysinfoProtocol::addToStock(const QString _icon, const QString text, const QString details, const QString link)
{
    QString iconpath = icon(_icon, 22, true);
    QString templator;
    QString temp = "";

    if (link != "")
        temp = QString(" onClick=\"location.href='%1'\" ").arg(link);

    templator += QString ("<tr class=\"info\" %1>").arg(temp);
    templator += QString ("<td><img src=\"%1\"></td><td>%2").arg(iconpath).arg(text);

    if (details != "")
        templator += QString("<span class=\"detail\">%1</span>").arg(details);

    templator += "</td><td></td></tr>";
    return templator;
}

QString kio_sysinfoProtocol::addProgress(const QString _icon, const unsigned long long size)
{
    QString iconpath = icon(_icon, 22, true);
    QString progress = "file:" + locate("data", "sysinfo/themes/Corporate2/images/progress.png");
    QString templator;

    templator += QString ("<tr class=\"progress\">");
    templator += QString ("<td><img src=\"%1\"></td>").arg(iconpath);
    templator += QString ("<td><img src=\"%1\" width=\"%2%\"></td><td></td></tr>").
                         arg(progress).arg(size);
    return templator;
}

QString kio_sysinfoProtocol::finishStock()
{
    return QString ("</table>");
}

static QString formatStr(QString st)
{
    if (st == "")
        return i18n("Not Available");
    return st;
}

void kio_sysinfoProtocol::get(const KURL & /*url*/)
{
    mimeType("application/x-sysinfo");

    // header
    QString location = locate("data", "sysinfo/themes/Corporate2/index.html");
    QFile f(location);
    f.open(IO_ReadOnly);
    QTextStream t(&f);

    infoMessage(i18n("Looking for hardware information..."));

    QString content = t.read();
    content = content.arg(i18n("My Computer")); // <title>
    content = content.arg("file:" + locate("data", "sysinfo/themes/Corporate2/style.css")); // style path

    QString dynamicInfo, staticInfo;
    QString dummy;

    // Dynamic Info

    // common folders
    dynamicInfo += startStock(i18n("Common Folders"));
    dynamicInfo += addToStock("folder_home2", i18n("My Home Folder"), QDir::homeDirPath(), "file:" + QDir::homeDirPath());
    dynamicInfo += addToStock("folder_red", i18n("Root Folder"), QDir::rootDirPath(), "file:" + QDir::rootDirPath());
    dynamicInfo += addToStock("network", i18n("Network Folders"), "remote:/" , "remote:/");
    dynamicInfo += finishStock();

    // memory info
    memoryInfo();

    dynamicInfo += startStock(i18n("Memory"));
    dynamicInfo += addToStock("memory", i18n("Physical memory: ") + i18n("%1 of %2 is free").arg(m_info[MEM_FREERAM]).arg(m_info[MEM_TOTALRAM]));
    dynamicInfo += addToStock("memory", i18n("Swap memory: ") + (m_info[MEM_TOTALSWAP]!="0" ?
                              i18n("%1 of %2 is free").arg(m_info[MEM_FREESWAP]).arg(m_info[MEM_TOTALSWAP]):
                              i18n("Not in use")));
    dynamicInfo += finishStock();

    content = content.arg(dynamicInfo); // put the dynamicInfo text into the dynamic left box

    // Disk Info

    content = content.arg(i18n("Disks"));
    content = content.arg(diskInfo()); // put the discInfo text into the disk right box

    // Static Info

    // CPU info
    cpuInfo();
    if (!m_info[CPU_MODEL].isNull())
    {
        staticInfo += startStock(i18n("Processor"));
        staticInfo += addToStock("kcmprocessor", m_info[CPU_MODEL]);

        // Hack to handle plural forms
#define ngettext i18n
       staticInfo += addToStock("kcmprocessor", i18n("%1 MHz").arg(
                    KGlobal::locale()->formatNumber(m_info[CPU_SPEED].toFloat(), 2))+ " (" + ngettext("1 core", "%n cores", m_info[CPU_NOFCORE].toLong()) + ")");
        staticInfo += addToStock("kcmprocessor", m_info[CPU_VT]);
        staticInfo += finishStock();
    }

    // update content..
    content = content.arg(staticInfo);
    staticInfo = "";

    // OS info
    osInfo();
    staticInfo += startStock(i18n("Operating System"));
    staticInfo += addToStock("system", m_info[OS_SYSNAME] + " <b>" + m_info[OS_RELEASE] + "</b>", m_info[OS_USER] + "@" + m_info[OS_HOSTNAME]);
    staticInfo += addToStock("system", i18n("KDE <b>%1</b> on <b>%2</b>").arg(KDE::versionString()).arg(m_info[OS_SYSTEM]));
    staticInfo += finishStock();

    // update content..
    content = content.arg(staticInfo);
    staticInfo = "";

    // OpenGL info
    if (glInfo())
    {
        staticInfo += startStock(i18n("Display"));
        staticInfo += addToStock("computer", formatStr(m_info[GFX_VENDOR]) + " " + formatStr(m_info[GFX_MODEL]));
        if (!m_info[GFX_DRIVER].isNull())
            staticInfo += addToStock("x", i18n("Driver: ") + m_info[GFX_DRIVER] + " (" + m_info[GFX_3D] + ")");
        staticInfo += finishStock();
    }

    // update content..
    content = content.arg(staticInfo);
    staticInfo = "";

    if (!m_info[MANUFACTURER].isEmpty() || !m_info[PRODUCT].isEmpty() || !m_info[BIOSVENDOR].isEmpty())
    {
        staticInfo += startStock(i18n("Machine Information"));
        staticInfo += addToStock("applications-other", i18n("Vendor: ") + m_info[MANUFACTURER]);
        staticInfo += addToStock("applications-other", i18n("Product: ") + m_info[PRODUCT]);
        staticInfo += addToStock("applications-other", i18n("BIOS: ") + m_info[BIOSVENDOR] + " " + m_info[BIOSVERSION] + " " + m_info[BIOSDATE]);
        staticInfo += finishStock();
    }
    // update content..
    content = content.arg(staticInfo);
    staticInfo = "";

    // Send the data
    data(QCString(content.utf8()));
    data(QByteArray()); // empty array means we're done sending the data
    finished();
}

void kio_sysinfoProtocol::mimetype(const KURL & /*url*/)
{
    mimeType("application/x-sysinfo");
    finished();
}

void kio_sysinfoProtocol::cpuInfo()
{
    QString speed = readFromFile("/proc/cpuinfo", "cpu MHz", ":");

    if (speed.isNull())    // PPC?
        speed = readFromFile("/proc/cpuinfo", "clock", ":");

    if (speed.endsWith("MHz", false))
        speed = speed.left(speed.length() - 3);

    m_info[CPU_SPEED] = speed;

    QString numberOfCores = readFromFile("/proc/cpuinfo", "processor", ":", true);
    numberOfCores = QString::number(numberOfCores.toInt() + 1);
    m_info[CPU_NOFCORE] = numberOfCores;
    m_info[CPU_MODEL] = readFromFile("/proc/cpuinfo", "model name", ":");
    if (m_info[CPU_MODEL].isNull()) // PPC?
         m_info[CPU_MODEL] = readFromFile("/proc/cpuinfo", "cpu", ":");

    QString flags = readFromFile("/proc/cpuinfo", "flags", ":");
    m_info[CPU_VT] = (flags.contains("vmx") || flags.contains("svm")) ? i18n("Processor supports virtualization"):
                                                                        i18n("Processor doesn't support virtualization");
}


QString kio_sysinfoProtocol::diskInfo()
{
    QString result;
    if (fillMediaDevices())
    {
        for (QValueList<DiskInfo>::ConstIterator it = m_devices.constBegin(); it != m_devices.constEnd(); ++it)
        {
            DiskInfo di = (*it);

            /*
            if (di.mounted && di.mountPoint == "/")
                // Skip root filesystem as it's listed above as 'Root Folder'
                continue;
            */

            unsigned long long usage,percent,peer;
            QString label = di.userLabel.isEmpty() ? di.label : di.userLabel;
            QString mountState = di.mounted ? i18n("Mounted on %1").arg(di.mountPoint) : i18n("Not mounted");
            QString tooltip = i18n(di.model);
            usage = di.total - di.avail;
            peer = di.total / 100;
            peer == 0 ? percent = 0 : percent = usage / peer;
            percent = di.mounted ? percent: 0;
            QString sizeStatus = di.mounted ? i18n("%1 of %2 is free").arg(formattedUnit(di.avail,0)).arg(formattedUnit(di.total,0)): "";

            result +=   QString("<tr class=\"media\">"
                                "   <td>"
                                "   <a href=\"media:/%1\" title=\"%2\">"
                                "       <img src=\"%3\" width=\"48\" height=\"48\" />"
                                "   </a></td>").
                                arg(di.name).
                                arg(tooltip+" "+di.deviceNode).
                                arg(icon(di.iconName, 48, true));

            result +=   QString("   <td>"
                                "       <span class=\"detail\">%1<br><span style=\"float:right\">%2</span></span>"
                                "       <a href=\"media:/%3\" title=\"%4\">"
                                "       %5<br><span class=\"mediaDf\">%6</span><br></a>"
                                "       <img class=\"diskusage\" src=\"file:%7\" width=\"%8%\">"
                                "   </td>"
                                "   <td></td>"
                                "</tr>").
                                arg(mountState).
                                arg(di.fsType).
                                arg(di.name).
                                arg(tooltip+" "+di.deviceNode).
                                arg(label).
                                arg(sizeStatus).
                                arg(locate("data", "sysinfo/themes/Corporate2/images/progress.png")).
                                arg(percent);
        }
    }
    return result;
}

#include <GL/glx.h>

bool isOpenGlSupported() {

    int scr = 0;               // print for screen 0
    Display *dpy;              // Active X display
    GLXContext ctx;            // GLX context
    XVisualInfo *visinfo;      // Visual info
    char *displayname = NULL;  // Server to connect
    Bool allowDirect = true;   // Direct rendering only
    Bool isEnabled = false;

    // GLX attributes
    int attribSingle[] = {
        GLX_RGBA,
        GLX_RED_SIZE,   1,
        GLX_GREEN_SIZE, 1,
        GLX_BLUE_SIZE,  1,
        None
    };
    int attribDouble[] = {
        GLX_RGBA,
        GLX_RED_SIZE, 1,
        GLX_GREEN_SIZE, 1,
        GLX_BLUE_SIZE, 1,
        GLX_DOUBLEBUFFER,
        None
    };

    // Open the display with screen#:scr to fiddle with
    dpy = XOpenDisplay (displayname);

    if (!dpy)
        return false;

    visinfo = glXChooseVisual(dpy, scr, attribSingle);
    if (!visinfo) 
    {
        visinfo = glXChooseVisual(dpy, scr, attribDouble);
        if (!visinfo) 
        {
            XCloseDisplay (dpy);
            return false;
        }
    }

    ctx = glXCreateContext(dpy, visinfo, NULL, allowDirect);
    if (!ctx) 
    {
       fprintf(stderr, "Error: glXCreateContext failed\n");
       XFree(visinfo);
       XCloseDisplay (dpy);
       return false;
    }

    if(glXIsDirect(dpy, ctx))
        isEnabled = true;

    glXDestroyContext (dpy,ctx);
    XFree(visinfo);
    XCloseDisplay (dpy);

    return isEnabled;
}

bool kio_sysinfoProtocol::glInfo()
{
    FILE *fd = popen("glxinfo", "r");
    if (!fd)
        return false;

    bool openGlSupported = isOpenGlSupported();
    QTextStream is(fd, IO_ReadOnly);

    while (!is.atEnd()) {
        QString line = is.readLine();
        line = line.stripWhiteSpace();
        if (line.startsWith("OpenGL vendor string:"))
            m_info[GFX_VENDOR] = line.section(":", 1, 1);
        else if (line.startsWith("OpenGL renderer string:"))
            m_info[GFX_MODEL] = line.section(":", 1, 1);
        else if (line.startsWith("OpenGL version string:"))
            m_info[GFX_DRIVER] = line.section(":", 1, 1);
    }

    if (!openGlSupported or m_info[GFX_MODEL].contains("Software Rasterizer"))
        m_info[GFX_3D] = i18n("3D Not Supported");
    else
        m_info[GFX_3D] = i18n("3D Supported");

    pclose(fd);
    return true;
}

QString kio_sysinfoProtocol::readFromFile(const QString & filename, const QString & info, const char * sep, const bool getlast) const
{
    QFile file(filename);

    if (!file.exists() || !file.open(IO_ReadOnly))
        return QString::null;

    QTextStream stream(&file);
    QString line;
    QString temp;

    while (!stream.atEnd())
    {
        line = stream.readLine();
        if (!line.isEmpty())
        {
            if (!sep)
                return line;
            if (line.startsWith(info))
            {
                temp = line.section(sep, 1, 1);
                if (!getlast)
                    return temp;
            }
        }
    }
    return temp;
}

QString kio_sysinfoProtocol::icon(const QString & name, int size, bool justPath) const
{
    QString path = KGlobal::iconLoader()->iconPath(name, -size);
    if (justPath == true)
        return QString("file:%1").arg(path);
    return QString("<img src=\"file:%1\" width=\"%2\" height=\"%3\" valign=\"center\"/>").arg(path).arg(size).arg(size);
}

QString kio_sysinfoProtocol::iconForDevice(const QString & name) const
{
    DCOPRef nsd("kded", "mediamanager");
    nsd.setDCOPClient(m_dcopClient);
    QStringList result = nsd.call("properties", name);

    if (result.isEmpty())
        return QString::null;

    KMimeType::Ptr mime = KMimeType::mimeType(result[10]);
    return mime->icon(QString::null, false);
}

void kio_sysinfoProtocol::osInfo()
{
    struct utsname uts;
    uname(&uts);
    m_info[ OS_SYSNAME ] = uts.sysname;
    m_info[ OS_RELEASE ] = uts.release;
    m_info[ OS_VERSION ] = uts.version;
    m_info[ OS_MACHINE ] = uts.machine;
    m_info[ OS_HOSTNAME ] = uts.nodename;

    m_info[ OS_USER ] = KUser().loginName();
    m_info[ OS_SYSTEM ] = readFromFile("/etc/pardus-release");
}

static const KCmdLineOptions options[] =
{
        { "+protocol", "Protocol name", 0 },
        { "+pool", "Socket name", 0 },
        { "+app", "Socket name",  0 },
        KCmdLineLastOption
};

extern "C"
{
    int kdemain(int argc, char **argv)
    {
        // we need KApp to check the display capabilities
        putenv(strdup("SESSION_MANAGER="));
        KCmdLineArgs::init(argc, argv, "kio_sysinfo", 0, 0, 0, 0);
        KCmdLineArgs::addCmdLineOptions(options);
        KApplication app(false, true);

        kdDebug(7101) << "*** Starting kio_sysinfo " << endl;

        if (argc != 4) 
        {
            kdDebug(7101) << "Usage: kio_sysinfo protocol domain-socket1 domain-socket2" << endl;
            exit(-1);
        }

        KCmdLineArgs *args = KCmdLineArgs::parsedArgs();

        kio_sysinfoProtocol slave(args->arg(1), args->arg(2));
        slave.dispatchLoop();

        kdDebug(7101) << "*** kio_sysinfo Done" << endl;
        return 0;
    }
}

bool kio_sysinfoProtocol::fillMediaDevices()
{

    DCOPRef nsd("kded", "mediamanager");
    nsd.setDCOPClient(m_dcopClient);
    QStringList devices = nsd.call("fullList");

    if (devices.isEmpty())
        return false;

    kdDebug() << devices << endl;

    m_devices.clear();

    LibHalContext  *m_halContext = libhal_ctx_new();

    if (!m_halContext)
        kdDebug(1219) << "Failed to initialize HAL!" << endl;

    DBusError error;
    dbus_error_init(&error);
    DBusConnection *dbus_connection = dbus_bus_get(DBUS_BUS_SYSTEM, &error);

    if (dbus_error_is_set(&error)) 
    {
        dbus_error_free(&error);
        libhal_ctx_free(m_halContext);
        m_halContext = 0;
    }

    if (m_halContext)
    {
        libhal_ctx_set_dbus_connection(m_halContext, dbus_connection);
        dbus_error_init(&error);
        if (!libhal_ctx_init(m_halContext, &error))
            {
                printf("error %s %s\n", error.name, error.message);
                if (dbus_error_is_set(&error))
                    dbus_error_free(&error);
                libhal_ctx_free(m_halContext);
                m_halContext = 0;
            }
    }

    for (QStringList::ConstIterator it = devices.constBegin(); it != devices.constEnd(); ++it)
    {
        DiskInfo di;

        di.id = (*it);
        di.name = *++it;
        di.label = *++it;
        di.userLabel = (*++it);
        di.mountable = (*++it == "true"); // bool
        di.deviceNode = (*++it);
        di.mountPoint = (*++it);
        di.fsType = (*++it);
        di.mounted = (*++it == "true"); // bool
        di.baseURL = (*++it);
        di.mimeType = (*++it);
        di.iconName = (*++it);

        if (di.iconName.isEmpty()) // no user icon, query the MIME type
        {
            KMimeType::Ptr mime = KMimeType::mimeType(di.mimeType);
            di.iconName = mime->icon(QString::null, false);
        }

        di.total = di.avail = 0;

        // calc the free/total space
        struct statfs sfs;
        if (di.mounted && statfs(QFile::encodeName(di.mountPoint), &sfs) == 0)
        {
            di.total = (unsigned long long) sfs.f_blocks * sfs.f_bsize;
            di.avail = (unsigned long long)(getuid() ? sfs.f_bavail : sfs.f_bfree) * sfs.f_bsize;
        } else if (m_halContext && di.id.startsWith("/org/freedesktop/Hal/"))
        {
            dbus_error_init(&error);
            di.total = libhal_device_get_property_uint64(m_halContext, di.id.latin1(), "volume.size", &error);
            if (dbus_error_is_set(&error))
                di.total = 0;
            }

            di.model = libhal_device_get_property_string(m_halContext, di.id.latin1(), "block.storage_device", &error);
            di.model = libhal_device_get_property_string(m_halContext, di.model.latin1(), "storage.model", &error);

            ++it; // skip separator

            m_devices.append(di);
    }

    m_info[PRODUCT] = libhal_device_get_property_string(m_halContext, "/org/freedesktop/Hal/devices/computer", "system.board.product", &error);
    m_info[CHASSISTYPE] = libhal_device_get_property_string(m_halContext, "/org/freedesktop/Hal/devices/computer", "system.chassis.type", &error);
    m_info[FORMFACTOR] = libhal_device_get_property_string(m_halContext, "/org/freedesktop/Hal/devices/computer", "system.formfactor", &error);
    m_info[MANUFACTURER] = libhal_device_get_property_string(m_halContext, "/org/freedesktop/Hal/devices/computer", "system.chassis.manufacturer", &error);
    m_info[BIOSVENDOR] = libhal_device_get_property_string(m_halContext, "/org/freedesktop/Hal/devices/computer", "system.firmware.vendor", &error);
    m_info[BIOSVERSION] = libhal_device_get_property_string(m_halContext, "/org/freedesktop/Hal/devices/computer", "system.firmware.version", &error);
    m_info[BIOSDATE] = libhal_device_get_property_string(m_halContext, "/org/freedesktop/Hal/devices/computer", "system.firmware.release_date", &error);

    libhal_ctx_free(m_halContext);

    return true;
}
