#!/bin/sh

# initialize reverser module if not done yet
if [  "x$UPDATE" = "x1" -o -z "$(ls -A $SRCDIR/reverser)" ]; then
	git_submodule_init
fi

pushd "$SRCDIR/reverser" || exitmsg "Cloning failed"
mkdir -p build-${LLVM_VERSION}
pushd build-${LLVM_VERSION}
if [ ! -d CMakeFiles ]; then
	# reverser must be compiled with the same RTTI setting as LLVM,
	# otherwise linking fails on missing typeinfo for LLVM classes
	# (LLVM is built without RTTI by default, distributions often enable it)
	REVERSER_CXX_FLAGS=
	if [ "$($LLVM_CONFIG --has-rtti)" = "NO" ]; then
		REVERSER_CXX_FLAGS="-fno-rtti"
	fi

	cmake .. \
		-DCMAKE_CXX_FLAGS="$REVERSER_CXX_FLAGS" \
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
