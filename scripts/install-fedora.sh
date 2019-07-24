#!/bin/sh

set -e

# install clang if there is not suitable compiler
if ! which g++ &>/dev/null; then
	if ! which clang++ &>/dev/null; then
		dnf install clang
	fi
fi


dnf install curl wget rsync make cmake unzip tar patch glibc-devel.i686
