from sys import version_info
from symbiotic import SymbioticException
from symbiotic.utils.utils import process_grep
from symbiotic.utils.process import ProcessRunner
from symbiotic.utils.watch import ProcessWatch

class IntegrityChecker(object):
    def __init__(self, versions):
        self._versions = versions

    def _decode(vers):
        print('decoding', vers)
        if version_info < (3,0):
            return vers.decode('utf-8')
        else:
            return bytes(vers, 'utf-8')

    def get_klee_version():
        (retval, lines) = process_grep(['klee', '-version'], 'revision')
        assert retval == 0
        assert(len(lines) == 1)

        return lines[0].split(b':')[1].strip()

    def get_slicer_version():
        pr = ProcessRunner(['sbt-slicer', '-version'], ProcessWatch(1))
        retval = pr.run()
        assert retval == 0
        lines = pr.getOutput()
        assert(len(lines) == 1)

        return lines[0].strip()[:8]

    def get_instr_version():
        pr = ProcessRunner(['sbt-instr', '--version'], ProcessWatch(1))
        retval = pr.run()
        assert retval == 0
        lines = pr.getOutput()
        assert(len(lines) == 1)

        return lines[0].strip()

    def _check(component, expected_version, actual_version):
        if expected_version != actual_version:
            raise SymbioticException("The version of '{0}' is different than expected (expect {1} but got {2})".\
                                     format(component, expected_version, actual_version))

    def check(self):
        """
        Check whether every module in Symbiotic agrees on versions
        stored in Symbiotic.
        """
        for (k, v) in self._versions.items():
            #print(k,v)
            if k == 'KLEE':
                vers = IntegrityChecker.get_klee_version()
                expected = IntegrityChecker._decode(v)
                IntegrityChecker._check(k, expected, vers)
            elif k == 'sbt-slicer':
                vers = IntegrityChecker.get_slicer_version()
                expected = IntegrityChecker._decode(v)
                IntegrityChecker._check(k, expected, vers)
            elif k == 'sbt-instrumentation':
                vers = IntegrityChecker.get_instr_version()
                expected = IntegrityChecker._decode(v[:8])
                IntegrityChecker._check(k, expected, vers)

