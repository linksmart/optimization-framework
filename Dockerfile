
# Use an official Python runtime as a parent image
FROM garagon/ipopt:arm

# Set the working directory to usr/src/app
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Copy the current directory contents into the container usr/src/app
COPY requirements.txt /usr/src/app/

RUN apt-get install gcc gfortran libopenblas-base libopenblas-dev python3-dev libhdf5-dev libblas-dev liblapack-dev python3-setuptools python3-h5py libzmq3 libzmq3-dev python3-zmq



# Install any needed packages specified in requirements.txt
RUN pip3 install -r requirements.txt
#RUN pip3 install --upgrade https://storage.googleapis.com/tensorflow/mac/cpu/tensorflow-0.12.0-py3-none-any.whl


# Set the working directory to usr/src/app
#RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY ofw.py /usr/src/app/
COPY optimization /usr/src/app/optimization
COPY utils /usr/src/app/utils
COPY prediction /usr/src/app/prediction
COPY swagger_server /usr/src/app/swagger_server
COPY IO /usr/src/app/IO






