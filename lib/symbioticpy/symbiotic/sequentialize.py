#!/usr/bin/env python3

import re
import sys
from os import listdir
from os.path import basename, dirname, isdir, isfile, join
from shutil import copyfile
from subprocess import run, PIPE, STDOUT, TimeoutExpired

from . utils import dbg
from . utils.utils import print_stdout

CSEQ_TIMEOUT = 120
# the first configuration of Lazy-CSeq's SV-COMP wrapper
CSEQ_OPTIONS = ['--sv-comp', '--threads', '100', '--atomic-parameters',
                '--deep-propagation', '--nondet-condvar-wakeups',
                '--backend', 'cpachecker',
                '--rounds', '2', '--unwind-while', '2', '--unwind-for', '2',
                # every thread creation calls __symbiotic_mark(creator << 16 |
                # created), which KLEE logs in the waypoints of the error path
                '--creation-markers']

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

# a failing assert of the program aborts it as abort() does, only the
# error calls are errors (CSeq gets them renamed to __VERIFIER_error)
ASSERT = '''\
extern void __VERIFIER_assume(int);
void __cs_seq_assert_fail(const char *a, const char *f, unsigned int l, const char *fn) { __VERIFIER_assume(0); }
#define __assert_fail __cs_seq_assert_fail
'''

# the program's own errors are pruned, the only error left is a race
RACE_PRELUDE = '''\
extern void __VERIFIER_assume(int);
void __cs_nonrace_fail(const char *a, const char *f, unsigned int l, const char *fn) { __VERIFIER_assume(0); }
void __cs_data_race(void) { reach_error(); }
#define __assert_fail __cs_nonrace_fail
#define assert(c) __VERIFIER_assume(c)
'''

def _keep_lines(replacement):
    return lambda m: replacement + '\n' * m.group().count('\n')

REWRITES = [
    # CSeq keeps static in parameter lists
    (r'(\(|, )static ', r'\1'),
    # CSeq leaves the variables that choose the context switches uninitialized
    (r'(?m)^([ \t]*unsigned int __cs_tmp_t\d+_r\d+);', r'\1 = __VERIFIER_nondet_uint();'),
    # glibc prototypes conflict with CSeq's definitions of pthread functions
    (r'extern\s+int\s+pthread_\w+\s*\([^;]*\)\s*;', _keep_lines(';')),
]

# calls of reach_error, not its definition; CSeq would turn them into
# assert(0), the same as an assert of the program
ERROR_REWRITES = [
    (r'(?<!void )(?<!void\t)(?<!void\n)\breach_error\s*\(\s*\)', '__VERIFIER_error()'),
]

RACE_REWRITES = [
    # calls of the error functions, not their definitions; CSeq's race
    # detector turns abort(), assert() and the error calls into __dummy__()
    (r'(?<!void )(?<!void\t)(?<!void\n)\b(__VERIFIER_error|reach_error|__dummy__)\s*\(\s*\)',
     '__VERIFIER_assume(0)'),
]

def _rewrite(text, rewrites):
    for pattern, replacement in rewrites:
        text = re.sub(pattern, replacement, text)
    return text

# KLEE then reports the lines of CSeq's output
def _line_marker(name):
    return '#line 1 "{0}"\n'.format(name)

def _postprocess(text, name):
    return PRELUDE + RENAMES + NOOPS + ASSERT + _line_marker(name) +\
           _rewrite(text, REWRITES)

def _postprocess_race(text, name):
    text = _rewrite(text, RACE_REWRITES)
    if '__CPROVER' in text:
        return None
    # the race detector declares its address variables repeatedly in one scope
    temps = sorted(set(re.findall(r'^\s*static void \*(__\w+___);', text, re.M)))
    text = re.sub(r'^\s*static void \*__\w+___;\n', _keep_lines(''), text,
                  flags=re.M)
    decls = ''.join('void *{0};\n'.format(t) for t in temps)
    return PRELUDE + RENAMES + NOOPS + RACE_PRELUDE + decls +\
           _line_marker(name) + _rewrite(text, REWRITES)

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

def _linemap(out):
    """ CSeq's -M table: line of its output -> line of its input """
    linemap = {}
    for line in out.splitlines():
        if line.startswith('.'):
            numbers = re.findall(r'-?\d+', line.split()[0])
            linemap.setdefault(int(numbers[0]), int(numbers[-1]))
    return linemap

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

