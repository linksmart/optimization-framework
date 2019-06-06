

###################################################################################################
# Dockerfile to build ipopt container images
# Based on Ubuntu
###################################################################################################
# Set the base image to Ubuntu
#FROM ubuntu:16.04
FROM python:3.6.4-jessie
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

# Set the working directory to usr/src/app
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Copy the current directory contents into the container usr/src/app
COPY connector/docker/requirements-arm.txt /usr/src/app/

# #new addition
RUN apt-get autoclean
RUN apt-get clean

RUN apt-get update -y && apt-get install -y \
	gcc build-essential gfortran libatlas-base-dev gfortran libblas-dev liblapack-dev libatlas-base-dev wget libpng-dev python3-pip python3-dev

RUN pip3 install --upgrade pip


RUN pip3 install -U paho-mqtt
RUN pip3 install -U pyzmq

RUN pip3 install -U senml
RUN pip3 install -U redis
RUN pip3 install -U requests

# Set the working directory to usr/src/app
#RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY utils /usr/src/app/utils
COPY IO /usr/src/app/IO
COPY connector /usr/src/app/connector
COPY connectors.py /usr/src/app/connectors.py
COPY config /usr/src/app/config
COPY utils_intern /usr/src/app/utils_intern