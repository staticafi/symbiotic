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

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import subprocess
import sys
import os
import re

import symbiotic.benchexec.result as result
import symbiotic.benchexec.util as util
import symbiotic.benchexec.tools.template

SOFTTIMELIMIT = 'timelimit'

class Tool(symbiotic.benchexec.tools.template.BaseTool):
    """
    Tool info for CPAchecker.
    It has additional features such as building CPAchecker before running it
    if executed within a source checkout.
    It also supports extracting data from the statistics output of CPAchecker
    for adding it to the result tables.
    """

    REQUIRED_PATHS = [
                  "lib/java/runtime",
                  "lib/*.jar",
                  "lib/native/x86_64-linux",
                  "scripts",
                  "cpachecker.jar",
                  "config",
                  ]

    def executable(self):
        executable = util.find_executable('cpa.sh', 'scripts/cpa.sh')
        executableDir = os.path.join(os.path.dirname(executable), os.path.pardir)
        if os.path.isdir(os.path.join(executableDir, 'src')):
            self._buildCPAchecker(executableDir)
        if not os.path.isfile(os.path.join(executableDir, "cpachecker.jar")):
            logging.warning("Required JAR file for CPAchecker not found in {0}.".format(executableDir))
        return executable


    def program_files(self, executable):
        installDir = os.path.join(os.path.dirname(executable), os.path.pardir)
        return util.flatten(util.expand_filename_pattern(path, installDir) for path in self.REQUIRED_PATHS)


    def _buildCPAchecker(self, executableDir):
        logging.debug('Building CPAchecker in directory {0}.'.format(executableDir))
        ant = subprocess.Popen(['ant', '-lib', 'lib/java/build', '-q', 'jar'], cwd=executableDir, shell=util.is_windows())
        ant.communicate()
        if ant.returncode:
            sys.exit('Failed to build CPAchecker, please fix the build first.')


    def version(self, executable):
        stdout = self._version_from_tool(executable, '-help')
        line = next(l for l in stdout.splitlines() if l.startswith('CPAchecker'))
        line = line.replace('CPAchecker' , '')
        line = line.split('(')[0]
        return line.strip()

    def name(self):
        return 'CPAchecker'

    def _get_additional_options(self, existing_options, propertyfile, rlimits):
        options = []
        if SOFTTIMELIMIT in rlimits:
            if "-timelimit" in existing_options:
                logging.warning('Time limit already specified in command-line options, not adding time limit from benchmark definition to the command line.')
            else:
                options = options + ["-timelimit", str(rlimits[SOFTTIMELIMIT]) + "s"] # benchmark-xml uses seconds as unit

        # if data.MEMLIMIT in rlimits:
        #     if "-heap" not in existing_options:
        #         heapsize = rlimits[MEMLIMIT]*0.8 # 20% overhead for non-java-memory
        #         options = options + ["-heap", str(int(heapsize))]

        if ("-stats" not in existing_options):
            options = options + ["-stats"]

        spec = ["-spec", propertyfile] if propertyfile is not None else []

        return options + spec

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        additional_options = self._get_additional_options(options, propertyfile, rlimits)
        return [executable, "-setprop", "language=LLVM"] + options + additional_options + tasks


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        @param returncode: code returned by CPAchecker
        @param returnsignal: signal, which terminated CPAchecker
        @param output: the output of CPAchecker
        @return: status of CPAchecker after executing a run
        """

        def isOutOfNativeMemory(line):
            return ('std::bad_alloc'             in line # C++ out of memory exception (MathSAT)
                 or 'Cannot allocate memory'     in line
                 or 'Native memory allocation (malloc) failed to allocate' in line # JNI
                 or line.startswith('out of memory')     # CuDD
                 )

        status = None

        for line in output:
            if 'java.lang.OutOfMemoryError' in line:
                status = 'OUT OF JAVA MEMORY'
            elif isOutOfNativeMemory(line):
                status = 'OUT OF NATIVE MEMORY'
            elif 'There is insufficient memory for the Java Runtime Environment to continue.' in line \
                    or 'cannot allocate memory for thread-local data: ABORT' in line:
                status = 'OUT OF MEMORY'
            elif 'SIGSEGV' in line:
                status = 'SEGMENTATION FAULT'
            elif (returncode == 0 or returncode == 1) and 'java.lang.AssertionError' in line:
                status = 'ASSERTION'
            elif ((returncode == 0 or returncode == 1)
                    and ('Exception:' in line or line.startswith('Exception in thread'))
                    and not line.startswith('cbmc')): # ignore "cbmc error output: ... Minisat::OutOfMemoryException"
                status = 'EXCEPTION'
            elif 'Could not reserve enough space for object heap' in line:
                status = 'JAVA HEAP ERROR'
            elif line.startswith('Error: ') and not status:
                status = result.RESULT_ERROR
                if 'Cannot parse witness' in line:
                    status += ' (invalid witness file)'
                elif 'Unsupported' in line:
                    if 'recursion' in line:
                        status += ' (recursion)'
                    elif 'threads' in line:
                        status += ' (threads)'
                elif 'Parsing failed' in line:
                    status += ' (parsing failed)'
            elif line.startswith('Invalid configuration: ') and not status:
                if 'Cannot parse witness' in line:
                    status = result.RESULT_ERROR
                    status += ' (invalid witness file)'
            elif line.startswith('For your information: CPAchecker is currently hanging at') and not status and isTimeout:
                status = 'TIMEOUT'

            elif line.startswith('Verification result: '):
                line = line[21:].strip()
                if line.startswith('TRUE'):
                    newStatus = result.RESULT_TRUE_PROP
                elif line.startswith('FALSE'):
                    newStatus = result.RESULT_FALSE_REACH
                    match = re.match('.* Property violation \(([^:]*)(:.*)?\) found by chosen configuration.*', line)
                    if match and match.group(1) in ['valid-deref', 'valid-free', 'valid-memtrack', 'no-overflow', 'no-deadlock', 'termination']:
                        newStatus = result.STR_FALSE + '(' + match.group(1) + ')'
                else:
                    newStatus = result.RESULT_UNKNOWN

                if not status:
                    status = newStatus
                elif newStatus != result.RESULT_UNKNOWN:
                    status = "{0} ({1})".format(status, newStatus)

        if (not status or status == result.RESULT_UNKNOWN) and isTimeout and returncode in [15, 143]:
            # The JVM sets such an returncode if it receives signal 15
            # (143 is 15+128)
            status = 'TIMEOUT'

        if not status:
            status = result.RESULT_ERROR
        return status


    def get_value_from_output(self, lines, identifier):
        # search for the text in output and get its value,
        # stop after the first line, that contains the searched text
        for line in lines:
            if identifier in line:
                startPosition = line.find(':') + 1
                endPosition = line.find('(', startPosition) # bracket maybe not found -> (-1)
                if (endPosition == -1):
                    return line[startPosition:].strip()
                else:
                    return line[startPosition: endPosition].strip()
        return None

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        return '3.9.1'

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
        """passes = []
        if not self._options.explicit_symbolic:
            passes.append('-initialize-uninitialized')

        return passes"""
        return []

    def prepare_after(self):
        """
        Same as prepare, but runs after slicing
        """
        return ["-reg2mem"]
