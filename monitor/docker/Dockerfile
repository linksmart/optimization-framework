

###################################################################################################
# Dockerfile to build ipopt container images
# Based on Ubuntu
###################################################################################################
# Set the base image to Ubuntu

#FROM python:3.6.4-jessie
# Switch to root for install
FROM python:3.6.8-stretch
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
RUN apt-get update -y && apt-get install -y git-core curl zlib1g-dev libssl-dev libreadline-dev libyaml-dev libsqlite3-dev sqlite3 libxml2-dev libxslt1-dev libcurl4-openssl-dev software-properties-common libffi-dev

# Set the working directory to usr/src/app
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# #new addition
RUN apt-get autoclean
RUN apt-get clean

RUN apt-get update -y && apt-get install -y \
	gcc build-essential sudo gfortran libatlas-base-dev gfortran libblas-dev liblapack-dev libatlas-base-dev wget libpng-dev python3-pip python3-dev

#RUN curl -sSL https://get.docker.com/ | sh

RUN pip3 install --upgrade pip


RUN pip3 install -U paho-mqtt==1.4.0
RUN pip3 install -U pyzmq==18.0.1

RUN pip3 install -U senml==0.1.0
RUN pip3 install -U redis==2.10.6
RUN pip3 install -U requests==2.21.0

#RUN pip3 install -U docker-compose
# Set the working directory to usr/src/app
#RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY IO /usr/src/app/IO
COPY utils /usr/src/app/utils
COPY monitor /usr/src/app/monitor
COPY monitor.py /usr/src/app/monitor.py
COPY config /usr/src/app/config
COPY utils_intern /usr/src/app/utils_intern