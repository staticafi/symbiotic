#!/bin/bash
#
# Build Symbiotic from scratch and setup environment for
# development if needed. This build script is meant to be more
# of a guide how to build Symbiotic, it may not work in all cases.
#
#  (c) Marek Chalupa, 2016 - 2019
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

#https://unix.stackexchange.com/a/48550
set -E
trap '[ "$?" -ne 77 ] || exit 77' ERR

exitmsg()
{
	echo "$1" >/dev/stderr
	exit 77
}

usage()
{
	echo "$0 [shell] [no-llvm] [update] [archive | full-archive] [slicer | scripts | klee | witness | bin] OPTS"
	echo "" # new line
	echo -e "shell    - run shell with environment set"
	echo -e "no-llvm  - skip compiling llvm"
	echo -e "update   - update repositories"
	echo -e "with-zlib          - compile zlib"
	echo -e "with-llvm=path     - use llvm from path"
	echo -e "with-llvm-dir=path - use llvm from path"
	echo -e "with-llvm-src=path - use llvm sources from path"
	echo -e "llvm-version=ver   - use this version of llvm"
	echo -e "build-type=TYPE    - set Release/Debug build"
	echo -e "build-stp          - build and use STP in KLEE"
	echo -e "build-klee         - build KLEE (default: yes)"
	echo -e "build-nidhugg      - build nidhugg bug-finding tool (default: no)"
	echo -e "archive            - create a zip file with symbiotic"
	echo -e "full-archive       - create a zip file with symbiotic and add non-standard dependencies"
	echo "" # new line
	echo -e "slicer, scripts,"
	echo -e "klee, witness"
	echo -e "bin     - run compilation _from_ this point"
	echo "" # new line
	echo -e "OPTS = options for make (i. e. -j8)"
}

