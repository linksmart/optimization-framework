
###################################################################################################
# Dockerfile to build ipopt container images
# Based on Ubuntu
###################################################################################################
# Set the base image to Ubuntu
#FROM ubuntu:16.04
#FROM python:3.6.4-jessie
#FROM arm32v7/debian:stretch
FROM resin/raspberrypi3-debian:stretch


# Dockerfile to build glpk container images # Based on Ubuntu
# Set the base image to Ubuntu FROM ubuntu:latest
# File Author / Maintainer MAINTAINER Douglas McCloskey <dmccloskey87@gmail.com>
# Switch to root for install
USER root
# Install wget
RUN apt-get update -y && apt-get install -y \
	wget \
	build-essential \
	python3-pip python3-dev \
	--no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*
# Install glpk from http
# instructions and documentation for glpk: http://www.gnu.org/software/glpk/
WORKDIR /user/local/
RUN wget http://ftp.gnu.org/gnu/glpk/glpk-4.57.tar.gz \
	&& tar -zxvf glpk-4.57.tar.gz
## Verify package contents
# RUN wget http://ftp.gnu.org/gnu/glpk/glpk-4.57.tar.gz.sig \
#	&& gpg --verify glpk-4.57.tar.gz.sig
#	#&& gpg --keyserver keys.gnupg.net --recv-keys 5981E818
WORKDIR /user/local/glpk-4.57
RUN ./configure \
	&& make
RUN echo "make check####################################################################################"
RUN make check
RUN echo "install####################################################################################"
RUN make install
RUN echo "distclean####################################################################################"
RUN make distclean
RUN echo "ldconfig####################################################################################"
RUN ldconfig
RUN echo "####################################################################################"
# Cleanup
RUN rm -rf /user/local/glpk-4.57.tar.gz \
    && apt-get clean

#RUN rm /usr/local/lib/libglpk.so.36 \
#    && ln -s /usr/local/lib/libglpk.so.36.2.0 /usr/local/lib/libglpk.so.36
#create a glpk user
#ENV HOME /home/user
#RUN useradd --create-home --home-dir $HOME user \
#    && chmod -R u+rwx $HOME \
#    && chown -R user:user $HOME
# switch back to user
#WORKDIR $HOME

#USER user

#RUN which glpsol
#WORKDIR /usr/local/bin
#RUN ls /usr/local/bin
#RUN ls /usr/local/glpk-4.57

### /usr/local/lib   --> library

#RUN apt-get update -y && apt-get install -y \
#	python3-pip python3-dev