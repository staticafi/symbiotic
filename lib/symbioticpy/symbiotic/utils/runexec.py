#!/usr/bin/env python3
"""
Helpers for running verification back-ends under BenchExec's runexec, to
limit their resources
"""

import os
import shutil
from subprocess import run, PIPE, STDOUT, DEVNULL

from . utils import dbg, print_stderr

# memory reserved for symbiotic itself and for runexec
_RESERVED_MEMORY = 512 * 1024 * 1024
_MIN_BACKEND_MEMORY = 128 * 1024 * 1024

_runexec_usable = None


def parse_memory_size(s):
    """
    Parse memory size such as '8000000000', '8000M', '8000MB', '8G', '8GB'.
    Returns the number of bytes.
    """
    s = s.strip().upper()
    if s.endswith('B'):
        s = s[:-1]
    mult = 1
    for suffix, m in (('K', 1024), ('M', 1024 ** 2), ('G', 1024 ** 3), ('T', 1024 ** 4)):
        if s.endswith(suffix):
            s = s[:-1]
            mult = m
            break
    return int(float(s) * mult)


def find_runexec():
    return shutil.which('runexec')


class _DelegatedCgroup:
    """
    runexec (BenchExec) can use a cgroup (v2) only if all processes in it
    are its descendants. Symbiotic itself is usually in the cgroup that
    we could use (e.g., when running under BenchExec or in a delegated systemd
    scope), so we move symbiotic into a child cgroup, enable controllers
    in the (now empty) cgroup and start each runexec in a fresh child cgroup.
    """
    def __init__(self):
        self.path = None
        self._counter = 0

    @staticmethod
    def _own_cgroup():
        try:
            with open('/proc/self/cgroup', 'r') as f:
                lines = [l.strip() for l in f if l.strip()]
            mount = None
            with open('/proc/mounts', 'r') as f:
                for l in f:
                    l = l.split()
                    if len(l) > 2 and l[2] == 'cgroup2':
                        mount = l[1]
                        break
        except OSError:
            return None
        # we support only the pure cgroup v2 hierarchy
        if mount is None or len(lines) != 1 or not lines[0].startswith('0::'):
            return None
        path = os.path.join(mount, lines[0][3:].lstrip('/'))
        # Do not mess with the real root cgroup. We may still see our cgroup
        # as the root if we are in a cgroup namespace (e.g., when running in
        # a BenchExec container). Only non-root cgroups have cgroup.freeze.
        if not os.path.exists(os.path.join(path, 'cgroup.freeze')):
            return None
        return path

    def setup(self):
        cgroup = self._own_cgroup()
        if cgroup is None:
            dbg('runexec: not in a usable cgroup v2')
            return False
        try:
            with open(os.path.join(cgroup, 'cgroup.controllers')) as f:
                controllers = f.read().split()
            if 'memory' not in controllers:
                dbg('runexec: memory controller not available in {0}'.format(cgroup))
                return False

            main = os.path.join(cgroup, 'symbiotic_main_{0}'.format(os.getpid()))
            os.mkdir(main)
            # move all processes (symbiotic and possibly its parents
            # in this cgroup) into the child cgroup
            with open(os.path.join(cgroup, 'cgroup.procs')) as f:
                pids = f.read().split()
            for pid in pids:
                try:
                    with open(os.path.join(main, 'cgroup.procs'), 'w') as f:
                        f.write(pid)
                except ProcessLookupError:
                    pass # the process already terminated
            # enable controllers for child cgroups
            wanted = [c for c in ('cpuset', 'cpu', 'io', 'memory', 'pids')
                      if c in controllers]
            with open(os.path.join(cgroup, 'cgroup.subtree_control'), 'w') as f:
                f.write(' '.join('+' + c for c in wanted))
        except OSError as e:
            dbg('runexec: cannot set up cgroup {0}: {1}'.format(cgroup, e))
            return False

        dbg('runexec: using cgroup {0}'.format(cgroup))
        self.path = cgroup
        return True

    def new_child(self):
        if self.path is None:
            return None
        self._counter += 1
        child = os.path.join(self.path, 'symbiotic_backend_{0}_{1}'\
                             .format(os.getpid(), self._counter))
        try:
            os.mkdir(child)
        except OSError as e:
            dbg('runexec: cannot create cgroup {0}: {1}'.format(child, e))
            return None
        return child

    @staticmethod
    def remove_child(child):
        if child is None:
            return
        # runexec leaves (empty) sub-cgroups in the cgroup,
        # remove them bottom-up
        try:
            for root, dirs, _ in os.walk(child, topdown=False):
                for d in dirs:
                    os.rmdir(os.path.join(root, d))
            os.rmdir(child)
        except OSError as e:
            dbg('runexec: cannot remove cgroup {0}: {1}'.format(child, e))


_cgroup = _DelegatedCgroup()


def new_cgroup():
    """
    Create a fresh cgroup in which runexec should be started
    (or return None if runexec should be started in the current cgroup)
    """
    return _cgroup.new_child()


def remove_cgroup(cgroup):
    _cgroup.remove_child(cgroup)


