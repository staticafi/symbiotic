"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2019-2021  Marek Chalupa
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

try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='10.0.1'

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
        self._memsafety = opts.property.memsafety()
        self._use_llvm_backend = False

        opts.explicit_symbolic = True

        if opts.target_settings:
            if 'use-llvm-backend' in opts.target_settings:
                self._use_llvm_backend = True

    def executable(self):
        executable = util.find_executable('cpa.sh', 'scripts/cpa.sh')
        executableDir = os.path.join(os.path.dirname(executable), os.path.pardir)
        if not os.path.isfile(os.path.join(executableDir, "cpachecker.jar")):
            logging.warning("Required JAR file for CPAchecker not found in {0}.".format(executableDir))
        return executable

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

       #if ("-stats" not in existing_options):
       #    options = options + ["-stats"]

        spec = ["-spec", propertyfile] if propertyfile is not None else []

        return options + spec

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        additional_options = self._get_additional_options(options, propertyfile, rlimits)
        # use a default configuration if no other is specicied
        if not options:
            config_paths = os.path.join(os.path.dirname(executable), '..', 'config')
            additional_options += ['-svcomp21', '-heap', '10000M', '-benchmark',
                                   '-timelimit', '900s']
        if self._options.is32bit:
            additional_options.append('-32')
        else:
            additional_options.append('-64')

        if self._use_llvm_backend:
            additional_options += ["-setprop", "language=LLVM"]
        return [executable] + options + additional_options + tasks


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        @param returncode: code returned by CPAchecker
        @param returnsignal: signal, which terminated CPAchecker
        @param output: the output of CPAchecker
        @return: status of CPAchecker after executing a run
        """
        def isOutOfNativeMemory(line):
            return (
                "std::bad_alloc" in line  # C++ out of memory exception (MathSAT)
                or "Cannot allocate memory" in line
                or "Native memory allocation (malloc) failed to allocate" in line  # JNI
                or line.startswith("out of memory")  # CuDD
            )

        status = None

        for line in map(str, output):
            if "java.lang.OutOfMemoryError" in line:
                status = "OUT OF JAVA MEMORY"
            elif isOutOfNativeMemory(line):
                status = "OUT OF NATIVE MEMORY"
            elif (
                "There is insufficient memory for the Java Runtime Environment to continue."
                in line
                or "cannot allocate memory for thread-local data: ABORT" in line
            ):
                status = "OUT OF MEMORY"
            elif "SIGSEGV" in line:
                status = "SEGMENTATION FAULT"
            elif "java.lang.AssertionError" in line:
                status = "ASSERTION"
            elif (
                ("Exception:" in line or line.startswith("Exception in thread"))
                # ignore "cbmc error output: ... Minisat::OutOfMemoryException"
                and not line.startswith("cbmc")
            ):
                status = "EXCEPTION"
            elif "Could not reserve enough space for object heap" in line:
                status = "JAVA HEAP ERROR"
            elif line.startswith("Error: ") and not status:
                status = result.RESULT_ERROR
                if "Cannot parse witness" in line:
                    status += " (invalid witness file)"
                elif "Unsupported" in line:
                    if "recursion" in line:
                        status += " (recursion)"
                    elif "threads" in line:
                        status += " (threads)"
                elif "Parsing failed" in line:
                    status += " (parsing failed)"
                elif "Interpolation failed" in line:
                    status += " (interpolation failed)"
            elif line.startswith("Invalid configuration: ") and not status:
                if "Cannot parse witness" in line:
                    status = result.RESULT_ERROR
                    status += " (invalid witness file)"
            elif (
                line.startswith(
                    "For your information: CPAchecker is currently hanging at"
                )
                and not status
                and isTimeout
            ):
                status = "TIMEOUT"

            elif "Verification result: " in line:
                line = line[21:].strip()
                if "TRUE" in line:
                    newStatus = result.RESULT_TRUE_PROP
                elif "FALSE" in line:
                    newStatus = result.RESULT_FALSE_PROP
                    match = re.match(
                        r".* Property violation \(([a-zA-Z0-9_-]+)(:.*)?\) found by chosen configuration.*",
                        line,
                    )
                    if match:
                        newStatus += f"({match.group(1)})"
                else:
                    newStatus = result.RESULT_UNKNOWN

                if not status:
                    status = newStatus
                elif newStatus != result.RESULT_UNKNOWN and status != newStatus:
                    status = f"{status} ({newStatus})"
                break # we got the result, ignore rest
            elif line == "Finished." and not status:
                status = result.RESULT_DONE

        if (
            (not status or status == result.RESULT_UNKNOWN)
            and isTimeout
            and returncode in [15, 143]
        ):
            # The JVM sets such an returncode if it receives signal 15 (143 is 15+128)
            status = "TIMEOUT"

        if not status:
            status = result.RESULT_ERROR
        return status

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        if self._use_llvm_backend:
            return '3.9.1'
        else:
            return llvm_version

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []


    def slicer_options(self):
        """ Override slicer options: do not slice bodies of funs
            that are slicing criteria. CBMC uses the assertions inside,
            not the calls themselves.
        """
        prp = self._options.property
        if not self._options.full_instrumentation and prp.signedoverflow():
            return (['__symbiotic_check_overflow'], ['-criteria-are-next-instr'])
        if prp.termination():
            return (['__VERIFIER_exit'], ['-cda=ntscd-legacy'])

        return super().slicer_options()

    def instrumentation_options(self):
        """
        Returns a triple (d, c, l, x) where d is the directory
        with configuration files, c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        prp = self._options.property
        if not self._options.full_instrumentation and prp.signedoverflow():
            return ('int_overflows',
                    self._options.overflow_config_file or 'config-marker.json',
                    'overflows-marker.c', False)
        if prp.termination():
            # we do not want any instrumentation here
            return (None, None, None, None)
        return super().instrumentation_options()

    def passes_before_verification(self):
        """
        Passes that should run before CPAchecker
        """
        # LLVM backend in CPAchecker does not handle switches correctly yet
        # and llvm2c has a bug with PHI nodes (which are not handled by the LLVM backend either)
        return super().passes_before_verification() +\
                ["-lowerswitch", "-simplifycfg", "-reg2mem", "-simplifycfg"]

    def actions_before_verification(self, symbiotic):
        # link our specific funs
        self._options.linkundef = ['verifier']
        symbiotic.link_undefined(only_func=['__VERIFIER_silent_exit','__VERIFIER_exit'])
        self._options.linkundef = []

        if self._use_llvm_backend:
            return

        output = symbiotic.curfile + '.c'
        runcmd(['llvm2c', symbiotic.curfile,
                '--no-function-call-casts', '--o', output], DbgWatch('all'))
        symbiotic.curfile = output
