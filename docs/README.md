## What is Symbiotic?
Symbiotic is a tool for analysis of sequential computer programs written in the programming language C. It can check all common safety properties like assertion violations, invalid pointer dereference, double free, memory leaks, etc. Symbiotic combines light-weight static analysis, compile-time code instrumentation, program slicing, and symbolic execution [2]. We use LLVM (<https://llvm.org>) as internal program representation. Symbiotic is highly modular and all of its components can be used separately.

## SV-COMP 2019
Symbiotic won the gold medal in MemSafety category and 4th place in the meta category Overall and FalsificationOverall of SV-COMP 2019. Complete results can be found at the [official SV-COMP 2019 site](https://sv-comp.sosy-lab.org/2019/results/results-verified/).

## SV-COMP 2018
Symbiotic won the gold medal in MemSafety category, Bronze medal in the FalsificationOverall meta category and took 4th place in the Overall category of SV-COMP 2018. Complete results can be found [official SV-COMP 2018 site](http://sv-comp.sosy-lab.org/2018/results/results-verified/).

## SV-COMP 2017
We participated in SV-COMP 2017 and we won the bronze medal in MemSafety category. Complete results can be found [official SV-COMP 2017 site](http://sv-comp.sosy-lab.org/2017/results/results-verified/).

## SV-COMP 2016
We participated in SV-COMP 2016 with this particular release: <https://github.com/staticafi/symbiotic/releases/tag/3.0.1> and we won the bronze medal in Arrays category. Complete results can be found [official SV-COMP 2016 site](http://sv-comp.sosy-lab.org/2016/results/results-verified/).


## Getting started
### Downloading Symbiotic
Tarball with Symbiotic distribution can be downloaded from <https://github.com/staticafi/symbiotic/releases>.
After unpacking, Symbiotic is ready to go.

### Building Symbiotic

First of all you must clone the repository:
```
$ git clone https://github.com/staticafi/symbiotic
```
Then you can run `build.sh` script.

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
them beforehand, or by passing them as make options (e.g. CFLAGS='-g')

### Running Symbiotic

Running Symbiotic is very easy. Change the directory to `bin` (or `install/bin` in the case that you built Symbiotic yourself) and give it a C program:

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
### Symbiotic Components

Components of Symbiotic can be found at <https://github.com/staticafi> with the only exception of the slicer, that can be found at <https://github.com/mchalupa/dg> (it will be moved to _staticafi_ in the future though). All parts of Symbiotic are open-source projects and are licensed under various open-source licenses (GPL, MIT license, University of Illinois Open Source license)

## Contact

For more information send an e-mail to <statica@fi.muni.cz>. We'll be happy to answer your questions :)

------------------------------------------------
[1] Slabý, Jiří and Strejček, Jan and Trtík, Marek. _Checking Properties Described by State Machines: On Synergy of Instrumentation, Slicing, and Symbolic Execution_. <http://is.muni.cz/repo/984069/sse.pdf>

[2] <http://www.fi.muni.cz/~xstrejc/publications/tacas2016symbiotic_preprint.pdf>

[Symbiotic presentation, TACAS 2016](symbiotic_tacas2016.pdf)
