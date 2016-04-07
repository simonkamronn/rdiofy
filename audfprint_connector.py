import audfprint.audfprint as afp
from audfprint import hash_table, audfprint_analyze
from audfprint.audio_read import audio_read
import docopt
from audfprint.audio_read import UnsupportedError
from audfprint.postgres_db import PostgreSQLDB

USAGE = afp.USAGE
ARGV = ["new",
        "--verbose", "0",
        "--density", "70",
        "--fanout", "15",
        "--bucketsize", "1",
        "--ncores", "1",
        "--search-depth", "1",  # Number of ids for each hash to save
        "--min-count", "1",
        "--hashbits", "26",  # Bits used to save hashes. Number of hashes to save = 2^hashbits
        "--continue-on-error", "True",
        "--sample_rate", "8000",
        "--max-matches", "5",
        "--maxtime", "8192"]
ARGS = docopt.docopt(USAGE, version=1, argv=ARGV)


class Connector(object):
    def __init__(self, args=ARGS):
        self.args = args
        self.verbose = False
        # Setup analyzer
        self.args.shifts = 1
        self.analyzer = afp.setup_analyzer(self.args)
        # Setup matcher
        self.args.shifts = 1
        self.match_analyzer = afp.setup_analyzer(self.args)
        self.matcher = afp.setup_matcher(self.args)
        self.ncores = 1  # Not very CPU intensitive at this point
        self.sample_rate = int(args['--sample_rate'])
        self.using_hashtable = args['--hashtable']

        # Database connection
        if self.using_hashtable:
            self.hash_tab = self.new_hashtable()
            print("Using Numpy hashtable")
        else:
            self.db = PostgreSQLDB(drop_tables=False)
            print("Using PostgreSQL database")

    def match_file(self, audio_file):
        if self.using_hashtable:
            return self.match_file_hash_table(audio_file)
        else:
            return self.match_file_db(audio_file)

    def match_file_db(self, audio_file):
        try:
            array, sr = audio_read(audio_file, sr=self.sample_rate, channels=1)
            hashes = self.fingerprint_array(array)
            matches = self.db.return_matches(hashes)
            if len(matches) > 0:
                print("Number of hashes: %d\nNumber of matches: %d" % (len(hashes), len(matches)))
                best_sids = self.db.get_best_sids(matches)
                results = self.db.align_matches(matches, best_sids)
            else:
                results = []
        except UnsupportedError:
            results = None

        matches = dict()
        if results is not None:
            for result in results:
                station, time = result['song_name'].split('.')
                if station not in matches.keys():
                    matches[station] = {'hashes': [result['confidence']],
                                        'time': [time]}
                else:
                    matches[station]['hashes'] += [result['confidence']]
                    matches[station]['time'] += [time]
        return matches

    def match_file_hash_table(self, audio_file):
        """
        Read file into numpy array, fingerprint to hashes and match from hash table
        """
        try: 
            array, sr = audio_read(audio_file, sr=self.sample_rate, channels=1)
            hashes = self.fingerprint_array(array)
            result = self.matcher.match_hashes(self.hash_tab, hashes)
        except UnsupportedError:
            result = []

        # The audio clip is likely spanning recordings so we will return multiple results with high score
        matches = dict()
        for r in result:
            id, nhashaligned, aligntime, nhashraw, rank, min_time, max_time = r
            if nhashaligned > 10:
                station, time = self.hash_tab.names[id].split('.')
                if station not in matches.keys():
                    matches[station] = {'hashes': [nhashaligned],
                                        'time': [time]}
                else:
                    matches[station]['hashes'] += [nhashaligned]
                    matches[station]['time'] += [time]
        
        return matches

    def ingest_array(self, array, store_name):
        hashes = self.fingerprint_array(array)
        if self.verbose:
            print('ingested: %s, nhash: %d' % (store_name, len(hashes)))
        if self.using_hashtable:
            self.hash_tab.store(store_name, hashes)
        else:
            self.db.store(store_name, hashes)
        return len(hashes)

    def ingest_file(self, audio_file, store_name):
        hashes = self.analyzer.wavfile2hashes(audio_file)
        if self.using_hashtable:
            self.hash_tab.store(store_name, hashes)
        else:
            self.db.store(store_name, hashes)

        nhash = len(hashes)
        if self.verbose:
            print('ingested: %s, nhash: %d' % (store_name, nhash))
        return nhash

    def new_hashtable(self):
        hash_tab = hash_table.HashTable(
                hashbits=int(self.args['--hashbits']),
                depth=int(self.args['--bucketsize']),
                maxtime=int(self.args['--maxtime']))
        return hash_tab

    def fingerprint_array(self, array):
        peaks = self.analyzer.find_peaks(array, self.sample_rate)
        query_hashes = audfprint_analyze.landmarks2hashes(self.analyzer.peaks2landmarks(peaks))
        return sorted(list(set(query_hashes)))
