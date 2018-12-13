#!/usr/bin/python

class SymbioticException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class SymbioticExceptionalResult(Exception):
    """
    If we hit a condition during analysis that
    immediately gives us a result (say 'unknown'
    on unsupported feature, we throw and catch
    this exception (it is indeed exceptional behavior)
    """
    def __init__(self, msg):
        Exception.__init__(self, msg)

