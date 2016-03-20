# -*- coding: utf-8 -*-
FROM ubuntu:14.04
MAINTAINER Simon Kamronn <simon@kamronn.dk>

RUN apt-get update

RUN apt-get --force-yes -y install \
  curl               \
  libav-tools        \
  libsamplerate0     \
  libsamplerate0-dev \
  libsndfile1        \
  libsndfile-dev     \
  python             \
  python-dev         \
  python-numpy       \
  python-scipy       \
  python-setuptools  \
  python-pip         \
  libfreetype6-dev   \
  libpng-dev         \
  git

RUN pip install -v   \
  matplotlib         \
  docopt             \
  joblib             \
  librosa            \
  scikits.audiolab   \
  scikits.example    \
  scikits.samplerate \
  scikits.talkbox    \
  flask              \
  boto3              \
  pytz               \
  gevent

RUN apt-get --force-yes -y install \
  libpq-dev

RUN pip install -v  \
  psycopg2          \
  postgres


RUN ln -s /usr/bin/avconv /usr/local/bin/avconv
RUN ln -s /usr/bin/avconv /usr/local/bin/ffmpeg

COPY ./ /opt/rdiofy/
WORKDIR /opt/rdiofy/
RUN mkdir new_recordings
RUN mv .aws /root/

EXPOSE 5000

CMD python app.py

####
## audfprint 0.9
## @see https://github.com/dpwe/audfprint
####
# RUN curl -LSs https://github.com/hinata/audfprint/archive/0.9.0.tar.gz | tar fxz - -C /usr/local/lib
# RUN git clone https://github.com/dpwe/audfprint.git
# RUN chmod +x /usr/local/lib/audfprint-0.9.0/audfprint.py
# RUN ln -s    /usr/local/lib/audfprint-0.9.0/audfprint.py /usr/bin/audfprint