#!/usr/bin/python

class SymbioticOptions(object):
    def __init__(self, symbiotic_dir = None):
        if symbiotic_dir is None:
	    from utils.utils import get_symbiotic_dir
	    symbiotic_dir = get_symbiotic_dir()

        self.is32bit = True
        self.prp = []
        self.noslice = False
        self.malloc_never_fails = False
        self.noprepare = False
        self.explicit_symbolic = False
        self.undef_retval_nosym = False
        self.nolinkundef = False
        self.timeout = 0
        self.add_libc = False
        self.no_lib = False
        self.old_slicer = False
        self.require_slicer = False
        self.no_optimize = False
        self.no_symexe = False
        self.final_output = None
        self.witness_output = '{0}/witness.graphml'.format(symbiotic_dir)
        self.source_is_bc = False
        self.optlevel = ["before-O3", "after-O3"]
        self.slicer_pta = 'fi'
        self.slicing_criterion = '__assert_fail'
        self.repeat_slicing = 1
        # these files will be linked unconditionally
        self.link_files = []
        # additional parameters that can be passed right
        # to the slicer and symbolic executor
        self.slicer_params = []
        self.symexe_params = []
        self.CFLAGS = []
        self.CPPFLAGS = []

