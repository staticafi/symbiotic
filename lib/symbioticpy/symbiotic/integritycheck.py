from sys import version_info
from . exceptions import SymbioticException
from . utils.utils import process_grep
from . utils.process import ProcessRunner
from . utils.watch import ProcessWatch

class IntegrityChecker(object):
    def __init__(self, versions):
        self._versions = versions
        self._process = ProcessRunner()

    def _decode(self, vers):
        if version_info < (3,0):
            return vers.decode('utf-8')
        else:
            return bytes(vers, 'utf-8')

    def _get_output(self, cmd):
        watch = ProcessWatch(1)
        retval = self._process.run(cmd, watch)
        assert retval == 0
        lines = watch.getLines()
        assert(len(lines) == 1)
        return lines


    def _get_klee_version(self):
        (retval, lines) = process_grep(['klee', '-version'], 'revision')
        assert retval == 0
        assert(len(lines) == 1)

        return lines[0].split(b':')[1].strip()

    def _get_slicer_version(self):
        lines = self._get_output(['sbt-slicer', '-version'])
        return lines[0].strip()[:8]

    def _get_instr_version(self):
        lines = self._get_output(['sbt-instr', '--version'])
        return lines[0].strip()[:8]
        return lines[0].strip()

    def _check(self, component, expected_version, actual_version):
        if expected_version != actual_version:
            raise SymbioticException("The version of '{0}' is different than expected (expect {1} but got {2})".\
                                     format(component, expected_version, actual_version))

    def check(self, verifier = None):
        """
        Check whether every module in Symbiotic agrees on versions
        stored in Symbiotic.
        """
        for (k, v) in self._versions.items():
            #print(k,v)
            if k == 'KLEE':
                # check KLEE only if we are using KLEE
                if verifier.startswith('klee'):
                    vers = self._get_klee_version()
                    expected = self._decode(v)
                    self._check(k, expected, vers)
            elif k == 'sbt-slicer':
                vers = self._get_slicer_version()
                expected = self._decode(v[:8])
                self._check(k, expected, vers)
            elif k == 'sbt-instrumentation':
                vers = self._get_instr_version()
                expected = self._decode(v[:8])
                self._check(k, expected, vers)