LLVM_VERSION_DEFAULT=4.0.1
get_llvm_version()
{
	# check whether we have llvm already present
	PRESENT_LLVM=`ls -d llvm-*`
	LLVM_VERSION=${PRESENT_LLVM#llvm-*}
	# if we got exactly one version, use it
	if echo ${LLVM_VERSION} | grep  -q '^[0-9]\+\.[0-9]\+\.[0-9]\+$'; then
		echo ${LLVM_VERSION}
	else
		echo ${LLVM_VERSION_DEFAULT}
	fi
}

export PREFIX=`pwd`/install

export LD_LIBRARY_PATH="$PREFIX/lib:$LD_LIBRARY_PATH"
export C_INCLUDE_PATH="$PREFIX/include:$C_INCLUDE_PATH"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/share/pkgconfig:$PKG_CONFIG_PATH"

FROM='0'
NO_LLVM='0'
UPDATE=
OPTS=
LLVM_VERSION=`get_llvm_version`
# LLVM tools that we need
LLVM_TOOLS="opt clang llvm-link llvm-dis llvm-nm"
WITH_LLVM=
WITH_LLVM_SRC=
WITH_LLVM_DIR=
BUILD_STP='no'
BUILD_Z3='no'

BUILD_KLEE="yes"
BUILD_NIDHUGG="no"

check_z3() {
	echo "#include <z3.h>" | gcc - -E &>/dev/null
}

check_zlib() {
	echo "#include <zlib.h>" | gcc - -E &>/dev/null
}

check_32_bit() {
	echo "#include <stdint.h>" | gcc - -E -m32 &>/dev/null
}

HAVE_32_BIT_LIBS=$(if check_32_bit; then echo "yes"; else echo "no"; fi)
HAVE_Z3=$(if check_z3; then echo "yes"; else echo "no"; fi)
WITH_ZLIB=$(if check_zlib; then echo "no"; else echo "yes"; fi)

export LLVM_PREFIX="$PREFIX/llvm-$LLVM_VERSION"

abspath() {
	if which realpath &>/dev/null; then
		realpath "$1" || exitmsg "Can not get absolute path of $1";
	elif [[ "$OSTYPE" == *darwin* ]]; then
		greadlink -f "$1" || exitmsg "Can not get absolute path of $1";
	else
		readlink -f "$1" || exitmsg "Can not get absolute path of $1";
	fi
}

RUNDIR=`pwd`
SRCDIR=`dirname $0`
ABS_RUNDIR=`abspath $RUNDIR`
ABS_SRCDIR=`abspath $SRCDIR`
ARCHIVE="no"
FULL_ARCHIVE="no"

while [ $# -gt 0 ]; do
	case $1 in
		'help'|'--help')
			usage
			exit 0
		;;
		'slicer')
			FROM='1'
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
		'no-klee')
			BUILD_KLEE=no
		;;
		'build-nidhugg')
			BUILD_NIDHUGG="yes"
		;;
		'update')
			UPDATE=1
		;;
		with-zlib)
			WITH_ZLIB="yes"
		;;
		build-stp)
			BUILD_STP="yes"
		;;
		build-z3)
			BUILD_Z3="yes"
		;;
		archive)
			ARCHIVE="yes"
		;;
		full-archive)
			ARCHIVE="yes"
			FULL_ARCHIVE="yes"
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
		llvm-version=*)
			LLVM_VERSION=${1##*=}
			LLVM_PREFIX="$PREFIX/llvm-$LLVM_VERSION"
		;;
		build-type=*)
			BUILD_TYPE=${1##*=}
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

if [ "$HAVE_32_BIT_LIBS" = "no" -a "$BUILD_KLEE" = "yes" ]; then
	exitmsg "KLEE needs 32-bit headers to build 32-bit versions of runtime libraries"
fi

if [ "$HAVE_Z3" = "no" -a "$BUILD_STP" = "no" ]; then
	if [ ! -d "z3" ]; then
		BUILD_Z3="yes"
		echo "Will build z3 as it is missing in the system"
	else
		HAVE_Z3="yes"
		echo "Found z3 directory, using that build"
	fi
fi

# Try to get the previous build type if no is given
if [ -z "$BUILD_TYPE" ]; then
	if [ -f "CMakeCache.txt" ]; then
		BUILD_TYPE=$(cat CMakeCache.txt | grep CMAKE_BUILD_TYPE | cut -f 2 -d '=')
	fi

	# no build type means Release
	[ -z "$BUILD_TYPE" ] && BUILD_TYPE="Release"

	echo "Previous build type identified as $BUILD_TYPE"
fi

if [ "$BUILD_TYPE" != "Debug" -a \
     "$BUILD_TYPE" != "Release" -a \
     "$BUILD_TYPE" != "RelWithDebInfo" -a \
     "$BUILD_TYPE" != "MinSizeRel" ]; then
	exitmsg "Invalid type of build: $BUILD_TYPE";
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

GET="curl -LRO"
check()
{
	MISSING=""
	if ! curl --version &>/dev/null; then
		echo "Need curl to download files"
		MISSING="curl"
	fi

	if ! patch --version &>/dev/null; then
		echo "Need 'patch' utility"
		MISSING="patch $MISSING"
	fi

	if [ "$BUILD_KLEE" = "yes" ]; then
		if ! which unzip &>/dev/null; then
			echo "Need 'unzip' utility"
			MISSING="unzip $MISSING"
		fi
	fi

	if ! cmake --version &>/dev/null; then
		echo "cmake is needed"
		MISSING="cmake $MISSING"
	fi

	if ! make --version &>/dev/null; then
		echo "make is needed"
		MISSING="make $MISSING"
	fi

	if ! rsync --version &>/dev/null; then
		# TODO: fix the bootstrap script to use also cp
		echo "sbt-instrumentation needs rsync when bootstrapping json. "
		MISSING="rsync $MISSING"
	fi

	if ! tar --version &>/dev/null; then
		echo "Need tar utility"
		MISSING="tar $MISSING"
	fi

	if ! xz --version &>/dev/null; then
		echo "Need xz utility"
		MISSING="xz $MISSING"
	fi


	if [ "$BUILD_STP" = "yes" ]; then
		if ! bison --version &>/dev/null; then
			echo "STP needs bison program"
			MISSING="bison $MISSING"
		fi

		if ! flex --version &>/dev/null; then
			echo "STP needs flex program"
			MISSING="flex $MISSING"
		fi
	fi

	if [ "$MISSING" != "" ]; then
		exitmsg "Missing dependencies: $MISSING"
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

	if [ "$BUILD_STP" = "no" -a "$HAVE_Z3" = "no" -a "$BUILD_Z3" = "no" ]; then
		exitmsg "Need z3 from package or enable building STP or Z3 by using 'build-stp' or 'build-z3' argument."
	fi

}

download_tar()
{
	$GET "$1" || exit 1
	BASENAME="`basename $1`"
	tar xf "$BASENAME" || exit 1
	rm -f "BASENAME"
}

download_zip()
{
	$GET "$1" || exit 1
	BASENAME="`basename $1`"
	unzip "$BASENAME" || exit 1
	rm -f "BASENAME"
}

# check if we have everything we need
check

build_llvm()
{
	if [ ! -d "llvm-${LLVM_VERSION}" ]; then
		$GET http://llvm.org/releases/${LLVM_VERSION}/llvm-${LLVM_VERSION}.src.tar.xz || exit 1
		$GET http://llvm.org/releases/${LLVM_VERSION}/cfe-${LLVM_VERSION}.src.tar.xz || exit 1
		$GET http://llvm.org/releases/${LLVM_VERSION}/compiler-rt-${LLVM_VERSION}.src.tar.xz || exit 1

		tar -xf llvm-${LLVM_VERSION}.src.tar.xz || exit 1
		tar -xf cfe-${LLVM_VERSION}.src.tar.xz || exit 1
		tar -xf compiler-rt-${LLVM_VERSION}.src.tar.xz || exit 1

                # rename llvm folder
                mv llvm-${LLVM_VERSION}.src llvm-${LLVM_VERSION}
		# move clang to llvm/tools and rename to clang
		mv cfe-${LLVM_VERSION}.src llvm-${LLVM_VERSION}/tools/clang
		mv compiler-rt-${LLVM_VERSION}.src llvm-${LLVM_VERSION}/tools/clang/runtime/compiler-rt

		# apply our patches for LLVM/Clang
		if [ "$LLVM_VERSION" = "4.0.1" ]; then
			pushd llvm-${LLVM_VERSION}/tools/clang
			patch -p0 --dry-run < $ABS_SRCDIR/patches/force_lifetime_markers.patch || exit 1
			patch -p0 < $ABS_SRCDIR/patches/force_lifetime_markers.patch || exit 1
			popd
		fi

		rm -f llvm-${LLVM_VERSION}.src.tar.xz &>/dev/null || exit 1
		rm -f cfe-${LLVM_VERSION}.src.tar.xz &>/dev/null || exit 1
		rm -f compiler-rt-${LLVM_VERSION}.src.tar.xz &>/dev/null || exit 1
	fi

	mkdir -p llvm-${LLVM_VERSION}/build
	pushd llvm-${LLVM_VERSION}/build

	# configure llvm
	if [ ! -d CMakeFiles ]; then
		EXTRA_FLAGS=
		if [ "x${BUILD_TYPE}" = "xDebug" ]; then
			EXTRA_FLAGS=-DLLVM_ENABLE_ASSERTIONS=ON
		fi
		cmake .. \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
			-DLLVM_INCLUDE_EXAMPLES=OFF \
			-DLLVM_INCLUDE_TESTS=OFF \
			-DLLVM_INCLUDE_DOCS=OFF \
			-DLLVM_BUILD_TESTS=OFF\
			-DLLVM_BUILD_TESTS=OFF\
			-DLLVM_ENABLE_TIMESTAMPS=OFF \
			-DLLVM_TARGETS_TO_BUILD="X86" \
			-DLLVM_ENABLE_PIC=ON \
			${EXTRA_FLAGS} \
			 || clean_and_exit
	fi

	# build llvm
	ONLY_TOOLS="$LLVM_TOOLS" build
	# copy the generated stddef.h due to compilation of instrumentation libraries
	mkdir -p "$LLVM_PREFIX/include"
	cp "lib/clang/${LLVM_VERSION}/include/stddef.h" "$LLVM_PREFIX/include" || exit 1

	popd
}

######################################################################
#   get LLVM either from user provided location or from the internet,
#   bulding it
######################################################################
if [ $FROM -eq 0 -a $NO_LLVM -ne 1 ]; then
	if [ -z "$WITH_LLVM" ]; then
		build_llvm
		LLVM_LOCATION=llvm-${LLVM_VERSION}/build
	else
		LLVM_LOCATION=$WITH_LLVM
	fi

	# we need these binaries in symbiotic, copy them
	# to instalation prefix there
	mkdir -p $LLVM_PREFIX/bin
	for B in $LLVM_TOOLS; do
		cp $LLVM_LOCATION/bin/${B} $LLVM_PREFIX/bin/${B} || exit 1
	done
fi


LLVM_MAJOR_VERSION="${LLVM_VERSION%%\.*}"
LLVM_MINOR_VERSION=${LLVM_VERSION#*\.}
LLVM_MINOR_VERSION="${LLVM_MINOR_VERSION%\.*}"
LLVM_CMAKE_CONFIG_DIR=share/llvm/cmake
if [ $LLVM_MAJOR_VERSION -gt 3 ]; then
	LLVM_CMAKE_CONFIG_DIR=lib/cmake/llvm
elif [ $LLVM_MAJOR_VERSION -ge 3 -a $LLVM_MINOR_VERSION -ge 9 ]; then
	LLVM_CMAKE_CONFIG_DIR=lib/cmake/llvm
fi

if [ -z "$WITH_LLVM" ]; then
	export LLVM_DIR=$ABS_RUNDIR/llvm-${LLVM_VERSION}/build/$LLVM_CMAKE_CONFIG_DIR
	export LLVM_BUILD_PATH=$ABS_RUNDIR/llvm-${LLVM_VERSION}/build/
else
	export LLVM_DIR=$WITH_LLVM/$LLVM_CMAKE_CONFIG_DIR
	export LLVM_BUILD_PATH=$WITH_LLVM
fi

if [ -z "$WITH_LLVM_SRC" ]; then
	export LLVM_SRC_PATH="$ABS_RUNDIR/llvm-${LLVM_VERSION}/"
else
	export LLVM_SRC_PATH="$WITH_LLVM_SRC"
fi

# do not do any funky nested ifs in the code above and just override
# the default LLVM_DIR in the case we are given that variable
if [ ! -z "$WITH_LLVM_DIR" ]; then
	LLVM_DIR=$WITH_LLVM_DIR
fi

# check
if [ ! -f $LLVM_DIR/LLVMConfig.cmake ]; then
	exitmsg "Cannot find LLVMConfig.cmake file in the directory $LLVM_DIR"
fi

######################################################################
#   dg
######################################################################
if [ $FROM -le 1 ]; then
	if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/dg)" ]; then
		git_submodule_init
	fi

	# download the dg library
	pushd "$SRCDIR/dg" || exitmsg "Cloning failed"
	mkdir -p build-${LLVM_VERSION} || exit 1
	pushd build-${LLVM_VERSION} || exit 1

	if [ ! -d CMakeFiles ]; then
		cmake .. \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
			-DCMAKE_INSTALL_LIBDIR:PATH=lib \
			-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
			-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
			-DLLVM_DIR=$LLVM_DIR \
			-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
			|| clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1
	popd
	popd

	# initialize instrumentation module if not done yet
	if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/sbt-slicer)" ]; then
		git_submodule_init
	fi

	pushd "$SRCDIR/sbt-slicer" || exitmsg "Cloning failed"
	mkdir -p build-${LLVM_VERSION} || exit 1
	pushd build-${LLVM_VERSION} || exit 1
	if [ ! -d CMakeFiles ]; then
		cmake .. \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
			-DCMAKE_INSTALL_LIBDIR:PATH=lib \
			-DCMAKE_INSTALL_FULL_DATADIR:PATH=$LLVM_PREFIX/share \
			-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
			-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
			-DLLVM_DIR=$LLVM_DIR \
			-DDG_PATH=$ABS_SRCDIR/dg \
			-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
			|| clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1
	popd
	popd
