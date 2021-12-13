#!/usr/bin/python

import sys

from . utils import dbg
from . utils import dbg, print_elapsed_time, restart_counting_time
from . utils.process import runcmd, ProcessRunner
from . utils.watch import ProcessWatch, DbgWatch
from . utils.utils import print_stderr, print_stdout
from . exceptions import SymbioticException, SymbioticExceptionalResult
from . transform import SymbioticCC

def initialize_verifier(opts):
    from . targets import targets
    try:
        return targets[opts.tool_name](opts)
    except KeyError:
        raise SymbioticException('Unknown verifier: {0}'.format(opts.tool_name))

class ToolWatch(ProcessWatch):
    def __init__(self, tool):
        # store the whole output of a tool
        ProcessWatch.__init__(self, None)
        self._tool = tool

    def parse(self, line):
        if b'ERROR' in line or b'WARN' in line or b'Assertion' in line\
           or b'error' in line or b'warn' in line:
            line = line.decode('utf-8', 'replace')
            sys.stderr.write(line)
        else:
            # characters on which decode fails
            msg = line.decode('utf-8', 'replace')
            dbg(msg, 'all', print_nl=msg[-1] != '\n', prefix='', color=None)

class SymbioticVerifier(object):
    """
    Instance of symbiotic tool. Instruments, prepares, compiles and runs
    symbolic execution on given source(s)
    """

    def __init__(self, bitcode, sources, tool, opts, env=None, params=None):
        # original sources (needed for witness generation)
        self.sources = sources
        # source compiled to llvm bitecode
        self.curfile = bitcode
        # environment
        self.env = env
        self.options = opts

        self.override_params = params

        # definitions of our functions that we linked
        self._linked_functions = []

        # tool to use
        self._tool = tool
        # create an instance of CC so that we can do auxiliary
        # transformations before verification
        self._cc = SymbioticCC(sources, tool, opts, env)

    def command(self, cmd):
        return runcmd(cmd, DbgWatch('all'),
                      "Failed running command: {0}".format(" ".join(cmd)))

    def run_opt(self, passes):
        self._cc.curfile = self.curfile
        self._cc.run_opt(passes)
        self.curfile = self._cc.curfile

    def link_undefined(self, only_func=None):
        self._cc.curfile = self.curfile
        self._cc.link_undefined(only_func)
        self.curfile = self._cc.curfile

    def _run_tool(self, tool, prp, params, timeout):
        cmd = []
        if timeout:
            cmd = ['timeout', str(int(timeout))]
        cmd += tool.cmdline(tool.executable(), params,
                            [self.curfile], prp, [])
        watch = ToolWatch(tool)
        process = ProcessRunner()

        returncode = process.run(cmd, watch)
        if returncode != 0:
            dbg('The verifier return non-0 return status')

        res = tool.determine_result(returncode, 0,
                                    watch.getLines(),
                                    False)
        if res.lower().startswith('error'):
            for line in watch.getLines():
                print_stderr(line.decode('utf-8', 'replace'),
                             color='RED', print_nl=False)
        return res, watch

    def _run_verifier(self, tool, addparams, timeout):
        # do any additional transformations before verification
        if hasattr(tool, 'passes_before_verification'):
            self.run_opt(tool.passes_before_verification())

        if hasattr(tool, 'actions_before_verification'):
            tool.actions_before_verification(self)

        # setup tool parameters
        params = self.override_params or self.options.tool_params
        if addparams:
            params = params + addparams
        prp = self.options.property.getPrpFile()

        # do it!
        return self._run_tool(tool, prp, params, timeout)

    def run_verification(self):
        print_stdout('INFO: Starting verification', color='WHITE')
        restart_counting_time()
        orig_bitcode = self.curfile
        for verifiertool, addparams, verifiertimeout in self._tool.verifiers():
            self.curfile = orig_bitcode
            res, watch = self._run_verifier(verifiertool, addparams, verifiertimeout)
            sw = res.lower().startswith
            # we got an answer, we can finish
            if sw('true') or sw('false'):
                return res, verifiertool
            print(f"{verifiertool.name()} answered {res}")
            if hasattr(self._tool, "verifier_failed"):
                self._tool.verifier_failed(verifiertool, res, watch)
        self.curfile = orig_bitcode # restore the original bitcode
        print_elapsed_time("INFO: Verification time", color='WHITE')
        return res, None

    def run(self):
        try:
            return self.run_verification()
        except KeyboardInterrupt as e:
            raise SymbioticException('interrupted')
        except SymbioticExceptionalResult as res:
            # we got result from some exceptional case
            return str(res), None

