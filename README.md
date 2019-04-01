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

Run `build.sh` or `system-build.sh` script to compile Symbiotic:

```
$ cd symbiotic
$ ./build.sh -j2
```

The scripts will complain about missing dependencies if any. You can try using `scripts/install-system-dependencies.sh` script to install the main dependencies (or at least check the names of packages). If the build script continues to complain, you must install the dependencies manually.
The difference betwee `build.sh` and `system-build.sh` is that `system-build.sh` will
try to build only the components of Symbiotic, using the system's packages.
`build.sh`, on the other hand, tries to build also the most of the missing dependencies,
including LLVM, z3, etc.

Possible options for the `build.sh` script include:
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

### Example

Let's see how you can use Symbiotic to find an error in the following program `test1.c`:

```C
#include <assert.h>
#define N 10

int main( ) { 
  int a[ N ];
  int swapped = 1;
  while ( swapped ) { 
    swapped = 0;
    int i = 1;
    while ( i < N ) { 
      if ( a[i - 1] < a[i] ) { 
        int t = a[i];
        a[i] = a[i - 1]; 
        a[i-1] = t;
        swapped = 1;
      }   
      i = i + 1;
    }   
  }

  int x;
  int y;
  for ( x = 0 ; x < N ; x++ ) { 
    for ( y = x+1 ; y < N ; y++ ) { 
      assert(  a[x] <= a[y]  );  
    }   
  }
  return 0;
}
```

Running `scripts/symbiotic test1.c` should produce an output similar to the following:
```
6.0.3-dev-llvm-4.0.1-symbiotic:e0b1d107-dg:5c2afa4c-sbt-slicer:0739f6e4-sbt-instrumentation:69fc0523-klee:e1cc1262
INFO: Optimizations time: 0.20078516006469727
INFO: Starting slicing
INFO: Total slicing time: 0.01668262481689453
INFO: Optimizations time: 0.15298175811767578
Linked our definitions to these undefined functions:
  __VERIFIER_assert
  __VERIFIER_error
INFO: After-slicing optimizations and transformations time: 0.010685443878173828
INFO: Starting verification
KLEE: ERROR: /home/marek/src/symbiotic/lib/svcomp/klee/__VERIFIER_error.c:9: ASSERTION FAIL: verifier assertion failed
KLEE: NOTE: now ignoring this error at this location
INFO: Verification time: 22.329169750213623
-------------------------------------------------------------------------------
Error found.
RESULT: false(unreach-call)

 --- Error trace ---

Error: ASSERTION FAIL: verifier assertion failed
File: /home/marek/src/symbiotic/lib/svcomp/klee/__VERIFIER_error.c
Line: 9
assembly.ll line: 14
Stack: 
	#000000014 in __VERIFIER_error () at /home/marek/src/symbiotic/lib/svcomp/klee/__VERIFIER_error.c:9
	#100000028 in __VERIFIER_assert (expr) at /home/marek/src/symbiotic/lib/verifier/__VERIFIER_assert.c:8
	#200000099 in main () at /home/marek/src/symbiotic/tests/sum-false-unreach-call.c:25

 --- ----------- ---
Generating error witness: /home/marek/src/symbiotic/witness.graphml
 -- ---- --
Symbolic objects:
b'main:uninitialized:0:1' := len 40 bytes, |0x1|2 times 0x0|0x70|3 times 0x0|0x70|3 times 0x0|0x70|0x1|2 times 0x0|0x60|3 times 0x0|0x60|0x1|2 times 0x0|0x40|3 times 0x0|0x40|0x1|7 times 0x0|0x1|2 times 0x0|0x80|
 -- ---- --
INFO: Total time elapsed: 23.30927062034607
```

Symbiotic found an assertion violation. This is also the default mode of Symbiotic. If you want to look for e.g. errors with pointers, use `--prp=memsafety` switch. Consider this program, say `test2.c`:

```C
extern void __VERIFIER_error() __attribute__ ((__noreturn__));
void __VERIFIER_assert(int);

typedef unsigned int size_t;
extern  __attribute__((__nothrow__)) void *malloc(size_t __size ) __attribute__((__malloc__));

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

 __VERIFIER_assert(l->next->next->n != 0); 
 return 0;
}

```

If you run `scripts/symbiotic --prp=memsafety test2.c`, you should get an output similar to the following:

```
6.0.3-dev-llvm-4.0.1-symbiotic:e0b1d107-dg:5c2afa4c-sbt-slicer:0739f6e4-sbt-instrumentation:69fc0523-klee:e1cc1262
INFO: Starting instrumentation
INFO: Instrumentation time: 0.02246999740600586
INFO: Optimizations time: 0.12847304344177246
INFO: Starting slicing
INFO: Total slicing time: 0.016747236251831055
INFO: Optimizations time: 0.08698320388793945
Linked our definitions to these undefined functions:
  __VERIFIER_assert
  __VERIFIER_error
INFO: After-slicing optimizations and transformations time: 0.012034416198730469
Removed calls to '__symbiotic_keep_ptr' (function is undefined)
INFO: Starting verification
KLEE: WARNING ONCE: Alignment of memory from call "malloc" is not modelled. Using alignment of 8.
KLEE: ERROR: /home/marek/src/symbiotic/tests/list-regression-false-valid-deref.c:24: memory error: out of bound pointer
KLEE: NOTE: now ignoring this error at this location
INFO: Verification time: 0.05180239677429199
-------------------------------------------------------------------------------
Error found.
RESULT: false(valid-deref)

 --- Error trace ---

Error: memory error: out of bound pointer
File: /home/marek/src/symbiotic/tests/list-regression-false-valid-deref.c
Line: 24
assembly.ll line: 21
Stack: 
	#000000021 in append (l=94876668759600, n=1) at /home/marek/src/symbiotic/tests/list-regression-false-valid-deref.c:24
	#100000047 in main () at /home/marek/src/symbiotic/tests/list-regression-false-valid-deref.c:36
Info: 
	address: 12:94876669426520
	pointing to: object at 94876669426512 of size 8
		MO11[8] allocated at append():  %call = tail call noalias i8* @malloc(i32 8) #2, !dbg !22

 --- ----------- ---
Generating error witness: /home/marek/src/symbiotic/witness.graphml
 -- ---- --
Symbolic objects:
b'main:uninitialized:0:2' := len 16 bytes, |16 times 0x0|
b'append:%dynalloc:21:1' := len 8 bytes, |8 times 0x0|
 -- ---- --
INFO: Total time elapsed: 1.111555576324463
```

If you would omit the `--prp=memsafety` switch, you would see that the output ends with `RESULT: unknown(false(valid-deref))`. This means that Symbiotic found an error but different one that it should look for. Note that the difference is not only in the output. Since Symbiotic slices the program w.r.t error-sites, it may remove some errors that are not related to the particular error that we looked for. So the fact that Symbiotic found an invalid dereference even though it looked for assertion violatoin is just a lucky coincidence and may not be true for other programs.

From the later example you can also see that you can use functions from [SV-COMP](http://sv-comp.sosy-lab.org/) in the programs.

### Symbiotic Components

Components of Symbiotic can be found at https://github.com/staticafi with the
only exception of `dg` library that is currently at https://github.com/mchalupa/dg.
All software used in Symbiotic are open-source projects and are licensed under various
open-source licenses (mostly MIT license,
and University of Illinois Open Source license)

## Contact

For more information send an e-mail to <statica@fi.muni.cz>.
