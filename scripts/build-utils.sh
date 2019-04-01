#!/bin/sh

set -x

#https://unix.stackexchange.com/a/48550
set -E
trap '[ "$?" -ne 77 ] || exit 77' ERR

exitmsg()
{
	echo "$1" >/dev/stderr
	exit 77
}

abspath() {
	if which realpath &>/dev/null; then
		realpath "$1" || exitmsg "Can not get absolute path of $1";
	elif [[ "$OSTYPE" == *darwin* ]]; then
		greadlink -f "$1" || exitmsg "Can not get absolute path of $1";
	else
		readlink -f "$1" || exitmsg "Can not get absolute path of $1";
	fi
}

download_tar()
{
	$GET "$1" || exit 1
	BASENAME="`basename $1`"
	tar xf "$BASENAME" || exit 1
	rm -f "BASENAME"
}

download_zip()
{
	$GET "$1" || exit 1
	BASENAME="`basename $1`"
	unzip "$BASENAME" || exit 1
	rm -f "BASENAME"
}

clean_and_exit()
{
	CODE="$1"

	if [ "$2" = "git" ]; then
		git clean -xdf
	else
		rm -rf *
	fi

	exit $CODE
}

build()
{
	make $OPTS CFLAGS="$CFLAGS" CPPFLAGS="$CPPFLAGS" LDFLAGS="$LDFLAGS" $@ || exit 1
	return 0
}

git_clone_or_pull()
{

	REPO="$1"
	FOLDER="$2"
	shift;shift

	if [ -d "$FOLDER" ]; then
		if [ "x$UPDATE" = "x1" ]; then
			cd $FOLDER && git pull && cd -
		fi
	else
		git clone $REPO $FOLDER $@
	fi
}

git_submodule_init()
{
	cd "$SRCDIR"

	git submodule init || exitmsg "submodule init failed"
	git submodule update || exitmsg "submodule update failed"

	cd -
}

GET="curl -LRO"

check_z3() {
	echo "#include <z3.h>" | gcc - -E &>/dev/null
}

check_zlib() {
	echo "#include <zlib.h>" | gcc - -E &>/dev/null
}

check_32_bit() {
	echo "#include <stdint.h>" | gcc - -E -m32 &>/dev/null
}

check_tcmalloc() {
	echo "#include <gperftools/malloc_extension.h>" | gcc - -E &>/dev/null
}

check_gtest() {
	echo "#include <gtest/gtest.h>" | gcc - -E &>/dev/null
}

get_external_library()
{
	LIB="$(ldd $1 | grep $2 | cut -d ' ' -f 3)"
	# if this is not library in our installation, return it
	if [ "$LIB" != "not" ]; then # not found
		if echo "$LIB" | grep -v -q "$PREFIX"; then
			echo "$LIB"
		fi
	else
		exitmsg "Did not find library matching $2"
	fi
}

get_any_library()
{
	LIB="$(ldd $1 | grep $2 | cut -d ' ' -f 3)"
	# if this is not library in our installation, return it
	if [ "$LIB" != "not" ]; then # not found
		echo "$LIB"
	else
		exitmsg "Did not find library matching $2"
	fi
}



