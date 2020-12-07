#!/usr/bin/python

from os.path import basename
from hashlib import sha256 as hashfunc
import datetime
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

def _add_edge_key(root, name):
    e = ET.SubElement(root, 'key', id=name)
    e.set('for', 'edge')
    e.set('attr.type', 'string')
    e.set('attr.name', name)

def _add_node_key(root, name):
    e = ET.SubElement(root, 'key', id=name)
    e.set('for', 'node')
    e.set('attr.type', 'string')
    e.set('attr.name', name)

def _add_graph_key(root, name):
    e = ET.SubElement(root, 'key', id=name)
    e.set('for', 'graph')
    e.set('attr.type', 'string')
    e.set('attr.name', name)

class GraphMLWriter(object):
    def __init__(self, source, prps, is32bit, is_correctness_wit):
        self._source = source
        self._prps = prps
        self._is32bit = is32bit
        self._correctness_wit = is_correctness_wit

        self._root = None
        self._graph = None

        # this prevents adding ns0 prefix to all tags
        ET.register_namespace("xsi",
                              "http://www.w3.org/2001/XMLSchema-instance")

    def _addKeys(self):
        root = self._root
        _add_graph_key(root, "witness-type")
        _add_graph_key(root, "specification")
        _add_graph_key(root, "programfile")
        _add_graph_key(root, "sourcecodelang")
        _add_graph_key(root, "producer")
        _add_graph_key(root, "creationtime")
        _add_graph_key(root, "architecture")
        _add_graph_key(root, "programhash")
        _add_node_key(root, "entry")
        _add_node_key(root, "violation")
        _add_edge_key(root, "assumption")
        _add_edge_key(root, "assumption.resultfunction")
        _add_edge_key(root, "startline")

        e = ET.SubElement(root, 'key', id="cyclehead")
        e.set('for', 'node')
        e.set('attr.type', 'boolean')
        e.set('attr.name', "cyclehead")
        se = ET.SubElement(e, 'default').text = 'false'

        e = ET.SubElement(root, 'key', id="enterLoopHead")
        e.set('for', 'edge')
        e.set('attr.type', 'boolean')
        e.set('attr.name', "enterLoopHead")
        se = ET.SubElement(e, 'default').text = 'false'


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
        ET.SubElement(self._graph, 'data', key='creationtime').text =\
            '{date:%Y-%m-%dT%T}'.format(date=datetime.datetime.utcnow())

        self._addKeys()

    def createTrivialWitness(self):
        if no_lxml:
            self._root = ET.Element('graphml')
        else:
            ns = {None: 'http://graphml.graphdrawing.org/xmlns',
                  "xsi": "http://www.w3.org/2001/XMLSchema-instance"}
            self._root = ET.Element('graphml', nsmap=ns)

        self._graphml = ET.ElementTree(self._root)
        self._graph = ET.SubElement(self._root, 'graph', edgedefault="directed")
        entry = ET.SubElement(self._graph, 'node', id='0')
        ET.SubElement(entry, 'data', key='entry').text = 'true'

        self._addCInfo()

    def parseError(self, ktest, is_termination):
        """
        Parse .path file from klee
        \param ktest        the .ktest file
        \param filename     name of the file the symbiotic ran on
                            -- in the case that we want to stick
                            only to this file in the witness
        """
        assert not self._correctness_wit

        # parse the graphml file from KLEE
        self._graphml = ET.parse('{0}graphml'.format(ktest[:ktest.rfind('.')+1]))
        assert self._graphml, "Failed parsing witness from KLEE" 
        self._root = self._graphml.getroot()

        assert len(self._root.getchildren()) == 1
        self._graph = list(self._root.getchildren())[0]
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

