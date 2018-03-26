#FROM dlwoodruff/pyomoglpk

#WORKDIR /usr/src/app
#VOLUME /usr/src/app/glpk

FROM ubuntu:16.04

# File Author / Maintainer MAINTAINER Douglas McCloskey <dmccloskey87@gmail.com>
# Switch to root for install
USER root
# Install wget
RUN apt-get update -y && apt-get install -y \
	wget \
	glpk-utils \
	build-essential \
	--no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

VOLUME
# Install glpk from http
# instructions and documentation for glpk: http://www.gnu.org/software/glpk/
# Set the working directory to usr/src/app/share
ENV PATH "$PATH:/usr/bin"
RUN echo $PATH
WORKDIR /usr/bin
RUN ls | grep "glpsol"


#ENV PATH "$PATH:/usr/bin"
