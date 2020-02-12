#!/bin/sh

set -e

PACKAGES="curl wget rsync make cmake unzip lib32-glibc xz python"

# install clang if there is not suitable compiler
if ! which g++ &>/dev/null; then
	if ! which clang++ &>/dev/null; then
		PACKAGES="$PACKAGES clang"
	fi
fi

INSTALL_Z3="N"
INSTALL_LLVM="N"
INSTALL_SQLITE="N"
INSTALL_ZLIB="N"

# Ask for these as the user may have his/her own build
if ! pacman -Qqe | grep -q z3; then
	echo "Z3 not found, should I install it? [y/N]"
	read INSTALL_Z3
fi

if ! pacman -Qqe | grep -q llvm; then
	echo "LLVM not found, should I install it? [y/N]"
	read INSTALL_LLVM
fi

if ! pacman -Qqe | grep -q sqlite; then
	echo "SQLite not found, should I install it? [y/N]"
	read INSTALL_SQLITE
fi

if ! pacman -Qqe | grep -q zlib; then
	echo "zlib not found, should I install it? [y/N]"
	read INSTALL_ZLIB
fi

if [ "$INSTALL_Z3" = "y" ]; then
	PACKAGES="$PACKAGES z3"
fi
if [ "$INSTALL_LLVM" = "y" ]; then
	PACKAGES="$PACKAGES llvm"
fi
if [ "$INSTALL_SQLITE" = "y" ]; then
	PACKAGES="$PACKAGES libsqlite3"
fi
if [ "$INSTALL_ZLIB" = "y" ]; then
	PACKAGES="$PACKAGES zlib"
fi

pacman -S $PACKAGES
