#!/usr/bin/python

from . property import get_property

class SymbioticOptions(object):
    def __init__(self, symbiotic_dir=None):
        if symbiotic_dir is None:
            from . utils.utils import get_symbiotic_dir
            self.symbiotic_dir = get_symbiotic_dir()
        else:
            self.symbiotic_dir = symbiotic_dir

        # source codes
        self.sources = []

        self.tool_name = 'klee-symbiotic'
        self.is32bit = False
        self.stats = False
        # properties mapped to our names
        self.property = get_property(self.symbiotic_dir, None)
        self.noslice = False
        # FIXME: make it False, this is just a temporary
        # switch for SV-COMP, since I do not want to send another
        # PR to change switches
        self.malloc_never_fails = True
        self.noprepare = False
        self.explicit_symbolic = False
        self.undef_retval_nosym = False
        self.undefined_are_pure = False
        # link all that we have by default
        self.linkundef = ['svcomp', 'verifier', 'libc', 'posix', 'kernel']
        self.timeout = 0
        self.add_libc = False
        self.no_lib = False
        self.require_slicer = False
        self.no_optimize = False
        self.no_verification = False
        self.final_output = None
        self.witness_output = '{0}/witness.graphml'.format(self.symbiotic_dir)
        self.source_is_bc = False
        self.optlevel = ["before-O3", "after-O3"]
        self.slicer_pta = 'fi'
        self.slicing_criterion = '__assert_fail,__VERIFIER_error'
        self.memsafety_config_file = 'config.json'
        self.repeat_slicing = 1
        self.dont_exit_on_error = False
        # these files will be linked unconditionally
        self.link_files = []
        # additional parameters that can be passed right
        # to the slicer and symbolic executor
        self.slicer_params = []
        self.tool_params = []
        # these llvm passes will not be run in the optimization phase
        self.disabled_optimizations = []
        self.CFLAGS = []
        self.CPPFLAGS = []
        self.devel_mode = False
        self.instrumentation_files_path = None
