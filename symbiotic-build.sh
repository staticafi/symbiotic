#!/bin/bash
#
# Build Symbiotic from scratch and setup environment for
# development if needed
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

set -x

usage()
{
	echo "$0 [shell] [no-llvm] [update] [slicer | scripts | minisat | stp | klee | witness | bin] OPTS"
	echo "" # new line
	echo -e "shell    - run shell with environment set"
	echo -e "no-llvm  - skip compiling llvm (assume that llvm is already"
	echo -e "           present in build directory in folders"
	echo -e "           llvm-build-cmake and llvm-build-configure)"
	echo -e "update   - update repositories"
	echo -e "with-cpa - download CPAchecker (due to witness checking)"
	echo -e "with-ultimate-automizer - download UltimateAutmizer (due to witness checking)"
	echo -e "with-llvm=path     - use llvm from path"
	echo -e "with-llvm-dir=path - use llvm from path"
	echo -e "with-llvm-src=path - use llvm sources from path"
	echo "" # new line
	echo -e "slicer, scripts,"
	echo -e "minisat, stp, klee, witness"
	echo -e "bin     - run compilation _from_ this point"
	echo "" # new line
	echo -e "OPTS = options for make (i. e. -j8)"
}

export PREFIX=`pwd`/install
export SYMBIOTIC_ENV=1

export LD_LIBRARY_PATH="$PREFIX/lib:$LD_LIBRARY_PATH"

FROM='0'
NO_LLVM='0'
UPDATE=
OPTS=
WITH_CPA='0'
WITH_ULTIMATEAUTOMIZER='0'
LLVM_VERSION=3.8.1
WITH_LLVM=
WITH_LLVM_SRC=
WITH_LLVM_DIR=

RUNDIR=`pwd`
SRCDIR=`dirname $0`
ABS_RUNDIR=`readlink -f $RUNDIR`
ABS_SRCDIR=`readlink -f $SRCDIR`

MODE="$1"

while [ $# -gt 0 ]; do
	case $1 in
		'shell')
			# stp needs this
			ulimit -s unlimited

			# most of the environment is already set
			export PATH=$PREFIX/bin:$PATH
			exec $SHELL
		;;
		'help'|'--help')
			usage
			exit 0
		;;
		'slicer')
			FROM='1'
		;;
		'minisat')
			FROM='2'
		;;
		'stp')
			FROM='3'
		;;
		'klee')
			FROM='4'
		;;
		'witness')
			FROM='5'
		;;
		'scripts')
			FROM='6'
		;;
		'bin')
			FROM='7'
		;;
		'no-llvm')
			NO_LLVM=1
		;;
		'update')
			UPDATE=1
		;;
		'with-cpa')
			WITH_CPA='1'
		;;
		'with-ultimate-automizer')
			WITH_ULTIMATEAUTOMIZER='1'
		;;
		with-llvm=*)
			WITH_LLVM=${1##*=}
		;;
		with-llvm-src=*)
			WITH_LLVM_SRC=${1##*=}
		;;
		with-llvm-dir=*)
			WITH_LLVM_DIR=${1##*=}
		;;
		*)
			if [ -z "$OPTS" ]; then
				OPTS="$1"
			else
				OPTS="$OPTS $1"
			fi
		;;
	esac
	shift
done

if [ "x$OPTS" = "x" ]; then
	OPTS='-j1'
fi

# create prefix directory
mkdir -p $PREFIX/bin
mkdir -p $PREFIX/lib
mkdir -p $PREFIX/lib32
mkdir -p $PREFIX/include

clean_and_exit()
{
	CODE="$1"

	if [ "$2" = "git" ]; then
		git clean -xdf
	else
		rm -rf *
	fi

	exit $CODE
}

exitmsg()
{
	echo "$1" >/dev/stderr
	exit 1
}

build()
{
	make "$OPTS" CFLAGS="$CFLAGS" CPPFLAGS="$CPPFLAGS" LDFLAGS="$LDFLAGS" $@ || exit 1
	return 0
}

git_clone_or_pull()
{

	REPO="$1"
	FOLDER="$2"
	shift;shift

	if [ -d "$FOLDER" ]; then
		if [ "x$UPDATE" = "x1" ]; then
			cd $FOLDER && git pull && cd -
		fi
	else
		git clone $REPO $FOLDER $@
	fi
}

git_submodule_init()
{
	cd "$SRCDIR"

	git submodule init || exitmsg "submodule init failed"
	git submodule update || exitmsg "submodule update failed"

	cd -
}

