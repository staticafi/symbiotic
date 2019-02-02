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

import re

try:
    import benchexec.util as util
    import benchexec.result as result
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result

from . kleebase import SymbioticTool as KleeBase

from os import listdir
from os.path import join

def has_tests(working_dir):
    for f in listdir(join(working_dir, 'klee-last')):
        if f.endswith('.ktest'):
            return True
    return False

class SymbioticTool(KleeBase):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        KleeBase.__init__(self, opts)

    def actions_after_compilation(self, symbiotic):
        if symbiotic.options.property.signedoverflow() and \
           not symbiotic.options.overflow_with_clang:
            symbiotic.link_undefined()

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """

        cmd = [executable, '-write-paths',
               '-output-stats=0', '-disable-opt',
               '-only-output-states-covering-new=1',
               '-max-memory=7000000']

        if self._options.property.errorcall():
            cmd.append('-exit-on-error-type=Assert')
            cmd.append('-dump-states-on-halt=0')
        else:
            cmd.append('-max-time=840')

        return cmd + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if has_tests(self._options.environment.working_dir):
            return result.RESULT_DONE

        return result.RESULT_UNKNOWN
