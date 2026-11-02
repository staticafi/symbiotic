#!/bin/sh

# initialize reverser module if not done yet
if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/reverser)" ]; then
	git_submodule_init
fi

pushd "$SRCDIR/reverser" || exitmsg "Cloning failed"
mkdir -p build-${LLVM_VERSION}
pushd build-${LLVM_VERSION}
if [ ! -d CMakeFiles ]; then
	cmake .. \
		-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
		-DLLVM_VERSION=${LLVM_VERSION} \
		-DLLVM_DIR=$LLVM_DIR \
		-DCMAKE_INSTALL_PREFIX=$LLVM_PREFIX \
		-DREVERSER_BUILD_TESTS=OFF \
		|| clean_and_exit 1 "git"
fi

(build && make install) || exit 1

popd
popd
