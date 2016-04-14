from __future__ import print_function
from postgres import Postgres
from itertools import zip_longest
import os
import numpy as np

class PostgreSQLDB(object):
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
    db = None

    # tables
    FINGERPRINTS_TABLENAME = 'fingerprints'
    SONGS_TABLENAME = 'songs'

    # creates
    CREATE_FINGERPRINTS_TABLE = """
        CREATE TABLE IF NOT EXISTS "%s"(
             "%s" INT PRIMARY KEY NOT NULL,
             "%s" INT NOT NULL,
             "%s" INT NOT NULL);""" % (
        FINGERPRINTS_TABLENAME,
        FIELD_HASH, FIELD_SONG_ID, FIELD_OFFSET)
    
    CREATE_SONGS_TABLE = \
        """CREATE TABLE IF NOT EXISTS "%s"(
                "%s" SERIAL PRIMARY KEY ,
                "%s" varchar(250) NOT NULL);""" % \
        (SONGS_TABLENAME, FIELD_SONG_ID, FIELD_SONGNAME)

    SELECT_SONG = """SELECT %s FROM %s WHERE %s = %%s;""" \
                  % (FIELD_SONGNAME, SONGS_TABLENAME, FIELD_SONG_ID)

    # inserts fingerprint. Update if existing
    INSERT_FINGERPRINT = \
        """INSERT INTO %s VALUES (%%s, %%s, %%s)
           ON
             CONFLICT (%s)
           DO UPDATE SET
             %s = EXCLUDED.%s,
             %s = EXCLUDED.%s;""" \
        % (FINGERPRINTS_TABLENAME, FIELD_HASH, FIELD_SONG_ID, FIELD_SONG_ID, FIELD_OFFSET, FIELD_OFFSET)

    INSERT_SONG = "INSERT INTO %s (%s) VALUES (%%s);" % (SONGS_TABLENAME, FIELD_SONGNAME)

    SELECT_MULTIPLE = """SELECT %s, %s, %s FROM %s WHERE %s IN (%%s);""" \
                      % (FIELD_HASH, FIELD_SONG_ID, FIELD_OFFSET,
                         FINGERPRINTS_TABLENAME, FIELD_HASH)

    def __init__(self, drop_tables=False):
        super(PostgreSQLDB, self).__init__()
        if os.environ.get('DOCKERCLOUD_SERVICE_HOSTNAME', None) is not None:
            self.db = Postgres(u"postgres://postgres:pervasivesounds@52.49.153.98/hashes")

            # self.db = Postgres(u"postgres://postgres:pervasivesounds@postgres/hashes")
        else:
            # self.db = Postgres(u"postgres://postgres:atiG0lddng@localhost/postgres")
            self.db = Postgres(u"postgres://postgres:pervasivesounds@52.49.153.98/hashes")

        if drop_tables:
            self.db.run("DROP TABLE IF EXISTS %s CASCADE" % self.SONGS_TABLENAME)
            self.db.run("DROP TABLE IF EXISTS %s CASCADE" % self.FINGERPRINTS_TABLENAME)

        self.db.run(self.CREATE_SONGS_TABLE)
        self.db.run(self.CREATE_FINGERPRINTS_TABLE)

    def store(self, name, hashes):
        sid = self.insert_song(name)
        self.insert_hashes(sid, hashes)

    def insert_hash(self, song_id, hash, offset):
        self.db.run(self.INSERT_FINGERPRINT, (hash, song_id, offset))

    def insert_hashes(self, sid, hashes):
        values = []
        for time_, hash_ in hashes:
            values.append((int(hash_), sid, time_))

        with self.db.get_cursor() as cur:
            for split_values in batch(values, 1000):
                cur.executemany(self.INSERT_FINGERPRINT, split_values)

    def insert_song(self, songname):
        """
        Inserts song in the database and returns the ID of the inserted record.
        """
        self.db.run(self.INSERT_SONG, (songname,))
        return self.db.one("SELECT %s FROM %s ORDER BY %s DESC LIMIT 1" %
                           (self.FIELD_SONG_ID, self.SONGS_TABLENAME, self.FIELD_SONG_ID))

    def get_song_by_id(self, sid):
        """
        Returns song by its ID.
        """
        return self.db.one(self.SELECT_SONG, (int(sid),))

    def return_matches(self, hashes):
        mapper = {}
        for offset, hash in hashes:
            mapper[int(hash)] = offset

        # Get an iteratable of all the hashes we need
        values = list(mapper.keys())

        res = []
        if hashes is not None:
            for split_values in batch(values, 100):
                query = self.SELECT_MULTIPLE
                query %= ', '.join(["%s"] * len(split_values))

                [res.append(r) for r in self.db.all(query, split_values, back_as=tuple)]
            return np.asarray([(sid, offset - mapper[hash]) for (hash, sid, offset) in res])

    def get_best_sids(self, matches):
        unique, counts = np.unique(matches[:, 0], return_counts=True)
        return unique[np.argsort(counts)[::-1][:np.minimum(len(counts), 20)]]

    def align_matches(self, matches, sids):
        """
            Finds hash matches that align in time with other matches and finds
            consensus about which hashes are "true" signal from the audio.

            Returns a dictionary with match information.
        """
        # align by diffs
        diff_counter = {}
        largest = 0
        largest_count = 0
        song_id = -1
        for sid in sids:
            for sid, diff in matches[matches[:, 0] == sid]:
                if sid not in diff_counter:
                    diff_counter[sid] = {}
                if diff not in diff_counter[sid]:
                    diff_counter[sid][diff] = 0
                diff_counter[sid][diff] += 1

                if diff_counter[sid][diff] > largest_count:
                    largest = diff
                    largest_count = diff_counter[sid][diff]
                    song_id = sid

        # total_count = {}
        # for sid in diff_counter.keys():
        #     total_count[sid] = np.sum(diff_counter[sid].values)

        songs = []
        for sid in diff_counter.keys():
            song_name = self.get_song_by_id(sid)
            for diff in diff_counter[sid].keys():
                confidence = diff_counter[sid][diff]
                if confidence > 4:
                    songs.append({
                        'song_id': song_id,
                        'song_name': song_name,
                        'confidence': confidence,
                        'offset': diff
                    })
        return songs


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]
