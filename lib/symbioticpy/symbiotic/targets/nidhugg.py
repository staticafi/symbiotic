"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2018-2021  Marek Chalupa
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
from symbiotic.utils.process import runcmd
from symbiotic.utils.watch import DbgWatch

try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='10.0.1'

try:
    import benchexec.util as util
    import benchexec.result as result
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result
    from symbiotic.benchexec.tools.template import BaseTool

from . tool import SymbioticBaseTool

class SymbioticTool(BaseTool, SymbioticBaseTool):
    """
    Nidhugg tool info object
    """

    def __init__(self, opts, only_results=None, unroll=None):
        SymbioticBaseTool.__init__(self, opts)
        self._options = opts
        self._only_results = only_results
        self._unroll = unroll

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable('nidhugg')

    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        """
        return self._version_from_tool(executable, arg='-version')

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'nidhugg'

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        return llvm_version

    def verifiers(self):
        prp = self._options.property
        return (
               #(SymbioticTool(self._options, only_results=['false'], unroll=2), None, 30),
               #(SymbioticTool(self._options, only_results=['false'], unroll=5), None, 200),
               #(SymbioticTool(self._options, only_results=['false'], unroll=10), None, 400),
                (SymbioticTool(self._options), None, None),
                )

    def set_environment(self, env, opts):
        """
        Set environment for the tool
        """
        if opts.devel_mode:
            env.prepend('PATH', '{0}/nidhugg/build-{1}/src'.\
                        format(env.symbiotic_dir, self.llvm_version()))
        # thread all programs as 64-bit as we just cannot change the architecture
        # in Nidhugg
        opts.is32bit = False

    def actions_after_slicing(self, symbiotic):
        # unroll the loops and rename __VERIFIER_atomic_begin/end
        # to avoid a bug in nidhugg
        symbiotic.run_opt(['-reg2mem', '-sbt-loop-unroll',
                           '-sbt-loop-unroll-count', '7',
                           '-sbt-loop-unroll-terminate',
                           '-replace-verifier-atomic'])

    def actions_before_slicing(self, symbiotic):
        symbiotic.link_undefined(['__VERIFIER_atomic_begin',
                                  '__VERIFIER_atomic_end'])

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        # -rf is buggy now...
        # cmd = [executable, '-sc', '-rf', '-disable-mutex-init-requirement']
        cmd = [executable, '-sc', '-disable-mutex-init-requirement']
        return cmd + options + tasks

    def actions_before_verification(self, symbiotic):
        if not self._unroll:
            return
        output = symbiotic.curfile + f'unrl{self._unroll}.bc'
        runcmd([self.executable(), symbiotic.curfile,
                '--unroll', str(self._unroll), '--transform', output],
                DbgWatch('all'))
        symbiotic.curfile = output

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return 'timeout'

        if output is None:
            return 'ERROR (no output)'

        status = None
        for line in map(lambda s: s.strip().decode('utf-8'), output):
            if line == 'No errors were detected.':
                status = result.RESULT_TRUE_PROP
           #elif line == 'Error detected:':
           #    status = result.RESULT_FALSE_REACH
            elif 'Error: Assertion violation at' in line:
                status = result.RESULT_FALSE_REACH

        if status:
            if self._only_results:
                res = status.lower()
                if res.startswith('false'):
                    res = 'false'
                elif res.startswith('true'):
                    res = 'true'
                if not res in self._only_results:
                    return result.RESULT_UNKNOWN
            return status

        if returnsignal != 0:
            return f"{result.RESULT_ERROR}(signal {returnsignal})"
        if returncode != 0:
            return f"{result.RESULT_ERROR}(returned {returncode})"
        return result.RESULT_ERROR

