try:
    from benchexec.tools.smack import Tool as SmackTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.smack import Tool as SmackTool

class SymbioticTool(SmackTool):
    """
    SMACK integrated into Symbiotic
    """

    REQUIRED_PATHS = SmackTool.REQUIRED_PATHS

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

