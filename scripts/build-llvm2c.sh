#!/bin/sh

# initialize instrumentation module if not done yet
if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/llvm2c)" ]; then
	git_submodule_init
fi

pushd "$SRCDIR/llvm2c" || exitmsg "Cloning failed"
mkdir -p build-${LLVM_VERSION}
pushd build-${LLVM_VERSION}
if [ ! -d CMakeFiles ]; then
	cmake .. \
		-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
		-DCMAKE_INSTALL_LIBDIR:PATH=lib \
		-DCMAKE_INSTALL_FULL_DATADIR:PATH=$LLVM_PREFIX/share \
		-DLLVM_SRC_PATH="$LLVM_SRC_PATH" \
		-DLLVM_LINK_DYLIB="$LLVM_DYLIB" \
		-DLLVM_BUILD_PATH="$LLVM_BUILD_PATH" \
		-DLLVM_DIR=$LLVM_DIR \
		-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
		|| clean_and_exit 1 "git"
fi

(build && make install) || exit 1

popd
popd

