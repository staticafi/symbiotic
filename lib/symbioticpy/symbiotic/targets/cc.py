from os.path import join, abspath

from . tool import SymbioticBaseTool

try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='8.0.1'

class CCTarget(SymbioticBaseTool):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)

    def name(self):
        return 'cc'

    def llvm_version(self):
        return llvm_version

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """
        if self._options.generate_c:
            output = self._options.final_output or\
                     join(self._options.env.symbiotic_dir, 'symbiotic-output.c')
            return ['gen-c', '-o', output] + options + tasks

        output = self._options.final_output or\
                 join(self._options.env.symbiotic_dir, 'symbiotic-output.ll')
        return ['llvm-dis', '-o', output] + options + tasks

