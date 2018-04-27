#!/usr/bin/python

from subprocess import call, Popen, PIPE, STDOUT
from . utils import dbg, err, print_stream
from . watch import ProcessWatch, DbgWatch
from .. import SymbioticException
from sys import stdout, stderr

try:
    from benchexec.util import find_executable
except ImportError:
    from symbiotic.benchexec.util import find_executable


class ProcessRunner(object):
    def __init__(self, cmd, watch=ProcessWatch()):
        self._cmd = cmd
        assert isinstance(watch, ProcessWatch)
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

        dbg('|> {0}'.format(' '.join(self._cmd)), prefix='', color='CYAN')

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

    def printOutput(self, stream=stdout, clr=None):
        for line in self._watch.getLines():
            print_stream(line.decode('utf-8'), stream,
                         color=clr, print_nl=False)


# we have one global process so that we can kill it anytime
# (there's always at most one process running anyway)
current_process = None

def getCurrentProcess():
    global current_process
    return current_process

def runcmd(cmd, watch = ProcessWatch(), err_msg = ""):
    # if the binary does not have absolute path, tell us which binary it is
    if cmd[0][0] != '/':
        dbg("'{0}' is '{1}'".format(cmd[0], find_executable(cmd[0])), color='DARK_GRAY')
    global current_process
    current_process = ProcessRunner(cmd, watch)
    if current_process.run() != 0:
        current_process.printOutput(sys.stderr, 'RED')
        current_process = None
        raise SymbioticException(err_msg)

    current_process = None

