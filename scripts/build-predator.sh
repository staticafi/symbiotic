#!/bin/bash

if [ ! -d predator-${LLVM_VERSION} ]; then
	git_clone_or_pull "https://github.com/staticafi/predator" -b svcomp21-v1 predator-${LLVM_VERSION}
fi

pushd predator-${LLVM_VERSION}

if [ ! -f cl_build/CMakeCache.txt ]; then
	./switch-host-llvm.sh ${ABS_SRCDIR}/llvm-${LLVM_VERSION}/build/${LLVM_CMAKE_CONFIG_DIR}
fi

build || exitmsg  "Building Predator"
mkdir -p $LLVM_PREFIX/predator/lib
cp sl_build/*.so $LLVM_PREFIX/predator/lib
cp sl_build/slllvm* $LLVM_PREFIX/bin/
cp sl_build/*.sh $LLVM_PREFIX/predator/
cp build-aux/cclib.sh $LLVM_PREFIX/predator/
cp passes-src/passes_build/*.so $LLVM_PREFIX/predator/lib

popd
