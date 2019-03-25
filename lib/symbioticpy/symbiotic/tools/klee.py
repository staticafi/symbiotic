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

class SymbioticTool(KleeBase):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        KleeBase.__init__(self, opts)

        # define and compile regular expressions for parsing klee's output
        self._patterns = [
            ('ASSERTIONFAILED', re.compile('.*ASSERTION FAIL:.*')),
            ('ASSERTIONFAILED2', re.compile('.Assertion .* failed.*')),
            ('ESTPTIMEOUT', re.compile('.*query timed out (resolve).*')),
            ('EKLEETIMEOUT', re.compile('.*HaltTimer invoked.*')),
            ('EEXTENCALL', re.compile('.*failed external call.*')),
            ('EEXTENCALLDIS', re.compile('.*external calls disallowed.*')),
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
            ('EFREE', re.compile('.*memory error: invalid pointer: free.*')),
            ('EMEMALLOC', re.compile('.*KLEE: WARNING: Allocating memory failed.*')),
            ('EMEMLEAK', re.compile('.*memory error: memory leak detected.*')),
            ('EFREEALLOCA', re.compile('.*ERROR:.*free of alloca.*')),
            ('ERESOLV', re.compile('.*ERROR:.*Could not resolve.*'))
        ]

    def instrumentation_options(self):
        """
        Returns a triple (c, l, x) where c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        # NOTE: we do not want to link the functions with memsafety/cleanup
        # because then the optimizations could remove the calls to markers
        if self._options.property.memsafety():
            return ('config-marker.json', 'marker.c', False)

        if self._options.property.memcleanup():
            return ('config-marker-memcleanup.json', 'marker.c', False)

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

        if self._options.property.memsafety():
            # default config file is 'config.json'
            # slice with respect to the memory handling operations
            return ('__INSTR_mark_pointer,__INSTR_mark_free,__INSTR_mark_allocation',
                    ['-criteria-are-next-instr'])

        elif self._options.property.memcleanup():
            # default config file is 'config.json'
            # slice with respect to the memory handling operations
            return ('__INSTR_mark_free,__INSTR_mark_allocation',
                    ['-criteria-are-next-instr'])

        return (self._options.slicing_criterion,[])

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        cmd = [executable, '-write-paths',
               '-dump-states-on-halt=0', '-silent-klee-assume=1',
               '-output-stats=0', '--optimize=false', '-only-output-states-covering-new=1',
               '-max-time={0}'.format(self._options.timeout),
               '-external-calls=none']
        if self._options.property.memsafety():
            cmd.append('-check-leaks')
            cmd.append('-exit-on-error-type=Ptr')
            cmd.append('-exit-on-error-type=Leak')
            cmd.append('-exit-on-error-type=ReadOnly')
            cmd.append('-exit-on-error-type=Free')
            cmd.append('-exit-on-error-type=BadVectorAccess')
        elif self._options.property.memcleanup():
            cmd.append('-check-leaks')
            cmd.append('-exit-on-error-type=Leak')
        else:
            cmd.append('-exit-on-error-type=Assert')

        return cmd + options + tasks

    def _parse_klee_output_line(self, line):
        for (key, pattern) in self._patterns:
            if pattern.match(line):
                # return True so that we know we should terminate
                if key.startswith('ASSERTIONFAILED'):
                    if self._options.property.signedoverflow():
                        return result.RESULT_FALSE_OVERFLOW
                    elif self._options.property.termination():
                        return result.RESULT_FALSE_TERMINATION
                    else:
                        return result.RESULT_FALSE_REACH
                elif key == 'EFREE' or key == 'EFREEALLOCA':
                        return result.RESULT_FALSE_FREE
                elif key == 'EMEMERROR':
                        return result.RESULT_FALSE_DEREF
                elif key == 'EMEMLEAK':
                    if self._options.property.memcleanup():
                        return result.RESULT_FALSE_MEMCLEANUP
                    else:
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
                found.append(fnd)

        if not found:
            if returncode != 0:
                return result.RESULT_ERROR
            else:
                # we haven't found anything
                return result.RESULT_TRUE_PROP
        else:
            if 'EINITVALS' in found: # EINITVALS would break the validity of the found error
                return "{0}({1})".format(result.RESULT_UNKNOWN, " ".join(found))

            for f in found:
                # we found error that we sought for?
                if f == result.RESULT_FALSE_REACH and self._options.property.assertions():
                    return f
                elif f == result.RESULT_FALSE_OVERFLOW and self._options.property.signedoverflow():
                    return f
                elif f in [result.RESULT_FALSE_FREE, result.RESULT_FALSE_DEREF, result.RESULT_FALSE_MEMTRACK]\
                    and self._options.property.memsafety():
                    return f
                elif f == result.RESULT_FALSE_MEMCLEANUP and self._options.property.memcleanup():
                    return f
                elif f == result.RESULT_FALSE_TERMINATION and self._options.property.termination():
                    return f

            return "{0}({1})".format(result.RESULT_UNKNOWN, " ".join(found))

        return result.RESULT_ERROR
