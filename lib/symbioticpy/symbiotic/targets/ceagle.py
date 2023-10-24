from symbiotic.utils.process import runcmd
from symbiotic.utils.watch import DbgWatch

try:
    from benchexec.tools.ceagle import Tool as CeagleTool
except ImportError:
    from .. benchexec.tools.ceagle import Tool as CeagleTool

class SymbioticTool(CeagleTool):

    REQUIRED_PATHS = CeagleTool.REQUIRED_PATHS

    def __init__(self, opts):
        pass

    def llvm_version(self):
        return '3.8.1'

    def actions_before_verification(self, symbiotic):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        output = symbiotic.curfile + '.ll'
        runcmd(['llvm-dis', symbiotic.curfile, '-o', output], DbgWatch('all'))
        symbiotic.curfile = output

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []

