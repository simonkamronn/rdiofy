# -*- coding: utf-8 -*-
FROM ubuntu:14.04
MAINTAINER Simon Kamronn <simon@kamronn.dk>

RUN apt-get update

RUN apt-get --force-yes -y install \
  curl              \
  libav-tools       \
  python            \
  python-dev        \
  python-nose       \
  python-setuptools \
  python-pip        \
  git               \
  libpq-dev         \
  libblas-dev       \
  liblapack-dev     \
  gfortran

RUN pip install -v  \
  docopt            \
  joblib            \
  flask             \
  boto3             \
  pytz              \
  gevent            \
  psycopg2          \
  postgres          \
  numpy			\
  scipy
  
RUN ln -s /usr/bin/avconv /usr/local/bin/avconv
RUN ln -s /usr/bin/avconv /usr/local/bin/ffmpeg

COPY ./ /opt/rdiofy/
WORKDIR /opt/rdiofy/
RUN mkdir recordings
RUN mv .aws /root/

CMD python app.py