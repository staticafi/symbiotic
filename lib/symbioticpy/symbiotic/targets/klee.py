"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2016-2019  Marek Chalupa
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

class KleeToolFullInstrumentation(KleeBase):
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
            ('EEXTENCALL', re.compile('.*failed external call*')),
            ('ELOADSYM', re.compile('.*ERROR: unable to load symbol.*')),
            ('EINVALINST', re.compile('.*LLVM ERROR: Code generator does not support.*')),
            ('EKLEEASSERT', re.compile('.*klee: .*Assertion .* failed.*')),
            ('EINITVALS', re.compile('.*unable to compute initial values.*')),
            ('ESYMSOL', re.compile('.*unable to get symbolic solution.*')),
            ('ESILENTLYCONCRETIZED', re.compile('.*silently concretizing.*')),
            ('EEXTRAARGS', re.compile('.*calling .* with extra arguments.*')),
            ('EPTRCMP', re.compile('.*WARNING.*: comparison of two pointers.*')),
            ('EMALLOC', re.compile('.*found huge malloc, returning 0.*')),
            ('ESKIPFORK', re.compile('.*skipping fork.*')),
            ('EKILLSTATE', re.compile('.*killing.*states \(over memory cap\).*')),
            ('EMEMALLOC', re.compile('.*KLEE: WARNING: Allocating memory failed.*')),
            ('EROSYMB', re.compile('.*cannot make readonly object symbolic.*')),
            ('ESTACKOVFLW', re.compile('.*WARNING: Maximum stack size reached.*')),
            ('EMEMERROR', re.compile('.*memory error: out of bound pointer.*')),
            ('EMAKESYMBOLIC', re.compile(
                '.*memory error: invalid pointer: make_symbolic.*')),
            ('EVECTORUNSUP', re.compile('.*XXX vector instructions unhandled.*')),
            ('EFREE', re.compile('.*memory error: invalid pointer: free.*')),
            ('ERESOLV', re.compile('.*ERROR:.*Could not resolve.*'))
        ]

    def passes_after_slicing(self):
        """
        Prepare the bitcode for verification after slicing:
        \return a list of LLVM passes that should be run on the code
        """
        # instrument our malloc -- either the version that can fail,
        # or the version that can not fail.
        passes = []
        if self._options.malloc_never_fails:
            passes.append('-instrument-alloc-nf')
        else:
            passes.append('-instrument-alloc')

        # remove/replace the rest of undefined functions
        # for which we do not have a definition and
        # that has not been removed
        #if self._options.undef_retval_nosym:
        #    passes.append('-delete-undefined-nosym')
        #else:
        #    passes.append('-delete-undefined')

        # for the memsafety property, make functions behave like they have
        # side-effects, because LLVM optimizations could remove them otherwise,
        # even though they contain calls to assert
        if self._options.property.memsafety():
            passes.append('-remove-readonly-attr')

        return passes

    def actions_after_compilation(self, symbiotic):
        # we want to link memsafety functions before instrumentation,
        # because we need to check for invalid dereferences in them
        if symbiotic.options.property.memsafety():
            symbiotic.link_undefined()

        if symbiotic.options.property.signedoverflow() and \
           not symbiotic.options.overflow_with_clang:
            symbiotic.link_undefined()

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """
        cmd = [executable, '--max-memory=8000',
               '-dump-states-on-halt=0', '-silent-klee-assume=1',
               '-output-stats=0', '--optimize=false', '-only-output-states-covering-new=1',
               '-max-time={0}'.format(self._options.timeout),
               '-external-calls=pure']

        if not self._options.dont_exit_on_error:
            cmd.append('-exit-on-error-type=Assert')

        return cmd + options + tasks

    def _parse_klee_output_line(self, line):
        for (key, pattern) in self._patterns:
            if pattern.match(line):
                if key == 'ASSERTIONFAILED':
                    if self._options.property.memsafety():
                        return result.RESULT_FALSE_DEREF
                    elif self._options.property.signedoverflow():
                        return result.RESULT_FALSE_OVERFLOW
                    elif self._options.property.termination():
                        return result.RESULT_FALSE_TERMINATION
                    elif self._options.property.memcleanup():
                        return result.RESULT_FALSE_MEMCLEANUP
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
                found.append(fnd)

        if not found:
            if returncode != 0:
                return result.RESULT_ERROR
            else:
                # we haven't found anything
                return result.RESULT_TRUE_PROP
        elif len(found) == 1:
            return found[0]
        else:
            if 'EINITVALS' not in found:
                for f in found:
                    if f.startswith('false'):
                        return f

            return "{0}({1})".format(result.RESULT_UNKNOWN, " ".join(found))

        return result.RESULT_ERROR


class SymbioticTool(KleeBase):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        KleeBase.__init__(self, opts)
        self.FullInstr = None

        if opts.full_instrumentation:
            self.FullInstr = KleeToolFullInstrumentation(opts)

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
            ('EPTRCMP', re.compile('.*WARNING.*: comparison of two pointers.*')),
            ('EMALLOC', re.compile('.*found huge malloc, returning 0.*')),
            ('ESKIPFORK', re.compile('.*skipping fork.*')),
            ('EKILLSTATE', re.compile('.*killing.*states \(over memory cap\).*')),
            ('EMEMERROR', re.compile('.*memory error: out of bound pointer.*')),
            ('EMAKESYMBOLIC', re.compile(
                '.*memory error: invalid pointer: make_symbolic.*')),
            ('EVECTORUNSUP', re.compile('.*XXX vector instructions unhandled.*')),
            ('EFREE', re.compile('.*memory error: invalid pointer: free.*')),
            ('EMEMALLOC', re.compile('.*KLEE: WARNING: Allocating memory failed.*')),
            ('ESTACKOVFLW', re.compile('.*WARNING: Maximum stack size reached.*')),
            ('EROSYMB', re.compile('.*cannot make readonly object symbolic.*')),
            ('EMEMLEAK', re.compile('.*memory error: memory leak detected.*')),
            ('EMEMCLEANUP', re.compile('.*memory error: memory not cleaned up.*')),
            ('EFREEALLOCA', re.compile('.*ERROR:.*free of alloca.*')),
            ('ERESOLVMEMCLN', re.compile('.*Failed resolving segment in memcleanup check.*')),
            ('ERESOLVMEMCLN2', re.compile('.*Cannot resolve non-constant segment in memcleanup check.*')),
            ('ERESOLV', re.compile('.*ERROR:.*Could not resolve.*'))
        ]

    def passes_after_slicing(self):
        if self.FullInstr:
            return self.FullInstr.passes_after_slicing()

        return []

    def actions_after_compilation(self, symbiotic):
        if self.FullInstr:
            return self.FullInstr.actions_after_compilation(symbiotic)

    def _testcomp_cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute for TEST-COMP
        """

        cmd = [executable, '--optimize=false',
               '-use-forked-solver=0',
               '--use-call-paths=0', '--output-stats=0',
               '-istats-write-interval=60s',
               #'--output-istats=0',
               '-output-dir={0}'.format(self._options.testsuite_output),
               '-write-testcases',
               '-max-memory=8000']

        if self._options.property.errorcall():
            cmd.append('-exit-on-error-type=Assert')
            cmd.append('-dump-states-on-halt=0')
        else:
            cmd.append('-only-output-states-covering-new=1')
            cmd.append('-write-ktests=false')
            cmd.append('-max-time=840')

        if not self._options.nowitness:
            cmd.append('-write-witness')

        if self._options.executable_witness:
            cmd.append('-write-harness')

        cmd.append('-output-source=false')

        return cmd + options + tasks

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        if self._options.test_comp:
            return self._testcomp_cmdline(executable, options, tasks, propertyfile, rlimits)

        elif self.FullInstr:
            return self.FullInstr.cmdline(executable, options, tasks, propertyfile, rlimits)

        cmd = [executable,
               '-dump-states-on-halt=0',
               '--output-stats=0', '--use-call-paths=0',
               '--optimize=false', '-silent-klee-assume=1',
               '-istats-write-interval=60s',
               #'--output-istats=0',
               '-only-output-states-covering-new=1',
               '-use-forked-solver=0',
               '-max-time={0}'.format(self._options.timeout),
               '-external-calls=pure', '-max-memory=8000']
        if self._options.property.memsafety():
            cmd.append('-check-leaks')
        elif self._options.property.memcleanup():
            cmd.append('-check-memcleanup')

        if not self._options.dont_exit_on_error:
            if self._options.property.memsafety():
                cmd.append('-exit-on-error-type=Ptr')
                cmd.append('-exit-on-error-type=Leak')
                cmd.append('-exit-on-error-type=ReadOnly')
                cmd.append('-exit-on-error-type=Free')
                cmd.append('-exit-on-error-type=BadVectorAccess')
            elif self._options.property.memcleanup():
                cmd.append('-exit-on-error-type=Leak')
            else:
                cmd.append('-exit-on-error-type=Assert')

        if not self._options.nowitness:
            cmd.append('-write-witness')

        if self._options.executable_witness:
            cmd.append('-write-harness')

        # we have the disassembly already (it may be a bit different,
        # but we may remove this switch during debugging)
        cmd.append('-output-source=false')

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
                    return result.RESULT_FALSE_MEMTRACK
                elif key == 'EMEMCLEANUP':
                    return result.RESULT_FALSE_MEMCLEANUP

                return key

        return None

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        ##
        # TEST-COMP
        # #
        if self._options.test_comp:
            if self._options.property.errorcall():
                found = []
                for line in output:
                    fnd = self._parse_klee_output_line(line.decode('ascii'))
                    if fnd == result.RESULT_FALSE_REACH:
                        return result.RESULT_DONE

                return result.RESULT_UNKNOWN

            # else its coverage
            return result.RESULT_DONE

        ##
        # GENERIC
        # #
        if self.FullInstr:
            return self.FullInstr.determine_result(returncode, returnsignal, output, isTimeout)

        if isTimeout:
            return 'timeout'

        if output is None:
            return 'ERROR (no output)'

        found = []
        for line in output:
            fnd = self._parse_klee_output_line(str(line))
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

            return "{0} ({1})".format(result.RESULT_UNKNOWN, " ".join(found))

        return result.RESULT_ERROR

