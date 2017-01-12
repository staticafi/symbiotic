# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module contains some useful functions for Strings, XML or Lists.
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

# THIS MODULE HAS TO WORK WITH PYTHON 2.7!

import bz2
import collections
import fnmatch
import glob
import logging
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
from xml.etree import ElementTree

try:
    from shlex import quote as escape_string_shell
except ImportError:
    from pipes import quote as escape_string_shell  # @UnusedImport for export


try:
    read_monotonic_time = time.monotonic
except AttributeError:
    # TODO Should probably warn about wall time affected by changing system clock
    read_monotonic_time = time.time


try:
    glob.iglob("/", recursive=True)
except TypeError:
    def maybe_recursive_iglob(pathname, recursive=False):
        """Workaround for glob.iglob not accepting parameter recursive on Python <= 3.4"""
        return glob.iglob(pathname)
else:
    maybe_recursive_iglob = glob.iglob


_BYTE_FACTOR = 1000 # byte in kilobyte


def is_windows():
    return os.name == 'nt'

def force_linux_path(path):
    if is_windows():
        return path.replace('\\', '/')
    return path

def printOut(value, end='\n'):
    """
    This function prints the given String immediately and flushes the output.
    """
    sys.stdout.write(value)
    sys.stdout.write(end)
    sys.stdout.flush()

def is_code(filename):
    """
    This function returns True, if  a line of the file contains bracket '{'.
    """
    with open(filename, "r") as file:
        for line in file:
            # ignore comments and empty lines
            if not is_comment(line) \
                    and '{' in line: # <-- simple indicator for code
                if '${' not in line: # <-- ${abc} variable to substitute
                    return True
    return False

def is_comment(line):
    return not line or line.startswith("#") or line.startswith("//")


def remove_all(list_, elemToRemove):
    return [elem for elem in list_ if elem != elemToRemove]


def flatten(iterable, exclude=[]):
    return [value for sublist in iterable for value in sublist if not value in exclude]


def get_list_from_xml(elem, tag="option", attributes=["name"]):
    '''
    This function searches for all "option"-tags and returns a list with all attributes and texts.
    '''
    return flatten(([option.get(attr) for attr in attributes] + [option.text] for option in elem.findall(tag)), exclude=[None])

def get_single_child_from_xml(elem, tag):
    """
    Get a single child tag from an XML element.
    Similar to "elem.find(tag)", but warns if there are multiple child tags with the given name.
    """
    children = elem.findall(tag)
    if not children:
        return None
    if len(children) > 1:
        logging.warning('Tag "%s" has more than one child tags with name "%s" in input file, '
                        'ignoring all but the first.',
                        elem.tag, tag)
    return children[0]

def text_or_none(elem):
    """
    Retrieve the text content of an XML tag, or None if the element itself is None
    """
    return elem.text if elem is not None else None

def copy_of_xml_element(elem):
    """
    This method returns a shallow copy of a XML-Element.
    This method is for compatibility with Python 2.6 or earlier..
    In Python 2.7 you can use  'copyElem = elem.copy()'  instead.
    """

    copyElem = ElementTree.Element(elem.tag, elem.attrib)
    for child in elem:
        copyElem.append(child)
    return copyElem


def decode_to_string(toDecode):
    """
    This function is needed for Python 3,
    because a subprocess can return bytes instead of a string.
    """
    try:
        return toDecode.decode('utf-8')
    except AttributeError: # bytesToDecode was of type string before
        return toDecode


def format_number(number, number_of_digits):
    """
    The function format_number() return a string-representation of a number
    with a number of digits after the decimal separator.
    If the number has more digits, it is rounded.
    If the number has less digits, zeros are added.

    @param number: the number to format
    @param digits: the number of digits
    """
    if number is None:
        return ""
    return "%.{0}f".format(number_of_digits) % number


def parse_int_list(s):
    """
    Parse a comma-separated list of strings.
    The list may additionally contain ranges such as "1-5",
    which will be expanded into "1,2,3,4,5".
    """
    result = []
    for item in s.split(','):
        item = item.strip().split('-')
        if len(item) == 1:
            result.append(int(item[0]))
        elif len(item) == 2:
            start, end = item
            result.extend(range(int(start), int(end)+1))
        else:
            raise ValueError("invalid range: '{0}'".format(s))
    return result


