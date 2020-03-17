#!/usr/bin/python

import os

from . utils import err, dbg
from . utils.utils import print_stdout, print_stderr, get_symbiotic_dir
from . environment import Environment
from . verifier import initialize_verifier
from . property import get_property

from . exceptions import SymbioticException

def _find_library(lib):
    # code taken and modified from benchexec.util.find_executable
    dirs = os.environ['LD_LIBRARY_PATH'].split(os.path.pathsep)

    for dir_ in dirs:
        name = os.path.join(dir_, lib)
        if os.path.isfile(name):
            return name

    return None

def rm_tmp_dir(d):
    def on_rm_error(func, pth, exc):
        print_stderr('Failed removing tmp dir: {0})'.format(str(exc[1])), color='RED')

    from shutil import rmtree
    rmtree(d, onerror=on_rm_error)

class SetupSymbiotic:
    """
    Setup and check environment for Symbiotic to run
    """

    def __init__(self, opts):
        self.opts = opts
        self._environment = None
        self._working_directory = None

    def _setup_working_directory(self):
        """
        Create temporary directory, either in the current folder or on tmp.
        Return the path to that directory.
        """

        from tempfile import mkdtemp
        from shutil import copy

        if self.opts.save_files:
            tmpdir = 'symbiotic_files'
            try:
                os.mkdir(tmpdir)
            except OSError:
                rm_tmp_dir(tmpdir)
                os.mkdir(tmpdir)
        else:
            if os.path.isdir(self.opts.working_dir_prefix):
                prefix = os.path.join(self.opts.working_dir_prefix, 'symbiotic-')
            else:
                dbg('Found no {0} dir, falling-back to curdir: {1}'.format(self.opts.working_dir_prefix, os.getcwd()))
                prefix = 'symbiotic-'

            tmpdir = mkdtemp(prefix=prefix, dir='.')

        return tmpdir

    def _perform_libraries_check(self):
        libraries = ['LLVMsbt.so', 'libCheckNSWPlugin.so',
                     'libdgPointsToPlugin.so', 'libPredatorPlugin.so',
                     'libdgllvmdg.so', 'libdgllvmpta.so', 'libdgllvmdda.so',
                     'libdgpta.so', 'libdgdda.so', 'libdgllvmcda.so']
        for lib in libraries:
            if not _find_library(lib):
                err("Cannot find library '{0}'".format(lib))

    def _perform_binaries_check(self, additional):
        try:
            from benchexec.util import find_executable
        except ImportError:
            from . benchexec.util import find_executable

        executables = ['clang', 'opt', 'llvm-link', 'llvm-nm',
                       'sbt-instr'] + additional
        for exe in executables:
            exe_path = find_executable(exe)
            if not os.path.isfile(exe_path):
                err("Cannot find executable '{0}' ('{1}')".format(exe, exe_path))
            else:
                dbg("'{0}' is '{1}'".format(os.path.basename(exe), exe_path))

    def _check_components(self, opts, additional_bins = []):
        # check availability of binaries and libraries
        self._perform_binaries_check(additional_bins)
        self._perform_libraries_check()

        # this calls the tools, so it must be after setting the environ
        if not self.opts.no_integrity_check:
            from . integritycheck import IntegrityChecker
            from . options import get_versions

            try:
                _, versions, _, _= get_versions()
                checker = IntegrityChecker(versions)
                checker.check(opts.tool_name);
            except SymbioticException as e:
                err('{0}\nIf you are aware of this, you may use --no-integrity-check '\
                    'to suppress this error'.format(str(e)))

    def setup(self):
        self.environment = Environment(get_symbiotic_dir())
        dbg('Symbiotic dir: {0}'.format(self.environment.symbiotic_dir))

        # setup the property (must be done before initializing the verifier)
        # and then initialize the verifier
        try:
            self.opts.property = get_property(self.environment.symbiotic_dir,
                                              self.opts.propertystr)
            if self.opts.property is None:
                err('Could not derive the right property')

            tool = initialize_verifier(self.opts)
        except SymbioticException as e:
            err(str(e))

        # set environment. That is set PATH and LD_LIBRARY_PATH and so on
        self.environment.set(tool, self.opts)

        check_bins = [self.opts.slicer_cmd[0], tool.executable()]
        if self.opts.generate_c:
            check_bins.append('llvm2c')
            check_bins.append('gen-c')
        self._check_components(self.opts, check_bins)

        # change working directory so that we do not mess up the current directory much
        self.environment.working_dir = os.path.abspath(self._setup_working_directory())
        os.chdir(self.environment.working_dir)
        dbg('Working directory: {0}'.format(self.environment.working_dir))
        assert self.environment.symbiotic_dir != self.environment.working_dir

        return tool, self.environment

    def cleanup(self):
        os.chdir(self.environment.symbiotic_dir)
        assert self.environment.symbiotic_dir != self.environment.working_dir
        if not self.opts.save_files:
            rm_tmp_dir(self.environment.working_dir)

