# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys

# CONSTANTS

# categorization of a run result
# 'correct' and 'wrong' refer to whether the tool's result matches the expected result.
# 'confirmed' and 'unconfirmed' refer to whether the tool's result was confirmed (e.g., by witness validation)
CATEGORY_CORRECT = 'correct'
"""run result given by tool is correct (we use 'correct' instead of 'correct-confirmed')"""

CATEGORY_CORRECT_UNCONFIRMED = 'correct-unconfirmed'
"""run result given by tool is correct but not confirmed"""

CATEGORY_WRONG   = 'wrong'
"""run result given by tool is wrong (we use 'wrong' instead of 'wrong-unconfirmed')"""

#CATEGORY_WRONG_CONFIRMED   = 'wrong-confirmed'
"""run result given by tool is wrong but confirmed by result validation"""

CATEGORY_UNKNOWN = 'unknown'
"""run result given by tool is "unknown" (i.e., no answer)"""

CATEGORY_ERROR   = 'error'
"""tool failed, crashed, or hit a resource limit"""

CATEGORY_MISSING = 'missing'
"""BenchExec could not determine whether run result was correct or wrong
because no property was defined, and no other categories apply."""


# internal property names used in this module (should not contain spaces)
# previously used by SV-COMP (http://sv-comp.sosy-lab.org/2014/rules.php):
_PROP_LABEL =        'unreach-label'
# currently used by SV-COMP (http://sv-comp.sosy-lab.org/2016/rules.php):
_PROP_CALL =         'unreach-call'
_PROP_TERMINATION =  'termination'
_PROP_OVERFLOW =     'no-overflow'
_PROP_DEADLOCK =     'no-deadlock'
_PROP_DEREF =        'valid-deref'
_PROP_FREE =         'valid-free'
_PROP_MEMTRACK =     'valid-memtrack'
_PROP_MEMCLEANUP =     'valid-memcleanup'
# for Java verification:
_PROP_ASSERT =       'assert'
# specification given as an automaton:
_PROP_AUTOMATON =    'observer-automaton'
# for solvers:
_PROP_SAT =          'sat'
# internal meta property
_PROP_MEMSAFETY =    'valid-memsafety'

# possible run results (output of a tool)
RESULT_DONE =               'done'
"""tool terminated properly and true/false does not make sense"""
RESULT_UNKNOWN =            'unknown'
"""tool could not find out an answer due to incompleteness"""
RESULT_ERROR =              'ERROR' # or any other value not listed here
"""tool could not complete due to an error
(it is recommended to instead use a string with more details about the error)"""
RESULT_TRUE_PROP =          'true'
"""property holds"""
RESULT_FALSE_PROP = 'false'
"""property does not hold"""
RESULT_FALSE_REACH =        RESULT_FALSE_PROP + '(' + _PROP_CALL + ')'
_RESULT_FALSE_REACH_OLD =   RESULT_FALSE_PROP + '(reach)'
"""SV-COMP reachability property violated"""
RESULT_FALSE_TERMINATION =  RESULT_FALSE_PROP + '(' + _PROP_TERMINATION + ')'
"""SV-COMP termination property violated"""
RESULT_FALSE_OVERFLOW =     RESULT_FALSE_PROP + '(' + _PROP_OVERFLOW    + ')'
"""SV-COMP overflow property violated"""
RESULT_FALSE_DEADLOCK =     RESULT_FALSE_PROP + '(' + _PROP_DEADLOCK    + ')'
"""deadlock property violated""" # not yet part of SV-COMP
RESULT_FALSE_DEREF =        RESULT_FALSE_PROP + '(' + _PROP_DEREF       + ')'
"""SV-COMP valid-deref property violated"""
RESULT_FALSE_FREE =         RESULT_FALSE_PROP + '(' + _PROP_FREE        + ')'
"""SV-COMP valid-free property violated"""
RESULT_FALSE_MEMTRACK =     RESULT_FALSE_PROP + '(' + _PROP_MEMTRACK    + ')'
"""SV-COMP valid-memtrack property violated"""
RESULT_FALSE_MEMCLEANUP =   RESULT_FALSE_PROP + '(' + _PROP_MEMCLEANUP  + ')'
"""SV-COMP valid-memcleanup property violated"""
RESULT_WITNESS_CONFIRMED =  'witness confirmed'
"""SV-COMP property violated and witness confirmed"""
RESULT_SAT =                'sat'
"""task is satisfiable"""
RESULT_UNSAT =              'unsat'
"""task is unsatisfiable"""

# List of all possible results.
# If a result is not in this list, it is handled as RESULT_CLASS_ERROR.
RESULT_LIST = [RESULT_TRUE_PROP, RESULT_UNKNOWN,
               RESULT_FALSE_PROP,
               RESULT_FALSE_REACH,
               _RESULT_FALSE_REACH_OLD,
               RESULT_FALSE_TERMINATION,
               RESULT_FALSE_DEREF, RESULT_FALSE_FREE, RESULT_FALSE_MEMTRACK,
               RESULT_FALSE_MEMCLEANUP,
               RESULT_WITNESS_CONFIRMED,
               RESULT_SAT, RESULT_UNSAT,
               RESULT_FALSE_OVERFLOW, RESULT_FALSE_DEADLOCK,
               RESULT_DONE
               ]

