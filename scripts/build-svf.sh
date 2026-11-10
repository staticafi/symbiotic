#!/bin/bash

git_clone_or_pull https://github.com/SVF-tools/SVF

# download the dg library
pushd "$SRCDIR/SVF" || exitmsg "Cloning failed"
mkdir -p build-${LLVM_VERSION} || exitmsg "error"
pushd build-${LLVM_VERSION} || exitmsg "error"

if [ ! -d CMakeFiles ]; then

	export LLVM_SRC="$LLVM_SRC_PATH"
	export LLVM_OBJ="$LLVM_BUILD_PATH"
	export LLVM_DIR="$LLVM_BUILDPATH"
	cmake .. \
		-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
		-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
		|| clean_and_exit 1 "git"
fi

(build && make install) || exitmsg "Building and installing SVF"
popd
popd
