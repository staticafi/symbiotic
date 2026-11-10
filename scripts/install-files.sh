#!/bin/bash

# Install scripts, headers, properties and function models (top-level CMakeLists.txt)
if [ ! -d CMakeFiles ]; then
	cmake . \
		-DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
		-DCMAKE_INSTALL_PREFIX=$PREFIX \
		-DCMAKE_INSTALL_LIBDIR:PATH=$LLVM_PREFIX/lib \
		|| exitmsg "Configuring files installation"
fi

(build && make install) || exitmsg "Installing files"

PHASE="precompiling function models"
if [ "$PRECOMPILE_BITCODE" = "yes" ]; then
	# precompile bitcode files
	CPPFLAGS="-I$LLVM_BUILD_PATH/lib/clang/$LLVM_VERSION/include/ -I/usr/include $CPPFLAGS" scripts/precompile_bitcode_files.sh\
        || exitmsg "Failed compiling function models (Symbotic should work, though, so you can skip this step)"
fi
