from os.path import abspath
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
    llvm_version='10.0.1'

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

        exe = abspath(self.executable())
        arch = '-pointer-bitwidth={0}'.format(32 if self._options.is32bit else 64)
        cmd = [exe, '-se-exit-on-error', '-se-replay-errors', arch]
        if prp.unreachcall():
            funs = ','.join(prp.getcalls())
            cmd.append(f'-error-fn={funs}')
        return cmd + options + tasks

    def set_environment(self, env, opts):
        """ Set environment for the tool """

        # do not link any functions
        opts.linkundef = []
        env.prepend('LD_LIBRARY_PATH', '{0}/slowbeast/'.\
                        format(env.symbiotic_dir))
        env.reset('PYTHONOPTIMIZE', '1')

    def passes_before_slicing(self):
        if self._options.property.termination():
            return ['-find-exits']
        return []

    def passes_before_verification(self):
        """
        Passes that should run before slowbeast
        """
        prp = self._options.property
        passes = []
        if prp.termination():
            passes.append('-instrument-nontermination')
            passes.append('-instrument-nontermination-mark-header')

        passes += ["-lowerswitch", "-simplifycfg", "-reg2mem",
                   "-simplifycfg", "-ainline"]
        passes.append("-ainline-noinline")
        # FIXME: get rid of the __VERIFIER_assert hack
        if prp.unreachcall():
            passes.append(",".join(prp.getcalls())+f",__VERIFIER_assert")
        return passes + ["-O3", "-remove-constant-exprs", "-reg2mem"]

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return ''

        no_path_killed = False
        have_problem = False
        no_errors = False
        memerr = False
        asserterr = False
        for line in output:
            if 'assertion failed!' in line:
                asserterr = True
            elif 'assertion failure:' in line:
                asserterr = True
            elif 'None: __VERIFIER_error called!' in line:
                asserterr = True
            elif 'memory error - uninitialized read' in line:
                memerr = True
            elif 'Killed paths: 0' in line:
                no_path_killed = True
            elif 'Did not extend the path and reached entry of CFG' in line or\
                 'a problem was met' in line:
                 have_problem = True
            elif 'Found errors: 0' in line:
                no_errors = True

        if not no_errors:
            if asserterr:
                if self._options.property.termination():
                    return result.RESULT_FALSE_TERMINATION
                return result.RESULT_FALSE_REACH
            elif memerr:
                return f"{result.RESULT_UNKNOWN}(uninit mem)"
                # we do not support memsafety yet...
                #return result.RESULT_FALSE_DEREF
            else:
                return f"{result.RESULT_UNKNOWN}(unknown-err)"
        if no_errors and no_path_killed and not have_problem:
            return result.RESULT_TRUE_PROP
        if returncode != 0:
            return f"{result.RESULT_ERROR}(returned {returncode})"
        if returnsignal:
            return f"{result.RESULT_ERROR}(signal {returnsignal})"
        return result.RESULT_UNKNOWN
