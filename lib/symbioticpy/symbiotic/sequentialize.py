#!/usr/bin/env python3

import re
import sys
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

# the thread functions that CSeq models; any other (rwlocks, semaphores,
# spinlocks, pthread_once, ...) would be a no-op with a nondet result;
# CSeq's model of pthread_barrier_wait gives wrong results;
# CSeq's thread-local storage (pthread_key_create, pthread_setspecific,
# pthread_getspecific) calls the destructor at the end of every context
# and its pthread_self returns the ID of the first thread in main
MODELLED = {'pthread_create', 'pthread_join', 'pthread_exit', 'pthread_detach',
            'pthread_mutex_init', 'pthread_mutex_destroy',
            'pthread_mutexattr_init', 'pthread_mutexattr_destroy',
            'pthread_mutexattr_settype',
            'pthread_mutex_lock', 'pthread_mutex_unlock',
            'pthread_cond_init', 'pthread_cond_destroy', 'pthread_cond_wait',
            'pthread_cond_signal', 'pthread_cond_broadcast'}
# the thread and synchronization functions (C11 atomics are instructions)
THREAD_API = ['pthread_*', '_pthread_*', '__pthread_*', 'sem_*',
              '__atomic_*', '__sync_*', 'thrd_*', 'mtx_*', 'cnd_*', 'tss_*',
              'call_once']

PRELUDE = '''\
extern void __assert_fail(const char *, const char *, unsigned int, const char *) __attribute__((__noreturn__));
void reach_error(void) { __assert_fail("cseq", "sequentialized", 0, "reach_error"); }
void __cs_seq_assert(int cond) { if (!cond) reach_error(); }
#define __VERIFIER_error reach_error
'''

# KLEE intercepts these by name, so CSeq's models would not run
RENAMES = '''\
#define pthread_join __cs_seq_pthread_join
'''

