try:
    from benchexec.tools.divine4 import Tool as DivineTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.divine4 import Tool as DivineTool

class SymbioticTool(DivineTool):
    """
    DIVINE integrated into Symbiotic
    """

    REQUIRED_PATHS = DivineTool.REQUIRED_PATHS

    def __init__(self, opts):
        self._options = opts
        self._memsafety = self._options.property.memsafety()

    def llvm_version(self):
        return '5.0.2'

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


    def set_environment(self, env, opts):
        """
        Set environment for the tool
        """
        if opts.devel_mode:
            env.prepend('PATH', '{0}/divine'.\
                        format(env.symbiotic_dir))


    def actions_before_verification(self, symbiotic):
        # link the DiOS environment
        symbiotic.command(['divine', 'cc', symbiotic.llvmfile])

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        return DivineTool.cmdline(self, executable, options, tasks, propertyfile, rlimits)

