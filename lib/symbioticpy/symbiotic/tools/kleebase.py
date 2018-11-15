"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from os.path import dirname, abspath, isfile
from symbiotic.utils.utils import print_stdout

try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='4.0.1'

try:
    import benchexec.util as util
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    from symbiotic.benchexec.tools.template import BaseTool

def dump_error(bindir, ismem=False):
    abd = abspath(bindir)
    if ismem:
        pth = abspath('{0}/klee-last/test000001.ptr.err'.format(abd))
        if not isfile(pth):
            pth = abspath('{0}/klee-last/test000001.leak.err'.format(abd))
    else:
        pth = abspath('{0}/klee-last/test000001.assert.err'.format(abd))

    if not isfile(pth):
        from symbiotic.utils import dbg
        dbg("Couldn't find the file with error description")
        return

    try:
        f = open(pth, 'r')
        print('\n --- Error trace ---\n')
        for line in f:
            print_stdout(line, print_nl = False)
        print('\n --- ----------- ---')
    except OSError:
        from symbiotic.utils import dbg
        # this dumping is just for convenience,
        # so do not return any error
        dbg('Failed dumping the error')


# we use are own fork of KLEE, so do not use the official
# benchexec module for klee (FIXME: update the module so that
# we can use it)
class SymbioticTool(BaseTool):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        self._options = opts

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable('klee')

    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        """
        return self._version_from_tool(executable, arg='-version')

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'klee'

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        return llvm_version

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """

        from os import environ

        # XXX: maybe there is a nicer solution?
        if opts.devel_mode:
            symbiotic_dir += '/install'

        if opts.is32bit:
            environ['KLEE_RUNTIME_LIBRARY_PATH'] \
                = '{0}/llvm-{1}/lib32/klee/runtime'.format(symbiotic_dir, self.llvm_version())
        else:
            environ['KLEE_RUNTIME_LIBRARY_PATH'] \
                = '{0}/llvm-{1}/lib/klee/runtime'.format(symbiotic_dir, self.llvm_version())

    def compilation_options(self):
        """
        List of compilation options specific for this tool
        """
        opts = []
        if self._options.property.undefinedness():
                opts.append('-fsanitize=undefined')
                opts.append('-fno-sanitize=unsigned-integer-overflow')
        elif self._options.property.signedoverflow():
                opts.append('-fsanitize=signed-integer-overflow')
                opts.append('-fsanitize=shift')

        return opts

    def passes_after_compilation(self):
        """
        Prepare the bitcode for verification - return a list of
        LLVM passes that should be run on the code
        """
        # remove definitions of __VERIFIER_* that are not created by us,
        # make extern globals local, etc. Also remove syntactically infinite loops.
        passes =  ['-remove-infinite-loops']
        if not self._options.nowitness:
            passes.append('-rename-verifier-funs')
            passes.append('-rename-verifier-funs-source={0}'.format(self._options.sources[0]))

        if not self._options.noprepare:
            passes.append('-prepare')

        if self._options.property.undefinedness() or \
           self._options.property.signedoverflow():
            passes.append('-replace-ubsan')

        if self._options.property.signedoverflow() and \
           not self._options.overflow_with_clang:
            passes.append('-prepare-overflows')

        # make all memory symbolic (if desired)
        if not self._options.explicit_symbolic:
            passes.append('-initialize-uninitialized')

        return passes

    def passes_after_slicing(self):
        """
        Prepare the bitcode for verification after slicing:
        \return a list of LLVM passes that should be run on the code
        """
        # instrument our malloc -- either the version that can fail,
        # or the version that can not fail.
        passes = []
        if self._options.malloc_never_fails:
            passes += ['-instrument-alloc-nf']
        else:
            passes += ['-instrument-alloc']

        # remove/replace the rest of undefined functions
        # for which we do not have a definition and
        # that has not been removed
        if self._options.undef_retval_nosym:
            passes += ['-delete-undefined-nosym']
        else:
            passes += ['-delete-undefined']

        # for the memsafety property, make functions behave like they have
        # side-effects, because LLVM optimizations could remove them otherwise,
        # even though they contain calls to assert
        if self._options.property.memsafety():
            passes.append('-remove-readonly-attr')

        return passes

    def describe_error(self, llvmfile):
        dump_error(dirname(llvmfile), self._options.property.memsafety())

