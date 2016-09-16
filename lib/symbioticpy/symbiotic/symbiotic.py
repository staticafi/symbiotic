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
        if 'removing' in line:
            sys.stdout.write(line)
        else:
            dbg(line, 'prepare', False)

class SlicerWatch(ProcessWatch):
    def __init__(self, lines = 100):
        ProcessWatch.__init__(self, lines)

    def parse(self, line):
        if 'INFO' in line:
            dbg(line,      domain = 'slicer', print_nl = False)
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

    def __init__(self, valid_deref = False):
        ProcessWatch.__init__(self, 100)
        self._found = []
        self._valid_deref = valid_deref

        # define and compile regular expressions for parsing klee's output
        self._patterns = {
            'ASSERTIONFAILED' : re.compile('.*ASSERTION FAIL:.*'),
            'ESTPTIMEOUT' : re.compile('.*query timed out (resolve).*'),
            'EKLEETIMEOUT' : re.compile('.*HaltTimer invoked.*'),
            'EEXTENCALL' : re.compile('.*failed external call.*'),
            'ELOADSYM' : re.compile('.*ERROR: unable to load symbol.*'),
            'EINVALINST' : re.compile('.*LLVM ERROR: Code generator does not support.*'),
            'EKLEEASSERT' : re.compile('.*klee: .*Assertion .* failed.*'),
            'EINITVALS' : re.compile('.*unable to compute initial values.*'),
            'ESYMSOL' : re.compile('.*unable to get symbolic solution.*'),
            'ESILENTLYCONCRETIZED' : re.compile('.*silently concretizing.*'),
            'ECONCRETIZED' : re.compile('.* concretized symbolic size.*'),
            'EEXTRAARGS' : re.compile('.*calling .* with extra arguments.*'),
            'EABORT' : re.compile('.*abort failure.*'),
            #'EGENERAL' : re.compile('.*now ignoring this error at this location.*'),
            'EMALLOC' : re.compile('.*found huge malloc, returning 0.*'),
            'ESKIPFORK' : re.compile('.*skipping fork.*'),
            'EKILLSTATE' : re.compile('.*killing.*states (over memory cap).*'),
            'EMEMERROR'  : re.compile('.*memory error: out of bound pointer.*'),
            'EVECTORUNSUP' : re.compile('.*XXX vector instructions unhandled.*'),
            'EFREE' : re.compile('.*memory error: invalid pointer: free.*')
        }

    def found(self):
        return ' '.join(self._found)

    def _parse_klee_output(self, line):
        for (key, pattern) in self._patterns.iteritems():
            if pattern.match(line):
                # return True so that we know we should terminate
                if key == 'ASSERTIONFAILED':
                    return key
                elif self._valid_deref and key == 'EMEMERROR':
                    return 'ASSERTIONFAILED (valid-deref)'
                elif self._valid_deref and key == 'EFREE':
                    return 'ASSERTIONFAILED (valid-free)'
                else:
                    return key

        return None

    def parse(self, line):
        found = self._parse_klee_output(line)
        if found:
            self._found.insert(0, found)

        if 'ERROR' in line or 'WARN' in line or 'Assertion' in line:
            sys.stdout.write(line)
        elif 'error' in line:
            sys.stderr.write(line)
        else:
            dbg(line, 'all', False)

# the list of optimizations is based on klee -optimize
# option, but is adjusted for our needs (therefore
# we don't use the -optimize option with klee)
optimizations_O2 = ['-simplifycfg', '-globalopt', '-globaldce', '-ipconstprop',
                    '-deadargelim', '-instcombine', '-simplifycfg', '-prune-eh',
                    '-functionattrs', '-inline', '-argpromotion', '-instcombine',
                    '-jump-threading', '-simplifycfg', '-gvn', '-scalarrepl',
                    '-instcombine', '-tailcallelim', '-simplifycfg',
                    '-reassociate', '-loop-rotate', '-licm', '-loop-unswitch',
                    '-instcombine', '-indvars', '-loop-deletion', '-loop-unroll',
                    '-instcombine', '-memcpyopt', '-sccp', '-instcombine',
                    '-dse', '-adce', '-simplifycfg', '-strip-dead-prototypes',
                    '-constmerge', '-ipsccp', '-deadargelim', '-die',
                    '-instcombine']

