#!/bin/bash

git_clone_or_pull https://github.com/madler/zlib
cd zlib || exitmsg "error"

if [ ! -d CMakeFiles ]; then
	cmake -DCMAKE_INSTALL_PREFIX=$PREFIX
fi

(make "$OPTS" && make install) || exitmsg  "Building and installing ZLib"

cd -
