"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2008  Marek Chalupa
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

try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='4.0.1'

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

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)

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

    def set_environment(self, env, opts):
        """
        Set environment for the tool
        """
        if opts.devel_mode:
            env.prepend('PATH', '{0}/nidhugg/build-{1}/src'.\
                        format(env.symbiotic_dir, self.llvm_version()))

    def actions_after_slicing(self, symbiotic):
        # unroll the loops and rename __VERIFIER_atomic_begin/end
        # to avoid a bug in nidhugg
        symbiotic.run_opt(['-reg2mem', '-sbt-loop-unroll',
                           '-sbt-loop-unroll-count', '5',
                           '-sbt-loop-unroll-terminate',
                           '-replace-verifier-atomic'])

    def actions_before_slicing(self, symbiotic):
        symbiotic.link_undefined(['__VERIFIER_atomic_begin',
                                  '__VERIFIER_atomic_end'])

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        # for now use 5
        cmd = [executable, '-sc', '-disable-mutex-init-requirement']
        return cmd + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return 'timeout'

        if output is None:
            return 'ERROR (no output)'

        for line in output:
            if line.strip() == 'No errors were detected.':
                return result.RESULT_TRUE_PROP
            elif line.strip() == 'Error detected:':
                return result.RESULT_FALSE_REACH

        if returncode != 0:
            return result.RESULT_ERROR
        else:
            return result.RESULT_UNKNOWN

