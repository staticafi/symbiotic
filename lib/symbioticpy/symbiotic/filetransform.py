#!/usr/bin/python

class FileTransform(object):
    """
    Do some transformation of file,
    like replacing words or similar
    """

    def run(self, inputfile, outputfile):
        pass

#class TypedefReplace(FileTransform):
#   """
#   Replace typedef by the original type in a C file
#   """
#   def __init__(self):
#       self._typedefs = {}
#
#       from re import compile
#       # FIXME: this does not match everything
#       self._tdre = compile('^\s*typedef\s+(.*)\s+(\w+)\s*;\s*$')
#
#   def run(self, inputfile, outputfile):
#       infile = open(inputfile, 'r')
#       outfile = open(outputfile, 'w')
#
#       for l in infile:
#           res = self._tdre.match(l)
#           if res:
#               v = res.group(1).strip()
#               k = res.group(2).strip()
#               assert not self._typedefs.has_key(k)
#               self._typedefs[k] = v
#               outfile.write('/* {0} -> {1} */\n'.format(res.group(1), res.group(2).strip()))
#           else:
#               for (k, v) in self._typedefs.iteritems():
#                   l = l.replace(k, v)
#
#               outfile.write(l)

class InlineRemove(FileTransform):
    """
    Remove __inline due to a bug in clang
    """
    def __init__(self):
        from re import compile
        self._tdre = compile('^\s*__inline\s+(.*)$')

    def run(self, inputfile, outputfile):
        infile = open(inputfile, 'r')
        outfile = open(outputfile, 'w')

        for l in infile:
            res = self._tdre.match(l)
            if res:
                outfile.write('/*__inline */ {0}\n'.format(res.group(1)))
            else:
                outfile.write(l)


