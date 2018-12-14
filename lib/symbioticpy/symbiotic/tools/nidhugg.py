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

class SymbioticTool(BaseTool):
    """
    Nidhugg tool info object
    """

    def __init__(self, opts):
        self._options = opts

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

    def compilation_options(self):
        """
        List of compilation options specific for this tool
        """
        opts = []
        if self._options.property.undefinedness():
                opts.append('-fsanitize=undefined')
                opts.append('-fno-sanitize=unsigned-integer-overflow')
        elif self._options.property.signedoverflow():
                opts.append('-fsanitize=signed-integer-overflow')
                opts.append('-fsanitize=shift')

        return opts

    def passes_after_compilation(self):
        """
        Prepare the bitcode for verification - return a list of
        LLVM passes that should be run on the code
        """
        # remove definitions of __VERIFIER_* that are not created by us,
        # make extern globals local, etc. Also remove syntactically infinite loops.
        passes = []

        if not self._options.property.termination():
            passes.append('-remove-infinite-loops')

        if self._options.property.undefinedness() or \
           self._options.property.signedoverflow():
            passes.append('-replace-ubsan')

        if self._options.property.signedoverflow() and \
           not self._options.overflow_with_clang:
            passes.append('-prepare-overflows')

        return passes

    def passes_after_slicing(self):
        """
        Prepare the bitcode for verification after slicing:
        \return a list of LLVM passes that should be run on the code
        """
        passes = []

        # side-effects, because LLVM optimizations could remove them otherwise,
        # even though they contain calls to assert
        if self._options.property.memsafety():
            passes.append('-remove-readonly-attr')
            passes.append('-dummy-marker')

        return passes

    def actions_after_slicing(self, symbiotic):
        llvmfile=symbiotic.llvmfile
        newfile='{0}-unrolled.bc'.format(llvmfile[:-3])
        runcmd(['nidhugg', '-unroll=5', llvmfile,
                '-transform', newfile])
        symbiotic.llvmfile = newfile

    def instrumentation_options(self):
        """
        Returns a triple (c, l, x) where c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        # NOTE: we do not want to link the functions with memsafety/cleanup
        # because then the optimizations could remove the calls to markers
        if self._options.property.memsafety():
            return ('config-marker.json', 'marker.c', False)

        if self._options.property.memcleanup():
            return ('config-marker-memcleanup.json', 'marker.c', False)

        if self._options.property.signedoverflow():
            # default config file is 'config.json'
            return (self._options.overflow_config_file, 'overflows.c', True)

        if self._options.property.termination():
            return ('config.json', 'termination.c', True)

        return (None, None, None)

    def slicer_options(self):
        """
        Returns tuple (c, opts) where c is the slicing
        criterion and opts is a list of options
        """

        if self._options.property.memsafety():
            # default config file is 'config.json'
            # slice with respect to the memory handling operations
            return ('__INSTR_mark_pointer,__INSTR_mark_free,__INSTR_mark_allocation',
                    ['-criteria-are-next-instr'])

        elif self._options.property.memcleanup():
            # default config file is 'config.json'
            # slice with respect to the memory handling operations
            return ('__INSTR_mark_free,__INSTR_mark_allocation',
                    ['-criteria-are-next-instr'])

        return (self._options.slicing_criterion,[])

    def passes_after_instrumentation(self):
        passes = []
        if self._options.property.memsafety():
            # replace llvm.lifetime.start/end with __VERIFIER_scope_enter/leave
            # so that optimizations will not mess the code up
            passes = ['-replace-lifetime-markers']

            # make all store/load insts that are marked by instrumentation
            # volatile, so that we can run optimizations later on them
            passes.append('-mark-volatile')
        return passes

    def actions_after_compilation(self, symbiotic):
        if symbiotic.options.property.signedoverflow() and \
           not symbiotic.options.overflow_with_clang:
            symbiotic.link_undefined()

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        # for now use 5
        cmd = [executable, '-sc']
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

