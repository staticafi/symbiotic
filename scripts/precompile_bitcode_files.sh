INSTR="sbt-instrumentation/"
PREFIX="install"

set -e

if [ ! -f "scripts/`basename $0`" ]; then
 echo "Must be run in Symbiotic's root directory"
 exit 1
fi

FILES=
ORIG_CPPFLAGS="$CPPFLAGS"
for LLVM in $PREFIX/llvm-*; do
	CLANG=$LLVM/bin/clang
	LLVM_VERSION=${LLVM#*llvm-*}
	INCLUDE_DIR="llvm-${LLVM_VERSION}/build/lib/clang/${LLVM_VERSION}/include/"
	CPPFLAGS="-I ${INCLUDE_DIR} $ORIG_CPPFLAGS"
	for F in `find $INSTR/instrumentations/ -name '*.c'`; do
		NAME=`basename $F`
		OUT=${NAME%*.c}.bc
		mkdir -p "$LLVM/lib" "$LLVM/lib32"

		FILES="$FILES ${LLVM#install/}/lib/$OUT"
		$CLANG $CPPFLAGS -O3 -emit-llvm -c $F -o $LLVM/lib/$OUT $CPPFLAGS $CFLAGS $LDFLAGS

		FILES="$FILES ${LLVM#install/}/lib32/$OUT"
		$CLANG $CPPFLAGS -O3 -emit-llvm -c $F -m32 -o $LLVM/lib32/$OUT $CPPFLAGS $CFLAGS $LDFLAGS
	done
done

echo "To add precompiled files to distribution, run this command from install/ folder:"
echo "git add $FILES"
