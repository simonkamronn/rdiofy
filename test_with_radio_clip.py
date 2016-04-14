from datetime import datetime
import requests
import time
from audfprint.audio_read import FFmpegAudioFile
import wave
import contextlib


SAMPLE_RATE = 8000
url = 'http://live-icy.gss.dr.dk/A/A08H.mp3'
recording_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

recordings = []
for n in range(1, 10):
    with contextlib.closing(wave.open('radio_recordings/radio_test_%d.wav' % n, 'wb')) as of:
        recordings.append('radio_recordings/radio_test_%d.wav' % n)
        of.setframerate(SAMPLE_RATE)
        of.setnchannels(1)
        of.setsampwidth(2)
        with FFmpegAudioFile(url, channels=1, sample_rate=SAMPLE_RATE, block_size=4096) as f:
            for idx, buf in enumerate(f):
                of.writeframes(buf)
                if idx > 100: break

time.sleep(30)

urls = []
urls += ['http://localhost:5000/match/']
# urls += ['http://172.17.0.2:5000/match']
# urls += ['http://192.168.99.100:8000/match/']
# urls += ['http://46.101.141.191:8000/match/']
# urls += ['http://52.49.153.98/match/']
# urls += ['http://pervasivesounds.com/match/']
for recording in recordings:
    for url in urls:
        files = {'audio_file': open(recording, 'rb')}
        response = requests.post(url,
                                 files=files,
                                 data={'recording_time': recording_time,
                                       'user_id': 'Simon_laptop_stream',
                                       'file_type': 'wav'},
                                 timeout=60)
        print("Received match: %s" % response.text)
