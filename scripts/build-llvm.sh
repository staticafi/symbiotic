#!/bin/bash

# Build LLVM (unless with-llvm=path was given) and copy the LLVM tools
# that Symbiotic needs into the installation prefix.

build_llvm()
{
    PHASE="building LLVM"
	URL=http://llvm.org/releases/${LLVM_VERSION}/
	CLANG_NAME="cfe"
	# UFFF, for some stupid reason this only release has a different url, the rest (even newer use the previous one)
	if [ ${LLVM_VERSION} = "8.0.1" ]; then
		URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-8.0.1/
	elif [ ${LLVM_MAJOR_VERSION} -ge 9 ]; then
		URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_VERSION}/
	        CLANG_NAME="clang"
	fi

	LLVM_URL=${URL}/llvm-${LLVM_VERSION}.src.tar.xz
	CLANG_URL=${URL}/$CLANG_NAME-${LLVM_VERSION}.src.tar.xz
	RT_URL=${URL}/compiler-rt-${LLVM_VERSION}.src.tar.xz

	if [ ! -d "llvm-${LLVM_VERSION}" ]; then
		$GET $LLVM_URL || exitmsg "Failed downloading LLVM"
		$GET $CLANG_URL || exitmsg "Failed downloading Clang"
		$GET $RT_URL || exitmsg "Failed downloading sanitizers"

		tar -xf llvm-${LLVM_VERSION}.src.tar.xz || exitmsg "Failed unpacking LLVM"
		tar -xf $CLANG_NAME-${LLVM_VERSION}.src.tar.xz || exitmsg "Failed unpacking Clang"
		tar -xf compiler-rt-${LLVM_VERSION}.src.tar.xz || exitmsg "Failed unpacking sanitizers"

                # rename llvm folder
                mv llvm-${LLVM_VERSION}.src llvm-${LLVM_VERSION}
		# move clang to llvm/tools and rename to clang
		mv $CLANG_NAME-${LLVM_VERSION}.src llvm-${LLVM_VERSION}/tools/clang
		mv compiler-rt-${LLVM_VERSION}.src llvm-${LLVM_VERSION}/tools/clang/runtime/compiler-rt

		# apply our patches for LLVM/Clang
		if [ "$LLVM_VERSION" = "4.0.1" ]; then
			pushd llvm-${LLVM_VERSION}/tools/clang
			patch -p0 --dry-run < $ABS_SRCDIR/patches/force_lifetime_markers.patch || exitmsg "Patching LLVM"
			patch -p0 < $ABS_SRCDIR/patches/force_lifetime_markers.patch || exitmsg "Patching LLVM"
			popd
		fi

		rm -f llvm-${LLVM_VERSION}.src.tar.xz &>/dev/null || exitmsg "Removing downloaded archive"
		rm -f $CLANG_NAME-${LLVM_VERSION}.src.tar.xz &>/dev/null || exitmsg "Removing downloaded archive"
		rm -f compiler-rt-${LLVM_VERSION}.src.tar.xz &>/dev/null || exitmsg "Removing downloaded archive"
	fi
	if [ $WITH_LLVMCBE = "yes" ]; then
		pushd ${ABS_SRCDIR}/llvm-${LLVM_VERSION}/projects || exitmsg "Invalid directory"
		git_clone_or_pull https://github.com/JuliaComputing/llvm-cbe
		popd
	fi

	mkdir -p llvm-${LLVM_VERSION}/build
	pushd llvm-${LLVM_VERSION}/build

	# configure llvm
	if [ ! -d CMakeFiles ]; then
		EXTRA_FLAGS=
		if [ "x${BUILD_TYPE}" = "xDebug" ]; then
			EXTRA_FLAGS=-DLLVM_ENABLE_ASSERTIONS=ON
		fi

		if [ $LLVM_MAJOR_VERSION -ge 9 ]; then
			EXTRA_FLAGS="$EXTRA_FLAGS -DLLVM_INCLUDE_TESTS=ON"
		else
			EXTRA_FLAGS="$EXTRA_FLAGS -DLLVM_INCLUDE_TESTS=OFF"
		fi
        if [ "$LLVM_DYLIB" = "on" ]; then
			EXTRA_FLAGS="$EXTRA_FLAGS -DLLVM_LINK_DYLIB=on"
        fi
		cmake .. \
			-DCMAKE_BUILD_TYPE=${BUILD_TYPE}\
			-DLLVM_INCLUDE_EXAMPLES=OFF \
			-DLLVM_INCLUDE_DOCS=OFF \
                        -DLLVM_INCLUDE_BENCHMARKS=OFF \
			-DLLVM_BUILD_TESTS=OFF\
			-DLLVM_BUILD_TESTS=OFF\
			-DLLVM_ENABLE_TIMESTAMPS=OFF \
			-DLLVM_TARGETS_TO_BUILD="X86" \
			-DLLVM_ENABLE_PIC=ON \
			${EXTRA_FLAGS} \
			 || clean_and_exit
	fi

	# build llvm
	ONLY_TOOLS="$LLVM_TOOLS" build
	# copy the generated stddef.h due to compilation of instrumentation libraries
	#mkdir -p "$LLVM_PREFIX/include"
	#cp "lib/clang/${LLVM_VERSION}/include/stddef.h" "$LLVM_PREFIX/include" || exitmsg "Copying stddef.h"

	popd
}

if [ -z "$WITH_LLVM" ]; then
	build_llvm
	LLVM_LOCATION=llvm-${LLVM_VERSION}/build
else
	LLVM_LOCATION=$WITH_LLVM
fi

# we need these binaries in symbiotic, copy them
# to instalation prefix there
mkdir -p $LLVM_PREFIX/bin
for B in $LLVM_TOOLS; do
	cp $LLVM_LOCATION/bin/${B} $LLVM_PREFIX/bin/${B} || exitmsg "Failed copying LLVM executables"
done