check()
{
	if ! wget --version &>/dev/null; then
		if ! curl --version &>/dev/null; then
			echo "Need wget or curl to download files"
			exit 1
		fi

		# try replace wget with curl
		alias wget='curl -O'
	fi

	if ! python --version 2>&1 | grep -q 'Python 2'; then
		echo "llvm-3.2 needs python 2 to build"
		exit 1
	fi

	if ! bison --version &>/dev/null; then
		echo "STP needs bison program"
		exit 1
	fi

	if ! flex --version &>/dev/null; then
		echo "STP needs flex program"
		exit 1
	fi

	if [ "x$WITH_LLVM" != "x" ]; then
		if [ ! -d "$WITH_LLVM" ]; then
			exitmsg "Invalid LLVM directory given: $WITH_LLVM"
		fi
	fi
	if [ "x$WITH_LLVM_SRC" != "x" ]; then
		if [ ! -d "$WITH_LLVM_SRC" ]; then
			exitmsg "Invalid LLVM src directory given: $WITH_LLVM_SRC"
		fi
	fi
	if [ "x$WITH_LLVM_DIR" != "x" ]; then
		if [ ! -d "$WITH_LLVM_DIR" ]; then
			exitmsg "Invalid LLVM src directory given: $WITH_LLVM_DIR"
		fi
	fi

}

# check if we have everything we need
check

build_llvm()
{
	if [ ! -d "llvm-${LLVM_VERSION}" ]; then
		wget http://llvm.org/releases/${LLVM_VERSION}/llvm-${LLVM_VERSION}.src.tar.xz || exit 1
		wget http://llvm.org/releases/${LLVM_VERSION}/cfe-${LLVM_VERSION}.src.tar.xz || exit 1

		tar -xf llvm-${LLVM_VERSION}.src.tar.xz || exit 1
		tar -xf cfe-${LLVM_VERSION}.src.tar.xz || exit 1

                # rename llvm folder
                mv llvm-${LLVM_VERSION}.src llvm-${LLVM_VERSION}
		# move clang to llvm/tools and rename to clang
		mv cfe-${LLVM_VERSION}.src llvm-${LLVM_VERSION}/tools/clang


		rm -f llvm-${LLVM_VERSION}.src.tar.xz &>/dev/null || exit 1
		rm -f cfe-${LLVM_VERSION}.src.tar.xz &>/dev/null || exit 1
	fi

	mkdir -p llvm-build-cmake
	cd llvm-build-cmake || exitmsg "downloading failed"

	# configure llvm
	if [ ! -d CMakeFiles ]; then
		echo 'we should definitely build RelWithDebInfo here, no?'
		echo 'N.B. we strip below anyway, so why not Release actually?'
		cmake ../llvm-${LLVM_VERSION} \
			-DCMAKE_BUILD_TYPE=Release\
			-DLLVM_INCLUDE_EXAMPLES=OFF \
			-DLLVM_INCLUDE_TESTS=OFF \
			-DLLVM_ENABLE_TIMESTAMPS=OFF \
			-DLLVM_TARGETS_TO_BUILD="X86" \
			-DLLVM_ENABLE_PIC=ON \
			-DCMAKE_C_FLAGS_DEBUG="-O0 -g" \
			-DCMAKE_CXX_FLAGS_DEBUG="-O0 -g" || clean_and_exit
	fi

	# build llvm
	ONLY_TOOLS='opt clang llvm-link llvm-dis llvm-nm' build
	cd -
}

######################################################################
#   get LLVM either from user provided location or from the internet,
#   bulding it
######################################################################
if [ $FROM -eq 0 -a $NO_LLVM -ne 1 ]; then
	if [ -z "$WITH_LLVM" ]; then
		build_llvm
		LLVM_LOCATION=llvm-build-cmake
	else
		LLVM_LOCATION=$WITH_LLVM
	fi

	# we need these binaries in symbiotic
	cp $LLVM_LOCATION/bin/clang $PREFIX/bin/clang || exit 1
	cp $LLVM_LOCATION/bin/opt $PREFIX/bin/opt || exit 1
	cp $LLVM_LOCATION/bin/llvm-link $PREFIX/bin/llvm-link || exit 1
	cp $LLVM_LOCATION/bin/llvm-nm $PREFIX/bin/llvm-nm || exit 1
fi

if [ -z "$WITH_LLVM" ]; then
	export LLVM_DIR=$ABS_RUNDIR/llvm-build-cmake/share/llvm/cmake/
	export LLVM_BUILD_PATH=$ABS_RUNDIR/llvm-build-cmake/
