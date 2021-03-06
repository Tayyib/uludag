# -*- coding: utf-8 -*-
#
# Copyright (C) 2005 - 2007, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.

"""package building code"""

# python standard library
import os
import glob
import copy
import stat
import pwd
import grp

import gettext
__trans = gettext.translation('pisi', fallback=True)
_ = __trans.ugettext

import pisi
import pisi.specfile
import pisi.util
import pisi.file
import pisi.context as ctx
import pisi.dependency as dependency
import pisi.api
import pisi.sourcearchive
import pisi.files
import pisi.fetcher
import pisi.uri
import pisi.metadata
import pisi.package
import pisi.component as component
import pisi.archive as archive
import pisi.actionsapi.variables
import pisi.db

class Error(pisi.Error):
    pass

# Helper Functions
def get_file_type(path, pinfo_list, install_dir):
    """Return the file type of a path according to the given PathInfo
    list"""

    Match = lambda x: [match for match in glob.glob(install_dir + x) if pisi.util.join_path(install_dir, path).find(match) > -1]

    def Sort(x):
        x.sort(reverse=True)
        return x

    best_matched_path = Sort([pinfo.path for pinfo in pinfo_list if Match(pinfo.path)])[0]
    info = [pinfo for pinfo in pinfo_list if best_matched_path == pinfo.path][0]
    return info.fileType, info.permanent

def check_path_collision(package, pkgList):
    """This function will check for collision of paths in a package with
    the paths of packages in pkgList. The return value will be the
    list containing the paths that collide."""
    collisions = []
    for pinfo in package.files:
        for pkg in pkgList:
            if pkg is package:
                continue
            for path in pkg.files:
                # if pinfo.path is a subpath of path.path like
                # the example below. path.path is marked as a
                # collide. Exp:
                # pinfo.path: /usr/share
                # path.path: /usr/share/doc
                if (path.path.endswith(ctx.const.ar_file_suffix) and ctx.get_option('create_static')) or \
                   (path.path.endswith(ctx.const.debug_file_suffix) and ctx.config.values.build.generatedebug):
                    # don't throw collision error for these files.
                    # we'll handle this in gen_files_xml..
                    continue
                if pisi.util.subpath(pinfo.path, path.path):
                    collisions.append(path.path)
                    ctx.ui.debug(_('Path %s belongs in multiple packages') %
                                 path.path)
    return collisions


