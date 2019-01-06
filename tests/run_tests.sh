#!/bin/sh

export PATH=$(pwd)/../scripts:$PATH
benchexec symbiotic-tests.xml
