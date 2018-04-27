try:
    from benchexec.tools.skink import Tool as SkinkTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.skink import Tool as SkinkTool

class SymbioticTool(SkinkTool):

    REQUIRED_PATHS = SkinkTool.REQUIRED_PATHS

    def __init__(self, opts):
        self._options = opts

    def llvm_version(self):
        return '5.0.1'

    def preprocess_llvm(self, infile):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        output = infile + '.ll'
        return (['llvm-dis', infile, '-o', output], output)

    def compilation_options(self):
        """
    List of compilation options specific for this tool
    """
                #'-target','i386-pc-linux-gnu','-m32','-O2',
        opts = ['-Wno-implicit-function-declaration','-Wno-incompatible-library-redeclaration','-fno-vectorize',
                '-fno-slp-vectorize','-gline-tables-only','-Xclang','-disable-lifetime-markers','-Rpass=.*','-Rpass-missed=.*',
                '-Rpass-analysis=.*','-mllvm','-inline-threshold=15000','-Dassert=__VERIFIER_assert']
        if self._options.property.undefinedness():
                opts.append('-fsanitize=undefined')
                opts.append('-fno-sanitize=unsigned-integer-overflow')
        elif self._options.property.signedoverflow():
                opts.append('-fsanitize=signed-integer-overflow')
                opts.append('-fsanitize=shift')

        return opts

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        # do not link any functions
        opts.linkundef = []


