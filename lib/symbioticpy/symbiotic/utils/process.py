#!/usr/bin/python

from subprocess import Popen, PIPE, STDOUT
from . utils import dbg, print_stderr
from . watch import ProcessWatch
from .. import SymbioticException
from sys import stdout, stderr

try:
    from benchexec.util import find_executable
except ImportError:
    from symbiotic.benchexec.util import find_executable


class ProcessRunner(object):
    # we have one global process so that we can kill it anytime
    # (there's always at most one process running anyway)
    current_process = None

    def run(self, cmd, watch = ProcessWatch()):
        """
        Run command cmd and pass its stdout+stderr output
        to the watch object. watch object is supposed to be
        an instance of ProcessWatch object.

        \return return code of the process or None when the
        process has been stopped by the watch object
        """

        assert isinstance(watch, ProcessWatch)
        # we executed another process while the previous one is still running
        assert ProcessRunner.current_process is None

        dbg('|> {0}'.format(' '.join(map(str, cmd))), prefix='', color='CYAN')

        # run the command and store the handle into the class attribute
        # current_process, so that we can easily kill this process
        # on timeout or signal. This way we can run only one
        # process at the time, but we don't need more (yet?)
        try:
            ProcessRunner.current_process = Popen(cmd, stdout=PIPE, stderr=STDOUT)
        except OSError as e:
            msg = ' '.join(cmd) + '\n'
            raise SymbioticException(msg + str(e))

        for line in ProcessRunner.current_process.stdout:
            if line == b'':
                break

            watch.putLine(line)
            if not watch.ok():
                # watch told us to kill the process for some reason
                ProcessRunner.current_process.terminate()
                ProcessRunner.current_process.kill()
                ProcessRunner.current_process = None
                return None

        status = ProcessRunner.current_process.wait()
        ProcessRunner.current_process = None

        return status

    def hasProcess(self):
        return ProcessRunner.current_process is not None

    def terminate(self):
        assert self.hasProcess()
        if self.exitStatus() is None:
            ProcessRunner.current_process.terminate()

    def kill(self):
        assert self.hasProcess()
        if self.exitStatus() is None:
            ProcessRunner.current_process.kill()

    def exitStatus(self):
        assert self.hasProcess()
        return ProcessRunner.current_process.poll()

def runcmd(cmd, watch = ProcessWatch(), err_msg = ""):
    ## if the binary does not have absolute path, tell us which binary it is
    #if cmd[0][0] != '/':
    #    dbg("'{0}' is '{1}'".format(cmd[0], find_executable(cmd[0])), color='DARK_GRAY')
    process = ProcessRunner()
    if process.run(cmd, watch) != 0:
        for line in watch.getLines():
            print_stderr(line.decode('utf-8'),
                         color='RED', print_nl=False)
        raise SymbioticException(err_msg)

