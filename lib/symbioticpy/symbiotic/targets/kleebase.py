"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2018-2019  Marek Chalupa
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from os.path import basename, dirname, abspath, isfile, join, realpath, exists, splitext
from os import listdir, rename
from struct import unpack
from symbiotic.utils.utils import print_stdout, process_grep
from symbiotic.utils import dbg
from symbiotic.utils.process import runcmd
from symbiotic.exceptions import SymbioticException
from symbiotic.witnesses.witnesses import GraphMLWriter
from symbiotic.witnesses.YAMLwitnesswriter import YAMLWriter


from sys import version_info
from sys import version_info
if version_info < (3, 0):
    from io import open



try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='10.0.1'

try:
    import benchexec.util as util
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    from symbiotic.benchexec.tools.template import BaseTool

from . tool import SymbioticBaseTool

def get_repr(obj):
    ret = []
    if not len(obj[1]) > 0:
        return ()

    b = obj[1][0]
    num = 1
    for i in range(1, len(obj[1])):
        if obj[1][i] != b:
            ret.append((b, num))
            b = obj[1][i]
            num = 1
        else:
            num += 1

    ret.append((b, num))
    return ret

def is_zero(obj):
    assert len(obj[1]) > 0

    for i in range(1, len(obj[1])):
        b = obj[1][i]
        if version_info.major < 3:
            value = ord(b)
        else:
            value = b
        if value != 0:
            return False

    return True

def get_nice_repr(obj):
    bytes_num = len(obj[1])
    rep = ''
    if bytes_num == 8:
        val = unpack('l', obj[1])[0]
        rep = "i64: {0}".format(val)
    elif bytes_num == 4:
        val = unpack('i', obj[1])[0]
        rep = "i32: {0}".format(val)
    elif bytes_num == 2:
        # unpack needs a buffer of size 4 for an integer
        val = unpack('h', obj[1])[0]
        rep = "i16: {0}".format(val)
    elif bytes_num == 1:
        # unpack needs a buffer of size 4 for an integer
        val = unpack('b', obj[1])[0]
        rep = "i8: {0}".format(val)
    else:
        return ''

    return rep

def print_object(obj):
    rep = 'len {0} bytes, ['.format(len(obj[1]))
    objrepr = get_repr(obj)
    if objrepr == ():
        assert(len(obj[1]) == 0)
        rep += "|"

    l = len(objrepr)
    for n in range(0, l):
        part  = objrepr[n]
        if version_info.major < 3:
            value = ord(part[0])
        else:
            value = part[0]

        value = hex(value)

        if part[1] > 1:
            rep += '{0} times {1}'.format(part[1], value)
        else:
            rep += '{0}'.format(value)
        if n == l - 1:
            rep += ']'
        else:
            rep += '|'
    nice_rep = get_nice_repr(obj)
    if nice_rep:
        rep += " ({0})".format(nice_rep)
    print('{0} := {1}'.format(obj[0].decode('ascii'), rep))

##
# dumping human readable error
##
def _parseKtest(pathFile):
    # this code is taken from ktest-tool from KLEE (but modified)

    f = open(pathFile, 'rb')

    hdr = f.read(5)
    if len(hdr) != 5 or (hdr != b'KTEST' and hdr != b"BOUT\n"):
        print('unrecognized file')
        sys.exit(1)
    version, = unpack('>i', f.read(4))
    if version > 3:
        print('unrecognized version')
        sys.exit(1)
    # skip args
    numArgs, = unpack('>i', f.read(4))
    for i in range(numArgs):
        size, = unpack('>i', f.read(4))
        f.read(size)

    if version >= 2:
        unpack('>i', f.read(4))
        unpack('>i', f.read(4))

    numObjects, = unpack('>i', f.read(4))
    objects = []
    for i in range(numObjects):
        size, = unpack('>i', f.read(4))
        name = f.read(size)
        size, = unpack('>i', f.read(4))
        bytes = f.read(size)
        objects.append((name, bytes))

    f.close()
    return objects

def _dumpObjects(ktestfile):
    objects = _parseKtest(ktestfile)
    if len(objects) > 100:
        n = 0
        for o in objects:
            if not is_zero(o):
                print_object(o)
                n += 1

        print('\nAnd the rest of objects ({0} objects) are 0'.format(len(objects) - n))
    else:
        for o in objects:
            print_object(o)


def dump_errors(bindir):
    pths = []
    abd = abspath(bindir)
    for item in listdir(abd):
        if item.endswith('.err'):
            dump_error(abspath(join(abd, item)))

