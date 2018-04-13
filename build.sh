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
	echo -e "no-llvm  - skip compiling llvm"
	echo -e "update   - update repositories"
	echo -e "with-cpa - download CPAchecker (due to witness checking)"
	echo -e "with-ultimate-automizer - download UltimateAutomizer (due to witness checking)"
	echo -e "with-zlib          - compile zlib"
	echo -e "with-llvm=path     - use llvm from path"
	echo -e "with-llvm-dir=path - use llvm from path"
	echo -e "with-llvm-src=path - use llvm sources from path"
	echo -e "llvm-version=ver   - use this version of llvm"
	echo -e "build-type=TYPE    - set Release/Debug build"
	echo "" # new line
	echo -e "slicer, scripts,"
	echo -e "minisat, stp, klee, witness"
	echo -e "bin     - run compilation _from_ this point"
	echo "" # new line
	echo -e "OPTS = options for make (i. e. -j8)"
}

LLVM_VERSION_DEFAULT=3.9.1
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
export SYMBIOTIC_ENV=1

export LD_LIBRARY_PATH="$PREFIX/lib:$LD_LIBRARY_PATH"
export C_INCLUDE_PATH="$PREFIX/include:$C_INCLUDE_PATH"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/share/pkgconfig:$PKG_CONFIG_PATH"

FROM='0'
NO_LLVM='0'
UPDATE=
OPTS=
WITH_CPA='0'
WITH_ULTIMATEAUTOMIZER='0'
LLVM_VERSION=`get_llvm_version`
WITH_LLVM=
WITH_LLVM_SRC=
WITH_LLVM_DIR=
WITH_ZLIB='no'
[ -z $BUILD_TYPE ] && BUILD_TYPE="Release"

export LLVM_PREFIX="$PREFIX/llvm-$LLVM_VERSION"

abspath() {
	if which realpath &>/dev/null; then
		realpath "$1"
	elif [[ "$OSTYPE" == *darwin* ]]; then
		greadlink -f "$1"
	else
		readlink -f "$1"
	fi
}

RUNDIR=`pwd`
SRCDIR=`dirname $0`
ABS_RUNDIR=`abspath $RUNDIR`
ABS_SRCDIR=`abspath $SRCDIR`
ARCHIVE="no"

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
		with-zlib)
			WITH_ZLIB="yes"
		;;
		archive)
			ARCHIVE="yes"
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

GET="curl -LRO"
check()
{
	if ! curl --version &>/dev/null; then
		echo "Need curl to download files"
		exit 1
	fi

	if ! cmake --version &>/dev/null; then
		echo "cmake is needed"
		exit 1
	fi

	if ! make --version &>/dev/null; then
		echo "make is needed"
		exit 1
	fi

	if ! rsync --version &>/dev/null; then
		echo "will need rsync... or hack the script so that it uses cp ;)"
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
	ONLY_TOOLS='opt clang llvm-link llvm-dis llvm-nm' build
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

	# we need these binaries in symbiotic
	mkdir -p $LLVM_PREFIX/bin
	cp $LLVM_LOCATION/bin/clang $LLVM_PREFIX/bin/clang || exit 1
	cp $LLVM_LOCATION/bin/opt $LLVM_PREFIX/bin/opt || exit 1
	cp $LLVM_LOCATION/bin/llvm-link $LLVM_PREFIX/bin/llvm-link || exit 1
	cp $LLVM_LOCATION/bin/llvm-nm $LLVM_PREFIX/bin/llvm-nm || exit 1
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
#   slicer
######################################################################
if [ $FROM -le 1 ]; then
	if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/dg)" ]; then
		git_submodule_init
	fi

	# download the dg library
	cd "$SRCDIR/dg" || exitmsg "Cloning failed"
	if [ ! -d CMakeFiles ]; then
		cmake . \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
			-DCMAKE_INSTALL_LIBDIR:PATH=lib \
			-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
			-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
			-DLLVM_DIR=$LLVM_DIR \
			-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
			|| clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1
	cd -

	# initialize instrumentation module if not done yet
	if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/sbt-slicer)" ]; then
		git_submodule_init
	fi

	cd "$SRCDIR/sbt-slicer" || exitmsg "Cloning failed"
	if [ ! -d CMakeFiles ]; then
		cmake . \
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
	cd -
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

######################################################################
#   minisat
######################################################################
if [ $FROM -le 2 ]; then
	git_clone_or_pull git://github.com/stp/minisat.git minisat
	pushd minisat
	mkdir -p build
	cd build || exit 1

	if [ ! -d CMakeFiles ]; then
		cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX \
				 -DSTATICCOMPILE=ON
	fi

	(make "$OPTS" && make install) || exit 1
	popd
fi

######################################################################
#   STP
######################################################################
if [ $FROM -le 3 ]; then
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

