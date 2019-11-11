#!/bin/sh

export PATH=$(pwd)/../install/bin/:$PATH
benchexec --read-only-dir / --read-only-dir /home --full-access-dir $(pwd)/.. --container symbiotic-tests.xml $@
