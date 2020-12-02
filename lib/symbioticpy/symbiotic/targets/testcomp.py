"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2016-2020  Marek Chalupa
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

from symbiotic.utils.utils import process_grep
from symbiotic.utils import dbg
from symbiotic.exceptions import SymbioticException


from . tool import SymbioticBaseTool

try:
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    from symbiotic.benchexec.tools.template import BaseTool

from . klee import SymbioticTool as KleeTool
from . slowbeast import SymbioticTool as SlowbeastTool

class SymbioticTool(BaseTool, SymbioticBaseTool):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        self.tool = KleeTool(opts)
        self._options = opts
        self._env = None
        self._has_threads = False

    def verifiers(self):
        return ((KleeTool(self._options), None, None),)

    def name(self):
        return 'svcomp' # if renamed, adjust models in lib\ folder

    def executable(self):
        return self.tool.executable()

    def llvm_version(self):
        # we suppose that all tools
        return self.tool.llvm_version()

    def set_environment(self, env, opts):
        self._env = env
        self.tool.set_environment(env, self._options)

    def actions_before_slicing(self, symbiotic):
        if hasattr(self.tool, 'actions_before_slicing'):
            self.tool.actions_before_slicing(symbiotic)

    def actions_after_slicing(self, symbiotic):
        if hasattr(self.tool, 'actions_after_slicing'):
            self.tool.actions_after_slicing(symbiotic)

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """
        return self.tool.cmdline(executable, options, tasks, propertyfile, rlimits)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        return self.tool.determine_result(returncode, returnsignal, output, isTimeout)

    def describe_error(self, llvmfile):
        if hasattr(self.tool, 'describe_error'):
            self.tool.describe_error(llvmfile)

    def generate_witness(self, llvmfile, sources, has_error):
        if hasattr(self.tool, "generate_witness"):
            self.tool.generate_witness(llvmfile, sources, has_error)

    def generate_exec_witness(self, llvmfile, sources):
        if hasattr(self.tool, "generate_exec_witness"):
            self.tool.generate_exec_witness(llvmfile, sources)
