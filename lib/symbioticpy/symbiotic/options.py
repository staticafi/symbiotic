#!/usr/bin/python

class SymbioticOptions(object):
    def __init__(self, is32bit = True, noslice=False, timeout=0):
        self.is32bit = is32bit
        self.prp = []
        self.noslice = noslice
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
        self.witness_output = 'witness.graphml'
        self.source_is_bc = False
        self.optlevel = ["before", "after"]
        self.slicer_pta = 'old'
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

