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
            ('EMEMERROR', re.compile('.*memory error: calling nullptr.*')),
            ('EPTHREAD', re.compile('.*ERROR:.*Call to pthread_.*')),
            ('EPTHREAD2', re.compile('.*ERROR:.*unsupported pthread API.*')),
            ('EFUNMODEL', re.compile('.*: unsupported function model.*')),
            ('EMAKESYMBOLIC', re.compile(
                '.*memory error: invalid pointer: make_symbolic.*')),
            ('EVECTORUNSUP', re.compile('.*XXX vector instructions unhandled.*')),
            ('EFREE', re.compile('.*memory error: invalid pointer: free.*')),
            ('EASM', re.compile('.*ERROR:.*inline assembly is unsupported.*')),
            ('EGLOBLFREE', re.compile('.*ERROR:.*free of global.*')),
            ('EUNREACH', re.compile('.*reached "unreachable" instruction.*')),
            ('ECMP', re.compile('.*Comparison other than (in)equality is not implemented.*')),
            ('ERESOLV', re.compile('.*Failed resolving.*segment.*')),
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
        if not self._options.malloc_never_fails:
       #    passes.append('-instrument-alloc-nf')
       #else:
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

        return passes + super().passes_after_slicing()

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
        opts = self._options

        cmd = [executable] + self._arguments

        if not opts.nowitness:
            cmd.append('-write-witness')

        if opts.executable_witness:
            cmd.append('-write-harness')

        return cmd + options + tasks + opts.argv

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
        for line in map(str, output):
            fnd = self._parse_klee_output_line(line)
            if fnd:
                found.append(fnd)

        if not found:
            if returncode != 0:
                return f'{result.RESULT_ERROR} (KLEE exited with {returncode})'
            # we haven't found anything
            return result.RESULT_TRUE_PROP

        if len(found) == 1:
            return found[0]

        if 'EINITVALS' not in found:
            for f in found:
                if f.startswith('false'):
                    return f

        return "{0}({1})".format(result.RESULT_UNKNOWN, " ".join(found))


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
            ('EPTHREAD', re.compile('.*ERROR:.*Call to pthread_.*')),
            ('EPTHREAD2', re.compile('.*ERROR:.*unsupported pthread API.*')),
            ('EMEMERROR', re.compile('.*memory error: out of bound pointer.*')),
            ('EMEMERROR', re.compile('.*memory error: calling nullptr.*')),
            ('EMAKESYMBOLIC', re.compile(
                '.*memory error: invalid pointer: make_symbolic.*')),
            ('EVECTORUNSUP', re.compile('.*XXX vector instructions unhandled.*')),
            ('EFREE', re.compile('.*memory error: invalid pointer: free.*')),
            ('EASM', re.compile('.*ERROR:.*inline assembly is unsupported.*')),
            ('EGLOBLFREE', re.compile('.*ERROR:.*free of global.*')),
            ('EMEMALLOC', re.compile('.*KLEE: WARNING: Allocating memory failed.*')),
            ('ESTACKOVFLW', re.compile('.*WARNING: Maximum stack size reached.*')),
            ('EROSYMB', re.compile('.*cannot make readonly object symbolic.*')),
            ('EFUNMODEL', re.compile('.*: unsupported function model.*')),
            ('EMEMLEAK', re.compile('.*memory error: memory leak detected.*')),
            ('EMEMCLEANUP', re.compile('.*memory error: memory not cleaned up.*')),
            ('EFREEALLOCA', re.compile('.*ERROR:.*free of alloca.*')),
            ('EINVREALLOC', re.compile('.*memory error:.*invalid pointer:.*realloc.*')),
            ('EROREALLOC', re.compile('.*memory error:.*realloc of read-only object.*')),
            ('EROREALLOC', re.compile('.*memory error:.*realloc on local object.*')),
            ('EROREALLOC', re.compile('.*memory error:.*realloc on global object.*')),
            ('ERESOLVMEMCLN', re.compile('.*Failed resolving segment in memcleanup check.*')),
            ('ERESOLVMEMCLN2', re.compile('.*Cannot resolve non-constant segment in memcleanup check.*')),
            ('ECMP', re.compile('.*Comparison other than (in)equality is not implemented.*')),
            ('ERESOLV', re.compile('.*Failed resolving.*segment.*')),
            ('EUNREACH', re.compile('.*reached "unreachable" instruction.*')),
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

        opts = self._options

       #cmd = [executable,
       #       '-use-forked-solver=0',
       #       '--use-call-paths=0', '--output-stats=0',
       #       '-istats-write-interval=60s',
       #       '-timer-interval=10',
       #       '-external-calls=pure',
       #       #'--output-istats=0',
       #       '-output-dir={0}'.format(opts.testsuite_output),
       #       '-write-testcases',
       #       '-malloc-symbolic-contents',
       #       '-max-memory=8000']

        cmd = [executable] + self._arguments +\
              ['-output-dir={0}'.format(opts.testsuite_output),
               '-write-testcases',
               '-malloc-symbolic-contents']

        if opts.property.errorcall():
            cmd.append('-exit-on-error')
            cmd.append('-dump-states-on-halt=0')
        else:
            cmd.append('-only-output-states-covering-new=1')
            # XXX: investigate: for some reason, this changes the number of searched paths
            #cmd.append('-write-ktests=false')
            cmd.append('-max-time=840')

        if not opts.nowitness:
            cmd.append('-write-witness')

        if opts.executable_witness:
            cmd.append('-write-harness')

        cmd.append('-output-source=false')

        return cmd + options + tasks

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        opts = self._options
        prop = opts.property

        if opts.test_comp:
            return self._testcomp_cmdline(executable, options, tasks, propertyfile, rlimits)

        elif self.FullInstr:
            return self.FullInstr.cmdline(executable, options, tasks, propertyfile, rlimits)

        cmd = [executable] + self._arguments

        if prop.memsafety():
            cmd.append('-check-leaks')
           #if opts.sv_comp:
           #    cmd.append('-check-leaks')
           #else: # if not in SV-COMP, consider any unfreed memory as a leak
           #    cmd.append('-check-memcleanup')
        elif prop.memcleanup():
            cmd.append('-check-memcleanup')
        elif prop.unreachcall():
            # filter out the non-standard error calls,
            # because we support only one such call atm.
            calls = [x for x in prop.getcalls() if x not in ['__VERIFIER_error', '__assert_fail']]
            if calls:
                assert len(calls) == 1, "Multiple error functions unsupported yet"
                cmd.append('-error-fn={0}'.format(calls[0]))
            # FIXME: append to all properties?
            cmd.append('-malloc-symbolic-contents')
        elif prop.signedoverflow():
            # we instrument with __VERIFIER_error
            cmd.append('-error-fn=__VERIFIER_error')

        if not opts.nowitness:
            cmd.append('-write-witness')

        if opts.executable_witness:
            cmd.append('-write-harness')

        # we have the disassembly already (it may be a bit different,
        # but we may remove this switch during debugging)
        cmd.append('-output-source=false')

        return cmd + options + tasks + self._options.argv

    def _parse_klee_output_line(self, line):
        opts = self._options

        for (key, pattern) in self._patterns:
            if pattern.match(line):
                # return True so that we know we should terminate
                if key.startswith('ASSERTIONFAILED'):
                    if opts.property.signedoverflow():
                        return result.RESULT_FALSE_OVERFLOW
                    elif opts.property.termination():
                        return result.RESULT_FALSE_TERMINATION
                    else:
                        return result.RESULT_FALSE_REACH
                elif key == 'EFREE' or key == 'EFREEALLOCA' or key=='EGLOBLFREE':
                    return result.RESULT_FALSE_FREE
                elif key in ('EMEMERROR', 'EINVREALLOC', 'EROREALLOC'):
                    return result.RESULT_FALSE_DEREF
                elif key == 'EMEMLEAK':
                    return result.RESULT_FALSE_MEMTRACK
                elif key == 'EMEMCLEANUP':
                    return result.RESULT_FALSE_MEMCLEANUP

                return key

        return None

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        opts = self._options
        prop = opts.property

        ##
        # TEST-COMP
        # #
        if opts.test_comp:
            if prop.errorcall():
                found = []
                for line in output:
                    fnd = self._parse_klee_output_line(str(line))
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
                return f'{result.RESULT_ERROR} (KLEE exited with {returncode})'
            # we haven't found anything
            return result.RESULT_TRUE_PROP

        if 'EINITVALS' in found: # EINITVALS would break the validity of the found error
            return "{0}({1})".format(result.RESULT_UNKNOWN, " ".join(found))

        FALSE_REACH = result.RESULT_FALSE_REACH
        FALSE_OVERFLOW = result.RESULT_FALSE_OVERFLOW
        FALSE_FREE = result.RESULT_FALSE_FREE
        FALSE_DEREF = result.RESULT_FALSE_DEREF
        FALSE_MEMTRACK = result.RESULT_FALSE_MEMTRACK
        FALSE_MEMCLEANUP = result.RESULT_FALSE_MEMCLEANUP
        FALSE_TERMINATION = result.RESULT_FALSE_TERMINATION
        FALSE_UNDEF = 'false(def-behavior)'

        for f in found:
            # we found error that we sought for?
            if f == FALSE_REACH and prop.unreachcall():
                return f
            elif f == FALSE_REACH and prop.undefinedness():
                return FALSE_UNDEF
            elif f == FALSE_OVERFLOW and prop.signedoverflow():
                return f
            elif f in (FALSE_FREE, FALSE_DEREF, FALSE_MEMTRACK)\
                and prop.memsafety():
                return f
            elif f == FALSE_MEMCLEANUP and\
                (prop.memcleanup() or prop.memsafety() and not opts.sv_comp):
                return f
            elif f == FALSE_TERMINATION and prop.termination():
                return f
            elif f == FALSE_DEREF and prop.nullderef():
                return f

        return "{0} ({1})".format(result.RESULT_UNKNOWN, " ".join(found))