else
	export LLVM_DIR=$WITH_LLVM/share/llvm/cmake/
	export LLVM_BUILD_PATH=$WITH_LLVM
fi

if [ -z "$WITH_LLVM_SRC" ]; then
	export LLVM_SRC_PATH="$ABS_RUNDIR/llvm-${LLVM_VERSION}/"
else
	export LLVM_SRC_PATH="$WITH_LLVM_SRC"
fi

# do not do any funky nested ifs, just override the LLVM_DIR
# in the case we are given that variable
if [ ! -z "$WITH_LLVM_DIR" ]; then
	LLVM_DIR=$WITH_LLVM_DIR
fi

######################################################################
#   slicer
######################################################################
if [ $FROM -le 1 ]; then
	git_submodule_init

#	cd "$SRCDIR/LLVMSlicer" || exitmsg "Cloning failed"
#	if [ ! -d CMakeFiles ]; then
#		cmake . \
#			-DLLVM_SRC_PATH="$ABS_RUNDIR/llvm-${LLVM_VERSION}/" \
#			-DLLVM_BUILD_PATH="$ABS_RUNDIR"/llvm-build-cmake/ \
#			-DLLVM_DIR=$LLVM_DIR \
#			-DCMAKE_INSTALL_PREFIX=$PREFIX \
#			|| clean_and_exit 1 "git"
#	fi
#
#	(build && make install) || exit 1
#
#	cd -

	# download new slicer
	cd "$SRCDIR/dg" || exitmsg "Cloning failed"
	if [ ! -d CMakeFiles ]; then
		cmake . \
			-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
			-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
			-DLLVM_DIR=$LLVM_DIR \
			-DCMAKE_INSTALL_PREFIX=$PREFIX \
			|| clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1
	cd -
fi

######################################################################
#   minisat
######################################################################
if [ $FROM -le 2 ]; then
	git_clone_or_pull git://github.com/stp/minisat.git minisat
	cd minisat
	(build lr && make prefix=$PREFIX install-headers) || exit 1
	cp build/release/lib/libminisat.a $PREFIX/lib/ || exit 1

	cd -
fi

######################################################################
#   STP
######################################################################
if [ $FROM -le 3 ]; then
	git_clone_or_pull git://github.com/stp/stp.git stp
	cd stp || exitmsg "Cloning failed"
	if [ ! -d CMakeFiles ]; then
		cmake . -DCMAKE_INSTALL_PREFIX=$PREFIX \
			-DCMAKE_CXX_FLAGS_RELEASE=-O2 \
			-DCMAKE_C_FLAGS_RELEASE=-O2 \
			-DCMAKE_BUILD_TYPE=Release \
			-DBUILD_SHARED_LIBS:BOOL=OFF \
			-DENABLE_PYTHON_INTERFACE:BOOL=OFF || clean_and_exit 1 "git"
	fi

	(build "OPTIMIZE=-O2 CFLAGS_M32=install" && make install) || exit 1
	cd -
fi

######################################################################
#   build LLVM using configure for KLEE
######################################################################
if [ $FROM -le 4 -a $NO_LLVM -ne 1 ]; then
	# we must build llvm once again with configure script (klee needs this)
	mkdir -p llvm-build-configure || exitmsg "Creating building directory failed"
	cd llvm-build-configure

	# on some systems the libxml library is libxml2 library and
	# the paths are mismatched. Use pkg-config in this case. If it won't
	# work, user has work to do ^_^
	if pkg-config --exists libxml-2.0; then
		export CPPFLAGS="$CPPFLAGS `pkg-config --cflags libxml-2.0`"
		export LDFLAGS="$LDFLAGS `pkg-config --libs libxml-2.0`"
	fi

	# configure llvm if not done yet
	if [ ! -f config.log ]; then
		# llvm does not built with gcc-4, so use gcc-5 & g++-5 if available
		if gcc --version 2>&1 | grep -q '5\..*'; then
			CC=gcc
			CXX=g++
		elif which gcc-5 2>&1; then
			CC=gcc-5
			CXX=gcc++-5
		elif which clang 2>&1; then
			CC=clang
			CXX=clang++
		else
			# let's see what happens
			CC=gcc
			CXX=g++
		fi

		$LLVM_SRC_PATH/configure \
			CC=$CC CXX=$CXX \
			--enable-optimized --enable-assertions \
			--enable-targets=x86 --enable-docs=no \
			--enable-timestamps=no || clean_and_exit 1
	fi

	build || exit 1
	cd -
