import audfprint.audfprint as afp
from audfprint import hash_table
import docopt
import time
import glob

USAGE = afp.USAGE
mp3_files = glob.glob('audiotest/*.mp3')
cmd = "match"
argv = [cmd,
        "--dbase", "fdbase.pklz",
        "--verbose", 1]

if isinstance(mp3_files, list):
    for mp3_file in mp3_files:
        argv.append(mp3_file)
else:
    argv.append(mp3_files)

args = docopt.docopt(USAGE, version=1, argv=argv)
print(args)

report = afp.setup_reporter(args)
analyzer = afp.setup_analyzer(args)

# Keep track of wall time
initticks = time.clock()

precomp_type = 'hashes'
dbasename = args['--dbase']

# Command line sanity.
if args["--maxtimebits"]:
    args["--maxtimebits"] = int(args["--maxtimebits"])
else:
    args["--maxtimebits"] = hash_table._bitsfor(int(args["--maxtime"]))

if cmd in ["new", "newmerge"]:
    hash_tab = hash_table.HashTable(
        hashbits=int(args['--hashbits']),
        depth=int(args['--bucketsize']),
        maxtime=(1 << int(args['--maxtimebits'])))
else:
    hash_tab = hash_table.HashTable(dbasename)

# Create a matcher
matcher = afp.setup_matcher(args)
filename_iter = afp.filename_list_iterator(args['<file>'], args['--wavdir'], args['--wavext'], args['--list'])

# How many processors to use (multiprocessing)
ncores = int(args['--ncores'])
if ncores > 1:  # not for merge, list and remove
    # merge/newmerge/list/remove are always single-thread processes
    afp.do_cmd_multiproc(cmd, analyzer, hash_tab, filename_iter,
                         matcher, args['--precompdir'],
                         precomp_type, report,
                         skip_existing=args['--skip-existing'],
                         ncores=ncores)
else:
    afp.do_cmd(cmd, analyzer, hash_tab, filename_iter,
               matcher, args['--precompdir'], precomp_type, report,
               skip_existing=args['--skip-existing'])

elapsedtime = time.clock() - initticks
if analyzer and analyzer.soundfiletotaldur > 0.:
    print("Processed "
          + "%d files (%.1f s total dur) in %.1f s sec = %.3f x RT" \
          % (analyzer.soundfilecount, analyzer.soundfiletotaldur,
             elapsedtime, (elapsedtime/analyzer.soundfiletotaldur)))

# Save the hash table file if it has been modified
if hash_tab and hash_tab.dirty:
    # We already created the directory, if "new".
    hash_tab.save(dbasename)
