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

from symbiotic.exceptions import SymbioticException
from . kleebase import SymbioticTool as KleeBase

class SymbioticTool(KleeBase):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        KleeBase.__init__(self, opts)

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable('witch-klee')

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'witch-klee'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        opts = self._options
        prop = opts.property

        cmd = [executable] + self._arguments

        if opts.timeout is not None:
               cmd.append('-max-time={0}'.format(opts.timeout))

        # assert prop.unreachcall(), "Witch-KLEE can do unreach call only"

        # filter out the non-standard error calls,
        # because we support only one such call atm.
        if prop.unreachcall():
            calls = [x for x in prop.getcalls() if x not in ['__VERIFIER_error', '__assert_fail']]
            if calls:
                assert len(calls) == 1, "Multiple error functions unsupported yet"
                cmd.append('-error-fn={0}'.format(calls[0]))
            # FIXME: append to all properties?
            cmd.append('-malloc-symbolic-contents')

        if opts.exit_on_error:
            print("Witch-KLEE does not support -exit-on-error")

        if self._options.witness_check_file is None:
            raise SymbioticException("Witch-KLEE needs a witness (--witness-check=<witness>)")
        return cmd + options + tasks + self._options.argv + [self._options.witness_check_file]

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        opts = self._options
        prop = opts.property

        if isTimeout:
            return 'timeout'

        if output is None:
            return 'ERROR (no output)'

        parsing_failed = None
        for line in output:
            if b'Parsing failed' in line:
                parsing_failed = line.strip().split(b':')[-1].strip().decode('utf-8')
            if b'Valid violation witness' in line:
                if b'unreach-call' in line:
                    return result.RESULT_FALSE_REACH
                if b'valid-free' in line:
                    return result.RESULT_FALSE_FREE
                if b'valid-deref' in line:
                    return result.RESULT_FALSE_DEREF
                if b'valid-memtrack' in line:
                    return result.RESULT_FALSE_MEMTRACK
                if b'valid-memcleanup' in line:
                    return result.RESULT_FALSE_MEMCLEANUP
                if b'no-overflow' in line:
                    return result.RESULT_FALSE_OVERFLOW
        if returncode != 0:
            if parsing_failed:
                return f'{result.RESULT_ERROR} ({parsing_failed})'
            return f'{result.RESULT_ERROR} (exitcode {returncode})'
        if returnsignal != 0:
            return f'{result.RESULT_ERROR} (signal {returnsignal})'

        return result.RESULT_UNKNOWN


    def set_environment(self, env, opts):
        """
        Set environment for the tool
        """
        if opts.devel_mode:
            env.prepend('PATH', '{0}/witch-klee/build-{1}/bin'.\
                        format(env.symbiotic_dir, self.llvm_version()))
            # XXX: we must take the runtime libraries from the install directory
            # because we have them compiled for 32-bit and 64-bit separately
            #(in build, there's only one of them)
            prefix = '{0}/install'.format(env.symbiotic_dir)
        else:
            prefix = '{0}'.format(env.symbiotic_dir)
            env.prepend('PATH', '{0}/llvm-{1}/witch-klee/bin'.format(env.symbiotic_dir, self.llvm_version()))
            env.prepend('LD_LIBRARY_PATH', '{0}/llvm-{1}/witch-klee/lib'.format(env.symbiotic_dir, self.llvm_version()))

        if opts.is32bit:
            env.prepend('KLEE_RUNTIME_LIBRARY_PATH',
                         '{0}/llvm-{1}/witch-klee/lib32/klee/runtime'.\
                         format(prefix, self.llvm_version()))
        else:
            env.prepend('KLEE_RUNTIME_LIBRARY_PATH',
                        '{0}/llvm-{1}/witch-klee/lib/klee/runtime'.\
                        format(prefix, self.llvm_version()))

