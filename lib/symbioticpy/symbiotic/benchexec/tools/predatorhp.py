"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
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

try:
    import benchexec.util as util
    import benchexec.result as result
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result
    from symbiotic.benchexec.tools.template import BaseTool

class Tool(BaseTool):
    """
    Wrapper for a Predator - Hunting Party
    http://www.fit.vutbr.cz/research/groups/verifit/tools/predator-hp/
    """

    REQUIRED_PATHS = ["predator", "predator-bfs", "predator-dfs", "predatorHP.py"]

    def executable(self):
        return util.find_executable("predatorHP.py")

    def name(self):
        return "PredatorHP"

    def version(self, executable):
        return self._version_from_tool(executable, use_stderr=True)

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        spec = ["--propertyfile", propertyfile] if propertyfile is not None else []
        return [executable] + options + spec + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = "UNKNOWN"
        for line in (l.decode('ascii') for l in output):
            if "UNKNOWN" in line:
                status = result.RESULT_UNKNOWN
            elif "TRUE" in line:
                status = result.RESULT_TRUE_PROP
            elif "FALSE(valid-memtrack)" in line:
                status = result.RESULT_FALSE_MEMTRACK
            elif "FALSE(valid-deref)" in line:
                status = result.RESULT_FALSE_DEREF
            elif "FALSE(valid-free)" in line:
                status = result.RESULT_FALSE_FREE
            elif "FALSE(valid-memcleanup)" in line:
                status = result.RESULT_FALSE_MEMCLEANUP
            elif "FALSE" in line:
                status = result.RESULT_FALSE_REACH
            if status == "UNKNOWN" and isTimeout:
                status = "TIMEOUT"
        return status
