try:
    from benchexec.tools.map2check import Tool as Map2CheckTool
except ImportError:
    from symbiotic.benchexec.tools.map2check import Tool as Map2CheckTool

class SymbioticTool(Map2CheckTool):
    """
    Map2Check integrated into Symbiotic
    """

    REQUIRED_PATHS = Map2CheckTool.REQUIRED_PATHS

    def __init__(self, opts):
        self._options = opts

    def llvm_version(self):
        return '6.0.1'

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []

