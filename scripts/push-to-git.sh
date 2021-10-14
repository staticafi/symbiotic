#!/bin/bash

get_klee_dependencies()
{
	KLEE_BIN="$1"
	LIBS=$(get_external_library $KLEE_BIN libstdc++)
	LIBS="$LIBS $(get_external_library $KLEE_BIN tinfo)"
	LIBS="$LIBS $(get_external_library $KLEE_BIN libgomp)"
	# FIXME: remove once we build/download our z3
	LIBS="$LIBS $(get_any_library $KLEE_BIN libz3)"
	LIBS="$LIBS $(get_any_library $KLEE_BIN libstp)"

	echo $LIBS
}

get_nidhugg_dependencies()
{
	KLEE_BIN="$1"
	LIBS=$(get_external_library $KLEE_BIN libstdc++)
	LIBS="$LIBS $(get_external_library $KLEE_BIN libboost)"

	echo $LIBS
}

######################################################################
#  create distribution
######################################################################
# copy license
cp LICENSE.txt $PREFIX/
cp README.md $PREFIX/

# copy the symbiotic python module
cp -r $SRCDIR/lib/symbioticpy $PREFIX/lib || exit 1

# copy dependencies
DEPENDENCIES=""
if [ "$FULL_ARCHIVE" = "yes" ]; then
	if [ "$BUILD_KLEE" = "yes" ]; then
		DEPS=`get_klee_dependencies $LLVM_PREFIX/bin/klee`
		if [ ! -z "$DEPS" ]; then
			for D in $DEPS; do
				DEST="$PREFIX/lib/$(basename $D)"
				cmp "$D" "$DEST" || cp -u "$D" "$DEST"
				DEPENDENCIES="$DEST $DEPENDENCIES"
			done
		fi
	fi
	if [ "$BUILD_WITCH_KLEE" = "yes" ]; then
		DEPS=`get_klee_dependencies $LLVM_PREFIX/witch-klee/bin/witch-klee`
		if [ ! -z "$DEPS" ]; then
			for D in $DEPS; do
				DEST="$PREFIX/lib/$(basename $D)"
				cmp "$D" "$DEST" || cp -u "$D" "$DEST"
				DEPENDENCIES="$DEST $DEPENDENCIES"
			done
		fi
	fi
	if [ "$BUILD_NIDHUGG" = "yes" ]; then
		DEPS=`get_nidhugg_dependencies $LLVM_PREFIX/bin/nidhugg`
		if [ ! -z "$DEPS" ]; then
			for D in $DEPS; do
				DEST="$PREFIX/lib/$(basename $D)"
				cmp "$D" "$DEST" || cp -u "$D" "$DEST"
				DEPENDENCIES="$DEST $DEPENDENCIES"
			done
		fi
	fi
fi

cd $PREFIX || exitmsg "Whoot? prefix directory not found! This is a BUG, sir..."

BINARIES="$LLVM_PREFIX/bin/sbt-slicer \
	  $LLVM_PREFIX/bin/llvm-slicer \
	  $LLVM_PREFIX/bin/sbt-instr"

for B in $LLVM_TOOLS; do
	BINARIES="$LLVM_PREFIX/bin/${B} $BINARIES"
done

if [ ${BUILD_KLEE} = "yes" ];  then
	BINARIES="$BINARIES $LLVM_PREFIX/bin/klee"
fi

if [ ${BUILD_WITCH_KLEE} = "yes" ];  then
	BINARIES="$BINARIES $LLVM_PREFIX/witch-klee/bin/witch-klee"
fi

SCRIPTS=
if [ "${BUILD_PREDATOR}" = "yes" ];  then
	SCRIPTS="$SCRIPTS $LLVM_PREFIX/bin/predator_wrapper.py"
	SCRIPTS="$SCRIPTS $LLVM_PREFIX/bin/slllvm*"
	SCRIPTS="$SCRIPTS $LLVM_PREFIX/predator/*.sh"
	LIBRARIES="$LIBRARIES $LLVM_PREFIX/predator/lib/*.so"
fi

if [ "${BUILD_LLVM2C}" = "yes" ];  then
	BINARIES="$BINARIES $LLVM_PREFIX/bin/llvm2c"