def check(source, is32bit):
    """
    Check whether CSeq can sequentialize the program, that is, it creates
    threads and uses only the thread functions that CSeq models.
    """
    # most tasks have no threads, do not compile them for the check
    with open(source, errors='replace') as f:
        if 'pthread_create' not in f.read():
            return False
    cmd = ['clang', '-c', '-emit-llvm', '-g', '-fgnu89-inline', '-D__inline=',
           '-fbracket-depth=2048', '-w', '-o', 'check.bc', source]
    if is32bit:
        cmd.append('-m32')
    if run(cmd, stdout=PIPE, stderr=STDOUT).returncode != 0:
        dbg('Compiling the program for the check failed')
        return False
    cmd = ['opt', '-load', 'LLVMsbt.so', '-check-module', '-detect-atomics',
           '-detect-calls=' + ','.join(THREAD_API),
           '-enable-new-pm=0', '-disable-output', 'check.bc']
    out = run(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True).stdout

    funs = {line.split()[2] for line in out.splitlines()
            if line.startswith('Found function ')}
    return 'pthread_create' in funs and 'Found atomic instruction' not in out\
           and funs <= MODELLED and _joins_without_result('check.bc')

def _error_labels_are_errors(source):
    """
    Whether every label ERROR is followed by an error call, so that CSeq
    may replace it and the gotos to it by an error (CSeq's inliner does not
    rename labels, so a kept label in a function inlined twice is defined
    twice)
    """
    with open(source, errors='replace') as f:
        text = f.read()
    return all(re.match(r'\s*\{?\s*(reach_error|__VERIFIER_error)\s*\(\s*\)',
                        text[m.end():])
               for m in re.finditer(r'\bERROR\s*:', text))

def sequentialize(source, prp, is32bit, cseqdir, outdir):
    """
    Sequentialize the program with CSeq.
    Return the path to the sequentialized program and the map of its lines
    to the lines of the program, or None.
    """
    # CSeq writes _cs_<name>.c next to its input
    name = basename(source)
    copy = join(outdir, name)
    if prp.datarace():
        copyfile(source, copy)
    else:
        with open(source, encoding='latin-1', newline='') as f:
            text = _rewrite(f.read(), ERROR_REWRITES)
        with open(copy, 'w', encoding='latin-1', newline='') as f:
            f.write(text)
    if name.endswith('.i'):
        name = name[:-2] + '.c'

    cmd = [sys.executable, join(cseqdir, 'cseq.py'), '-i', copy, '-M'] +\
          CSEQ_OPTIONS
    if is32bit:
        cmd.append('--32')
    if prp.datarace():
        cmd.append('--data-race-check')
    elif not _error_labels_are_errors(source):
        # CSeq turns the label ERROR and the gotos to it into an error, also
        # if the label only marks cleanup code; then keep the label (the
        # race detector drops the label, so keep it in race mode)
        cmd += ['--error-label', '__cs_seq_no_error_label']
    try:
        out = run(cmd, cwd=cseqdir, stdout=PIPE, stderr=STDOUT,
                  timeout=CSEQ_TIMEOUT, universal_newlines=True,
                  errors='replace').stdout
    except TimeoutExpired:
        dbg('CSeq timed out')
        return None
    except OSError as e:
        print_stdout('INFO: Cannot run CSeq: {0}'.format(e), color='WHITE')
        return None
    name = '_cs_' + name
    cs = join(outdir, name)
    if not isfile(cs):
        dbg('CSeq failed')
        return None

    with open(cs, errors='replace') as f:
        text = f.read()
    if _writes_thread_parameter(text):
        dbg('A thread assigns its parameter')
        return None
    if prp.datarace():
        text = _postprocess_race(text, name)
    else:
        text = _postprocess(text, name)
    if text is None:
        dbg('Rewriting the race checks failed')
        return None
    seq = join(outdir, 'seq-' + name[4:])
    with open(seq, 'w') as f:
        f.write(text)
    if run(['clang', '-fsyntax-only', '-fgnu89-inline', '-Wno-everything', seq],
           stdout=PIPE, stderr=STDOUT).returncode != 0:
        dbg('The sequentialized program does not compile')
        return None
    return seq, _linemap(out)

def _creation_order(waypoints, name):
    """
    The creations of threads in the order of KLEE's run as (line, creating
    thread, created thread), or None: CSeq marks every creation on its
    line by __symbiotic_mark(creator << 16 | created) (--creation-markers)
    and KLEE logs the marks of the error path in its waypoints as
    @MARK:file:line:column:value, the file being CSeq's output (name)
    """
    if not isfile(waypoints):
        return None
    with open(waypoints) as f:
        marks = re.findall(r'^@MARK:(?:.*/)?{0}:(\d+):\d+:(\d+)$'.format(re.escape(name)),
                           f.read(), re.M)
    order, active = [], {0}
    for line, value in marks:
        creator, created = int(value) >> 16, int(value) & 0xffff
        if creator not in active or created in active:
            return None
        order.append((int(line), creator, created))
        active.add(created)
    return order

