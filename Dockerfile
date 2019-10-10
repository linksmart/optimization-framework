
# Use an official Python runtime as a parent image
FROM garagon/solvers:amd_v3

RUN useradd -rm -d /home/garagon -s /bin/bash -g root -G sudo -u 1000 garagon


# Set the working directory to usr/src/app
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Copy the current directory contents into the container usr/src/app
COPY requirements.txt /usr/src/app/

# #new addition
RUN apt-get autoclean
RUN apt-get clean

RUN apt-get update -y && apt-get install -y \
    sudo gcc build-essential gfortran libatlas-base-dev gfortran libblas-dev liblapack-dev libatlas-base-dev wget libpng-dev python3-pip python3-dev python3-setuptools libhdf5-serial-dev libatlas-dev

RUN pip3 install --upgrade pip

RUN pip3 install -U requests==2.21.0
RUN pip3 install -U pyomo==5.6.6
#RUN pip3 install -U pyomo.extras==2.0
RUN pip3 install -U gunicorn==19.9.0
RUN pip3 install -U sh==1.12.14
RUN pip3 install -U connexion==2.2.0
RUN pip3 install -U paho-mqtt==1.4.0
RUN pip3 install -U pyzmq==18.0.1
RUN pip3 install -U psutil==5.6.1
RUN pip3 install -U tensorflow==1.8.0
RUN pip3 install -U keras==2.1.6
RUN pip3 install -U senml==0.1.0
RUN pip3 install -U redis==2.10.6

#RUN pip3 install --upgrade pyomo

RUN pip3 install -U numpy==1.14.3
RUN pip3 install -U h5py
RUN pip3 install -U scipy
RUN pip3 install -U pandas==0.22.0
RUN pip3 install -U sklearn

RUN pip3 install -U Pyro4

RUN pip3 install -U pydevd
RUN pip3 install -U xlrd


USER garagon

WORKDIR /usr/src/app

#COPY entry.sh /usr/src/app/
COPY ofw.py /usr/src/app/
COPY optimization /usr/src/app/optimization
COPY utils /usr/src/app/utils
COPY prediction /usr/src/app/prediction
COPY swagger_server /usr/src/app/swagger_server
COPY IO /usr/src/app/IO
COPY mock_data /usr/src/app/mock_data
COPY config /usr/src/app/config
COPY profev /usr/src/app/profev
#COPY logs /usr/src/app/logs
COPY utils_intern /usr/src/app/utils_intern
COPY stochastic_programming /usr/src/app/stochastic_programming


USER root

RUN echo "PATH=$PATH" >> /usr/src/app/utils_intern/env_var.txt
RUN echo "GUROBI_HOME=$GUROBI_HOME" >> /usr/src/app/utils_intern/env_var.txt
RUN echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH" >> /usr/src/app/utils_intern/env_var.txt
RUN echo "GRB_LICENSE_FILE=$GRB_LICENSE_FILE" >> /usr/src/app/utils_intern/env_var.txt

RUN chown -R garagon /usr/src/app/
USER garagon

