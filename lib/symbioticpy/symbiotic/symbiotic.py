#!/usr/bin/python

import os, sys
import re

from options import SymbioticOptions
from utils import err, dbg, enable_debug, print_elapsed_time, restart_counting_time
from utils.process import ProcessRunner
from utils.watch import ProcessWatch, DbgWatch
from utils.utils import print_stdout, print_stderr, get_symbiotic_dir
from exceptions import SymbioticException

class PrepareWatch(ProcessWatch):
    def __init__(self, lines = 100):
        ProcessWatch.__init__(self, lines)

    def parse(self, line):
        if 'Removed' in line or 'Defining':
            sys.stdout.write(line)
        else:
            dbg(line, 'prepare', False)

class SlicerWatch(ProcessWatch):
    def __init__(self, lines = 100):
        ProcessWatch.__init__(self, lines)

    def parse(self, line):
        if 'INFO' in line:
            dbg(line, domain = 'slicer', print_nl = False)
        elif 'ERROR' in line or 'error' in line:
            print_stderr(line)
        else:
            dbg(line, 'slicer', False)

class CompileWatch(ProcessWatch):
    """ Parse output of compilation """

    def __init__(self):
        ProcessWatch.__init__(self)

    def parse(self, line):
        if 'error' in line or 'ERROR' in line:
            sys.stderr.write('cc: {0}'.format(line))
        else:
            dbg(line, 'compile', print_nl = False)

class UnsuppWatch(ProcessWatch):
    unsupported_call = re.compile('.*call to .* is unsupported.*')

    def __init__(self):
        ProcessWatch.__init__(self)
        self._ok = True

    def ok(self):
        return self._ok

    def parse(self, line):
        dbg(line, domain='prepare', print_nl = False)
        self._ok = not UnsuppWatch.unsupported_call.match(line)

class KleeWatch(ProcessWatch):

    def __init__(self, memsafety  = False):
        ProcessWatch.__init__(self, 100)
        self._found = []
        self._memsafety = memsafety

        # define and compile regular expressions for parsing klee's output
        self._patterns = [
           ('EDOUBLEFREE' , re.compile('.*ASSERTION FAIL: 0 && "double free".*')),
           ('EINVALFREE' , re.compile('.*ASSERTION FAIL: 0 && "free on non-allocated memory".*')),
           ('EMEMLEAK' , re.compile('.*ASSERTION FAIL: 0 && "memory leak detected".*')),
           ('ASSERTIONFAILED' , re.compile('.*ASSERTION FAIL:.*')),
           ('ESTPTIMEOUT' , re.compile('.*query timed out (resolve).*')),
           ('EKLEETIMEOUT' , re.compile('.*HaltTimer invoked.*')),
           ('EEXTENCALL' , re.compile('.*failed external call.*')),
           ('ELOADSYM' , re.compile('.*ERROR: unable to load symbol.*')),
           ('EINVALINST' , re.compile('.*LLVM ERROR: Code generator does not support.*')),
           ('EKLEEASSERT' , re.compile('.*klee: .*Assertion .* failed.*')),
           ('EINITVALS' , re.compile('.*unable to compute initial values.*')),
           ('ESYMSOL' , re.compile('.*unable to get symbolic solution.*')),
           ('ESILENTLYCONCRETIZED' , re.compile('.*silently concretizing.*')),
           ('EEXTRAARGS' , re.compile('.*calling .* with extra arguments.*')),
           ('EABORT' , re.compile('.*abort failure.*')),
           #('EGENERAL' , re.compile('.*now ignoring this error at this location.*')),
           ('EMALLOC' , re.compile('.*found huge malloc, returning 0.*')),
           ('ESKIPFORK' , re.compile('.*skipping fork.*')),
           ('EKILLSTATE' , re.compile('.*killing.*states \(over memory cap\).*')),
           ('EMEMERROR'  , re.compile('.*memory error: out of bound pointer.*')),
           ('EMAKESYMBOLIC' , re.compile('.*memory error: invalid pointer: make_symbolic.*')),
           ('EVECTORUNSUP' , re.compile('.*XXX vector instructions unhandled.*')),
           ('EFREE' , re.compile('.*memory error: invalid pointer: free.*'))
        ]

        if not memsafety:
            # we do not want this pattern to be found in memsafety benchmarks,
            # because we insert our own check that do not care about what KLEE
            # really allocated underneath
            self._patterns.append(('ECONCRETIZED', re.compile('.* concretized symbolic size.*')))

    def found(self):
        return ' '.join(self._found)

    def _parse_klee_output(self, line):
        for (key, pattern) in self._patterns:
            if pattern.match(line):
                # return True so that we know we should terminate
                if key == 'ASSERTIONFAILED':
                    if self._memsafety:
                        key += ' (valid-deref)'
                    return key
                elif self._memsafety:
		    #if key == 'EMEMERROR':
                    #   return 'ASSERTIONFAILED (valid-deref)'
                    #if key == 'EFREE' or key == 'EDOUBLEFREE' or key == 'EINVALFREE':
                    if key == 'EDOUBLEFREE' or key == 'EINVALFREE':
                        return 'ASSERTIONFAILED (valid-free)'
                    if key == 'EMEMLEAK':
                        return 'ASSERTIONFAILED (valid-memtrack)'
                return key

        return None

    def parse(self, line):
        found = self._parse_klee_output(line)
        if found:
            self._found.insert(0, found)

        if 'ERROR' in line or 'WARN' in line or 'Assertion' in line\
           or 'error' in line or 'undefined reference' in line:
            sys.stderr.write(line)
        else:
            dbg(line, 'all', False)

