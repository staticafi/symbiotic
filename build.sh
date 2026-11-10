#!/bin/bash
#
# Build Symbiotic from scratch and setup environment for
# development if needed. This build script is meant to be more
# of a guide how to build Symbiotic, it may not work in all cases.
#
#  (c) Marek Chalupa, 2016 - 2021
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

PHASE="doing initialization"

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
	echo -e "only=C1,C2,...     - build only the given components (default: all enabled ones)."
	echo -e "                     Components (in build order): llvm, svf, dg, sbt-slicer, zlib, stp,"
	echo -e "                     googletest, z3, klee, witch-klee, nidhugg, llvm2c, reverser,"
	echo -e "                     predator, sbt-instrumentation, transforms, files, dist."
	echo -e "                     The components that a component depends on must be already built."
	echo "" # new line
	echo -e "slicer, scripts,"
	echo -e "klee, witness"
	echo -e "bin     - run compilation _from_ this point"
	echo "" # new line
	echo -e "OPTS = options for make (i. e. -j8)"
}

LLVM_VERSION_DEFAULT=10.0.1
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
LLVM_DYLIB="on" # default link type of LLVM (used when first building LLVM)
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
BUILD_REVERSER='yes'

BUILD_KLEE="yes"
BUILD_WITCH_KLEE="no"
BUILD_NIDHUGG="no"


HAVE_32_BIT_LIBS=$(if check_32_bit; then echo "yes"; else echo "no"; fi)
HAVE_Z3=$(if check_z3; then echo "yes"; else echo "no"; fi)
HAVE_GTEST=$(if check_gtest; then echo "yes"; else echo "no"; fi)
WITH_ZLIB=$(if check_zlib; then echo "no"; else echo "yes"; fi)
ENABLE_TCMALLOC=$(if check_tcmalloc; then echo "on"; else echo "off"; fi)

ARCHIVE="no"
FULL_ARCHIVE="no"
ARCHIVE_PREFIX="symbiotic/"
PRECOMPILE_BITCODE="yes"
ONLY=

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
		'witch-klee')
			BUILD_WITCH_KLEE=yes
		;;
		'no-llvm2c')
			BUILD_LLVM2C="no"
		;;
		'no-reverser')
			BUILD_REVERSER="no"
		;;
		'no-precompile-bitcode')
			PRECOMPILE_BITCODE="no"
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
        archive-prefix=*)
            ARCHIVE_PREFIX=${1##*=}
        ;;
		only=*)
			ONLY=${1##*=}
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

# return true if the component $1 should be built
# (i.e., no only= was given or it lists the component)
want()
{
	if [ -z "$ONLY" ]; then
		return 0
	fi
	case ",$ONLY," in
		*",$1,"*) return 0 ;;
	esac
	return 1
}

for C in $(echo "$ONLY" | tr ',' ' '); do
	case "$C" in
		llvm|svf|dg|sbt-slicer|zlib|stp|googletest|z3|klee|witch-klee|nidhugg|llvm2c|reverser|predator|sbt-instrumentation|transforms|files|dist) ;;
		*) usage; exitmsg "Unknown component in only=: $C" ;;
	esac
done

if [ "x$OPTS" = "x" ]; then
	OPTS='-j1'
fi

if [ -d witch-klee ]; then
	echo "Found a build of witch-klee, turning its build on"
	BUILD_WITCH_KLEE="yes"
fi

PHASE="checking system"
export LLVM_PREFIX="$PREFIX/llvm-$LLVM_VERSION"

if [ "$HAVE_32_BIT_LIBS" = "no" -a "$BUILD_KLEE" = "yes" ]; then
	exitmsg "KLEE needs 32-bit libc headers to build 32-bit versions of runtime libraries. On Ubuntu, this is the package libc6-dev-i386 (or gcc-multilib), on Fedora-based systems it is glibc-devel.i686."
fi
if [ "$HAVE_32_BIT_LIBS" = "no" -a "$BUILD_WITCH_KLEE" = "yes" ]; then
	exitmsg "KLEE needs 32-bit libc headers to build 32-bit versions of runtime libraries. On Ubuntu, this is the package libc6-dev-i386 (or gcc-multilib), on Fedora-based systems it is glibc-devel.i686."
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

	if [ "$BUILD_KLEE" = "yes" -o "$BUILD_WITCH_KLEE" = "yes" ]; then
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

######################################################################
#   Each component is built by its own script in scripts/. The scripts
#   are sourced (they share the variables set up above) and are always
#   run from $ABS_SRCDIR.
######################################################################
build_component()
{
	PHASE="building $1"
	source "$ABS_SRCDIR/scripts/$2"

	if [ "`pwd`" != $ABS_SRCDIR ]; then
		exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
	fi
}

