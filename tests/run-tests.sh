#!/bin/sh

TOTAL_NUM=0
FAILED_NUM=0

fail()
{
	FAILED_NUM=$(($FAILED_NUM + 1))

	while [ $# -gt 0 ]; do
		echo "$1"
		shift
	done
}

errmsg()
{
	while [ $# -gt 0 ]; do
		echo "$1" > /dev/stderr
		shift
	done

	exit 1
}

DIR=`dirname $0`
SYMBIOTIC=`readlink -f $DIR/../install/bin/symbiotic`

if [ ! -f $SYMBIOTIC ]; then
	errmsg "Couldn't find compiled symbiotic"
fi

if [ $# -ne 1 ]; then
	errmsg "Usage: $0 tests.txt"
fi

TESTS=`readlink -f $1`
cat $TESTS | while read DESIRED ARGS; do
	TOTAL_NUM=$(($TOTAL_NUM + 1))
	OUTPUT=`$SYMBIOTIC $ARGS 2>&1`
	echo -n "$ARGS ... "

	if [ "$DESIRED" = "FALSE" ]; then
		echo "$OUTPUT" | grep -q "RESULT: false" || fail "FAILED"
		echo "OK"
	elif [ "$DESIRED" = "TRUE" ]; then
		echo "$OUTPUT" | grep -q "RESULT: true" || fail "FAILED"
		echo "OK"
	else
		errmsg  "Wrong syntax in tests.txt"
	fi
done

if [ $FAILED_NUM -ne 0 ]; then
	echo " ------------------------------------ "
	echo "$FAILED_NUM of $TOTAL_NUM tests failed"
	echo " ------------------------------------ "
	exit 1
fi
