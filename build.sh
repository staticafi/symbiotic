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

set -e

source "$(dirname $0)/scripts/build-utils.sh"

RUNDIR=`pwd`
SRCDIR=`dirname $0`
ABS_RUNDIR=`abspath $RUNDIR`
ABS_SRCDIR=`abspath $SRCDIR`

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

LLVM_VERSION_DEFAULT=8.0.1
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

export PREFIX=${PREFIX:-`pwd`/install}

# export LD_LIBRARY_PATH="$PREFIX/lib:$LD_LIBRARY_PATH"
# export C_INCLUDE_PATH="$PREFIX/include:$C_INCLUDE_PATH"
# export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/share/pkgconfig:$PKG_CONFIG_PATH"

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
WITH_LLVMCBE='no'
BUILD_STP='no'
BUILD_Z3='no'
BUILD_SVF='no'
BUILD_PREDATOR='no'
BUILD_LLVM2C='yes'

BUILD_KLEE="yes"
BUILD_NIDHUGG="no"


HAVE_32_BIT_LIBS=$(if check_32_bit; then echo "yes"; else echo "no"; fi)
HAVE_Z3=$(if check_z3; then echo "yes"; else echo "no"; fi)
HAVE_GTEST=$(if check_gtest; then echo "yes"; else echo "no"; fi)
WITH_ZLIB=$(if check_zlib; then echo "no"; else echo "yes"; fi)
ENABLE_TCMALLOC=$(if check_tcmalloc; then echo "on"; else echo "off"; fi)

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
		'no-llvm2c')
			BUILD_LLVM2C="no"
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
		build-predator)
			BUILD_PREDATOR="yes"
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
		;;
		build-type=*)
			BUILD_TYPE=${1##*=}
		;;
		with-llvm-cbe)
			WITH_LLVMCBE="yes"
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

export LLVM_PREFIX="$PREFIX/llvm-$LLVM_VERSION"

if [ "$HAVE_32_BIT_LIBS" = "no" -a "$BUILD_KLEE" = "yes" ]; then
	exitmsg "KLEE needs 32-bit headers to build 32-bit versions of runtime libraries"
fi

if [ "$HAVE_Z3" = "no" -a "$BUILD_STP" = "no" ]; then
	if [ ! -d "z3" ]; then
		BUILD_Z3="yes"
		echo "Will build z3 as it is missing in the system"
	else
		BUILD_Z3="yes"
		echo "Found z3 directory, using that build"
	fi
fi

if [ "$WITH_LLVMCBE" = "yes" ]; then
	if echo ${LLVM_VERSION} | grep -v -q '^[67]'; then
		exitmsg "llvm-cbe needs LLVM 6 or 7"
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

