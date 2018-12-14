#!/usr/bin/python

from os import environ

class Environment:
    """
    Helper class for setting and maintaining
    evnironment for tools
    """
    def __init__(self, symb_dir):
        self.symbiotic_dir = symb_dir
        self.working_dir = None

    def prepend(self, env, what):
        """ Prepend 'what' to environment variable 'env'"""
        if env in environ:
            newenv = '{0}:{1}'.format(what, environ[env])
        else:
            newenv = what

        environ[env] = newenv

    def append(self, env, what):
        """ Append 'what' to environment variable 'env'"""
        if env in environ:
            newenv = '{0}:{1}'.format(environ[env], what)
        else:
            newenv = what

        environ[env] = newenv


