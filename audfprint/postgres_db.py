from __future__ import print_function
from postgres import Postgres
from itertools import izip_longest


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
        self.db = Postgres(u"postgres://postgres:postgres@postgres/postgres")
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
            values.append((hash_.astype('int'), sid, time_))

        with self.db.get_cursor() as cur:
            for split_values in grouper(values, 1000):
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
        return self.db.one(self.SELECT_SONG, (sid,))

    def return_matches(self, hashes):
        mapper = {}
        for offset, hash in hashes:
            mapper[hash] = offset

        # Get an iteratable of all the hashes we need
        values = mapper.keys()

        if hashes is not None:
            for split_values in grouper(values, 1000):
                query = self.SELECT_MULTIPLE
                query %= ', '.join(["%s"] * len(split_values))

                res = self.db.all(query, split_values, back_as=tuple)
                for (hash, sid, offset) in res:
                    yield(sid, offset - mapper[hash])

    def get_hits(self, hashes):
        return self.return_matches(hashes)

    def align_matches(self, matches):
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
        for tup in matches:
            sid, diff = tup
            if diff not in diff_counter:
                diff_counter[diff] = {}
            if sid not in diff_counter[diff]:
                diff_counter[diff][sid] = 0
            diff_counter[diff][sid] += 1

            if diff_counter[diff][sid] > largest_count:
                largest = diff
                largest_count = diff_counter[diff][sid]
                song_id = sid

        # extract idenfication
        song = self.get_song_by_id(song_id)
        if song:
            songname = song
        else:
            return None

        song = {
            'song_id': song_id,
            'song_name': songname,
            'confidence': largest_count,
            'offset': int(largest)
        }
        return song


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return (filter(None, values) for values in izip_longest(fillvalue=fillvalue, *args))
