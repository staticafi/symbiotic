INSTR="LLVMInstrumentation/"
PREFIX="install"
CLANG=$PREFIX/bin/clang

set -e

if [ ! -f "scripts/`basename $0`" ]; then
 echo "Must be run in Symbiotic's root directory"
 exit 1
fi

FILES=
for F in `find $INSTR/instrumentations/ -name '*.c'`; do
	NAME=`basename $F`
	OUT=${NAME%*.c}.bc
	FILES="$FILES lib/$OUT"
	$CLANG -emit-llvm -c $F -o $PREFIX/lib/$OUT $CPPFLAGS $CFLAGS $LDFLAGS

	FILES="$FILES lib32/$OUT"
	$CLANG -emit-llvm -c $F -m32 -o $PREFIX/lib32/$OUT $CPPFLAGS $CFLAGS $LDFLAGS
done

echo "To add precompiled files to distribution, run this command from install/ folder:"
echo "git add $FILES"