class Builder:
    """Provides the package build and creation routines"""
    #FIXME: this class and every other class must use URLs as paths!

    @staticmethod
    def from_name(name):
        repodb = pisi.db.repodb.RepoDB()
        sourcedb = pisi.db.sourcedb.SourceDB()
        # download package and return an installer object
        # find package in repository
        sf, reponame = sourcedb.get_spec_repo(name)
        src = sf.source
        if src:

            src_uri = pisi.uri.URI(src.sourceURI)
            if src_uri.is_absolute_path():
                src_path = str(src_uri)
            else:
                repo = repodb.get_repo(reponame)
                #FIXME: don't use dirname to work on URLs
                src_path = os.path.join(os.path.dirname(repo.indexuri.get_uri()),
                                        str(src_uri.path()))

            ctx.ui.debug(_("Source URI: %s") % src_path)

            return Builder(src_path)
        else:
            raise Error(_("Source %s not found in any active repository.") % name)

    def __init__(self, specuri):

        # process args
        if not isinstance(specuri, pisi.uri.URI):
            specuri = pisi.uri.URI(specuri)

        # read spec file, we'll need it :)
        self.set_spec_file(specuri)

        if specuri.is_remote_file():
            self.specdir = self.fetch_files()
        else:
            self.specdir = os.path.dirname(self.specuri.get_uri())

        self.read_translations(self.specdir)

        self.sourceArchive = pisi.sourcearchive.SourceArchive(self.spec, self.pkg_work_dir())

        self.set_environment_vars()

        self.actionLocals = None
        self.actionGlobals = None
        self.srcDir = None

        self.componentdb = pisi.db.componentdb.ComponentDB()
        self.installdb = pisi.db.installdb.InstallDB()

    def set_spec_file(self, specuri):
        if not specuri.is_remote_file():
            specuri = pisi.uri.URI(os.path.realpath(specuri.get_uri()))  # FIXME: doesn't work for file://
        self.specuri = specuri
        spec = pisi.specfile.SpecFile()
        spec.read(self.specuri, ctx.config.tmp_dir())
        self.spec = spec

    def read_translations(self, specdir):
        self.spec.read_translations(pisi.util.join_path(specdir, ctx.const.translations_file))

    # directory accessor functions

    # pkg_x_dir: per package directory for storing info type x

    def pkg_dir(self):
        "package build directory"
        packageDir = self.spec.source.name + '-' + \
                     self.spec.getSourceVersion() + '-' + self.spec.getSourceRelease()
        return pisi.util.join_path(ctx.config.dest_dir(), ctx.config.values.dirs.tmp_dir,
                     packageDir)

    def pkg_work_dir(self):
        return self.pkg_dir() + ctx.const.work_dir_suffix

    def pkg_debug_dir(self):
        return self.pkg_dir() + ctx.const.debug_dir_suffix

    def pkg_install_dir(self):
        return self.pkg_dir() + ctx.const.install_dir_suffix

    def set_state(self, state):
        stateFile = pisi.util.join_path(self.pkg_work_dir(), "pisiBuildState")
        open(stateFile, "w").write(state)

    def get_state(self):
        stateFile = pisi.util.join_path(self.pkg_work_dir(), "pisiBuildState")
        if not os.path.exists(stateFile): # no state
            return None
        return open(stateFile, "r").read()

    def build(self):
        """Build the package in one shot."""

        ctx.ui.status(_("Building PiSi source package: %s") % self.spec.source.name)

        self.compile_action_script()
        self.compile_comar_script()

        # check if all patch files exists, if there are missing no need to unpack!
        self.patch_exists()

        self.check_build_dependencies()
        self.fetch_component()
        self.fetch_source_archive()
        self.unpack_source_archive()

        self.run_setup_action()
        self.run_build_action()
        if ctx.get_option('debug') and not ctx.get_option('ignore_check'):
            self.run_check_action()
        self.run_install_action()

        # after all, we are ready to build/prepare the packages
        return self.build_packages()

    def set_environment_vars(self):
        """Sets the environment variables for actions API to use"""

        # Each time a builder is created we must reset
        # environment. See bug #2575
        pisi.actionsapi.variables.initVariables()

        env = {
            "PKG_DIR": self.pkg_dir(),
            "WORK_DIR": self.pkg_work_dir(),
            "INSTALL_DIR": self.pkg_install_dir(),
            "SRC_NAME": self.spec.source.name,
            "SRC_VERSION": self.spec.getSourceVersion(),
            "SRC_RELEASE": self.spec.getSourceRelease()
            }
        os.environ.update(env)

        # First check icecream, if not found use ccache, no need to use both
        # together (according to kde-wiki it cause performance loss)
        if ctx.config.values.build.buildhelper == "icecream":
            if os.path.exists("/opt/icecream/bin/gcc"):
                # Add icecream directory for support distributed compiling :)
                os.environ["PATH"] = "/opt/icecream/bin/:%s" % os.environ["PATH"]
                ctx.ui.info(_("IceCream detected. Make sure your daemon is up and running..."))
        elif ctx.config.values.build.buildhelper == "ccache":
            if os.path.exists("/usr/lib/ccache/bin/gcc"):
                # Add ccache directory for support Compiler Cache :)
                os.environ["PATH"] = "/usr/lib/ccache/bin/:%s" % os.environ["PATH"]
                ctx.ui.info(_("CCache detected..."))

    def fetch_files(self):
        self.specdiruri = os.path.dirname(self.specuri.get_uri())
        pkgname = os.path.basename(self.specdiruri)
        self.destdir = pisi.util.join_path(ctx.config.tmp_dir(), pkgname)
        #self.location = os.path.dirname(self.url.uri)

        self.fetch_pspecfile()
        self.fetch_actionsfile()
        self.fetch_translationsfile()
        self.fetch_patches()
        self.fetch_comarfiles()
        self.fetch_additionalFiles()

        return self.destdir

    def fetch_pspecfile(self):
        pspecuri = pisi.util.join_path(self.specdiruri, ctx.const.pspec_file)
        self.download(pspecuri, self.destdir)

    def fetch_actionsfile(self):
        actionsuri = pisi.util.join_path(self.specdiruri, ctx.const.actions_file)
        self.download(actionsuri, self.destdir)

    def fetch_translationsfile(self):
        translationsuri = pisi.util.join_path(self.specdiruri, ctx.const.translations_file)
        try:
            self.download(translationsuri, self.destdir)
        except pisi.fetcher.FetchError:
            # translations.xml is not mandatory for PiSi
            pass

    def fetch_patches(self):
        spec = self.spec
        for patch in spec.source.patches:
            file_name = os.path.basename(patch.filename)
            dir_name = os.path.dirname(patch.filename)
            patchuri = pisi.util.join_path(self.specdiruri,
                            ctx.const.files_dir, dir_name, file_name)
            self.download(patchuri, pisi.util.join_path(self.destdir, ctx.const.files_dir, dir_name))

    def fetch_comarfiles(self):
        spec = self.spec
        for package in spec.packages:
            for pcomar in package.providesComar:
                comaruri = pisi.util.join_path(self.specdiruri,
                                ctx.const.comar_dir, pcomar.script)
                self.download(comaruri, pisi.util.join_path(self.destdir, ctx.const.comar_dir))

    def fetch_additionalFiles(self):
        spec = self.spec
        for pkg in spec.packages:
            for afile in pkg.additionalFiles:
                file_name = os.path.basename(afile.filename)
                dir_name = os.path.dirname(afile.filename)
                afileuri = pisi.util.join_path(self.specdiruri,
                                ctx.const.files_dir, dir_name, file_name)
                self.download(afileuri, pisi.util.join_path(self.destdir, ctx.const.files_dir, dir_name))

    def download(self, uri, transferdir):
        # fix auth info and download
        uri = pisi.file.File.make_uri(uri)
        pisi.file.File.download(uri, transferdir)

    def fetch_component(self):
        if not self.spec.source.partOf:
            ctx.ui.warning(_('PartOf tag not defined, looking for component'))
            diruri = pisi.util.parenturi(self.specuri.get_uri())
            parentdir = pisi.util.parenturi(diruri)
            url = pisi.util.join_path(parentdir, 'component.xml')
            progress = ctx.ui.Progress
            if pisi.uri.URI(url).is_remote_file():
                pisi.fetcher.fetch_url(url, self.pkg_work_dir(), progress)
                path = pisi.util.join_path(self.pkg_work_dir(), 'component.xml')
            else:
                if not os.path.exists(url):
                    raise Exception(_('Cannot find component.xml in upper directory'))
                path = url
            comp = component.Component()
            comp.read(path)
            ctx.ui.info(_('Source is part of %s component') % comp.name)
            self.spec.source.partOf = comp.name

    def fetch_source_archive(self):
        ctx.ui.info(_("Fetching source from: %s") % self.spec.source.archive.uri)
        self.sourceArchive.fetch()
        ctx.ui.info(_("Source archive is stored: %s/%s")
                %(ctx.config.archives_dir(), self.spec.source.archive.name))

    def unpack_source_archive(self):
        ctx.ui.info(_("Unpacking archive..."))
        self.sourceArchive.unpack()
        # apply the patches and prepare a source directory for build.
        if self.apply_patches():
            ctx.ui.info(_(" unpacked (%s)") % self.pkg_work_dir())
            self.set_state("unpack")

    def run_setup_action(self):
        #  Run configure, build and install phase
        ctx.ui.action(_("Setting up source..."))
        if self.run_action_function(ctx.const.setup_func):
            self.set_state("setupaction")

    def run_build_action(self):
        ctx.ui.action(_("Building source..."))
        if self.run_action_function(ctx.const.build_func):
            self.set_state("buildaction")

    def run_check_action(self):
        ctx.ui.action(_("Testing package..."))
        self.run_action_function(ctx.const.check_func)

    def run_install_action(self):
        ctx.ui.action(_("Installing..."))

        # Before install make sure install_dir is clean
        if os.path.exists(self.pkg_install_dir()):
            pisi.util.clean_dir(self.pkg_install_dir())

        # install function is mandatory!
        if self.run_action_function(ctx.const.install_func, True):
            self.set_state("installaction")

    def get_abandoned_files(self):
        # return the files those are not collected from the install dir

        install_dir = self.pkg_dir() + ctx.const.install_dir_suffix
        abandoned_files = []
        all_paths_in_packages = []


        for package in self.spec.packages:
            for path in package.files:
                map(lambda p: all_paths_in_packages.append(p), [p for p in glob.glob(install_dir + path.path)])

        for root, dirs, files in os.walk(install_dir):
            for file_ in files:
                already_in_package = False
                fpath = pisi.util.join_path(root, file_)
                for path in all_paths_in_packages:
                    if not fpath.find(path):
                        already_in_package = True
                if not already_in_package:
                    abandoned_files.append(fpath)

        return abandoned_files

    def compile_action_script(self):
        """Compiles given actions.py to check syntax error in it and sets the actionLocals and actionGlobals"""
        fname = pisi.util.join_path(self.specdir, ctx.const.actions_file)
        try:
            localSymbols = globalSymbols = {}
            buf = open(fname).read()
            exec compile(buf, "error", "exec") in localSymbols, globalSymbols
        except IOError, e:
            raise Error(_("Unable to read Actions Script (%s): %s") %(fname,e))
        except SyntaxError, e:
            raise Error(_("SyntaxError in Actions Script (%s): %s") %(fname,e))

        self.actionLocals = localSymbols
        self.actionGlobals = globalSymbols
        self.srcDir = self.pkg_src_dir()

    def compile_comar_script(self):
        """Compiles comar scripts to check syntax errors"""
        for package in self.spec.packages:
            for pcomar in package.providesComar:
                fname = pisi.util.join_path(self.specdir, ctx.const.comar_dir,
                                     pcomar.script)

                try:
                    buf = open(fname).read()
                    compile(buf, "error", "exec")
                except IOError, e:
                    raise Error(_("Unable to read COMAR script (%s): %s") %(fname,e))
                except SyntaxError, e:
                    raise Error(_("SyntaxError in COMAR file (%s): %s") %(fname,e))

    def pkg_src_dir(self):
        """Returns the real path of WorkDir for an unpacked archive."""
        try:
            workdir = self.actionGlobals['WorkDir']
        except KeyError:
            workdir = self.spec.source.name + "-" + self.spec.getSourceVersion()

        return pisi.util.join_path(self.pkg_work_dir(), workdir)

    def log_sandbox_violation(self, operation, path, canonical_path):
        ctx.ui.error(_("Sandbox violation: %s (%s -> %s)") % (operation, path, canonical_path))

    def run_action_function(self, func, mandatory=False):
        """Calls the corresponding function in actions.py.

        If mandatory parameter is True, and function is not present in
        actionLocals pisi.build.Error will be raised."""
        # we'll need our working directory after actionscript
        # finished its work in the archive source directory.
        curDir = os.getcwd()
        os.chdir(self.srcDir)

        if func in self.actionLocals:
            if not ctx.get_option('enable_sandbox'):
                self.actionLocals[func]()
            else:
                import catbox
                # stupid autoconf family needs /usr/lib/conftest* and /usr/lib/cf* for some conftest,
                # http://sources.gentoo.org/viewcvs.py/portage/trunk/sandbox/files/sandbox/sandbox.c also permits these
                valid_dirs = [self.pkg_dir(), "/tmp/", "/var/tmp/", "/dev/tty", "/dev/pts/", "/dev/pty", "/dev/null", "/dev/zero", "/dev/ptmx", "/proc/", "/usr/lib/conftest", "/usr/lib/cf"]
                if ctx.config.values.build.buildhelper == "ccache":
                    valid_dirs.append("%s/.ccache" % os.environ["HOME"])
                # every qt/KDE application check these
                valid_dirs.append("%s/.qt/.qt_plugins_3.3rc.lock" % os.environ["HOME"])
                valid_dirs.append("%s/.qt/qt_plugins_3.3rc.tmp" % os.environ["HOME"])
                valid_dirs.append("%s/.qt/.qtrc.lock" % os.environ["HOME"])
                valid_dirs.append("%s/.qt/.qt_designerrc.lock" % os.environ["HOME"])
                valid_dirs.append("/usr/qt/3/etc/settings/.qt_plugins_3.3rc.lock")
                valid_dirs.append("/usr/qt/3/etc/settings/qt_plugins_3.3rc.tmp")
                valid_dirs.append("/usr/qt/3/etc/settings/qt_plugins_3.3rc")
                ret = catbox.run(self.actionLocals[func], valid_dirs, logger=self.log_sandbox_violation)
                if ret.code == 1:
                    raise RuntimeError
                if ret.violations != []:
                    ctx.ui.error(_("Sandbox violations!"))
        else:
            if mandatory:
                raise Error(_("unable to call function from actions: %s") % func)
        
        os.chdir(curDir)
        return True

    def check_build_dependencies(self):
        """check and try to install build dependencies, otherwise fail."""

        build_deps = self.spec.source.buildDependencies

        if not ctx.get_option('ignore_safety'):
            if self.componentdb.has_component('system.devel'):
                build_deps_names = set([x.package for x in build_deps])
                devel_deps_names = set(self.componentdb.get_component('system.devel').packages)
                extra_names = devel_deps_names - build_deps_names
                extra_names = filter(lambda x: not self.installdb.has_package(x), extra_names)
                if extra_names:
                    ctx.ui.warning(_('Safety switch: following extra packages in system.devel will be installed: ') +
                               pisi.util.strlist(extra_names))
                    extra_deps = [dependency.Dependency(package = x) for x in extra_names]
                    build_deps.extend(extra_deps)
                else:
                    ctx.ui.warning(_('Safety switch: system.devel is already installed'))
            else:
                ctx.ui.warning(_('Safety switch: the component system.devel cannot be found'))

        # find out the build dependencies that are not satisfied...
        dep_unsatis = []
        for dep in build_deps:
            if not dependency.installed_satisfies_dep(dep):
                dep_unsatis.append(dep)

        if dep_unsatis:
            ctx.ui.info(_("Unsatisfied Build Dependencies:") + ' '
                        + pisi.util.strlist([str(x) for x in dep_unsatis]) )

            def fail():
                raise Error(_('Cannot build package due to unsatisfied build dependencies'))

            if ctx.config.get_option('no_install'):
                fail()

            if not ctx.config.get_option('ignore_dependency'):
                for dep in dep_unsatis:
                    if not dependency.repo_satisfies_dep(dep):
                        raise Error(_('Build dependency %s cannot be satisfied') % str(dep))
                if ctx.ui.confirm(
                _('Do you want to install the unsatisfied build dependencies')):
                    ctx.ui.info(_('Installing build dependencies.'))
                    pisi.api.install([dep.package for dep in dep_unsatis])
                else:
                    fail()
            else:
                ctx.ui.warning(_('Ignoring build dependencies.'))

    def patch_exists(self):
        """check existence of patch files declared in PSPEC"""

        files_dir = os.path.abspath(pisi.util.join_path(self.specdir,
                                                 ctx.const.files_dir))
        for patch in self.spec.source.patches:
            patchFile = pisi.util.join_path(files_dir, patch.filename)
            if not os.access(patchFile, os.F_OK):
                raise Error(_("Patch file is missing: %s\n") % patch.filename)

    def apply_patches(self):
        files_dir = os.path.abspath(pisi.util.join_path(self.specdir,
                                                 ctx.const.files_dir))

        for patch in self.spec.source.patches:
            patchFile = pisi.util.join_path(files_dir, patch.filename)
            if patch.compressionType:
                patchFile = pisi.util.uncompress(patchFile,
                                            compressType=patch.compressionType,
                                            targetDir=ctx.config.tmp_dir())

            ctx.ui.action(_("* Applying patch: %s") % patch.filename)
            pisi.util.do_patch(self.srcDir, patchFile, level=patch.level)
        return True
        return True

    def generate_static_package_object(self):
        ar_files = []
        for root, dirs, files in os.walk(self.pkg_install_dir()):
            for f in files:
                if f.endswith(ctx.const.ar_file_suffix) and pisi.util.is_ar_file(pisi.util.join_path(root, f)):
                    ar_files.append(pisi.util.join_path(root, f))

        if not len(ar_files):
            return None

        static_package_obj = pisi.specfile.Package()
        static_package_obj.name = self.spec.source.name + ctx.const.static_name_suffix
        # FIXME: find a better way to deal with the summary and description constants.
        static_package_obj.summary['en'] = u'Ar files for %s' % (self.spec.source.name)
        static_package_obj.description['en'] = u'Ar files for %s' % (self.spec.source.name)
        static_package_obj.partOf = self.spec.source.partOf
        for f in ar_files:
            static_package_obj.files.append(pisi.specfile.Path(path = f[len(self.pkg_install_dir()):], fileType = "library"))

        # append all generated packages to dependencies
        for p in self.spec.packages:
            static_package_obj.packageDependencies.append(
                pisi.dependency.Dependency(package = p.name))

        return static_package_obj

    def generate_debug_package_object(self):
        debug_files = []
        for root, dirs, files in os.walk(self.pkg_debug_dir()):
            for f in files:
                if f.endswith(ctx.const.debug_file_suffix):
                    debug_files.append(pisi.util.join_path(root, f))

        if not len(debug_files):
            return None

        debug_package_obj = pisi.specfile.Package()
        debug_package_obj.debug_package = True
        debug_package_obj.name = self.spec.source.name + ctx.const.debug_name_suffix
        # FIXME: find a better way to deal with the summary and description constants.
        debug_package_obj.summary['en'] = u'Debug files for %s' % (self.spec.source.name)
        debug_package_obj.description['en'] = u'Debug files for %s' % (self.spec.source.name)
        debug_package_obj.partOf = self.spec.source.partOf + '-debug'
        for f in debug_files:
            debug_package_obj.files.append(pisi.specfile.Path(path = f[len(self.pkg_debug_dir()):], fileType = "debug"))

        # append all generated packages to dependencies
        for p in self.spec.packages:
            debug_package_obj.packageDependencies.append(
                pisi.dependency.Dependency(package = p.name))

        return debug_package_obj

    def strip_install_dir(self):
        """strip install directory"""
        ctx.ui.action(_("Stripping files.."))
        install_dir = self.pkg_install_dir()
        try:
            nostrip = self.actionGlobals['NoStrip']
            pisi.util.strip_directory(install_dir, nostrip)
        except KeyError:
            pisi.util.strip_directory(install_dir)

    def gen_metadata_xml(self, package):
        """Generate the metadata.xml file for build source.

        metadata.xml is composed of the information from specfile plus
        some additional information."""
        metadata = pisi.metadata.MetaData()
        metadata.from_spec(self.spec.source, package, self.spec.history)

        metadata.package.distribution = ctx.config.values.general.distribution
        metadata.package.distributionRelease = ctx.config.values.general.distribution_release
        metadata.package.architecture = ctx.config.values.general.architecture
        metadata.package.packageFormat = ctx.get_option('package_format')

        size = 0
        for fileinfo in self.files.list:
            size += fileinfo.size

        metadata.package.installedSize = size

        self.metadata = metadata

    def gen_files_xml(self, package):
        """Generates files.xml using the path definitions in specfile and
        the files produced by the build system."""
        files = pisi.files.Files()

        if package.debug_package:
            install_dir = self.pkg_debug_dir()
        else:
            install_dir = self.pkg_install_dir()

        # FIXME: We need to expand globs before trying to calculate hashes
        # Not on the fly like now.

        # we'll exclude collisions in get_file_hashes. Having a
        # collisions list is not wrong, we must just handle it :).
        collisions = check_path_collision(package, self.spec.packages)
        # FIXME: material collisions after expanding globs could be
        # reported as errors

        d = {}
        def add_path(path):
            # add the files under material path
            for fpath, fhash in pisi.util.get_file_hashes(path, collisions, install_dir):
                if ctx.get_option('create_static') \
                    and fpath.endswith(ctx.const.ar_file_suffix) \
                    and not package.name.endswith(ctx.const.static_name_suffix) \
                    and pisi.util.is_ar_file(fpath):
                    # if this is an ar file, and this package is not a static package,
                    # don't include this file into the package.
                    continue
                frpath = pisi.util.removepathprefix(install_dir, fpath) # relative path
                ftype, permanent = get_file_type(frpath, package.files, install_dir)
                fsize = pisi.util.dir_size(fpath)
                if not os.path.islink(fpath):
                    st = os.stat(fpath)
                else:
                    st = os.lstat(fpath)
                d[frpath] = pisi.files.FileInfo(path=frpath, type=ftype, permanent=permanent,
                                     size=fsize, hash=fhash, uid=str(st.st_uid), gid=str(st.st_gid),
                                     mode=oct(stat.S_IMODE(st.st_mode)))

        for pinfo in package.files:
            wildcard_path = pisi.util.join_path(install_dir, pinfo.path)
            for path in glob.glob(wildcard_path):
                add_path(path)

        for (p, fileinfo) in d.iteritems():
            files.append(fileinfo)

        files_xml_path = pisi.util.join_path(self.pkg_dir(), ctx.const.files_xml)
        files.write(files_xml_path)
        self.files = files

    def calc_build_no(self, package_name):
        """Calculate build number"""

        def metadata_changed(old_metadata, new_metadata):
            for key in old_metadata.package.__dict__.keys():
                if old_metadata.package.__dict__[key] != new_metadata.package.__dict__[key]:
                    if key != "build":
                        return True

            return False

        # find previous build in packages dir
        found = []
        def locate_old_package(old_package_fn):
            if pisi.util.is_package_name(os.path.basename(old_package_fn), package_name):
                try:
                    old_pkg = pisi.package.Package(old_package_fn, 'r')
                    old_pkg.read(pisi.util.join_path(ctx.config.tmp_dir(), 'oldpkg'))
                    ctx.ui.info(_('(found old version %s)') % old_package_fn)
                    if str(old_pkg.metadata.package.name) != package_name:
                        ctx.ui.warning(_('Skipping %s with wrong pkg name ') %
                                                old_package_fn)
                        return
                    old_build = old_pkg.metadata.package.build
                    found.append( (old_package_fn, old_build) )
                except Error:
                    ctx.ui.warning('Package file %s may be corrupt. Skipping.' % old_package_fn)

        for root, dirs, files in os.walk(ctx.config.compiled_packages_dir()):
            for f in files:
                locate_old_package(pisi.util.join_path(root,f))

        outdir=ctx.get_option('output_dir')
        if not outdir:
            outdir = '.'
        for f in [pisi.util.join_path(outdir,entry) for entry in os.listdir(outdir)]:
            if os.path.isfile(f):
                locate_old_package(f)

        if not found:
            return (1, None)
            ctx.ui.warning(_('(no previous build found, setting build no to 1.)'))
        else:
            a = filter(lambda (x,y): y != None, found)
            ctx.ui.debug(str(a))
            if a:
                # sort in order of increasing build number
                a.sort(lambda x,y : cmp(x[1],y[1]))
                old_package_fn = a[-1][0]   # get the last one
                old_build = a[-1][1]

                # compare old files.xml with the new one..
                old_pkg = pisi.package.Package(old_package_fn, 'r')
                old_pkg.read(pisi.util.join_path(ctx.config.tmp_dir(), 'oldpkg'))

                changed = False
                fnew = self.files.list
                fold = old_pkg.files.list
                fold.sort(lambda x,y : cmp(x.path,y.path))
                fnew.sort(lambda x,y : cmp(x.path,y.path))

                if len(fnew) != len(fold):
                    changed = True
                else:
                    for i in range(len(fold)):
                        fo = fold.pop(0)
                        fn = fnew.pop(0)
                        if fo.path != fn.path:
                            changed = True
                            break
                        else:
                            if fo.hash != fn.hash:
                                changed = True
                                break

                if metadata_changed(old_pkg.metadata, self.metadata):
                    changed = True

                self.old_packages.append(os.path.basename(old_package_fn))
            else: # no old build had a build number
                old_build = None

            ctx.ui.debug('old build number: %s' % old_build)

            # set build number
            if old_build is None:
                ctx.ui.warning(_('(old package lacks a build no, setting build no to 1.)'))
                return (1, None)
            elif changed:
                ctx.ui.info(_('There are changes, incrementing build no to %d') % (old_build + 1))
                return (old_build + 1, old_build)
            else:
                ctx.ui.info(_('There is no change from previous build %d') % old_build)
                return (old_build, old_build)

    def build_packages(self):
        """Build each package defined in PSPEC file. After this process there
        will be .pisi files hanging around, AS INTENDED ;)"""

        self.fetch_component() # bug 856

        # Strip install directory before building .pisi packages.
        self.strip_install_dir()

        if ctx.get_option('create_static'):
            obj = self.generate_static_package_object()
            if obj:
                self.spec.packages.append(obj)

        if ctx.config.values.build.generatedebug:
            obj = self.generate_debug_package_object()
            if obj:
                self.spec.packages.append(obj)

        self.new_packages = []
        self.old_packages = []

        for package in self.spec.packages:

            # removing "farce" in specfile.py:SpecFile.override_tags
            # this block of code came here... SpecFile should never
            # ever ruin the generated PSPEC file. If build process
            # needs this, we should do it in here... (bug: #3773)
            if not package.summary:
                package.summary = self.spec.source.summary
            if not package.description:
                # TODO: remove this if statement with the part in
                # specfile.py:SpecFile
                if not self.spec.source.description:
                    self.spec.dirtyWorkAround()

                package.description = self.spec.source.description
            if not package.partOf:
                package.partOf = self.spec.source.partOf
            if not package.license:
                package.license = self.spec.source.license
            if not package.icon:
                package.icon = self.spec.source.icon



            old_package_name = None
            # store additional files
            c = os.getcwd()
            os.chdir(self.specdir)
            install_dir = self.pkg_dir() + ctx.const.install_dir_suffix
            for afile in package.additionalFiles:
                src = os.path.join(ctx.const.files_dir, afile.filename)
                dest = os.path.join(install_dir + os.path.dirname(afile.target), os.path.basename(afile.target))
                pisi.util.copy_file(src, dest)
                if afile.permission:
                    # mode is octal!
                    os.chmod(dest, int(afile.permission, 8))
                if afile.owner:
                    try:
                        os.chown(dest, pwd.getpwnam(afile.owner)[2], -1)
                    except KeyError:
                        ctx.ui.warning(_("No user named '%s' found on the system") % afile.owner)
                if afile.group:
                    try:
                        os.chown(dest, -1, grp.getgrnam(afile.group)[2])
                    except KeyError:
                        ctx.ui.warning(_("No group named '%s' found on the system") % afile.group)
            os.chdir(c)

            ctx.ui.action(_("** Building package %s") % package.name);

            ctx.ui.info(_("Generating %s,") % ctx.const.files_xml)
            self.gen_files_xml(package)

            ctx.ui.info(_("Generating %s,") % ctx.const.metadata_xml)
            self.gen_metadata_xml(package)

            # build number
            if ctx.config.options.ignore_build_no or not ctx.config.values.build.buildno:
                build_no = old_build_no = None
                ctx.ui.warning(_('Build number is not available. For repo builds you must enable buildno in pisi.conf.'))
            else:
                build_no, old_build_no = self.calc_build_no(package.name)

            self.metadata.package.build = build_no
            self.metadata.write(pisi.util.join_path(self.pkg_dir(), ctx.const.metadata_xml))

            # Calculate new and oldpackage names for buildfarm
            name =  pisi.util.package_name(package.name,
                                     self.spec.getSourceVersion(),
                                     self.spec.getSourceRelease(),
                                     self.metadata.package.build)

            outdir = ctx.get_option('output_dir')
            if outdir:
                name = pisi.util.join_path(outdir, name)
            self.new_packages.append(name)

            ctx.ui.info(_("Creating PiSi package %s.") % name)

            pkg = pisi.package.Package(name, 'w')

            # add comar files to package
            os.chdir(self.specdir)
            for pcomar in package.providesComar:
                fname = pisi.util.join_path(ctx.const.comar_dir,
                                     pcomar.script)
                pkg.add_to_package(fname)

            # add xmls and files
            os.chdir(self.pkg_dir())

            pkg.add_to_package(ctx.const.metadata_xml)
            pkg.add_to_package(ctx.const.files_xml)

            # Now it is time to add files to the packages using newly
            # created files.xml
            files = pisi.files.Files()
            files.read(ctx.const.files_xml)

            if ctx.get_option('package_format') == "1.0":
                for finfo in files.list:
                    orgname = arcname = pisi.util.join_path("install", finfo.path)
                    if package.debug_package:
                        orgname = pisi.util.join_path("debug", finfo.path)
                    pkg.add_to_package(orgname, arcname)
                pkg.close()
            else: # default package format is 1.1, so make it fallback.
                ctx.build_leftover = pisi.util.join_path(self.pkg_dir(), ctx.const.install_tar_lzma)
                tar = archive.ArchiveTar(ctx.const.install_tar_lzma, "tarlzma")
                for finfo in files.list:
                    orgname = arcname = pisi.util.join_path("install", finfo.path)
                    if package.debug_package:
                        orgname = pisi.util.join_path("debug", finfo.path)
                    tar.add_to_archive(orgname, arcname.lstrip("install"))
                tar.close()
                pkg.add_to_package(ctx.const.install_tar_lzma)
                pkg.close()
                os.unlink(ctx.const.install_tar_lzma)
                ctx.build_leftover = None

            os.chdir(c)
            self.set_state("buildpackages")
            ctx.ui.info(_("Done."))

        #show the files those are not collected from the install dir
        if ctx.get_option('debug'):
            abandoned_files = self.get_abandoned_files()
            if abandoned_files:
                ctx.ui.warning(_('Abandoned files under the install dir (%s):') % (install_dir))
                for f in abandoned_files:
                    ctx.ui.info('    - %s' % (f))
            else:
                ctx.ui.warning(_('All of the files under the install dir (%s) has been collected by package(s)')
                                                                % (install_dir))

        if ctx.config.values.general.autoclean is True:
            ctx.ui.info(_("Cleaning Build Directory..."))
            pisi.util.clean_dir(self.pkg_dir())
        else:
            ctx.ui.info(_("Keeping Build Directory"))


        # reset environment variables after build.  this one is for
        # buildfarm actually. buildfarm re-inits pisi for each build
        # and left environment variables go directly into initial dict
        # making actionsapi.variables.exportFlags() useless...
        os.environ = {}
        os.environ = copy.deepcopy(ctx.config.environ)

        return self.new_packages, self.old_packages