def report_results(res):
    dbg(res)
    result = res
    color = 'BROWN'

    if res.startswith('ASSERTIONFAILED'):
        result = 'FALSE'
	info = res[15:].strip()
	if info:
	    result += ' ' + info
        color = 'RED'
    elif res == '':
        result = 'TRUE'
        color='GREEN'
    elif res == 'TIMEOUT':
        result = 'TIMEOUT'
    elif 'EKLEEERROR' in res:
        result = 'ERROR'
        color='RED'
    else:
        result = 'UNKNOWN'

    sys.stdout.flush()
    print_stdout(result, color=color)
    sys.stdout.flush()

    return result

def get_optlist_before(optlevel):
    from optimizations import optimizations
    lst = []
    for opt in optlevel:
        if not opt.startswith('before-'):
            continue

        o = opt[7:]
        if o.startswith('opt-'):
            lst.append(o[3:])
        else:
            if optimizations.has_key(o):
                lst += optimizations[o]

    return lst

def get_optlist_after(optlevel):
    from optimizations import optimizations
    lst = []
    for opt in optlevel:
        if not opt.startswith('after-'):
            continue

        o = opt[6:]
        if o.startswith('opt-'):
            lst.append(o[3:])
        else:
            if optimizations.has_key(o):
                lst += optimizations[o]

    return lst

