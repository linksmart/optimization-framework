
###################################################################################################
# Dockerfile to build container images
# Based on Ubuntu
###################################################################################################
# Set the base image to Ubuntu

#FROM resin/raspberrypi3-debian:stretch
#FROM balenalib/armv7hf-debian-python:3.7.2-stretch-run
#FROM balenalib/raspberry-pi-debian-python:3.5.6
# s4g3
#FROM balenalib/raspberrypi3-debian-python:3.7.2-stretch-build
# s4g2
FROM balenalib/raspberrypi3-debian:stretch-run
#FROM balenalib/raspberrypi3-debian:stretch-build


# Switch to root for install
USER root

RUN apt-get update -y && apt-get install -y \
    wget \
    ca-certificates \
	gcc \
	g++ \
	patch \
	gfortran \
	subversion \
	build-essential \
	--no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

###### "First apt-get install finished"
RUN apt-get update -y && apt-get install -y git-core curl zlib1g-dev libssl-dev libreadline-dev libyaml-dev \
    libsqlite3-dev sqlite3 libxml2-dev libxslt1-dev libcurl4-openssl-dev software-properties-common libffi-dev \
    libsdl2-2.0 libsdl2-dev libblas-dev liblapack-dev \
    python3-dev python3-pip \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*