def dump_error(pth):
    if not isfile(pth):
        dbg("Couldn't find the file with error description")
        return

    try:
        f = open(pth, 'r')
        print('\n --- Error trace ---\n')
        for line in f:
            print_stdout(line, print_nl = False)
        print('\n --- Sequence of non-deterministic values [function:file:line:col] ---\n')
        _dumpObjects(pth[:pth.find('.')+1]+'ktest')
        print('\n --- ----------- ---')
    except OSError as e:
        # this dumping is just for convenience,
        # so do not return any error
        dbg('Failed dumping the error: {0}'.format(str(e)))

def generate_graphml(path, source, is_correctness_wit, opts, saveto):
    assert saveto is not None
    gen = GraphMLWriter(source, opts.property.ltl(),
                        opts.is32bit, is_correctness_wit)
    if not is_correctness_wit:
        gen.generate_violation_witness(path, opts.property.termination())
    else:
        gen.createTrivialWitness()
        assert path is None
    gen.write(saveto)

def generate_yaml(path, source, is_correctness_wit, opts, saveto):
    assert saveto is not None
    gen = YAMLWriter(source, opts.property.ltl(),
                        opts.is32bit, is_correctness_wit)
    if not is_correctness_wit:
        gen.generate_violation_witness(path)
    else:
        gen.generate_correctness_witness()
        assert path is None
    gen.write(saveto)

def get_testcase(bindir):
    abd = abspath(bindir)
    for path in listdir(abd):
        if path.endswith('.err'):
            # get the corresponding .path file
            return abspath('{0}/{1}'.format(abd, path[:path.find(".")]))

def get_ktest(bindir):
    return get_testcase(bindir) + '.ktest';

def get_harness_file(bindir):
    return get_testcase(bindir) + '.harness.c';

def generate_graphml_witness(bindir, sources, is_correctness_wit, opts, saveto):
    assert len(sources) == 1 and "Can not generate witnesses for more sources yet"
    print('Generating GraphML {0} witness: {1}'.format('correctness' if is_correctness_wit else 'error', saveto))
    if is_correctness_wit:
        generate_graphml(None, sources[0], is_correctness_wit, opts, saveto)
        return

    pth = get_ktest(join(bindir, 'klee-last'))
    graphml = '{0}.graphml'.format(splitext(pth)[0])
    generate_graphml(graphml, sources[0], is_correctness_wit, opts, saveto)

def generate_yaml_witness(bindir, sources, is_correctness_wit, opts, saveto):
    assert len(sources) == 1 and "Can not generate witnesses for more sources yet"
    print('Generating YAML {0} witness: {1}'.format('correctness' if is_correctness_wit else 'error', saveto))
    if is_correctness_wit:
        generate_yaml(None, sources[0], is_correctness_wit, opts, saveto)
        return

    yaml_support =  opts.property.signedoverflow() or opts.property.unreachcall() or \
                    opts.property.assertions()

    if not yaml_support:
        print('Failed generating YAML witness: Property not supported by format')
        return

    pth = get_ktest(join(bindir, 'klee-last'))
    test = '{0}.waypoints'.format(splitext(pth)[0])
    generate_yaml(test, sources[0], is_correctness_wit, opts, saveto)

def generate_exec_witness(bindir, sources, opts, saveto = None):
    assert len(sources) == 1 and "Can not generate witnesses for more sources yet"
    if saveto is None:
        saveto = '{0}.exe'.format(sources[:sources.rfind('.')])
    print('Generating executable witness to : {0}'.format(saveto))

    if opts.test_comp:
        pth = get_harness_file(join(opts.testsuite_output))
    else:
        pth = get_harness_file(join(bindir, 'klee-last'))

    from symbiotic.exceptions import SymbioticException
    try:
        from symbiotic.transform import CompileWatch
        flags = ['-D__inline=']
        if opts.property.memsafety():
            flags+=['-fsanitize=address']
        elif opts.property.signedoverflow() or opts.property.undefinedness():
            flags+=['-fsanitize=undefined']
        runcmd(['clang', '-g', pth, sources[0], '-o', saveto] + flags,
               CompileWatch(), 'Generating executable witness failed')
    except SymbioticException as e:
        dbg(str(e))


