from recording import mic_recorder
from datetime import datetime
import requests
import time

recording_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
rec = mic_recorder.Recorder(channels=1)
with rec.open('mic_recording.wav', 'wb') as recfile:
    recfile.record(duration=30.0)

time.sleep(60)

# url = 'http://localhost:5000/match/'
# url = 'http://192.168.99.100:8000/match/'
url = 'http://46.101.177.208:8000/match/'
files = {'audio_file': open('mic_recording.wav', 'rb')}
response = requests.post(url, files=files, data={'recording_time': recording_time,
                                                 'user_id': 'Simon',
                                                 'file_type': 'wav'})
print("Received match: %s" % response.text)