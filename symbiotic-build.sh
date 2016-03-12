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

usage()
{
	echo "$0 [shell] [no-llvm] [update] [slicer | scripts | minisat | stp | klee | witness | bin] OPTS"
	echo "" # new line
	echo -e "shell    - run shell with environment set"
	echo -e "no-llvm  - skip compiling llvm (assume that llvm is already"
	echo -e "           present in build directory in folders"
	echo -e "           llvm-build-cmake and llvm-build-configure)"
	echo -e "update   - update repositories"
	echo -e "with-cpa - downlad CPAchecker (due to witness checking)"
	echo -e "with-ultimate-automizer - downlad UltimateAutmizer (due to witness checking)"
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

# klee does not handle builts with abi::cxx11 yet, so we must
# build llvm with the old abi too (if the compiler does
# not support this, then it will ignore the definition
export CPPFLAGS="-D_GLIBCXX_USE_CXX11_ABI=0"


FROM='0'
NO_LLVM='0'
UPDATE=
OPTS=
WITH_CPA='0'
WITH_ULTIMATEAUTOMIZER='0'

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
}

# check if we have everything we need
check

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

# download llvm-3.4 and unpack
if [ $FROM -eq 0 -a $NO_LLVM -ne 1 ]; then
	if [ ! -d 'llvm-3.4' ]; then
		wget http://llvm.org/releases/3.4/llvm-3.4.src.tar.gz || exit 1
		wget http://llvm.org/releases/3.4/clang-3.4.src.tar.gz || exit 1

		tar -xf llvm-3.4.src.tar.gz || exit 1
		tar -xf clang-3.4.src.tar.gz || exit 1

		# move clang to llvm/tools and rename to clang
		mv clang-3.4 llvm-3.4/tools/clang
	fi

	mkdir -p llvm-build-cmake
	cd llvm-build-cmake || exitmsg "downloading failed"

	# configure llvm
	if [ ! -d CMakeFiles ]; then
		echo 'we should definitely build RelWithDebInfo here, no?'
		echo 'N.B. we strip below anyway, so why not Release actually?'
		cmake ../llvm-3.4 \
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
	ONLY_TOOLS='opt clang llvm-link llvm-dis' build

	# we need these binaries in symbiotic
	cp bin/clang $PREFIX/bin/clang || exit 1
	cp bin/opt $PREFIX/bin/opt || exit 1
	cp bin/llvm-link $PREFIX/bin/llvm-link || exit 1
	cd -
fi

export LLVM_DIR=`pwd`/llvm-build-cmake/share/llvm/cmake/

rm -f llvm-3.4.src.tar.gz &>/dev/null || exit 1
rm -f clang-3.4.src.tar.gz &>/dev/null || exit 1

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

if [ $FROM -le 1 ]; then
	git_submodule_init

	cd "$SRCDIR/LLVMSlicer" || exitmsg "Cloning failed"
	if [ ! -d CMakeFiles ]; then
		cmake . \
			-DLLVM_SRC_PATH="$ABS_RUNDIR/llvm-3.4/" \
			-DLLVM_BUILD_PATH="$ABS_RUNDIR"/llvm-build-cmake/ \
			-DCMAKE_INSTALL_PREFIX=$PREFIX || clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1

	# need slicer version
	git rev-parse --short=8 HEAD > $PREFIX/LLVM_SLICER_VERSION
	cd -

	# download new slicer
	cd "$SRCDIR/dg" || exitmsg "Cloning failed"
	if [ ! -d CMakeFiles ]; then
		cmake . \
			-DLLVM_SRC_PATH="$ABS_RUNDIR/llvm-3.4/" \
			-DLLVM_BUILD_PATH="$ABS_RUNDIR/llvm-build-cmake/" \
			-DCMAKE_INSTALL_PREFIX=$PREFIX || clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1

	# need slicer version
	git rev-parse --short=8 HEAD > $PREFIX/LLVM_NEW_SLICER_VERSION
	cd -
fi

if [ $FROM -le 2 ]; then
	git_clone_or_pull git://github.com/niklasso/minisat.git minisat
	cd minisat
	(build lr && make prefix=$PREFIX install-headers) || exit 1
	cp build/release/lib/libminisat.a $PREFIX/lib/ || exit 1

	# we need stp version
	git rev-parse --short=8 HEAD > $PREFIX/MINISAT_VERSION

	cd -
fi

