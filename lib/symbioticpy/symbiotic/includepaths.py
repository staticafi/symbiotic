from . utils.process import ProcessRunner
from . utils.watch import ProcessWatch
from . utils import dbg
from . exceptions import SymbioticException

class IncludePathsSearcher:
    def __init__(self):
        self._paths = []

    def _get_include_paths(self, cmd):
        """
        Find paths where standard headers are located
        """
        pr = ProcessRunner()
        watch = ProcessWatch(lines_limit = None)
        if pr.run(cmd, watch) == 0:
            lines_iter = iter(watch.getLines())
            # find the beginning of include paths
            for line in lines_iter:
                if line == b'#include <...> search starts here:\n':
                    break

            for line in lines_iter:
                line = line.decode('ascii').strip()
                if line == 'End of search list.':
                    break
                else:
                    self._paths.append(line)

    def _get_cpp_include_paths(self):
        cmd = ['cpp', '-xc', '-v', '/dev/null']
        try:
            self._get_include_paths(cmd)
        except SymbioticException as e:
            dbg('Failed getting include paths: {0}'.format(str(e)))


    def _get_clang_include_paths(self):
        cmd = ['clang', '-E', '-xc', '-v', '/dev/null']
        try:
            self._get_include_paths(cmd)
        except SymbioticException as e:
            dbg('Failed getting include paths: {0}'.format(str(e)))

    def get(self):
        self._get_clang_include_paths()
        if not self._paths:
            self._get_cpp_include_paths()

        return self._paths

