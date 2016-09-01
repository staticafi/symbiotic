#!/usr/bin/python

from subprocess import call, Popen, PIPE, STDOUT
from utils import dbg, err
from watch import BufferedDbgWatch
from .. import SymbioticException

def run_and_watch(cmd, watch):
    """
    Run command @cmd and pass its stdout+stderr output
    to @watch object. watch object is supposed to be
    an instance of ProcessWatch object. Running process
    has handle in current_process global variable.

    \return return code of the process or -1 on watch error
    """

    dbg(' '.join(cmd))

    # run the command and store handle into global variable
    # current_process, so that we can easily kill this process
    # on timeout or signal. This way we can run only one
    # process at the time, but we don't need more (yet?)
    global current_process
    current_process = Popen(cmd, stdout=PIPE, stderr=STDOUT)

    while True:
        line = current_process.stdout.readline()
        if line == '' and current_process.poll() is not None:
            break

        watch.parse(line)
        if not watch.ok():
            # watch told us to kill the process for some reason
            current_process.terminate()
            current_process.kill()
            return -1

    ret = current_process.wait()
    current_process = None

    return ret

def run_checked(cmd, error_msg, dbg_domain = 'all'):
    """
    Run command and raise an exeception on error
    """
    watch = BufferedDbgWatch(dbg_domain)
    if run_and_watch(cmd, watch) != 0:
       for line in watch.getLines():
           print_stderr(line, 'ERR: ')
       raise SymbioticException(error_msg)


