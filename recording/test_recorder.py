from recording import radiorec
from audfprint_connector import Connector

# Create connector to audfprint
afp = Connector()
afp.verbose = True

# Setup radio recording
radiorec_args = radiorec.ARGS
radiorec_args['duration'] = 10  # Seconds
radiorec_args['ingest'] = afp.ingest
radiorec_args['target_dir'] = '.'

# Create recorder object
recorder = radiorec.RadioRecorder(args=radiorec_args)

recorder.record()
recorder.conn.close()

