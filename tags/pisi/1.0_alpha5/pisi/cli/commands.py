# -*- coding:utf-8 -*-
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

import sys
from optparse import OptionParser
    
import gettext
__trans = gettext.translation('pisi', fallback=True)
_ = __trans.ugettext

import pisi
import pisi.cli
import pisi.context as ctx
from pisi.uri import URI

class Command(object):
    _("""generic help string for any command""")

    # class variables

    cmd = []
    cmd_dict = {}

    def commands_string():
        s = ''
        list = [x.name[0] for x in Command.cmd]
        list.sort()
        for x in list:
            s += x + '\n'
        return s
    commands_string = staticmethod(commands_string)
    
    def get_command(cmd, fail=False):
    
        if Command.cmd_dict.has_key(cmd):
            return Command.cmd_dict[cmd]()
    
        if fail:
            ctx.ui.info(_("Unrecognized command: ") + cmd)
            sys.exit(1)
        else:
            return None
    get_command = staticmethod(get_command)

    # instance variabes

    def __init__(self):
        # now for the real parser
        import pisi
        self.comar = False
        self.parser = OptionParser(usage=getattr(self, "__doc__"),
                                   version="%prog " + pisi.__version__)
        self.options()
        self.commonopts()
        (self.options, self.args) = self.parser.parse_args()
        self.args.pop(0)                # exclude command arg
        
        self.check_auth_info()

    def commonopts(self):
        '''common options'''
        p = self.parser
        p.add_option("-D", "--destdir", action="store")
        p.add_option("", "--yes-all", action="store_true",
                     default=False, help = _("assume yes in all yes/no queries"))
        p.add_option("-u", "--username", action="store")
        p.add_option("-p", "--password", action="store")
        p.add_option("-P", action="store_true", dest="getpass", default=False,
                     help=_("get password from the command line"))
        p.add_option("-v", "--verbose", action="store_true",
                     dest="verbose", default=False,
                     help=_("detailed output"))
        p.add_option("-d", "--debug", action="store_true",
                     default=False, help=_("show debugging information"))
        p.add_option("-n", "--dry-run", action="store_true", default=False,
                     help = _("do not perform any action, just show what\
                     would be done"))
        return p

    def options(self):
        """This is a fall back function. If the implementer module provides an
        options function it will be called"""
        pass

    def check_auth_info(self):
        username = self.options.username
        password = self.options.password

        # TODO: We'll get the username, password pair from a configuration
        # file from users home directory. Currently we need user to
        # give it from the user interface.
        #         if not username and not password:
        #             if someauthconfig.username and someauthconfig.password:
        #                 self.authInfo = (someauthconfig.username,
        #                                  someauthconfig.password)
        #                 return
        if username and password:
            self.authInfo = (username, password)
            return
        
        if username and self.options.getpass:
            from getpass import getpass
            password = getpass(_("Password: "))
            self.authInfo = (username, password)
        else:
            self.authInfo = None

    def init(self, database = True):
        """initialize PiSi components"""
        
        # NB: command imports here or in the command class run fxns
        import pisi.api
        pisi.api.init(database = database, options = self.options,
                      comar = self.comar)

    def finalize(self):
        """do cleanup work for PiSi components"""
        pass
        
    def get_name(self):
        return self.__class__.name

    def format_name(self):
        (name, shortname) = self.get_name()
        if shortname:
            return "%s (%s)" % (name, shortname)
        else:
            return name

    def help(self):
        """print help for the command"""
        ctx.ui.info(self.format_name() + ': ')
        ctx.ui.info(getattr(self, "__doc__") + '\n')
        ctx.ui.info(self.parser.format_option_help())

    def die(self):
        """exit program"""
        ctx.ui.error(_('Program terminated abnormally.'))
        sys.exit(-1)


