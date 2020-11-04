FROM ubuntu:20.04

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
RUN apt-get install -y git cmake make llvm zlib1g-dev clang g++ python3 python curl wget rsync make cmake unzip gcc-multilib xz-utils libz3-dev libsqlite3-dev

WORKDIR /opt
RUN git clone https://github.com/staticafi/symbiotic
WORKDIR /opt/symbiotic
RUN git config --global user.email "hey@you.com"
RUN git config --global user.name "Symbiotic User"
RUN ./system-build.sh
