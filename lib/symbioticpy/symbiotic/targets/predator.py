"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2020-2021  Marek Chalupa
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

from . tool import SymbioticBaseTool
from symbiotic.utils.process import runcmd
from symbiotic.utils.watch import DbgWatch
try:
    import benchexec.util as util
    import benchexec.result as result
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result

try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='8.0.1'


class SymbioticTool(SymbioticBaseTool):
    """
    Predator integraded into Symbiotic
    """

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._memsafety = self._options.property.memsafety()

    def name(self):
        return 'predator'

    def executable(self):
        return util.find_executable('check-property.sh',
                                    'sl_build/check-property.sh')

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        return llvm_version

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []

    def passes_before_verification(self):
        """
        Passes that should run before CPAchecker
        """
        return super().passes_before_verification() +\
                ["-delete-undefined", "-lowerswitch", "-simplifycfg"]

    def actions_before_verification(self, symbiotic):
        output = symbiotic.curfile + '.c'
        runcmd(['llvm2c', symbiotic.curfile, '--o', output], DbgWatch('all'))
        symbiotic.curfile = output

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        #cmd = PredatorTool.cmdline(self, executable, options,
        #                           tasks, propertyfile, rlimits)
        cmd = [self.executable(), '--trace=/dev/null',
               '--propertyfile', propertyfile, '--'] + tasks

        if self._options.is32bit:
            cmd.append("-m32")
        else:
            cmd.append("-m64")
        return cmd

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = "UNKNOWN"
        for line in (l.decode('ascii') for l in output):
            if "UNKNOWN" in line:
                status = result.RESULT_UNKNOWN
            elif "TRUE" in line:
                status = result.RESULT_TRUE_PROP
            elif "FALSE(valid-memtrack)" in line:
                status = result.RESULT_FALSE_MEMTRACK
            elif "FALSE(valid-deref)" in line:
                status = result.RESULT_FALSE_DEREF
            elif "FALSE(valid-free)" in line:
                status = result.RESULT_FALSE_FREE
            elif "FALSE(valid-memcleanup)" in line:
                status = result.RESULT_FALSE_MEMCLEANUP
            elif "FALSE" in line:
                status = result.RESULT_FALSE_REACH
            if status == "UNKNOWN" and isTimeout:
                status = "TIMEOUT"
        return status
