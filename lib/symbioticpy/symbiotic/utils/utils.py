#/usr/bin/python

import sys
import os
from time import time
from distutils.version import LooseVersion

COLORS = {
    'DARK_BLUE': '\033[0;34m',
    'CYAN': '\033[0;36m',
    'BLUE': '\033[1;34m',
    'PURPLE': '\033[0;35m',
    'RED': '\033[1;31m',
    'GREEN': '\033[1;32m',
    'BROWN': '\033[0;33m',
    'YELLOW': '\033[1;33m',
    'WHITE': '\033[1;37m',
    'GRAY': '\033[0;37m',
    'DARK_GRAY': '\033[1;30m',
    'RESET': '\033[0m'
}


def print_stream(msg, stream, prefix=None, print_nl=True, color=None):
    """
    Print message to stderr/stdout

    @ msg      : str    message to print
    @ prefix   : str    prefix for the message
    @ print_nl : bool  print new line after the message
    @ color    : str    color to use when printing, default None
    """

    # don't print color when the output is redirected
    # to a file
    if not stream.isatty():
        color = None

    if not color is None:
        stream.write(COLORS[color])

    if msg == '':
        return
    if not prefix is None:
        stream.write(prefix)

    stream.write(msg)

    if not color is None:
        stream.write(COLORS['RESET'])

    if print_nl:
        stream.write('\n')

    stream.flush()


def print_stderr(msg, prefix=None, print_nl=True, color=None):
    print_stream(msg, sys.stderr, prefix, print_nl, color)


def print_stdout(msg, prefix=None, print_nl=True, color=None):
    print_stream(msg, sys.stdout, prefix, print_nl, color)


def err(msg, color='RED'):
    print_stderr(msg, 'ERROR: ', color=color)
    sys.exit(1)


def process_grep(cmd, pattern):
    from . watch import GrepWatch
    from . process import ProcessRunner

    watch = GrepWatch(pattern)
    retval = ProcessRunner().run(cmd, watch)
    return (retval, watch.getLines())


debug_enabled = False
debug_opts = []


def enable_debug(d_opts):
    global debug_enabled
    global debug_opts

    debug_enabled = True
    debug_opts = d_opts


def dbg(msg, domain='all', print_nl=True, prefix='[DBG] ', color='GRAY'):
    global debug_enabled

    if debug_enabled:
        global debug_opts
        should_print = 'all' in debug_opts or\
                       domain in debug_opts
        if should_print:
            print_stderr(msg, prefix, print_nl, color)


# variable used to measure elapsed time
last_time = None


def restart_counting_time():
    global last_time
    last_time = time()


def print_elapsed_time(msg, color=None):
    global last_time
    assert last_time is not None

    tm = time() - last_time
    print_stdout('{0}: {1}'.format(msg, tm), color=color)
    # set new starting point
    last_time = time()


def get_symbiotic_dir():
    # get real path (strip off links)
    realpath = os.path.realpath(os.path.join(sys.argv[0], '..'))
    return os.path.abspath(os.path.dirname(realpath))

def get_clang_version():
    (retval, lines) = process_grep(['clang', '-v'], 'version')
    assert(retval == 0)
    assert(len(lines) == 1)

    return lines[0].split()[2].strip()

def dump_paths(dump_as_cmd=False, fun = print_stdout):
    variables = ['PATH', 'LD_LIBRARY_PATH', 'C_INCLUDE_DIR']
    for v in variables:
        if v in os.environ:
            if dump_as_cmd:
                fun('export {0}={1}:${0}'.format(v, os.environ[v]))
            else:
                fun('{0}={1}'.format(v, os.environ[v]))

    variables = ['CFLAGS', 'CPPFLAGS']
    for v in variables:
        if v in os.environ:
            if dump_as_cmd:
                fun('export {0}="{1} ${0}"'.format(v, os.environ[v]))
            else:
                fun('{0}="{1}"'.format(v, os.environ[v]))