def split_number_and_unit(s):
    """Parse a string that consists of a integer number and an optional unit.
    @param s a non-empty string that starts with an int and is followed by some letters
    @return a triple of the number (as int) and the unit
    """
    if not s:
        raise ValueError('empty value')
    s = s.strip()
    pos = len(s)
    while pos and not s[pos-1].isdigit():
        pos -= 1
    number = int(s[:pos])
    unit = s[pos:].strip()
    return (number, unit)

def parse_memory_value(s):
    """Parse a string that contains a number of bytes, optionally with a unit like MB.
    @return the number of bytes encoded by the string
    """
    number, unit = split_number_and_unit(s)
    if not unit or unit == 'B':
        return number
    elif unit == 'kB':
        return number * _BYTE_FACTOR
    elif unit == 'MB':
        return number * _BYTE_FACTOR * _BYTE_FACTOR
    elif unit == 'GB':
        return number * _BYTE_FACTOR * _BYTE_FACTOR * _BYTE_FACTOR
    elif unit == 'TB':
        return number * _BYTE_FACTOR * _BYTE_FACTOR * _BYTE_FACTOR * _BYTE_FACTOR
    else:
        raise ValueError('unknown unit: {} (allowed are B, kB, MB, GB, and TB)'.format(unit))

def parse_timespan_value(s):
    """Parse a string that contains a time span, optionally with a unit like s.
    @return the number of seconds encoded by the string
    """
    number, unit = split_number_and_unit(s)
    if not unit or unit == "s":
        return number
    elif unit == "min":
        return number * 60
    elif unit == "h":
        return number * 60 * 60
    elif unit == "d":
        return number * 24 * 60 * 60
    else:
        raise ValueError('unknown unit: {} (allowed are s, min, h, and d)'.format(unit))


def expand_filename_pattern(pattern, base_dir):
    """
    Expand a file name pattern containing wildcards, environment variables etc.

    @param pattern: The pattern string to expand.
    @param base_dir: The directory where relative paths are based on.
    @return: A list of file names (possibly empty).
    """
    # 'join' ignores base_dir, if expandedPattern is absolute.
    # 'normpath' replaces 'A/foo/../B' with 'A/B', for pretty printing only
    pattern = os.path.normpath(os.path.join(base_dir, pattern))

    # expand tilde and variables
    pattern = os.path.expandvars(os.path.expanduser(pattern))

    # expand wildcards
    fileList = glob.glob(pattern)

    return fileList


def get_files(paths):
    changed = False
    result = []
    for path in paths:
        if os.path.isfile(path):
            result.append(path)
        elif os.path.isdir(path):
            changed = True
            for currentPath, dirs, files in os.walk(path):
                # ignore hidden files, on Linux they start with '.',
                # inplace replacement of 'dirs', because it is used later in os.walk
                files = [f for f in files if not f.startswith('.')]
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                result.extend(os.path.join(currentPath, f) for f in files)
    return result if changed else paths


def find_executable(program, fallback=None, exitOnError=True):
    def is_executable(programPath):
        return os.path.isfile(programPath) and os.access(programPath, os.X_OK)

    dirs = os.environ['PATH'].split(os.path.pathsep)
    dirs.append(os.path.curdir)

    for dir_ in dirs:
        name = os.path.join(dir_, program)
        if is_executable(name):
            return name

    if fallback is not None and is_executable(fallback):
        return fallback

    if exitOnError:
        sys.exit("ERROR: Could not find '{0}' executable".format(program))
    else:
        return fallback


def common_base_dir(l):
    # os.path.commonprefix returns the common prefix, not the common directory
    return os.path.dirname(os.path.commonprefix(l))

def log_rmtree_error(func, arg, exc_info):
    """Suited as onerror handler for (sh)util.rmtree() that logs a warning."""
    logging.warning("Failure during '%s(%s)': %s", func.__name__, arg, exc_info[1])