fi


######################################################################
#   KLEE
######################################################################
if [ $FROM -le 4 ]; then
	# build klee
	git_clone_or_pull "-b 3.0.7 git://github.com/staticafi/klee.git" klee || exitmsg "Cloning failed"

	mkdir -p klee-build/
	cd klee-build/

	if [ ! -f config.log ]; then
	../klee/configure \
		--prefix=$PREFIX \
		--without-zlib \
		--with-llvmsrc=$LLVM_SRC_PATH \
		--with-llvmobj=`pwd`/../llvm-build-configure \
		--with-stp=$PREFIX || clean_and_exit 1 "git"
	fi

	# clean runtime libs, it may be 32-bit from last build
	make -C runtime clean 2>/dev/null
	rm -f Release+Asserts/lib/kleeRuntimeIntrinsic.bc* 2>/dev/null
	rm -f Release+Asserts/lib/klee-libc.bc* 2>/dev/null

	# build 64-bit libs and install them to prefix
	pwd
	(build "ENABLE_SHARED=0" && make install) || exit 1

	# clean 64-bit build and build 32-bit version of runtime library
	make -C runtime clean \
		|| exitmsg "Failed building klee 32-bit runtime library"
	rm -f Release+Asserts/lib/kleeRuntimeIntrinsic.bc*
	rm -f Release+Asserts/lib/klee-libc.bc*
	make -C runtime/Intrinsic CFLAGS=-m32 ENABLE_SHARED=0 \
		|| exitmsg "Failed building 32-bit klee runtime library"
	make -C runtime/klee-libc CFLAGS=-m32 ENABLE_SHARED=0 \
		|| exitmsg "Failed building 32-bit klee runtime library"

	# copy 32-bit library version to prefix
	mkdir -p $PREFIX/lib32/klee/runtime
	cp Release+Asserts/lib/kleeRuntimeIntrinsic.bc \
		$PREFIX/lib32/klee/runtime/kleeRuntimeIntrinsic.bc \
		|| exitmsg "Did not build 32-bit klee runtime lib"
	cp Release+Asserts/lib/klee-libc.bc \
		$PREFIX/lib32/klee/runtime/klee-libc.bc \
		|| exitmsg "Did not build 32-bit klee runtime lib"


	cd -
fi

download_tar()
{
	wget "$1" || exit 1
	BASENAME="`basename $1`"
	tar xf "$BASENAME" || exit 1
	rm -f "BASENAME"
}

get_cpa()
{
	if [ ! -d CPAchecker-1.4-unix ]; then
		download_tar https://cpachecker.sosy-lab.org/CPAchecker-1.6.1-unix.tar.bz2
	fi
}

get_ultimize()
{
	if [ ! -d UltimateAutomizer ]; then
		download_tar http://www.sosy-lab.org/~dbeyer/cpa-witnesses/ultimateautomizer.tar.gz
	fi
}

######################################################################
#   witness checkers
######################################################################
if [ $FROM -le 5 ]; then
	if [ $WITH_CPA -eq 1 ]; then
		get_cpa
		rsync -a CPAchecker-1.6.1-unix/ $PREFIX/CPAchecker/
	fi
	if [ $WITH_ULTIMATEAUTOMIZER -eq 1 ]; then
		get_ultimize
		rsync -a UltimateAutomizer $PREFIX/
	fi
fi

######################################################################
#   instrumentation and scripts
######################################################################
if [ $FROM -le 6 ]; then

	# build prepare and install lib and scripts
	if [ ! -d CMakeFiles ]; then
		cmake . \
			-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
			-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
			-DLLVM_DIR=$LLVM_DIR \
			-DCMAKE_INSTALL_PREFIX=$PREFIX \
			|| clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1

	# download scripts
	git_submodule_init

	cd "$SRCDIR/LLVMInstrumentation" || exitmsg "Cloning failed"
	if [ ! -d CMakeFiles ]; then
		./bootstrap-json.sh || exitmsg "Failed generating json files"
		cmake . \
			-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
			-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
			-DLLVM_DIR=$LLVM_DIR \
			-DDG_PATH=$ABS_SRCDIR/dg \
			-DCMAKE_INSTALL_PREFIX=$PREFIX \
			|| clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1

	# we need the config files and error checkers
	mkdir -p $PREFIX/instrumentation
	rsync -r instrumentations/null_deref $PREFIX/instrumentation
	rsync -r instrumentations/double_free $PREFIX/instrumentation
	rsync -r instrumentations/valid_deref $PREFIX/instrumentation

	cd -

	# and also the symbiotic scripts itself
	cp $SRCDIR/symbiotic $PREFIX/ || exit 1
	cp -r $SRCDIR/lib/symbioticpy $PREFIX/lib || exit 1

	cd "$SRCDIR"

