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

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template

import os
import re

class Tool(benchexec.tools.template.BaseTool):

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
        return 'SMACK+Corral'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Allows us to define special actions to be taken or command line argument
        modifications to make just before calling SMACK.
        """
        assert len(tasks) == 1
        assert propertyfile is not None
        prop = ['--svcomp-property', propertyfile]
        return [executable] + options + prop + tasks

    def llvm_version(self):
        return '3.7.1'

    def preprocess_llvm(self, infile):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        return (None, None)

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
        """
        Returns a BenchExec result status based on the output of SMACK
        """
        splitout = "\n".join(output)
        if 'SMACK found no errors' in splitout:
          return result.RESULT_TRUE_PROP
        errmsg = re.search(r'SMACK found an error(:\s+([^\.]+))?\.', splitout)
        if errmsg:
          errtype = errmsg.group(2)
          if errtype:
            if 'invalid pointer dereference' == errtype:
              return result.RESULT_FALSE_DEREF
            elif 'invalid memory deallocation' == errtype:
              return result.RESULT_FALSE_FREE
            elif 'memory leak' == errtype:
              return result.RESULT_FALSE_MEMTRACK
            elif 'signed integer overflow' == errtype:
              return result.RESULT_FALSE_OVERFLOW
          else:
            return result.RESULT_FALSE_REACH
        return result.RESULT_UNKNOWN

