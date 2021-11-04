#  try:
#      from benchexec.tools.divine4 import Tool as DivineTool
#  except ImportError:
#import symbiotic.benchexec.util as util
import symbiotic.benchexec.result as result
#from symbiotic.benchexec.tools.template import BaseTool
from .. benchexec.tools.divine4 import Tool as DivineTool
from . tool import SymbioticBaseTool

class SymbioticTool(DivineTool, SymbioticBaseTool):
    """
    DIVINE integrated into Symbiotic
    """

    def __init__(self, opts):
        SymbioticBaseTool.__init__(self, opts)
        self._memsafety = self._options.property.memsafety()

    def llvm_version(self):
        return '7.0.1'

    def set_environment(self, env, opts):
        """
        Set environment for the tool
        """
        opts.linkundef = []
        if opts.devel_mode:
            env.prepend('PATH', '{0}/divine'.\
                        format(env.symbiotic_dir))
        opts.is32bit = False

    def cc(self):
        #return ['divine', 'cc']
        return ['clang', '--target=x86_64-unknown-none-elf',
                '-fgnu89-inline', '-Os']

    def actions_before_slicing(self, symbiotic):
        symbiotic.link_undefined(['__VERIFIER_atomic_begin',
                                  '__VERIFIER_atomic_end'])

   # not needed anymore?
   #def actions_before_verification(self, symbiotic):
   #    # link the DiOS environment
   #    newfile = symbiotic.curfile[:-3] + '-cc' + symbiotic.curfile[-3:]
   #    symbiotic.command(['divine', 'cc', symbiotic.curfile, '-o', newfile])
   #    symbiotic.curfile = newfile

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        #return DivineTool.cmdline(self, executable, options, tasks, propertyfile, rlimits)

        prp = self._options.property
        cmd = ['divine', 'check',
               '--lart', 'stubs', '--lart', 'lowering',
               '--lart', 'svc-trace-nondets',
               '-o', 'ignore:exit', '-o', 'ignore:control',
               '--svcomp', '--sequential']
        if prp.unreachcall():
            cmd.extend(['-o', 'ignore:memory'])
        elif prp.memsafety():
            cmd.extend(['-o', 'ignore:diosassert',
                        '--leakcheck', 'exit,state'])
        cmd.extend(tasks)
        return cmd

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """
        if not output:
            return "no output"

        has_error = False
        has_memerr = False
        memerr = None
        res='no result'
        for line in map(str, output):
            if "error found: yes" in line:
                has_error = True
            if "error found: boot" in line:
                return result.RESULT_UNKNOWN
            if "error found: no" in line:
                if has_error:
                    return 'parsing error'
                has_error = False
            if "not implemented in userspace" in line:
                res = result.RESULT_UNKNOWN
            if "memory error in userspace" in line:
                has_memerr = True
            if "__vm_obj_free" in line:
                memerr = result.RESULT_FALSE_FREE
            if "out of bounds" in line:
                memerr = result.RESULT_FALSE_DEREF
            if "memory leak in userspace" in line:
                #if "heap" in fault:
                memerr = result.RESULT_FALSE_MEMTRACK
            if "assertion violation in userspace" in line:
                res = result.RESULT_FALSE_REACH
            if "verifier error called" in line:
                res = result.RESULT_FALSE_REACH

        if has_error:
            if has_memerr and memerr is not None:
                return memerr
            return res
        elif returncode != 0:
            return f'returned {returncode}'
        elif returnsignal != 0:
            return f'signal {returnsignal}'
        elif res == 'no result' and not has_memerr and memerr is None:
            return result.RESULT_TRUE_PROP

        return result.RESULT_UNKNOWN


