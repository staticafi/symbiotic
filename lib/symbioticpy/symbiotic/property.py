#!/usr/bin/python

from . exceptions import SymbioticException
from os.path import abspath, join

class Property:
    def __init__(self, prpfile = None):
        self._prpfile = prpfile
        # property as LTL formulae (if available)
        self._ltl = []

    def memsafety(self):
        """ Check for memory safety violations """
        return False

    def nullderef(self):
        """
        Check for null dereferences (this property is distinct from memsafety)
        """
        return False

    def memcleanup(self):
        """ Check for memory leaks """
        return False

    def signedoverflow(self):
        """ Check for signed integer overflows """
        return False

    def assertions(self):
        """ Check for assertion violations. Implies 'unreachcall' """
        return False

    def unreachcall(self):
        """ Check for unreachability of a function call """
        return False

    def undefinedness(self):
        """ Check for undefined behavior """
        return False

    def termination(self):
        """ Check termination """
        return False

    # FIXME: merge somehow with unreachcall
    def errorcall(self):
        """ Check for error calls """
        return False

    def coverage(self):
        """ Generate tests for coverage """
        return False

    def getPrpFile(self):
        return self._prpfile

    def ltl(self):
        """ Is the property described by a generic LTL formula(e)? """
        return self._ltl

    def help(self):
        return "unspecified property"

