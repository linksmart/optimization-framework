
# Use an official Python runtime as a parent image
FROM garagon/glpk:V0.1

# Set the working directory to usr/src/app
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Copy the current directory contents into the container usr/src/app
COPY requirements.txt /usr/src/app/
COPY ofw.py /usr/src/app/
COPY optimization /usr/src/app/optimization
COPY utils /usr/src/app/utils
COPY prediction /usr/src/app/prediction
COPY webServices /usr/src/app/webServices
#COPY myAgent /usr/src/app/myAgent

# Install any needed packages specified in requirements.txt
#RUN pip install --trusted-host pypi.python.org -r requirements.txt
# Install the gpio library for Raspberry pi
#RUN pip install rpi.gpio
RUN pip install --upgrade pip
#RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt
RUN pyomo install-extras

#VOLUME /usr/src/app/optimization
#ENTRYPOINT ["python3", "prediction/training/pyroAdapter.py"]




