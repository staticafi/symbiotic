#!/bin/sh

# run symbiotic from the scripts/ preferably, so that the tests use
# the current (development) version
PATH="$PWD/../scripts:$PWD/../install/bin/:$PATH"

# use llvm tools linked to symbiotic's install directory
# FIXME: this is a really ugly hack
LLVM_VERSION="$(symbiotic --version | grep 'LLVM' | cut -d' ' -f3)"
export PATH="$PWD/../install/llvm-$LLVM_VERSION/bin:$PATH"

# sanitizer settings
export ASAN_OPTIONS=detect_leaks=0

# GitHub Actions defines this variable
if [ -n "$CI" ]; then
  color='--color'
fi

./test_runner.py $color ./*.set
./test_runner.py $color --32 ./*.set
