
class SymbioticBaseTool(object):
    """
    Base class that describes settings of all tools
    integrated into the SymbioticVerifier.
    These can be overriden by the tools if needed
    """

    def __init__(self, opts):
        self._options = opts

    def compilation_options(self):
        """
        List of compilation options specific for the tool
        """
        opts = []
        if self._options.property.undefinedness():
            opts.append('-fsanitize=undefined')
            opts.append('-fno-sanitize=unsigned-integer-overflow')
        elif self._options.property.signedoverflow():
            opts.append('-fsanitize=signed-integer-overflow')
            opts.append('-fsanitize=shift')

        return opts

   # we run these passes for every tool
   #def passes_after_compilation(self):
   #    """
   #    LLVM passes that should be run on the code after the compilation.
   #    """
   #    # remove definitions of __VERIFIER_* that are not created by us,
   #    # make extern globals local, etc. Also remove syntactically infinite loops.
   #    passes = []

   #    if not self._options.property.termination():
   #        passes.append('-remove-infinite-loops')

   #    if self._options.property.undefinedness() or \
   #       self._options.property.signedoverflow():
   #        passes.append('-replace-ubsan')

   #    if self._options.property.signedoverflow() and \
   #       not self._options.overflow_with_clang:
   #        passes.append('-prepare-overflows')

   #    return passes


    def instrumentation_options(self):
        """
        Returns a triple (c, l, x) where c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        if self._options.full_instrumentation:
            if self._options.property.memsafety():
                # default config file is 'config.json'
                return (self._options.memsafety_config_file, 'memsafety.c', True)

            if self._options.property.signedoverflow():
                # default config file is 'config.json'
                return (self._options.overflow_config_file, 'overflows.c', True)

            if self._options.property.termination():
                return ('config.json', 'termination.c', True)

            if self._options.property.memcleanup():
                return ('config-memcleanup.json', 'memsafety.c', True)

            return (None, None, None)
        else:
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

        if self._options.full_instrumentation:
            # all is reachability
            return (self._options.slicing_criterion,[])

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

