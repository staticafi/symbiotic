#!/bin/sh

set -e

cd $(dirname $0)

SUDO=
if [ which sudo &>/dev/null ]; then
	SUDO=sudo
else
	echo "Need root privileges:"
	SUDO="su -c"
fi

if apt-get -v &>/dev/null; then
	$SUDO ./install-ubuntu.sh
elif pacman --version &>/dev/null; then
	$SUDO ./install-arch.sh
elif dnf --version &>/dev/null; then
	$SUDO ./install-fedora.sh
elif which --version &>/dev/null; then
	$SUDO ./install-fedora.sh
fi