def rmtree(path, ignore_errors=False, onerror=None):
    """Same as shutil.rmtree, but supports directories without write or execute permissions."""
    if ignore_errors:
        def onerror(*args):
            pass
    elif onerror is None:
        def onerror(*args):
            raise
    for root, dirs, unused_files in os.walk(path):
        for directory in dirs:
            try:
                abs_directory = os.path.join(root, directory)
                os.chmod(abs_directory, stat.S_IRWXU)
            except EnvironmentError as e:
                onerror(os.chmod, abs_directory, e)
    shutil.rmtree(path, ignore_errors=ignore_errors, onerror=onerror)

def copy_all_lines_from_to(inputFile, outputFile):
    """Copy all lines from an input file object to an output file object."""
    currentLine = inputFile.readline()
    while currentLine:
        outputFile.write(currentLine)
        currentLine = inputFile.readline()

def write_file(content, *path):
    """
    Simply write some content to a file, overriding the file if necessary.
    """
    with open(os.path.join(*path), "w") as file:
        return file.write(content)

def shrink_text_file(filename, max_size, removal_marker=None):
    """Shrink a text file to approximately maxSize bytes
    by removing lines from the middle of the file.
    """
    file_size = os.path.getsize(filename)
    assert file_size > max_size

    # We partition the file into 3 parts:
    # A) start: maxSize/2 bytes we want to keep
    # B) middle: part we want to remove
    # C) end: maxSize/2 bytes we want to keep

    # Trick taken from StackOverflow:
    # https://stackoverflow.com/questions/2329417/fastest-way-to-delete-a-line-from-large-file-in-python
    # We open the file twice at the same time, once for reading (input_file) and once for writing (output_file).
    # We position output_file at the beginning of part B
    # and input_file at the beginning of part C.
    # Then we copy the content of C into B, overwriting what is there.
    # Afterwards we truncate the file after A+C.

    with open(filename, 'r+b') as output_file:
        with open(filename, 'rb') as input_file:
            # Position outputFile between A and B
            output_file.seek(max_size // 2)
            output_file.readline() # jump to end of current line so that we truncate at line boundaries
            if output_file.tell() == file_size:
                # readline jumped to end of file because of a long line
                return

            if removal_marker:
                output_file.write(removal_marker.encode())

            # Position inputFile between B and C
            input_file.seek(-max_size // 2, os.SEEK_END) # jump to beginning of second part we want to keep from end of file
            input_file.readline() # jump to end of current line so that we truncate at line boundaries

            # Copy C over B
            copy_all_lines_from_to(input_file, output_file)

            output_file.truncate()


def read_file(*path):
    """
    Read the full content of a file.
    """
    with open(os.path.join(*path)) as f:
        return f.read().strip()

def read_key_value_pairs_from_file(*path):
    """
    Read key value pairs from a file (each pair on a separate line).
    Key and value are separated by ' ' as often used by the kernel.
    @return a generator of tuples
    """
    with open(os.path.join(*path)) as f:
        for line in f:
            yield line.split(' ', 1) #maxsplit=1


class BZ2FileHack(bz2.BZ2File):
    """Hack for Python 3.2, where BZ2File cannot be used in a io.TextIOWrapper
    because it lacks several functions.
    """
    def __init__(self, filename, mode, *args, **kwargs):
        assert mode == "wb"
        bz2.BZ2File.__init__(self, filename, mode, *args, **kwargs)

    def readable(self):
        return False

    def seekable(self):
        return False

    def writable(self):
        return True

    def flush(self):
        pass


ProcessExitCode = collections.namedtuple('ProcessExitCode', 'raw value signal')
"""Tuple for storing the exit status indication given by a os.wait() call.
Only value or signal are present, not both
(a process cannot return a value when it is killed by a signal).
"""
@classmethod
def _ProcessExitCode_from_raw(cls, exitcode):
    if not (0 <= exitcode < 2**16):
        raise ValueError("invalid exitcode " + str(exitcode))
    # calculation: exitcode == (returnvalue * 256) + exitsignal
    # highest bit of exitsignal shows only whether a core file was produced, we clear it
    exitsignal = exitcode & 0x7F
    returnvalue = exitcode >> 8
    if exitsignal == 0:
        # signal 0 does not exist, this means there was no signal that killed the process
        exitsignal = None
    else:
        assert returnvalue == 0,\
            "returnvalue " + str(returnvalue) + ", although exitsignal is " + str(exitsignal)
        returnvalue = None
    return cls(exitcode, returnvalue, exitsignal)
ProcessExitCode.from_raw = _ProcessExitCode_from_raw

def _ProcessExitCode__str__(self):
    return (("exit signal " + str(self.signal)) if self.signal
        else ("return value " + str(self.value)))
ProcessExitCode.__str__ = _ProcessExitCode__str__

def _ProcessExitCode__bool__(self):
    return bool(self.signal or self.value)
ProcessExitCode.__bool__ = _ProcessExitCode__bool__
ProcessExitCode.__nonzero__ = _ProcessExitCode__bool__


def add_files_to_git_repository(base_dir, files, description):
    """
    Add and commit all files given in a list into a git repository in the
    base_dir directory. Nothing is done if the git repository has
    local changes.

    @param files: the files to commit
    @param description: the commit message
    """
    if not os.path.isdir(base_dir):
        printOut('Output path is not a directory, cannot add files to git repository.')
        return

    # find out root directory of repository
    gitRoot = subprocess.Popen(['git', 'rev-parse', '--show-toplevel'],
                               cwd=base_dir,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = gitRoot.communicate()[0]
    if gitRoot.returncode != 0:
        printOut('Cannot commit results to repository: git rev-parse failed, perhaps output path is not a git directory?')
        return
    gitRootDir = decode_to_string(stdout).splitlines()[0]

    # check whether repository is clean
    gitStatus = subprocess.Popen(['git','status','--porcelain', '--untracked-files=no'],
                                 cwd=gitRootDir,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = gitStatus.communicate()
    if gitStatus.returncode != 0:
        printOut('Git status failed! Output was:\n' + decode_to_string(stderr))
        return

    if stdout:
        printOut('Git repository has local changes, not commiting results.')
        return

    # add files to staging area
    files = [os.path.realpath(file) for file in files]
    # Use --force to add all files in result-files directory even if .gitignore excludes them
    gitAdd = subprocess.Popen(['git', 'add', '--force', '--'] + files,
                               cwd=gitRootDir)
    if gitAdd.wait() != 0:
        printOut('Git add failed, will not commit results!')
        return

    # commit files
    printOut('Committing results files to git repository in ' + gitRootDir)
    gitCommit = subprocess.Popen(['git', 'commit', '--file=-', '--quiet'],
                                 cwd=gitRootDir,
                                 stdin=subprocess.PIPE)
    gitCommit.communicate(description.encode('UTF-8'))
    if gitCommit.returncode != 0:
        printOut('Git commit failed!')
        return


def wildcard_match(word, wildcard):
    return word and fnmatch.fnmatch(word, wildcard)


def _debug_current_process(sig, current_frame):
    """Interrupt running process, and provide a python prompt for interactive debugging.
    This code is based on http://stackoverflow.com/a/133384/396730
    """
    # Import modules only if necessary, readline is for shell history support.
    import code, traceback, readline, threading  # @UnresolvedImport @UnusedImport

    d={'_frame':current_frame}         # Allow access to frame object.
    d.update(current_frame.f_globals)  # Unless shadowed by global
    d.update(current_frame.f_locals)

    i = code.InteractiveConsole(d)
    message  = "Signal received : entering python shell.\n"

    threads = dict((thread.ident, thread) for thread in threading.enumerate())
    current_thread = threading.current_thread()
    for thread_id, frame in sys._current_frames().items():
        if current_thread.ident != thread_id:
            message += "\nTraceback of thread {}:\n".format(threads[thread_id])
            message += ''.join(traceback.format_stack(frame))
    message += "\nTraceback of current thread {}:\n".format(current_thread)
    message += ''.join(traceback.format_stack(current_frame))
    i.interact(message)

def activate_debug_shell_on_signal():
    """Install a signal handler for USR1 that dumps stack traces
    and gives an interactive debugging shell.
    """
    signal.signal(signal.SIGUSR1, _debug_current_process)  # Register handler