######################################################################
#   KLEE
######################################################################
if [ $FROM -le 4 ]; then
	# build klee
	git_clone_or_pull "-b 6.0.0 https://github.com/staticafi/klee.git" klee || exitmsg "Cloning failed"

	# workaround a problem with calling llvm-config from build directory
	if [ ! -f ${ABS_SRCDIR}/llvm-3.9.1/build/lib/libgtest.a -o
	     ! -f ${ABS_SRCDIR}/llvm-3.9.1/build/lib/libgtest_main.a ]; then
		touch ${ABS_SRCDIR}/llvm-3.9.1/build/lib/libgtest.a
		touch ${ABS_SRCDIR}/llvm-3.9.1/build/lib/libgtest_main.a
	fi

	mkdir -p klee-build/
	cd klee-build/

	if [ "x$BUILD_TYPE" = "xRelease" ]; then
		KLEE_BUILD_TYPE="Release+Asserts"
	else
		KLEE_BUILD_TYPE="$BUILD_TYPE"
	fi

	if [ ! -d CMakeFiles ]; then
		# use our zlib, if we compiled it
		ZLIB_FLAGS=
		if [ -d $RUNDIR/zlib ]; then
			ZLIB_FLAGS="-DZLIB_LIBRARY=-L${PREFIX}/lib;-lz"
			ZLIB_FLAGS="$ZLIB_FLAGS -DZLIB_INCLUDE_DIR=$PREFIX/include"
		fi

		cmake ../klee -DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
			-DKLEE_RUNTIME_BUILD_TYPE=${KLEE_BUILD_TYPE} \
			-DENABLE_SOLVER_STP=ON \
			-DSTP_DIR=`pwd`/../stp \
			-DLLVM_CONFIG_BINARY=`pwd`/../llvm-${LLVM_VERSION}/build/bin/llvm-config \
			-DENABLE_UNIT_TESTS=OFF \
			$ZLIB_FLAGS \
			|| clean_and_exit 1 "git"
	fi

	# clean runtime libs, it may be 32-bit from last build
	make -C runtime -f Makefile.cmake.bitcode clean 2>/dev/null
	rm -f ${KLEE_BUILD_TYPE}/lib/kleeRuntimeIntrinsic.bc* 2>/dev/null
	rm -f ${KLEE_BUILD_TYPE}/lib/klee-libc.bc* 2>/dev/null

	# build 64-bit libs and install them to prefix
	pwd
	(build && make install) || exit 1

	mv $LLVM_PREFIX/lib64/klee $LLVM_PREFIX/lib/klee
	rmdir $LLVM_PREFIX/lib64

	# clean 64-bit build and build 32-bit version of runtime library
	make -C runtime -f Makefile.cmake.bitcode clean \
		|| exitmsg "Failed building klee 32-bit runtime library"
	rm -f ${KLEE_BUILD_TYPE}/lib/kleeRuntimeIntrinsic.bc*
	rm -f ${KLEE_BUILD_TYPE}/lib/klee-libc.bc*
	# EXTRA_LLVMCC.Flags is obsolete and to be removed soon
	make -C runtime/Intrinsic -f Makefile.cmake.bitcode \
		LLVMCC.ExtraFlags=-m32 \
		EXTRA_LLVMCC.Flags=-m32 \
		|| exitmsg "Failed building 32-bit klee runtime library"
	make -C runtime/klee-libc -f Makefile.cmake.bitcode \
		LLVMCC.ExtraFlags=-m32 \
		EXTRA_LLVMCC.Flags=-m32 \
		|| exitmsg "Failed building 32-bit klee runtime library"

	# copy 32-bit library version to prefix
	mkdir -p $LLVM_PREFIX/lib32/klee/runtime
	cp ${KLEE_BUILD_TYPE}/lib/kleeRuntimeIntrinsic.bc \
		$LLVM_PREFIX/lib32/klee/runtime/kleeRuntimeIntrinsic.bc \
		|| exitmsg "Did not build 32-bit klee runtime lib"
	cp ${KLEE_BUILD_TYPE}/lib/klee-libc.bc \
		$LLVM_PREFIX/lib32/klee/runtime/klee-libc.bc \
		|| exitmsg "Did not build 32-bit klee runtime lib"

	cd -
fi

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

get_cpa()
{
	if [ ! -d CPAchecker ]; then
		CPA_VERSION="CPAchecker-1.6.12-svcomp17-unix"
		download_tar https://cpachecker.sosy-lab.org/${CPA_VERSION}.tar.bz2
		mv "$CPA_VERSION" "CPAchecker" || exit 1
	fi
}

get_ultimize()
{
	if [ ! -d UltimateAutomizer ]; then
		ULTIMATE_VERSION=UltimateAutomizer-linux
		download_zip https://ultimate.informatik.uni-freiburg.de/downloads/svcomp2017/${ULTIMATE_VERSION}.zip
		mv "UAutomizer-linux" "UltimateAutomizer" || exit 1
	fi
}

