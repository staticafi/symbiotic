#!/bin/bash

# Build symbiotic from scratch and setup environment for
# development if needed

usage()
{

	echo "$0 [shell] [no-llvm] [slicer | scripts | stp | klee | bin] OPTS"
	echo "" # new line
	echo -e "shell   - run shell with environment set"
	echo -e "no-llvm - skip compiling llvm (assume that llvm is already"
	echo -e "          present in build directory in folders"
	echo -e "          llvm-build-cmake and llvm-build-configure)"
	echo "" # new line
	echo -e "slicer, svc13"
	echo -e "klee, bin, stp      - run compilation _from_ this point"
	echo "" # new line
	echo -e "OPTS = options for make (i. e. -j8)"
}


export PREFIX=`pwd`/install
export SYMBIOTIC_ENV=1

FROM='0'
NO_LLVM='0'
OPTS=

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
		'scripts')
			FROM='2'
		;;
		'stp')
			FROM='3'
		;;
		'klee')
			FROM='4'
		;;
		'bin')
			FROM='5'
		;;
		'no-llvm')
			NO_LLVM=1
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

# we don't want to build symbiotic in the same directory as
# these scripts
if [ "`dirname $0`" = '.' ]; then
	echo "Building symbiotic in this directory is forbidden"
	exit 1
fi

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

build()
{
	make "$OPTS" CFLAGS="$CFLAGS" CPPFLAGS="$CPPFLAGS" LDFLAGS="$LDFLAGS" $1 || exit 1
	return 0
}

# download llvm-3.2 and unpack
if [ $FROM -eq 0 -a $NO_LLVM -ne 1 ]; then
	if [ ! -d 'llvm-3.2.src' ]; then
		wget http://llvm.org/releases/3.2/llvm-3.2.src.tar.gz || exit 1
		wget http://llvm.org/releases/3.2/clang-3.2.src.tar.gz || exit 1

		tar -xf llvm-3.2.src.tar.gz || exit 1
		tar -xf clang-3.2.src.tar.gz || exit 1

		# move clang to llvm/tools and rename to clang
		mv clang-3.2.src llvm-3.2.src/tools/clang
	fi

	mkdir -p llvm-build-cmake
	cd llvm-build-cmake

	# configure llvm
	if [ ! -d CMakeFiles ]; then
		cmake ../llvm-3.2.src \
			-DCMAKE_BUILD_TYPE=Debug \
			-DLLVM_INCLUDE_EXAMPLES=OFF \
			-DLLVM_INCLUDE_TESTS=OFF \
			-DLLVM_ENABLE_TIMESTAMPS=OFF \
			-DLLVM_TARGETS_TO_BUILD="X86" \
			-DCMAKE_C_FLAGS_DEBUG="-O0 -g" \
			-DCMAKE_CXX_FLAGS_DEBUG="-O0 -g" || clean_and_exit
	fi

	# build llvm
	build

	# we need build binaries

	# we need these binaries in symbiotic
	cp bin/clang $PREFIX/bin/clang || exit 1
	cp bin/opt $PREFIX/bin/opt || exit 1
	cp bin/llvm-link $PREFIX/bin/llvm-link || exit 1
	cd -
fi

export LLVM_DIR=`pwd`/llvm-build-cmake/share/llvm/cmake/

rm -f llvm-3.2.src.tar.gz &>/dev/null || exit 1
rm -f clang-3.2.src.tar.gz &>/dev/null || exit 1

git_clone_or_pull()
{
	REPO="$1"
	FOLDER="$2"

	git clone $REPO || (cd $FOLDER && git pull)
	# do not throw error if pull fails, we can have uncommited
	# changes that we want there
}

