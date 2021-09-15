import os
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

class SymbioticTool(BaseTool, SymbioticBaseTool):

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._memsafety = self._options.property.memsafety()

    def llvm_version(self):
        return '10.0.1'

    def executable(self):
        return util.find_executable('sea', os.path.join("bin", 'sea'))

    def compilation_options(self):
        return ['-D__SEAHORN__', '-O1', '-Xclang',
                '-disable-llvm-optzns', '-fgnu89-inline']

    def actions_before_verification(self, symbiotic):
        prp = self._options.property
        if not (prp.unreachcall() or prp.assertions()):
            return
        for fun in self._options.property.getcalls():
            symbiotic.run_opt(['-replace-asserts',
                               f'-replace-asserts-fn={fun}'])

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        prp = self._options.property

        cmd = ['sea']
        if prp.unreachcall() or prp.assertions():
            cmd.append('pf')
        elif prp.memsafety():
            cmd.append('smc')
        elif prp.termination():
            cmd.append('term')
        cmd += ['--track=mem', '--horn-stats',
                '-m32' if self._options.is32bit else '-m64',
                '--step=large'] + options + tasks
        return cmd
       #return ['sea', '--mem=-1', '-m32', 'pf', '--step=large', '-g',
       #        '--horn-global-constraints=true', '--track=mem',
       #        '--horn-stats', '--enable-nondet-init', '--strip-extern',
       #        '--externalize-addr-taken-functions', '--horn-singleton-aliases=true',
       #        '--horn-pdr-contexts=600', '--devirt-functions',
       #        '--horn-ignore-calloc=false', '--enable-indvar',
       #        '--horn-answer', '--inline'] + options + tasks

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(map(str, output))
        if "BRUNCH_STAT Result TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "BRUNCH_STAT Result FALSE" in output:
            if "BRUNCH_STAT Termination" in output:
                status = result.RESULT_FALSE_TERMINATION
            else:
                status = result.RESULT_FALSE_REACH
        elif "BRUNCH_STAT Result UNKNOWN" in output:
            status = result.RESULT_UNKNOWN
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
