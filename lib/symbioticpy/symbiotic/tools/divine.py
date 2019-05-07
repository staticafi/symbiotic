try:
    from benchexec.tools.divine4 import Tool as DivineTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.divine4 import Tool as DivineTool

from . tool import SymbioticBaseTool

class SymbioticTool(DivineTool, SymbioticBaseTool):
    """
    DIVINE integrated into Symbiotic
    """

    REQUIRED_PATHS = DivineTool.REQUIRED_PATHS

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._memsafety = self._options.property.memsafety()

    def llvm_version(self):
        return '6.0.1'

    def set_environment(self, env, opts):
        """
        Set environment for the tool
        """
        if opts.devel_mode:
            env.prepend('PATH', '{0}/divine'.\
                        format(env.symbiotic_dir))

    def cc(self):
        #return ['divine', 'cc']
        return ['clang', '--target=x86_64-unknown-none-elf']

    def actions_before_slicing(self, symbiotic):
        symbiotic.link_undefined(['__VERIFIER_atomic_begin',
                                  '__VERIFIER_atomic_end'])

   # not needed anymore?
   #def actions_before_verification(self, symbiotic):
   #    # link the DiOS environment
   #    newfile = symbiotic.curfile[:-3] + '-cc' + symbiotic.curfile[-3:]
   #    symbiotic.command(['divine', 'cc', symbiotic.curfile, '-o', newfile])
   #    symbiotic.curfile = newfile

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        return DivineTool.cmdline(self, executable, options, tasks, propertyfile, rlimits)

