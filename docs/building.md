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

Then you must make sure you have all the basic dependencies.
We provide a script that is able to install most of the dependencies
for the common operating systems: `scripts/install-system-dependencies.sh`.
If you use this script , you must have the `sudo`
and `which` executables (or hack the script and run it as root).

```
scripts/install-system-dependencies.sh
```

If the script does not work, follow one of the guides bellow.


## Building on Ubuntu

Tested on Ubuntu 20, but should work also for the most of other Ubuntu systems.

Install system dependencies with `scripts/install-ubuntu.sh`
(or `scripts/install-system-dependencies.sh):

```
sudo scripts/install-ubuntu.sh
```

If the script does not work, install the dependencies manually with the following command:

```
apt install curl wget rsync make cmake unzip gcc-multilib xz-utils python zlib1g-dev libz3-dev llvm libsqlite3-dev
```

Now we can run the `system-build.sh` script that will finish the compilation of
Symbiotic:

```
./system-build.sh -j2
```


## Building on Fedora

### Fedora 33

Install system dependencies with `scripts/install-fedora.sh`
(or `scripts/install-system-dependencies.sh):

```
sudo scripts/install-fedora.sh
```

If the script does not work, install the dependencies manually with the following command:

```
dnf install curl wget rsync make cmake unzip tar patch glibc-devel.i686 xz zlib python z3-devel llvm-devel libsq3-devel zlib-static which
```
If you wish Symbiotic to build components that link to LLVM statically,
you must install `llvm-static` package. Maybe you will need to force
the static compilation by overriding LLVM_DYLIB to "on" in the build script
after LLVM is set up.

Now we can run the `system-build.sh` script that will finish the compilation of
Symbiotic:

```
./system-build.sh -j2
```

## Building on CentOS

### CentOS 8

If `scripts/install-system-dependencies.sh` does not work, install the
dependencies manually with the following command:

```
dnf which curl wget rsync make cmake unzip tar patch glibc-devel.i686 xz zlib llvm-devel clang python38
```

Note: The package python38 may get obsolete. Use any package that installs Python 3.
Also, if you wish Symbiotic to build components that link to LLVM statically,
you must install `llvm-static` package. Maybe you will need to force
the static compilation by overriding LLVM_DYLIB to "on" in the build script
after LLVM is set up.

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
git clone https://github.com/Z3Prover/z3 -b "z3-4.8.4" z3
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