fi

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi

######################################################################
#   zlib
######################################################################
if [ $FROM -le 2 -a $WITH_ZLIB = "yes" ]; then
	git_clone_or_pull https://github.com/madler/zlib
	cd zlib || exit 1

	if [ ! -d CMakeFiles ]; then
		cmake -DCMAKE_INSTALL_PREFIX=$PREFIX
	fi

	(make "$OPTS" && make install) || exit 1

	cd -
fi

if [ "$BUILD_STP" = "yes" ]; then
	######################################################################
	#   minisat
	######################################################################
	if [ $FROM -le 4  -a "$BUILD_KLEE" = "yes" ]; then
		git_clone_or_pull git://github.com/stp/minisat.git minisat
		pushd minisat
		mkdir -p build
		cd build || exit 1

		# use our zlib, if we compiled it
		ZLIB_FLAGS=
		if [ -d $ABS_RUNDIR/zlib ]; then
			ZLIB_FLAGS="-DZLIB_LIBRARY=-L${PREFIX}/lib;-lz"
			ZLIB_FLAGS="$ZLIB_FLAGS -DZLIB_INCLUDE_DIR=$PREFIX/include"
		fi

		if [ ! -d CMakeFiles ]; then
			cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX \
				  -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
					 -DSTATICCOMPILE=ON $ZLIB_FLAGS
		fi

		(make "$OPTS" && make install) || exit 1
		popd
	fi

	######################################################################
	#   STP
	######################################################################
	if [ $FROM -le 4  -a "$BUILD_KLEE" = "yes" ]; then
		git_clone_or_pull git://github.com/stp/stp.git stp
		cd stp || exitmsg "Cloning failed"
		if [ ! -d CMakeFiles ]; then
			cmake . -DCMAKE_INSTALL_PREFIX=$PREFIX \
				-DCMAKE_INSTALL_LIBDIR:PATH=lib \
				-DSTP_TIMESTAMPS:BOOL="OFF" \
				-DCMAKE_CXX_FLAGS_RELEASE=-O2 \
				-DCMAKE_C_FLAGS_RELEASE=-O2 \
				-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
				-DBUILD_SHARED_LIBS:BOOL=OFF \
				-DENABLE_PYTHON_INTERFACE:BOOL=OFF || clean_and_exit 1 "git"
		fi

		(build "OPTIMIZE=-O2 CFLAGS_M32=install" && make install) || exit 1
		cd -
	fi