def _probe_runexec(runexec, cgroup):
    def preexec():
        if cgroup:
            with open(os.path.join(cgroup, 'cgroup.procs'), 'w') as f:
                f.write('0')
    try:
        p = run([runexec, '--no-container', '--quiet',
                 '--memlimit', str(_MIN_BACKEND_MEMORY),
                 '--output', os.devnull, '--', 'true'],
                stdout=PIPE, stderr=STDOUT, stdin=DEVNULL, timeout=60,
                preexec_fn=preexec)
    except Exception as e:
        return False, str(e)
    out = p.stdout.decode('utf-8', 'replace')
    return p.returncode == 0 and 'returnvalue=0' in out, out


def runexec_usable():
    """
    Check that runexec is available and that it can enforce a memory limit
    """
    global _runexec_usable
    if _runexec_usable is not None:
        return _runexec_usable

    _runexec_usable = False
    runexec = find_runexec()
    if runexec is None:
        print_stderr('WARNING: runexec not found, verification back-ends '
                     'will run without a memory limit', color='BROWN')
        return False

    # first try to prepare a cgroup for runexec inside our cgroup
    # (so that the back-end stays within the limits imposed on symbiotic),
    # otherwise try whether runexec works as it is (e.g., if it uses
    # systemd to get a cgroup)
    ok, out = False, ''
    if _cgroup.setup():
        cgroup = new_cgroup()
        ok, out = _probe_runexec(runexec, cgroup)
        remove_cgroup(cgroup)
        if not ok:
            _cgroup.path = None
    if not ok:
        ok, out = _probe_runexec(runexec, None)

    if ok:
        _runexec_usable = True
    else:
        print_stderr('WARNING: runexec is not usable (cgroups not available?), '
                     'verification back-ends will run without a memory limit',
                     color='BROWN')
        dbg('runexec output:\n{0}'.format(out))
    return _runexec_usable


def _cgroup_memory_limit():
    """
    Return the tightest memory limit set on the cgroup (v2 or v1)
    of this process or on any of its ancestors, or None.
    """
    limits = []
    try:
        with open('/proc/self/cgroup', 'r') as f:
            entries = [l.strip().split(':', 2) for l in f if l.strip()]
    except OSError:
        return None

    for hid, controllers, path in entries:
        if hid == '0' and controllers == '':
            # cgroup v2
            base, fname = '/sys/fs/cgroup', 'memory.max'
        elif 'memory' in controllers.split(','):
            # cgroup v1
            base, fname = '/sys/fs/cgroup/memory', 'memory.limit_in_bytes'
        else:
            continue

        path = path.lstrip('/')
        while True:
            try:
                with open(os.path.join(base, path, fname), 'r') as f:
                    val = f.read().strip()
                if val != 'max':
                    limits.append(int(val))
            except (OSError, ValueError):
                pass
            if not path:
                break
            path = os.path.dirname(path)

    return min(limits) if limits else None


def _total_memory():
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def default_backend_memlimit():
    """
    Memory available to symbiotic minus a reserve for symbiotic itself.
    """
    avail = [m for m in (_cgroup_memory_limit(), _total_memory()) if m]
    if not avail:
        return None
    return max(min(avail) - _RESERVED_MEMORY, _MIN_BACKEND_MEMORY)


def backend_memlimit(opts):
    """
    Get the memory limit (in bytes) for back-ends, or None if the back-ends
    should not be run under runexec.
    """
    limit = opts.backend_memlimit
    if limit == 0:
        return None
    if not runexec_usable():
        return None
    if limit is None:
        limit = default_backend_memlimit()
    return limit


def runexec_cmd(cmd, memlimit, outputfile):
    """
    Wrap the command so that it runs under runexec with the given memory limit.
    """
    runexec = [find_runexec(), '--no-container', '--quiet',
               '--memlimit', str(memlimit),
               '--output', outputfile, '--']
    # runexec overrides HOME and TMPDIR, keep the original values
    envvars = ['{0}={1}'.format(var, os.environ[var])
               for var in ('HOME', 'TMPDIR', 'TMP', 'TEMP')
               if var in os.environ]
    if envvars:
        runexec += ['env'] + envvars
    return runexec + cmd


def parse_runexec_result(lines):
    """
    Parse key=value lines printed by runexec.
    """
    result = {}
    for line in lines:
        line = line.decode('utf-8', 'replace').strip()
        key, sep, val = line.partition('=')
        if sep and key and ' ' not in key:
            result[key] = val
    return result


def read_runexec_output(outputfile):
    """
    Read the output of the tool from the file written by runexec,
    skipping the header that runexec puts there.
    """
    try:
        with open(outputfile, 'rb') as f:
            lines = f.readlines()
    except OSError:
        return []

    # runexec writes the command line, empty lines and a line of dashes
    # before the output of the tool
    for n, line in enumerate(lines[:20]):
        if line.strip() == b'-' * 80:
            lines = lines[n + 1:]
            if lines and lines[0].strip() == b'':
                lines = lines[1:]
            break
    return lines
