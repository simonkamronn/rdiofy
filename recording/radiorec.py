import datetime
import os
import requests
from contextlib import closing
from audfprint.audio_read import FFmpegAudioFile
import numpy as np
SAMPLE_RATE = 8000
CHUNK_SIZE = 1024

ARGS = {'url': 'http://live-icy.gss.dr.dk/A/A03H.mp3',  # DR P3
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


    def record_stream(self, ingest, logger):
        logger("Starting recording of %s" % self.station)
        self.recording = True
        with FFmpegAudioFile(self.url, block_size=65536) as f:
            for i, buf in enumerate(f):
                ingest(np.frombuffer(buf, np.int16).astype(np.float32), self.station)

        logger("Stopping recording of %s" % self.station)
        self.recording = False


def m3u_to_url(url):
    remote_file = requests.get(url)
    return remote_file.content.decode('utf8').strip()


def record_stream(radio_station, queue):
    """
    Record a radio stream an send segments to be ingested
    :param radio_station: name of the station
    :param queue: queue to consumer
    :return:
    """
    url = radio_station.get('url')
    station = radio_station.get('name')
    if url.endswith('m3u'):
        url = m3u_to_url(url)

    y = []
    idx = 0
    with FFmpegAudioFile(url, channels=1, sample_rate=SAMPLE_RATE, block_size=4096) as f:
        for buf in f:
            idx += 1
            y.append(buf)

            if idx > 100:
                print('ingest %s to queue' % station)
                queue.put(('ingest', (y, station)))
                y = []
                idx = 0
