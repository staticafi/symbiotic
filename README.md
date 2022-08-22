
[![Build - Linux CI](https://github.com/staticafi/symbiotic/actions/workflows/linux.yml/badge.svg)](https://github.com/staticafi/symbiotic/actions/workflows/linux.yml)

Symbiotic is an open-source framework for program analysis integrating
instrumentation, static program slicing and various program analysis tools.
Symbiotic is highly modular and most of its components are self-standing
programs or LLVM passes that have their own repositories at
https://github.com/staticafi.

## Getting started

### Downloading Symbiotic

Tarballs with Symbiotic distribution can be downloaded from
https://github.com/staticafi/symbiotic/releases. The latest release is the [fixed version of Symbiotic archive that competed in SV-COMP 21](https://github.com/staticafi/symbiotic/releases/tag/svcomp21).
Alternatively, you can download archives used in [SV-COMP 2021](https://gitlab.com/sosy-lab/sv-comp/archives-2021/-/blob/master/2021/symbiotic.zip)
(compiled on Ubuntu 20) or [SV-COMP 2020](https://gitlab.com/sosy-lab/sv-comp/archives-2020/-/blob/master/2020/symbiotic.zip) (compiled on Ubuntu 18).

After unpacking, Symbiotic should be ready to go.

### Docker image

WARNING: is not up-to-date.

You can use also the docker image, but we do not keep them up to date:

```
docker pull mchalupa/symbiotic
docker run -ti mchalupa/symbiotic
```

### Building Symbiotic from Sources

First of all you must clone the repository:

```
$ git clone https://github.com/staticafi/symbiotic
```

Run `build.sh` or `system-build.sh` script to compile Symbiotic:

```
$ cd symbiotic
$ ./build.sh -j2
```
The difference betwee `build.sh` and `system-build.sh` is that
`system-build.sh` will try to build only the components of Symbiotic, using the
system's packages.  `build.sh`, on the other hand, tries to build also the most
of the missing dependencies, including LLVM, z3, etc.

The scripts should complain about missing dependencies if any. You can try using
`scripts/install-system-dependencies.sh` script to install the main
dependencies (or at least check the names of packages). If the build script
continues to complain, you must install the dependencies manually.

Possible options for the `build.sh` script include:
  - `build-type=TYPE` (TYPE one of `Release`, `Debug`)
  - `llvm-version=VERSION` (the default `VERSION` is `10.0.1`,
     other versions are rather experimental)
  - `with-llvm=`, `with-llvm-src=`, `with-llvm-dir=`
     This set of options orders the script to use already built external LLVM
     (the build script will build LLVM otherwise if it has not been built
     already in this folder)
  - `no-llvm` Do not try building LLVM

There are many other options, but they are not properly documented (check the
script). Actually, the whole build script should be rather a guidance of what
is needed and how to build the components, but is not guaranteed to work on any
system.

As you can see from the example, you can pass also arguments for make, e.g.
`-j2`, to the build script.  If you need to specify paths to header files or
libraries, you can do it by passing `CFLAGS`, `CPPFLAGS`, and/or `LDFLAGS`
environment variables either by exporting them beforehand, or by passing them
on the command line similarly to make options (e.g. ./build.sh `CFLAGS='-g'`)

If everything goes well, Symbiotic components are built and should be usable
right from the build directories (see the next section for more details).
Also, the components are installed to the `install/` directory that can be
packed or copied wherever you need (you can use ./build.sh `archive` to create
a .zip file or `full-archive` to create .zip file including system libraries
like libc with the build script).
The `install/` directory is under `git` control, so you can see the differences
between versions or manually create an archive using `git archive` command.

When building on mac, you may need to build LLVM with shared libraries
(modify the build script) or use `with-llvm-*` switch with your LLVM build.

### Running Symbiotic

You can run Symbiotic directly from the root directory:
```
scripts/symbiotic <OPTIONS> file.c
```
If you run symbiotic from the `scripts/` directory, it uses the components
directly from the build directories, any changes to the components should
take effect in this mode.

Alternatively, you can run Symbiotic also from the `install/` directory:
```
$ install/bin/symbiotic <OPTIONS> file.c
```

In this mode, Symbiotic uses the components from the `install/` directory.

### Troubleshooting

In the case that something went wrong, try running Symbiotic with `--debug=all`
switch.  When the source code does not contain everything to compile
(i.e. it includes some headers), you can use `CFLAGS` and `CPPFLAGS`
environment variables to pass additional options to the compiler (clang).
Either export them before running Symbiotic, or on one line:

```
CPPFLAGS='-I /lib/gcc/include' scripts/symbiotic file.c
```

You can also use `--cppflags` switch that works exactly the same as environment
variables.  If the program is split into more files, you can give Symbiotic all
the files.  At least one of them must contain the `main` function.

```
scripts/symbiotic main.c additional_definitions.c lib.c
```

Use `--help` switch to see all available options.

### Example

Let's see how you can use Symbiotic to find an error in the following program `test1.c`:

```C
#include <assert.h>
#define N 10

extern int __VERIFIER_nondet_int(void);

int main( ) {
  int a[N];
  for (int i = 0; i < N; ++i) {
	  a[i] = __VERIFIER_nondet_int();
  }

  int swapped = 1;
  while (swapped) {
    swapped = 0;
    for (int i = 1; i < N; ++i) {
      if ( a[i - 1] < a[i] ) {
        int t = a[i];
        a[i] = a[i - 1];
        a[i-1] = t;
        swapped = 1;
      }
    }
  }

  for (int x = 0 ; x < N ; x++ ) {
    for (int y = x+1 ; y < N ; y++ ) {
      assert(a[x] <= a[y]);
    }
  }
  return 0;
}
```

Running `scripts/symbiotic --exit-on-error test1.c` should produce an output similar to the following.
The `--exit-on-error` option ensures that we stop after the first error is found, otherwise the computation
would run for much longer.

```
7.0.0-dev-llvm-9.0.1-symbiotic:5a52b0ca-dg:e89761ff-sbt-slicer:fff6245c-sbt-instrumentation:2f9be629-klee:e643b135
INFO: Optimizations time: 0.028319835662841797
INFO: Starting slicing
INFO: Total slicing time: 0.0068209171295166016
INFO: Optimizations time: 0.027271509170532227
INFO: After-slicing optimizations and transformations time: 2.288818359375e-05
INFO: Starting verification
b'KLEE: WARNING: undefined reference to function: klee_make_nondet'
b'KLEE: ERROR: /home/marek/src/symbiotic/test1.c:27: ASSERTION FAIL: a[x] <= a[y]'
b'KLEE: NOTE: now ignoring this error at this location'
INFO: Verification time: 12.27576208114624

 --- Error trace ---

Error: ASSERTION FAIL: a[x] <= a[y]
File: /home/marek/src/symbiotic/test1.c
Line: 27
assembly.ll line: 172
Stack:
	#000000172 in main () at /home/marek/src/symbiotic/test1.c:27

 --- Sequence of non-deterministic values [function:file:line:col] ---

__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [4 times 0x0] (i32: 0)
__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [3 times 0x0|0x80] (i32: -2147483648)
__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [3 times 0x0|0x80] (i32: -2147483648)
__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [3 times 0x0|0x80] (i32: -2147483648)
__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [3 times 0x0|0x80] (i32: -2147483648)
__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [3 times 0x0|0x80] (i32: -2147483648)
__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [3 times 0x0|0x80] (i32: -2147483648)
__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [3 times 0x0|0x80] (i32: -2147483648)
__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [3 times 0x0|0x80] (i32: -2147483648)
__VERIFIER_nondet_int:test1.c:9:11 := len 4 bytes, [3 times 0x0|0x80] (i32: -2147483648)

 --- ----------- ---
Error found.
INFO: Total time elapsed: 12.659614086151123
```

In some cases, Symbiotic is able to generate also an executable witness.
You must use `--executable-witness` switch. Then, you should see a message
like this in the output:

```
Generating executable witness to : /home/marek/src/symbiotic/witness.exe
```

If you run the binary, it follows the found error path:
```
$ ./witness.exe
witness.exe: /home/marek/src/symbiotic/tests/test1-false-unreach-call.c:27: int main(): Assertion `a[x] <= a[y]' failed.
[1]    18810 abort (core dumped)  ./witness.exe
```

The binary is compiled with the `-g` option, so you can load it into a debugger.


In the default mode, Symbiotic looks for assertion violations.
If you want to look for e.g., errors in memory manipulations, use `--prp`
switch. For example, say you have a file `test2.c` with this contents:

```C
extern void __VERIFIER_error() __attribute__ ((__noreturn__));

struct list {
 int n;
 struct list *next;
};

int i = 1;

struct list* append(struct list *l, int n)
{
 struct list *new_el;

 new_el = malloc(8);
 new_el->n = n;
 new_el->next = l;

 return new_el;
}

int main(void)
{
 struct list *l,m;
 l = &m;
 l->next = 0;
 l->n = 0;

 l = append(l, 1);
 l = append(l, 2);

 if (l->next->next->n == 0)
   __VERIFIER_error();
 return 0;
}
```

If you run `scripts/symbiotic --prp=memsafety test2.c`,
you should get an output similar to the following:

```
7.0.0-dev-llvm-9.0.1-symbiotic:5a52b0ca-dg:e89761ff-sbt-slicer:fff6245c-sbt-instrumentation:2f9be629-klee:e643b135
INFO: Starting instrumentation
wrapper: `which slllvm` failed with error code 1

INFO: Instrumentation time: 0.04639697074890137
INFO: Optimizations time: 0.02850055694580078
INFO: Starting slicing
INFO: Total slicing time: 0.00681614875793457
INFO: Optimizations time: 0.02629995346069336
INFO: After-slicing optimizations and transformations time: 2.7894973754882812e-05
INFO: Starting verification
b'KLEE: WARNING ONCE: Alignment of memory from call "malloc" is not modelled. Using alignment of 8.'
b'KLEE: ERROR: /home/marek/src/symbiotic/test2_false-valid-deref.c:16: memory error: out of bound pointer'
b'KLEE: NOTE: now ignoring this error at this location'
INFO: Verification time: 0.029797792434692383

 --- Error trace ---

Error: memory error: out of bound pointer
File: /home/marek/src/symbiotic/test2_false-valid-deref.c
Line: 16
assembly.ll line: 31
Stack:
	#000000031 in append (=94514011128176, =1) at /home/marek/src/symbiotic/test2_false-valid-deref.c:16
	#100000064 in main () at /home/marek/src/symbiotic/test2_false-valid-deref.c:28
Info:
	address: 26:94514011726424
	pointing to: object at 94514011726416 of size 8
		MO15[8] allocated at append():  %7 = call i8* @malloc(i64 8), !dbg !23

 --- Sequence of non-deterministic values [function:file:line:col] ---


 --- ----------- ---
Error found.
INFO: Total time elapsed: 0.6174993515014648
```

If you would omit the `--prp=memsafety` switch, you would see that Symbiotic
reports no error. However, the output mentions some memory errors.
This means that Symbiotic hit an error but different one that it should look for.
Note that the difference is not only in parsing the output.
Since Symbiotic slices the program w.r.t
error-sites, it may remove some errors that are not related to the particular
error that we looked for. So the fact that Symbiotic found an invalid
dereference even though it did not look for that is just a lucky
coincidence and may not be true for other programs.

### Verification backends

By default, Symbiotic runs KLEE to analyze the program.
However, it can use many other tools for the analysis. Here is the list
of supported tools (some of them are integrated rather experimentally
and may not work seamlessly):

|tool        | switch               |
|------------|----------------------|
|KLEE        | `--target=klee`      |
|CPAchecker  | `--target=cpachecker`|
|DIVINE      | `--target=divine`    |
|CBMC        | `--target=cbmc`      |
|SMACK       | `--target=smack`     |
|SeaHorn     | `--target=seahorn`   |
|Nidhugg     | `--target=nidhugg`   |
|IKOS        | `--target=ikos`      |
|UAutomizer  | `--target=ultimate`  |

### CC mode

Symbiotic can also just output the transformed bitcode or generate C code
from the transformed bitcode. ...TBD...

### Symbiotic Components

Components of Symbiotic can be found at https://github.com/staticafi with the
only exception of `dg` library that is currently at https://github.com/mchalupa/dg.
All software used in Symbiotic are open-source projects and are licensed under various
open-source licenses (mostly MIT license,
and University of Illinois Open Source license)

## Contact

For more information send an e-mail to <statica@fi.muni.cz>.
