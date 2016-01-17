from datetime import datetime
import requests
from glob import glob
SAMPLE_RATE = 11025

url = 'http://localhost:5000/match/'
# url = 'http://192.168.99.100:8000/match/'
# url = 'http://46.101.177.208:8000/match/'

for wav_file in glob('recordings/*.wav'):
    files = {'audio_file': open(wav_file, 'rb')}
    response = requests.post(url, files=files, data={'recording_time': wav_file.strip(),
                                                     'user_id': 'Simon',
                                                     'file_type': 'wav'})
    print("Received match: %s" % response.text)