#!/usr/bin/python

import os
import sys
import re

from . options import SymbioticOptions
from . utils import err, dbg, enable_debug, print_elapsed_time, restart_counting_time
from . utils.process import ProcessRunner, runcmd
from . utils.watch import ProcessWatch, DbgWatch
from . utils.utils import print_stdout, print_stderr, process_grep
from . exceptions import SymbioticException, SymbioticExceptionalResult

class ToolWatch(ProcessWatch):
    def __init__(self, tool):
        # store the whole output of a tool
        ProcessWatch.__init__(self, None)
        self._tool = tool

    def parse(self, line):
        if b'ERROR' in line or b'WARN' in line or b'Assertion' in line\
           or b'error' in line or b'warn' in line:
            sys.stderr.write(line.decode('utf-8'))
        else:
            dbg(line.decode('utf-8'), 'all', print_nl=False,
                prefix='', color=None)

class SymbioticVerifier(object):
    """
    Instance of symbiotic tool. Instruments, prepares, compiles and runs
    symbolic execution on given source(s)
    """

    def __init__(self, bitcode, sources, tool, opts, env=None, params=None):
        # original sources (needed for witness generation)
        self.sources = sources
        # source compiled to llvm bitecode
        self.llvmfile = bitcode
        # environment
        self.env = env
        self.options = opts

        self.override_params = params

        # definitions of our functions that we linked
        self._linked_functions = []

        # tool to use
        self._tool = tool

    def command(self, cmd):
        return runcmd(cmd, DbgWatch('all'),
                      "Failed running command: {0}".format(" ".join(cmd)))

    def _run_verifier(self, cmd):
        returncode = 0
        watch = ToolWatch(self._tool)
        try:
            runcmd(cmd, watch, 'Running the verifier failed')
        except SymbioticException as e:
            print_stderr(str(e), color='RED')
            returncode = 1

        res = self._tool.determine_result(returncode, 0,
                                          watch.getLines(), False)
        return res

    def run_verification(self):
        params = self.override_params or self.options.tool_params
        cmd = self._tool.cmdline(self._tool.executable(),
                                 params, [self.llvmfile],
                                 self.options.property.getPrpFile(), [])

        return self._run_verifier(cmd)

    def run(self):
        try:
            return self.run_verification()
        except KeyboardInterrupt as e:
            raise SymbioticException('interrupted')
        except SymbioticExceptionalResult as res:
            # we got result from some exceptional case
            return str(res)

