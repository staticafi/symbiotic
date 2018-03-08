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
    from benchexec.tools.template import  BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result
    from symbiotic.benchexec.tools.template import  BaseTool

class Tool(BaseTool):

    REQUIRED_PATHS = [
        "bin/*",
        "lib/*",
        "skink.sh",
        "skink.jar"
    ]

    def executable(self):
        return 'java'

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        from os.path import abspath, join
        dr = abspath(join(__file__, '../../../../..'))
        return [executable, '-Xmx140m', '-Xss5m', '-cp',
                '{0}/skink-v2.0/:{0}/skink-v2.0/skink.jar'.format(dr),
                'au.edu.mq.comp.skink.Main', '-f', 'LLVM', '--verify'] + tasks

    def name(self):
        return 'skink'

    def llvm_version(self):
        return '3.7.1'

    def preprocess_llvm(self, infile):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        output = infile + '.ll'
        return (['llvm-dis', infile, '-o', output], output)

    def prepare(self):
        """
        Prepare the bitcode for verification - return a list of
        LLVM passes that should be run on the code
        """
        return []

    def prepare_after(self):
        """
        Same as prepare, but runs after slicing
        """
        return []

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "FALSE" in output:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status
