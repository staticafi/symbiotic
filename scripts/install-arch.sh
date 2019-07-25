#!/bin/sh

set -e

# install clang if there is not suitable compiler
if ! which g++ &>/dev/null; then
	if ! which clang++ &>/dev/null; then
		pacman -S install clang
	fi
fi


pacman -S curl wget rsync make cmake unzip lib32-gcc-libs xz
