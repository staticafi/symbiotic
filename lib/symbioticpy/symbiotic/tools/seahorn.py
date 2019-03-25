try:
    from benchexec.tools.seahorn import Tool as SeaTool
except ImportError:
    from .. utils import dbg
    dbg('Using the fallback tool module')
    from .. benchexec.tools.seahorn import Tool as SeaTool

from . tool import SymbioticBaseTool

class SymbioticTool(SeaTool, SymbioticBaseTool):

    REQUIRED_PATHS = SeaTool.REQUIRED_PATHS

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._memsafety = self._options.property.memsafety()

    def llvm_version(self):
        return '5.0.2'

    def compilation_options(self):
        return ['-D__SEAHORN__', '-O1', '-Xclang',
                '-disable-llvm-optzns', '-fgnu89-inline']

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        assert self._options.property.assertions()

        return ['sea', '--mem=-1', '-m32', 'pf', '--step=large', '-g',
                '--horn-global-constraints=true', '--track=mem',
                '--horn-stats', '--enable-nondet-init', '--strip-extern',
                '--externalize-addr-taken-functions', '--horn-singleton-aliases=true',
                '--horn-pdr-contexts=600', '--devirt-functions',
                '--horn-ignore-calloc=false', '--enable-indvar',
                '--horn-answer', '--inline'] + options + tasks

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []

