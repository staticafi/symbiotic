FROM ubuntu:22.04

RUN set -e

# Setup time-zone so that the build does not hang
# on configuring the tzdata package.
# I work in Brno, that is basically Vienna-North :)
# (definitely its closer than Prague)
ENV TZ=Europe/Vienna
RUN ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime
RUN echo "$TZ" > /etc/timezone

# Install packages
RUN apt-get update
RUN apt-get install -y git cmake make llvm zlib1g-dev clang g++ python3 curl wget rsync make cmake unzip gcc-multilib xz-utils libz3-dev libsqlite3-dev python3-pip libboost-all-dev libgmp-dev ninja-build build-essential m4 pkg-config

RUN pip3 install z3-solver
RUN pip3 install pyinstaller
RUN pip3 install numpy
RUN pip3 install setuptools
RUN pip3 install meson
RUN pip3 install cython
RUN pip3 install clang==14

WORKDIR /opt

RUN mkdir symbiotic
COPY . symbiotic
WORKDIR symbiotic

RUN cd contrib && ./build_slowbeast.sh
RUN mkdir -p install/slowbeast
RUN cp -r contrib/slowbeast/dist/sb/* install/slowbeast

# fixes the "No module named clang" error
RUN pip3 install --no-deps --target install/lib/symbioticpy libclang==14.0.6

RUN git config --global user.email "hey@you.com"
RUN git config --global user.name "Symbiotic User"
#RUN ./system-build.sh . full-archive -j8
RUN ./build.sh llvm-version=14.0.0 -j8 full-archive
