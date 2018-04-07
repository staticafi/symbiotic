try:
    from benchexec.tools.skink import Tool as SkinkTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.skink import Tool as SkinkTool

class SymbioticTool(SkinkTool):

    REQUIRED_PATHS = SkinkTool.REQUIRED_PATHS

    def llvm_version(self):
        return '3.7.1'

    def preprocess_llvm(self, infile):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        output = infile + '.ll'
        return (['llvm-dis', infile, '-o', output], output)

