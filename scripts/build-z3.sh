#!/bin/bash

if [ ! -d "z3" ]; then
	git_clone_or_pull git://github.com/Z3Prover/z3 -b "z3-4.8.4" z3
fi

mkdir -p "z3/build" && pushd "z3/build"
if [ ! -d CMakeFiles ]; then
	cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX \
		 -DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
		 || clean_and_exit 1 "git"
fi

make && make install
popd
