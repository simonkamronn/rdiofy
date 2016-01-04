import datetime
import os
import glob
import requests
from contextlib import closing

SAMPLE_RATE = 44100
CHUNK_SIZE = 1024

ARGS = {'url': 'http://live-icy.gss.dr.dk/A/A05H.mp3',
        'duration': 60,
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

        self.url = args['url']
        if not self.url.endswith('mp3'):
            # Possibly a playlist file
            remote_file = requests.get(self.url)
            self.url = remote_file.content.decode('utf8').strip()

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
        ingest(filename, self.station)

        try:
            os.remove(filename)
        except WindowsError:
            print("Can't delete file: %s" % filename)
        except IOError, e:
            print(e)

    def remove_files(self):
        for mp3_file in glob.glob(self.target_dir + '/*.mp3')[:-1]:
            try:
                os.remove(mp3_file)
            except WindowsError:
                print("Can't delete file: %s" % mp3_file)
            except IOError, e:
                print(e)


if __name__ == "__main__":
    RadioRecorder(args=ARGS).record()
