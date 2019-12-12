#!/bin/sh

set -e

cd $(dirname $0)

if which apt-get &>/dev/null; then
	sudo ./install-ubuntu.sh
elif which pacman &>/dev/null; then
	sudo ./install-arch.sh
elif which dnf &>/dev/null; then
	sudo ./install-fedora.sh
elif which yum &>/dev/null; then
	sudo ./install-fedora.sh
fi
