# -*- coding: utf-8 -*-
FROM ubuntu:14.04
MAINTAINER Simon Kamronn <simon@kamronn.dk>

RUN apt-get update && apt-get upgrade -y

RUN apt-get --force-yes -y install \
  curl              \
  libav-tools       \
  pkg-config        \
  git               \
  libpq-dev         \
  libblas-dev       \
  liblapack-dev     \
  gfortran          \
  wget

RUN apt-get autoremove -y \
  && apt-get clean

# Install python 3.5 using Miniconda
RUN wget -q https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
  bash /tmp/miniconda.sh -f -b -p /opt/conda

RUN /opt/conda/bin/conda install --yes python=3.5 pip && \
  /opt/conda/bin/pip install --upgrade pip && \
  rm /tmp/miniconda.sh

ENV PATH=/opt/conda/bin:$PATH

RUN conda install   \
  docopt            \
  joblib            \
  flask             \
  boto3             \
  pytz              \
  gevent            \
  psycopg2          \
  numpy			    \
  scipy

RUN pip install -v postgres

RUN ln -s /usr/bin/avconv /usr/local/bin/avconv
RUN ln -s /usr/bin/avconv /usr/local/bin/ffmpeg

COPY ./ /opt/rdiofy/
WORKDIR /opt/rdiofy/
#RUN mkdir recordings
RUN mv .aws /root/

CMD python app.py