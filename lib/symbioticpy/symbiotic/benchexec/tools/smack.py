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

import os
import re

class Tool(BaseTool):

    REQUIRED_PATHS = [
                  "boogie",
                  "corral",
                  "llvm",
                  "lockpwn",
                  "smack",
                  "smack.sh"
                  ]

    def executable(self):
        """
        Tells BenchExec to search for 'smack.sh' as the main executable to be
        called when running SMACK.
        """
        return util.find_executable('smack.sh')

    def version(self, executable):
        """
        Sets the version number for SMACK, which gets displayed in the "Tool" row
        in BenchExec table headers.
        """
        return self._version_from_tool(executable, use_stderr=True).split(' ')[2]

    def name(self):
        """
        Sets the name for SMACK, which gets displayed in the "Tool" row in
        BenchExec table headers.
        """
        return 'SMACK'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Allows us to define special actions to be taken or command line argument
        modifications to make just before calling SMACK.
        """
        assert len(tasks) == 1
        assert propertyfile is not None
        prop = ['--svcomp-property', propertyfile]
        return [executable] + options + prop + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Returns a BenchExec result status based on the output of SMACK
        """
        splitout = b"\n".join(output)
        if b'SMACK found no errors' in splitout:
          return result.RESULT_TRUE_PROP
        errmsg = re.search('SMACK found an error(:\s+([^\.]+))?\.', splitout.decode('utf-8'))
        if errmsg:
          errtype = errmsg.group(2)
          if errtype:
            if 'invalid pointer dereference' == errtype:
              return result.RESULT_FALSE_DEREF
            elif 'invalid memory deallocation' == errtype:
              return result.RESULT_FALSE_FREE
            elif 'memory leak' == errtype:
              return result.RESULT_FALSE_MEMTRACK
            elif 'memory cleanup' == errtype:
              return result.RESULT_FALSE_MEMCLEANUP
            elif 'integer overflow' == errtype:
              return result.RESULT_FALSE_OVERFLOW
          else:
            return result.RESULT_FALSE_REACH
        return result.RESULT_UNKNOWN

