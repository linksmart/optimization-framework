
# Use an official Python runtime as a parent image
FROM garagon/ipopt:V0.2

# Set the working directory to usr/src/app
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Copy the current directory contents into the container usr/src/app
COPY requirements.txt /usr/src/app/

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
RUN pip3 install -U h5py
RUN pip3 install -U scipy
RUN pip3 install -U pandas==0.22.0
RUN pip3 install -U sklearn

RUN pip3 install -U tensorflow==1.8.0
RUN pip3 install -U keras==2.1.6
RUN pip3 install -U redis
RUN pip3 install -U senml

WORKDIR /usr/src/app

COPY mlTraining.py /usr/src/app/
COPY prediction /usr/src/app/prediction
COPY IO/redisDB.py /usr/src/app/IO/redisDB.py
COPY utils /usr/src/app/utils
COPY config /usr/src/app/config
COPY utils_intern /usr/src/app/utils_intern