fi # BUILD_STP

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi

######################################################################
#   googletest
######################################################################
if [ $FROM -le 4  -a "$BUILD_KLEE" = "yes" ]; then
	if [ ! -d googletest ]; then
		download_zip https://github.com/google/googletest/archive/release-1.7.0.zip || exit 1
		mv googletest-release-1.7.0 googletest || exit 1
		rm -f release-1.7.0.zip
	fi

	pushd googletest
	mkdir -p build
	pushd build
	if [ ! -d CMakeFiles ]; then
		cmake ..
	fi

	build || clean_and_exit 1
	# copy the libraries to LLVM build, there is a "bug" in llvm-config
	# that requires them
	cp *.a ${ABS_SRCDIR}/llvm-${LLVM_VERSION}/build/lib

	popd; popd
fi

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi

if [ "$BUILD_Z3" = "yes" -o "$HAVE_Z3" = "yes" ]; then
	######################################################################
	#   Z3
	######################################################################
	if [ $FROM -le 4 -a "$BUILD_KLEE" = "yes" ]; then
		git_clone_or_pull git://github.com/Z3Prover/z3 -b "z3-4.8.4" z3
		mkdir -p "z3/build" && pushd "z3/build"
		if [ ! -d CMakeFiles ]; then
			cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX \
				 -DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
				 || clean_and_exit 1 "git"
		fi

		make && make install
		popd
	fi
