#!/usr/bin/python

from . symbiotic import SymbioticException

class Property:
    def __init__(self, prpfile = None):
        self._prpfile = prpfile

    def memsafety(self):
        """ Check for memory safety violations """
        return False

    def signedoverflow(self):
        """ Check for signed integer overflows """
        return False

    def assertions(self):
        """ Check for assertion violations """
        return False

    def undefinedness(self):
        """ Check for undefined behavior """
        return False

class PropertyMemSafety(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def memsafety(self):
        return True


class PropertyNoOverflow(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def signedoverflow(self):
        return True


class PropertyDefBehavior(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def undefinedness(self):
        return True


class PropertyUnreachCall(Property):
    def __init__(self, prpfile = None):
        Property.__init__(self, prpfile)

    def assertions(self):
        return True

supported_properties = {
    'CHECK( init(main()), LTL(G ! call(__VERIFIER_error())) )' : 'REACHCALL',
    'CHECK( init(main()), LTL(G valid-free) )'                 : 'VALID-FREE',
    'CHECK( init(main()), LTL(G valid-deref) )'                : 'VALID-DEREF',
    'CHECK( init(main()), LTL(G valid-memtrack) )'             : 'MEM-TRACK',
    'CHECK( init(main()), LTL(G ! overflow) )'                 : 'SIGNED-OVERFLOW',
    'CHECK( init(main()), LTL(G def-behavior) )'               : 'UNDEF-BEHAVIOR',
    'valid-deref'                                              : 'VALID-DEREF',
    'valid-free'                                               : 'VALID-FREE',
    'valid-memtrack'                                           : 'MEM-TRACK',
    'null-deref'                                               : 'NULL-DEREF',
    'undefined-behavior'                                       : 'UNDEF-BEHAVIOR',
    'undef-behavior'                                           : 'UNDEF-BEHAVIOR',
    'signed-overflow'                                          : 'SIGNED-OVERFLOW',
    'memsafety'                                                : 'MEMSAFETY',
}



def _get_prp(prp):
    from os.path import abspath, expanduser, isfile
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


def _map_property(prps):
    mapped_prps = []
    try:
        for prp in prps:
            prp_key = supported_properties[prp]
            mapped_prps.append(prp_key)
    except KeyError as ke:
        raise SymbioticException('Unknown or unsupported property: {0}'.format(ke.message))

    return mapped_prps

def get_property(prp):
    if prp is None:
        return PropertyUnreachCall()

    prps, prpfile = _get_prp(prp)
    prps = _map_property(prps)

    if 'MEMSAFETY' in prps or\
       ('VALID-FREE' in prps and 'MEM-TRACK' in prps and 'VALID-DEREF' in prprs):
       return PropertyMemSafety(prpfile)

    if 'UNDEF-BEHAVIOR' is prps:
        return PropertyUnreachCall(prpfile)

    if 'SIGNED-OVERFLOW' in prps:
        return PropertyNoOverflow(prpfile)

    return None
