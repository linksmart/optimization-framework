
# Use an official Python runtime as a parent image
FROM python:3.6

# Set the working directory to usr/src/app
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Copy the current directory contents into the container usr/src/app
COPY requirements.txt /usr/src/app/
COPY frameworkAdapter.py /usr/src/app/
COPY optimization /usr/src/app/optimization
#COPY myAgent /usr/src/app/myAgent

# Install any needed packages specified in requirements.txt
#RUN pip install --trusted-host pypi.python.org -r requirements.txt
# Install the gpio library for Raspberry pi
#RUN pip install rpi.gpio
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pyomo install-extras

VOLUME /usr/src/app/optimization

# Run frameworkAdapter.py.py when the container launches
ENTRYPOINT ["python", "-u", "frameworkAdapter.py"]