fi # BUILD_Z3

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi


######################################################################
#   KLEE
######################################################################
if [ $FROM -le 4  -a "$BUILD_KLEE" = "yes" ]; then
	if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/klee)" ]; then
		git_submodule_init
	fi

	mkdir -p klee/build-${LLVM_VERSION}
	pushd klee/build-${LLVM_VERSION}

	if [ "x$BUILD_TYPE" = "xRelease" ]; then
		KLEE_BUILD_TYPE="Release+Asserts"
	else
		KLEE_BUILD_TYPE="$BUILD_TYPE"
	fi

	# Our version of KLEE does not work with STP now
	# STP_FLAGS=
	# if [ "$BUILD_STP" = "yes" -o -d $ABS_SRCDIR/stp ]; then
	# 	STP_FLAGS="-DENABLE_SOLVER_STP=ON -DSTP_DIR=${ABS_SRCDIR}/stp"
	# fi
	STP_FLAGS="-DENABLE_SOLVER_STP=OFF"

	Z3_FLAGS=
	if [ "$HAVE_Z3" = "yes" -o "$BUILD_Z3" = "yes" ]; then
		Z3_FLAGS=-DENABLE_SOLVER_Z3=ON
		if [ -d ${ABS_SRCDIR}/z3 ]; then
			Z3_FLAGS="$Z3_FLAGS -DCMAKE_LIBRARY_PATH=${ABS_SRCDIR}/z3/build/"
			Z3_FLAGS="$Z3_FLAGS -DCMAKE_INCLUDE_PATH=${ABS_SRCDIR}/z3/src/api"
		fi
	else
		exitmsg "KLEE needs Z3 library"
	fi

	if [ ! -d CMakeFiles ]; then
		# use our zlib, if we compiled it
		ZLIB_FLAGS=
		if [ -d $ABS_RUNDIR/zlib ]; then
			ZLIB_FLAGS="-DZLIB_LIBRARY=-L${PREFIX}/lib;-lz"
			ZLIB_FLAGS="$ZLIB_FLAGS -DZLIB_INCLUDE_DIR=$PREFIX/include"
		fi

		cmake .. -DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
			-DKLEE_RUNTIME_BUILD_TYPE=${KLEE_BUILD_TYPE} \
			-DLLVM_CONFIG_BINARY=${ABS_SRCDIR}/llvm-${LLVM_VERSION}/build/bin/llvm-config \
			-DGTEST_SRC_DIR=$ABS_SRCDIR/googletest \
			-DENABLE_UNIT_TESTS=ON \
			-DENABLE_TCMALLOC=OFF \
			$ZLIB_FLAGS $Z3_FLAGS $STP_FLAGS \
			|| clean_and_exit 1 "git"
	fi

	if [ "$UPDATE" = "1" ]; then
		git fetch --all
		git checkout $KLEE_BRANCH
		git pull
	fi

	# clean runtime libs, it may be 32-bit from last build
	make -C runtime -f Makefile.cmake.bitcode clean 2>/dev/null

	# build 64-bit libs and install them to prefix
	(build && make install) || exit 1

	mv $LLVM_PREFIX/lib64/klee $LLVM_PREFIX/lib/klee || true
	rmdir $LLVM_PREFIX/lib64 || true

	# clean 64-bit build and build 32-bit version of runtime library
	make -C runtime -f Makefile.cmake.bitcode clean \
		|| exitmsg "Failed building klee 32-bit runtime library"

	# EXTRA_LLVMCC.Flags is obsolete and to be removed soon
	make -C runtime -f Makefile.cmake.bitcode \
		LLVMCC.ExtraFlags=-m32 \
		EXTRA_LLVMCC.Flags=-m32 \
		|| exitmsg "Failed building 32-bit klee runtime library"

	# copy 32-bit library version to prefix
	mkdir -p $LLVM_PREFIX/lib32/klee/runtime
	cp ${KLEE_BUILD_TYPE}/lib/*.bc* \
		$LLVM_PREFIX/lib32/klee/runtime/ \
		|| exitmsg "Did not build 32-bit klee runtime lib"

	popd
fi

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi

######################################################################
#   nidhugg
######################################################################
if [ $FROM -le 4  -a "$BUILD_NIDHUGG" = "yes" ]; then
	if [ ! -d nidhugg ]; then
		git_clone_or_pull "https://github.com/nidhugg/nidhugg"

	fi

	mkdir -p nidhugg/build-${LLVM_VERSION}
	pushd nidhugg/build-${LLVM_VERSION}

	if [ "x$BUILD_TYPE" = "xRelease" ]; then
		NIDHUGG_OPTIONS=""
	else
		NIDHUGG_OPTIONS="--enable-asserts"
	fi

	if [ ! -f "config.h" ]; then

		OLD_PATH="$PATH"
		PATH="$ABS_SRCDIR/llvm-${LLVM_VERSION}/build/bin":$PATH

		autoreconf --install ..
		../configure --prefix="$LLVM_PREFIX" \
			     $NIDHUGG_OPTIONS \
		  || clean_and_exit 1 "git"

		  PATH="$OLD_PATH"
	fi

	(build && make install) || exit 1
	popd
fi

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi

######################################################################
#   instrumentation
######################################################################
if [ $FROM -le 6 ]; then
	# initialize instrumentation module if not done yet
	if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/sbt-instrumentation)" ]; then
		git_submodule_init
	fi

	pushd "$SRCDIR/sbt-instrumentation" || exitmsg "Cloning failed"

	# bootstrap JSON library if needed
	if [ ! -d jsoncpp ]; then
		./bootstrap-json.sh || exitmsg "Failed generating json files"
	fi

	# build RA library
	if [ ! -d "ra/build-${LLVM_VERSION}" ]; then
		if [ ! -d "ra" ]; then
			git_clone_or_pull "https://github.com/xvitovs1/ra" ra
		fi

		mkdir -p ra/build-${LLVM_VERSION}
		pushd ra/build-${LLVM_VERSION}
		cmake .. \
			-DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
			-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
			-DCMAKE_INSTALL_LIBDIR:PATH=lib \
		|| clean_and_exit 1 "git"
		make && make install
		popd;
	fi

	mkdir -p build-${LLVM_VERSION}
	pushd build-${LLVM_VERSION}
	if [ ! -d CMakeFiles ]; then
		cmake .. \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
			-DCMAKE_INSTALL_LIBDIR:PATH=lib \
			-DCMAKE_INSTALL_FULL_DATADIR:PATH=$LLVM_PREFIX/share \
			-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
			-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
			-DLLVM_DIR=$LLVM_DIR \
			-DDG_PATH=$ABS_SRCDIR/dg \
			-DRA_BUILD_PATH=`pwd`/../ra/build-${LLVM_VERSION} \
			-DRA_SRC_PATH=`pwd`/../ra \
			-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
			|| clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1

	popd
	popd
fi

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi

######################################################################
#   transforms (LLVMsbt.so)
######################################################################
if [ $FROM -le 6 ]; then

	mkdir -p transforms/build-${LLVM_VERSION}
	pushd transforms/build-${LLVM_VERSION}

	# build prepare and install lib and scripts
	if [ ! -d CMakeFiles ]; then
		cmake .. \
			-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
			-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
			-DLLVM_DIR=$LLVM_DIR \
			-DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
			-DCMAKE_INSTALL_PREFIX=$PREFIX \
			-DCMAKE_INSTALL_LIBDIR:PATH=$LLVM_PREFIX/lib \
			|| clean_and_exit 1
	fi

	(build && make install) || clean_and_exit 1
	popd

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi
fi

######################################################################
#   copy lib and include files
######################################################################
if [ $FROM -le 6 ]; then
	if [ ! -d CMakeFiles ]; then
		cmake . \
			-DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
			-DCMAKE_INSTALL_PREFIX=$PREFIX \
			-DCMAKE_INSTALL_LIBDIR:PATH=$LLVM_PREFIX/lib \
			|| exit 1
	fi

	(build && make install) || exit 1

	# precompile bitcode files
	scripts/precompile_bitcode_files.sh

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi
fi

######################################################################
#  extract versions of components
######################################################################
if [ $FROM -le 7 ]; then

	SYMBIOTIC_VERSION=`git rev-parse HEAD`
	cd dg || exit 1
	DG_VERSION=`git rev-parse HEAD`
	cd -
	cd sbt-slicer || exit 1
	SBT_SLICER_VERSION=`git rev-parse HEAD`
	cd -
	cd sbt-instrumentation || exit 1
	INSTRUMENTATION_VERSION=`git rev-parse HEAD`
	cd -
if [ "$BUILD_STP" = "yes" ]; then
	cd minisat || exit 1
	MINISAT_VERSION=`git rev-parse HEAD`
	cd -
	cd stp || exit 1
	STP_VERSION=`git rev-parse HEAD`
	cd -
fi

if [ "$BUILD_Z3" = "yes" ]; then
	cd z3 || exit 1
	Z3_VERSION=`git rev-parse HEAD`
	cd -
fi
	cd klee || exit 1
	KLEE_VERSION=`git rev-parse HEAD`
	cd -

	VERSFILE="$SRCDIR/lib/symbioticpy/symbiotic/versions.py"
	echo "#!/usr/bin/python" > $VERSFILE
	echo "# This file is automatically generated by symbiotic-build.sh" >> $VERSFILE
	echo "" >> $VERSFILE
	echo "versions = {" >> $VERSFILE
	echo -e "\t'symbiotic' : '$SYMBIOTIC_VERSION'," >> $VERSFILE
	echo -e "\t'dg' : '$DG_VERSION'," >> $VERSFILE
	echo -e "\t'sbt-slicer' : '$SBT_SLICER_VERSION'," >> $VERSFILE
	echo -e "\t'sbt-instrumentation' : '$INSTRUMENTATION_VERSION'," >> $VERSFILE
if [ "$BUILD_STP" = "yes" ]; then
	echo -e "\t'minisat' : '$MINISAT_VERSION'," >> $VERSFILE
	echo -e "\t'stp' : '$STP_VERSION'," >> $VERSFILE
fi
if [ "$BUILD_Z3" = "yes" ]; then
	echo -e "\t'z3' : '$Z3_VERSION'," >> $VERSFILE
fi
	echo -e "\t'klee' : '$KLEE_VERSION'," >> $VERSFILE
	echo -e "}\n\n" >> $VERSFILE
	echo "llvm_version = '${LLVM_VERSION}'" >> $VERSFILE

get_external_library()
{
	LIB="$(ldd $1 | grep $2 | cut -d ' ' -f 3)"
	# if this is not library in our installation, return it
	if [ "$LIB" != "not" ]; then # not found
		if echo "$LIB" | grep -v -q "$PREFIX"; then
			echo "$LIB"
		fi
	else
		exitmsg "Did not find library matching $2"
	fi
}

get_any_library()
{
	LIB="$(ldd $1 | grep $2 | cut -d ' ' -f 3)"
	# if this is not library in our installation, return it
	if [ "$LIB" != "not" ]; then # not found
		echo "$LIB"
	else
		exitmsg "Did not find library matching $2"
	fi
}

get_klee_dependencies()
{
	KLEE_BIN="$1"
	LIBS=$(get_external_library $KLEE_BIN libstdc++)
	LIBS="$LIBS $(get_external_library $KLEE_BIN tinfo)"
	LIBS="$LIBS $(get_external_library $KLEE_BIN libgomp)"
	# FIXME: remove once we build/download our z3
	LIBS="$LIBS $(get_any_library $KLEE_BIN libz3)"
	LIBS="$LIBS $(get_any_library $KLEE_BIN libstp)"

	echo $LIBS
}

######################################################################
#  create distribution
######################################################################
	# copy license
	cp LICENSE.txt $PREFIX/

	# copy the symbiotic python module
	cp -r $SRCDIR/lib/symbioticpy $PREFIX/lib || exit 1

	# copy dependencies
	DEPENDENCIES=""
	if [ "$FULL_ARCHIVE" = "yes" ]; then
		DEPS=`get_klee_dependencies $LLVM_PREFIX/bin/klee`
		if [ ! -z "$DEPS" ]; then
			for D in $DEPS; do
				DEST="$PREFIX/lib/$(basename $D)"
				cmp "$D" "$DEST" || cp -u "$D" "$DEST"
				DEPENDENCIES="$DEST $DEPENDENCIES"
			done
		fi
	fi

	cd $PREFIX || exitmsg "Whoot? prefix directory not found! This is a BUG, sir..."

	BINARIES="$LLVM_PREFIX/bin/sbt-slicer \
		  $LLVM_PREFIX/bin/llvm-slicer \
		  $LLVM_PREFIX/bin/sbt-instr"
	for B in $LLVM_TOOLS; do
		BINARIES="$LLVM_PREFIX/bin/${B} $BINARIES"
	done

if [ ${BUILD_KLEE} = "yes" ];  then
	BINARIES="$BINARIES $LLVM_PREFIX/bin/klee"
fi

	LIBRARIES="\
		$LLVM_PREFIX/lib/libLLVMdg.so $LLVM_PREFIX/lib/libLLVMpta.so \
		$LLVM_PREFIX/lib/libLLVMrd.so $LLVM_PREFIX/lib/libDGAnalysis.so \
		$LLVM_PREFIX/lib/libPTA.so $LLVM_PREFIX/lib/libRD.so \
		$LLVM_PREFIX/lib/LLVMsbt.so \
		$LLVM_PREFIX/lib/libPointsToPlugin.so \
		$LLVM_PREFIX/lib/libRangeAnalysisPlugin.so \
		$LLVM_PREFIX/lib/libCheckNSWPlugin.so \
		$LLVM_PREFIX/lib/libInfiniteLoopsPlugin.so \
		$LLVM_PREFIX/lib/libValueRelationsPlugin.so \
		$LLVM_PREFIX/lib/libRA.so"

if [ ${BUILD_KLEE} = "yes" ];  then
	LIBRARIES="${LIBRARIES} \
		$LLVM_PREFIX/lib/klee/runtime/*.bc* \
		$LLVM_PREFIX/lib32/klee/runtime/*.bc* \
		$LLVM_PREFIX/lib/*.bc* \
		$LLVM_PREFIX/lib32/*.bc*"
fi
if [ ${BUILD_NIDHUGG} = "yes" ];  then
	LIBRARIES="$LLVM_PREFIX/bin/nidhugg"
fi

	INSTR="$LLVM_PREFIX/share/sbt-instrumentation/"

if [ "$BUILD_STP" = "yes" ]; then
		LIBRARIES="$LIBRARIES $PREFIX/lib/libminisat*.so"
fi

if [ "$BUILD_Z3" = "yes" ]; then
		LIBRARIES="$LIBRARIES $PREFIX/lib/libz3*.so"
fi

	#strip binaries, it will save us 500 MB!
	strip $BINARIES

	git init
	git add \
		$BINARIES \
		$LIBRARIES \
		$DEPENDENCIES \
		$INSTR\
		bin/symbiotic \
		include/symbiotic.h \
		include/symbiotic-size_t.h \
		$LLVM_PREFIX/include/stddef.h \
		lib/*.c \
		properties/* \
		lib/symbioticpy/symbiotic/*.py \
		lib/symbioticpy/symbiotic/benchexec/*.py \
		lib/symbioticpy/symbiotic/benchexec/tools/*.py \
		lib/symbioticpy/symbiotic/tools/*.py \
		lib/symbioticpy/symbiotic/utils/*.py \
		lib/symbioticpy/symbiotic/witnesses/*.py \
		LICENSE.txt

	git commit -m "Create Symbiotic distribution `date`" || true

	# remove unnecessary files
	# git clean -xdf
fi

if [ "x$ARCHIVE" = "xyes" ]; then
	git archive --prefix "symbiotic/" -o symbiotic.zip -9 --format zip HEAD
	mv symbiotic.zip ..
fi
