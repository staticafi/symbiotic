# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import subprocess
import sys
import os
import re

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


SOFTTIMELIMIT = 'timelimit'

class SymbioticTool(BaseTool, SymbioticBaseTool):
    """
    Tool info for CPAchecker.
    It has additional features such as building CPAchecker before running it
    if executed within a source checkout.
    It also supports extracting data from the statistics output of CPAchecker
    for adding it to the result tables.
    """
    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)

    def executable(self):
        return util.find_executable('ikos')

    def version(self, executable):
        stdout = self._version_from_tool(executable, '--version')
        line = next(l for l in stdout.splitlines() if l.startswith('ikos'))
        line = line.replace('ikos' , '')
        return line.strip()

    def name(self):
        return 'ikos'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        opts = ['-d=dbm']

        if self._options.property.assertions():
            opts.append('-a=prover')
        elif self._options.property.memsafety():
            opts.append('-a=boa')
            opts.append('-a=nullity')
            opts.append('-a=dfa')
        elif self._options.property.signedoverflow():
            opts.append('-a=sio')

        return [executable] + options + opts + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        # TODO: fixme for memsafety
        for line in output:
            if 'error: double free' in line:
                return result.RESULT_FALSE_FREE
            elif 'error: buffer overflow' in line:
                return result.RESULT_FALSE_DEREF
            elif 'error: assertion never holds' in line:
                return result.RESULT_FALSE_REACH
            elif 'The program is SAFE' in line:
                return result.RESULT_TRUE_PROP
            elif 'The program is potentially UNSAFE' in line:
                return result.RESULT_UNKNOWN

        return result.RESULT_ERROR

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        return '7.0.1'