class PropertyNullDeref(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def nullderef(self):
        return True

    def help(self):
        return "null pointer dereferences"

class PropertyMemSafety(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def memsafety(self):
        return True

    def help(self):
        return "invalid dereferences, invalid free, memory leaks, etc."

class PropertyMemCleanup(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def memcleanup(self):
        return True

    def help(self):
        return "unfreed memory"


class PropertyNoOverflow(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def signedoverflow(self):
        return True

    def help(self):
        return "signed integer overflow"


class PropertyDefBehavior(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def undefinedness(self):
        return True

    def help(self):
        return "undefined behavior"


class PropertyUnreachCall(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)
        self.calls = ['reach_error'] # the default value

    def unreachcall(self):
        return True

    def getcalls(self):
        return self.calls

    def help(self):
        return "reachability of calls to {0}".format(",".join(self.calls))

class PropertyAssertions(PropertyUnreachCall):
    def __init__(self, prpfile = None):
        super().__init__(prpfile)
        self.calls = ['__assert_fail', '__VERIFIER_error']

    def assertions(self):
        return True

class PropertyTermination(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def termination(self):
        return True

    def help(self):
        return "non-terminating loops and recursion"

class PropertyCoverage(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def coverage(self):
        return True

    def coverStmts(self):
        return False

    def coverBranches(self):
        return False

    def coverConditions(self):
        return False

class PropertyCoverBranches(PropertyCoverage):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def coverBranches(self):
        return True

    def help(self):
        return "generating tests to maximize the coverage of branches"

class PropertyCoverConditions(PropertyCoverage):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def coverConditions(self):
        return True

    def help(self):
        return "generating tests to maximize the coverage of conditions"

class PropertyCoverStmts(PropertyCoverage):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def coverStmts(self):
        return True

    def help(self):
        return "generating tests to maximize the coverage of statements"

# FIXME: remove this in favor of UnreachCall
class PropertyErrorCall(PropertyCoverage):
    def __init__(self, calls=None, prpfile = None):
        Property.__init__(self, prpfile)
        self.calls = calls or ['reach_error'] # the default value

    def getcalls(self):
        return self.calls

    def errorcall(self):
        return True

    def help(self):
        return f"generating tests that cover calls of {' '.join(self.calls)}"

supported_ltl_properties = {
    'CHECK( init(main()), LTL(G ! call(__VERIFIER_error())) )'         : PropertyUnreachCall,
    'CHECK( init(main()), LTL(G valid-free) )'                         : PropertyMemSafety,
    'CHECK( init(main()), LTL(G valid-deref) )'                        : PropertyMemSafety,
    'CHECK( init(main()), LTL(G valid-memtrack) )'                     : PropertyMemSafety,
    'CHECK( init(main()), LTL(G valid-memcleanup) )'                   : PropertyMemCleanup,
    'CHECK( init(main()), LTL(G ! overflow) )'                         : PropertyNoOverflow,
    'CHECK( init(main()), LTL(G def-behavior) )'                       : PropertyDefBehavior,
    'CHECK( init(main()), LTL(F end) )'                                : PropertyTermination,
    'COVER( init(main()), FQL(COVER EDGES(@DECISIONEDGE)) )'           : PropertyCoverBranches,
    'COVER( init(main()), FQL(COVER EDGES(@CONDITIONEDGE)) )'          : PropertyCoverConditions,
    'COVER( init(main()), FQL(COVER EDGES(@BASICBLOCKENTRY)) )'        : PropertyCoverStmts,
    'COVER( init(main()), FQL(COVER EDGES(@CALL(__VERIFIER_error))) )' : PropertyErrorCall,
}

supported_properties = {
    'assert'                                                   : PropertyAssertions,
    'assertions'                                               : PropertyAssertions,
    'valid-deref'                                              : PropertyMemSafety,
    'valid-free'                                               : PropertyMemSafety,
    'valid-memtrack'                                           : PropertyMemSafety,
    'null-deref'                                               : PropertyNullDeref,
    'undefined-behavior'                                       : PropertyDefBehavior,
    'undef-behavior'                                           : PropertyDefBehavior,
    'undefined'                                                : PropertyDefBehavior,
    'signed-overflow'                                          : PropertyNoOverflow,
    'no-overflow'                                              : PropertyNoOverflow,
    'memsafety'                                                : PropertyMemSafety,
    'memcleanup'                                               : PropertyMemCleanup,
    'termination'                                              : PropertyTermination,
    'coverage'                                                 : PropertyCoverStmts,
    'cover-branches'                                           : PropertyCoverBranches,
    'cover-conditions'                                         : PropertyCoverConditions,
    'cover-statements'                                         : PropertyCoverStmts,
    'cover-error'                                              : PropertyErrorCall,
}

def _parse_prp(prp):
    from os.path import expanduser, isfile
    # if property is given in file, read the file
    epath = abspath(expanduser(prp))
    if isfile(epath):
        prp_list = []
        f = open(epath, 'r')
        for line in f.readlines():
            line = line.strip()
            # ignore empty lines
            if line:
                prp_list.append(line)
        f.close()
        return (prp_list, epath)

    # it is not a file, so it is given as a string
    # FIXME: this does not work for properties given
    # as LTL (there are spaces)
    return (prp.split(), None)

def _filter_properties(prps):
    keyword_prps = []
    ltl_prps = []
    other_prps = []
    for prp in prps:
        if prp in supported_properties:
            keyword_prps.append(prp)
        elif prp in supported_ltl_properties:
            ltl_prps.append(prp)
        else:
            other_prps.append(prp)

    return keyword_prps, ltl_prps, other_prps

def _report_unsupported(prps):
    msg  = 'Unknown or unsupported properties: {0}\n'.format(prps)
    msg += 'Supported properties are:\n'
    for k in supported_ltl_properties.keys():
        msg += '    {0}\n'.format(k)
    msg += "or use shortcuts:\n"
    for k in supported_properties.keys():
        msg += '    {0}\n'.format(k)
    msg += '\nBy default, we are looking just for assertion violations.\n'

    raise SymbioticException(msg)

def _create_keyword_props(prps, prpfile):
    retval = []
    for p in prps:
        retval.append(supported_properties[p](prpfile))
    return retval

def _create_ltl_props(prps, prpfile):
    retval = []
    for p in prps:
        retval.append(supported_ltl_properties[p](prpfile))
    return retval


def _get_simple_property(prps, prpfile):
    keyword_prps, ltl_prps, other_prps = _filter_properties(prps)

    properties = _create_keyword_props(keyword_prps, prpfile)
    properties += _create_ltl_props(ltl_prps, prpfile)

    return properties, other_prps

def _get_parametrized_property(prps, prpfile):
    unresolved = []
    retval = []
    for p in prps:
        # This should be sufficient for now...
        if p.startswith('CHECK( init(main()), LTL(G ! call'):
            suff = p[34:]
            fun = suff[:suff.find('()')]
            P = PropertyUnreachCall(prpfile)
            P.calls = [fun]
            retval.append(P)
        elif p.startswith('COVER( init(main()), FQL(COVER EDGES(@CALL('):
            suff = p[43:]
            fun = suff[:suff.find(')')]
            P = PropertyErrorCall(prpfile)
            P.calls = [fun]
            retval.append(P)
     
        else:
            unresolved.append(p)

    return retval, unresolved


def _assign_default_prpfile(p, symbiotic_dir):
    prpfile = abspath(join(symbiotic_dir, 'properties'))

    if p.unreachcall() or p.assertions():
        p._prpfile = join(prpfile, 'unreach-call.prp')
    elif p.memsafety():
        p._prpfile = join(prpfile, 'valid-memsafety.prp')
    elif p.memcleanup():
        p._prpfile = join(prpfile, 'valid-memcleanup.prp')
    elif p.nullderef():
        p._prpfile = join(prpfile, 'no-null-deref.prp')
    elif p.termination():
        p._prpfile = join(prpfile, 'termination.prp')
    elif p.signedoverflow():
        p._prpfile = join(prpfile, 'no-overflow.prp')
    elif p.undefinedness():
        p._prpfile = join(prpfile, 'def-behavior.prp')

    elif p.coverage():
        if p.coverBranches():
            p._prpfile = join(prpfile, 'coverage-branches.prp')
        elif p.coverConditions():
            p._prpfile = join(prpfile, 'coverage-conditions.prp')
        elif p.coverStmts():
            p._prpfile = join(prpfile, 'coverage-statements.prp')
        elif p.errorcall():
            p._prpfile = join(prpfile, 'coverage-error-call.prp')
        else:
            raise SymbioticException("unhandled covereage property: {0}".format(p))
    else:
        raise SymbioticException("unhandled property: {0}".format(p))

def _merge_memsafety_prop(properties):
    memsafety = None
    props = []
    for p in properties:
        if p.memsafety():
            if not memsafety:
                memsafety = p
                props.append(p)
        else:
            props.append(p)

    return props

def get_property(symbiotic_dir, prp):
    properties = []
    if prp is None:
        prop = PropertyAssertions()
        _assign_default_prpfile(prop, symbiotic_dir)
        # FIXME once we have multiprop
        #return [prop]
        return prop

    prps, prpfile = _parse_prp(prp)
    properties, unresolved = _get_simple_property(prps, prpfile)
    if unresolved:
        props, unresolved = _get_parametrized_property(unresolved, prpfile)
        if unresolved:
            _report_unsupported(";".join(unresolved))

        properties += props

    for p in properties:
        if p.getPrpFile() is None:
            _assign_default_prpfile(p, symbiotic_dir)
        if not p._ltl:
            p._ltl, _ = _parse_prp(p.getPrpFile())

    # FOR NOW squeeze all memsafety properties into one
    properties = _merge_memsafety_prop(set(properties))
    assert len(properties) == 1, "Multiple properties unsupported at this moment"
    return properties[0]