fi


######################################################################
#  extract versions of components
######################################################################
if [ $FROM -le 7 ]; then

	SYMBIOTIC_VERSION=`git rev-parse HEAD`
	cd dg || exit 1
	DG_VERSION=`git rev-parse HEAD`
	cd -
	cd svc15 || exit 1
	SVC15_VERSION=`git rev-parse HEAD`
	cd -
	cd LLVMInstrumentation || exit 1
	INSTRUMENTATION_VERSION=`git rev-parse HEAD`
	cd -
	cd minisat || exit 1
	MINISAT_VERSION=`git rev-parse HEAD`
	cd -
	cd stp || exit 1
	STP_VERSION=`git rev-parse HEAD`
	cd -
	cd klee || exit 1
	KLEE_VERSION=`git rev-parse HEAD`
	cd -

	VERSFILE="$PREFIX/lib/symbioticpy/symbiotic/versions.py"
	echo "#!/usr/bin/python" > $VERSFILE
	echo "# This file is automatically generated by symbiotic-build.sh" >> $VERSFILE
	echo "" >> $VERSFILE
	echo "versions = {" >> $VERSFILE
	echo -e "\t'symbiotic' : '$SYMBIOTIC_VERSION'," >> $VERSFILE
	echo -e "\t'dg' : '$DG_VERSION'," >> $VERSFILE
	echo -e "\t'svc15' : '$SVC15_VERSION'," >> $VERSFILE
	echo -e "\t'LLVMInstrumentation' : '$INSTRUMENTATION_VERSION'," >> $VERSFILE
	echo -e "\t'minisat' : '$MINISAT_VERSION'," >> $VERSFILE
	echo -e "\t'stp' : '$STP_VERSION'," >> $VERSFILE
	echo -e "\t'KLEE' : '$KLEE_VERSION'," >> $VERSFILE
	echo -e "}\n" >> $VERSFILE
fi

######################################################################
#  create distribution
######################################################################
if [ $FROM -le 7 ]; then
	cd $PREFIX || exitmsg "Whoot? prefix directory not found! This is a BUG, sir..."

	# create git repository and add all files that we need
	# then remove the rest and create distribution
	BINARIES="bin/clang bin/opt bin/klee bin/llvm-link bin/llvm-nm bin/llvm-slicer"
	LIBRARIES="\
		lib/libLLVMdg.so lib/libLLVMpta.so lib/libPTA.so lib/libRD.so\
		lib/LLVMsvc15.so \
		lib/klee/runtime/kleeRuntimeIntrinsic.bc \
		lib32/klee/runtime/kleeRuntimeIntrinsic.bc\
		lib/klee/runtime/klee-libc.bc\
		lib32/klee/runtime/klee-libc.bc"
#		lib/LLVMSlicer.so
	INSTR="bin/LLVMinstr\
	       instrumentation/null_deref/config.json\
	       instrumentation/null_deref/null_deref.c\
	       instrumentation/double_free/config.json\
	       instrumentation/double_free/double_free.c\
	       instrumentation/valid_deref/config.json\
	       instrumentation/valid_deref/valid_deref.c"

	CPACHECKER=
	ULTIAUTO=
	if [ $WITH_CPA -eq 1 ]; then
		CPACHECKER=`find CPAchecker/ -type f`
	fi
	if [ $WITH_ULTIMATEAUTOMIZER -eq 1 ]; then
		ULTIAUTO=`find UltimateAutomizer/ -type f`
	fi

	#strip binaries, it will save us 500 MB!
	strip $BINARIES

	git init
	git add \
		$BINARIES \
		$LIBRARIES \
		$INSTR\
		$CPACHECKER \
		$ULTIAUTO \
		symbiotic \
		include/symbiotic.h \
		include/symbiotic-size_t.h \
		lib/*.c \
		lib/symbioticpy/symbiotic/*.py \
		lib/symbioticpy/symbiotic/utils/*.py \
		lib/symbioticpy/symbiotic/witnesses/*.py

	git commit -m "Create Symbiotic distribution `date`"
	# remove unnecessary files
# DO NOT: so that the tools are not rebuilt over and over
# They depend on the installed headers and libs.
#	git clean -xdf
fi
