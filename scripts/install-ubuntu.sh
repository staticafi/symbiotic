#!/bin/sh

set -e

apt-get update

PACKAGES="curl wget rsync make cmake unzip gcc-multilib xz-utils python zlib1g-dev"

# install clang if there is not suitable compiler
if ! which g++ &>/dev/null; then
	if ! which clang++ &>/dev/null; then
		PACKAGES="$PACKAGES clang"
	fi
fi

INSTALL_Z3="N"
INSTALL_LLVM="N"

# Ask for these as the user may have his/her own build
if !  dpkg -l | grep -q libz3-dev; then
	echo "Z3 not found, should I install it? [y/N]"
	read INSTALL_Z3
fi

if !  dpkg -l | grep -q 'llvm.*-dev'; then
	echo "LLVM not found, should I install it? [y/N]"
	read INSTALL_LLVM
fi

if [ "$INSTALL_Z3" = "y" ]; then
	PACKAGES="$PACKAGES libz3-dev"
fi
if [ "$INSTALL_LLVM" = "y" ]; then
	PACKAGES="$PACKAGES llvm"
fi

apt-get install $PACKAGES
