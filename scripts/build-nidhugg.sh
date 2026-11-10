#!/bin/bash

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

(build && make install) || exitmsg  "Building and installing Nidhugg"
popd
