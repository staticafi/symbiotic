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

    def name(self):
        return 'slowbeast'

    def llvm_version(self):
        return llvm_version

    def executable(self):
        return util.find_executable('sb', 'slowbeast/sb')

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        prp = self._options.property
        assert prp.unreachcall() or prp.termination()

        arch = '-pointer-bitwidth={0}'.format(32 if self._options.is32bit else 64)
        cmd = ['sb', '-se-exit-on-error', arch]
        if prp.unreachcall():
            funs = ','.join(prp.getcalls())
            cmd.append('-error-fn={funs}')
        return cmd + options + tasks

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []

    def passes_before_slicing(self):
        if self._options.property.termination():
            return ['-find-exits']
        return []

    def passes_before_verification(self):
        """
        Passes that should run before CPAchecker
        """
        prp = self._options.property
        passes = []
        if prp.termination():
            passes.append('-instrument-nontermination')
            passes.append('-instrument-nontermination-mark-header')

        passes += ["-lowerswitch", "-simplifycfg", "-reg2mem",
                   "-simplifycfg", "-ainline"]
        if prp.unreachcall():
            passes.append("-ainline-noinline")
            # FIXME: get rid of the __VERIFIER_assert hack
            passes.append(",".join(prp.getcalls())+f",__VERIFIER_assert")
        return passes + ["-O3", "-reg2mem"]

    def actions_before_verification(self, symbiotic):
        symbiotic.optimize(['-O3'])

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return ''

        no_path_killed = False
        have_problem = False
        no_errors = False
        found_error = False
        for line in output:
            if 'assertion failed!' in line:
                found_error = True
            elif 'assertion failure:' in line:
                found_error = True
            elif 'None: __VERIFIER_error called!' in line:
                found_error = True
            elif 'Error found.' in line:
                found_error = True
            elif 'Killed paths: 0' in line:
                no_path_killed = True
            elif 'Did not extend the path and reached entry of CFG' in line or\
                 'a problem was met' in line:
                 have_problem = True
            elif 'Found errors: 0' in line:
                no_errors = True

        if found_error and not no_errors:
            if self._options.property.termination():
                return result.RESULT_FALSE_TERMINATION
            return result.RESULT_FALSE_REACH
        if no_errors and no_path_killed and not have_problem:
            return result.RESULT_TRUE_PROP
        if returncode != 0 or returnsignal:
            return result.RESULT_ERROR
        return result.RESULT_UNKNOWN
