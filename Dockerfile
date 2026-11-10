# Multi-stage build of Symbiotic.
#
# Every component is built in its own stage that copies in only the sources
# it needs, so a change in one component rebuilds only that component and the
# stages that depend on it. For example, a change in reverser/ reuses the cached
# LLVM, dg, KLEE, ... stages and rebuilds only the reverser and final stages.
#
# Stage graph:
#
#   base ─┬─ slowbeast ───────────────────────────────┐
#         └─ llvm ─┬─ dg ─┬─ sbt-slicer ──────────────┤
#                  │      └─ sbt-instrumentation ─────┤
#                  ├─ klee ───────────────────────────┤
#                  ├─ llvm2c ─────────────────────────┼─ final
#                  ├─ reverser ───────────────────────┤
#                  └─ transforms ─────────────────────┘
#
# Requires BuildKit (default in recent Docker), which also builds independent
# stages in parallel. Build with e.g.:
#
#   docker build -t symbiotic --build-arg JOBS=8 .
#
# Components cloned from the internet (slowbeast and its dependencies, LLVM
# release tarballs, googletest, jsoncpp) are cached as well; to force fetching
# a fresh slowbeast, use: docker build --no-cache-filter slowbeast ...

ARG LLVM_VERSION=14.0.0
ARG JOBS=8

######################################################################
# base: system dependencies
######################################################################
FROM ubuntu:22.04 AS base

# Setup time-zone so that the build does not hang
# on configuring the tzdata package.
# I work in Brno, that is basically Vienna-North :)
# (definitely its closer than Prague)
ENV TZ=Europe/Vienna
RUN ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime && echo "$TZ" > /etc/timezone

# Install packages
RUN apt-get update && \
    apt-get install -y git cmake make llvm zlib1g-dev clang g++ python3 curl wget rsync unzip gcc-multilib xz-utils libz3-dev libsqlite3-dev python3-pip libboost-all-dev libgmp-dev ninja-build build-essential m4 pkg-config

RUN pip3 install z3-solver pyinstaller numpy setuptools meson cython clang==14

RUN git config --global user.email "hey@you.com" && \
    git config --global user.name "Symbiotic User"

WORKDIR /opt/symbiotic

######################################################################
# slowbeast (independent of the rest)
######################################################################
FROM base AS slowbeast
WORKDIR /opt/symbiotic/contrib
COPY contrib/build_slowbeast.sh .
RUN ./build_slowbeast.sh

######################################################################
# LLVM
######################################################################
FROM base AS llvm
ARG LLVM_VERSION
ARG JOBS
# only what build.sh needs to build LLVM, so that changes elsewhere
# (including the other scripts/build-*.sh) do not invalidate this stage
COPY build.sh .
COPY scripts/build-utils.sh scripts/build-llvm.sh scripts/
COPY patches patches
RUN ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} only=llvm

# Helper for the component stages below:
#   COPY <component> <component>                         - the sources
#   COPY .git/modules/<componen>[t]/HEAD .git/modules/<component>/
#                                                        - git metadata of the submodule
#                                                          (used to embed versions);
#                                                          the wildcard makes it optional
#   COPY scripts/build-<component>.sh scripts/           - the build script

######################################################################
# dg
######################################################################
FROM llvm AS dg
ARG LLVM_VERSION
ARG JOBS
COPY .git/modules/d[g]/HEAD .git/modules/dg/
COPY dg dg
COPY scripts/build-dg.sh scripts/
RUN mkdir -p .git/modules/dg/objects .git/modules/dg/refs && \
    ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} only=dg

######################################################################
# sbt-slicer (needs dg)
######################################################################
FROM dg AS sbt-slicer
ARG LLVM_VERSION
ARG JOBS
COPY .git/modules/sbt-slice[r]/HEAD .git/modules/sbt-slicer/
COPY sbt-slicer sbt-slicer
COPY scripts/build-sbt-slicer.sh scripts/
RUN mkdir -p .git/modules/sbt-slicer/objects .git/modules/sbt-slicer/refs && \
    ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} only=sbt-slicer

