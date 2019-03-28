
###################################################################################################
# Dockerfile to build container images
# Based on Ubuntu
###################################################################################################
# Set the base image to Ubuntu

FROM resin/raspberrypi3-debian:stretch

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
	python3-pip python3-dev \
	--no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

###### "First apt-get install finished"
RUN apt-get update -y && apt-get install -y git-core curl zlib1g-dev libssl-dev libreadline-dev libyaml-dev libsqlite3-dev sqlite3 libxml2-dev libxslt1-dev libcurl4-openssl-dev software-properties-common libffi-dev


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
###RUN echo "Installing ASL"
RUN ./get.ASL
####RUN echo "Installing MUMPS linear solver"
WORKDIR ../Mumps
RUN ./get.Mumps
####RUN echo "Installing METIS"
WORKDIR ../Metis
RUN ./get.Metis

#Creating a directory for building ipopt
WORKDIR /usr/src/app/share/CoinIpopt
RUN mkdir -p /usr/src/app/share/CoinIpopt/build
WORKDIR /usr/src/app/share/CoinIpopt/build

RUN ../configure ADD_CFLAGS=-DNO_fpu_control
#--withglpk-lib=""
####RUN echo "Configuration finished"

RUN make
####RUN echo "Make finished"

RUN make test
###RUN echo "Make test finished"
RUN make install
###RUN echo "Install finished"
RUN make distclean
RUN ldconfig
# Cleanup
RUN rm -rf /usr/src/app/share/Ipopt-3.12.9.tgz
#RUN apk add clean
ENV PATH "$PATH:/usr/src/app/share/CoinIpopt/build/bin"



#######################Bonmin##########################################
WORKDIR /usr/src/app/share

# Install ipopt from http
RUN wget https://www.coin-or.org/download/source/Bonmin/Bonmin-1.8.6.tgz
RUN gunzip Bonmin-1.8.6.tgz
RUN tar xvf Bonmin-1.8.6.tar

RUN mv Bonmin-1.8.6 CoinBonmin

#Installing thirdparty services
WORKDIR /usr/src/app/share/CoinBonmin/ThirdParty/Blas
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
WORKDIR /usr/src/app/share/CoinBonmin
RUN mkdir -p /usr/src/app/share/CoinBonmin/build
WORKDIR /usr/src/app/share/CoinBonmin/build

RUN ../configure ADD_CFLAGS=-DNO_fpu_control
#--withglpk-lib=""
###RUN echo "Configuration finished"

RUN make
####RUN echo "Make finished"

RUN make test
#####RUN echo "Make test finished"
RUN make install
#####RUN echo "Install finished"
RUN make distclean
RUN ldconfig
# Cleanup
RUN rm -rf /usr/src/app/share/Bonmin-1.8.6.tgz
#RUN apk add clean
ENV PATH "$PATH:/usr/src/app/share/CoinBonmin/build/bin"

RUN apt-get clean


#######################GLPK##########################################
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
####RUN echo "make check####################################################################################"
RUN make check
####RUN echo "install####################################################################################"
RUN make install
###RUN echo "distclean####################################################################################"
RUN make distclean
####RUN echo "ldconfig####################################################################################"
RUN ldconfig
####RUN echo "####################################################################################"
# Cleanup
RUN rm -rf /usr/src/app/share/glpk-4.65.tar.gz \
    && apt-get clean


ENV PATH "$PATH:/usr/bin/local"


###############################gurobi############################################


# Set the working directory to usr/src/app/share
RUN mkdir -p /usr/src/app/share
WORKDIR /usr/src/app/share

# Install ipopt from http
COPY gurobi811 /usr/src/app/share

#RUN apk add clean

ENV GUROBI_HOME "/share/gurobi811/linux64"
ENV PATH "$PATH:/usr/src/app/share/gurobi811/linux64/bin"
ENV LD_LIBRARY_PATH "${LD_LIBRARY_PATH}:${GUROBI_HOME}/lib"

RUN apt-get clean