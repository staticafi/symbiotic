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
        self.klee = KleeTool(opts)
        self.slowbeast = SlowbeastTool(opts)
        self._options = opts
        self._env = None

    def verifiers(self):
        prp = self._options.property
        if prp.unreachcall():
            return ((KleeTool(self._options), None, 222),
                    (SlowbeastTool(self._options), ['-bself'], None),
                    # if slowbeast crashes, run KLEE w/o timeout
                    (KleeTool(self._options), None, None),
                    # slowbeast  got better support for floats, so if KLEE
                    # fails, try slowbeast once more
                    (SlowbeastTool(self._options), None, None),
                    )
        return ((KleeTool(self._options), None, None),)

    def name(self):
        return 'svcomp'

    def executable(self):
        raise NotImplementedError("This should be never called")

    def llvm_version(self):
        # we suppose that all tools
        assert self.klee.llvm_version() == self.slowbeast.llvm_version()
        return self.klee.llvm_version()

    def set_environment(self, env, opts):
        self._env = env
        self.klee.set_environment(env, self._options)
        self.slowbeast.set_environment(env, self._options)

    def actions_before_slicing(self, symbiotic):
        if hasattr(self.klee, 'actions_before_slicing'):
            self.klee.actions_before_slicing(symbiotic)

    def passes_before_slicing(self):
        if self._options.property.termination():
            return ['-find-exits']
        return []

    def actions_after_slicing(self, symbiotic):
        if hasattr(self.klee, 'actions_after_slicing'):
            self.klee.actions_after_slicing(symbiotic)

    def replay_error_params(self, llvmfile):
        raise NotImplementedError("This should be never called")

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        raise NotImplementedError("This should be never called")

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        raise NotImplementedError("This should be never called")