class autocommand(type):
    def __init__(cls, name, bases, dict):
        super(autocommand, cls).__init__(name, bases, dict)
        Command.cmd.append(cls)
        name = getattr(cls, 'name', None)
        if name is None:
            raise pisi.cli.Error(_('command lacks name'))
        longname, shortname = name
        def add_cmd(cmd):
            if Command.cmd_dict.has_key(cmd):
                raise pisi.cli.Error(_('duplicate command %s') % cmd)
            else:
                Command.cmd_dict[cmd] = cls
        add_cmd(longname)
        if shortname:
            add_cmd(shortname)
            

class Help(Command):
    _("""Prints help for given commands.

Usage: help [ <command1> <command2> ... <commandn> ]

If run without parameters, it prints the general help.""")

    __metaclass__ = autocommand

    def __init__(self):
        #TODO? Discard Help's own usage doc in favor of general usage doc
        #self.__doc__ = usage_text
        #self.__doc__ += commands_string()
        super(Help, self).__init__()

    name = ("help", "h")

    def run(self):
        if not self.args:
            self.parser.set_usage(usage_text)
            ctx.ui.info(self.parser.format_help())
            return
            
        self.init()
        
        for arg in self.args:
            obj = Command.get_command(arg, True)
            obj.help()
            ctx.ui.info('')
        
        self.finalize()

class Clean(Command):
    _("""Clean stale locks.""")

    __metaclass__ = autocommand

    def __init__(self):
        super(Clean, self).__init__()

    name = ("clean", None)

    def run(self):
        self.init()
        pisi.util.clean_locks()
        self.finalize()
        

class Graph(Command):
    _("""Graph package relations.
Usage: graph <package1> <package2> ...

Write a graph of package relations, tracking dependency and
conflicts relations starting from given packages.
""")

    __metaclass__ = autocommand

    def __init__(self):
        super(Graph, self).__init__()

    name = ("graph", None)

    def run(self):
        self.init()
        if self.args:
            g = pisi.api.package_graph(self.args)
            g.write_graphviz(file('pgraph.dot', 'w'))
        self.finalize()


def buildno_opts(self):
    self.parser.add_option("", "--ignore-build-no", action="store_true",
                           default=False,
                           help=_("do not take build no into account."))