# build functions...

def build(pspec):
    if pspec.endswith('.xml'):
        pb = Builder(pspec)
    else:
        pb = Builder.from_name(pspec)
    return pb.build()

order = {"none": 0,
         "fetch": 1,
         "unpack": 2,
         "setupaction": 3,
         "buildaction": 4,
         "installaction": 5,
         "buildpackages": 6}

def __buildState_fetch(pb):
    # fetch is the first state to run.
    pb.patch_exists()
    pb.fetch_source_archive()

def __buildState_unpack(pb, last):
    if order[last] < order["fetch"]:
        __buildState_fetch(pb)
    pb.unpack_source_archive()

def __buildState_setupaction(pb, last):
    if order[last] < order["unpack"]:
        __buildState_unpack(pb, last)
    pb.run_setup_action()

def __buildState_buildaction(pb, last):

    if order[last] < order["setupaction"]:
        __buildState_setupaction(pb, last)
    pb.run_build_action()

def __buildState_checkaction(pb, last):

    if order[last] < order["buildaction"]:
        __buildState_buildaction(pb, last)
    pb.run_check_action()

def __buildState_installaction(pb, last):

    if order[last] < order["buildaction"]:
        __buildState_buildaction(pb, last)
    pb.run_install_action()

def __buildState_buildpackages(pb, last):

    if order[last] < order["installaction"]:
        __buildState_installaction(pb, last)
    pb.build_packages()

def build_until(pspec, state):
    if pspec.endswith('.xml'):
        pb = Builder(pspec)
    else:
        pb = Builder.from_name(pspec)

    pb.compile_action_script()
    pb.compile_comar_script()

    last = pb.get_state()
    ctx.ui.info("Last state was %s"%last)

    if not last: last = "none"

    if state == "fetch":
        __buildState_fetch(pb)
        return

    if state == "unpack":
        __buildState_unpack(pb, last)
        return

    # from now on build dependencies are needed
    pb.check_build_dependencies()

    if state == "setup":
        __buildState_setupaction(pb, last)
        return

    if state == "build":
        __buildState_buildaction(pb, last)
        return

    if state == "check":
        __buildState_checkaction(pb, last)
        return

    if state == "install":
        __buildState_installaction(pb, last)
        return

    __buildState_buildpackages(pb, last)
