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
        self._memsafety = 'MEMSAFETY' in self._options.prp

    def llvm_version(self):
        return '3.8.1'

    def slicer_options(self):
        """
        Returns tuple (c, opts) where c is the slicing
        criterion and opts is a list of options
        """

        if self._memsafety:
            # default config file is 'config.json'
            # slice with respect to the memory handling operations
            return ('__INSTR_mark_pointer', ['-criteria-are-next-instr'])

        return (self._options.slicing_criterion,[])

