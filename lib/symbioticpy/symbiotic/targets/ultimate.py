"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2015  Daniel Dietsch
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

import functools
import logging
import os
import re
import subprocess
import sys

try:
    import benchexec.result as result
    import benchexec.tools.template
    import benchexec.util as util
    from benchexec import BenchExecException
    from benchexec.model import MEMLIMIT
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.result as result
    import symbiotic.benchexec.tools.template
    import symbiotic.benchexec.util as util
    from symbiotic.benchexec.tools.template import BaseTool
    from symbiotic.exceptions import SymbioticException as BenchExecException
    MEMLIMIT = 10000

_OPTION_NO_WRAPPER = '--force-no-wrapper'
_SVCOMP17_VERSIONS = {"f7c3ed31"}
_SVCOMP17_FORBIDDEN_FLAGS = {"--full-output", "--architecture"}
_ULTIMATE_VERSION_REGEX = re.compile('^Version is (.*)$', re.MULTILINE)
# .jar files that are used as launcher arguments with most recent .jar first
_LAUNCHER_JARS = ["plugins/org.eclipse.equinox.launcher_1.3.100.v20150511-1540.jar"]


class UltimateTool(BaseTool):
    """
    Abstract tool info for Ultimate-based tools.
    """

    REQUIRED_PATHS = [
        "artifacts.xml",
        "config",
        "configuration",
        "cvc4",
        "cvc4nyu",
        "cvc4-LICENSE",
        "features",
        "LICENSE",
        "LICENSE.GPL",
        "LICENSE.GPL.LESSER",
        "mathsat",
        "mathsat-LICENSE",
        "p2",
        "plugins",
        "README",
        "Ultimate",
        "Ultimate.ini",
        "Ultimate.py",
        "z3",
        "z3-LICENSE"
    ]

    REQUIRED_PATHS_SVCOMP17 = []

    def __init__(self):
        self._uses_propertyfile = False

    def executable(self):
        return util.find_executable('Ultimate.py')
       #if not os.path.isfile(os.path.join(exe, '..', 'Ultimate')):
       #    sys.exit("ERROR: Could not find Ultimate executable in '{0}' or '{1}'".format(str(exe), str(os.getcwd())))
       #return exe

    def _ultimate_version(self, executable):
        data_dir = os.path.join(os.path.dirname(executable), 'data')
        launcher_jar = self._get_current_launcher_jar(executable)

        cmds = [
            # 2
            ["java", "-Xss4m", "-jar", launcher_jar, "-data", "@noDefault", "-ultimatedata", data_dir, "--version"],
            # 1
            ["java", "-Xss4m", "-jar", launcher_jar, "-data", data_dir, "--version"],
        ]

        self.api = len(cmds)
        for cmd in cmds:
            version = self._query_ultimate_version(cmd, self.api)
            if version != '':
                return version
            self.api = self.api - 1
        raise BenchExecException("Could not determine Ultimate version")

    def _query_ultimate_version(self, cmd, api):
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = process.communicate()
        except OSError as e:
            logging.warning('Cannot run Java to determine Ultimate version (API {0}): {1}'
                            .format(api, e.strerror))
            return ''
        if stderr:
            logging.warning('Cannot determine Ultimate version (API {0}). Error output: {1}'
                            .format(api, util.decode_to_string(stderr)))
            return ''
        if process.returncode:
            logging.warning(
                'Cannot determine Ultimate version (API {0}). Exit code : {1}\nCommand was {2}'
                    .format(api, process.returncode, ' '.join(cmd)))
            return ''

        version_ultimate_match = _ULTIMATE_VERSION_REGEX.search(util.decode_to_string(stdout))
        if not version_ultimate_match:
            logging.warning(
                'Cannot determine Ultimate version, output (API {0}): {1}'.format(api, util.decode_to_string(stdout)))
            return ''
        return version_ultimate_match.group(1)

    def _get_current_launcher_jar(self, executable):
        ultimatedir = os.path.dirname(executable)
        for jar in _LAUNCHER_JARS:
            launcher_jar = os.path.join(ultimatedir, jar)
            if os.path.isfile(launcher_jar):
                return launcher_jar
        raise FileNotFoundError('No suitable launcher jar found in {0}'.format(ultimatedir))

    def version(self, executable):
        wrapper_version = self._version_from_tool(executable)
        if wrapper_version in _SVCOMP17_VERSIONS:
            # Keep reported version number for old versions as they were before
            return wrapper_version

        ultimate_version = self._ultimate_version(executable)
        return ultimate_version + '-' + wrapper_version

    def _is_svcomp17_version(self, executable):
        return self.version(executable) in _SVCOMP17_VERSIONS

    def _requires_ultimate_data(self, executable):
        if self._is_svcomp17_version(executable):
            return False

        version = self.version(executable)
        ult, wrapper = version.split("-")
        major, minor, patch = ult.split(".")
        # all versions before 0.1.24 do not require ultimatedata
        return not (int(major) == 0 and int(minor) < 2 and int(patch) < 24)

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits=None):
        if rlimits is None:
            rlimits = {}

        self._uses_propertyfile = (propertyfile is not None)
        if _OPTION_NO_WRAPPER in options:
            # do not use old wrapper script even if property file is given
            self._uses_propertyfile = False
            propertyfile = None
            options.remove(_OPTION_NO_WRAPPER)

        if self._is_svcomp17_version(executable):
            assert propertyfile
            cmdline = [executable, propertyfile]

            cmdline += [option for option in options if option not in _SVCOMP17_FORBIDDEN_FLAGS]

            cmdline.append("--full-output")

            cmdline += tasks
            self.__assert_cmdline(cmdline, "cmdline contains empty or None argument when using SVCOMP17 mode: ")
            return cmdline

        if self._uses_propertyfile:
            # use the old wrapper script if a property file is given
            cmdline = [executable, '--spec', propertyfile]
            if tasks:
                cmdline += ['--file'] + tasks
            cmdline += options
            self.__assert_cmdline(cmdline, "cmdline contains empty or None argument when using default SVCOMP mode: ")
            return cmdline

        # if no property file is given and toolchain (-tc) is, use ultimate directly
        if '-tc' in options or '--toolchain' in options:
            # ignore executable (old executable is just around for backwards compatibility)
            mem_bytes = rlimits.get(MEMLIMIT, None)
            cmdline = ['java']

            # -ea has to be given directly to java
            if '-ea' in options:
                options = [e for e in options if e != '-ea']
                cmdline += ['-ea']

            if mem_bytes:
                cmdline += ['-Xmx' + str(mem_bytes)]
            cmdline += ['-Xss4m']
            cmdline += ['-jar', self._get_current_launcher_jar(executable)]

            if self._requires_ultimate_data(executable):
                if '-ultimatedata' not in options and '-data' not in options:
                    if self.api == 2:
                        cmdline += ['-data', '@noDefault', '-ultimatedata',
                                    os.path.join(os.path.dirname(executable), 'data')]
                    if self.api == 1:
                        raise ValueError('Illegal option -ultimatedata for API {} and Ultimate version {}'
                                         .format(self.api, self.version(executable)))
                elif '-ultimatedata' in options and '-data' not in options:
                    if self.api == 2:
                        cmdline += ['-data', '@noDefault']
                    if self.api == 1:
                        raise ValueError('Illegal option -ultimatedata for API {} and Ultimate version {}'
                                         .format(self.api, self.version(executable)))
            else:
                if '-data' not in options:
                    if self.api == 2 or self.api == 1:
                        cmdline += ['-data', os.path.join(os.path.dirname(executable), 'data')]

            cmdline += options

            if tasks:
                cmdline += ['-i'] + tasks
            self.__assert_cmdline(cmdline, "cmdline contains empty or None argument when using Ultimate raw mode: ")
            return cmdline

        # there is no way to run ultimate; not enough parameters
        raise NotImplemented(
            "Unsupported argument combination: options={} propertyfile={} rlimits={}".format(options, propertyfile,
                                                                                             rlimits))

    def __assert_cmdline(self, cmdline, msg):
        assert all(cmdline), msg + str(cmdline)
        pass

    def program_files(self, executable):
        install_dir = os.path.dirname(executable)
        paths = self.REQUIRED_PATHS_SVCOMP17 if self._is_svcomp17_version(executable) else self.REQUIRED_PATHS
        return [executable] + util.flatten(util.expand_filename_pattern(path, install_dir) for path in paths)

    def determine_result(self, returncode, returnsignal, output, is_timeout):
        if self._uses_propertyfile:
            return self._determine_result_with_propertyfile(returncode, returnsignal, output, is_timeout)
        return self._determine_result_without_propertyfile(returncode, returnsignal, output, is_timeout)

    def _determine_result_without_propertyfile(self, returncode, returnsignal, output, is_timeout):
        # special strings in ultimate output
        treeautomizer_sat = 'TreeAutomizerSatResult'
        treeautomizer_unsat = 'TreeAutomizerUnsatResult'
        unsupported_syntax_errorstring = 'ShortDescription: Unsupported Syntax'
        incorrect_syntax_errorstring = 'ShortDescription: Incorrect Syntax'
        type_errorstring = 'Type Error'
        witness_errorstring = 'InvalidWitnessErrorResult'
        exception_errorstring = 'ExceptionOrErrorResult'
        safety_string = 'Ultimate proved your program to be correct'
        all_spec_string = 'AllSpecificationsHoldResult'
        unsafety_string = 'Ultimate proved your program to be incorrect'
        mem_deref_false_string = 'pointer dereference may fail'
        mem_deref_false_string_2 = 'array index can be out of bounds'
        mem_free_false_string = 'free of unallocated memory possible'
        mem_memtrack_false_string = 'not all allocated memory was freed'
        termination_false_string = 'Found a nonterminating execution for the following ' \
                                   'lasso shaped sequence of statements'
        termination_true_string = 'TerminationAnalysisResult: Termination proven'
        ltl_false_string = 'execution that violates the LTL property'
        ltl_true_string = 'Buchi Automizer proved that the LTL property'
        overflow_false_string = 'overflow possible'

        for line in output:
            if line.find(unsupported_syntax_errorstring) != -1:
                return 'ERROR: UNSUPPORTED SYNTAX'
            if line.find(incorrect_syntax_errorstring) != -1:
                return 'ERROR: INCORRECT SYNTAX'
            if line.find(type_errorstring) != -1:
                return 'ERROR: TYPE ERROR'
            if line.find(witness_errorstring) != -1:
                return 'ERROR: INVALID WITNESS FILE'
            if line.find(exception_errorstring) != -1:
                return 'ERROR: EXCEPTION'
            if self._contains_overapproximation_result(line):
                return 'UNKNOWN: OverapproxCex'
            if line.find(termination_false_string) != -1:
                return 'FALSE(TERM)'
            if line.find(termination_true_string) != -1:
                return 'TRUE'
            if line.find(ltl_false_string) != -1:
                return 'FALSE(valid-ltl)'
            if line.find(ltl_true_string) != -1:
                return 'TRUE'
            if line.find(unsafety_string) != -1:
                return 'FALSE'
            if line.find(mem_deref_false_string) != -1:
                return 'FALSE(valid-deref)'
            if line.find(mem_deref_false_string_2) != -1:
                return 'FALSE(valid-deref)'
            if line.find(mem_free_false_string) != -1:
                return 'FALSE(valid-free)'
            if line.find(mem_memtrack_false_string) != -1:
                return 'FALSE(valid-memtrack)'
            if line.find(overflow_false_string) != -1:
                return 'FALSE(OVERFLOW)'
            if line.find(safety_string) != -1 or line.find(all_spec_string) != -1:
                return 'TRUE'
            if line.find(treeautomizer_unsat) != -1:
                return 'unsat'
            if line.find(treeautomizer_sat) != -1 or line.find(all_spec_string) != -1:
                return 'sat'

        return result.RESULT_UNKNOWN

    def _contains_overapproximation_result(self, line):
        triggers = [
            'Reason: overapproximation of',
            'Reason: overapproximation of bitwiseAnd',
            'Reason: overapproximation of bitwiseOr',
            'Reason: overapproximation of bitwiseXor',
            'Reason: overapproximation of shiftLeft',
            'Reason: overapproximation of shiftRight',
            'Reason: overapproximation of bitwiseComplement'
        ]

        for trigger in triggers:
            if line.find(trigger) != -1:
                return True

        return False

    def _determine_result_with_propertyfile(self, returncode, returnsignal, output, is_timeout):
        for line in output:
            if line.startswith('FALSE(valid-free)'):
                return result.RESULT_FALSE_FREE
            elif line.startswith('FALSE(valid-deref)'):
                return result.RESULT_FALSE_DEREF
            elif line.startswith('FALSE(valid-memtrack)'):
                return result.RESULT_FALSE_MEMTRACK
            elif line.startswith('FALSE(TERM)'):
                return result.RESULT_FALSE_TERMINATION
            elif line.startswith('FALSE(OVERFLOW)'):
                return result.RESULT_FALSE_OVERFLOW
            elif line.startswith('FALSE'):
                return result.RESULT_FALSE_REACH
            elif line.startswith('TRUE'):
                return result.RESULT_TRUE_PROP
            elif line.startswith('UNKNOWN'):
                return result.RESULT_UNKNOWN
            elif line.startswith('ERROR'):
                status = result.RESULT_ERROR
                if line.startswith('ERROR: INVALID WITNESS FILE'):
                    status += ' (invalid witness file)'
                return status
        return result.RESULT_UNKNOWN

    def get_value_from_output(self, lines, identifier):
        # search for the text in output and get its value,
        # stop after the first line, that contains the searched text
        for line in lines:
            if identifier in line:
                start_position = line.find('=') + 1
                return line[start_position:].strip()
        return None
