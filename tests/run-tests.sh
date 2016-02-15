#!/bin/bash

fail()
{
	while [ $# -gt 0 ]; do
		echo "$1" > /dev/stderr
		shift
	done

	exit 1
}

DIR=`dirname $0`
SYMBIOTIC=`readlink -f $DIR/../install/symbiotic`

if [ ! -f $SYMBIOTIC ]; then
	fail "Couldn't find compiled symbiotic"
fi

cat `dirname $0`/tests.txt | while read DESIRED FILE; do
	TOTAL_NUM=$[$TOTAL_NUM + 1]
	OUTPUT=`$SYMBIOTIC $FILE 2>&1`

	if [ "$DESIRED" = "FALSE" ]; then
		echo -n "$FILE ... "
		echo "$OUTPUT" | grep -q FALSE || fail "FAILED"
		echo "OK"
	elif [ "$DESIRED" = "TRUE" ]; then
		echo -n "$FILE ... "
		echo "$OUTPUT" | grep -q TRUE || fail "FAILED"
		echo "OK"
	else
		fail  "Wrong syntax in tests.txt"
	fi
done
