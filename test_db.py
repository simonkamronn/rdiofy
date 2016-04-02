from audfprint_connector import Connector
from audfprint.audio_read import audio_read
from glob import glob
import time

file_path = "recordings"
files = glob(file_path + '\*.wav')

afp = Connector()

time_then = time.clock()
print(files[-10])
array, sr = audio_read(files[-10], sr=8000, channels=1)

# Ingest
hashes = afp.fingerprint_array(array)
# hashes1 = hashes[:10]
# hashes2 = hashes[5:25]
# afp.db.store("tmp", hashes1)

#Match
matches = afp.db.return_matches(hashes)
best_sids = afp.db.get_best_sids(matches) if len(matches) > 0 else []
result = afp.db.align_matches(matches, best_sids)
print(result)

print("Elapsed time: %f" % (time.clock() - time_then))