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

