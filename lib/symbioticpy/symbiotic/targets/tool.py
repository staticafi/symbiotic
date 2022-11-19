
class SymbioticBaseTool(object):
    """
    Base class that describes settings of all tools
    integrated into the SymbioticVerifier.
    These can be overriden by the tools if needed
    """

    def __init__(self, opts):
        self._options = opts

    def executable(self):
        return 'true'

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if returncode != 0 or returnsignal != 0:
            return 'error'
        return 'done'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable
        """
        return [executable] + options + tasks

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

    def can_replay(self):
        """ Return true if the tool can do error replay """
        return False

    def verifiers(self):
        """
        Return an iterable of tool modules to run on the generated file.
        By default, it is this tool, but it can be several other tools
        (in which this Tool module serves to merge them together
        and describes how to generate the bitcode such that it can
        be run by all the tools)
        """
        # pairs (tool, params, timeout)
        return ((self, None, None),)

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
        Returns a triple (d, c, l, x) where d is the directory
        with configuration files, c is the configuration
        file for instrumentation (or None if no instrumentation
        should be performed), l is the
        file with definitions of the instrumented functions
        and x is True if the definitions should be linked after
        instrumentation (and False otherwise)
        """

        if self._options.property.signedoverflow() and\
             self._options.overflow_with_clang:
            # clang already instrumented all that we need
             return (None, None, None, None)

        if self._options.full_instrumentation:
            if self._options.property.memsafety():
                # default config file is 'config.json'
                return ('memsafety',
                        self._options.memsafety_config_file or 'config.json',
                        'memsafety.c', True)

            if self._options.property.signedoverflow():
                # default config file is 'config.json'
                return ('int_overflows',
                        self._options.overflow_config_file or 'config-no-assert.json',
                        'overflows-no-assert.c', True)

            if self._options.property.termination():
                return ('termination', 'config.json', 'termination.c', True)

            if self._options.property.memcleanup():
                return ('memsafety', 'config-memcleanup.json', 'memsafety.c', True)

            return (None, None, None, None)
        else:
            if self._options.property.signedoverflow():
                # default config file is 'config.json'
                return ('int_overflows',
                        self._options.overflow_config_file or 'config-no-assert.json',
                        'overflows-no-assert.c', True)

            if self._options.property.termination():
                return ('termination', 'config.json', 'termination.c', True)

            if self._options.property.nullderef():
                return ('null_deref', 'config.json', 'null_deref.c', False)

            if self._options.noslice:
                # no point in marking instructions without slicing
                return (None, None, None, None)
            # NOTE: we do not want to link the functions with memsafety/cleanup
            # because then the optimizations could remove the calls to markers
            if self._options.property.memsafety():
                return ('memsafety',
                        self._options.memsafety_config_file or 'config-marker.json',
                        'marker.c', False)

            if self._options.property.memcleanup():
                return ('memsafety', 'config-marker-memcleanup.json',
                        'marker.c', False)

            return (None, None, None, None)

    def slicer_options(self):
        """
        Returns tuple (c, opts) where c is a list with slicing
        criteria and opts is a list of options
        """

        if self._options.full_instrumentation:
            # all is reachability
            return (['__VERIFIER_error','__assert_fail'],[])

        prop = self._options.property
        if prop.memsafety() or prop.memcleanup():
            # slice with respect to the memory handling operations
            return (['__INSTR_mark_pointer','__INSTR_mark_free',
                    '__INSTR_mark_allocation','__INSTR_mark_exit'],
                    ['-memsafety'])

        if prop.termination():
            # have explicitly also __assert_fail, because otherwise it is going
            # to be sliced away from __INSTR_fail
            return (['__INSTR_fail','__assert_fail',
                     '__VERIFIER_silent_exit', '__VERIFIER_exit',
                     '__INSTR_check_assume'],
                    ['-cd-alg=ntscd-legacy'])

        if prop.nullderef():
            # slice with respect to the memory handling operations
            return (['__INSTR_mark_pointer'], ['-criteria-are-next-instr'])

        if prop.unreachcall():
            return (prop.getcalls(), [])

        if prop.errorcall():
            return (prop.getcalls(), [])

        if prop.signedoverflow() or prop.undefinedness():
            # default config file is 'config.json'
            # slice wrt asserts checking for the overflow
            return (['__VERIFIER_error'],[])

        return ([],[])

    def passes_before_slicing(self):
        if self._options.property.termination():
            return ['-find-exits', '-use-exit', '-no-change-assumes']
        return []

    def passes_after_slicing(self):
        """ By default, remove all inserted markers and so on in memsafety
             checking """

        if self._options.full_instrumentation:
            return []

        prop = self._options.property
        if prop.memsafety() or prop.memcleanup() or prop.nullderef():
            # slice with respect to the memory handling operations
            return (['-delete-calls',
                     '-delete-call', '__INSTR_mark_pointer',
                     '-delete-call', '__INSTR_mark_allocation',
                     '-delete-call', '__INSTR_mark_free',
                     '-delete-call', '__INSTR_mark_exit',
                     '-delete-call', '__symbiotic_keep_ptr']
                    )
        elif prop.signedoverflow():
            return ['-delete-call', '__symbiotic_check_overflow']
        return []

   #def passes_before_verification(self):
   #def actions_before_verification(self, symbiotic):
   # These callbacks are run 'always' before running a verification tool,
    # so even multiple times. If you want to run something only once,
    # put it into passes/actions_after_slicing

