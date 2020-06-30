
# Use an official Python runtime as a parent image
#FROM garagon/ipopt:V0.2

FROM python:3.7.6-stretch
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

# Copy the current directory contents into the container usr/src/app
#COPY requirements.txt /usr/src/app/

# #new addition
RUN apt-get autoclean
RUN apt-get clean

RUN apt-get update -y && apt-get install -y \
	gcc build-essential gfortran libatlas-base-dev gfortran libblas-dev liblapack-dev libatlas-base-dev wget libpng-dev python3-pip python3-dev

RUN pip3 install --upgrade pip

RUN apt-get update -y && apt-get install -y \
    libhdf5-serial-dev libatlas-dev python3-setuptools

#RUN pip3 install setuptools
#RUN apt-get install libhdf5-serial-dev
RUN pip3 install -U numpy==1.14.3
RUN pip3 install -U h5py==2.10.0
RUN pip3 install -U scipy==1.4.1
RUN pip3 install -U pandas==1.0.0
RUN pip3 install -U sklearn==0.0

RUN pip3 install -U tensorflow==1.14.0
RUN pip3 install -U keras
#==2.1.6
RUN pip3 install -U redis==2.10.6
RUN pip3 install -U senml==0.1.0
#RUN pip3 install -U numpy==1.14.3
RUN pip3 install -U stopit==1.1.2
RUN pip3 install -U treelib

WORKDIR /usr/src/app

COPY mlTraining.py /usr/src/app/
COPY prediction /usr/src/app/prediction
COPY IO/redisDB.py /usr/src/app/IO/redisDB.py
COPY utils /usr/src/app/utils
COPY utils_intern /usr/src/app/utils_intern
COPY config /usr/src/app/config