# we use are own fork of KLEE, so do not use the official
# benchexec module for klee (FIXME: update the module so that
# we can use it)
class SymbioticTool(BaseTool, SymbioticBaseTool):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._options = opts
        self._arguments = ['-dump-states-on-halt=0',
                           '--output-stats=0', '--use-call-paths=0',
                           '--optimize=false', '-silent-klee-assume=1',
                           '-istats-write-interval=60s',
                           '-timer-interval=10',
                           #'--output-istats=0',
                           '-only-output-states-covering-new=1',
                           '-use-forked-solver=0',
                           '--libc=klee',
                           '--lazy-init',
                           '-external-calls=pure', '-max-memory=8000']

    def can_replay(self):
        """ Return true if the tool can do error replay """
        return True

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable('klee')

    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        """
        return self._version_from_tool(executable, arg='-version')

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'klee'

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        return llvm_version

    def set_environment(self, env, opts):
        """
        Set environment for the tool
        """
        if opts.devel_mode:
            env.prepend('PATH', '{0}/klee/build-{1}/bin'.\
                        format(env.symbiotic_dir, llvm_version))
            # XXX: we must take the runtime libraries from the install directory
            # because we have them compiled for 32-bit and 64-bit separately
            #(in build, there's only one of them)
            prefix = '{0}/install'.format(env.symbiotic_dir)
        else:
            prefix = '{0}'.format(env.symbiotic_dir)

        if opts.is32bit:
            env.prepend('KLEE_RUNTIME_LIBRARY_PATH',
                         '{0}/llvm-{1}/lib32/klee/runtime'.\
                         format(prefix, self.llvm_version()))
        else:
            env.prepend('KLEE_RUNTIME_LIBRARY_PATH',
                        '{0}/llvm-{1}/lib/klee/runtime'.\
                        format(prefix, self.llvm_version()))

    #  def actions_before_slicing(self, symbiotic):
    #      # FIXME: use -abort-on-threads with slicer
    #      # check whether there are threads in the program
    #      cmd = ['opt', '-q', '-load', 'LLVMsbt.so', '-check-module',
    #             '-detect-calls=pthread_create', '-o=/dev/null', symbiotic.curfile]
    #      retval, lines =\
    #      process_grep(cmd, 'Found call to function')
    #      if retval == 0:
    #          if lines:
    #             #self._has_threads = True
    #             #self.tool = NidhuggTool(self._options)
    #             #self.tool.set_environment(self._env, self._options)
    #             #dbg("Found threads, will use Nidhugg")
    #             #raise SymbioticException('Found threads, giving up')
    #
    #              # We do not slice threads correctly right now
    #              dbg("Found threads, will not slice (a temporary solution)")
    #              self._options.noslice = True
    #      else:
    #          dbg('Checking the module failed!')

    def passes_before_slicing(self):
        if self._options.property.termination():
            return ['-find-exits']
        return []

    def passes_after_slicing(self):
        passes = []

        # make the uninitialized variables symbolic (if desired)
        if not self._options.explicit_symbolic:
            passes.append('-initialize-uninitialized')

        # make external globals non-deterministic
        if not self._options.sv_comp:
            passes.append('-internalize-globals')

        # for the memsafety property, make functions behave like they have
        # side-effects, because LLVM optimizations could remove them otherwise,
        # even though they contain calls to assert
        if self._options.property.memsafety():
            passes.append('-remove-readonly-attr')
        elif self._options.property.termination():
            passes.append('-instrument-nontermination')
            passes.append('-instrument-nontermination-mark-header')

        return super().passes_after_slicing() + passes

    def describe_error(self, llvmfile):
        if self._options.test_comp:
            dump_errors(self._options.testsuite_output)
        else:
            dump_errors(join(dirname(llvmfile), 'klee-last'))

    def replay_error_params(self, llvmfile):
        """ Replay error on the unsliced file """
        if self._options.test_comp:
            srcdir = self._options.testsuite_output
            ktest = get_ktest(srcdir)
        else:
            srcdir = dirname(llvmfile)
            # replay the counterexample on non-sliced module
            ktest = get_ktest(join(srcdir, 'klee-last'))
        # resolve the symlink to klee-last as it is going to
        # be overwritten
        ktest = realpath(ktest)

        params = self._options.tool_params if self._options.tool_params else []
        params.append('-replay-nondets={0}'.format(ktest))

        return params

    def generate_witness(self, llvmfile, sources, has_error):
        if self._options.witness_output:
            generate_yaml_witness(dirname(llvmfile), sources, not has_error,
                                  self._options, self._options.witness_output)
        if self._options.graphml_witness_output:
            generate_graphml_witness(dirname(llvmfile), sources, not has_error,
                                     self._options, self._options.graphml_witness_output)

    def generate_exec_witness(self, bitcode, sources):
        out = self._options.witness_output[:self._options.witness_output.rfind('.')+1]+'exe'
        generate_exec_witness(dirname(bitcode), sources,
                              self._options, out)
