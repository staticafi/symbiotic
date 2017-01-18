# -*- coding: utf-8 -*-

"""
SeaHorn Verification Framework
Copyright (c) 2015 Carnegie Mellon University.
All Rights Reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1. Redistributions of source code must retain the above copyright
notice, this list of conditions and the following acknowledgments and
disclaimers.

2. Redistributions in binary form must reproduce the
above copyright notice, this list of conditions and the following
acknowledgments and disclaimers in the documentation and/or other
materials provided with the distribution.

3. Products derived from this software may not include “Carnegie
Mellon University,” "SEI” and/or “Software Engineering Institute" in
the name of such derived product, nor shall “Carnegie Mellon
University,” "SEI” and/or “Software Engineering Institute" be used to
endorse or promote products derived from this software without prior
written permission. For written permission, please contact
permission@sei.cmu.edu.

ACKNOWLEDGMENTS AND DISCLAIMERS:

Copyright 2015 Carnegie Mellon University

This material is based upon work funded and supported by the
Department of Defense under Contract No. FA8721-05-C-0003 with
Carnegie Mellon University for the operation of the Software
Engineering Institute, a federally funded research and development
center. Moreover, this work is funded by NASA NRA Contract No. NNX14AI09G
and NSF Award No. 1422705

Any opinions, findings and conclusions or recommendations expressed in
this material are those of the author(s) and do not necessarily
reflect the views of the United States Department of Defense, NASA or NSF.

NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING
INSTITUTE MATERIAL IS FURNISHED ON AN “AS-IS” BASIS. CARNEGIE MELLON
UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR
IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF
FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS
OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT
MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT,
TRADEMARK, OR COPYRIGHT INFRINGEMENT.

This material has been approved for public release and unlimited
distribution.

DM-0002198
"""
import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

import os

class Tool(benchexec.tools.template.BaseTool):


    REQUIRED_PATHS = [
                  "bin",
                  "include",
                  "lib",
                  "share"
                  ]

    def executable(self):
        return util.find_executable('sea_svcomp', os.path.join("bin", 'sea_svcomp'))

    def program_files(self, executable):
        installDir = os.path.join(os.path.dirname(executable), os.path.pardir)
        return util.flatten(util.expand_filename_pattern(path, installDir) for path in self.REQUIRED_PATHS)

    def name(self):
        return 'SeaHorn-F16'

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        assert propertyfile is not None
        spec = ['--spec=' + propertyfile]
        return [executable] + options + spec + tasks

    def version(self, executable):
        return self._version_from_tool(executable)

    def llvm_version(self):
        return '3.6.2'

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
        output = '\n'.join(output)
        if "BRUNCH_STAT Result TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "BRUNCH_STAT Result FALSE" in output:
            if "BRUNCH_STAT Termination" in output:
                status = result.RESULT_FALSE_TERMINATION
            else:
                status = result.RESULT_FALSE_REACH
        elif returnsignal == 9 or returnsignal == (128+9):
            if isTimeout:
                status = "TIMEOUT"
            else:
                status = "KILLED BY SIGNAL 9"
        elif returncode != 0:
            status = "ERROR ({0})".format(returncode)
        else:
            status = 'FAILURE'

        return status
