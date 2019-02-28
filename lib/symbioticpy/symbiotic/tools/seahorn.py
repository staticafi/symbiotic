try:
    from benchexec.tools.seahorn import Tool as SeaTool
except ImportError:
    from .. utils import dbg
    dbg('Using the fallback tool module')
    from .. benchexec.tools.seahorn import Tool as SeaTool

class SymbioticTool(SeaTool):

    REQUIRED_PATHS = SeaTool.REQUIRED_PATHS

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

    def compilation_options(self):
        return ['-D__SEAHORN__','-fgnu89-inline']

    def slicer_options(self):
        """
        Returns tuple (c, opts) where c is the slicing
        criterion and opts is a list of options
        """

        if self._options.property.memsafety():
            # default config file is 'config.json'
            # slice with respect to the memory handling operations
            return ('__INSTR_mark_pointer,__INSTR_mark_free,__INSTR_mark_allocation',
                    ['-criteria-are-next-instr'])

        elif self._options.property.memcleanup():
            # default config file is 'config.json'
            # slice with respect to the memory handling operations
            return ('__INSTR_mark_free,__INSTR_mark_allocation',
                    ['-criteria-are-next-instr'])

        return (self._options.slicing_criterion,[])

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []

