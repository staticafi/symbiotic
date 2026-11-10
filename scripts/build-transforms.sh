#!/bin/bash

mkdir -p transforms/build-${LLVM_VERSION}
pushd transforms/build-${LLVM_VERSION}

# build prepare and install lib and scripts
if [ ! -d CMakeFiles ]; then
	cmake .. \
		-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
		-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
		-DLLVM_DIR=$LLVM_DIR \
		-DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
		-DCMAKE_INSTALL_PREFIX=$PREFIX \
		-DCMAKE_INSTALL_LIBDIR:PATH=$LLVM_PREFIX/lib \
		|| clean_and_exit 1
fi

(build && make install) || clean_and_exit 1
popd
