import requests
from glob import glob
from datetime import datetime

test_files = glob('audiotest/*.mp3')
url = 'http://localhost:5000/match/'

for test_file in test_files:
    files = {'audio_file': open(test_file, 'rb')}
    print('Requesting match for: %s' % test_file)
    response = requests.post(url, files=files, data={'recording_time': datetime.now()})
    print("Received match: %s" % response.text)
