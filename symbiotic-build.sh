#!/bin/bash

# Build symbiotic from scratch and setup environment for
# development if needed

usage()
{

	echo "$0 [shell] [no-llvm] [update] [slicer | scripts | minisat | stp | klee | bin] OPTS"
	echo "" # new line
	echo -e "shell   - run shell with environment set"
	echo -e "no-llvm - skip compiling llvm (assume that llvm is already"
	echo -e "          present in build directory in folders"
	echo -e "          llvm-build-cmake and llvm-build-configure)"
	echo -e "update  - update repositories"
	echo "" # new line
	echo -e "slicer, scripts,"
	echo -e "minisat, stp, klee,"
	echo -e "bin     - run compilation _from_ this point"
	echo "" # new line
	echo -e "OPTS = options for make (i. e. -j8)"
}

export PREFIX=`pwd`/install
export SYMBIOTIC_ENV=1

FROM='0'
NO_LLVM='0'
UPDATE=
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
		'minisat')
			FROM='3'
		;;
		'stp')
			FROM='4'
		;;
		'klee')
			FROM='5'
		;;
		'bin')
			FROM='6'
		;;
		'no-llvm')
			NO_LLVM=1
		;;
		'update')
			UPDATE=1
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
	cd llvm-build-cmake || exitmsg "downloading failed"

	# configure llvm
	if [ ! -d CMakeFiles ]; then
		echo 'we should definitely build RelWithDebInfo here, no?'
		echo 'N.B. we strip below anyway, so why not Release actually?'
		cmake ../llvm-3.2.src \
			-DCMAKE_BUILD_TYPE=Debug \
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

rm -f llvm-3.2.src.tar.gz &>/dev/null || exit 1
rm -f clang-3.2.src.tar.gz &>/dev/null || exit 1

git_clone_or_pull()
{

	REPO="$1"
	FOLDER="$2"

	if [ -d "$FOLDER" ]; then
		if [ "x$UPDATE" = "x1" ]; then
			# we don't have to cd back, because if git pull fails
			# the script will be killed
			cd $FOLDER && git pull
		fi
	else
		git clone $REPO $FOLDER
	fi

	return 0
}

if [ $FROM -le 1 ]; then
	# download slicer
	git_clone_or_pull https://github.com/mchalupa/LLVMSlicer.git LLVMSlicer
	cd LLVMSlicer || exitmsg "Cloning failed"
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
	cd svc13 || exitmsg "Clonging failed"
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
	cp AI_slicing/klee-log-parser.sh $PREFIX/ || exit 1
fi

if [ $FROM -le 3 ]; then
	git_clone_or_pull git://github.com/niklasso/minisat.git minisat
	cd minisat
	(build lr && make prefix=$PREFIX install-headers) || exit 1
	cp build/release/lib/libminisat.a $PREFIX/lib/ || exit 1

	# we need stp version
	git rev-parse --short=8 HEAD > $PREFIX/MINISAT_VERSION

	cd -
fi

if [ $FROM -le 4 ]; then
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

if [ $FROM -le 5 -a $NO_LLVM -ne 1 ]; then
	# we must build llvm once again with configure script (klee needs this)
	mkdir -p llvm-build-configure || exitmsg "Creating building directory failed"
	cd llvm-build-configure


	# configure llvm if not done yet
	if [ ! -f config.log ]; then
		../llvm-3.2.src/configure \
			--enable-optimized --enable-assertions \
			--enable-targets=x86 --enable-docs=no \
			--enable-timestamps=no || clean_and_exit 1
	fi

	build || exit 1
	cd -
fi


if [ $FROM -le 5 ]; then
	# build klee
	git_clone_or_pull git://github.com/klee/klee.git klee || exitmsg "Cloning failed"

	mkdir klee-build/
	cd klee-build/

	if [ ! -f config.log ]; then
	../klee/configure \
		--prefix=$PREFIX \
		--with-llvmsrc=../llvm-3.2.src \
		--with-llvmobj=../llvm-build-configure \
		--with-stp=$PREFIX || clean_and_exit 1 "git"
	fi

	# clean any other previous build (it can be 64-bit)
	# and build 32-bit version of runtime library
	make -C runtime/Intrinsic clean
	rm -f Release+Asserts/lib/libkleeRuntimeIntrinsic.bca*
	make -C runtime/Intrinsic CFLAGS=-m32

	# create 32-bit version of runtime libraries
	mkdir -p $PREFIX/lib32
	cp Release+Asserts/lib/libkleeRuntimeIntrinsic.bca $PREFIX/lib32/libkleeRuntimeIntrinsic.bca

	make -C runtime/Intrinsic clean
	rm -f Release+Asserts/lib/libkleeRuntimeIntrinsic.bca*
	(build "ENABLE_SHARED=0" && make install) || exit 1

	# we need klee version
	cd -
	cd klee
	git rev-parse --short=8 HEAD > $PREFIX/KLEE_VERSION

	cd -
fi

if [ $FROM -le 6 ]; then
	cd $PREFIX || exitmsg "Whoot? prefix directory not found! This is a BUG, sir..."

	# create git repository and add all files that we need
	# then remove the rest and create distribution
	BINARIES="bin/clang bin/opt bin/klee bin/stp bin/llvm-link"
	LIBRARIES="lib/LLVMSlicer.so lib/LLVMsvc13.so lib/libkleeRuntest.so \
			lib/libkleeRuntimeIntrinsic.bca \
			lib32/libkleeRuntimeIntrinsic.bca"
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
		MINISAT_VERSION \
		SVC_SCRIPTS_VERSION \
		STP_VERSION	    \
		KLEE_VERSION

	git commit -m "Create Symbiotic distribution `date`"
	# remove unnecessary files
# DO NOT: so that the tools are not rebuilt over and over
# They depend on the installed headers and libs.
#	git clean -xdf
fi
