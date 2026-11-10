#!/bin/bash

if [ ! -d googletest ]; then
	download_zip https://github.com/google/googletest/archive/release-1.7.0.zip || exitmsg "Downloading googletest"
	mv googletest-release-1.7.0 googletest || exitmsg "error"
	rm -f release-1.7.0.zip
fi

pushd googletest
mkdir -p build
pushd build
if [ ! -d CMakeFiles ]; then
	cmake ..
fi

build || clean_and_exit 1
# copy the libraries to LLVM build, there is a "bug" in llvm-config
# that requires them
if [ -d ${ABS_SRCDIR}/llvm-${LLVM_VERSION}/build/lib ]; then
  cp *.a ${ABS_SRCDIR}/llvm-${LLVM_VERSION}/build/lib
fi

popd; popd