if [ $FROM -le 3 ]; then
	git_clone_or_pull git://github.com/stp/stp.git stp
	cd stp || exitmsg "Clonging failed"
	cmake . -DCMAKE_INSTALL_PREFIX=$PREFIX \
		-DCMAKE_CXX_FLAGS_RELEASE=-O2 \
		-DCMAKE_C_FLAGS_RELEASE=-O2 \
		-DCMAKE_BUILD_TYPE=Release \
		-DBUILD_SHARED_LIBS:BOOL=OFF \
		-DENABLE_PYTHON_INTERFACE:BOOL=OFF || clean_and_exit 1 "git"

	(build "OPTIMIZE=-O2 CFLAGS_M32=install" && make install) || exit 1

	# we need stp version
	git rev-parse --short=8 HEAD > $PREFIX/STP_VERSION

	cd -
fi

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
		../llvm-3.4/configure \
			--enable-optimized --enable-assertions \
			--enable-targets=x86 --enable-docs=no \
			--enable-timestamps=no || clean_and_exit 1
	fi

	build || exit 1
	cd -
fi


if [ $FROM -le 4 ]; then
	# build klee
	git_clone_or_pull git://github.com/staticafi/klee.git klee || exitmsg "Cloning failed"

	mkdir -p klee-build/
	cd klee-build/

	if [ ! -f config.log ]; then
	../klee/configure \
		--prefix=$PREFIX \
		--with-llvmsrc=`pwd`/../llvm-3.4 \
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


	# we need klee version
	cd -
	cd klee || exit 1
	git rev-parse --short=8 HEAD > $PREFIX/KLEE_VERSION

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
		download_tar http://cpachecker.sosy-lab.org/CPAchecker-1.4-unix.tar.bz2
	fi
}

get_ultimize()
{
	if [ ! -d UltimateAutomizer ]; then
		download_tar http://www.sosy-lab.org/~dbeyer/cpa-witnesses/ultimateautomizer.tar.gz
	fi
}

if [ $FROM -le 5 ]; then
	if [ $WITH_CPA -eq 1 ]; then
		get_cpa
		rsync -a CPAchecker-1.4-unix/ $PREFIX/CPAchecker/
	fi
	if [ $WITH_ULTIMATEAUTOMIZER -eq 1 ]; then
		get_ultimize
		rsync -a UltimateAutomizer $PREFIX/
	fi
fi

if [ $FROM -le 6 ]; then
	# download scripts
	git_submodule_init

	cd "$SRCDIR/svc15" || exitmsg "Clonging failed"
	if [ ! -d CMakeFiles ]; then
		cmake . \
			-DLLVM_SRC_PATH="$ABS_RUNDIR/llvm-3.4/" \
			-DLLVM_BUILD_PATH="$ABS_RUNDIR/llvm-build-cmake/" \
			-DCMAKE_INSTALL_PREFIX=$PREFIX || clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1

	git rev-parse --short=8 HEAD > $PREFIX/SVC_SCRIPTS_VERSION

	cd -

	# and also the symbiotic script
	cp $SRCDIR/symbiotic $PREFIX/ || exit 1

	cd "$SRCDIR"
	git rev-parse --short=8 HEAD > $PREFIX/SYMBIOTIC_VERSION
	cd -
fi


if [ $FROM -le 7 ]; then
	cd $PREFIX || exitmsg "Whoot? prefix directory not found! This is a BUG, sir..."

	# create git repository and add all files that we need
	# then remove the rest and create distribution
	BINARIES="bin/clang bin/opt bin/klee bin/llvm-link bin/llvm-slicer"
	LIBRARIES="\
		lib/libLLVMdg.so lib/libPSS.so lib/LLVMSlicer.so lib/LLVMsvc15.so \
		lib/klee/runtime/kleeRuntimeIntrinsic.bc \
		lib32/klee/runtime/kleeRuntimeIntrinsic.bc\
		lib/klee/runtime/klee-libc.bc\
		lib32/klee/runtime/klee-libc.bc"
	SCRIPTS="build-fix.sh path_to_ml.pl symbiotic"

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
		$SCRIPTS \
		$CPACHECKER \
		$ULTIAUTO \
		include/klee/klee.h \
		include/symbiotic.h \
		lib.c \
		LLVM_SLICER_VERSION \
		LLVM_NEW_SLICER_VERSION \
		MINISAT_VERSION \
		SVC_SCRIPTS_VERSION \
		SYMBIOTIC_VERSION \
		STP_VERSION	    \
		KLEE_VERSION

	git commit -m "Create Symbiotic distribution `date`"
	# remove unnecessary files
# DO NOT: so that the tools are not rebuilt over and over
# They depend on the installed headers and libs.
#	git clean -xdf
fi
