#!/usr/bin/env bash
set -e

LLVMLITE_DIR=llvmlite
SLOWBEAST_DIR=slowbeast
MATHSAT5_DIR=mathsat
CADICAL_DIR=cadical
MPFR_DIR=mpfr
BITWUZLA_DIR=bitwuzla
GMP_DIR=gmp

if [ ! -d ${LLVMLITE_DIR} ];then
    git clone https://github.com/mchalupa/llvmlite
fi
if [ ! -d ${SLOWBEAST_DIR} ];then
    # git clone https://gitlab.com/mchalupa/slowbeast
    # git clone https://gitlab.fi.muni.cz/xkumor/slowbeastcse.git slowbeast
    # git clone -b kristian_kumor_cse https://gitlab.com/jonasmartin/slowbeast
    git clone -b svcomp27 https://gitlab.com/JindraSe/slowbeast.git
fi
if [ ! -d ${MATHSAT5_DIR} ]; then
    wget https://mathsat.fbk.eu/release/mathsat-5.6.19-linux-x86_64.tar.gz
    tar -xzf mathsat-5.6.19-linux-x86_64.tar.gz
    mv mathsat-5.6.19-linux-x86_64 ${MATHSAT5_DIR}
    rm mathsat-5.6.19-linux-x86_64.tar.gz
fi

# necessary for bitwuzla
if [ ! -d ${GMP_DIR} ]; then
    wget https://gmplib.org/download/gmp/gmp-6.3.0.tar.xz
    tar -xf gmp-6.3.0.tar.xz
    mv gmp-6.3.0 ${GMP_DIR}
    rm gmp-6.3.0.tar.xz
fi

if [ ! -d ${CADICAL_DIR} ]; then
    git clone https://github.com/arminbiere/cadical.git
fi

if [ ! -d ${MPFR_DIR} ]; then
    wget https://www.mpfr.org/mpfr-4.2.2/mpfr-4.2.2.tar.xz
    tar -xf mpfr-4.2.2.tar.xz
    mv mpfr-4.2.2 ${MPFR_DIR}
    rm mpfr-4.2.2.tar.xz
fi

if [ ! -d ${BITWUZLA_DIR} ]; then
    git clone -b 0.9.1 https://github.com/bitwuzla/bitwuzla.git
fi

if [ -e ${LLVMLITE_DIR}/build ];then rm -r ${LLVMLITE_DIR}/build ; fi
if [ -e ${SLOWBEAST_DIR}/build ];then rm -r ${SLOWBEAST_DIR}/build ; fi
if [ -e ${SLOWBEAST_DIR}/dist ];then rm -r ${SLOWBEAST_DIR}/dist ; fi
if [ -e ${MATHSAT5_DIR}/build ];then rm -r ${MATHSAT5_DIR}/build ; fi
if [ -e ${CADICAL_DIR}/build ];then rm -r ${CADICAL_DIR}/build ; fi

pushd ${LLVMLITE_DIR}
python3 setup.py build
popd

pushd ${MATHSAT5_DIR}/python
python3 setup.py build
cp build/lib.linux-x86_64-3.10/_mathsat.cpython-310-x86_64-linux-gnu.so .
popd

pushd ${CADICAL_DIR}
./configure
make
cp build/libcadical.a /usr/lib
popd

pushd ${GMP_DIR}
./configure --enable-shared --enable-cxx
make -j4
make install
ldconfig
popd

pushd ${MPFR_DIR}
./configure --enable-shared --with-gmp=/usr/local
make -j4
make install
ldconfig
popd

pushd ${BITWUZLA_DIR}
GMP_HOME=/usr MPFR_HOME=/usr/local ./configure.py
pushd build
ninja install
popd
pip install .
popd

pushd ${SLOWBEAST_DIR}
# the clang python package loads libclang-14.so by name, bundle it
cp -L /usr/lib/x86_64-linux-gnu/libclang-14.so.1 libclang-14.so
pyinstaller -p ../${LLVMLITE_DIR} -p ../${MATHSAT5_DIR}/python \
    --collect-binaries z3 \
    --collect-submodules clang \
    --add-binary libclang-14.so:. sb
popd
