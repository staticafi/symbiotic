#!/usr/bin/python

from subprocess import call, Popen, PIPE, STDOUT
from . utils import dbg, err, print_stream
from . watch import ProcessWatch, DbgWatch
from .. import SymbioticException
from sys import stdout, stderr

class ProcessRunner(object):
    def __init__(self, cmd, watch = ProcessWatch()):
        self._cmd = cmd
        self._watch = watch
        self._process = None

    def run(self):
        """
        Run command _cmd and pass its stdout+stderr output
        to _watch object. watch object is supposed to be
        an instance of ProcessWatch object. Running process
        has handle in current_process global variable.

        \return return code of the process or -1 on watch error
        """

        dbg('|> {0}'.format(' '.join(self._cmd)), prefix='')

        # run the command and store handle into global variable
        # current_process, so that we can easily kill this process
        # on timeout or signal. This way we can run only one
        # process at the time, but we don't need more (yet?)
        try:
            self._process = Popen(self._cmd, stdout=PIPE, stderr=STDOUT)
        except OSError as e:
            msg = ' '.join(self._cmd) + '\n'
            raise SymbioticException(msg + str(e))

        while True:
            line = self._process.stdout.readline()
            if line == b'' and self._process.poll() is not None:
                break

            self._watch.putLine(line)
            if not self._watch.ok():
                # watch told us to kill the process for some reason
                self._process.terminate()
                self._process.kill()
                return -1

        return self._process.wait()

    def terminate(self):
        if self._process:
            self._process.terminate()

    def kill(self):
        if self._process:
            self._process.kill()

    def exitStatus(self):
        assert self._process

        return self._process.poll()

    def getOutput(self):
        return self._watch.getLines()

    def printOutput(self, stream = stdout, clr = None):
        for line in self._watch.getLines():
            print_stream(line.decode('utf-8'), stream, color = clr, print_nl = False)

def run_checked(cmd, error_msg, dbg_domain = 'all'):
    """
    Run command and raise an exeception on error
    """
    pr = ProcessRunner(cmd, DbgWatch(dbg_domain, None))
    if pr.run() != 0:
       pr.printOutput(stderr)
       raise SymbioticException(error_msg)

