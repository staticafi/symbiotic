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


from . tool import SymbioticBaseTool

try:
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    from symbiotic.benchexec.tools.template import BaseTool

from . klee import SymbioticTool as KleeTool
from . nidhugg import SymbioticTool as NidhuggTool

class SymbioticTool(BaseTool, SymbioticBaseTool):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        self.tool = KleeTool(opts)
        self._options = opts
        self._env = None
        self._has_threads = False

    def name(self):
        return self.tool.name()

    def can_replay(self):
        return self.tool.can_replay()

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
                self._has_threads = True
                self.tool = NidhuggTool(self._options)
                self.tool.set_environment(self._env, self._options)
                dbg("Found threads, will use Nidhugg")
        else:
            dbg('Checking the module failed!')

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
        # instrument our malloc -- either the version that can fail,
        # or the version that can not fail.
        # KLEE and Nidhugg already assumes that
        #if self._options.malloc_never_fails:
        #    passes.append('-instrument-alloc-nf')
        #else:
        #    passes.append('-instrument-alloc')

        # remove/replace the rest of undefined functions
        # for which we do not have a definition and
        # that has not been removed
        # KLEE now handles undefined functions
        # passes.append('-delete-undefined')

        # for the memsafety property, make functions behave like they have
        # side-effects, because LLVM optimizations could remove them otherwise,
        # even though they contain calls to assert
        if self._options.property.memsafety():
            passes.append('-remove-readonly-attr')

        return passes

    def replay_error_params(self, llvmfile):
        return self.tool.replay_error_params(llvmfile)


    def slicing_params(self):
        if self._has_threads:
            return ['-threads', '-cd-alg=ntscd']
        return []

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


    def generate_witness(self, llvmfile, sources, has_error):
        if hasattr(self.tool, "generate_witness"):
            self.tool.generate_witness(llvmfile, sources, has_error)

    def generate_exec_witness(self, llvmfile, sources):
        if hasattr(self.tool, "generate_exec_witness"):
            self.tool.generate_exec_witness(llvmfile, sources)
