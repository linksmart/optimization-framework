
###################################################################################################
# Dockerfile to build container images
# Based on Ubuntu
###################################################################################################
# Set the base image to Ubuntu

#FROM resin/raspberrypi3-debian:stretch
#FROM balenalib/armv7hf-debian-python:3.7.2-stretch-run
#FROM balenalib/raspberry-pi-debian-python:3.5.6
# s4g3
#FROM balenalib/raspberrypi3-debian-python:3.7.2-stretch-build
# s4g2
FROM balenalib/raspberrypi3-debian:stretch-run
#FROM balenalib/raspberrypi3-debian:stretch-build


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
RUN apt-get update -y && apt-get install -y git-core curl zlib1g-dev libssl-dev libreadline-dev libyaml-dev \
    libsqlite3-dev sqlite3 libxml2-dev libxslt1-dev libcurl4-openssl-dev software-properties-common libffi-dev \
    libsdl2-2.0 libsdl2-dev libblas-dev liblapack-dev \
    python3-dev python3-pip \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*



#RUN pip3 install --upgrade setuptools
#RUN pip3 install --upgrade pip
#RUN pip3 install -U connexion==2.2.0
#RUN pip3 install -U paho-mqtt==1.4.0
#RUN pip3 install -U pyzmq==18.0.1
#RUN pip3 install -U psutil==5.6.1
#RUN pip3 install --extra-index-url https://www.piwheels.org/simple -U tensorflow


#########################################################################
###########################GLPK ########################################
##########################################################################

# Install glpk from http
# instructions and documentation for glpk: http://www.gnu.org/software/glpk/
# Set the working directory to usr/src/app/share
RUN mkdir -p /usr/src/app/share
WORKDIR /usr/src/app/share

RUN wget http://ftp.gnu.org/gnu/glpk/glpk-4.65.tar.gz \
	&& tar -zxvf glpk-4.65.tar.gz
## Verify package contents
# RUN wget http://ftp.gnu.org/gnu/glpk/glpk-4.57.tar.gz.sig \
#	&& gpg --verify glpk-4.57.tar.gz.sig
#	#&& gpg --keyserver keys.gnupg.net --recv-keys 5981E818
WORKDIR /usr/src/app/share/glpk-4.65
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
RUN rm -rf /usr/src/app/share/glpk-4.65.tar.gz \
    && apt-get clean

ENV PATH "$PATH:/usr/bin/local"



############################################################################
##############ipopt#########################################################
############################################################################


# Set the working directory to usr/src/app/share
RUN mkdir -p /usr/src/app/share
WORKDIR /usr/src/app/share

# Install ipopt from http
RUN wget https://www.coin-or.org/download/source/Ipopt/Ipopt-3.12.13.tgz
RUN gunzip Ipopt-3.12.13.tgz
RUN tar xvf Ipopt-3.12.13.tar

RUN mv Ipopt-3.12.13 CoinIpopt
## Verify package contents
# RUN wget http://ftp.gnu.org/gnu/glpk/glpk-4.57.tar.gz.sig \
#	&& gpg --verify glpk-4.57.tar.gz.sig
#	#&& gpg --keyserver keys.gnupg.net --recv-keys 5981E818

#Installing thirdparty services
WORKDIR /usr/src/app/share/CoinIpopt/ThirdParty/Blas
RUN ./get.Blas
WORKDIR ../ASL
#RUN echo "Installing ASL"
RUN ./get.ASL
#RUN echo "Installing MUMPS linear solver"
WORKDIR ../Mumps
RUN ./get.Mumps
#RUN echo "Installing METIS"
WORKDIR ../Metis
RUN ./get.Metis

#Creating a directory for building ipopt
WORKDIR /usr/src/app/share/CoinIpopt
RUN mkdir -p /usr/src/app/share/CoinIpopt/build
WORKDIR /usr/src/app/share/CoinIpopt/build

RUN ../configure ADD_CFLAGS=-DNO_fpu_control
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
RUN rm -rf /usr/src/app/share/Ipopt-3.12.13.tgz
#RUN apk add clean
ENV PATH "$PATH:/usr/src/app/share/CoinIpopt/build/bin"


RUN apt-get update -y && apt-get install -y coinor-cbc coinor-clp
###############################################################################
###############BONMIN
############################################################################
# Set the working directory to usr/src/app/share
RUN mkdir -p /usr/src/app/share
WORKDIR /usr/src/app/share

# Install ipopt from http
RUN wget https://www.coin-or.org/download/source/Bonmin/Bonmin-1.8.6.tgz
RUN gunzip Bonmin-1.8.6.tgz
RUN tar xvf Bonmin-1.8.6.tar

RUN mv Bonmin-1.8.6 CoinBonmin

#Creating a directory for building ipopt
WORKDIR /usr/src/app/share/CoinBonmin
RUN mkdir -p /usr/src/app/share/CoinBonmin/build
WORKDIR /usr/src/app/share/CoinBonmin/build

RUN ../configure -C
#RUN ../configure --with-clp=/usr/bin/clp --with-cbc=/usr/bin/cbc --with-ipopt=/usr/src/app/share/CoinIpopt/build/bin/ipopt -C ADD_CFLAGS=-DNO_fpu_control
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
RUN rm -rf /usr/src/app/share/Bonmin-1.8.6.tgz
#RUN apk add clean
ENV PATH "$PATH:/usr/src/app/share/CoinBonmin/build/bin"


################CBC#################
# Set the working directory to usr/src/app/share
RUN mkdir -p /usr/src/app/share
WORKDIR /usr/src/app/share

# Install ipopt from http
RUN wget https://www.coin-or.org/download/source/Cbc/Cbc-2.9.8.tgz
RUN gunzip Cbc-2.9.8.tgz
RUN tar xvf Cbc-2.9.8.tar

RUN mv Cbc-2.9.8 CoinCBC

#Creating a directory for building ipopt
WORKDIR /usr/src/app/share/CoinCBC
RUN mkdir -p /usr/src/app/share/CoinCBC/build
WORKDIR /usr/src/app/share/CoinCBC/build

RUN ../configure --enable-cbc-parallel -C ADD_CFLAGS=-DNO_fpu_control
# CFLAGS="-O2 -march=armv7-a -mfpu=neon-vfpv4 -mfloat-abi=hard"
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
RUN rm -rf /usr/src/app/share/Cbc-2.9.8.tgz
#RUN apk add clean
ENV PATH "$PATH:/usr/src/app/share/CoinCBC/build/bin"