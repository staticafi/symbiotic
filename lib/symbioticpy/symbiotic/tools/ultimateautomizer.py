"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2015 Daniel Dietsch (dietsch@informatik.uni-freiburg.de)
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

from . import ultimate

try:
    import benchexec.util as util
    import benchexec.result as result
    from benchexec.tools.ultimate import UltimateTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result
    from . ultimate import UltimateTool

from symbiotic.utils.process import runcmd
from symbiotic.utils.watch import DbgWatch
from . tool import SymbioticBaseTool

class SymbioticTool(UltimateTool, SymbioticBaseTool):

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._memsafety = opts.property.memsafety()

    def name(self):
        return 'ULTIMATE Automizer'

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        return '7.0.1'

    def passes_before_verification(self):
        """
        Passes that should run before CPAchecker
        """
        # LLVM backend in CPAchecker does not handle switches correctly yet
        return ["-reg2mem", "-lowerswitch", "-simplifycfg"]

    def actions_before_verification(self, symbiotic):
        output = symbiotic.curfile + '.c'
        runcmd(['llvm2c', symbiotic.curfile, '--o', output],
                DbgWatch('all'))
        symbiotic.curfile = output

