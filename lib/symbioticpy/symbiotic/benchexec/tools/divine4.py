"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2015-2018  Vladimir Still
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

This file contains tool support for DIVINE (divine.fi.muni.cz)
"""

import logging

try:
    import benchexec.util as util
    import benchexec.result as result
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result
    from symbiotic.benchexec.tools.template import BaseTool

import subprocess

import os

class Tool(BaseTool):
    """
    DIVINE tool info object
    """

    BINS = ['divine', 'divine-svc']
    REQUIRED_PATHS = BINS + ['lib']
    RESMAP = { 'true': result.RESULT_TRUE_PROP
             , 'false': result.RESULT_FALSE_REACH
             , 'false-deref': result.RESULT_FALSE_DEREF
             , 'false-free': result.RESULT_FALSE_FREE
             , 'false-memtrack': result.RESULT_FALSE_MEMTRACK
             , 'false-term': result.RESULT_FALSE_TERMINATION
             , 'false-deadlock': result.RESULT_FALSE_DEADLOCK
             , 'false-overflow': result.RESULT_FALSE_OVERFLOW
             }

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        The path returned should be relative to the current directory.
        """
        return util.find_executable(self.BINS[0])

    def version(self, executable):
        output = self._version_from_tool(executable, ignore_stderr=True)
        for l in output.splitlines():
            k, v = l.split(':', maxsplit=1)
            if k == 'version':
                return v.strip()
        return ''

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'DIVINE'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the inputfile to analyze.
        This method can get overridden, if, for example, some options should
        be enabled or if the order of arguments must be changed.

        All paths passed to this method (executable, tasks, and propertyfile)
        are either absolute or have been made relative to the designated working directory.

        @param executable: the path to the executable of the tool (typically the result of executable())
        @param options: a list of options, in the same order as given in the XML-file.
        @param tasks: a list of tasks, that should be analysed with the tool in one run.
                            In most cases we we have only _one_ inputfile.
        @param propertyfile: contains a specification for the verifier.
        @param rlimits: This dictionary contains resource-limits for a run,
                        for example: time-limit, soft-time-limit, hard-time-limit, memory-limit, cpu-core-limit.
                        All entries in rlimits are optional, so check for existence before usage!
        """
        directory = os.path.dirname(executable)
        prp = propertyfile or "-"

        # prefix command line with wrapper script
        return [os.path.join(directory, self.BINS[1]), executable, prp] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """

        if not output:
            return 'ERROR - no output'

        last = output[-1].decode("utf-8")

        if isTimeout:
            return 'TIMEOUT'

        if returncode != 0:
            return 'ERROR - {0}'.format( last )

        if 'result:' in last:
            res = last.split(':', 1)[1].strip()
            return self.RESMAP.get( res, result.RESULT_UNKNOWN );
        else:
            return 'UNKNOWN ERROR'
