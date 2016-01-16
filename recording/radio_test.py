from datetime import datetime
import requests
import time
from audfprint.audio_read import FFmpegAudioFile
import wave
import contextlib
import numpy as np

url = 'http://live-icy.gss.dr.dk/A/A03L.mp3'
recording_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

with contextlib.closing(wave.open('radio_test.wav', 'w')) as of:
    of.setframerate(44100)
    of.setnchannels(1)
    of.setsampwidth(2)
    with FFmpegAudioFile(url, channels=1, sample_rate=44100, block_size=65536) as f:
        for idx, buf in enumerate(f):
            of.writeframes(buf)
            if idx > 50: break

time.sleep(60)

url = 'http://localhost:5000/match/'
# url = 'http://192.168.99.100:8000/match/'
# url = 'http://46.101.177.208:8000/match/'
files = {'audio_file': open('radio_test.wav', 'rb')}
response = requests.post(url, files=files, data={'recording_time': recording_time,
                                                 'user_id': 'Simon',
                                                 'file_type': 'wav'})
print("Received match: %s" % response.text)