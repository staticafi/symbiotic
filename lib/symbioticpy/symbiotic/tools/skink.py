try:
    from benchexec.tools.skink import Tool as SkinkTool
except ImportError:
    print('Using the fallback tool module')
    from .. benchexec.tools.skink import Tool as SkinkTool

class SymbioticTool(SkinkTool):

    REQUIRED_PATHS = SkinkTool.REQUIRED_PATHS

    def llvm_version(self):
        return '5.0.1'

