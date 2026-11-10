#!/bin/bash

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
		-DLLVM_LINK_DYLIB="$LLVM_DYLIB" \
		-DDG_PATH=$ABS_SRCDIR/dg \
		-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
		|| clean_and_exit 1 "git"
fi

(build && make install) || exitmsg  "Building and installing sbt-instrumentation"

popd
popd