######################################################################
# sbt-instrumentation (needs dg)
######################################################################
FROM dg AS sbt-instrumentation
ARG LLVM_VERSION
ARG JOBS
COPY .git/modules/sbt-instrumentatio[n]/HEAD .git/modules/sbt-instrumentation/
COPY sbt-instrumentation sbt-instrumentation
COPY scripts/build-sbt-instrumentation.sh scripts/
RUN mkdir -p .git/modules/sbt-instrumentation/objects .git/modules/sbt-instrumentation/refs && \
    ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} only=sbt-instrumentation

######################################################################
# KLEE (+ googletest)
######################################################################
FROM llvm AS klee
ARG LLVM_VERSION
ARG JOBS
COPY scripts/build-googletest.sh scripts/
RUN ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} only=googletest
COPY .git/modules/kle[e]/HEAD .git/modules/klee/
COPY klee klee
COPY scripts/build-klee.sh scripts/
RUN mkdir -p .git/modules/klee/objects .git/modules/klee/refs && \
    ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} only=klee

######################################################################
# llvm2c
######################################################################
FROM llvm AS llvm2c
ARG LLVM_VERSION
ARG JOBS
COPY .git/modules/llvm2[c]/HEAD .git/modules/llvm2c/
COPY llvm2c llvm2c
COPY scripts/build-llvm2c.sh scripts/
RUN mkdir -p .git/modules/llvm2c/objects .git/modules/llvm2c/refs && \
    ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} only=llvm2c

######################################################################
# reverser
######################################################################
FROM llvm AS reverser
ARG LLVM_VERSION
ARG JOBS
COPY .git/modules/reverse[r]/HEAD .git/modules/reverser/
COPY reverser reverser
COPY scripts/build-reverser.sh scripts/
RUN mkdir -p .git/modules/reverser/objects .git/modules/reverser/refs && \
    ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} only=reverser

######################################################################
# transforms (LLVMsbt.so)
######################################################################
FROM llvm AS transforms
ARG LLVM_VERSION
ARG JOBS
COPY transforms transforms
COPY scripts/build-transforms.sh scripts/
RUN ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} only=transforms

######################################################################
# final: merge the components, install files, create the distribution
######################################################################
FROM llvm AS final
ARG LLVM_VERSION
ARG JOBS

# the whole repository (incl. .git, needed by scripts/gen-version.sh)
COPY . .

# installed files of all components
COPY --from=dg                  /opt/symbiotic/install install
COPY --from=sbt-slicer          /opt/symbiotic/install install
COPY --from=sbt-instrumentation /opt/symbiotic/install install
COPY --from=klee                /opt/symbiotic/install install
COPY --from=llvm2c              /opt/symbiotic/install install
COPY --from=reverser            /opt/symbiotic/install install
COPY --from=transforms          /opt/symbiotic/install install
COPY --from=slowbeast           /opt/symbiotic/contrib/slowbeast/dist/sb install/slowbeast

# build directories (scripts/gen-version.sh reads the build types from them)
COPY --from=dg                  /opt/symbiotic/dg/build-${LLVM_VERSION} dg/build-${LLVM_VERSION}
COPY --from=sbt-slicer          /opt/symbiotic/sbt-slicer/build-${LLVM_VERSION} sbt-slicer/build-${LLVM_VERSION}
COPY --from=sbt-instrumentation /opt/symbiotic/sbt-instrumentation/build-${LLVM_VERSION} sbt-instrumentation/build-${LLVM_VERSION}
COPY --from=klee                /opt/symbiotic/klee/build-${LLVM_VERSION} klee/build-${LLVM_VERSION}
COPY --from=llvm2c              /opt/symbiotic/llvm2c/build-${LLVM_VERSION} llvm2c/build-${LLVM_VERSION}
COPY --from=reverser            /opt/symbiotic/reverser/build-${LLVM_VERSION} reverser/build-${LLVM_VERSION}
COPY --from=transforms          /opt/symbiotic/transforms/build-${LLVM_VERSION} transforms/build-${LLVM_VERSION}

# fixes the "No module named clang" error
RUN pip3 install --no-deps --target install/lib/symbioticpy libclang==14.0.6

#RUN ./system-build.sh . full-archive -j8
RUN ./build.sh llvm-version=${LLVM_VERSION} -j${JOBS} full-archive only=files,dist
