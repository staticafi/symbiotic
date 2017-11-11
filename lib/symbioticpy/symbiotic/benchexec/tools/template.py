# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging
import subprocess

import benchexec.result as result
import benchexec.util as util

class BaseTool(object):
    """
    This class serves both as a template for tool-info implementations,
    and as an abstract super class for them.
    For writing a new tool info, inherit from this class and override
    the necessary methods (always executable(), name(), and determine_result(),
    maybe version(), cmdline(), working_directory(), and get_value_from_output(), too).
    The class for each specific tool need to be named "Tool".
    For more information, please refer to
    https://github.com/sosy-lab/benchexec/blob/master/doc/tool-integration.md
    """

    REQUIRED_PATHS = []

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        @return a string pointing to an executable file
        """
        return util.find_executable('tool')


    def program_files(self, executable):
        """
        OPTIONAL, this method is only necessary for situations when the benchmark environment
        needs to know all files belonging to a tool
        (to transport them to a cloud service, for example).
        Returns a list of files or directories that are necessary to run the tool,
        relative to the current directory.
        @return a list of paths as strings
        """
        installDir = os.path.dirname(executable)
        return [executable] + util.flatten(util.expand_filename_pattern(path, installDir) for path in self.REQUIRED_PATHS)


    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        Do not hard-code a version in this function, either extract the version
        from the tool or do not return a version at all.
        There is a helper function `self._version_from_tool`
        that should work with most tools, you only need to extract the version number
        from the returned tool output.
        @return a (possibly empty) string
        """
        return ''

    def _version_from_tool(self, executable, arg='--version', use_stderr=False):
        """
        Get version of a tool by executing it with argument "--version"
        and returning stdout.
        @param executable: the path to the executable of the tool (typically the result of executable())
        @param arg: an argument to pass to the tool to let it print its version
        @param use_stderr: True if the tool prints version on stderr, False for stdout
        @return a (possibly empty) string of output of the tool
        """
        try:
            process = subprocess.Popen([executable, arg],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = process.communicate()
        except OSError as e:
            logging.warning('Cannot run {0} to determine version: {1}'.
                            format(executable, e.strerror))
            return ''
        if stderr and not use_stderr:
            logging.warning('Cannot determine {0} version, error output: {1}'.
                            format(executable, util.decode_to_string(stderr)))
            return ''
        if process.returncode:
            logging.warning('Cannot determine {0} version, exit code {1}'.
                            format(executable, process.returncode))
            return ''
        return util.decode_to_string(stderr if use_stderr else stdout).strip()


    def name(self):
        """
        Return the name of the tool, formatted for humans.
        This function should always be overriden.
        @return a non-empty string
        """
        return 'UNKOWN'


    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the inputfile to analyze.
        This method can get overridden, if, for example, some options should
        be enabled or if the order of arguments must be changed.

        All paths passed to this method (executable, tasks, and propertyfile)
        are either absolute or have been made relative to the designated working directory.

        @param executable: the path to the executable of the tool (typically the result of executable())
        @param options: a list of options, in the same order as given in the XML-file.
        @param tasks: a list of tasks, that should be analysed with the tool in one run.
                            A typical run has only one input file, but there can be more than one.
        @param propertyfile: contains a specification for the verifier (optional, not always present).
        @param rlimits: This dictionary contains resource-limits for a run,
                        for example: time-limit, soft-time-limit, hard-time-limit, memory-limit, cpu-core-limit.
                        All entries in rlimits are optional, so check for existence before usage!
        @return a list of strings that represent the command line to execute
        """
        return [executable] + options + tasks


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        @param returncode: the exit code of the program, 0 if the program was killed
        @param returnsignal: the signal that killed the program, 0 if program exited itself
        @param output: a list of strings of output lines of the tool (both stdout and stderr)
        @param isTimeout: whether the result is a timeout
        (useful to distinguish between program killed because of error and timeout)
        @return a non-empty string, usually one of the benchexec.result.RESULT_* constants
        """
        return result.RESULT_UNKNOWN


    def get_value_from_output(self, lines, identifier):
        """
        OPTIONAL, extract a statistic value from the output of the tool.
        This value will be added to the resulting tables.
        It may contain HTML code, which will be rendered appropriately in the HTML tables.
        @param lines: The output of the tool as list of lines.
        @param identifier: The user-specified identifier for the statistic item.
        @return a (possibly empty) string, optional with HTML tags
        """


    def working_directory(self, executable):
        """
        OPTIONAL, this method is only necessary for situations
        when the tool needs a separate working directory.
        @param executable: the path to the executable of the tool (typically the result of executable())
        @return a string pointing to a directory
        """
        return os.curdir


    def environment(self, executable):
        """
        OPTIONAL, this method is only necessary for tools
        that needs special environment variable, such as a modified PATH.
        However, for usability of the tool it is in general not recommended to require
        additional variables (tool uses outside of BenchExec would need to have them specified
        manually), but instead change the tool such that it does not need additional variables.
        For example, instead of requiring the tool directory to be added to PATH,
        the tool can be changed to call binaries from its own directory directly.
        This also has the benefit of not confusing bundled binaries
        with existing binaries of the system.

        Note that when executing benchmarks under a separate user account (with flag --user),
        the environment of the tool is a fresh almost-empty one.
        This function can be used to set some variables.

        Note that runexec usually overrides the environment variable $HOME and sets it to a fresh
        directory. If your tool relies on $HOME pointing to the real home directory,
        you can use the result of this function to overwrite the value specified by runexec.
        This is not recommended, however, because it means that runs may be influenced
        by files in the home directory, which hinders reproducibility.

        This method returns a dict that contains several further dicts.
        All keys and values have to be strings.
        Currently we support 3 identifiers in the outer dict:

        "keepEnv": If specified, the run gets initialized with a fresh environment and only
                  variables listed in this dict are copied from the system environment
                  (the values in this dict are ignored).
        "newEnv": Before the execution, the values are assigned to the real environment-identifiers.
                  This will override existing values.
        "additionalEnv": Before the execution, the values are appended to the real environment-identifiers.
                  The seperator for the appending must be given in this method,
                  so that the operation "realValue + additionalValue" is a valid value.
                  For example in the PATH-variable the additionalValue starts with a ":".
        @param executable: the path to the executable of the tool (typically the result of executable())
        @return a possibly empty dict with three possibly empty dicts with environment variables in them
        """
        return {}