LLVM_MAJOR_VERSION="${LLVM_VERSION%%\.*}"
LLVM_MINOR_VERSION=${LLVM_VERSION#*\.}
LLVM_MINOR_VERSION="${LLVM_MINOR_VERSION%\.*}"

######################################################################
#   get LLVM either from user provided location or from the internet,
#   bulding it
######################################################################
PHASE="setting up LLVM"
if [ $FROM -eq 0 -a $NO_LLVM -ne 1 ] && want llvm; then
	build_component "LLVM" build-llvm.sh
fi

LLVM_CMAKE_CONFIG_DIR=share/llvm/cmake
if [ $LLVM_MAJOR_VERSION -gt 3 ]; then
	LLVM_CMAKE_CONFIG_DIR=lib/cmake/llvm
elif [ $LLVM_MAJOR_VERSION -ge 3 -a $LLVM_MINOR_VERSION -ge 9 ]; then
	LLVM_CMAKE_CONFIG_DIR=lib/cmake/llvm
fi

if [ -z "$WITH_LLVM" ]; then
	export LLVM_DIR=$ABS_RUNDIR/llvm-${LLVM_VERSION}/build/$LLVM_CMAKE_CONFIG_DIR
	export LLVM_BUILD_PATH=$ABS_RUNDIR/llvm-${LLVM_VERSION}/build/
	export LLVM_CONFIG=${ABS_SRCDIR}/llvm-${LLVM_VERSION}/build/bin/llvm-config
else
	export LLVM_DIR=$WITH_LLVM/$LLVM_CMAKE_CONFIG_DIR
	export LLVM_BUILD_PATH=$WITH_LLVM
	export LLVM_CONFIG=${WITH_LLVM}/bin/llvm-config
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

# detect the link type of LLVM that we use
if [ "$($LLVM_CONFIG --shared-mode --libs)" = "shared" ]; then
    LLVM_DYLIB="on"
else
    LLVM_DYLIB="off"
fi

if [ "`pwd`" != $ABS_SRCDIR ]; then
	exitmsg "Inconsistency in the build script, should be in $ABS_SRCDIR"
fi

######################################################################
#   slicer: SVF, dg, sbt-slicer
######################################################################
if [ $FROM -le 1 -a $BUILD_SVF = "yes" ] && want svf; then
	build_component "SVF" build-svf.sh
fi

if [ $FROM -le 1 ] && want dg; then
	build_component "dg" build-dg.sh
fi

if [ $FROM -le 1 ] && want sbt-slicer; then
	build_component "sbt-slicer" build-sbt-slicer.sh
fi

######################################################################
#   zlib, minisat, STP, googletest, Z3
######################################################################
if [ $FROM -le 2 -a $WITH_ZLIB = "yes" ] && want zlib; then
	build_component "zlib" build-zlib.sh
fi

if [ $FROM -le 4 -a "$BUILD_STP" = "yes" -a "$BUILD_KLEE" = "yes" ] && want stp; then
	build_component "minisat and stp" build-stp.sh
fi

if [ $FROM -le 4 -a "$BUILD_KLEE" = "yes" ] && want googletest; then
	build_component "googletest for KLEE" build-googletest.sh
fi

if [ $FROM -le 4 -a "$BUILD_Z3" = "yes" -a "$BUILD_KLEE" = "yes" ] && want z3; then
	build_component "Z3 for KLEE" build-z3.sh
fi

######################################################################
#   KLEE, Witch-KLEE, nidhugg
######################################################################
if [ $FROM -le 4 -a "$BUILD_KLEE" = "yes" ] && want klee; then
	build_component "KLEE" build-klee.sh
fi

if [ $FROM -le 4 -a "$BUILD_WITCH_KLEE" = "yes" ] && want witch-klee; then
	build_component "Witch-KLEE" build-witch-klee.sh
fi

if [ $FROM -le 4 -a "$BUILD_NIDHUGG" = "yes" ] && want nidhugg; then
	build_component "Nidhugg" build-nidhugg.sh
fi

######################################################################
#   llvm2c, reverser, Predator
######################################################################
if [ $FROM -le 6 -a "$BUILD_LLVM2C" = "yes" ] && want llvm2c; then
	build_component "llvm2c" build-llvm2c.sh
fi

if [ $FROM -le 6 -a "$BUILD_REVERSER" = "yes" ] && want reverser; then
	build_component "reverser" build-reverser.sh
fi

if [  -d predator-${LLVM_VERSION} ]; then
	# we already got a build of predator, so rebuild it
	BUILD_PREDATOR="yes"
fi
if [ $FROM -le 6 -a "$BUILD_PREDATOR" = "yes" ] && want predator; then
	build_component "Predator" build-predator.sh
fi

######################################################################
#   instrumentation, transforms (LLVMsbt.so)
######################################################################
if [ $FROM -le 6 ] && want sbt-instrumentation; then
	build_component "sbt-instrumentation" build-sbt-instrumentation.sh
fi

if [ $FROM -le 6 ] && want transforms; then
	build_component "LLVMsbt.so" build-transforms.sh
fi

######################################################################
#   copy lib and include files, precompile function models
######################################################################
if [ $FROM -le 6 ] && want files; then
	build_component "installing files and function models" install-files.sh
fi

######################################################################
#  extract versions of components and create the distribution
######################################################################
if [ $FROM -le 7 ] && want dist; then
	PHASE="generating versions.py file"
	source scripts/gen-version.sh

	PHASE="creating distribution"
	source scripts/push-to-git.sh
fi
