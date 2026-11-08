#!/usr/bin/env python3

import re
import sys
from fnmatch import fnmatchcase
from os.path import basename, isfile, join
from shutil import copyfile
from subprocess import run, PIPE, STDOUT, TimeoutExpired

from . utils import dbg
from . utils.utils import print_stdout

CSEQ_TIMEOUT = 120
# the first configuration of Lazy-CSeq's SV-COMP wrapper
CSEQ_OPTIONS = ['--sv-comp', '--threads', '100', '--atomic-parameters',
                '--deep-propagation', '--nondet-condvar-wakeups',
                '--backend', 'cpachecker',
                '--rounds', '2', '--unwind-while', '2', '--unwind-for', '2']

# CSeq's model of rwlocks is wrong and it does not model semaphores,
# spinlocks and C11 atomics (an unmodelled lock protects nothing)
UNSUPPORTED = ['pthread_rwlock_*lock', 'sem_*', 'pthread_spin_*',
               '__atomic_*', '__sync_*']

PRELUDE = '''\
extern void __assert_fail(const char *, const char *, unsigned int, const char *) __attribute__((__noreturn__));
void reach_error(void) { __assert_fail("cseq", "sequentialized", 0, "reach_error"); }
void __cs_seq_assert(int cond) { if (!cond) reach_error(); }
#define __VERIFIER_error reach_error
'''

# KLEE intercepts these by name, so CSeq's models would not run
RENAMES = '''\
#define pthread_join __cs_seq_pthread_join
#define pthread_key_create __cs_seq_pthread_key_create
#define pthread_setspecific __cs_seq_pthread_setspecific
#define pthread_getspecific __cs_seq_pthread_getspecific
'''

# an undefined assert() would be invisible to the verifier
ASSERT = '#define assert(c) __cs_seq_assert(c)\n'

# the program's own errors are pruned, the only error left is a race
RACE_PRELUDE = '''\
extern void __VERIFIER_assume(int);
void __cs_nonrace_fail(const char *a, const char *f, unsigned int l, const char *fn) { __VERIFIER_assume(0); }
void __cs_data_race(void) { reach_error(); }
#define __assert_fail __cs_nonrace_fail
#define assert(c) __VERIFIER_assume(c)
'''

REWRITES = [
    # CSeq keeps static in parameter lists
    (r'(\(|, )static ', r'\1'),
    # CSeq leaves the variables that choose the context switches uninitialized
    (r'(?m)^([ \t]*unsigned int __cs_tmp_t\d+_r\d+);', r'\1 = __VERIFIER_nondet_uint();'),
    # glibc prototypes conflict with CSeq's definitions of pthread functions
    (r'extern\s+int\s+pthread_\w+\s*\([^;]*\)\s*;', ';'),
]

RACE_REWRITES = [
    # calls of the error functions, not their definitions
    (r'(?<!void )\b(__VERIFIER_error|reach_error)\s*\(\s*\)', '__VERIFIER_assume(0)'),
]

def _rewrite(text, rewrites):
    for pattern, replacement in rewrites:
        text = re.sub(pattern, replacement, text)
    return text

def _postprocess(text):
    return PRELUDE + RENAMES + ASSERT + _rewrite(text, REWRITES)

def _postprocess_race(text):
    text = _rewrite(text, RACE_REWRITES)
    if '__CPROVER' in text:
        return None
    # the race detector declares its address variables repeatedly in one scope
    temps = sorted(set(re.findall(r'^\s*static void \*(__\w+___);', text, re.M)))
    text = re.sub(r'^\s*static void \*__\w+___;\n', '', text, flags=re.M)
    decls = ''.join('void *{0};\n'.format(t) for t in temps)
    return PRELUDE + RENAMES + RACE_PRELUDE + decls + _rewrite(text, REWRITES)

def check(source, errcalls, is32bit):
    """
    Check whether CSeq can sequentialize the program, that is, it creates
    threads and does not use unsupported synchronization.
    Return the locations of the calls of errcalls or None.
    """
    cmd = ['clang', '-c', '-emit-llvm', '-g', '-fgnu89-inline', '-D__inline=',
           '-w', '-o', 'check.bc', source]
    if is32bit:
        cmd.append('-m32')
    if run(cmd, stdout=PIPE, stderr=STDOUT).returncode != 0:
        dbg('Compiling the program for the check failed')
        return None
    cmd = ['opt', '-load', 'LLVMsbt.so', '-check-module', '-detect-atomics',
           '-detect-calls=' + ','.join(['pthread_create'] + UNSUPPORTED + errcalls),
           '-enable-new-pm=0', '-disable-output', 'check.bc']
    out = run(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True).stdout

    funs, locs = set(), []
    for line in out.splitlines():
        words = line.split()
        if line.startswith('Found function '):
            funs.add(words[2])
        elif line.startswith('Found call to function ') and words[4] in errcalls:
            locs.append(tuple(int(n) for n in words[6].split(':')))
    if 'pthread_create' not in funs or 'Found atomic instruction' in out or\
       any(fnmatchcase(f, u) for f in funs for u in UNSUPPORTED):
        return None
    return locs

def sequentialize(source, prp, is32bit, cseqdir, outdir):
    """
    Sequentialize the program with CSeq.
    Return the path to the sequentialized program or None.
    """
    # CSeq writes _cs_<name>.c next to its input
    name = basename(source)
    copy = join(outdir, name)
    copyfile(source, copy)
    if name.endswith('.i'):
        name = name[:-2] + '.c'

    cmd = [sys.executable, join(cseqdir, 'cseq.py'), '-i', copy] + CSEQ_OPTIONS
    if is32bit:
        cmd.append('--32')
    if prp.datarace():
        cmd.append('--data-race-check')
    try:
        run(cmd, cwd=cseqdir, stdout=PIPE, stderr=STDOUT, timeout=CSEQ_TIMEOUT)
    except TimeoutExpired:
        dbg('CSeq timed out')
        return None
    except OSError as e:
        print_stdout('INFO: Cannot run CSeq: {0}'.format(e), color='WHITE')
        return None
    cs = join(outdir, '_cs_' + name)
    if not isfile(cs):
        dbg('CSeq failed')
        return None

    with open(cs, errors='replace') as f:
        text = f.read()
    text = _postprocess_race(text) if prp.datarace() else _postprocess(text)
    if text is None:
        dbg('Rewriting the race checks failed')
        return None
    seq = join(outdir, 'seq-' + name)
    with open(seq, 'w') as f:
        f.write(text)
    if run(['clang', '-fsyntax-only', '-fgnu89-inline', '-Wno-everything', seq],
           stdout=PIPE, stderr=STDOUT).returncode != 0:
        dbg('The sequentialized program does not compile')
        return None
    return seq
