#!/bin/sh

export PATH=$(pwd)/../install/bin/:$PATH
benchexec symbiotic-tests.xml $@
