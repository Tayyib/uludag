/*
  Copyright (c) 2004, 2006 TUBITAK/UEKAE

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  Please read the COPYING file.
*/

#ifndef KAPTAN_H
#define KAPTAN_H

#include <kwizard.h>
#include <kprocess.h>
#include <comar.h>

class KLocale;

class Welcome;
class Mouse;
class Style;
class Wallpaper;
class Network;
class Package;
class Goodbye;

class Kaptan:public KWizard
{
    Q_OBJECT

public:
    Kaptan(QWidget* parent=0, const char *name=0);
    virtual void next();

protected:
    bool checkComarACL(QString methodName);

public slots:
    void aboutToQuit();
    void migration(KProcess*, char*, int);

private:
    KLocale *locale;
    Welcome *welcome;
    Style *style;
    Mouse *mouse;
    Wallpaper *wallpaper;
    Network *network;
    Package *package;
    Goodbye *goodbye;
    // COMAR stuff
    comar_t *comarConnection;
    bool networkEnabled;
    bool packageEnabled;
};

#endif // KAPTAN_H
