What is Symbiotic?
======================

Symbiotic is a tool for verifying computer programs. It uses three well-know techniques -
instrumentation, slicing and symbolic execution. Symbiotic is highly modular,
so most of the components are in self-standing repositories (see https://github.com/staticafi)
## Getting started
### Downloading Symbiotic
Tarball with Symbiotic distribution can be downloaded from https://github.com/staticafi/symbiotic/releases
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

There is a known problem that can arise while building KLEE:

```
llvm-config: error: missing: /home/mchalupa/src/symbiotic/llvm-3.9.1/build/lib/libgtest.a
llvm-config: error: missing: /home/mchalupa/src/symbiotic/llvm-3.9.1/build/lib/libgtest_main.a
CMake Error at cmake/find_llvm.cmake:62 (message):
  Failed running
  /home/mchalupa/src/symbiotic/llvm-3.9.1/build/bin/llvm-config;--system-libs
Call Stack (most recent call first):
  cmake/find_llvm.cmake:163 (_run_llvm_config)
  lib/Basic/CMakeLists.txt:19 (klee_get_llvm_libs)
```
This is due to [b5cd41e2](https://github.com/llvm-mirror/llvm/commit/b5cd41e26f89aad2f2dc4f5dc37577f7abf8528a) commit in LLVM. Until we have this fixed, the fastest workaround is to just create empty files `build/lib/libgtest.a` and `build/lib/libgtest_main.a` in the LLVM's folder.

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

Components of Symbiotic can be found at https://github.com/staticafi with the only exception of the slicer, that can be found at https://github.com/mchalupa/dg (it will be moved to _staticafi_ in the future though). All parts of Symbiotic are open-source projects and are licensed under various open-source licenses (GPL, MIT license, University of Illinois Open Source license)

## Contact

For more information send an e-mail to <statica@fi.muni.cz>. We'll be happy to answer your questions :)
