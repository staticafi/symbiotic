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

class SymbioticTool(BaseTool, SymbioticBaseTool):
    """
    Tool info for CBMC (http://www.cprover.org/cbmc/).
    It always adds --xml-ui to the command-line arguments for easier parsing of
    the output, unless a propertyfile is passed -- in which case running under
    SV-COMP conditions is assumed.
    """

    REQUIRED_PATHS = [
                  "cbmc",
                  "cbmc-binary",
                  "goto-cc"
                  ]
    def executable(self):
        return util.find_executable('cbmc')


    def version(self, executable):
        return self._version_from_tool(executable)


    def name(self):
        return 'CBMC'


    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        if propertyfile:
            options = options + ['--propertyfile', propertyfile]
        elif ("--xml-ui" not in options):
            options = options + ["--xml-ui"]

        self.options = options

        return [executable] + options + tasks


    def parse_XML(self, output, returncode, isTimeout):
        #an empty tag cannot be parsed into a tree
        def sanitizeXML(s):
            return s.replace("<>", "<emptyTag>") \
                    .replace("</>", "</emptyTag>")

        try:
            tree = ET.fromstringlist(map(sanitizeXML, output))
            status = tree.findtext('cprover-status')

            if status is None:
                def isErrorMessage(msg):
                    return msg.get('type', None) == 'ERROR'

                messages = list(filter(isErrorMessage, tree.getiterator('message')))
                if messages:
                    # for now, use only the first error message if there are several
                    msg = messages[0].findtext('text')
                    if msg == 'Out of memory':
                        status = 'OUT OF MEMORY'
                    elif msg:
                        status = 'ERROR ({0})'.format(msg)
                    else:
                        status = 'ERROR'
                else:
                    status = 'INVALID OUTPUT'

            elif status == "FAILURE":
                assert returncode == 10
                reason = tree.find('goto_trace').find('failure').findtext('reason')
                if not reason:
                    reason = tree.find('goto_trace').find('failure').get('reason')
                if 'unwinding assertion' in reason:
                    status = result.RESULT_UNKNOWN
                else:
                    status = result.RESULT_FALSE_REACH

            elif status == "SUCCESS":
                assert returncode == 0
                if "--unwinding-assertions" in self.options:
                    status = result.RESULT_TRUE_PROP
                else:
                    status = result.RESULT_UNKNOWN

        except Exception:
            if isTimeout:
                # in this case an exception is expected as the XML is invalid
                status = 'TIMEOUT'
            elif 'Minisat::OutOfMemoryException' in output:
                status = 'OUT OF MEMORY'
            else:
                status = 'INVALID OUTPUT'
                logging.exception("Error parsing CBMC output for returncode %d", returncode)

        return status



    def determine_result(self, returncode, returnsignal, output, isTimeout):

        if returnsignal == 0 and ((returncode == 0) or (returncode == 10)):
            status = result.RESULT_ERROR
            if ('--xml-ui' in self.options):
                status = self.parse_XML(output, returncode, isTimeout)
            elif len(output) > 0:
                # SV-COMP mode
                result_str = output[-1].strip()

                if result_str == 'TRUE' :
                    status = result.RESULT_TRUE_PROP
                elif 'FALSE' in result_str:
                    if result_str == 'FALSE(valid-memtrack)':
                        status = result.RESULT_FALSE_MEMTRACK
                    elif result_str == 'FALSE(valid-deref)':
                        status = result.RESULT_FALSE_DEREF
                    elif result_str == 'FALSE(valid-free)':
                        status = result.RESULT_FALSE_FREE
                    elif result_str == 'FALSE(no-overflow)':
                        status = result.RESULT_FALSE_OVERFLOW
                    elif result_str == 'FALSE(valid-memcleanup)':
                        status = result.RESULT_FALSE_MEMCLEANUP
                    else:
                        status = result.RESULT_FALSE_REACH
                elif 'UNKNOWN' in output:
                    status = result.RESULT_UNKNOWN

        elif returncode == 64 and 'Usage error!\n' in output:
            status = 'INVALID ARGUMENTS'

        elif returncode == 6 and 'Out of memory\n' in output:
            status = 'OUT OF MEMORY'

        else:
            status = result.RESULT_ERROR

        return status

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        return '7.0.1'

    def passes_before_verification(self):
        """
        Passes that should run before CPAchecker
        """
        # LLVM backend in CPAchecker does not handle switches correctly yet
        return ["-reg2mem", "-lowerswitch", "-simplifycfg"]

    def actions_before_verification(self, symbiotic):
        output = symbiotic.curfile + '.c'
        runcmd(['llvm2c', symbiotic.curfile, '--o', output],
                DbgWatch('all'))
        symbiotic.curfile = output
