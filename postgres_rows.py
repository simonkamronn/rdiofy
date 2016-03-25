from postgres import Postgres


FIELD_SONG_ID = 'song_id'
FIELD_SONGNAME = 'song_name'
FIELD_OFFSET = 'time'
FIELD_HASH = 'hash'
SONG_ID = 'song_id'
SONG_NAME = 'song_name'
CONFIDENCE = 'confidence'
MATCH_TIME = 'match_time'
OFFSET = 'time'
OFFSET_SECS = 'offset_seconds'
FINGERPRINTS_TABLENAME = 'fingerprints'
SONGS_TABLENAME = 'songs'
COUNT_ROWS = "SELECT reltuples AS approximate_row_count FROM pg_class WHERE relname = '%s';"
postgres_url = '52.49.153.98:5432'

db = Postgres(u"postgres://postgres:pervasivesounds@%s/hashes" % postgres_url)
print("Number of hashes: %d" % db.one(COUNT_ROWS % FINGERPRINTS_TABLENAME))
# print("Number of songs: %d" % db.one(COUNT_ROWS % SONGS_TABLENAME))

print("\nSong table first and last element:")
print(db.one("SELECT %s, %s FROM %s ORDER BY %s ASC LIMIT 1" % (FIELD_SONG_ID, FIELD_SONGNAME, SONGS_TABLENAME, FIELD_SONG_ID)))
print(db.one("SELECT %s, %s FROM %s ORDER BY %s DESC LIMIT 1" % (FIELD_SONG_ID, FIELD_SONGNAME, SONGS_TABLENAME, FIELD_SONG_ID)))

print("\nFingerprint table first and last element:")
first_hash = db.one("SELECT %s, %s FROM %s ORDER BY %s ASC LIMIT 1" % (FIELD_HASH, FIELD_SONG_ID, FINGERPRINTS_TABLENAME, FIELD_SONG_ID))
print(db.one("SELECT * FROM %s WHERE %s=%d;" % (SONGS_TABLENAME, FIELD_SONG_ID, first_hash.song_id)))
last_hash = db.one("SELECT %s, %s FROM %s ORDER BY %s DESC LIMIT 1" % (FIELD_HASH, FIELD_SONG_ID, FINGERPRINTS_TABLENAME, FIELD_SONG_ID))
print(db.one("SELECT * FROM %s WHERE %s=%d;" % (SONGS_TABLENAME, FIELD_SONG_ID, last_hash.song_id)))

print("\nSize of database: %s" % db.one("SELECT pg_size_pretty(pg_database_size('hashes'));"))
print("Size of %s table: %s" % (FINGERPRINTS_TABLENAME, db.one("SELECT pg_size_pretty(pg_table_size('%s'));" % FINGERPRINTS_TABLENAME)))
print("Size of %s table: %s" % (SONGS_TABLENAME, db.one("SELECT pg_size_pretty(pg_table_size('%s'));" % SONGS_TABLENAME)))