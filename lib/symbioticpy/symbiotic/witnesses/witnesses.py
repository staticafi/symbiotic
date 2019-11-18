#!/usr/bin/python

from os.path import basename
from sys import version_info
from hashlib import sha256 as hashfunc
from struct import unpack

from sys import version_info
if version_info < (3, 0):
    from io import open

import re

no_lxml = False
try:
    from lxml import etree as ET
except ImportError:
    no_lxml = True

if no_lxml:
    # if this fails, then we're screwed, so let the script die
    from xml.etree import ElementTree as ET


def get_hash(source):
    f = open(source, 'r', encoding='utf-8')
    hsh = hashfunc()
    for l in f:
        hsh.update(l.encode('utf-8'))

    f.close()
    return hsh.hexdigest()


def get_repr(obj):
    ret = []
    if not len(obj[1]) > 0:
        return ()

    b = obj[1][0]
    num = 1
    for i in range(1, len(obj[1])):
        if obj[1][i] != b:
            ret.append((b, num))
            b = obj[1][i]
            num = 1
        else:
            num += 1

    ret.append((b, num))
    return ret

def is_zero(obj):
    assert len(obj[1]) > 0

    for i in range(1, len(obj[1])):
        b = obj[1][i]
        if version_info.major < 3:
            value = ord(b)
        else:
            value = b
        if value != 0:
            return False

    return True

def get_nice_repr(obj):
    bytes_num = len(obj[1])
    rep = ''
    if bytes_num == 8:
        val = unpack('l', obj[1])[0]
        rep = "i64: {0}".format(val)
    elif bytes_num == 4:
        val = unpack('i', obj[1])[0]
        rep = "i32: {0}".format(val)
    elif bytes_num == 2:
        # unpack needs a buffer of size 4 for an integer
        val = unpack('h', obj[1])[0]
        rep = "i16: {0}".format(val)
    elif bytes_num == 1:
        # unpack needs a buffer of size 4 for an integer
        val = unpack('b', o[1])[0]
        rep = "bool: {0}".format(val)
    else:
        return ''

    return rep


def print_object(obj):
    rep = 'len {0} bytes, ['.format(len(obj[1]))
    objrepr = get_repr(obj)
    if objrepr == ():
        assert(len(obj[1]) == 0)
        rep += "|"

    l = len(objrepr)
    for n in range(0, l):
        part  = objrepr[n]
        if version_info.major < 3:
            value = ord(part[0])
        else:
            value = part[0]

        value = hex(value)

        if part[1] > 1:
            rep += '{0} times {1}'.format(part[1], value)
        else:
            rep += '{0}'.format(value)
        if n == l - 1:
            rep += ']'
        else:
            rep += '|'
    nice_rep = get_nice_repr(obj)
    if nice_rep:
        rep += " ({0})".format(nice_rep)
    print('{0} := {1}'.format(obj[0], rep))


