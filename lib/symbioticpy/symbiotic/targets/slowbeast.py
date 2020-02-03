from .. utils import dbg
from . tool import SymbioticBaseTool

try:
    import benchexec.util as util
    import benchexec.result as result
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    import symbiotic.benchexec.result as result
    from symbiotic.benchexec.tools.template import BaseTool

try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='8.0.1'

class SymbioticTool(BaseTool, SymbioticBaseTool):

    REQUIRED_PATHS = ['sb', 'slowbeast']

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._memsafety = self._options.property.memsafety()

    def name(self):
        return 'slowbeast'

    def llvm_version(self):
        return llvm_version

    def executable(self):
        return util.find_executable('sb', 'slowbeast/sb')

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        assert self._options.property.assertions()

        return ['sb'] + options + tasks

    def passes_before_verification(self):
        """
        Passes that should run before CPAchecker
        """
        # LLVM backend in CPAchecker does not handle switches correctly yet
        # and llvm2c has a bug with PHI nodes (which are not handled by the LLVM backend either)
        return ["-lowerswitch", "-simplifycfg", "-reg2mem", "-simplifycfg"]

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        @param returncode: code returned by CPAchecker
        @param returnsignal: signal, which terminated CPAchecker
        @param output: the output of CPAchecker
        @return: status of CPAchecker after executing a run
        """
        if isTimeout:
            return ''

        no_path_killed = False
        for line in output:
            if b'Assertion failed: assertion failed!' in line:
                return result.RESULT_FALSE_REACH
            if b'Assertion failed: __VERIFIER_error called!' in line:
                return result.RESULT_FALSE_REACH
            elif b'Killed paths: 0' in line:
                no_path_killed = True
            elif b'Found errors: 0' in line and no_path_killed:
                return result.RESULT_TRUE_PROP
        if returncode != 0 or returnsignal:
            return result.RESULT_ERROR
        return result.RESULT_UNKNOWN
