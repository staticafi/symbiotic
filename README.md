Symbiotic is an open-source tool for finding bugs in sequential computer programs.
It is based on three well-know techniques:
instrumentation, static program slicing and symbolic execution.
Symbiotic is highly modular and most of its components are self-standing programs of LLVM passes that have their own repositories at https://github.com/staticafi.

## Getting started

### Downloading Symbiotic
The archive used in SV-COMOP 2018 can be downloaded from [https://gitlab.com/sosy-lab/sv-comp/archives/raw/svcomp18/2018/symbiotic.zip](https://gitlab.com/sosy-lab/sv-comp/archives/raw/svcomp18/2018/symbiotic.zip)

Other tarballs with Symbiotic distribution (not updated reguralry) can be downloaded from https://github.com/staticafi/symbiotic/releases
After unpacking, Symbiotic is ready to go.

### Docker image

You can use also the docker image:

```
docker pull mchalupa/symbiotic
docker run -ti mchalupa/symbiotic
```

### Building Symbiotic from Sources

First of all you must clone the repository:

```
$ git clone https://github.com/staticafi/symbiotic
```

The build script of Symbiotic uses `curl`, `make`, and `cmake`, so make sure
you have them installed (the script will complain otherwise).
STP theorem prover further needs `bison` and `flex` and minisat needs `zlib`.
These components are needed when building KLEE. However, if you do not want to
build Symbiotic with KLEE (and therefore with STP and minisat), then you can comment
these components out in the build script (there is no switch for not building these
components yet).

If you have all the dependencies, you are ready to run the `build.sh` script:


```
$ cd symbiotic
$ ./build.sh -j2
```

And that should be it! However, if something goes wrong or you need to adust the build
process, you can pass different options to the build script. Possible options include:
  - `build-type=TYPE` (TYPE one of `Release`, `Debug`)
  - `llvm-version=VERSION` (the default `VERSION` is `4.0.1`, other versions are rather experimental)
  - `with-llvm=`, `with-llvm-src=`, `with-llvm-dir=` This set of options orders the script to use already built external LLVM (the build script will build LLVM otherwise if it has not been built already in this folder)
  - `with-zlib` Build also zlib
  - `no-llvm` Do not try building LLVM
  - `slicer`, `minisat`, `stp`, `klee`, `scripts`, `bin` Start building Symbiotic from this point


As you can see from the example, you can pass also arguments for make, e.g. `-j2`, to the build script.
If you need to specify paths to header files or libraries, you can do it
by passing `CFLAGS`, `CPPFLAGS`, LDFLAGS environment variables either by exporting
them beforehand, or by passing them as make options (e.g. `CFLAGS='-g'`)

If everything goes well, Symbiotic components are built and also installed
to the `install/` directory that can be packed or copied wherever you need.
This directory is under `git` control, so you can see the differences between
versions or make an archive using `git archive` command.

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

When building on mac, you may need to build LLVM with shared libraries
(modify the build script) or use `with-llvm-*` switch with your LLVM build.

### Running Symbiotic

You can run Symbiotic directly from the root directory:
```
scripts/symbiotic <OPTIONS> file.c
```

Alternatively, you can run Symbiotic also from the install directory:
```
$ install/bin/symbiotic <OPTIONS> file.c
```

In the case that something went wrong, try running Symbiotic with `--debug=OPT` where `OPT`
is one of: `compile`, `instrumentation`, `slicer`, `prepare`, `all`.
When the source code does not contain everything to compile (i.e. it includes
some headers), you can use `CFLAGS` and `CPPFLAGS` environment variables to
pass additional options to the compiler (clang). Either export them before
running Symbiotic, or on one line:

```
CPPFLAGS='-I /lib/gcc/include' scripts/symbiotic file.c
```
You can also use `--cppflags` switch that works exactly the same as environment variables.
If the program is split into more files, you can give Symbiotic all the files.
At least one of them must contain the 'main' function.

```
scripts/symbiotic main.c additional_definitions.c lib.c
```

Use `--help` switch to see all available options.

### Symbiotic Components

Components of Symbiotic can be found at https://github.com/staticafi with the
only exception of `dg` library that is currently at https://github.com/mchalupa/dg.
All sowtware used in Symbiotic are open-source projects and are licensed under various
open-source licenses (mostly MIT license, Apache-2.0,
and University of Illinois Open Source license)

## Contact

For more information send an e-mail to <statica@fi.muni.cz>.
