#!/usr/bin/python

class SymbioticException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


