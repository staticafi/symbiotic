#!/usr/bin/env python3

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
from . sequentialize import sequentialize

def _error_call(source, calls):
    """ Line and column of the only call of an error function """
    pattern = re.compile(r'\b(?:{0})\s*\('.format('|'.join(calls)))
    found = None
    with open(source, errors='replace') as f:
        for lineno, line in enumerate(f, 1):
            for m in pattern.finditer(line):
                # skip the definition and declarations
                if re.search(r'\bvoid\s*$', line[:m.start()]):
                    continue
                if found:
                    return None
                found = (lineno, m.start() + 1)
    return found

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
            self.options = SymbioticOptions()
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

    def replay_nonsliced(self, tool, cc):
        bitcode = cc.prepare_unsliced_file(tool)
        params = []
        if hasattr(tool, "replay_error_params"):
            params = tool.replay_error_params(cc.curfile)

        print_stdout('INFO: Replaying error path', color='WHITE')
        restart_counting_time()

        verifier = SymbioticVerifier(bitcode, self.sources,
                                     tool, self.options,
                                     self.env, params)
        res, _ = verifier.run()

        print_elapsed_time('INFO: Replaying error path time', color='WHITE')

        return res

    def _verify(self, sources, witness=True):
        options = self.options
        cc = SymbioticCC(sources, self._tool, options, self.env)
        bitcode = cc.run()

        if options.no_verification:
            return 'No verification'

        verifier = SymbioticVerifier(bitcode, sources,
                                     self._tool, options, self.env)
        # result and the tool that decided this result
        res, tool = verifier.run()

        # if we crashed on the sliced file, try running on the unsliced file
        # (TODO: do this optional, as well as for slicer and instrumentation)
        resstartswith = res.lower().startswith
        if (not options.noslice) and \
           (options.sv_comp or options.test_comp) and \
           (resstartswith('error') or resstartswith('unknown')):
            print_stdout("INFO: Failed on the sliced code, trying on the unsliced code",
                         color="WHITE")
            options.replay_error = False # now we do not need to replay the error
            options.noslice = True # now we behave like without slicing
            bitcode = cc.prepare_unsliced_file(tool)
            verifier = SymbioticVerifier(bitcode, sources,
                                         self._tool, options, self.env)
            res, tool = verifier.run()
            print_elapsed_time('INFO: Running on unsliced code time', color='WHITE')

        if tool and options.replay_error and not tool.can_replay():
           dbg('Replay required but the tool does not support it')

        has_error = res and\
                    (res.startswith('false') or\
                    (res.startswith('done') and options.property.errorcall()))
        if has_error and options.replay_error and\
           not options.noslice and tool.can_replay():
            print_stdout("Trying to confirm the error path")
            newres = self.replay_nonsliced(tool, cc)

            dbg("Original result: '{0}'".format(res))
            dbg("Replayed result: '{0}'".format(newres))

            if res != newres:
                # if we did not replay the original error, but we found a different error
                # on this path, report it, since it should be real
                has_error = newres and\
                            (newres.startswith('false') or\
                            (newres.startswith('done') and\
                             options.property.errorcall()))
                if has_error:
                    res = newres
                else:
                    res = 'cex not-confirmed'
                    has_error = False

        if res == 'cex not-confirmed':
            # if we failed confirming CEX, rerun on unsliced file
            bitcode = cc.prepare_unsliced_file(tool)
            verifier = SymbioticVerifier(bitcode, sources,
                                         self._tool, options, self.env)
            res, tool = verifier.run()
            has_error = res and\
                        (res.startswith('false') or\
                        (res.startswith('done') and options.property.errorcall()))
 
        if has_error and hasattr(tool, "describe_error"):
            tool.describe_error(cc.curfile)

        if has_error and options.executable_witness and\
           hasattr(tool, "generate_exec_witness"):
            tool.generate_exec_witness(cc.curfile, sources)

        if witness and not options.nowitness and hasattr(tool, "generate_witness"):
            tool.generate_witness(cc.curfile, sources, has_error)

        return res

    def _generate_target_witness(self, source):
        """ Witness that only marks the call of the error function """
        options = self.options
        if not options.property.unreachcall():
            return
        loc = _error_call(source, options.property.getcalls())
        if loc is None:
            return
        from . witnesses.YAMLwitnesswriter import YAMLWriter
        print_stdout('Generating YAML error witness: {0}'.format(options.witness_output))
        gen = YAMLWriter(source, options.property, options.is32bit,
                         False, options.witness_output)
        gen.generate_target_witness(*loc)
        gen.write(options.witness_output)

    def _run_sequentialized(self):
        options = self.options
        source = self.sources[0]
        seq = sequentialize(source, options.property, options.is32bit,
                            os.path.join(self.env.symbiotic_dir, 'cseq'),
                            os.getcwd())
        if seq is None:
            return None

        print_stdout('INFO: Verifying the sequentialized program', color='WHITE')
        res = self._verify([seq], witness=False)
        # the sequentialization bounds the schedules, so only errors are real;
        # not leaks: threads cut off by the bound never free their memory
        if not res.startswith('false') or res == 'false(valid-memtrack)':
            return None

        if options.property.datarace():
            return 'false(no-data-race)'
        if options.witness_output and not options.nowitness:
            self._generate_target_witness(source)
        return res

    def _run_symbiotic(self):
        options = self.options
        prp = options.property
        if not (prp.unreachcall() or prp.memsafety()):
            options.sequentialize = False

        if prp.datarace():
            # data races are found only in the sequentialized program
            res = 'unknown'
        else:
            res = self._verify(self.sources)

        undecided = not (res.startswith('true') or res.startswith('false'))
        if options.sequentialize and undecided and\
           not options.no_verification and len(self.sources) == 1:
            seqres = self._run_sequentialized()
            if seqres:
                return seqres
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

