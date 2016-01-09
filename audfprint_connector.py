import audfprint.audfprint as afp
from audfprint import hash_table
import docopt


USAGE = afp.USAGE
argv = ['new',
        '--verbose', '1',
        "--density", "70",
        "--fanout", "8",
        "--bucketsize", "100",
        "--ncores", "1",
        "--search-depth", "100",
        "--min-count", "5",
        "--hashbits", "20"]
args = docopt.docopt(USAGE, version=1, argv=argv)

# TODO Strip out matplotlib and librosa from audfprint. No use on the server and takes up space


class Connector:
    def __init__(self):
        self.args = args
        self.verbose = False
        self.reporter = afp.setup_reporter(self.args)
        # Setup analyzer
        self.args.shifts = 1
        self.analyzer = afp.setup_analyzer(self.args)
        self.analyzer.fail_on_error = False
        # Setup matcher
        self.args.shifts = 4
        self.match_analyzer = afp.setup_analyzer(self.args)
        self.matcher = afp.setup_matcher(self.args)

        self.ncores = 1  # Not very CPU intensitive at this point
        self.hash_tab = self.new_hashtable()  # We should keep an array of tables

    def match(self, audio_file):
        result, durd, num_hashes = self.matcher.match_file(self.match_analyzer, self.hash_tab, audio_file)

        if len(result) > 0:
            print(result)
            tophitid, nhashaligned, aligntime, nhashraw, rank, min_time, max_time = result[0]
            match_station = self.hash_tab.names[tophitid]
            return match_station, nhashaligned
        else:
            return None, 0

    def ingest_stream(self, audio_stream):
        # TODO ingest directly from stream instead of saving to file first
        pass

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

