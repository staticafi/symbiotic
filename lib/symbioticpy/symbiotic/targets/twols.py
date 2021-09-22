"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2019-2021  Marek Chalupa
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
import logging
import xml.etree.ElementTree as ET

try:
    import benchexec.util as util
    import benchexec.result as result
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result
    from symbiotic.benchexec.tools.template import BaseTool

from symbiotic.utils.process import runcmd
from symbiotic.utils.watch import DbgWatch
from . tool import SymbioticBaseTool

try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='10.0.1'

class SymbioticTool(BaseTool, SymbioticBaseTool):
    """
    Tool info for CBMC (http://www.cprover.org/cbmc/).
    It always adds --xml-ui to the command-line arguments for easier parsing of
    the output, unless a propertyfile is passed -- in which case running under
    SV-COMP conditions is assumed.
    """

    def __init__(self, opts, only_results=None):
        """ only_results = if not none, report only these results as real,
            otherwise report 'unknown'. Used to implement incremental BMC.
        """
        SymbioticBaseTool.__init__(self, opts)
        opts.explicit_symbolic = True
        self._only_results = only_results

    def executable(self):
        return util.find_executable("2ls")

    def name(self):
        return "2LS"

    def version(self, executable):
        return self._version_from_tool(executable)

    def slicer_options(self):
        """ Override slicer options: do not slice bodies of funs
            that are slicing criteria. CBMC uses the assertions inside,
            not the calls themselves.
        """
        prp = self._options.property
        if not self._options.full_instrumentation and prp.signedoverflow():
            return (['__symbiotic_check_overflow'], ['-criteria-are-next-instr'])

        sc, opts = super().slicer_options()
        return (sc, opts + ['--preserved-functions={0}'.format(','.join(sc))])

    def instrumentation_options(self):
        """
        Returns a triple (d, c, l, x) where d is the directory
        with configuration files, c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        if not self._options.full_instrumentation and\
            self._options.property.signedoverflow():
            return ('int_overflows',
                    self._options.overflow_config_file or 'config-marker.json',
                    'overflows-marker.c', False)
        return super().instrumentation_options()

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
        # LLVM backend in CPAchecker does not handle switches correctly yet
        return super().passes_before_verification() + ["-reg2mem", "-lowerswitch", "-simplifycfg"]

    def passes_before_slicing(self):
        if self._options.property.termination():
            return ['-find-exits', '-use-exit']
        return []

    def actions_before_verification(self, symbiotic):
        # link our specific funs
        self._options.linkundef = ['verifier']
        symbiotic.link_undefined(only_func=['__VERIFIER_silent_exit','__VERIFIER_exit'])
        self._options.linkundef = []
        # translate to C
        output = symbiotic.curfile + '.c'
        runcmd(['llvm2c', symbiotic.curfile, '--add-includes', '--o', output],
                DbgWatch('all'))
        symbiotic.curfile = output

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        if propertyfile:
            options = options + ["--propertyfile", propertyfile]

        options.append('--32' if self._options.is32bit else '--64')

        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if (
            (returnsignal == 9) or (returncode == 15)
        ) and isTimeout:
            status = "TIMEOUT"
        elif returnsignal == 9:
            status = "OUT OF MEMORY"
        elif returnsignal:
            status = f"ERROR(SIGNAL {run.exit_code.signal})"
        elif returncode == 0:
            status = result.RESULT_TRUE_PROP
        elif returncode == 10:
            if output:
                result_str = str(output[-1]).strip()
                if result_str == "FALSE(valid-memtrack)":
                    status = result.RESULT_FALSE_MEMTRACK
                elif result_str == "FALSE(valid-deref)":
                    status = result.RESULT_FALSE_DEREF
                elif result_str == "FALSE(valid-free)":
                    status = result.RESULT_FALSE_FREE
                elif result_str == "FALSE(no-overflow)":
                    status = result.RESULT_FALSE_OVERFLOW
                elif result_str == "FALSE(termination)":
                    status = result.RESULT_FALSE_TERMINATION
                elif result_str == "FALSE(valid-memcleanup)":
                    status = result.RESULT_FALSE_MEMCLEANUP
                else:
                    status = result.RESULT_FALSE_REACH
            else:
                status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status
