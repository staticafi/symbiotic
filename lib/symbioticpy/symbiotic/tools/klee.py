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
from os.path import dirname, abspath
from os.path import join as joinpath
from symbiotic.utils.utils import print_stdout

import re

try:
    import benchexec.util as util
    import benchexec.result as result
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result
    from symbiotic.benchexec.tools.template import BaseTool

def dump_error(bindir, ismem=False):
    abd = abspath(bindir)
    if ismem:
        pth = abspath('{0}/klee-last/test000001.ptr.err'.format(abd))
    else:
        pth = abspath('{0}/klee-last/test000001.assert.err'.format(abd))

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
        self._memsafety = 'MEMSAFETY' in self._options.prp
        self._overflow = 'SIGNED-OVERFLOW' in self._options.prp
        self._undefined = 'UNDEF-BEHAVIOR' in self._options.prp
        assert not (self._memsafety and self._overflow)
        assert not (self._memsafety and self._undefined)
        assert not (self._overflow and self._undefined)

        # define and compile regular expressions for parsing klee's output
        self._patterns = [
            ('ASSERTIONFAILED', re.compile('.*klee: .*Assertion .* failed.*')),
            ('VERIFIERERR', re.compile('.*ASSERTION FAIL: verifier assertion failed.*')),
            ('ESTPTIMEOUT', re.compile('.*query timed out (resolve).*')),
            ('EKLEETIMEOUT', re.compile('.*HaltTimer invoked.*')),
            ('EEXTENCALL', re.compile('.*failed external call.*')),
            ('ELOADSYM', re.compile('.*ERROR: unable to load symbol.*')),
            ('EINVALINST', re.compile('.*LLVM ERROR: Code generator does not support.*')),
            ('EINITVALS', re.compile('.*unable to compute initial values.*')),
            ('ESYMSOL', re.compile('.*unable to get symbolic solution.*')),
            ('ESILENTLYCONCRETIZED', re.compile('.*silently concretizing.*')),
            ('EEXTRAARGS', re.compile('.*calling .* with extra arguments.*')),
            #('EABORT' , re.compile('.*abort failure.*')),
            ('EMALLOC', re.compile('.*found huge malloc, returning 0.*')),
            ('ESKIPFORK', re.compile('.*skipping fork.*')),
            ('EKILLSTATE', re.compile('.*killing.*states \(over memory cap\).*')),
            ('EMEMERROR', re.compile('.*memory error: out of bound pointer.*')),
            ('EMAKESYMBOLIC', re.compile(
                '.*memory error: invalid pointer: make_symbolic.*')),
            ('EVECTORUNSUP', re.compile('.*XXX vector instructions unhandled.*')),
            ('EFREE', re.compile('.*memory error: invalid pointer: free.*'))
        ]

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
        return '3.9.1'

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
        if self._undefined:
                opts.append('-fsanitize=undefined')
                opts.append('-fno-sanitize=unsigned-integer-overflow')
        elif self._overflow:
                opts.append('-fsanitize=signed-integer-overflow')
                opts.append('-fsanitize=shift')

        return opts

    def prepare(self):
        """
        Prepare the bitcode for verification - return a list of
        LLVM passes that should be run on the code
        """
        # make all memory symbolic (if desired)
        # and then delete undefined function calls
        # and replace them by symbolic stuff
        passes = \
        ['-rename-verifier-funs',
         '-rename-verifier-funs-source={0}'.format(self._options.sources[0])]

        if self._overflow or self._undefined:
            passes.append('-replace-ubsan')

        if not self._options.explicit_symbolic:
            passes.append('-initialize-uninitialized')

        return passes

    def instrumentation_options(self):
        """
        Returns a triple (c, l, x) where c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        if self._memsafety:
            # default config file is 'config.json'
            return ('config-marker.json', 'marker.c', False)

        return (None, None, None)

    def slicer_options(self):
        """
        Returns tuple (c, opts) where c is the slicing
        criterion and opts is a list of options
        """

        if self._memsafety:
            # default config file is 'config.json'
            # slice with respect to the memory handling operations
            return ('__INSTR_mark_pointer,free', ['-criteria-are-mem-uses'])

        return (self._options.slicing_criterion,[])

    def prepare_after(self):
        """
        Same as prepare, but runs after slicing
        """
        return []

    def describe_error(self, llvmfile):
        dump_error(dirname(llvmfile), self._memsafety)

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        cmd = [executable, '-write-paths',
               '-dump-states-on-halt=0', '-silent-klee-assume=1',
               '-output-stats=0', '-disable-opt', '-only-output-states-covering-new=1',
               '-max-time={0}'.format(self._options.timeout)]

        return cmd + options + tasks

    def preprocess_llvm(self, infile):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        return (None, None)

    def _parse_klee_output_line(self, line):
        for (key, pattern) in self._patterns:
            if pattern.match(line):
                # return True so that we know we should terminate
                if key == 'ASSERTIONFAILED' or key == 'VERIFIERERR':
                    return result.RESULT_FALSE_REACH
                elif key == 'EFREE':
                        return result.RESULT_FALSE_FREE
                elif key == 'EMEMERROR':
                        return result.RESULT_FALSE_DEREF
                elif key == 'EMEMLEAK':
                        return result.RESULT_FALSE_MEMTRACK
                return key

        return None

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return 'timeout'

        if output is None:
            return 'ERROR (no output)'

        found = []
        for line in output:
            fnd = self._parse_klee_output_line(line.decode('ascii'))
            if fnd:
                if fnd.startswith('false'):
                    return fnd
                else:
                    found.append(fnd)

        if not found:
            if returncode != 0:
                return result.RESULT_ERROR
            else:
                # we haven't found anything
                return result.RESULT_TRUE_PROP
        else:
            return result.RESULT_UNKNOWN

        return result.RESULT_ERROR
