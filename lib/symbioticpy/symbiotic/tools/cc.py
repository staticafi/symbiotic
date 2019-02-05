
class SymbioticTool:
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        self._options = opts

    def name(self):
        return 'cc'

    def llvm_version(self):
        return '7.0.1'

    def instrumentation_options(self):
        """
        Returns a triple (c, l, x) where c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        # NOTE: we do not want to link the functions with memsafety/cleanup
        # because then the optimizations could remove the calls to markers
        if self._options.property.memsafety():
            return ('config-marker.json', 'marker.c', False)

        if self._options.property.memcleanup():
            return ('config-marker-memcleanup.json', 'marker.c', False)

        if self._options.property.signedoverflow():
            # default config file is 'config.json'
            return (self._options.overflow_config_file, 'overflows.c', True)

        if self._options.property.termination():
            return ('config.json', 'termination.c', True)

        return (None, None, None)

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

    def executable(self):
        return 'true'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """
        if self._options.generate_c:
            output = self._options.final_output or 'symbiotic-output.c'
            return ['llvm-cbe', '-o', output] + options + tasks

        output = self._options.final_output or 'symbiotic-output.ll'
        return ['llvm-dis', '-o', output] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if returncode != 0 or returnsignal != 0:
            return 'error'
        return 'done'
