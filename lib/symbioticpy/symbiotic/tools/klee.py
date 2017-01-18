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
from os.path import dirname
from os.path import join as joinpath

import re

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        self._options = opts
        self._memsafety = 'VALID-DEREF' in self._options.prp or \
	                  'VALID-FREE' in self._options.prp or \
	                  'VALID-MEMTRACK' in self._options.prp or \
	                  'MEMSAFETY' in self._options.prp
        self._overflow = 'SIGNED-OVERFLOW' in self._options.prp
        assert not (self._memsafety and self._overflow)

        # define and compile regular expressions for parsing klee's output
        self._patterns = [
           ('EDOUBLEFREE' , re.compile('.*ASSERTION FAIL: 0 && "double free".*')),
           ('EINVALFREE' , re.compile('.*ASSERTION FAIL: 0 && "free on non-allocated memory".*')),
           ('EMEMLEAK' , re.compile('.*ASSERTION FAIL: 0 && "memory leak detected".*')),
           ('ASSERTIONFAILED' , re.compile('.*ASSERTION FAIL:.*')),
           ('ESTPTIMEOUT' , re.compile('.*query timed out (resolve).*')),
           ('EKLEETIMEOUT' , re.compile('.*HaltTimer invoked.*')),
           ('EEXTENCALL' , re.compile('.*failed external call.*')),
           ('ELOADSYM' , re.compile('.*ERROR: unable to load symbol.*')),
           ('EINVALINST' , re.compile('.*LLVM ERROR: Code generator does not support.*')),
           ('EKLEEASSERT' , re.compile('.*klee: .*Assertion .* failed.*')),
           ('EINITVALS' , re.compile('.*unable to compute initial values.*')),
           ('ESYMSOL' , re.compile('.*unable to get symbolic solution.*')),
           ('ESILENTLYCONCRETIZED' , re.compile('.*silently concretizing.*')),
           ('EEXTRAARGS' , re.compile('.*calling .* with extra arguments.*')),
           ('EABORT' , re.compile('.*abort failure.*')),
           ('EMALLOC' , re.compile('.*found huge malloc, returning 0.*')),
           ('ESKIPFORK' , re.compile('.*skipping fork.*')),
           ('EKILLSTATE' , re.compile('.*killing.*states \(over memory cap\).*')),
           ('EMEMERROR'  , re.compile('.*memory error: out of bound pointer.*')),
           ('EMAKESYMBOLIC' , re.compile('.*memory error: invalid pointer: make_symbolic.*')),
           ('EVECTORUNSUP' , re.compile('.*XXX vector instructions unhandled.*')),
           ('EFREE' , re.compile('.*memory error: invalid pointer: free.*'))
        ]

        if not self._memsafety:
            # we do not want this pattern to be found in memsafety benchmarks,
            # because we insert our own check that do not care about what KLEE
            # really allocated underneath
            self._patterns.append(('ECONCRETIZED', re.compile('.* concretized symbolic size.*')))

    REQUIRED_PATHS = [
                  "bin",
                  "include",
                  "share",
                  "instrumentations",
                  "lib",
                  "lib32",
                  "symbiotic"
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
        return '3.8.1'

    def preprocess_llvm(self, infile):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        return (None, None)

    def prepare(self):
        """
        Prepare the bitcode for verification - return a list of
        LLVM passes that should be run on the code
        """
        return []

    def prepare_after(self):
        """
        Same as prepare, but runs after slicing
        """
        self._options.linkundef.append('verifier')

        # instrument our malloc -- either the version that can fail,
        # or the version that can not fail.
        if self._options.malloc_never_fails:
            passes = ['-instrument-alloc-nf']
        else:
            passes = ['-instrument-alloc']

        # make all memory symbolic (if desired)
        # and then delete undefined function calls
        # and replace them by symbolic stuff
        if not self._options.explicit_symbolic:
            passes.append('-initialize-uninitialized')

        # remove/replace the rest of undefined functions
        # for which we do not have a definition and
	# that has not been removed
        if self._options.undef_retval_nosym:
            passes += ['-delete-undefined-nosym']
        else:
            passes += ['-delete-undefined']

        return passes

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        cmd = [executable, '-write-paths',
               '-dump-states-on-halt=0', '-silent-klee-assume=1',
               '-output-stats=0', '-disable-opt', '-only-output-states-covering-new=1',
               '-max-time={0}'.format(self._options.timeout)]

        if not self._options.dont_exit_on_error:
            cmd.append('-exit-on-error-type=Assert')

        return cmd + options + tasks

    def _parse_klee_output_line(self, line):
        for (key, pattern) in self._patterns:
            if pattern.match(line):
                # return True so that we know we should terminate
                if key == 'ASSERTIONFAILED':
                    if self._memsafety:
                        return result.RESULT_FALSE_DEREF
                    elif self._overflow:
                        return result.RESULT_FALSE_OVERFLOW
                    return result.RESULT_FALSE_REACH
                elif self._memsafety:
                    if key == 'EDOUBLEFREE' or key == 'EINVALFREE':
                        return result.RESULT_FALSE_FREE
                    if key == 'EMEMLEAK':
                        return result.RESULT_FALSE_MEMTRACK
                return key

        return None

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return 'timeout'

        if output is None:
            return 'error (no output)'

        found = []
        for line in output:
            fnd = self._parse_klee_output_line(line)
            if fnd:
                if fnd.startswith('false'):
                    return fnd
                else:
                    found += fnd

        if not fnd:
            if returncode != 0:
                return result.RESULT_ERROR

            # we haven't found anything
            if not found:
                return result.RESULT_TRUE_PROP

        return result.RESULT_ERROR