# Classification of results
RESULT_CLASS_TRUE    = 'true'
RESULT_CLASS_FALSE   = 'false'
RESULT_CLASS_UNKNOWN = 'unknown'
RESULT_CLASS_ERROR   = 'error'

# This maps content of property files to property name.
_PROPERTY_NAMES = {'LTL(G ! label(':                    _PROP_LABEL,
                   'LTL(G ! call(__VERIFIER_error()))': _PROP_CALL,
                   'LTL(F end)':                        _PROP_TERMINATION,
                   'LTL(G valid-free)':                 _PROP_FREE,
                   'LTL(G valid-deref)':                _PROP_DEREF,
                   'LTL(G valid-memtrack)':             _PROP_MEMTRACK,
                   'LTL(G valid-memcleanup)':           _PROP_MEMCLEANUP,
                   'OBSERVER AUTOMATON':                _PROP_AUTOMATON,
                   'SATISFIABLE':                       _PROP_SAT,
                   'LTL(G ! overflow)':                 _PROP_OVERFLOW,
                   'LTL(G ! deadlock)':                 _PROP_DEADLOCK,
                  }

# This maps a possible result substring of a file name
# to the expected result string of the tool and the set of properties
# for which this result is relevant.
_FILE_RESULTS = {
              '_true-unreach-label':   (RESULT_TRUE_PROP, {_PROP_LABEL}),
              '_true-unreach-call':    (RESULT_TRUE_PROP, {_PROP_CALL}),
              '_true_assert':          (RESULT_TRUE_PROP, {_PROP_ASSERT}),
              '_true-termination':     (RESULT_TRUE_PROP, {_PROP_TERMINATION}),
              '_true-valid-deref':     (RESULT_TRUE_PROP, {_PROP_DEREF}),
              '_true-valid-free':      (RESULT_TRUE_PROP, {_PROP_FREE}),
              '_true-valid-memtrack':  (RESULT_TRUE_PROP, {_PROP_MEMTRACK}),
              '_true-valid-memcleanup':(RESULT_TRUE_PROP, {_PROP_MEMCLEANUP}),
              '_true-valid-memsafety': (RESULT_TRUE_PROP, {_PROP_DEREF, _PROP_FREE, _PROP_MEMTRACK}),
              '_true-no-overflow':     (RESULT_TRUE_PROP, {_PROP_OVERFLOW}),
              '_true-no-deadlock':     (RESULT_TRUE_PROP, {_PROP_DEADLOCK}),

              '_false-unreach-label':  (RESULT_FALSE_REACH,       {_PROP_LABEL}),
              '_false-unreach-call':   (RESULT_FALSE_REACH,       {_PROP_CALL}),
              '_false_assert':         (RESULT_FALSE_REACH,       {_PROP_ASSERT}),
              '_false-termination':    (RESULT_FALSE_TERMINATION, {_PROP_TERMINATION}),
              '_false-valid-deref':    (RESULT_FALSE_DEREF,       {_PROP_DEREF}),
              '_false-valid-free':     (RESULT_FALSE_FREE,        {_PROP_FREE}),
              '_false-valid-memtrack': (RESULT_FALSE_MEMTRACK,    {_PROP_MEMTRACK}),
              '_false-valid-memcleanup':(RESULT_FALSE_MEMCLEANUP, {_PROP_MEMCLEANUP}),
              '_false-no-overflow':    (RESULT_FALSE_OVERFLOW,    {_PROP_OVERFLOW}),
              '_false-no-deadlock':    (RESULT_FALSE_DEADLOCK,    {_PROP_DEADLOCK}),

              '_sat':                  (RESULT_SAT,   {_PROP_SAT}),
              '_unsat':                (RESULT_UNSAT, {_PROP_SAT}),
              }

_MEMSAFETY_SUBPROPERTIES = {_PROP_DEREF, _PROP_FREE, _PROP_MEMTRACK}

# Map a property to all possible results for it.
_VALID_RESULTS_PER_PROPERTY = {
    _PROP_ASSERT:      {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_REACH},
    _PROP_LABEL:       {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_REACH},
    _PROP_CALL:        {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_REACH},
    _PROP_AUTOMATON:   {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_REACH},
    _PROP_DEREF:       {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_DEREF},
    _PROP_FREE:        {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_FREE},
    _PROP_MEMTRACK:    {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_MEMTRACK},
    _PROP_MEMSAFETY:   {RESULT_TRUE_PROP, RESULT_FALSE_DEREF, RESULT_FALSE_FREE, RESULT_FALSE_MEMTRACK},
    _PROP_MEMCLEANUP:  {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_MEMCLEANUP},
    _PROP_OVERFLOW:    {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_OVERFLOW},
    _PROP_DEADLOCK:    {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_DEADLOCK},
    _PROP_TERMINATION: {RESULT_TRUE_PROP, RESULT_FALSE_PROP, RESULT_FALSE_TERMINATION},
    _PROP_SAT:         {RESULT_SAT, RESULT_UNSAT},
    }

