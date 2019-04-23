#!/usr/bin/python

import os
import sys
import re

from . transform import SymbioticCC
from . verifier import SymbioticVerifier
from . options import SymbioticOptions
from . utils import err, dbg, print_elapsed_time, restart_counting_time
from . utils.utils import print_stdout
from . utils.process import ProcessRunner
from . exceptions import SymbioticExceptionalResult

class Symbiotic(object):
    """
    Instance of symbiotic tool. Instruments, prepares, compiles and runs
    symbolic execution on given source(s)
    """

    def __init__(self, tool, src, opts=None, env=None):
        # source file
        self.sources = src
        # source compiled to llvm bytecode
        self.curfile = None
        # environment
        self.env = env

        if opts is None:
            self.options = SymbioticOptions(env.symbiotic_dir)
        else:
            self.options = opts

        # tool to use
        self._tool = tool

    def terminate(self):
        pr = ProcessRunner()
        if pr.hasProcess():
            pr.terminate()

    def kill(self):
        pr = ProcessRunner()
        if pr.hasProcess():
            pr.kill()

    def kill_wait(self):
        pr = ProcessRunner()
        if not pr.hasProcess():
            return

        if pr.exitStatus() is None:
            from time import sleep
            while pr.exitStatus() is None:
                pr.kill()

                print('Waiting for the child process to terminate')
                sleep(0.5)

            print('Killed the child process')

    def replay_nonsliced(self, cc):
        bitcode = cc.prepare_unsliced_file()
        params = self._tool.replay_error_params(cc.curfile)

        print_stdout('INFO: Replaying error path', color='WHITE')
        restart_counting_time()

        verifier = SymbioticVerifier(bitcode, self.sources,
                                     self._tool, self.options,
                                     self.env, params)
        res = verifier.run()

        print_elapsed_time('INFO: Replaying error path time', color='WHITE')

        return res

    def _run_symbiotic(self):
        cc = SymbioticCC(self.sources, self._tool, self.options, self.env)
        bitcode = cc.run()

        if self.options.no_verification:
            return 'No verification'

        verifier = SymbioticVerifier(bitcode, self.sources,
                                     self._tool, self.options, self.env)
        res = verifier.run()

        if self.options.replay_error and not self.options.noslice and\
            hasattr(self._tool, "replay_error_params"):
            print_stdout("Trying to confirm the error path")
            newres = self.replay_nonsliced(cc)

            if res != newres:
                dbg("Replayed result: {0}".format(newres))
                res = 'cex not-confirmed'

        has_error = res and res.startswith('false')

        if has_error and hasattr(self._tool, "describe_error"):
            self._tool.describe_error(cc.curfile)

        if not self.options.nowitness and hasattr(self._tool, "generate_witness"):
            self._tool.generate_witness(cc.curfile, self.sources, has_error)

        return res

    def run(self):
        try:
            return self._run_symbiotic()
        except KeyboardInterrupt:
            self.terminate()
            self.kill()
            print('Interrupted...')
            return 'interrupted'
        except SymbioticExceptionalResult as res:
            # we got result from some exceptional case
            return str(res)