# CSeq does not model these, KLEE would return a nondet value; return 0
# and do nothing (a detached thread runs on, only joining it is undefined);
# CSeq's mutexes ignore their attributes, and as a second lock and an
# unlock by another thread block, a recursive or error-checking mutex only
# loses executions (settype fails with EINVAL on an unknown kind as glibc)
NOOPS = '''\
#define pthread_detach(t) ((void)(t), 0)
#define pthread_mutexattr_init(a) ((void)(a), 0)
#define pthread_mutexattr_destroy(a) ((void)(a), 0)
#define pthread_mutexattr_settype(a, k) ((void)(a), (unsigned int)(k) > 3 ? 22 : 0)
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
    return PRELUDE + RENAMES + NOOPS + ASSERT + _rewrite(text, REWRITES)

def _postprocess_race(text):
    text = _rewrite(text, RACE_REWRITES)
    if '__CPROVER' in text:
        return None
    # the race detector declares its address variables repeatedly in one scope
    temps = sorted(set(re.findall(r'^\s*static void \*(__\w+___);', text, re.M)))
    text = re.sub(r'^\s*static void \*__\w+___;\n', '', text, flags=re.M)
    decls = ''.join('void *{0};\n'.format(t) for t in temps)
    return PRELUDE + RENAMES + NOOPS + RACE_PRELUDE + decls +\
           _rewrite(text, REWRITES)

def _writes_thread_parameter(text):
    """
    CSeq calls a thread function again with its argument at every context
    switch, so an assignment to its parameter is lost; taking the address
    of the parameter counts as one
    """
    # the race detector takes the address of every accessed variable
    text = re.sub(r'(?m)^\s*__\w+___ = \(& \w+\);$', '', text)
    for fun in set(re.findall(r'(\w+)\(__cs_threadargs\[\d+\]\)', text)):
        d = re.search(r'\b{0}\(static [^()]*?(\w+)\s*\)\s*{{'.format(fun),
                      text)
        if not d:
            continue
        # the body of the thread function (an inlined call of the function
        # elsewhere has a parameter of the same name); braces in string and
        # char literals and in comments do not count
        depth, end = 1, d.end()
        while depth and end < len(text):
            c = text[end]
            if c in '"\'':
                end += 1
                while end < len(text) and text[end] != c:
                    end += 2 if text[end] == '\\' else 1
            elif text.startswith('/*', end):
                end = text.find('*/', end + 2)
                end = len(text) if end < 0 else end + 1
            elif text.startswith('//', end):
                end = text.find('\n', end)
                end = len(text) if end < 0 else end
            else:
                depth += {'{': 1, '}': -1}.get(c, 0)
            end += 1
        body = text[d.end():end]
        for m in re.finditer(r'\b{0}\b'.format(d.group(1)), body):
            before = body[max(0, m.start() - 100):m.start()].rstrip()
            after = body[m.end():m.end() + 100].lstrip()
            while before.endswith('(') and after.startswith(')'):
                before, after = before[:-1].rstrip(), after[1:].lstrip()
            if after.startswith(('++', '--')) or before.endswith(('++', '--')):
                return True
            # an assignment, but not one to *p
            if re.match(r'(?:[-+*/%&|^]|<<|>>)?=(?!=)', after) and\
               not before.endswith('*'):
                return True
            # &p, but not x & p or x && p
            if before.endswith('&') and not re.search(
                    r'(?:&|\]|\b(?!return\b)\w+)\s*&$', before):
                return True
    return False

def _joins_without_result(bitcode):
    """
    CSeq's pthread_join never writes the thread's result, so accept only
    joins whose result pointer is NULL or a local variable that is used
    by nothing else than joins (it is never read); any other use of
    pthread_join, e.g., through a cast, is rejected too
    """
    res = run(['llvm-dis', '-o', '-', bitcode], stdout=PIPE, stderr=PIPE,
              universal_newlines=True)
    if res.returncode != 0:
        return False
    join = re.compile(r'\bcall i32 @pthread_join\([^()]*, i8\*\* '
                      r'(?:noundef )?(null|%[-\w$.]+)\)')
    calls = [line for line in res.stdout.splitlines()
             if '@pthread_join' in line and not line.startswith('declare ')]
    if not all(join.search(line) for line in calls):
        return False
    for body in re.findall(r'(?ms)^define .*?^}$', res.stdout):
        for var in {m.group(1) for m in join.finditer(body)} - {'null'}:
            use = re.compile(re.escape(var) + r'(?![-\w$.])')
            alloca = var + ' = alloca '
            if alloca not in body:
                return False
            for line in body.splitlines():
                line = line.strip()
                if use.search(line) and not (line.startswith(alloca) or
                        join.search(line) or
                        line.startswith('call void @llvm.dbg.declare(')):
                    return False
    return True

def check(source, errcalls, is32bit):
    """
    Check whether CSeq can sequentialize the program, that is, it creates
    threads and uses only the thread functions that CSeq models.
    Return the locations of the calls of errcalls or None.
    """
    # most tasks have no threads, do not compile them for the check
    with open(source, errors='replace') as f:
        if 'pthread_create' not in f.read():
            return None
    cmd = ['clang', '-c', '-emit-llvm', '-g', '-fgnu89-inline', '-D__inline=',
           '-fbracket-depth=2048', '-w', '-o', 'check.bc', source]
    if is32bit:
        cmd.append('-m32')
    if run(cmd, stdout=PIPE, stderr=STDOUT).returncode != 0:
        dbg('Compiling the program for the check failed')
        return None
    cmd = ['opt', '-load', 'LLVMsbt.so', '-check-module', '-detect-atomics',
           '-detect-calls=' + ','.join(THREAD_API + errcalls),
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
       not funs - set(errcalls) <= MODELLED or\
       not _joins_without_result('check.bc'):
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
    if _writes_thread_parameter(text):
        dbg('A thread assigns its parameter')
        return None
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
