# Building Symbiotic via system-build.sh

The following text summarizes our experience in building
Symbiotic on some particular systems. It may be out of date, though.
In case of any trouble, contact us by [email](mailto:statica@fi.muni.cz).

The first step in any of these guides is to clone symbiotic via git
into a folder (say `symbiotic`):

```
git clone https://github.com/staticafi/symbiotic
cd symbiotic
```

## Building on Ubuntu

TBD

## Building on Fedora

TBD

## Building on CentOS

### CentOS 8

If you use `scripts/install-system-dependencies.sh`, you must have the `sudo`
and `which` executables (or hack the script and run it as root).

If you want to install the dependencies manually, run the following command:

```
dnf which curl wget rsync make cmake unzip tar patch glibc-devel.i686 xz zlib llvm-devel clang python38
```

Note: The package python38 may get obsolete. Use any package that installs Python 3.
Also, if you wish Symbiotic to build components that link to LLVM statically,
you must install `llvm-static` package. Probably you will need to force
the static compilation with `-DLLVM_LINK_DYLIB=on` option added to every configuration
of a component (dg, sbt-slicer, ...).

CentOS does not contain Z3 package in the official mirros, so one must compile
it manually. In the very unlikely case that you installed Python for the first
time with the command above, you must create the "unversioned" link so that the
build of Z3 can find `python` binary:

```
sudo alternatives --set python /usr/bin/python3
```

Now we can clone and compile Z3. Symbiotic assumes that Z3 is compiled inside
the `z3` subdirectory of `symbiotic` directory. Do not change the paths unless
you install Z3 system-wide -- in that case Symbiotic will be able to find it in
later stages. If you change the paths, you must fix them later when compiling
KLEE inside `system-build.sh` script:

```
git clone git://github.com/Z3Prover/z3 -b "z3-4.8.4" z3
mkdir -p "z3/build" && pushd "z3/build"
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4
make install
popd
```

Note: you may try using a newer version of z3.

Before proceeding, we must also install the SQL and zlib packages 
that are needed by KLEE:

```
dnf install sqlite-devel zlib-devel
```

Now we can run the `system-build.sh` script that will finish the compilation of
Symbiotic:

```
./system-build.sh -j2
```

## Building on Arch Linux

TBD
