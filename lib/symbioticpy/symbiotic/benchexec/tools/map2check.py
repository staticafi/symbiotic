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
import os

try:
    import benchexec.util as Util
    import benchexec.result as result
    from benchexec.tools.template import  BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as Util
    import symbiotic.benchexec.result as result
    from symbiotic.benchexec.tools.template import  BaseTool


class Tool(BaseTool):
    """
    This class serves as tool adaptor for Map2Check (https://github.com/hbgit/Map2Check)
    """

    REQUIRED_PATHS_6 = [
                  "__init__.py",
                  "map2check.py",
                  "map2check-wrapper.sh",
                  "modules"
                  ]

    REQUIRED_PATHS_7_1 = [
                  "map2check",
                  "map2check-wrapper.py",
                  "bin",
                  "include",
                  "lib"
                  ]

    def executable(self):
        #Relative path to map2check wrapper
        if self._get_version() == 6:
            return Util.find_executable('map2check-wrapper.sh')
        elif self._get_version() > 6:
            return Util.find_executable('map2check-wrapper.py')


    def program_files(self, executable):
        """
        Determine the file paths to be adopted
        """
        if self._get_version() == 6:
            paths = self.REQUIRED_PATHS_6
        elif self._get_version() > 6:
            paths = self.REQUIRED_PATHS_7_1

        return paths

    def _get_version(self):
        """
        Determine the version based on map2check-wrapper.sh file
        """
        exe_v6 = Util.find_executable('map2check-wrapper.sh', exitOnError=False)
        if exe_v6:
            return 6
        else:
            return 7


    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return 'Map2Check'

    def cmdline(self, executable, options, sourcefiles, propertyfile, rlimits):
        assert len(sourcefiles) == 1, "only one sourcefile supported"
        assert propertyfile, "property file required"
        sourcefile = sourcefiles[0]
        if self._get_version() == 6:
            return [executable] + options + ['-c', propertyfile, sourcefile]
        elif self._get_version() > 6:
            return [executable] + options + ['-p', propertyfile, sourcefile]


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if not output:
            return result.RESULT_UNKNOWN
        output = output[-1].strip()
        status = result.RESULT_UNKNOWN

        if self._get_version() > 6:
            if output.endswith('TRUE'):
                status = result.RESULT_TRUE_PROP
            elif 'FALSE' in output:
                if "FALSE_MEMTRACK" in output:
                    status = result.RESULT_FALSE_MEMTRACK
                elif "FALSE_DEREF" in output:
                    status = result.RESULT_FALSE_DEREF
                elif "FALSE_FREE" in output:
                    status = result.RESULT_FALSE_FREE
                elif "FALSE_OVERFLOW" in output:
                    status = result.RESULT_FALSE_OVERFLOW
                else:
                    status = result.RESULT_FALSE_REACH
            elif output.endswith('UNKNOWN'):
                status = result.RESULT_UNKNOWN
            elif isTimeout:
                status = 'TIMEOUT'
            else:
                status = 'ERROR'

        elif self._get_version() == 6:
            if output.endswith('TRUE'):
                status = result.RESULT_TRUE_PROP
            elif 'FALSE' in output:
                if "FALSE(valid-memtrack)" in output:
                    status = result.RESULT_FALSE_MEMTRACK
                elif "FALSE(valid-deref)" in output:
                    status = result.RESULT_FALSE_DEREF
                elif "FALSE(valid-free)" in output:
                    status = result.RESULT_FALSE_FREE
            elif output.endswith('UNKNOWN'):
                status = result.RESULT_UNKNOWN
            elif isTimeout:
                status = 'TIMEOUT'
            else:
                status = 'ERROR'

        return status
