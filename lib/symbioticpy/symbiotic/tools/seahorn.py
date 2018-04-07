try:
    from benchexec.tools.seahorn import Tool as SeaTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.seahorn import Tool as SeaTool

class SymbioticTool(SeaTool):

    REQUIRED_PATHS = SeaTool.REQUIRED_PATHS

    def llvm_version(self):
        return '3.6.2'

