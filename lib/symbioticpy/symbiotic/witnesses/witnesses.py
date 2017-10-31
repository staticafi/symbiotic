#!/usr/bin/python

from os.path import basename
from hashlib import sha1
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

class GraphMLWriter(object):
    def __init__(self, source, is32bit, is_correctness_wit, with_source_lines = False):
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

        self._graph = ET.SubElement(self._root, 'graph', edgedefault="directed")
        # add the description
        if is_correctness_wit:
            ET.SubElement(self._graph, 'data', key='witness-type').text = 'correctness_witness'
        else:
            ET.SubElement(self._graph, 'data', key='witness-type').text = 'violation_witness'
        ET.SubElement(self._graph, 'data', key='sourcecodelang').text = 'C'
        ET.SubElement(self._graph, 'data', key='producer').text = 'Symbiotic'
        # XXX: this may change in the future
        ET.SubElement(self._graph, 'data', key='specification').text \
            = 'CHECK( init(main()), LTL(G ! call(__VERIFIER_error())) )'
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

    def parseError(self, pathFile, filename = None):
        """
        Parse .path file from klee
        \param pathFile     the .path file
        \param filename     name of the file the symbiotic ran on
                            -- in the case that we want to stick
                            only to this file in the witness
        """
        if filename:
            filenm = basename(filename)
        else:
            filenm = None

        # replace .path with .ktest
        ktestfile = '{0}ktest'.format(pathFile[:-4])
        objects = self._parseKtest(ktestfile)
        print(objects)

        dump_source_lines = self._with_source_lines and filename
        if dump_source_lines:
            fl = open(filename, 'r')
            lines = fl.readlines()
            fl.close()

        f = open(pathFile, 'r')
        last_id=1
        last_node = None

        #ctrlelem = None
        for line in f:
            l = line.split()

            # discard invalid records
            if len(l) != 4:
                continue

            # the file name is l[2]
            originfile = basename(l[2])
            if filenm and filenm != originfile:
                continue

            # create new node
            last_node = ET.SubElement(self._graph, 'node', id=str(last_id))

            # create new edge
            edge = ET.SubElement(self._graph, 'edge',
                                    source=str(last_id - 1),
                                    target=str(last_id))
            ET.SubElement(edge, 'data', key='startline').text = l[3]
            ET.SubElement(edge, 'data', key='originfile').text = originfile

            if dump_source_lines:
                ET.SubElement(edge, 'data', key='sourcecode').text\
                    = lines[int(l[3]) - 1].strip().encode('utf-8')

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

