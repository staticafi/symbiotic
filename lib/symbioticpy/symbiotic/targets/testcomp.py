"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2016-2020  Marek Chalupa
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

from symbiotic.utils.utils import process_grep
from symbiotic.utils import dbg
from symbiotic.exceptions import SymbioticException

try:
    import benchexec.util as util
    import benchexec.result as result
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result
    from symbiotic.benchexec.tools.template import BaseTool


from . tool import SymbioticBaseTool

try:
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    from symbiotic.benchexec.tools.template import BaseTool

from . klee import SymbioticTool as KleeTool

class SymbioticTool(KleeTool):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        super().__init__(opts)

    def name(self):
        return 'svcomp' # if renamed, adjust models in lib\ folder

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable('kleetester.py', 'bin/kleetester.py',
                                    'scripts/kleetester.py')


    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        assert len(tasks) == 1
        prp = 'coverage'
        prop = self._options.property
        iserr = prop.errorcall()
        if iserr:
            calls = [x for x in prop.getcalls() if x not in ['__VERIFIER_error', '__assert_fail']]
            if len(calls) == 1:
                prp = calls[0]
 

        return [executable, prp, self._options.testsuite_output] + tasks


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        return result.RESULT_DONE

