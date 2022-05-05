#!/usr/bin/env python3

from glob import glob
from subprocess import Popen, PIPE
from os import path

import argparse
import re
import sys

GREEN = '\u001b[32m'
RED = '\u001b[31m'
YELLOW = '\u001b[33m'
BOLD_GRAY = '\u001b[1m'
RESET = '\u001b[0m'


result_re = re.compile(r'(?<=^RESULT: ).*(?=\s)', re.MULTILINE)
failure = False
force_color = False


def print(*args, color='', end='\n'):
    import builtins
    import sys

    if not sys.stdout.isatty() and not force_color:
        builtins.print(*args, end=end)
    else:
        builtins.print(color, end='')
        builtins.print(*args, end='')
        builtins.print(RESET, end=end)

    sys.stdout.flush()


def get_expected_result(input_regex):
    if 'true' in input_regex:
        return 'true'

    # *false-valid-memtrack* -> |prefix| = 7 and |suffix| = 1
    return 'false(%s)' % input_regex[7:-1]


def run_tests(test_files, prp, expected_result, args):
    global failure

    cmd = ['symbiotic', '--exit-on-error', '--report=sv-comp',
           '--timeout=%d' % args.timeout]

    if prp != 'reach':
        cmd.append('--prp=' + prp)

    if args.debug:
        cmd.append('--debug=all')

    if args.is32bit:
        cmd.append('--32')

    if not args.with_integrity_check:
        cmd.append('--no-integrity-check')

    for test in test_files:
        print(test, end=': ')

        symbiotic = Popen(cmd + [test], stdout=PIPE, stderr=PIPE)
        out, err = map(lambda x: x.decode(), symbiotic.communicate())

        if expected_result in out and symbiotic.returncode == 0:
            print('PASS', color=GREEN)
            continue

        failure = True

        if 'timeout' in out:
            print('TIMEOUT', color=YELLOW)
            continue

        match = result_re.search(out)
        if match and 'ERROR' not in match[0] and symbiotic.returncode == 0:
            print('FAIL', color=RED)
        else:
            print('FATAL ERROR', color=RED)

        print('\tExpected result:', expected_result)
        print('\tActual result:', match[0] if match else 'N/A')

        print('\nstdout:')
        print(out)
        print('stderr:')
        print(err)


def main(args):
    if not args.with_integrity_check:
        print('WARNING', color=YELLOW, end='')
        print(': Symbiotic will be executed with \'--no-integrity-check\'!')
        print('WARNING', color=YELLOW, end='')
        print(': If that is not intended, pass \'--with-integrity-check\' to '
              'this script.')

    global force_color
    force_color = args.force_color

    for test in args.test_sets:
        basename = path.basename(test)
        prp = path.splitext(basename)[0]
        print('Executing', basename, '(%d-bit)' % (32 if args.is32bit else 64),
              color=BOLD_GRAY)

        with open(test, 'r') as input_regexes:
            for line in input_regexes:
                line = line.strip()
                run_tests(glob(line), prp, get_expected_result(line), args)

    sys.exit(int(failure))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--32', action='store_true', dest='is32bit',
                        default=False, help='use 32-bit environment')
    parser.add_argument('-c', '--color', action='store_true',
                        dest='force_color', default=False,
                        help='force colored output')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='execute Symbiotic in debug mode')
    parser.add_argument('-i', '--with-integrity-check', action='store_true',
                        default=False,
                        help='enable Symbiotic\'s integrity check')
    parser.add_argument('-t', '--timeout', action='store', type=int,
                        default=20, help='single test timeout')
    parser.add_argument('test_sets', nargs='+', type=str,
                        help='test sets to be executed')

    main(parser.parse_args())
