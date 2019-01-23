#!/bin/sh

set -e

apt-get update

# install clang if there is not suitable compiler
if ! which g++ &>/dev/null; then
	if ! which clang++ &>/dev/null; then
		apt-get install clang
	fi
fi

apt-get install curl wget rsync make cmake unzip gcc-multilib
