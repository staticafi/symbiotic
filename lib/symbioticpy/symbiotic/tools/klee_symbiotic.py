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
import re

try:
    import benchexec.util as util
    import benchexec.result as result
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result

from . kleebase import SymbioticTool as KleeBase
from . kleebase import dump_error
from os.path import dirname

class SymbioticTool(KleeBase):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        KleeBase.__init__(self, opts)

        # define and compile regular expressions for parsing klee's output
        self._patterns = [
            ('EDOUBLEFREE', re.compile('.*ASSERTION FAIL: 0 && "double free".*')),
            ('EINVALFREE', re.compile(
                '.*ASSERTION FAIL: 0 && "free on non-allocated memory".*')),
            ('EMEMLEAK', re.compile('.*ASSERTION FAIL: 0 && "memory leak detected".*')),
            ('ASSERTIONFAILED', re.compile('.*ASSERTION FAIL:.*')),
            ('ESTPTIMEOUT', re.compile('.*query timed out (resolve).*')),
            ('EKLEETIMEOUT', re.compile('.*HaltTimer invoked.*')),
            ('EEXTENCALL', re.compile('.*failed external call.*')),
            ('ELOADSYM', re.compile('.*ERROR: unable to load symbol.*')),
            ('EINVALINST', re.compile('.*LLVM ERROR: Code generator does not support.*')),
            ('EKLEEASSERT', re.compile('.*klee: .*Assertion .* failed.*')),
            ('EINITVALS', re.compile('.*unable to compute initial values.*')),
            ('ESYMSOL', re.compile('.*unable to get symbolic solution.*')),
            ('ESILENTLYCONCRETIZED', re.compile('.*silently concretizing.*')),
            ('EEXTRAARGS', re.compile('.*calling .* with extra arguments.*')),
            #('EABORT' , re.compile('.*abort failure.*')),
            ('EMALLOC', re.compile('.*found huge malloc, returning 0.*')),
            ('ESKIPFORK', re.compile('.*skipping fork.*')),
            ('EKILLSTATE', re.compile('.*killing.*states \(over memory cap\).*')),
            ('EMEMALLOC', re.compile('.*KLEE: WARNING: Allocating memory failed.*')),
            ('EMEMERROR', re.compile('.*memory error: out of bound pointer.*')),
            ('EMAKESYMBOLIC', re.compile(
                '.*memory error: invalid pointer: make_symbolic.*')),
            ('EVECTORUNSUP', re.compile('.*XXX vector instructions unhandled.*')),
            ('EFREE', re.compile('.*memory error: invalid pointer: free.*'))
        ]

        if not self._options.property.memsafety():
            # we do not want this pattern to be found in memsafety benchmarks,
            # because we insert our own check that do not care about what KLEE
            # really allocated underneath
            self._patterns.append(
                ('ECONCRETIZED', re.compile('.* concretized symbolic size.*')))

    def instrumentation_options(self):
        """
        Returns a triple (c, l, x) where c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        if self._options.property.memsafety():
            # default config file is 'config.json'
            return (self._options.memsafety_config_file, 'memsafety.c', True)

        if self._options.property.signedoverflow():
            # default config file is 'config.json'
            return (self._options.overflow_config_file, 'overflows.c', True)

        if self._options.property.termination():
            return ('config.json', 'termination.c', True)

        return (None, None, None)

    def slicer_options(self):
        """
        Returns tuple (c, opts) where c is the slicing
        criterion and opts is a list of options
        """

        return (self._options.slicing_criterion,[])

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        cmd = [executable, '-write-paths',
               '-dump-states-on-halt=0', '-silent-klee-assume=1',
               '-output-stats=0', '-disable-opt', '-only-output-states-covering-new=1',
               '-max-time={0}'.format(self._options.timeout),
               '-external-calls=none']

        if not self._options.dont_exit_on_error:
            cmd.append('-exit-on-error-type=Assert')

        return cmd + options + tasks

    def _parse_klee_output_line(self, line):
        for (key, pattern) in self._patterns:
            if pattern.match(line):
                # return True so that we know we should terminate
                if key == 'ASSERTIONFAILED':
                    if self._options.property.memsafety():
                        return result.RESULT_FALSE_DEREF
                    elif self._options.property.signedoverflow():
                        return result.RESULT_FALSE_OVERFLOW
                    elif self._options.property.termination():
                        return result.RESULT_FALSE_TERMINATION
                    return result.RESULT_FALSE_REACH
                elif self._options.property.memsafety():
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

    def describe_error(self, llvmfile):
        dump_error(dirname(llvmfile))

