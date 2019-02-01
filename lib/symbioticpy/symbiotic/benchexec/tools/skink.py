"""
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

    REQUIRED_PATHS = [
                  "bin",
                  "lib",
                  "include",
                  "logback-test.xml",
                  "skink.sh",
                  "skink.jar",
                  "skink-fpbv.jar",
                  "application.conf"
                  ]

    def executable(self):
        return util.find_executable('skink.sh')

    def name(self):
        return 'skink'

    def version(self, executable):
        return self._version_from_tool(executable)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "FALSE" in output:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status
