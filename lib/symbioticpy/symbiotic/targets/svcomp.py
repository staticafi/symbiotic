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
        self.tool = KleeTool(opts)
        self._options = opts
        self._env = None
        self._has_threads = False

    def verifiers(self):
        prp = self._options.property
        if prp.unreachcall():
            return ((KleeTool(self._options), None, 222),
                    (SlowbeastTool(self._options), ['-kind'], None),
                    # if slowbeast crashes, run KLEE w/o timeout
                    (KleeTool(self._options), None, None),
                    # slowbeast  got better support for floats, so if KLEE
                    # fails, try slowbeast once more
                    (SlowbeastTool(self._options), ['-se-replay-errors'], None),
                    )
        return ((KleeTool(self._options), None, None),)

    def name(self):
        return 'svcomp'

    def executable(self):
        return self.tool.executable()

    def llvm_version(self):
        # we suppose that all tools
        return self.tool.llvm_version()

    def set_environment(self, env, opts):
        self._env = env
        self.tool.set_environment(env, self._options)

    def actions_before_slicing(self, symbiotic):
        # check whether there are threads in the program
        cmd = ['opt', '-q', '-load', 'LLVMsbt.so', '-check-module',
               '-detect-calls=pthread_create', '-o=/dev/null', symbiotic.curfile]
        retval, lines =\
        process_grep(cmd, 'Found call to function')
        if retval == 0:
            if lines:
               #self._has_threads = True
               #self.tool = NidhuggTool(self._options)
               #self.tool.set_environment(self._env, self._options)
               #dbg("Found threads, will use Nidhugg")
                raise SymbioticException('Found threads, giving up')
        else:
            dbg('Checking the module failed!')

        if hasattr(self.tool, 'actions_before_slicing'):
            self.tool.actions_before_slicing(symbiotic)

   #def passes_after_compilation(self):
   #    return ['-prepare']

    def passes_before_slicing(self):
        if self._options.property.termination():
            return ['-find-exits']
        return []

    def passes_before_verification(self):
        """
        Prepare the bitcode for verification after slicing:
        \return a list of LLVM passes that should be run on the code
        """
        passes = []
        # for the memsafety property, make functions behave like they have
        # side-effects, because LLVM optimizations could remove them otherwise,
        # even though they contain calls to assert
        if self._options.property.memsafety():
            passes.append('-remove-readonly-attr')
        elif self._options.property.termination():
            passes.append('-instrument-nontermination')
            passes.append('-instrument-nontermination-mark-header')

        return passes 

    def replay_error_params(self, llvmfile):
        return self.tool.replay_error_params(llvmfile)


    def slicing_params(self):
        if self._has_threads:
            return ['-threads', '-cd-alg=ntscd']
        return []

    def actions_after_slicing(self, symbiotic):
        if hasattr(self.tool, 'actions_after_slicing'):
            self.tool.actions_after_slicing(symbiotic)

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """
        return self.tool.cmdline(executable, options, tasks, propertyfile, rlimits)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        res = self.tool.determine_result(returncode, returnsignal, output, isTimeout)
        dbg('Tool result: {0}'.format(res))
        if res == 'true' and self.tool.name() == 'nidhugg':
            res='unknown (bounded)'
        return res

    def describe_error(self, llvmfile):
        if hasattr(self.tool, 'describe_error'):
            self.tool.describe_error(llvmfile)

    def generate_witness(self, llvmfile, sources, has_error):
        if hasattr(self.tool, "generate_witness"):
            self.tool.generate_witness(llvmfile, sources, has_error)

    def generate_exec_witness(self, llvmfile, sources):
        if hasattr(self.tool, "generate_exec_witness"):
            self.tool.generate_exec_witness(llvmfile, sources)