class Symbiotic(object):
    """
    Instance of symbiotic tool. Instruments, prepares, compiles and runs
    symbolic execution on given source(s)
    """
    def __init__(self, src, opts = None, symb_dir = None):
        # source file
        self.sources = src
        # source compiled to llvm bytecode
        self.llvmfile = None
        # the file that will be used for symbolic execution
        self.runfile = None
        # currently running process
        self.current_process = None
        # the directory that symbiotic script is located
        if symb_dir:
            self.symbiotic_dir = symb_dir
        else:
            self.symbiotic_dir = get_symbiotic_dir()

        if opts is None:
            self.options = SymbioticOptions(self.symbiotic_dir)
        else:
            self.options = opts

        # definitions of our functions that we linked
        self._linked_functions = []

    def _run(self, cmd, watch, err_msg):
        self.current_process = ProcessRunner(cmd, watch)
        if self.current_process.run() != 0:
            self.current_process.printOutput(sys.stderr, 'RED')
            self.current_process = None
            raise SymbioticException(err_msg)

        self.current_process = None

    def _compile_to_llvm(self, source, output = None, with_g = True, opts = []):
        """
        Compile given source to LLVM bytecode
        """

        cmd = ['clang', '-c', '-emit-llvm', '-include', 'symbiotic.h'] + opts

        if with_g:
            cmd.append('-g')

        if self.options.CFLAGS:
            cmd += self.options.CFLAGS
        if self.options.CPPFLAGS:
            cmd += self.options.CPPFLAGS

        if self.options.is32bit:
            cmd.append('-m32')


        cmd.append('-o')
        if output is None:
            llvmfile = '{0}.bc'.format(source[:source.rfind('.')])
        else:
            llvmfile = output

        cmd.append(llvmfile)
        cmd.append(source)

        self._run(cmd, CompileWatch(), "Compiling source '{0}' failed".format(source))

        return llvmfile

    def prepare(self, passes = ['-prepare', '-delete-undefined']):
        if self.options.noprepare:
            return

        self._prepare(passes)

    def _prepare(self, passes):
        output = '{0}-pr.bc'.format(self.llvmfile[:self.llvmfile.rfind('.')])
        cmd = ['opt', '-load', 'LLVMsvc15.so', self.llvmfile, '-o', output] + passes

        self._run(cmd, PrepareWatch(), 'Prepare phase failed')
        self.llvmfile = output

    def old_slicer_find_init(self):
        self._prepare(passes=['-find-init'])

    def _instrument(self, prp):
        prefix = '{0}/instrumentations/'.format(self.symbiotic_dir)
	if self.options.is32bit:
	    libdir = os.path.join(self.symbiotic_dir, 'lib32')
	else:
	    libdir = os.path.join(self.symbiotic_dir, 'lib')

	tolinkbc = None
        if prp == 'MEMSAFETY':
            config = prefix + 'memsafety/config.json'
	    # check wether we have this file precompiled
	    # (this may be a distribution where we're trying to
	    # avoid compilation of anything else than sources)
            precompiled_bc = '{0}/memsafety.bc'.format(libdir)
	    if os.path.isfile(precompiled_bc):
	        tolinkbc = precompiled_bc
	    else:
                tolink = prefix + 'memsafety/memsafety.c'
        elif prp == 'VALID-FREE' or prp == 'MEM-TRACK':
            config = prefix + 'double_free/config.json'
	    # check wether we have this file precompiled
	    # (this may be a distribution where we're trying to
	    # avoid compilation of anything else than sources)
            precompiled_bc = '{0}/double_free.bc'.format(libdir)
	    if os.path.isfile(precompiled_bc):
	        tolinkbc = precompiled_bc
	    else:
                tolink = prefix + 'double_free/double_free.c'
        elif prp == 'VALID-DEREF':
            config = prefix + 'valid_deref/config.json'
            precompiled_bc = '{0}/valid_deref.bc'.format(libdir)
	    if os.path.isfile(precompiled_bc):
	        tolinkbc = precompiled_bc
	    else:
                tolink = prefix + 'valid_deref/valid_deref.c'
        elif prp == 'NULL-DEREF':
            config = prefix + 'null_deref/config.json'
            precompiled_bc = '{0}/null_deref.bc'.format(libdir)
	    if os.path.isfile(precompiled_bc):
	        tolinkbc = precompiled_bc
	    else:
                tolink = prefix + 'null_deref/null_deref.c'
        else:
            raise SymbioticException('BUG: Unhandled property')

        # we need to compile and link the state machines to the code
        # before the actual instrumentation - LLVMinstr requires that
	if not tolinkbc:
            tolinkbc = self._compile_to_llvm(tolink, with_g = False)
        self.link(libs=[tolinkbc])

        output = '{0}-inst.bc'.format(self.llvmfile[:self.llvmfile.rfind('.')])
        cmd = ['LLVMinstr', config, self.llvmfile, output]

        self._run(cmd, DbgWatch('instrument'), 'Instrumenting the code failed')
        self.llvmfile = output

    def instrument(self):
        """
        Instrument the code.
        """

        # FIXME: do not compare the strings all the time...

        if 'MEMSAFETY' in self.options.prp:
            self._instrument('MEMSAFETY')
        elif 'MEM-TRACK' in self.options.prp and\
             'VALID-DEREF' in self.options.prp and\
             'VALID-FREE' in self.options.prp:
            self._instrument('MEMSAFETY')
        else:
            # these two are mutually exclusive
            if 'MEM-TRACK' in self.options.prp:
                self._instrument('MEM-TRACK')
            elif 'VALID-FREE' in self.options.prp:
                self._instrument('VALID-FREE')

            if 'VALID-DEREF' in self.options.prp:
                self._instrument('VALID-DEREF')

            if 'NULL-DEREF' in self.options.prp:
                self._instrument('NULL-DEREF')

    def _get_libraries(self, which=[]):
        files = []
        if self.options.add_libc:
            d = '{0}/lib'.format(self.symbiotic_dir)
            if self.options.is32bit:
                d += '32'

            files.append('{0}/klee/runtime/klee-libc.bc'.format(d))

        return files

    def link(self, output = None, libs = None):
        if libs is None:
            libs = self._get_libraries()

        if not libs:
            return

        if output is None:
            output = '{0}-ln.bc'.format(self.llvmfile[:self.llvmfile.rfind('.')])

        cmd = ['llvm-link', '-o', output] + libs
        if self.llvmfile:
            cmd.append(self.llvmfile)

        self._run(cmd, DbgWatch('compile'), 'Failed linking llvm file with libraries')
        self.llvmfile = output

    def _link_undefined(self, undefs):
        tolink = []
        for ty in self.options.linkundef:
            for undef in undefs:
                name = '{0}/lib/{1}/{2}.c'.format(self.symbiotic_dir, ty, undef)
                if os.path.isfile(name):
	            output = os.path.join(os.getcwd(), os.path.basename(name))
                    output = '{0}.bc'.format(output[:output.rfind('.')])
	            self._compile_to_llvm(name, output)
                    tolink.append(output)

                    # for debugging
                    self._linked_functions.append(undef)

        if tolink:
            self.link(libs = tolink)
            return True

        return False

    def link_unconditional(self):
        """ Link the files that we got on the command line """

        return self._link_undefined(self.options.link_files)


    def _get_undefined(self, bitcode):
        cmd = ['llvm-nm', '-undefined-only', '-just-symbol-name', bitcode]
        watch = ProcessWatch(None)
        self._run(cmd, watch, 'Failed getting undefined symbols from bitcode')
        return map (lambda s: s.strip(), watch.getLines())

    def link_undefined(self, only_func = None):
        if not self.options.linkundef:
            return

        # get undefined functions from the bitcode
        undefs = self._get_undefined(self.llvmfile)
        if not only_func is None:
            if only_func in undefs:
                undefs = [only_func]
            else:
                undefs = []
        if self._link_undefined(undefs):
            # if we linked someting, try get undefined again,
            # because the functions may have added some new undefined
            # functions
            if only_func is None:
                self.link_undefined()

    def slicer(self, criterion, add_params = []):
        output = '{0}.sliced'.format(self.llvmfile[:self.llvmfile.rfind('.')])
        if self.options.old_slicer:
            cmd = ['opt', '-load', 'LLVMSlicer.so',
                   '-create-hammock-cfg', '-slice-inter',
                   '-o', output] + self.options.slicer_params
        else:
            cmd = ['llvm-slicer', '-c', criterion]
            if self.options.slicer_pta in ['fi', 'fs']:
                cmd.append('-pta')
                cmd.append(self.options.slicer_pta)

            cmd.append('-statistics')

            if self.options.slicer_params:
                cmd += self.options.slicer_params

            if add_params:
                cmd += add_params

        cmd.append(self.llvmfile)

        self._run(cmd, SlicerWatch(), 'Slicing failed')
        self.llvmfile = output

    def remove_unused_only(self):
        output = '{0}.sliced'.format(self.llvmfile[:self.llvmfile.rfind('.')])
        cmd = ['llvm-slicer', '-remove-unused-only']

        cmd.append('-statistics')
        cmd.append(self.llvmfile)

        self._run(cmd, SlicerWatch(), 'Slicing failed (removing unused only)')
        self.llvmfile = output

    def optimize(self, passes):
        if self.options.no_optimize:
            return

        output = '{0}-opt.bc'.format(self.llvmfile[:self.llvmfile.rfind('.')])
        cmd = ['opt', '-o', output, self.llvmfile] + passes

        self._run(cmd, CompileWatch(), 'Optimizing the code failed')
        self.llvmfile = output

    def check_llvmfile(self, llvmfile, check='-check-unsupported'):
        """
        Check whether the bitcode does not contain anything
        that we do not support
        """
        cmd = ['opt', '-load', 'LLVMsvc15.so', check,
               '-o', '/dev/null', llvmfile]
        try:
            self._run(cmd, UnsuppWatch(), 'Failed checking the code')
        except SymbioticException:
            return False

        return True

    def run_symexe(self):
        cmd = ['klee', '-write-paths',
               '-dump-states-on-halt=0', '-silent-klee-assume=1',
               '-output-stats=0', '-disable-opt', '-only-output-states-covering-new=1',
               '-max-time={0}'.format(self.options.timeout)] + self.options.symexe_params

        if not self.options.dont_exit_on_error:
            cmd.append('-exit-on-error-type=Assert')

        cmd.append(self.llvmfile)

        failed = False
        memsafety = 'VALID-DEREF' in self.options.prp or \
	            'VALID-FREE' in self.options.prp or \
	            'VALID-MEMTRACK' in self.options.prp or \
	            'MEMSAFETY' in self.options.prp
        watch = KleeWatch(memsafety)

        try:
            self._run(cmd, watch, 'Symbolic execution failed')
        except SymbioticException:
            failed = True

        found = watch.found()
        if failed:
            found += ' EKLEEERROR'

        return found

    def terminate(self):
        if self.current_process:
            self.current_process.terminate()

    def kill(self):
        if self.current_process:
            self.current_process.kill()

    def run(self, criterion = '__assert_fail'):
        try:
            return self._run_symbiotic(criterion);
        except KeyboardInterrupt:
            self.terminate()
            self.kill()
            print('Interrupted...')

    def _run_symbiotic(self, criterion = '__assert_fail'):
        restart_counting_time()

        if self.options.source_is_bc:
            self.llvmfile = sources[0]
        else:
            # compile all sources
            llvmsrc = []
            for source in self.sources:
                opts = ['-Wno-unused-parameter', '-Wno-unused-attribute',
                        '-Wno-unused-label', '-Wno-unknown-pragmas']
                if 'UNDEF-BEHAVIOR' in self.options.prp:
                    opts.append('-fsanitize=undefined')
                    opts.append('-fno-sanitize=unsigned-integer-overflow')
                elif 'SIGNED-OVERFLOW' in self.options.prp:
                    opts.append('-fsanitize=signed-integer-overflow')

                llvms = self._compile_to_llvm(source, opts=opts)
                llvmsrc.append(llvms)

            # link all compiled sources to a one bytecode
            # the result is stored to self.llvmfile
            self.link('code.bc', llvmsrc)

        if not self.check_llvmfile(self.llvmfile, '-check-concurr'):
            dbg('Unsupported call (probably pthread API)')
            return report_results('unsupported call')

        # remove definitions of __VERIFIER_* that are not created by us
        self.prepare(passes = ['-prepare', '-remove-infinite-loops'])

        # link the files that we got on the command line
        self.link_unconditional()


        memsafety = 'VALID-DEREF' in self.options.prp or \
	            'VALID-FREE' in self.options.prp or \
	            'VALID-MEMTRACK' in self.options.prp or \
	            'MEMSAFETY' in self.options.prp
        passes = []
        if memsafety:
            # remove error calls, we'll put there our own
            passes = ['-remove-error-calls']
        elif 'UNDEF-BEHAVIOR' in self.options.prp:
            # remove the original calls to __VERIFIER_error and put there
            # new on places where the code exhibits an undefined behavior
            passes = ['-remove-error-calls', '-replace-ubsan']
        elif 'SIGNED-OVERFLOW' in self.options.prp:
            # we instrumented the code with ub sanitizer,
            # so make the calls errors
           passes = ['-replace-ubsan']

        if passes:
            self.prepare(passes = passes)

        # now instrument the code according to properties
        self.instrument()

        # instrument our malloc -- either the version that can fail,
        # or the version that can not fail.
        if self.options.malloc_never_fails:
            self.prepare(passes = ['-instrument-alloc-nf'])
        else:
            self.prepare(passes = ['-instrument-alloc'])

        # make all memory symbolic (if desired)
        # and then delete undefined function calls
        # and replace them by symbolic stuff
        if not self.options.explicit_symbolic:
            self.prepare(['-initialize-uninitialized'])

        # link with the rest of libraries if needed (klee-libc)
        self.link()

        # link undefined (no-op when prepare is turned off)
        self.link_undefined()

        # slice the code
        if not self.options.noslice:
            # run optimizations that can make slicing more precise
            opt = get_optlist_before(self.options.optlevel)
            if opt:
                self.optimize(passes=opt)

            # if this is old slicer run, we must find the starting functions
            # (this adds the __ai_init_funs global variable to the module)
            # NOTE: must be after the optimizations that could remove it
            if self.options.old_slicer:
                self.old_slicer_find_init()

            # break the infinite loops just before slicing
            # so that the optimizations won't make them syntactically infinite again
            self.prepare(['-break-infinite-loops', '-remove-infinite-loops'])

            # print info about time
            print_elapsed_time('INFO: Compilation, preparation and '\
                               'instrumentation time')

            for n in range(0, self.options.repeat_slicing):
                dbg('Slicing the code for the {0}. time'.format(n + 1))
                add_params = []
                if n == 0 and self.options.repeat_slicing > 1:
                    add_params = ['-pta-field-sensitive=8']

                self.slicer(self.options.slicing_criterion, add_params)

                if self.options.repeat_slicing > 1:
                    opt = get_optlist_after(self.options.optlevel)
                    if opt:
                        self.optimize(passes=opt)
                        self.prepare(['-break-infinite-loops', '-remove-infinite-loops'])

            print_elapsed_time('INFO: Total slicing time')

            # new slicer removes unused itself, but for the old slicer
            # we must do it manually (this calls the new slicer ;)
            if self.options.old_slicer:
                self.remove_unused_only()
        else:
            print_elapsed_time('INFO: Compilation, preparation and '\
                               'instrumentation time')

        # start a new time era
        restart_counting_time()

        # optimize the code before symbolic execution
        opt = get_optlist_after(self.options.optlevel)
        if opt:
            self.optimize(passes=opt)

        if not self.check_llvmfile(self.llvmfile):
            dbg('Unsupported call (probably floating handling)')
            return report_results('unsupported call')

        # there may have been created new loops
        self.prepare(['-remove-infinite-loops'])

        # remove/replace the rest of undefined functions
        # for which we do not have a definition and
	# that has not been removed
        if self.options.undef_retval_nosym:
            self.prepare(['-delete-undefined-nosym'])
        else:
            self.prepare(['-delete-undefined'])

        # delete-undefined inserts __VERIFIER_make_symbolic
        self.link_undefined(only_func = '__VERIFIER_make_symbolic');

        if self._linked_functions:
            print('Linked our definitions to these undefined functions:')
            for f in self._linked_functions:
                print_stdout('  ', print_nl = False)
                print_stdout(f)

        # XXX: we could optimize the code again here...
        print_elapsed_time('INFO: After-slicing optimizations and preparation time')

        if not self.options.final_output is None:
            # copy the file to final_output
            try:
                os.rename(self.llvmfile, self.options.final_output)
                self.llvmfile = self.options.final_output
            except OSError as e:
                msg = 'Cannot create {0}: {1}'.format(self.options.final_output, e.message)
                raise SymbioticException(msg)

        if not self.options.no_symexe:
            print('INFO: Starting verification')
            found = self.run_symexe()
        else:
            found = 'Did not run symbolic execution'

        return report_results(found)

