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
from os.path import dirname, abspath, isfile, join
from os import listdir
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

def dump_errors(bindir):
    pths = []
    abd = abspath(join(bindir, 'klee-last'))
    for item in listdir(abd):
        if item.endswith('.err'):
            dump_error(abspath(join('klee-last', item)))

def dump_error(pth):
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

    def set_environment(self, env, opts):
        """
        Set environment for the tool
        """
        if opts.devel_mode:
            env.prepend('PATH', '{0}/klee/build-{1}/bin'.\
                        format(env.symbiotic_dir, llvm_version))

        prefix = '{0}/install'.format(env.symbiotic_dir)

        if opts.is32bit:
            env.prepend('KLEE_RUNTIME_LIBRARY_PATH',
                         '{0}/llvm-{1}/lib32/klee/runtime'.\
                         format(prefix, self.llvm_version()))
        else:
            env.prepend('KLEE_RUNTIME_LIBRARY_PATH',
                        '{0}/llvm-{1}/lib/klee/runtime'.\
                        format(prefix, self.llvm_version()))

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
        passes = []
        if not self._options.nowitness:
            passes.append('-make-nondet')
            passes.append('-make-nondet-source={0}'.format(self._options.sources[0]))

        return passes

    def passes_before_verification(self):
        # for once, delete all undefined functions before the verification
        # (we may have new calls of undefined function because of
        # the previous passes
        passes = []

        # make the uninitialized variables symbolic (if desired)
        if not self._options.explicit_symbolic:
            passes.append('-initialize-uninitialized')

        if self._options.undef_retval_nosym:
            passes.append('-delete-undefined-nosym')
        else:
            passes.append('-delete-undefined')

        # make external globals non-deterministic
        passes.append('-internalize-globals')

        return passes

    def describe_error(self, llvmfile):
        dump_errors(dirname(llvmfile))

