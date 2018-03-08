try:
    from benchexec.tools.seahorn import Tool as SeaTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.seahorn import Tool as SeaTool

class SymbioticTool(SeaTool):

    REQUIRED_PATHS = SeaTool.REQUIRED_PATHS

    def llvm_version(self):
        return '3.6.2'

    def preprocess_llvm(self, infile):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        return (None, None)

    def prepare(self):
        """
        Prepare the bitcode for verification - return a list of
        LLVM passes that should be run on the code
        """
        return []

    def prepare_after(self):
        """
        Same as prepare, but runs after slicing
        """
        return []

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """
        pass

