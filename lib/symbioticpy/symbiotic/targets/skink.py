from symbiotic.utils.process import runcmd
from symbiotic.utils.watch import DbgWatch

try:
    from benchexec.tools.skink import Tool as SkinkTool
except ImportError:
    from .. benchexec.tools.skink import Tool as SkinkTool

class SymbioticTool(SkinkTool):

    REQUIRED_PATHS = SkinkTool.REQUIRED_PATHS

    def __init__(self, opts):
        self._options = opts

    def llvm_version(self):
        return '5.0.2'

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [self.executable(), '-f', 'LLVM'] + tasks

    def actions_before_verification(self, symbiotic):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        output = symbiotic.curfile + '.ll'
        runcmd(['llvm-dis', symbiotic.curfile, '-o', output], DbgWatch('all'))
        symbiotic.curfile = output

    def compilation_options(self):
        """
    List of compilation options specific for this tool
    """
        opts=[]
        if self._options.property.undefinedness():
                opts.append('-fsanitize=undefined')
                opts.append('-fno-sanitize=unsigned-integer-overflow')
        elif self._options.property.signedoverflow():
                opts.append('-fsanitize=signed-integer-overflow')
                opts.append('-fsanitize=shift')

        return opts

    # skink needs inlined procedures
    def passes_before_verification(self):
        return super().passes_before_verification() +\
                ['-strip-debug',
                '-inline-threshold=150000', '-inline', '-always-inline']

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []


