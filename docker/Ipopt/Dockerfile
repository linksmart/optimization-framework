
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


# Set the working directory to usr/src/app/share
RUN mkdir -p /usr/src/app/share
WORKDIR /usr/src/app/share

# Install ipopt from http
RUN wget https://www.coin-or.org/download/source/Ipopt/Ipopt-3.12.9.tgz
RUN gunzip Ipopt-3.12.9.tgz
RUN tar xvf Ipopt-3.12.9.tar

RUN mv Ipopt-3.12.9 CoinIpopt
## Verify package contents
# RUN wget http://ftp.gnu.org/gnu/glpk/glpk-4.57.tar.gz.sig \
#	&& gpg --verify glpk-4.57.tar.gz.sig
#	#&& gpg --keyserver keys.gnupg.net --recv-keys 5981E818

#Installing thirdparty services
WORKDIR /usr/src/app/share/CoinIpopt/ThirdParty/Blas
RUN ./get.Blas
WORKDIR ../ASL
RUN echo "Installing ASL"
RUN ./get.ASL
RUN echo "Installing MUMPS linear solver"
WORKDIR ../Mumps
RUN ./get.Mumps
RUN echo "Installing METIS"
WORKDIR ../Metis
RUN ./get.Metis

#Creating a directory for building ipopt
WORKDIR /usr/src/app/share/CoinIpopt
RUN mkdir -p /usr/src/app/share/CoinIpopt/build
WORKDIR /usr/src/app/share/CoinIpopt/build

RUN ../configure
#--withglpk-lib=""
RUN echo "Configuration finished"

RUN make
RUN echo "Make finished"

RUN make test
RUN echo "Make test finished"
RUN make install
RUN echo "Install finished"
RUN make distclean
RUN ldconfig
# Cleanup
RUN rm -rf /usr/src/app/share/Ipopt-3.12.9.tgz
#RUN apk add clean
ENV PATH "$PATH:/usr/src/app/share/CoinIpopt/build/bin"
