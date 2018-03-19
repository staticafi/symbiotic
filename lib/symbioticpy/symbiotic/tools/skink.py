try:
    from benchexec.tools.skink import Tool as SkinkTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.skink import Tool as SkinkTool

class SymbioticTool(SkinkTool):

    REQUIRED_PATHS = SkinkTool.REQUIRED_PATHS

    def llvm_version(self):
        return '3.7.1'

    def compilation_options(self):
    	"""
	List of compilation options specific for this tool
	"""
        pass

    def preprocess_llvm(self, infile):
        """
        A tool's specific preprocessing steps for llvm file
        before verification itself. Returns a pair (cmd, outputfile),
        where cmd is the list suitable to pass to Popen and outputfile
        is the resulting file from the preprocessing
        """
        output = infile + '.ll'
        return (['llvm-dis', infile, '-o', output], output)

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

