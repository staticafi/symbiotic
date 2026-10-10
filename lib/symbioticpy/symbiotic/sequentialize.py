#!/usr/bin/env python3

import re
import sys
from os.path import basename, isfile, join
from subprocess import run, PIPE, STDOUT, TimeoutExpired

from . utils import dbg

CSEQ_TIMEOUT = 120
# the first configuration of Lazy-CSeq's SV-COMP wrapper
CSEQ_OPTIONS = ['--sv-comp', '--threads', '100', '--atomic-parameters',
                '--deep-propagation', '--nondet-condvar-wakeups',
                '--backend', 'cpachecker',
                '--rounds', '2', '--unwind-while', '2', '--unwind-for', '2']

# CSeq's model of rwlocks is wrong and it does not model C11 atomics
UNSUPPORTED = re.compile(r'^(?!.*\bextern\b).*\bpthread_rwlock_\w*lock\s*\('
                         r'|\b_Atomic\b|\b__atomic_\w+\s*\(|\b__sync_\w+\s*\(',
                         re.M)

PRELUDE = '''\
extern void __assert_fail(const char *, const char *, unsigned int, const char *) __attribute__((__noreturn__));
void reach_error(void) { __assert_fail("cseq", "sequentialized", 0, "reach_error"); }
void __cs_seq_assert(int cond) { if (!cond) reach_error(); }
'''

RACE_PRELUDE = '''\
extern void __VERIFIER_assume(int);
void __cs_nonrace_fail(const char *a, const char *f, unsigned int l, const char *fn) { __VERIFIER_assume(0); }
'''

def _postprocess(text):
    text = re.sub(r'\(static ', '(', text)
    text = re.sub(r', static ', ', ', text)
    text = text.replace('__VERIFIER_error()', 'reach_error()')
    # an undefined assert() would be invisible to the verifier
    text = re.sub(r'\bassert\s*\(', '__cs_seq_assert(', text)
    # CSeq leaves the variables that choose the context switches uninitialized
    text = re.sub(r'^([ \t]*unsigned int __cs_tmp_t\d+_r\d+);',
                  r'\1 = __VERIFIER_nondet_uint();', text, flags=re.M)
    # constant folding emits float array sizes (1024/32 -> 32.0)
    text = re.sub(r'\[(\d+)\.0\]', r'[\1]', text)
    # glibc prototypes conflict with CSeq's definitions of pthread functions
    text = re.sub(r'extern\s+int\s+pthread_\w+\s*\([^;]*\)\s*;', ';', text)
    # KLEE intercepts these by name, so CSeq's models would not run
    for fn in ('pthread_join', 'pthread_key_create',
               'pthread_setspecific', 'pthread_getspecific'):
        text = re.sub(r'\b{0}\b'.format(fn), '__cs_seq_' + fn, text)
    return PRELUDE + text

def _postprocess_race(text):
    # the program's own errors are pruned, the only error left is a race
    text = re.sub(r'\b__assert_fail\b', '__cs_nonrace_fail', text)
    text = re.sub(r'(?<!void )\b__VERIFIER_error\(\)', '__VERIFIER_assume(0)', text)
    text = re.sub(r'(?<!void )\breach_error\s*\(\s*\)', '__VERIFIER_assume(0)', text)
    text = re.sub(r'\bassert\s*\(', '__VERIFIER_assume(', text)
    text = re.sub(r'__CPROVER_assert\((.*?), "Data race found on [^\n]*?"\);',
                  r'if (!(\1)) reach_error();', text)
    if '__CPROVER' in text:
        return None
    # the race detector declares its address variables repeatedly in one scope
    temps = sorted(set(re.findall(r'^\s*static void \*(__\w+___);', text, re.M)))
    text = re.sub(r'^\s*static void \*__\w+___;\n', '', text, flags=re.M)
    decls = ''.join('void *{0};\n'.format(t) for t in temps)
    return RACE_PRELUDE + decls + _postprocess(text)

def sequentialize(source, prp, is32bit, cseqdir, outdir):
    """
    Sequentialize the program with CSeq if it creates threads.
    Return the path to the sequentialized program or None.
    """
    with open(source, errors='replace') as f:
        text = f.read()
    if 'pthread_create' not in text or UNSUPPORTED.search(text):
        return None

    # CSeq writes _cs_<name>.c next to its input
    name = basename(source)
    copy = join(outdir, name)
    with open(copy, 'w') as f:
        f.write(text)
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