fi
	LIBRARIES="\
		$LLVM_PREFIX/lib/libdgllvmdg.so $LLVM_PREFIX/lib/libdgllvmpta.so \
		$LLVM_PREFIX/lib/libdgdda.so $LLVM_PREFIX/lib/libdganalysis.so \
		$LLVM_PREFIX/lib/libdgpta.so $LLVM_PREFIX/lib/libdgllvmdda.so \
		$LLVM_PREFIX/lib/libdgcda.so $LLVM_PREFIX/lib/libdgllvmcda.so \
		$LLVM_PREFIX/lib/libdgllvmthreadregions.so\
		$LLVM_PREFIX/lib/libdgllvmforkjoin.so\
		$LLVM_PREFIX/lib/libdgllvmpta.so\
		$LLVM_PREFIX/lib/libdgllvmcda.so \
		$LLVM_PREFIX/lib/libdgllvmslicer.so \
		$LLVM_PREFIX/lib/LLVMsbt.so \
		$LLVM_PREFIX/lib/libdgPointsToPlugin.so \
		$LLVM_PREFIX/lib/libPredatorPlugin.so \
		$LLVM_PREFIX/lib/libRangeAnalysisPlugin.so \
		$LLVM_PREFIX/lib/libCheckNSWPlugin.so \
		$LLVM_PREFIX/lib/libInfiniteLoopsPlugin.so \
		$LLVM_PREFIX/lib/libLLVMPointsToPlugin.so \
		$LLVM_PREFIX/lib/libValueRelationsPlugin.so"

BCFILES=""
if [ "${BUILD_KLEE}" = "yes" ];  then
	BCFILES="${BCFILES} \
		$LLVM_PREFIX/lib/klee/runtime/*.bc* \
		$LLVM_PREFIX/lib32/klee/runtime/*.bc* \
		$LLVM_PREFIX/lib/*.bc* \
		$LLVM_PREFIX/lib32/*.bc*"
fi
if [ "${BUILD_WITCH_KLEE}" = "yes" ];  then
	BCFILES="${BCFILES} \
		$LLVM_PREFIX/witch-klee/lib/klee/runtime/*.bc* \
		$LLVM_PREFIX/witch-klee/lib32/klee/runtime/*.bc* \
		$LLVM_PREFIX/witch-klee/lib/*.bc* \
		$LLVM_PREFIX/witch-klee/lib32/*.bc*"
fi
if [ "${BUILD_NIDHUGG}" = "yes" ];  then
	BINARIES="$BINARIES $LLVM_PREFIX/bin/nidhugg"
fi

SCRIPTS=
if [ ${BUILD_PREDATOR} = "yes" ];  then
	SCRIPTS="$SCRIPTS $LLVM_PREFIX/bin/predator_wrapper.py"
	SCRIPTS="$SCRIPTS $LLVM_PREFIX/bin/slllvm*"
	SCRIPTS="$SCRIPTS $LLVM_PREFIX/predator/*.sh"
	LIBRARIES="$LIBRARIES $LLVM_PREFIX/predator/lib/*.so"
fi

	INSTR="$LLVM_PREFIX/share/sbt-instrumentation/"

if [ "$BUILD_STP" = "yes" ]; then
	LIBRARIES="$LIBRARIES $PREFIX/lib/libminisat*.so"
fi

if [ "$BUILD_Z3" = "yes" ]; then
	LIBRARIES="$LIBRARIES $PREFIX/lib/libz3*.so*"
fi

#strip binaries, it will save us 500 MB!
for B in $BINARIES $LIBRARIES; do
	echo "Stripping $B"
	test -w $B && strip $B
done

git init
git add \
	$BINARIES \
	$BCFILES \
	$SCRIPTS \
	$LIBRARIES \
	$DEPENDENCIES \
	$INSTR\
	bin/symbiotic \
	bin/kleetester.py \
	bin/gen-c \
	include/symbiotic.h \
	include/symbiotic-size_t.h \
	$(find lib -name '*.c')\
	$(find . -name '*.bc')\
	properties/* \
	$(find lib/symbioticpy/symbiotic -name '*.py')\
	LICENSE.txt README.md
	#$LLVM_PREFIX/include/stddef.h \

git commit -m "Create Symbiotic distribution `date`" || true

# remove unnecessary files
# git clean -xdf

if [ "x$ARCHIVE" = "xyes" ]; then
	git archive --prefix "symbiotic/" -o symbiotic.zip -9 --format zip HEAD
	mv symbiotic.zip ..
fi
