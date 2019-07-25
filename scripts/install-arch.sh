#!/bin/sh

set -e

PACKAGES="curl wget rsync make cmake unzip lib32-gcc-libs xz"

# install clang if there is not suitable compiler
if ! which g++ &>/dev/null; then
	if ! which clang++ &>/dev/null; then
		PACKAGES="$PACKAGES clang"
	fi
fi

INSTALL_Z3="N"
INSTALL_LLVM="N"

# Ask for these as the user may have his/her own build
if ! pacman -Qqe | grep -q z3; then
	echo "Z3 not found, should I install it? [y/N]"
	read INSTALL_Z3
fi

if ! pacman -Qqe | grep -q llvm; then
	echo "LLVM not found, should I install it? [y/N]"
	read INSTALL_LLVM
fi

if [ "$INSTALL_Z3" = "y" ]; then
	PACKAGES="$PACKAGES z3"
fi
if [ "$INSTALL_LLVM" = "y" ]; then
	PACKAGES="$PACKAGES llvm"
fi

pacman -S $PACKAGES
