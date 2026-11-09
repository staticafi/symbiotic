"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2016-2019  Marek Chalupa
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from os.path import dirname
from time import time

from symbiotic.utils import dbg
from symbiotic.utils.process import ProcessRunner
from symbiotic.utils.watch import ProcessWatch
from symbiotic.utils.utils import print_stdout, print_stderr
from symbiotic.exceptions import SymbioticException

from . klee import SymbioticTool as KleeTool
from . kleebase import generate_yaml_witness


class ReverserWatch(ProcessWatch):
    """ Parse output of reversing """

    def __init__(self):
        # keep the tail of the output to show it if reversing fails
        ProcessWatch.__init__(self, 100)

    def parse(self, line):
        if b'INFO' in line:
            print_stdout(line.decode('utf-8'), print_nl=False, prefix="[reverser] ")
        elif b'ERROR' in line or b'error' in line:
            print_stderr(line.decode('utf-8'))
        elif b'Unsupported' in line:
            pass
        else:
            dbg(line.decode('utf-8'), domain='reverser', print_nl=False,
                prefix='', color=None)


class SymbioticTool(KleeTool):
    """
    Reverse the program using reverser and run KLEE on the reversed program.
    Supports only the unreach-call property.
    """

    def __init__(self, opts):
        KleeTool.__init__(self, opts)
        # the file produced by 'reverser --error-ids', mapping ids of error locations 
        # from the reversed program returned by
        # __reverser_error_id() to the original error locations
        self._error_ids_file = None

    def name(self):
        return 'revklee'

    def additional_executables(self):
        return ['reverser']

    def can_replay(self):
        # the error path is found in the reversed program,
        # it cannot be replayed on the original program
        return False

    def actions_before_verification(self, symbiotic):
        if not symbiotic.options.property.unreachcall():
            raise SymbioticException("reverser supports only the unreach-call property")

        curfile = symbiotic.curfile
        output = '{0}-rev.bc'.format(curfile[:curfile.rfind('.')])
        error_ids = '{0}.error-ids'.format(output[:output.rfind('.')])

        cmd = []
        if self._options.reverser_timeout > 0:
            cmd = ['timeout', str(self._options.reverser_timeout)]
        cmd += ['reverser', '--bc', '-o', output, '--error-ids', error_ids, '--status']
        if not self._options.property.assertions():
            cmd.append('--sv-comp')
        cmd.append(curfile)

        print_stdout('INFO: Starting reverser', color='WHITE')
        start = time()
        watch = ReverserWatch()
        retval = ProcessRunner().run(cmd, watch)
        elapsed = time() - start
        if retval != 0:
            for line in watch.getLines():
                print_stderr(line.decode('utf-8'), color='RED', print_nl=False)
            print_stdout('INFO: Reverser [FAILED] time: {0:.2f} s'.format(elapsed), color='WHITE')
            raise SymbioticException("cannot reverse")

        print_stdout('INFO: Reverser time: {0:.2f} s'.format(elapsed), color='WHITE')
        symbiotic.curfile = output
        self._error_ids_file = error_ids

    def generate_witness(self, llvmfile, sources, has_error):
        # GraphML witnesses are deprecated, generate only YAML witnesses
        if self._options.witness_output:
            generate_yaml_witness(dirname(llvmfile), sources, not has_error,
                                  self._options, self._options.witness_output,
                                  reverser_error_ids=self._error_ids_file)

    def generate_exec_witness(self, bitcode, sources):
        # the harness is generated for the reversed program
        dbg('Executable witnesses are not supported with reverser')