class Build(Command):
    _("""Build a PISI package using a pspec.xml file

Usage: build <pspec.xml>

You can give a URI of the pspec.xml file. PISI will
fetch all necessary files and build the package for you.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(Build, self).__init__()

    name = ("build", "bi")

    def options(self):
        buildno_opts(self)
        self.parser.add_option("-O", "--output-dir", action="store", default=".",
                               help=_("output directory for produced packages"))

    def run(self):
        if not self.args:
            self.help()
            return

        self.init()
        ctx.ui.info('Output directory: %s\n' % ctx.config.options.output_dir)
        for arg in self.args:
            pisi.api.build(arg, self.authInfo)
        self.finalize()


class PackageOp(Command):
    """Abstract package operation command"""

    def __init__(self):
        super(PackageOp, self).__init__()
        self.comar = True

    def options(self):
        p = self.parser
        p.add_option("-B", "--ignore-comar", action="store_true",
                     default=False, help=_("bypass comar configuration agent"))
        p.add_option("", "--ignore-dependency", action="store_true",
                     default=False,
                     help=_("do not take dependency information into account"))

    def init(self):
        super(PackageOp, self).init(True)
                
    def finalize(self):
        #self.finalize_db()
        pass

class Install(PackageOp):
    _("""Install PISI packages

Usage: install <package1> <package2> ... <packagen>

You may use filenames, URIs or package names for packages. If you have
specified a package name, it should exist in a specified repository.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(Install, self).__init__()

    name = "install", "it"

    def options(self):
        super(Install, self).options()
        buildno_opts(self)

    def run(self):
        if not self.args:
            self.help()
            return

        self.init()
        pisi.api.install(self.args)
        self.finalize()

class Upgrade(PackageOp):
    _("""Upgrade PISI packages

Usage: Upgrade <package1> <package2> ... <packagen>

You may use only package names to specify packages because
the package upgrade operation is defined only with respect 
to repositories. If you have specified a package name, it
should exist in the package repositories. If you just want to
reinstall a package from a pisi file, use the install command.""")

    __metaclass__ = autocommand

    def __init__(self):
        super(Upgrade, self).__init__()

    name = ("upgrade", "up")

    def options(self):
        super(Upgrade, self).options()
        buildno_opts(self)

    def run(self):
        if not self.args:
            self.help()
            return

        self.init()
        pisi.api.upgrade(self.args)
        self.finalize()


class Remove(PackageOp):
    _("""Remove PISI packages

Usage: remove <package1> <package2> ... <packagen>

Remove package(s) from your system. Just give the package names to remove.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(Remove, self).__init__()

    name = ("remove", "rm")

    def run(self):
        if not self.args:
            self.help()
            return

        self.init()
        pisi.api.remove(self.args)
        self.finalize()


class UpgradeAll(PackageOp):
    _("""Upgrade system

Usage: Upgrade

Upgrade the entire system.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(UpgradeAll, self).__init__()

    name = ("upgrade-all", None)

    def options(self):
        super(UpgradeAll, self).options()
        buildno_opts(self)

    def run(self):
        if self.args:
            self.help()
            return

        self.init()
        pisi.api.upgrade(ctx.installdb.list_installed())
        self.finalize()


class ConfigurePending(PackageOp):
    _("""configure pending packages
    """)
    
    __metaclass__ = autocommand

    def __init__(self):
        super(ConfigurePending, self).__init__()

    name = ("configure-pending", "cp")

    def run(self):

        self.init()
        pisi.api.configure_pending()
        self.finalize()


class Info(Command):
    _("""Display package information

Usage: info <package1> <package2> ... <packagen>

""")
    __metaclass__ = autocommand

    def __init__(self):
        super(Info, self).__init__()

    name = ("info", "i")

    def options(self):
        self.parser.add_option("-f", "--files", action="store_true",
                               default=False,
                               help=_("show a list of package files."))
        self.parser.add_option("-F", "--files-path", action="store_true",
                               default=False,
                               help=_("Show only paths."))

    def run(self):
        if not self.args:
            self.help()
            return

        self.init(True)
        for arg in self.args:
            self.printinfo(arg)
        self.finalize()

    def printinfo(self, arg):
        import os.path

        metadata, files = pisi.api.info(arg)
        ctx.ui.info(str(metadata.package))
        if self.options.files or self.options.files_path:
            if files:
                ctx.ui.info(_('\nFiles:'))
                for fileinfo in files.list:
                    if self.options.files:
                        print fileinfo
                    else:
                        print fileinfo.path
            else:
                ctx.ui.warning(_('File information not available'))


class Index(Command):
    _("""Index PISI files in a given directory

Usage: index <directory>

This command searches for all PiSi files in a directory, collects PiSi
tags from them and accumulates the information in an output XML file,
named by default 'pisi-index.xml'. In particular, it indexes both
source and binary packages.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(Index, self).__init__()

    name = ("index", "ix")

    def options(self):
        self.parser.add_option("-a", "--absolute-uris", action="store_true",
                               default=False,
                               help=_("store absolute links for indexed files."))

    def run(self):
        
        self.init()
        from pisi.api import index
        if len(self.args)==1:
            index(self.args[0])
        elif len(self.args)==0:
            ctx.ui.info( _('Indexing current directory.'))
            index()
        else:
            ctx.ui.info( _('Indexing only a single directory supported.'))
            return
        self.finalize()


class ListInstalled(Command):
    _("""Print the list of all installed packages  

Usage: list-installed

""")

    __metaclass__ = autocommand

    def __init__(self):
        super(ListInstalled, self).__init__()

    name = ("list-installed", "li")

    def options(self):
        self.parser.add_option("-l", "--long", action="store_true",
                               default=False, help="show in long format")
        self.parser.add_option("-i", "--install-info", action="store_true",
                               default=False, help="show detailed install info")

    def run(self):
        self.init(True)
        list = ctx.installdb.list_installed()
        list.sort()
        if self.options.install_info:
            ctx.ui.info(_('Package Name     |St|   Version|  Rel.| Build|  Distro|             Date'))
            print         '========================================================================'
        for pkg in list:
            package = pisi.packagedb.inst_packagedb.get_package(pkg)
            inst_info = ctx.installdb.get_info(pkg)
            if self.options.long:
                ctx.ui.info(package)
                ctx.ui.info(inst_info)
            elif self.options.install_info:
                ctx.ui.info('%-15s | %s ' % (package.name, inst_info.one_liner()))
            else:
                ctx.ui.info('%15s - %s ' % (package.name, package.summary))
        self.finalize()


class UpdateRepo(Command):
    _("""Update repository databases

Usage: update-repo <repo1> <repo2> ... <repon>

<repoi>: repository name
Synchronizes the PiSi databases with the current repository.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(UpdateRepo, self).__init__()

    name = ("update-repo", "ur")

    def run(self):
        if not self.args:
            self.help()
            return

        self.init(True)
        for repo in self.args:
            pisi.api.update_repo(repo)
        self.finalize()


class AddRepo(Command):
    _("""Add a repository

Usage: add-repo <repo> <indexuri>

<repo>: name of repository to add
<indexuri>: URI of index file

NB: We support only local files (e.g., /a/b/c) and http:// URIs at the moment
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(AddRepo, self).__init__()

    name = ("add-repo", "ar")

    def run(self):

        if len(self.args)>=2:
            self.init()
            name = self.args[0]
            indexuri = self.args[1]
            pisi.api.add_repo(name, indexuri)
            self.init()
        else:
            self.help()
            return


class RemoveRepo(Command):
    _("""Remove repositories

Usage: remove-repo <repo1> <repo2> ... <repon>

Remove all repository information from the system.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(RemoveRepo, self).__init__()

    name = ("remove-repo", "rr")

    def run(self):

        if len(self.args)>=1:
            self.init()
            for repo in self.args:
                pisi.api.remove_repo(repo)
            self.finalize()
        else:
            self.help()
            return


class ListRepo(Command):
    _("""List repositories

Usage: list-repo

Lists currently tracked repositories.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(ListRepo, self).__init__()

    name = ("list-repo", "lr")

    def run(self):

        self.init()
        for repo in ctx.repodb.list():
            ctx.ui.info(repo)
            print '  ', ctx.repodb.get_repo(repo).indexuri.get_uri()
        self.finalize()


class ListAvailable(Command):
    _("""List available packages in the repositories

Usage: list-available [ <repo1> <repo2> ... repon ]

Gives a brief list of PiSi components published in the repository.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(ListAvailable, self).__init__()

    name = ("list-available", "la")

    def run(self):

        self.init(True)

        if self.args:
            for arg in self.args:
                self.print_packages(arg)
        else:
            # print for all repos
            for repo in ctx.repodb.list():
                ctx.ui.info(_("Repository : %s\n") % repo)
                self.print_packages(repo)
        self.finalize()

    def print_packages(self, repo):
        from pisi import packagedb
        from colors import colorize

        pkg_db = packagedb.get_db(repo)
        list = pkg_db.list_packages()
        installed_list = ctx.installdb.list_installed()
        list.sort()
        for p in list:
            if p in installed_list:
                print colorize(p, "cyan")
            else:
                print p

class ListUpgrades(Command):
    _("""List packages to be upgraded

Usage: list-upgrades [ <repo1> <repo2> ... repon ]

""")
    __metaclass__ = autocommand

    def __init__(self):
        super(ListUpgrades, self).__init__()

    name = ("list-upgrades", "lu")

    def options(self):
        self.parser.add_option("-l", "--long", action="store_true",
                               default=False, help="show in long format")
        self.parser.add_option("-i", "--install-info", action="store_true",
                               default=False, help=_("show detailed install info"))
        buildno_opts(self)
                               
    def run(self):
        self.init(True)
        list = pisi.api.list_upgradable()
        list.sort()
        if self.options.install_info:
            ctx.ui.info(_('Package Name     |St|   Version|  Rel.| Build|  Distro|             Date'))
            print         '========================================================================'
        for pkg in list:
            package = pisi.packagedb.inst_packagedb.get_package(pkg)
            inst_info = ctx.installdb.get_info(pkg)
            if self.options.long:
                ctx.ui.info(package)
                print inst_info
            elif self.options.install_info:
                ctx.ui.info('%-15s | %s ' % (package.name, inst_info.one_liner()))
            else:
                ctx.ui.info('%15s - %s ' % (package.name, package.summary))
        self.finalize()


class ListPending(Command):
    _("""List pending packages""")

    __metaclass__ = autocommand

    def __init__(self):
        super(ListPending, self).__init__()
    
    name = ("list-pending", "lp")

    def run(self):
        self.init(True)

        list = ctx.installdb.list_pending()
        list.sort()
        for p in list:
            print p

        self.finalize()


class Search(Command):
    _("""Search packages

Usage: search <search pattern>

#FIXME: fill this later
""")
    pass


# Partial build commands        

class BuildUntil(Build):
    _("""Run the build process partially

Usage: -sStateName build-until <pspec file>

where states are:
unpack, setupaction, buildaction, installaction, buildpackages

You can give an URI of the pspec.xml file. PISI will fetch all
necessary files and unpack the source and prepare a source directory
for you.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(BuildUntil, self).__init__()

    name = ("build-until", "bu")

    def options(self):
        super(BuildUntil, self).options()        
        self.parser.add_option("-s", action="store", dest="state")

    def run(self):

        if not self.args:
            self.help()
            return

        self.init()
        state = self.options.state

        for arg in self.args:
            pisi.api.build_until(arg, state, self.authInfo)
        self.finalize()


class BuildUnpack(Build):
    _("""Unpack the source archive

Usage: build-unpack <pspec file>

TODO: desc.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(BuildUnpack, self).__init__()

    name = ("build-unpack", "biu")

    def run(self):
        if not self.args:
            self.help()
            return

        self.init()
        for arg in self.args:
            pisi.api.build_until(arg, "unpack", self.authInfo)
        self.finalize()


class BuildSetup(Build):
    _("""Setup the source

Usage: build-setup <pspec file>

TODO: desc.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(BuildSetup, self).__init__()

    name = ("build-setup", "bis")

    def run(self):
        if not self.args:
            self.help()
            return

        self.init()
        for arg in self.args:
            pisi.api.build_until(arg, "setupaction",
                                      self.authInfo)
        self.finalize()


class BuildBuild(Command):
    _("""Setup the source

Usage: build-build <pspec file>

TODO: desc.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(BuildBuild, self).__init__()

    name = ("build-build", "bib")

    def run(self):
        if not self.args:
            self.help()
            return

        self.init()
        for arg in self.args:
            pisi.api.build_until(arg, "buildaction", self.authInfo)
        self.finalize()


class BuildInstall(Build):
    _("""Install to the sandbox

Usage: build-install <pspec file>

TODO: desc.
""")
    __metaclass__ = autocommand

    def __init__(self):
        super(BuildInstall, self).__init__()

    name = ("build-install", "bii")

    def run(self):
        if not self.args:
            self.help()
            return

        self.init()
        for arg in self.args:
            pisi.api.build_until(arg, "installaction",
                                      self.authInfo)
        self.finalize()


class BuildPackage(Build):
    _("""Setup the source

Usage: build-build <pspec file>

TODO: desc.
""")

    __metaclass__ = autocommand

    def __init__(self):
        super(BuildPackage, self).__init__()

    name = ("build-package", "bip")

    def run(self):
        if not self.args:
            self.help()
            return

        self.init()
        for arg in self.args:
            pisi.api.build_until(arg, "buildpackages", self.authInfo)
        self.finalize()

usage_text1 = _("""%prog [options] <command> [arguments]

where <command> is one of:

""")

usage_text2 = _("""
Use \"%prog help <command>\" for help on a specific command.
""")

usage_text = (usage_text1 + Command.commands_string() + usage_text2)
