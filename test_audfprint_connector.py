from audfprint_connector import Connector
from glob import glob


audio_ref_files = glob('music/Ghost Reveries/*.mp3')
audio_test_files = glob('audiotest/*.mp3')
afp = Connector()

for audio in audio_ref_files:
    nhash = afp.ingest(audio)
    if nhash > 0:
        print('Ingested %d hashes from %s' % (nhash, audio))

for audio in audio_test_files:
    result = afp.match(audio)
    print('Matched to: %s' % result)
