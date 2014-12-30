#!/bin/sh

# Build symbiotic from scratch and setup environment for
# development if needed

# this is either 'shell' - that means setting development enivironment
# and run shell - or it contains options for compilation
OPTS="$1"

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

set_env()
{
	export PREFIX=`pwd`/install
	export PATH=$PREFIX/bin:$PATH
	export SYMBIOTIC_ENV=1
}

set_env

if [ "$OPTS" = "shell" ]; then
	# stp needs this
	ulimit -s unlimited
	# the environment is already set, just exec the shell
	exec $SHELL
elif [ "x$OPTS" = "x" ]; then
	OPTS='-j1'
fi

# check if we have everything we need
check

# download llvm-3.2 and unpack
if [ ! -d 'llvm-3.2.src' ]; then
	wget http://llvm.org/releases/3.2/llvm-3.2.src.tar.gz || exit 1
	wget http://llvm.org/releases/3.2/clang-3.2.src.tar.gz || exit 1

	tar -xf llvm-3.2.src.tar.gz || exit 1
	tar -xf clang-3.2.src.tar.gz || exit 1

	# move clang to llvm/tools and rename to clang
	mv clang-3.2.src llvm-3.2.src/tools/clang
fi

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
make "$OPTS" || exit 1

# we need build binaries
make install DESTDIR=$PREFIX || exit 1

# we need these binaries in symbiotic
cp bin/clang $PREFIX/bin
cp bin/opt $PREFIX/bin
cd -

export LLVM_DIR=`pwd`/llvm-build-cmake/share/llvm/cmake/

# download slicer
git clone git://github.com/jirislaby/LLVMSlicer.git
cd LLVMSlicer
if [ ! -d CMakeFiles ]; then
	cmake . \
		-DLLVM_SRC_PATH=../llvm-3.2.src/ \
		-DLLVM_BUILD_PATH=../llvm-build-cmake/ \
		-DCMAKE_INSTALL_PREFIX=$PREFIX || clean_and_exit 1 "git"
fi

(make "$OPTS" && make install) || exit 1
cd -


# download svc13
git clone git://github.com/jirislaby/svc13.git
cd svc13
if [ ! -d CMakeFiles ]; then
	cmake . \
		-DLLVM_SRC_PATH=../llvm-3.2.src/ \
		-DLLVM_BUILD_PATH=../llvm-build-cmake/ \
		-DCMAKE_INSTALL_PREFIX=$PREFIX || clean_and_exit 1 "git"
fi

(make "$OPTS" && make install) || exit 1
cd -

git clone git://github.com/stp/stp.git
cd stp
cmake . -DCMAKE_INSTALL_PREFIX=$PREFIX \
	-DBUILD_SHARED_LIBS:BOOL=OFF \
	-DENABLE_PYTHON_INTERFACE:BOOL=OFF || clean_and_exit 1 "git"

(make "$OPTS" OPTIMIZE=-O2 CFLAGS_M32=install && make install) || exit 1
cd -

# we must build llvm once again with configure script (klee needs this)
mkdir -p llvm-build-configure
cd llvm-build-configure

# configure llvm if not done yet
if [ ! -f config.log ]; then
	../llvm-3.2.src/configure \
		--enable-optimized --enable-assertions \
		--enable-targets=x86 --enable-docs=no || clean_and_exit 1
fi

make "$OPTS" || exit 1
cd -


# build klee
git clone git://github.com/klee/klee.git
cd klee

if [ ! -f config.log ]; then
	./configure \
		--prefix=$PREFIX \
		--with-llvmsrc=../llvm-3.2.src \
		--with-llvmobj=../llvm-build-configure \
		--with-stp=$PREFIX || clean_and_exit 1 "git"
fi

(make "$OPTS" ENABLE_OPTIMIZED=1 DISABLE_ASSERTIONS=1 ENABLE_SHARED=0 && make install) || exit 1
cd -

cd $PREFIX
# create git repository and add all files that we need
# then remove the rest and create distribution
git init
git add \
	bin/clang \
	bin/opt \
	bin/klee \
	bin/stp \
	lib/LLVMSlicer.so \
	lib/LLVMsvc13.so \
	lib/libkleeRuntest.so \
	lib/libkleeRuntimeIntrinsic.bca

git commit -m "Create Symbiotic distribution `date`"
# remove unnecessary files
git clean -xdf
