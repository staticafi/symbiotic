#!/usr/bin/python

from os.path import basename
from sys import version_info
from hashlib import sha256 as hashfunc
import datetime

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


class MetadataWriter(object):
    def __init__(self, source, prps, is32bit):
        if is32bit:
            arch = '32bit'
        else:
            arch = '64bit'

        self._metadata = ET.Element('test-metadata')
        ET.SubElement(self._metadata, 'sourcecodelang').text = 'C'
        ET.SubElement(self._metadata, 'producer').text = 'Symbiotic'
        for p in prps:
            ET.SubElement(self._metadata, 'specification').text = p
        ET.SubElement(self._metadata, 'programfile').text = source
        ET.SubElement(self._metadata, 'programhash').text = get_hash(source)
        ET.SubElement(self._metadata, 'architecture').text = arch
        ET.SubElement(self._metadata, 'entryfunction').text = 'main'
        ET.SubElement(self._metadata, 'creationtime').text =\
            '{date:%Y-%m-%d %T}Z'.format(date=datetime.datetime.utcnow())

    def dump(self):
        if no_lxml:
            print(ET.tostring(self._metadata))
        else:
            print(ET.tostring(self._metadata, pretty_print=True))

    def write(self, to):
        et = ET.ElementTree(self._metadata)
        doctype = """<!DOCTYPE test-metadata PUBLIC "+//IDN sosy-lab.org//DTD test-format test-metadata 1.0//EN" "https://sosy-lab.org/test-format/test-metadata-1.0.dtd">"""
        if no_lxml:
           with open(to, 'wb') as f:
                f.write("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>""".encode('utf8'))
                f.write(doctype.encode('utf8'))
                et.write(f, encoding='UTF-8', method="xml",
                     xml_declaration=False)
        else:
            et.write(to, encoding='UTF-8', method="xml", doctype = doctype,
                     pretty_print=True, xml_declaration=True)