if [ $FROM -le 1 ]; then
	# download slicer
	git_clone_or_pull https://github.com/mchalupa/LLVMSlicer.git LLVMSlicer
	cd LLVMSlicer
	if [ ! -d CMakeFiles ]; then
		cmake . \
			-DLLVM_SRC_PATH=../llvm-3.2.src/ \
			-DLLVM_BUILD_PATH=../llvm-build-cmake/ \
			-DCMAKE_INSTALL_PREFIX=$PREFIX || clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1
	cd -
fi


if [ $FROM -le 2 ]; then
	# download scripts
	git_clone_or_pull https://github.com/mchalupa/svc13.git svc13
	cd svc13
	if [ ! -d CMakeFiles ]; then
		cmake . \
			-DLLVM_SRC_PATH=../llvm-3.2.src/ \
			-DLLVM_BUILD_PATH=../llvm-build-cmake/ \
			-DCMAKE_INSTALL_PREFIX=$PREFIX || clean_and_exit 1 "git"
	fi

	(build && make install) || exit 1
	cd -

	# we need klee-log-parser
	git_clone_or_pull https://github.com/mchalupa/AI_slicing.git AI_slicing
	cp AI_slicing/klee-log-parser.sh $PREFIX/
fi

if [ $FROM -le 3 ]; then
	git_clone_or_pull git://github.com/stp/stp.git stp
	cd stp
	cmake . -DCMAKE_INSTALL_PREFIX=$PREFIX \
		-DBUILD_SHARED_LIBS:BOOL=OFF \
		-DENABLE_PYTHON_INTERFACE:BOOL=OFF || clean_and_exit 1 "git"

	(build "OPTIMIZE=-O2 CFLAGS_M32=install" && make install) || exit 1

	# we need stp version
	git rev-parse --short=8 HEAD > $PREFIX/STP_VERSION

	cd -
fi

if [ $FROM -le 4 -a $NO_LLVM -ne 1 ]; then
	# we must build llvm once again with configure script (klee needs this)
	mkdir -p llvm-build-configure
	cd llvm-build-configure

	# configure llvm if not done yet
	if [ ! -f config.log ]; then
		../llvm-3.2.src/configure \
			--enable-optimized --enable-assertions \
			--enable-targets=x86 --enable-docs=no || clean_and_exit 1
	fi

	build || exit 1
	cd -
fi


if [ $FROM -le 4 ]; then
	# build klee
	git_clone_or_pull git://github.com/klee/klee.git klee
	cd klee

	if [ ! -f config.log ]; then
	./configure \
		--prefix=$PREFIX \
		--with-llvmsrc=../llvm-3.2.src \
		--with-llvmobj=../llvm-build-configure \
		--with-stp=$PREFIX || clean_and_exit 1 "git"
	fi

	(build "ENABLE_OPTIMIZED=1 DISABLE_ASSERTIONS=1 ENABLE_SHARED=0" && make install) || exit 1

	# we need klee version
	git rev-parse --short=8 HEAD > $PREFIX/KLEE_VERSION

	cd -
fi

if [ $FROM -le 5 ]; then
	cd $PREFIX
	# create git repository and add all files that we need
	# then remove the rest and create distribution
	BINARIES="bin/clang bin/opt bin/klee bin/stp bin/llvm-link"
	LIBRARIES="lib/LLVMSlicer.so lib/LLVMsvc13.so lib/libkleeRuntest.so\
			lib/libkleeRuntimeIntrinsic.bca"
	SCRIPTS="klee-log-parser.sh build-fix.sh instrument.sh\
		process_set.sh runme"

	#strip binaries, it will save us 500 MB!
	strip $BINARIES

	git init
	git add \
		$BINARIES \
		$LIBRARIES \
		$SCRIPTS \
		include/klee/klee.h \
		include/symbiotic.h \
		lib.c \
		LLVM_SLICER_VERSION \
		SVC_SCRIPTS_VERSION \
		STP_VERSION	    \
		KLEE_VERSION

	git commit -m "Create Symbiotic distribution `date`"
	# remove unnecessary files
	git clean -xdf
fi
