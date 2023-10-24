from os.path import abspath, dirname, join as pathjoin
from os import listdir
from shutil import copy as copyfile
from symbiotic.utils.utils import dbg, print_stdout
from symbiotic.witnesses.witnesses import GraphMLWriter
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

    def __init__(self, opts, bself=False):
        SymbioticBaseTool.__init__(self, opts)
        self._bself = bself

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
        cmd = [exe, '-se-exit-on-error', '-se-replay-errors',
               '-only-tests=err', arch]
        if prp.unreachcall():
            funs = ','.join(prp.getcalls())
            cmd.append(f'-error-fn={funs}')
        if self._options.sv_comp:
            cmd.append('-svcomp-witness')
        cmd.extend(options)
        if '-bself' in cmd:
            cmd.append('-forbid-floats')
            cmd.append('-unsupported-undefs=__VERIFIER_nondet_float,__VERIFIER_nondet_double')
        return cmd + tasks

    def set_environment(self, env, opts):
        """ Set environment for the tool """

        # do not link any functions
        opts.linkundef = []
        env.prepend('LD_LIBRARY_PATH', '{0}/slowbeast/'.\
                        format(env.symbiotic_dir))
        env.reset('PYTHONOPTIMIZE', '1')

        if opts.devel_mode:
            # look for slowbeast in the symbiotic's directory
            env.prepend('PATH', '{0}/slowbeast'.format(env.symbiotic_dir))
            env.prepend('PYTHONPATH', '{0}/slowbeast/llvmlite'.format(env.symbiotic_dir))

    def passes_before_slicing(self):
        if self._options.property.termination():
            return ['-find-exits']
        return []

    def passes_before_verification(self):
        """
        Passes that should run before slowbeast
        """
       # prp = self._options.property
       #passes += ["-lowerswitch", "-simplifycfg", "-reg2mem", "-simplifycfg"]
        #, "-ainline"]
        # passes.append("-ainline-noinline")
        # FIXME: get rid of the __VERIFIER_assert hack
       #if prp.unreachcall():
       #    passes.append(",".join(prp.getcalls())+f",__VERIFIER_assert,__VERIFIER_assume,assume_abort_if_not")
        passes = ["-lowerswitch", "-simplifycfg"]
        if self._bself:
            passes.append("-flatten-loops")
        return passes + ["-O3", "-remove-constant-exprs", "-reg2mem"]

    def generate_witness(self, llvmfile, sources, has_error):
        print_stdout('Generating {0} witness: {1}'\
                .format('violation' if has_error else 'correctness',
                        self._options.witness_output))

        sbdir = pathjoin(dirname(llvmfile), 'sb-out')
        witnesses = [abspath(pathjoin(sbdir, f)) for f in listdir(sbdir)
                     if f.endswith('.graphml')]

        assert len(sources) == 1
        gen = GraphMLWriter(sources[0],
                            self._options.property.ltl(),
                            self._options.is32bit,
                            not has_error)

        if len(witnesses) != 1:
            dbg("Do not have a unique witness in slowbeast output")
            gen.createTrivialWitness()
        else:
            gen.generate_witness(witnesses[0],
                                 self._options.property.termination())
        gen.write(self._options.witness_output)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return ''

        no_path_killed = False
        have_problem = False
        no_errors = False
        memerr = False
        asserterr = False
        for line in map(str, output):
            if '[assertion error]: unreachable' in line:
                continue # ignore assertions from unreachable
            if 'assertion failed!' in line:
                asserterr = True
            elif 'assertion failure' in line:
                asserterr = True
            elif '[assertion error]' in line:
                asserterr = True
            elif 'None: __VERIFIER_error called!' in line:
                asserterr = True
            elif 'Error found.' in line:
                no_errors = False
            elif '[memory error]' in line:
                memerr = True
            elif 'Killed paths: 0' in line:
                no_path_killed = True
            elif 'Did not extend the path and reached entry of CFG' in line or\
                 'a problem was met' in line or\
                 'Failed deciding the result.' in line:
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

    def set_environment(self, env, opts):
        env.prepend('PATH', '{0}/slowbeast'.format(env.symbiotic_dir, self.llvm_version()))