def report_results(res):
    dbg(res)
    result = res
    color = 'BROWN'

    if res.startswith('ASSERTIONFAILED'):
        result = 'FALSE'
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
            self.options = SymbioticOptions()
        else:
            self.options = opts

    def _run(self, cmd, watch, err_msg):
        self.current_process = ProcessRunner(cmd, watch)
        if self.current_process.run() != 0:
            self.current_process.printOutput(sys.stderr, 'RED')
            self.current_process = None
            raise SymbioticException(err_msg)

        self.current_process = None

    def _compile_to_llvm(self, source, output = None, with_g = True):
        """
        Compile given source to LLVM bytecode
        """

        cmd = ['clang', '-c', '-emit-llvm', '-include', 'symbiotic.h']

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
        prefix = '{0}/instrumentation/'.format(self.symbiotic_dir)
        if prp == 'VALID-FREE' or prp == 'MEM-TRACK':
            config = prefix + 'double_free/config.json'
            tolink = prefix + 'double_free/double_free.c'
        elif prp == 'NULL-DEREF':
            config = prefix + 'null_deref/config.json'
            tolink = prefix + 'null_deref/null_deref.c'
        else:
            raise SymbioticException('BUG: Unhandled property')

        # we need to compile and link the state machines to the code
        # before the actual instrumentation - LLVMinstr requires that
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

        # these options are exclusive
        if 'MEM-TRACK' in self.options.prp:
            self._instrument('MEM-TRACK')
        elif 'VALID-FREE' in self.options.prp:
            self._instrument('VALID-FREE')

        if 'NULL-DEREF' in self.options.prp:
            self._instrument('NULL-DEREF')

    def _get_libraries(self, which=[]):
        files = []

        if not self.options.no_lib:
            if 'memalloc' in which:
                libc = '{0}/lib/memalloc.c'.format(self.symbiotic_dir)
                llvmlibbc = self._compile_to_llvm(libc)
                files.append(llvmlibbc)

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
        for undef in undefs:
            name = '{0}/lib/{1}.c'.format(self.symbiotic_dir, undef)
            if os.path.isfile(name):
                output_name = self._compile_to_llvm(name)
                tolink.append(output_name)
            #else:
            #   dbg('Did not find the definition of \'{0}\''.format(undef))

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

    def link_undefined(self):
        if self.options.nolinkundef:
            return

        # get undefined functions from the bitcode
        undefs = self._get_undefined(self.llvmfile)
        if self._link_undefined(undefs):
            # if we linked someting, try get undefined again,
            # because the functions may have added some new undefined
            # functions
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

    def optimize(self, passes = optimizations_O2):
        if self.options.no_optimize:
            return

        output = '{0}-opt.bc'.format(self.llvmfile[:self.llvmfile.rfind('.')])
        cmd = ['opt', '-o', output, self.llvmfile] + passes

        self._run(cmd, DbgWatch('prepare'), 'Optimizing the code failed')
        self.llvmfile = output

    def check_llvmfile(self, llvmfile):
        """
        Check whether the bitcode does not contain anything
        that we do not support
        """
        cmd = ['opt', '-load', 'LLVMsvc15.so', '-check-unsupported',
               '-o', '/dev/null', llvmfile]
        try:
            self._run(cmd, UnsuppWatch(), 'Failed checking the code')
        except SymbioticException:
            return False

        return True

    def run_symexe(self):
        cmd = ['klee', '-exit-on-error-type=Assert', '-write-paths',
               '-dump-states-on-halt=0', '-silent-klee-assume=1',
               '-output-stats=0',#'-only-output-states-covering-new=1',
               '-max-time={0}'.format(self.options.timeout)] + self.options.symexe_params

        cmd.append(self.llvmfile)

        failed = False
        watch = KleeWatch('VALID-DEREF' in self.options.prp)

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
                llvms = self._compile_to_llvm(source)
                llvmsrc.append(llvms)

            # link all compiled sources to a one bytecode
            # the result is stored to self.llvmfile
            self.link('code.bc', llvmsrc)

        if not self.check_llvmfile(self.llvmfile):
            dbg('Unsupported call (probably pthread API)')
            return report_results('unsupported call')

        # remove definitions of __VERIFIER_* that are not created by us
        self.prepare(passes = ['-prepare'])

        # link the files that we got on the command line
        self.link_unconditional()

        # check if we should instrument the version of malloc
        # that never returns a NULL pointer
        if self.options.malloc_never_fails:
            instrument_alloc = '-instrument-alloc-nf'
        else:
            instrument_alloc = '-instrument-alloc'

        # instrument our malloc,
        # make all memory symbolic (if desired)
        # and then delete undefined function calls
        # and replace them by symbolic stuff
        passes = [instrument_alloc]
        if not self.options.explicit_symbolic:
            passes.append('-initialize-uninitialized')

        self.prepare(passes = passes)

        # in the case of valid-free property we want to
        # instrument even __VERIFIER_malloc functions,
        # so we need to link it before instrumenting
        #is_valid_free = ('VALID-FREE' in self.options.prp) or\
        #                ('MEM-TRACK' in self.options.prp) or \
        #                ('VALID-DEREF' in self.options.prp)
        #if is_valid_free and not self.options.noprepare:
        if not self.options.noprepare:
            lib = self._get_libraries(['memalloc'])
            self.link(libs = lib)

        # now instrument the code according to properties
        self.instrument()

        # link with the rest of libraries if needed (klee-libc)
        self.link()

        # link undefined (no-op when prepare is turned off)
        self.link_undefined()

        # remove/replace the rest of undefined functions
        # for which we do not have a definition
        if self.options.undef_retval_nosym:
            self.prepare(['-delete-undefined-nosym'])
        else:
            self.prepare(['-delete-undefined'])

        # slice the code
        if not self.options.noslice:
            # run optimizations that can make slicing more precise
            if "before-O2" in self.options.optlevel:
                if "opt-O2" in self.options.optlevel:
                    self.optimize(passes=['-O2'])
                else:
                    self.optimize(passes=optimizations_O2)
            elif "before" in self.options.optlevel:
                self.optimize(passes=['-simplifycfg', '-constmerge', '-dce',
                                      '-ipconstprop', '-argpromotion',
                                      '-instcombine', '-deadargelim',
                                      '-simplifycfg'])


            # if this is old slicer run, we must find the starting functions
            # (this adds the __ai_init_funs global variable to the module)
            # NOTE: must be after the optimizations that could remove it
            if self.options.old_slicer:
                self.old_slicer_find_init()

            # print info about time
            print_elapsed_time('INFO: Compilation, preparation and '\
                               'instrumentation time')

            for n in range(0, self.options.repeat_slicing):
                dbg('Slicing the code for the {0}. time'.format(n + 1))
                add_params = []
                if n == 0 and self.options.repeat_slicing > 1:
                    add_params = ['-pta-field-sensitive', '8',
                                  '-rd-max-set-size', '3']

                self.slicer(self.options.slicing_criterion, add_params)

                # optimize the code after slicing
                # -- when we slice more times, we wouldn't
                # slice anything in another passes without
                # the optimization
                if "after" in self.options.optlevel\
                    and self.options.repeat_slicing > 1:
                    if "opt-O2" in self.options.optlevel:
                        self.optimize(passes=['-O2'])
                    else:
                        self.optimize(passes=optimizations_O2)

            print_elapsed_time('INFO: Total slicing time')

            # new slicer removes unused itself, but for the old slicer
            # we must do it manually (this calls the new slicer ;)
            if self.options.old_slicer:
                self.remove_unused_only()

        # optimize the code before symbolic execution
        if "after" in self.options.optlevel:
            if "opt-O2" in self.options.optlevel:
                self.optimize(passes=['-O2'])
            else:
                self.optimize(passes=optimizations_O2)

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

