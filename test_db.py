from audfprint_connector import Connector
from audfprint.audio_read import audio_read


file_path = "tmp_audio.wav"
afp = Connector()

array, sr = audio_read(file_path, sr=8000, channels=1)

# Ingest
hashes = afp.fingerprint_array(array)
hashes1 = hashes[:10]
hashes2 = hashes[5:25]
afp.db.store("tmp", hashes1)

#Match
matches = afp.db.return_matches(hashes2)
result = afp.db.align_matches(matches)
print(result)