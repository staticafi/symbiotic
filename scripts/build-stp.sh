#!/bin/bash

# minisat
git_clone_or_pull git://github.com/stp/minisat.git minisat
pushd minisat
mkdir -p build
cd build || exitmsg "error"

# use our zlib, if we compiled it
ZLIB_FLAGS=
if [ -d $ABS_RUNDIR/zlib ]; then
	ZLIB_FLAGS="-DZLIB_LIBRARY=-L${PREFIX}/lib;-lz"
	ZLIB_FLAGS="$ZLIB_FLAGS -DZLIB_INCLUDE_DIR=$PREFIX/include"
fi

if [ ! -d CMakeFiles ]; then
	cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX \
		  -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
			 -DSTATICCOMPILE=ON $ZLIB_FLAGS
fi

(make "$OPTS" && make install) || exitmsg  "Building and installing minisat"
popd

# STP
git_clone_or_pull git://github.com/stp/stp.git stp
cd stp || exitmsg "Cloning failed"
if [ ! -d CMakeFiles ]; then
	cmake . -DCMAKE_INSTALL_PREFIX=$PREFIX \
		-DCMAKE_INSTALL_LIBDIR:PATH=lib \
		-DSTP_TIMESTAMPS:BOOL="OFF" \
		-DCMAKE_CXX_FLAGS_RELEASE=-O2 \
		-DCMAKE_C_FLAGS_RELEASE=-O2 \
		-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
		-DBUILD_SHARED_LIBS:BOOL=OFF \
		-DENABLE_PYTHON_INTERFACE:BOOL=OFF || clean_and_exit 1 "git"
fi

(build "OPTIMIZE=-O2 CFLAGS_M32=install" && make install) || exitmsg  "Building and installing STP"
cd -
