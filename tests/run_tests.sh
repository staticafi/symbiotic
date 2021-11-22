#!/bin/sh

set -ex

# run symbiotic from the scripts/ preferably, so that the tests use
# the current (development) version
PATH="$PWD/../scripts:$PWD/../install/bin/:$PATH"

# use LLVM tools linked to symbiotic's install directory
ENV_CMD="$(symbiotic --debug=all --dump-env-cmd)"
eval "$ENV_CMD"

# sanitizer settings
export ASAN_OPTIONS=detect_leaks=0
export UBSAN_OPTIONS=print_stacktrace=1

# clear the environment
# (We don't want to have ASAN & friends baked into the verified bitcode.)
unset CFLAGS
unset CXXFLAGS
unset CPPFLAGS
unset LDFLAGS

# GitHub Actions define this variable
if [ -n "$CI" ]; then
  ci_args='--color --with-integrity-check'
fi

./test_runner.py "$@" $ci_args ./*.set
./test_runner.py "$@" $ci_args --32 ./*.set
