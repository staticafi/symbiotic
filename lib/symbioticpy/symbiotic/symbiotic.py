#!/usr/bin/env python3

import os
import sys

from . transform import SymbioticCC
from . verifier import SymbioticVerifier
from . options import SymbioticOptions
from . utils import err, dbg, print_elapsed_time, restart_counting_time
from . utils.utils import print_stdout
from . utils.process import ProcessRunner
from . exceptions import SymbioticException, SymbioticExceptionalResult
from . sequentialize import check, sequentialize, violation

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
            # give the process (e.g., runexec) a moment to clean up
            # its children before we kill it
            from time import sleep
            for _ in range(20):
                if pr.exitStatus() is not None:
                    break
                sleep(0.1)

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

        self._decider = tool
        return res

    def _generate_concurrent_witness(self, source, found):
        options = self.options
        from . witnesses.YAMLwitnesswriter import YAMLWriter
        print_stdout('Generating YAML error witness: {0}'.format(options.witness_output))
        gen = YAMLWriter(source, options.property, options.is32bit, False,
                         options.witness_output)
        gen.generate_concurrent_witness(*found)
        gen.write(options.witness_output)

    def _run_sequentialized(self):
        options = self.options
        source = self.sources[0]
        seq, linemap = sequentialize(source, options.property, options.is32bit,
                                     os.path.join(self.env.symbiotic_dir, 'cseq'),
                                     os.getcwd()) or (None, None)
        if seq is None:
            return None

        print_stdout('INFO: Verifying the sequentialized program', color='WHITE')
        # the slicer would remove CSeq's assumptions that bound the schedules
        options.noslice = True
        options.replay_error = False
        # the sequentialized program has no threads, use the sequential tools
        options.sequentialize = False
        if hasattr(self._tool, '_hit_threads'):
            self._tool._hit_threads = False
        # malloc does not fail here: a NULL from an unchecked malloc gave
        # invalid dereferences in memory-safe tasks (sssc12), and races
        # through CSeq's race slots, which use NULL for no access; only
        # errors are reported here, fewer executions miss an error at most
        options.malloc_never_fails = True
        try:
            res = self._verify([seq], witness=False)
        except (SymbioticException, SymbioticExceptionalResult) as e:
            # e.g., Predator's 'true', which the bound does not justify
            print_stdout('INFO: No result on the sequentialized program: {0}'.format(e),
                         color='WHITE')
            return None
        # the sequentialization bounds the schedules, so only errors are real;
        # not leaks: threads cut off by the bound never free their memory
        if not res.startswith('false') or res == 'false(valid-memtrack)':
            return None

        prp = options.property
        # the witness comes from KLEE's error path; klee-last is not the
        # error when slowbeast decided (no witness then, the verdict stays)
        decider = getattr(self, '_decider', None)
        if options.witness_output and not options.nowitness and\
           prp.unreachcall() and decider is not None and decider.name() == 'klee':
            try:
                found = violation(seq, linemap, os.path.join(os.getcwd(), 'klee-last'),
                                  prp.getcalls() + ['__VERIFIER_error'],
                                  prp.datarace())
                if found:
                    self._generate_concurrent_witness(source, found)
            except Exception as e:
                # a witness is optional, the verdict is not
                print_stdout('INFO: No witness for the sequentialized program: {0}'.format(e),
                             color='WHITE')
        return 'false(no-data-race)' if prp.datarace() else res

    def _run_symbiotic(self):
        options = self.options
        prp = options.property
        # decide it before the first run, the tools leave time for the
        # sequentialized program only if it will be verified
        if options.sequentialize:
            options.sequentialize = (prp.unreachcall() or prp.memsafety()) and\
                not options.no_verification and len(self.sources) == 1 and\
                check(self.sources[0], options.is32bit)

        # the options of the first run, the rerun without the cap starts with them
        initial = (options.noslice, options.replay_error,
                   options.malloc_never_fails)
        if prp.datarace():
            # data races are found only in the sequentialized program
            res = 'unknown'
        else:
            res = self._verify(self.sources)

        undecided = not (res.startswith('true') or res.startswith('false'))
        if options.sequentialize and undecided:
            capped = getattr(self._tool, '_hit_threads', False)
            seqres = self._run_sequentialized()
            if seqres:
                return seqres
            if capped:
                # no error in the sequentialized program, verify the original
                # program again as without CSeq, slowbeast -threads uncapped
                print_stdout('INFO: Verifying the program again without the time limit',
                             color='WHITE')
                options.noslice, options.replay_error,\
                    options.malloc_never_fails = initial
                options.sequentialize = False
                self._tool._hit_threads = False
                res = self._verify(self.sources)
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

