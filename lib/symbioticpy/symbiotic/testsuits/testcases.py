#!/usr/bin/python

from os.path import basename
from sys import version_info
from hashlib import sha256 as hashfunc

from sys import version_info
if version_info < (3, 0):
    from io import open

import re

skip_repeating_lines = False
include_objects = True
only_objects_in_main = True
trivial_witness = True

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


def split_name(name):
    var = name.decode('utf-8').split(":")
    if len(var) != 4:
        return None, None, None
    return var[0], var[1], var[2]


class TestCaseWriter(object):
    def __init__(self, source, covers_error):
        if covers_error:
            self._root = ET.Element('testcase', key = 'coverError')
        else:
            self._root = ET.Element('testcase')

        # is this string a valid variable identificatior?
        self._variable_re = re.compile("^[_a-zA-Z\$][_a-zA-Z\$0-9]*$")
        # is this string a valid variable identificatior or array access?
        # XXX: this is not supported now
        self._variable_index_re = re.compile(
            "^[_a-zA-Z\$][_a-zA-Z\$0-9]*(\[.*\])?$")

    def _parseKtest(self, pathFile):
        # this code is taken from ktest-tool from KLEE
        # (but modified)
        from struct import unpack

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

    def _newNodeEdge(self, last_id, line=None, originfile=None):
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

    def _dumpObjects(self, ktestfile, originfile):
        from struct import unpack

        objects = self._parseKtest(ktestfile)
       #print(' -- ---- --')
       #print('Symbolic objects:')
       #for o in objects:
       #    print_object(o)
       #print(' -- ---- --')

        if not include_objects:
            return 1

        last_id = 1

        if only_objects_in_main:
            # filter the objects to those that are present in main
            # and sort them according to line numbers
            new_objects = []
            for o in objects:
                var_fun, var_name, var_line = split_name(o[0])
                if var_fun is None or var_fun != 'main':
                    continue

                # for the trivial witnesses use only scalar variables, as for
                # array accesses we would need a full path
                if trivial_witness and not self._variable_re.match(var_name):
                    continue

                new_objects.append((var_line, o))

            # sort the objects according to line numbers
            new_objects.sort(key=lambda x: int(x[0]))
            objects = [o for o in map(lambda x: x[1], new_objects)]

        for o in objects:
            var_fun, var_name, var_line = split_name(o[0])
            if var_line is None:
                continue

            assert var_fun and var_name and var_line
            if not only_objects_in_main and\
               not self._variable_re.match(var_name):
               # use only scalar variables now, as we do not support arrays
               # or multiple assignments now
                continue

            ass_list = []
            bytes_num = len(o[1])
            # If possible, dump the value as a regular number (not byte per byte)
            # XXX: the length may not be sufficient. We need to know also
            # that it is really a primitive type (we can have a struct of size 8)
            if bytes_num == 8:
                val = unpack('l', o[1])[0]
            elif bytes_num == 4:
                val = unpack('i', o[1])[0]
            elif bytes_num == 2:
                # unpack needs a buffer of size 4 for an integer
                val = unpack('h', o[1])[0]
            elif bytes_num == 1:
                # unpack needs a buffer of size 4 for an integer
                val = unpack('b', o[1])[0]
            else:
                # dump this as bytes
                for i in range(0, bytes_num):
                    if version_info.major < 3:
                        val = ord(o[1][i])
                    else:
                        val = o[1][i]

            ET.SubElement(self._root, 'input', variable = var_name).text = str(val)

            last_id += 1

        return last_id

    def parseTest(self, pathFile, filename=None):
        """
        Parse .path file from klee
        \param pathFile     the .path file
        \param filename     name of the file the symbiotic ran on
                            -- in the case that we want to stick
                            only to this file in the witness
        """
        # replace .path with .ktest
        last_id = self._dumpObjects('{0}ktest'.format(pathFile[:-4]), filename)

    def dump(self):
        if no_lxml:
            print(ET.tostring(self._root))
        else:
            print(ET.tostring(self._root, pretty_print=True))

    def write(self, to):
        et = ET.ElementTree(self._root)
        doctype = """<!DOCTYPE testcase PUBLIC "+//IDN sosy-lab.org//DTD test-format testcase 1.0//EN" "https://sosy-lab.org/test-format/testcase-1.0.dtd">"""
        if no_lxml:
           with open(to, 'wb') as f:
                f.write("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>""".encode('utf8'))
                f.write(doctype.encode('utf8'))
                et.write(f, encoding='UTF-8', method="xml",
                     xml_declaration=False)
        else:
            et.write(to, encoding='UTF-8', method="xml", doctype = doctype,
                     pretty_print=True, xml_declaration=True)
