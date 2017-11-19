#!/usr/bin/python

from os.path import basename
from sys import version_info
from hashlib import sha1

import re

skip_repeating_lines = False
include_objects = False
trivial_witness = True

no_lxml = False
try:
    from lxml import etree as ET
except ImportError:
    no_lxml = True

if no_lxml:
    # if this fails, then we're screwed, so let the script die
    from xml.etree import ElementTree as ET

def get_sha1(source):
    f = open(source, 'r')
    hsh = sha1()
    for l in f:
        hsh.update(l.encode('utf-8'))

    f.close()
    return hsh.hexdigest()

def get_repr(obj):
    ret = []
    assert len(obj[1]) > 0

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

def print_object(obj):
    rep = 'len {0} bytes, |'.format(len(obj[1]))
    for part in get_repr(obj):
        if version_info.major < 3:
            value = ord(part[0])
        else:
            value = part[0]

        value = hex(value)

        if part[1] > 1:
            rep += '{0} times {1}|'.format(part[1], value)
        else:
            rep += '{0}|'.format(value)
    print('{0} := {1}'.format(obj[0], rep))

class GraphMLWriter(object):
    def __init__(self, source, prps, is32bit, is_correctness_wit, with_source_lines = False):
        if no_lxml:
            self._root = ET.Element('graphml')
        else:
            ns = {None:'http://graphml.graphdrawing.org/xmlns/graphml'}
            self._root = ET.Element('graphml', nsmap=ns)

        if is32bit:
            arch = '32bit'
        else:
            arch = '64bit'

        self._with_source_lines = with_source_lines

        self._variable_index_re = re.compile("^[_a-zA-Z\$][_a-zA-Z\$0-9]*(\[.*\])?$")

        self._graph = ET.SubElement(self._root, 'graph', edgedefault="directed")
        # add the description
        if is_correctness_wit:
            ET.SubElement(self._graph, 'data', key='witness-type').text = 'correctness_witness'
        else:
            ET.SubElement(self._graph, 'data', key='witness-type').text = 'violation_witness'
        ET.SubElement(self._graph, 'data', key='sourcecodelang').text = 'C'
        ET.SubElement(self._graph, 'data', key='producer').text = 'Symbiotic'
        # XXX: this may change in the future
        for p in prps:
            ET.SubElement(self._graph, 'data', key='specification').text = p
        ET.SubElement(self._graph, 'data', key='programfile').text = source
        ET.SubElement(self._graph, 'data', key='programhash').text = get_sha1(source)
        #ET.SubElement(self._graph, 'data', key='memorymodel').text = 'precise'
        ET.SubElement(self._graph, 'data', key='architecture').text = arch

        # create the entry node
        self._entry = ET.SubElement(self._graph, 'node', id='0')
        ET.SubElement(self._entry, 'data', key='entry').text = 'true'

    def _parseKtest(self, pathFile):
        # this code is taken from ktest-tool from KLEE
        # (but modified)
        from struct import unpack

        f = open(pathFile,'rb')

        hdr = f.read(5)
        if len(hdr)!=5 or (hdr!=b'KTEST' and hdr != b"BOUT\n"):
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
            objects.append( (name,bytes) )

        f.close()
        return objects

    def _newNodeEdge(self, last_id, line = None, originfile = None):
        # create new node
        node = ET.SubElement(self._graph, 'node', id=str(last_id))

        # create new edge
        edge = ET.SubElement(self._graph, 'edge',
                                source=str(last_id - 1),
                                target=str(last_id))
        if line is not None:
            ET.SubElement(edge, 'data', key='startline').text = line
        if originfile is not None:
            ET.SubElement(edge, 'data', key='originfile').text = originfile

        return node, edge

    def _dumpObjects(self, ktestfile):
        objects = self._parseKtest(ktestfile)
        print(' -- ---- --')
        print('Symbolic objects:')
        for o in objects:
            print_object(o)
        print(' -- ---- --')

        if not include_objects:
            return 1

        last_id = 1

        for o in objects:
            var = o[0].split(":")
            if len(var) != 3:
                continue
            var_fun = var[0]
            var_name = var[1]

            if not self._variable_index_re.match(var_name):
                continue

            ass_list = []
            for i in range(0, len(o[1])):
                ass_list.append("*(char *)&({0}))[{1}] == {2}".format(var_name, i, ord(o[1][i])))

            node, edge = self._newNodeEdge(last_id)
            ET.SubElement(edge, 'data', key='assumption').text = "; ".join(ass_list)
            ET.SubElement(edge, 'data', key='assumption_scope').text = var_fun

            last_id += 1

        return last_id

    def _dumpPath(self, pathFile, last_id, filename):
        #ctrlelem = None
        last_node = None
        line_set = set()

        if filename:
            filenm = basename(filename)
        else:
            filenm = None

        dump_source_lines = self._with_source_lines and filename
        if dump_source_lines:
            fl = open(filename, 'r')
            lines = fl.readlines()
            fl.close()

        f = open(pathFile, 'r')

        for line in f:
            l = line.split()

            # discard invalid records
            if len(l) != 4:
                continue

            # the file name is l[2]
            originfile = basename(l[2])
            if filenm and filenm != originfile:
                continue

            lineno = int(l[3])

            if skip_repeating_lines and lineno in line_set:
                continue

            line_set.add(lineno)

            last_node, edge = self._newNodeEdge(last_id, l[3], originfile)

            if dump_source_lines:
                ET.SubElement(edge, 'data', key='sourcecode').text\
                    = lines[lineno - 1].strip().encode('utf-8')

            # not all of the lines are branches and also not every
            # branch evaluation corresponds to the same evaluation
            # of the source code (e.g. optimizations may negate the condition)
            # if int(l[0]) == 0:
            #     # KLEE splits the true/false inverted for some reason
            #     control = 'condition-true'
            # else:
            #     control = 'condition-false'

            # ctrlelem = ET.SubElement(edge, 'data', key='control')
            # ctrlelem.text = control

            last_id += 1

        # create the violation - it is the last node in our graph
        if last_node is None:
            last_node = ET.SubElement(self._graph, 'node', id=str(last_id))
            ET.SubElement(self._graph, 'edge',
                             source=str(last_id - 1),
                             target=str(last_id))

        ET.SubElement(last_node, 'data', key='violation').text = 'true'

        # remove the control key from the last edge
        # if ctrlelem is not None:
        #     ctrlelem.getparent().remove(ctrlelem)

        f.close()

    def parseError(self, pathFile, filename = None):
        """
        Parse .path file from klee
        \param pathFile     the .path file
        \param filename     name of the file the symbiotic ran on
                            -- in the case that we want to stick
                            only to this file in the witness
        """
        # replace .path with .ktest
        last_id = self._dumpObjects('{0}ktest'.format(pathFile[:-4]))
        if trivial_witness:
            last_node = ET.SubElement(self._graph, 'node', id=str(last_id))
            ET.SubElement(self._graph, 'edge',
                             source=str(last_id - 1),
                             target=str(last_id))

            ET.SubElement(last_node, 'data', key='violation').text = 'true'
        else:
            self._dumpPath(pathFile, last_id, filename)

    def dump(self):
        if no_lxml:
            print(ET.tostring(self._root))
        else:
            print(ET.tostring(self._root, pretty_print=True))

    def write(self, to):
        et = ET.ElementTree(self._root)
        if no_lxml:
            et.write(to, encoding='UTF-8', method="xml",
                     xml_declaration=True)
        else:
            et.write(to, encoding='UTF-8', method="xml",
                     pretty_print=True, xml_declaration=True)

