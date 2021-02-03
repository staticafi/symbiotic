---
layout: default
title: Getting started
navigation_weight: 2
---

## Getting started
### Downloading Symbiotic
Tarball with Symbiotic distribution can be downloaded from <https://github.com/staticafi/symbiotic/releases>.
After unpacking, Symbiotic is ready to go.

### Building Symbiotic from Sources

First of all you must clone the repository:
```
$ git clone https://github.com/staticafi/symbiotic
```
Then you can run `build.sh` or `system-build.sh` script. In the later case,
you may want to check out also the [page with information about building
via system-build.sh on different systems](building.md).

```
$ cd symbiotic
$ ./build.sh make_options
```
Where make_options are arguments that will be passed to 'make' program while building.
Result is to be in install/ directory and is under git control, so you
can see the differences between versions or make an archive using git archive
command.

If you need to specify paths to header files or libraries, you can do it
by passing CFLAGS, CPPFLAGS, LDFLAGS environment variables either by exporting
them beforehand, or by passing them as make options (e.g. CFLAGS='-g').
More detailed information on how to build Symbiotic is in the main [README](../README.md).


### Running Symbiotic

Change the directory to `bin` (or `install/bin` in the case that you built Symbiotic yourself) and give it a C program:

```
$ ./symbiotic file.c
```
In the case that something went wrong, try running Symbiotic with --debug=OPT where OPT is one of: compile, slicer, prepare, all. When the source code does not contain everything to compile (i. e. it includes some headers), you can use CFLAGS and CPPFLAGS environment variables to pass additional options to the compiler (clang). Either export them before running Symbiotic, or on one line:

```
CPPFLAGS='-I /lib/gcc/include' ./symbiotic file.c
```
You can also use --cppflags switch that works exactly the same as environmental variables.
If the program is split into more files, you can give Symbiotic all the files. At least one of them must contain the 'main' function.

```
./symbiotic main.c additional_definitions.c lib.c
```

To see all available options, just run:

```
$ ./symbiotic --help
```
