import audfprint.audfprint as afp
from audfprint import hash_table, audfprint_analyze
import docopt


USAGE = afp.USAGE
argv = ['new',
        '--verbose', 'True',
        "--density", "70",
        "--fanout", "8",
        "--bucketsize", "100",
        "--ncores", "1",
        "--search-depth", "100",
        "--min-count", "5",
        "--hashbits", "20",
        '--continue-on-error', 'True']
args = docopt.docopt(USAGE, version=1, argv=argv)

# TODO Strip out matplotlib and librosa from audfprint. No use on the server and takes up space


class Connector:
    def __init__(self):
        self.args = args
        self.verbose = True
        self.reporter = afp.setup_reporter(self.args)
        # Setup analyzer
        self.args.shifts = 1
        self.analyzer = afp.setup_analyzer(self.args)
        self.analyzer.fail_on_error = False
        # Setup matcher
        self.args.shifts = 4
        self.match_analyzer = afp.setup_analyzer(self.args)
        self.match_analyzer.fail_on_error = False
        self.matcher = afp.setup_matcher(self.args)

        self.ncores = 1  # Not very CPU intensitive at this point
        self.hash_tab = self.new_hashtable()  # We should keep an array of tables

    def match(self, audio_file):
        result, durd, num_hashes = self.matcher.match_file(self.match_analyzer, self.hash_tab, audio_file)

        if len(result) > 0:
            tophitid, nhashaligned, aligntime, nhashraw, rank, min_time, max_time = result[0]
            match_station = self.hash_tab.names[tophitid]
            return match_station, nhashaligned
        else:
            return None, 0

    def ingest_array(self, audio_stream, store_name):
        peaks = self.analyzer.find_peaks(audio_stream, self.analyzer.target_sr)
        query_hashes = audfprint_analyze.landmarks2hashes(self.analyzer.peaks2landmarks(peaks))
        hashes = sorted(list(set(query_hashes)))
        self.hash_tab.store(store_name, hashes)

    def ingest(self, audio_file, store_name):
        hashes = self.analyzer.wavfile2hashes(audio_file)
        self.hash_tab.store(store_name, hashes)

        nhash = len(hashes)
        if self.verbose:
            print('ingested: %s, nhash: %d' % (store_name, nhash))
        return nhash

    def new_hashtable(self):
        hash_tab = hash_table.HashTable(
                hashbits=int(args['--hashbits']),
                depth=int(args['--bucketsize']),
                maxtime=4096)
        return hash_tab

