#!/bin/bash
#
# Build Symbiotic from scratch and setup environment for
# development if needed. Try using only system libraries.
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
	echo "$0 [archive | full-archive] [update] [slicer | scripts | klee | witness | bin] OPTS"
	echo "" # new line
	echo -e "build-type=TYPE    - set Release/Debug build"
	echo -e "llvm-config        - use the given llvm-config binary"
	echo -e "archive            - create a zip file with symbiotic"
	echo -e "full-archive       - create a zip file with symbiotic and add non-standard dependencies"
	echo -e "update             - update repositories"
	echo "" # new line
	echo -e "slicer, scripts,"
	echo -e "klee, witness"
	echo -e "bin     - run compilation _from_ this point"
	echo "" # new line
	echo -e "OPTS = options for make (i. e. -j8)"
}

export PREFIX=`pwd`/install
export LD_LIBRARY_PATH="$PREFIX/lib:$LD_LIBRARY_PATH"
export C_INCLUDE_PATH="$PREFIX/include:$C_INCLUDE_PATH"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/share/pkgconfig:$PKG_CONFIG_PATH"

FROM='0'
UPDATE=
OPTS=

ARCHIVE="no"
FULL_ARCHIVE="no"
BUILD_KLEE="yes"
LLVM_CONFIG=

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
		'no-klee')
			BUILD_KLEE=no
		;;
		'update')
			UPDATE=1
		;;

		llvm-config=*)
			LLVM_CONFIG=${1##*=}
		;;
		archive)
			ARCHIVE="yes"
		;;
		full-archive)
			ARCHIVE="yes"
			FULL_ARCHIVE="yes"
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

HAVE_32_BIT_LIBS=$(if check_32_bit; then echo "yes"; else echo "no"; fi)
HAVE_Z3=$(if check_z3; then echo "yes"; else echo "no"; fi)
HAVE_GTEST=$(if check_gtest; then echo "yes"; else echo "no"; fi)
ENABLE_TCMALLOC=$(if check_tcmalloc; then echo "on"; else echo "off"; fi)

if [ "$HAVE_32_BIT_LIBS" = "no" -a "$BUILD_KLEE" = "yes" ]; then
	exitmsg "KLEE needs 32-bit headers to build 32-bit versions of runtime libraries"
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

	if [ "$MISSING" != "" ]; then
		exitmsg "Missing dependencies: $MISSING"
	fi
}


# check if we have everything we need
check

######################################################################
#   LLVM
#     Copy the LLVM libraries
######################################################################

test -z "$LLVM_CONFIG" && LLVM_CONFIG=$(which llvm-config || true)

if [ ! -z $LLVM_CONFIG -a -x $LLVM_CONFIG ]; then
	echo "Using llvm-config: $LLVM_CONFIG";
else
	exitmsg "Cannot find llvm-config binary. Try using llvm-config= switch"
fi

# LLVM tools that we need
LLVM_VERSION=$($LLVM_CONFIG --version)
LLVM_TOOLS="opt clang llvm-link llvm-dis llvm-nm"
export LLVM_PREFIX="$PREFIX/llvm-$LLVM_VERSION"

mkdir -p $LLVM_PREFIX/bin
for T in $LLVM_TOOLS; do
	TOOL=$(which $T || true)
	if [ -z "${TOOL}" -o ! -x "${TOOL}" ]; then
		exitmsg "Cannot find working $T binary".
	fi

	cp ${TOOL} $LLVM_PREFIX/bin
done

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
			-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
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
	if [ "$HAVE_Z3" = "yes" ]; then
		Z3_FLAGS=-DENABLE_SOLVER_Z3=ON
	else
		exitmsg "KLEE needs Z3 library"
	fi

	if which lit &>/dev/null; then
		HAVE_LIT=on
	else
		HAVE_LIT=off
	fi

	if [ "$HAVE_LIT"="yes" -a "$HAVE_GTEST" = "yes" ]; then
		ENABLE_TESTS="on"
	else
		ENABLE_TESTS="off"
	fi

	if [ ! -d CMakeFiles ]; then

		cmake .. -DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
			-DKLEE_RUNTIME_BUILD_TYPE=${KLEE_BUILD_TYPE} \
			-DLLVM_CONFIG_BINARY=$(abspath ${LLVM_CONFIG}) \
			-DENABLE_UNIT_TESTS=${ENABLE_TESTS} \
			-DENABLE_SYSTEM_TESTS=${ENABLE_TESTS} \
			-DENABLE_TCMALLOC=${ENABLE_TCMALLOC} \
			$Z3_FLAGS $STP_FLAGS \
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
	echo -e "\t'klee' : '$KLEE_VERSION'," >> $VERSFILE
	echo -e "}\n\n" >> $VERSFILE
	echo "llvm_version = '${LLVM_VERSION}'" >> $VERSFILE

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

	INSTR="$LLVM_PREFIX/share/sbt-instrumentation/"

	#strip binaries, it will save us 500 MB!
	strip $BINARIES

	git init
	git add \
		$BINARIES \
		$LIBRARIES \
		$DEPENDENCIES \
		$INSTR\
		bin/symbiotic \
		bin/gen-c \
		include/symbiotic.h \
		include/symbiotic-size_t.h \
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