check()
{
	MISSING=""
	if ! curl --version &>/dev/null; then
		echo "Need curl to download files"
		MISSING="curl"
	fi

	if ! which true ; then
		echo "Need 'which' command."
		MISSING="which"
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

# check if we have everything we need
check

build_llvm()
{
	URL=http://llvm.org/releases/${LLVM_VERSION}/
	CLANG_NAME="cfe"
	# UFFF, for some stupid reason this only release has a different url, the rest (even newer use the previous one)
	if [ ${LLVM_VERSION} = "8.0.1" ]; then
		URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-8.0.1/
	elif [ ${LLVM_VERSION} = "10.0.0" ]; then
		URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-10.0.0/
	        CLANG_NAME="clang"
	fi

	LLVM_URL=${URL}/llvm-${LLVM_VERSION}.src.tar.xz
	CLANG_URL=${URL}/$CLANG_NAME-${LLVM_VERSION}.src.tar.xz
	RT_URL=${URL}/compiler-rt-${LLVM_VERSION}.src.tar.xz

	if [ ! -d "llvm-${LLVM_VERSION}" ]; then
		$GET $LLVM_URL || exit 1
		$GET $CLANG_URL || exit 1
		$GET $RT_URL || exit 1

		tar -xf llvm-${LLVM_VERSION}.src.tar.xz || exit 1
		tar -xf $CLANG_NAME-${LLVM_VERSION}.src.tar.xz || exit 1
		tar -xf compiler-rt-${LLVM_VERSION}.src.tar.xz || exit 1

                # rename llvm folder
                mv llvm-${LLVM_VERSION}.src llvm-${LLVM_VERSION}
		# move clang to llvm/tools and rename to clang
		mv $CLANG_NAME-${LLVM_VERSION}.src llvm-${LLVM_VERSION}/tools/clang
		mv compiler-rt-${LLVM_VERSION}.src llvm-${LLVM_VERSION}/tools/clang/runtime/compiler-rt

		# apply our patches for LLVM/Clang
		if [ "$LLVM_VERSION" = "4.0.1" ]; then
			pushd llvm-${LLVM_VERSION}/tools/clang
			patch -p0 --dry-run < $ABS_SRCDIR/patches/force_lifetime_markers.patch || exit 1
			patch -p0 < $ABS_SRCDIR/patches/force_lifetime_markers.patch || exit 1
			popd
		fi

		rm -f llvm-${LLVM_VERSION}.src.tar.xz &>/dev/null || exit 1
		rm -f $CLANG_NAME-${LLVM_VERSION}.src.tar.xz &>/dev/null || exit 1
		rm -f compiler-rt-${LLVM_VERSION}.src.tar.xz &>/dev/null || exit 1
	fi
	if [ $WITH_LLVMCBE = "yes" ]; then
		pushd ${ABS_SRCDIR}/llvm-${LLVM_VERSION}/projects || exitmsg "Invalid directory"
		git_clone_or_pull https://github.com/JuliaComputing/llvm-cbe
		popd
	fi

	mkdir -p llvm-${LLVM_VERSION}/build
	pushd llvm-${LLVM_VERSION}/build

	# configure llvm
	if [ ! -d CMakeFiles ]; then
		EXTRA_FLAGS=
		if [ "x${BUILD_TYPE}" = "xDebug" ]; then
			EXTRA_FLAGS=-DLLVM_ENABLE_ASSERTIONS=ON
		fi

		if [ $LLVM_MAJOR_VERSION -ge 9 ]; then
			EXTRA_FLAGS="$EXTRA_FLAGS -DLLVM_INCLUDE_TESTS=ON"
		else
			EXTRA_FLAGS="$EXTRA_FLAGS -DLLVM_INCLUDE_TESTS=OFF"
		fi
		cmake .. \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
			-DLLVM_INCLUDE_EXAMPLES=OFF \
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
	#mkdir -p "$LLVM_PREFIX/include"
	#cp "lib/clang/${LLVM_VERSION}/include/stddef.h" "$LLVM_PREFIX/include" || exit 1

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

LLVM_CONFIG=${ABS_SRCDIR}/llvm-${LLVM_VERSION}/build/bin/llvm-config

if [ "$LLVM_MAJOR_VERSION" -lt 6 ]; then
        echo "LLVM version too low for llvm2c, I'm not building it"
        BUILD_LLVM2C="no"
fi


######################################################################
#   SVF
######################################################################
if [ $FROM -le 1 -a $BUILD_SVF = "yes" ]; then
	git_clone_or_pull https://github.com/SVF-tools/SVF

	# download the dg library
	pushd "$SRCDIR/SVF" || exitmsg "Cloning failed"
	mkdir -p build-${LLVM_VERSION} || exit 1
	pushd build-${LLVM_VERSION} || exit 1

	if [ ! -d CMakeFiles ]; then

		export LLVM_SRC="$LLVM_SRC_PATH"
		export LLVM_OBJ="$LLVM_BUILD_PATH"
		export LLVM_DIR="$LLVM_BUILDPATH"
		cmake .. \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
			-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
			|| clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1
	popd
	popd
fi # SVF

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi

######################################################################
#   dg
######################################################################
if [ $FROM -le 1 ]; then
	if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/dg)" ]; then
		git_submodule_init
	fi

	if [ -d $SRCDIR/SVF ]; then
		SVF_FLAGS="-DSVF_DIR=$ABS_SRCDIR/SVF/build-${LLVM_VERSION}"
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
			-DCMAKE_INSTALL_RPATH="\$ORIGIN/../lib" \
			${SVF_FLAGS} \
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
			-DCMAKE_INSTALL_RPATH="\$ORIGIN/../lib" \
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

if [ "$BUILD_Z3" = "yes" ]; then
	######################################################################
	#   Z3
	######################################################################
	if [ $FROM -le 4 -a "$BUILD_KLEE" = "yes" ]; then
		if [ ! -d "z3" ]; then
			git_clone_or_pull git://github.com/Z3Prover/z3 -b "z3-4.8.4" z3
		fi

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
	source scripts/build-klee.sh
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

	pushd nidhugg
	# get the immer submodule
	git submodule init
	git submodule update
	popd

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
		../configure --prefix="$LLVM_PREFIX" CXXFLAGS="-I$(pwd)/../deps/immer" \
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
#   llvm2c
######################################################################
if [ $FROM -le 6 -a "$BUILD_LLVM2C" = "yes" ]; then
	source scripts/build-llvm2c.sh
fi

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi


if [  -d predator-${LLVM_VERSION} ]; then
	# we already got a build of predator, so rebuild it
	BUILD_PREDATOR="yes"
fi
######################################################################
#   Predator
######################################################################
if [ $FROM -le 6 -a "$BUILD_PREDATOR" = "yes" ]; then
	if [ ! -d predator-${LLVM_VERSION} ]; then
               git_clone_or_pull "https://github.com/staticafi/predator" -b svcomp2019 predator-${LLVM_VERSION}
	fi

	pushd predator-${LLVM_VERSION}

	if [ ! -d CMakeFiles ]; then
	        CXX=clang++ ./switch-host-llvm.sh ${ABS_SRCDIR}/llvm-${LLVM_VERSION}/build/${LLVM_CMAKE_CONFIG_DIR}
	fi

       	build || exit 1
	mkdir -p $LLVM_PREFIX/predator/lib
	cp sl_build/*.so $LLVM_PREFIX/predator/lib
	cp sl_build/slllvm* $LLVM_PREFIX/bin/
	cp sl_build/*.sh $LLVM_PREFIX/predator/
	cp build-aux/cclib.sh $LLVM_PREFIX/predator/
	cp passes-src/passes_build/*.so $LLVM_PREFIX/predator/lib

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

#if [ "$ARCHIVE" = "yes" ]; then
	# precompile bitcode files
	CPPFLAGS="-I/usr/include $CPPFLAGS" scripts/precompile_bitcode_files.sh
#fi

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi
fi

######################################################################
#  extract versions of components and create the distribution
######################################################################
if [ $FROM -le 7 ]; then
	source scripts/gen-version.sh
	source scripts/push-to-git.sh
fi
