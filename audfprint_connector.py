import audfprint.audfprint as afp
from audfprint import hash_table, audfprint_analyze
from audfprint.audio_read import audio_read
import docopt

USAGE = afp.USAGE
ARGV = ['new',
        '--verbose', '0',
        "--density", "70",
        "--fanout", "8",
        "--bucketsize", "100",
        "--ncores", "1",
        "--search-depth", "100",
        "--min-count", "1",
        "--hashbits", "20",
        '--continue-on-error', 'False'
        '--samplerate', '44100']
ARGS = docopt.docopt(USAGE, version=1, argv=ARGV)

# TODO Strip out matplotlib and librosa from audfprint. No use on the server and takes up space


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
        self.hash_tab = self.new_hashtable()  # We should keep an array of tables
        self.samplerate = args['--samplerate']

    def match_file(self, audio_file):
        """
        Read file into numpy array, fingerprint to hashes and match from hash table
        """
        array, sr = audio_read(audio_file, sr=44100, channels=1)
        hashes = self.fingerprint_array(array)
        result = self.matcher.match_hashes(self.hash_tab, hashes)
        print(result)
        
        if len(result) > 0:
            tophitid, nhashaligned, aligntime, nhashraw, rank, min_time, max_time = result[0]
            match_station = self.hash_tab.names[tophitid]
            return match_station, nhashaligned
        else:
            return None, 0

    def ingest_array(self, array, store_name):
        hashes = self.fingerprint_array(array)
        if self.verbose:
            print('ingested: %s, nhash: %d' % (store_name, len(hashes)))
        self.hash_tab.store(store_name, hashes)

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
                maxtime=4096)
        return hash_tab

    def fingerprint_array(self, array):
        # TODO what sr to pass to find_peaks. The real or target?
        peaks = self.analyzer.find_peaks(array, self.samplerate)
        query_hashes = audfprint_analyze.landmarks2hashes(self.analyzer.peaks2landmarks(peaks))
        return sorted(list(set(query_hashes)))
