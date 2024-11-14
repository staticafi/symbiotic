#!/usr/bin/env bash

LLVMLITE_DIR=llvmlite
SLOWBEAST_DIR=slowbeast

if [ ! -d ${LLVMLITE_DIR} ];then
    git clone https://github.com/mchalupa/llvmlite
fi
if [ ! -d ${SLOWBEAST_DIR} ];then
    # git clone https://gitlab.com/mchalupa/slowbeast
    # git clone https://gitlab.fi.muni.cz/xkumor/slowbeastcse.git slowbeast
    git clone -b remove_numpy_float https://gitlab.com/jonasmartin/slowbeast
fi

if [ -e ${LLVMLITE_DIR}/build ];then rm -r ${LLVMLITE_DIR}/build ; fi
if [ -e ${SLOWBEAST_DIR}/build ];then rm -r ${SLOWBEAST_DIR}/build ; fi
if [ -e ${SLOWBEAST_DIR}/dist ];then rm -r ${SLOWBEAST_DIR}/dist ; fi

pushd ${LLVMLITE_DIR}
python3 setup.py build
popd

pushd ${SLOWBEAST_DIR}
pyinstaller -p ../${LLVMLITE_DIR} --collect-binaries z3 sb
popd