def _stack(kleedir):
    errs = sorted(f for f in listdir(kleedir) if f.endswith('.err'))\
           if isdir(kleedir) else []
    if not errs:
        return None, None
    with open(join(kleedir, errs[0])) as f:
        stack = re.findall(r'#\d+ in (\w+) \(.*\) at (\S+):(\d+)', f.read())
    return stack, join(kleedir, errs[0].split('.')[0] + '.waypoints')

def _race(text, stack, threads, name, waypoints):
    """ The racing accesses as (thread, line of text) and the variable """
    funs = [fun for fun, f, l in stack]
    if '__cs_data_race' not in funs:
        return None
    below = stack[funs.index('__cs_data_race') + 1:]
    if not below or below[0][1] != name:
        return None
    second = int(below[0][2])
    thread = next((threads[fun] for fun, f, l in below if fun in threads), None)
    # the check that fired names the other thread and the address
    check = next((m for m in (re.search(r'if \(__cs_thread_to_write_pos\[(\d+)\] == (\w+)\)',
                                       text[n - 1])
                              for n in range(second, max(0, second - 12), -1)) if m), None)
    if thread is None or check is None or not isfile(waypoints):
        return None
    k, addr = int(check.group(1)), check.group(2)

    # the last context switch chosen for thread k is the label where it stopped
    pc = None
    with open(waypoints) as f:
        for m in re.finditer(r'^__VERIFIER_nondet_\w+:(\d+):\d+:(-?\d+)$', f.read(), re.M):
            t = re.search(r'__cs_tmp_t(\d+)_r\d+', text[int(m.group(1)) - 1])
            if t and int(t.group(1)) == k:
                pc = m.group(2)
    fun = next((f for f, t in threads.items() if t == k), None)
    label = 'tmain_' if k == 0 else 't{0}_'.format(fun)
    stop = next((n for n, l in enumerate(text, 1)
                 if l.strip().startswith(label + str(pc) + ':')), None)
    if pc is None or fun is None or stop is None:
        return None

    # the write it is about to do is the statement after the last announcement
    write = re.compile(r'__cs_thread_to_write_pos\[{0}\] = \((.*)\);'.format(k))
    n = next((n for n in range(stop - 1, 0, -1) if write.search(text[n - 1])), None)
    if n is None or write.search(text[n - 1]).group(1) != addr:
        return None
    n += 1
    while n < len(text) and text[n - 1].strip() in ('', ';'):
        n += 1
    var = re.sub(r'^_+(cs_local_\w+?_|cs_param_\w+?_)?', '', addr).rstrip('_')
    return [(k, n), (thread, second)], [var, var.split('_')[-1], var.replace('_', '.')]

def violation(seq, linemap, kleedir, calls, race=False):
    """
    Find KLEE's error in the sequentialized program in the program.
    Return the creations of the threads on the path to the error and the
    errors, each as (thread, line), and the names to find the column of an error
    (the error calls or the racing variable), or None.
    """
    stack, waypoints = _stack(kleedir)
    if not stack:
        return None
    name = '_cs_' + basename(seq)[4:]
    with open(join(dirname(seq), name), errors='replace') as f:
        text = f.read().split('\n')

    threads = {'main_thread': 0}
    for line in text:
        for fun, k in re.findall(r'(\w+)\(__cs_threadargs\[(\d+)\]\)', line):
            threads[fun] = int(k)

    if race:
        found = _race(text, stack, threads, name, waypoints)
        if found is None:
            return None
        errors, calls = found
    else:
        line = next((int(l) for fun, f, l in stack
                     if f == name and linemap.get(int(l), -1) > 0), None)
        thread = next((threads[fun] for fun, f, l in stack if fun in threads), None)
        if line is None or thread is None:
            return None
        errors = [(thread, line)]

    # the witness numbers the threads in the order of their creation
    order = _creation_order(waypoints, name)
    if order is None:
        return None
    ids = {0: 0}
    ids.update((k, i) for i, (n, t, k) in enumerate(order, 1))
    if any(t not in ids for t, l in errors):
        return None
    # every creation KLEE logged happened on the path to the error, also
    # after the erring thread was created (an error in main may need the
    # writes of a thread created later)
    created = [(ids[t], linemap.get(n, -1)) for n, t, k in order]
    errors = [(ids[t], linemap.get(l, -1)) for t, l in errors]
    if any(l <= 0 for t, l in created + errors):
        return None
    return created, errors, calls