class GraphMLWriter(object):
    def __init__(self, source, prps, is32bit, is_correctness_wit):
        self._source = source
        self._prps = prps
        self._is32bit = is32bit
        self._correctness_wit = is_correctness_wit

        self._root = None
        self._graph = None

    def _addCInfo(self):
        assert self._root is not None

        if self._is32bit:
            arch = '32bit'
        else:
            arch = '64bit'

        # add the description
        if self._correctness_wit:
            ET.SubElement(self._graph, 'data',
                          key='witness-type').text = 'correctness_witness'
        else:
            ET.SubElement(self._graph, 'data',
                          key='witness-type').text = 'violation_witness'
        ET.SubElement(self._graph, 'data', key='sourcecodelang').text = 'C'
        ET.SubElement(self._graph, 'data', key='producer').text = 'Symbiotic'
        for p in self._prps:
            ET.SubElement(self._graph, 'data', key='specification').text = p
        ET.SubElement(self._graph, 'data', key='programfile').text = self._source
        ET.SubElement(self._graph, 'data',
                      key='programhash').text = get_hash(self._source)
        ET.SubElement(self._graph, 'data', key='architecture').text = arch

    def _addInfiniteLoop(self, lastNode):
        assert lastNode is not None
        assert self._graph is not None

        for c in list(lastNode):
            key = c.attrib.get('key')
            if key and key == 'violation':
                lastNode.remove(c)
                break

        loop_node = ET.SubElement(self._graph, 'node', id="cycle")
        ET.SubElement(loop_node, 'data', key='cyclehead').text = 'true'
        enter_loop_edge = ET.SubElement(self._graph, 'edge',
                            source=lastNode.attrib["id"],
                            target="cycle")
        ET.SubElement(enter_loop_edge, 'data', key='enterLoopHead').text = 'true'
        enter_loop_edge = ET.SubElement(self._graph, 'edge',
                            source="cycle",
                            target="cycle")
        ET.SubElement(enter_loop_edge, 'data', key='enterLoopHead').text = 'true'

    def createTrivialWitness(self):
        if no_lxml:
            self._root = ET.Element('graphml')
        else:
            ns = {None: 'http://graphml.graphdrawing.org/xmlns'}
            self._root = ET.Element('graphml', nsmap=ns)

        self._graphml = ET.ElementTree(self._root)
        self._graph = ET.SubElement(self._root, 'graph', edgedefault="directed")
        entry = ET.SubElement(self._graph, 'node', id='0')
        ET.SubElement(entry, 'data', key='entry').text = 'true'

        self._addCInfo()

    def parseError(self, pathFile, is_termination):
        """
        Parse .path file from klee
        \param pathFile     the .path file
        \param filename     name of the file the symbiotic ran on
                            -- in the case that we want to stick
                            only to this file in the witness
        """
        assert not self._correctness_wit

        self._dumpObjects('{0}ktest'.format(pathFile[:-4]))

        # parse the graphml file from KLEE
        self._graphml = ET.parse('{0}graphml'.format(pathFile[:-4]))
        assert self._graphml, "Failed parsing witness from KLEE" 
        self._root = self._graphml.getroot()

        assert len(self._root.getchildren()) == 1
        self._graph = list(self._root.getchildren())[0]

        if is_termination:
            # do it this way for the cases when parser added xmlns stuff to the tag names
            nodes = [x for x in list(self._graph) if x.tag.endswith('node')]
            assert len(nodes) > 0
            self._addInfiniteLoop(nodes[-1])

        self._addCInfo()

    def dump(self):
        if no_lxml:
            print(ET.tostring(self._root).decode('utf-8'))
        else:
            print(ET.tostring(self._root, pretty_print=True).decode('utf-8'))

    def write(self, to):
        et = self._graphml
        if no_lxml:
            et.write(to, encoding='UTF-8', method="xml",
                     xml_declaration=True)
        else:
            et.write(to, encoding='UTF-8', method="xml",
                     pretty_print=True, xml_declaration=True)

    ##
    # dumping human readable error
    ##
    def _parseKtest(self, pathFile):
        # this code is taken from ktest-tool from KLEE (but modified)

        f = open(pathFile, 'rb')

        hdr = f.read(5)
        if len(hdr) != 5 or (hdr != b'KTEST' and hdr != b"BOUT\n"):
            print('unrecognized file')
            sys.exit(1)
        version, = unpack('>i', f.read(4))
        if version > 3:
            print('unrecognized version')
            sys.exit(1)
        # skip args
        numArgs, = unpack('>i', f.read(4))
        for i in range(numArgs):
            size, = unpack('>i', f.read(4))
            f.read(size)

        if version >= 2:
            unpack('>i', f.read(4))
            unpack('>i', f.read(4))

        numObjects, = unpack('>i', f.read(4))
        objects = []
        for i in range(numObjects):
            size, = unpack('>i', f.read(4))
            name = f.read(size)
            size, = unpack('>i', f.read(4))
            bytes = f.read(size)
            objects.append((name, bytes))

        f.close()
        return objects

    def _dumpObjects(self, ktestfile):

        objects = self._parseKtest(ktestfile)
        print(' -- ---- --')
        print('Symbolic objects:')
        if len(objects) > 100:
            n = 0
            for o in objects:
                if not is_zero(o):
                    print_object(o)
                    n += 1

            print('\nAnd the rest of objects ({0} objects) are 0'.format(len(objects) - n))
        else:
            for o in objects:
                print_object(o)
        print(' -- ---- --')


