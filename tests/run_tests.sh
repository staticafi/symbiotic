#!/bin/sh

# run symbiotic from the scripts/ preferably, so that the tests use
# the current (developement) version
export PATH=$(pwd)/../scripts:$(pwd)/../install/bin/:$PATH
export ASAN_OPTIONS=detect_leaks=0
benchexec --read-only-dir / --read-only-dir /home --full-access-dir $(pwd)/.. --container symbiotic-tests.xml $@
