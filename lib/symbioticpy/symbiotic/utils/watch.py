#!/usr/bin/python

from utils import dbg

class ProcessWatch(object):
    """ Parse output of running process """

    def parse(self, line):
        """
        Parse output of running process.
        This method will be override by child class
        """
        pass

    def ok(self):
        """
        Return True if everyithing is ok with the process,
        or False if anything went wrong (based on the process' output).
        In case that this method returns False, run_and_watch() function
        will terminate the process and return -1
        """
        return True


class DbgWatch(ProcessWatch):
    def __init__(self, domain = 'all', print_nl = False):
        self.domain = domain
        self.print_nl = print_nl

    def parse(self, line):
        dbg(line, self.domain, self.print_nl)

class BufferedDbgWatch(DbgWatch):
    """
    This is same as dbg watch, but it stores
    few last lines of the output
    """
    def __init__(self, domain = 'all', print_nl = False, maxlines = 50):
        DbgWatch.__init__(self, domain, print_nl)
        self.lines = []
        self.MAX_LINES_NUM = maxlines
        self.cur_lines_num = 0

        # use DbgWatch in this case
        assert maxlines > 0

    def getLines(self):
        return self.lines

    def parse(self, line):
        DbgWatch.parse(self, line)

        # store the output
        if self.cur_lines_num == self.MAX_LINES_NUM:
            self.lines.pop(0)
        else:
            self.cur_lines_num += 1

        self.lines.append(line)
        assert self.cur_lines_num <= self.MAX_LINES_NUM


