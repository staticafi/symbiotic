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

try:
    from benchexec.tools.predatorhp import Tool as PredatorHPTool
except ImportError:
    from .. benchexec.tools.predatorhp import Tool as PredatorHPTool

from . tool import SymbioticBaseTool
from symbiotic.utils.process import runcmd
from symbiotic.utils.watch import DbgWatch

try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='8.0.1'


class SymbioticTool(PredatorHPTool, SymbioticBaseTool):
    """
    PredatorHP integraded into Symbiotic
    """

    REQUIRED_PATHS = PredatorHPTool.REQUIRED_PATHS

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._memsafety = self._options.property.memsafety()

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
        # llvm2c has a bug with PHI nodes
        return ["-lowerswitch", "-simplifycfg", "-reg2mem", "-simplifycfg"]

    def actions_before_verification(self, symbiotic):
        output = symbiotic.curfile + '.c'
        runcmd(['llvm2c', symbiotic.curfile, '--o', output], DbgWatch('all'))
        symbiotic.curfile = output

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        cmd = PredatorHPTool.cmdline(self, executable, options, tasks, propertyfile, rlimits)
        if self._options.is32bit:
            cmd.append("--compiler-options=-m32")
        else:
            cmd.append("--compiler-options=-m64")
        return cmd


