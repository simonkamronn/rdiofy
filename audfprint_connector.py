import audfprint.audfprint as afp
from audfprint import hash_table, audfprint_analyze
from audfprint.audio_read import audio_read
import docopt
from audfprint.audio_read import UnsupportedError

USAGE = afp.USAGE
ARGV = ["new",
        "--verbose", "0",
        "--density", "70",
        "--fanout", "8",
        "--bucketsize", "100",
        "--ncores", "1",
        "--search-depth", "10",  # Number of ids for each hash to save
        "--min-count", "1",
        "--hashbits", "20",  # Bits used to save hashes. Number of hashes to save = 2^hashbits
        "--continue-on-error", "False",
        "--sample_rate", "8000",
        "--max-matches", "5",
        "--maxtime", "4096"]
ARGS = docopt.docopt(USAGE, version=1, argv=ARGV)

class Connector(object):
    def __init__(self, args=ARGS):
        self.args = args
        self.verbose = False
        # Setup analyzer
        self.args.shifts = 1
        self.analyzer = afp.setup_analyzer(self.args)
        # Setup matcher
        self.args.shifts = 4
        self.match_analyzer = afp.setup_analyzer(self.args)
        self.matcher = afp.setup_matcher(self.args)

        self.ncores = 1  # Not very CPU intensitive at this point
        self.hash_tab = self.new_hashtable()
        self.sample_rate = int(args['--sample_rate'])

    def match_file(self, audio_file):
        """
        Read file into numpy array, fingerprint to hashes and match from hash table
        """
        try: 
            array, sr = audio_read(audio_file, sr=self.sample_rate, channels=1)
            hashes = self.fingerprint_array(array)
            result = self.matcher.match_hashes(self.hash_tab, hashes)
        except UnsupportedError:
            hashes = []
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
        self.hash_tab.store(store_name, hashes)
        return len(hashes)

    def ingest_file(self, audio_file, store_name):
        hashes = self.analyzer.wavfile2hashes(audio_file)
        self.hash_tab.store(store_name, hashes)

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
        # TODO what sr to pass to find_peaks. The real or target?
        peaks = self.analyzer.find_peaks(array, self.sample_rate)
        query_hashes = audfprint_analyze.landmarks2hashes(self.analyzer.peaks2landmarks(peaks))
        return sorted(list(set(query_hashes)))
