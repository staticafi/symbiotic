try:
    from benchexec.tools.smack import Tool as SmackTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.smack import Tool as SmackTool

class SymbioticTool(SmackTool):
    """
    SMACK integrated into Symbiotic
    """

    REQUIRED_PATHS = SmackTool.REQUIRED_PATHS

    def __init__(self, opts):
        self._options = opts
        self._memsafety = self._options.property.memsafety()

    def llvm_version(self):
        return '3.8.1'

    def instrumentation_options(self):
        """
        Returns a triple (c, l, x) where c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        if self._memsafety:
            # default config file is 'config.json'
            return ('config-marker.json', 'marker.c', False)

        return (None, None, None)

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



