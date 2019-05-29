try:
    from benchexec.tools.smack import Tool as SmackTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.smack import Tool as SmackTool

from . tool import SymbioticBaseTool

class SymbioticTool(SmackTool, SymbioticBaseTool):
    """
    SMACK integrated into Symbiotic
    """

    REQUIRED_PATHS = SmackTool.REQUIRED_PATHS

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._memsafety = self._options.property.memsafety()

    def llvm_version(self):
        return '3.9.1'

    def set_environment(self, env, opts):
        """
        Set environment for the tool
        """
        if opts.devel_mode:
            env.prepend('PATH', '{0}/smack'.\
                        format(env.symbiotic_dir))

        # do not link any functions
        opts.linkundef = []

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        cmd = SmackTool.cmdline(self, executable, options, tasks, propertyfile, rlimits)
        if self._options.is32bit:
            cmd.append("--clang-options=-m32")
        return cmd

