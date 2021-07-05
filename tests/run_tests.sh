#!/bin/sh

# run symbiotic from the scripts/ preferably, so that the tests use
# the current (developement) version
export PATH=$PWD/../scripts:$PWD/../install/bin/:$PATH
export ASAN_OPTIONS=detect_leaks=0

# GitHub Actions defines this variable
if [ -n "$CI" ]; then
  color='--color'
fi

./test_runner.py "$color" ./*.set
./test_runner.py "$color" --32 ./*.set
