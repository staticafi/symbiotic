Symbiotic is an open-source tool for finding bugs in sequential computer programs.
It is based on three well-know techniques:
instrumentation, static program slicing and symbolic execution.
Symbiotic is highly modular and most of its components are self-standing programs or LLVM passes that have their own repositories at https://github.com/staticafi.

## Getting started

### Downloading Symbiotic

Tarballs with Symbiotic distribution can be downloaded from https://github.com/staticafi/symbiotic/releases.
Alternatively, you can download archives used in [SV-COMP 2018](https://gitlab.com/sosy-lab/sv-comp/archives/raw/svcomp18/2018/symbiotic.zip) or [SV-COMP 2019](https://gitlab.com/sosy-lab/sv-comp/archives-2019/raw/svcomp19/2019/symbiotic.zip).

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

Run `build.sh` script to compile Symbiotic:

```
$ cd symbiotic
$ ./build.sh -j2
```

The build script will complain about missing dependencies if any. You can try using `scripts/install-system-dependencies.sh` script to install the main dependencies (or at least check the names of packages). If the build script continues to complain, you must install the dependencies manually.

If you need to adjust the build process, you can pass different options to the build script.
Possible options include:
  - `build-type=TYPE` (TYPE one of `Release`, `Debug`)
  - `llvm-version=VERSION` (the default `VERSION` is `4.0.1`, other versions are rather experimental)
  - `with-llvm=`, `with-llvm-src=`, `with-llvm-dir=` This set of options orders the script to use already built external LLVM (the build script will build LLVM otherwise if it has not been built already in this folder)
  - `no-llvm` Do not try building LLVM

There are many other options, but they are not properly documented (check the script). Actually, the whole build script should be rather a guidance of what is needed and how to build the components, but is not guaranteed to work on any system.

As you can see from the example, you can pass also arguments for make, e.g. `-j2`, to the build script.
If you need to specify paths to header files or libraries, you can do it
by passing `CFLAGS`, `CPPFLAGS`, and/or `LDFLAGS` environment variables either by exporting
them beforehand, or by passing them as make options (e.g. `CFLAGS='-g'`)

If everything goes well, Symbiotic components are built and also installed
to the `install/` directory that can be packed or copied wherever you need (you can use `archive` to create a .zip file
or `full-archive` to create .zip file including system libraries like libc with the build script).
This directory is under `git` control, so you can see the differences between
versions or make an archive using `git archive` command.

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
All software used in Symbiotic are open-source projects and are licensed under various
open-source licenses (mostly MIT license,
and University of Illinois Open Source license)

## Contact

For more information send an e-mail to <statica@fi.muni.cz>.