######################################################################
#   witness checkers
######################################################################
if [ $FROM -le 5 ]; then
	if [ $WITH_CPA -eq 1 ]; then
		get_cpa
		rsync -a CPAchecker $PREFIX/
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
			-DCMAKE_INSTALL_LIBDIR:PATH=$LLVM_PREFIX/lib \
			|| exit 1
			# DONT call clean_and_exit 1 "git" here, otherwise
			# everything that was compiled will be removed
	fi

	(build && make install) || exit 1

	# initialize instrumentation module if not done yet
	if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/sbt-instrumentation)" ]; then
		git_submodule_init
	fi

	cd "$SRCDIR/sbt-instrumentation" || exitmsg "Cloning failed"
	if [ ! -d CMakeFiles ]; then
		./bootstrap-json.sh || exitmsg "Failed generating json files"
		cmake . \
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
	cd -

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
	cd sbt-slicer || exit 1
	SBT_SLICER_VERSION=`git rev-parse HEAD`
	cd -
	cd sbt-instrumentation || exit 1
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

	VERSFILE="$SRCDIR/lib/symbioticpy/symbiotic/versions.py"
	echo "#!/usr/bin/python" > $VERSFILE
	echo "# This file is automatically generated by symbiotic-build.sh" >> $VERSFILE
	echo "" >> $VERSFILE
	echo "versions = {" >> $VERSFILE
	echo -e "\t'symbiotic' : '$SYMBIOTIC_VERSION'," >> $VERSFILE
	echo -e "\t'dg' : '$DG_VERSION'," >> $VERSFILE
	echo -e "\t'sbt-slicer' : '$SBT_SLICER_VERSION'," >> $VERSFILE
	echo -e "\t'sbt-instrumentation' : '$INSTRUMENTATION_VERSION'," >> $VERSFILE
	echo -e "\t'minisat' : '$MINISAT_VERSION'," >> $VERSFILE
	echo -e "\t'stp' : '$STP_VERSION'," >> $VERSFILE
	echo -e "\t'KLEE' : '$KLEE_VERSION'," >> $VERSFILE
	echo -e "}\n\n" >> $VERSFILE
	echo "llvm_version = '${LLVM_VERSION}'" >> $VERSFILE

######################################################################
#  create distribution
######################################################################
	# copy the symbiotic python module
	cp -r $SRCDIR/lib/symbioticpy $PREFIX/lib || exit 1

	cd $PREFIX || exitmsg "Whoot? prefix directory not found! This is a BUG, sir..."

	# create git repository and add all files that we need
	# then remove the rest and create distribution
	BINARIES="$LLVM_PREFIX/bin/clang $LLVM_PREFIX/bin/opt \
		  $LLVM_PREFIX/bin/klee $LLVM_PREFIX/bin/llvm-link \
		  $LLVM_PREFIX/bin/llvm-nm $LLVM_PREFIX/bin/sbt-slicer \
		  $LLVM_PREFIX/bin/sbt-instr"
	LIBRARIES="\
		$LLVM_PREFIX/lib/libLLVMdg.so $LLVM_PREFIX/lib/libLLVMpta.so \
		$LLVM_PREFIX/lib/libPTA.so $LLVM_PREFIX/lib/libRD.so \
		$LLVM_PREFIX/lib/LLVMsbt.so \
		$LLVM_PREFIX/lib/libPoints_to_plugin.so \
		$LLVM_PREFIX/lib/klee/runtime/kleeRuntimeIntrinsic.bc \
		$LLVM_PREFIX/lib32/klee/runtime/kleeRuntimeIntrinsic.bc \
		$LLVM_PREFIX/lib/klee/runtime/klee-libc.bc \
		$LLVM_PREFIX/lib32/klee/runtime/klee-libc.bc"
	INSTR="$LLVM_PREFIX/share/sbt-instrumentation/*/*.c \
	       $LLVM_PREFIX/share/sbt-instrumentation/*/*.json"

#CPACHECKER=
#ULTIAUTO=
#if [ $WITH_CPA -eq 1 ]; then
#	CPACHECKER=`find CPAchecker/ -type f`
#fi
#if [ $WITH_ULTIMATEAUTOMIZER -eq 1 ]; then
#	ULTIAUTO=`find UltimateAutomizer/ -type f`
#fi

	#strip binaries, it will save us 500 MB!
	strip $BINARIES

	git init
	git add \
		$BINARIES \
		$LIBRARIES \
		$INSTR\
		bin/symbiotic \
		include/symbiotic.h \
		include/symbiotic-size_t.h \
		$LLVM_PREFIX/include/stddef.h \
		lib/*.c \
		lib/symbioticpy/symbiotic/*.py \
		lib/symbioticpy/symbiotic/benchexec/*.py \
		lib/symbioticpy/symbiotic/benchexec/tools/*.py \
		lib/symbioticpy/symbiotic/tools/*.py \
		lib/symbioticpy/symbiotic/utils/*.py \
		lib/symbioticpy/symbiotic/witnesses/*.py \
		$CPACHECKER \
		$ULTIAUTO

	git commit -m "Create Symbiotic distribution `date`"
	# remove unnecessary files
# DO NOT: so that the tools are not rebuilt over and over
# They depend on the installed headers and libs.
#	git clean -xdf
fi

if [ "x$ARCHIVE" = "xyes" ]; then
	git archive --prefix "symbiotic/" -o symbiotic.zip -9 --format zip HEAD
fi
