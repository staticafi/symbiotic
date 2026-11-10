#!/bin/bash

if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/dg)" ]; then
	git_submodule_init
fi

if [ -d $SRCDIR/SVF ]; then
	SVF_FLAGS="-DSVF_DIR=$ABS_SRCDIR/SVF/build-${LLVM_VERSION}"
fi

# download the dg library
pushd "$SRCDIR/dg" || exitmsg "Cloning failed"
mkdir -p build-${LLVM_VERSION} || exitmsg "error"
pushd build-${LLVM_VERSION} || exitmsg "error"

if [ ! -d CMakeFiles ]; then
	cmake .. \
		-DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
		-DCMAKE_INSTALL_LIBDIR:PATH=lib \
		-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
		-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
		-DLLVM_LINK_DYLIB="$LLVM_DYLIB" \
		-DLLVM_DIR=$LLVM_DIR \
		-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
		-DCMAKE_INSTALL_RPATH="\$ORIGIN/../lib" \
		${SVF_FLAGS} \
		|| clean_and_exit 1 "git"
fi

(build && make install) || exitmsg "Building and installing DG"
popd
popd
