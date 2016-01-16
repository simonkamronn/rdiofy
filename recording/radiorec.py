import datetime
import os
import glob
import requests
from contextlib import closing
import audioread
from audioread import ffdec
import numpy as np
SAMPLE_RATE = 44100
CHUNK_SIZE = 1024

ARGS = {'url': 'http://live-icy.gss.dr.dk/A/A05H.mp3',  # DR P3
        'duration': 40,  # Seconds
        'station': 'DR P3',
        'name': None,
        'target_dir': 'new_recordings',
        'dt_format': '%Y-%m-%dT%H_%M_%S'}


class RadioRecorder:
    def __init__(self, args=ARGS):
        self.args = args
        self.duration = args['duration']
        self.station = args['station']
        self.name = args['name']
        self.filename = ''
        self.target_dir = os.path.abspath(args['target_dir'])
        self.dt_format = args['dt_format']
        self.recording = False

        self.url = args['url']
        if not self.url.endswith('mp3'):
            # Possibly a playlist file
            self.url = m3u_to_url(self.url)

    def record(self, ingest):
        cur_dt_string = datetime.datetime.now().strftime(self.dt_format)
        filename = self.target_dir + os.sep + cur_dt_string.replace(':', '') + "_" + self.station
        if self.name:
            filename += '_' + self.name
        filename += '.mp3'

        chunks = (self.duration*SAMPLE_RATE)//CHUNK_SIZE
        with open(filename, "wb") as target:
            with closing(requests.get(self.url, stream=True)) as r:
                for _ in range(chunks):
                    target.write(r.raw.read(CHUNK_SIZE))

        # Ingest file in database
        nhash = ingest(filename, self.station)

        try:
            os.remove(filename)
        except WindowsError:
            print("Can't delete file: %s" % filename)
        except IOError, e:
            print(e)

    def record_stream(self, ingest, logger):
        try:
            logger("Starting recording of %s" % self.station)
            self.recording = True
            with ffdec.FFmpegAudioFile(self.url, block_size=65536) as f:
                for i, buf in enumerate(f):
                    ingest(np.frombuffer(buf, np.int16).astype(np.float32), self.station)

        except audioread.DecodeError:
            logger("File could not be decoded")

        finally:
            logger("Stopping recording of %s" % self.station)
            self.recording = False

    def remove_files(self):
        for mp3_file in glob.glob(self.target_dir + '/*.mp3')[:-2]:
            try:
                os.remove(mp3_file)
            except WindowsError:
                print("Can't delete file: %s" % mp3_file)
            except IOError, e:
                print(e)


def m3u_to_url(url):
    remote_file = requests.get(url)
    return remote_file.content.decode('utf8').strip()


def record_stream(radio_station, queue):
    url = radio_station.get('url')
    station = radio_station.get('name')
    if url.endswith('m3u'):
        url = m3u_to_url(url)

    try:
        with ffdec.FFmpegAudioFile(url, block_size=65536*10) as f:
            for buf in f:
                queue.put(('ingest', (np.frombuffer(buf, np.int16).astype(np.float32), station)))

    except audioread.DecodeError:
        print("File could not be decoded")
