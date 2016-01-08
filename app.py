from flask import Flask, request
from audfprint_connector import Connector
from datetime import datetime
from glob import glob
import logging
from flask_apscheduler import APScheduler
from recording import radiorec
import boto3
tmp_path = 'tmp_audio.mp3'
dt_format = '%Y-%m-%d %H:%M:%S'

# Initialize logging for APScheduler
logging.basicConfig()

# Create connector to audfprint
afp = Connector()
afp.verbose = True

# Setup radio recording
radiorec_args = radiorec.ARGS
radiorec_args['duration'] = 60  # Seconds
radiorec_args['dt_format'] = dt_format
radiorec_args['ingest'] = afp.ingest
radiorec_args['url'] = 'http://live-icy.gss.dr.dk/A/A08H.mp3.m3u'
radiorec_args['station'] = "P4_Kobenhavn"

# Create recorder object
recorder = radiorec.RadioRecorder(args=radiorec_args)
record = recorder.record

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', endpoint_url="https://dynamodb.eu-central-1.amazonaws.com")
table = dynamodb.Table('audio_matches')


class Config(object):
    JOBS = [
        {
            'id': 'record',
            'func': '__main__:record',
            'args': (afp.ingest, ),
            'trigger': 'interval',
            'seconds': 60
        },
        {
            'id': 'reset hashtable',
            'func': '__main__:reset_hashtable',
            'args': (afp, ),
            'trigger': 'interval',
            'minutes': 10
        }
    ]
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': False,
        'max_instances': 5
    }
    SCHEDULER_EXECUTORS = {
        'default': {'type': 'threadpool', 'max_workers': 20}
    }
    SCHEDULER_VIEWS_ENABLED = True
    DEBUG = False

app = Flask(__name__)
app.config.from_object(Config())
app.logger.setLevel(logging.INFO)  # use the native logger of flask


def init_audio(afp):
    for audio in glob('music/Ghost Reveries/*.mp3'):
        nhash = afp.ingest(audio)
        if nhash > 0:
            app.logger.info('Ingested %d hashes from %s' % (nhash, audio))
# init_audio(afp)


@app.route('/match/', methods=['POST'])
def station_match():
    app.logger.info('Got a new match request')
    recording_time = request.form.get('recording_time', '')
    user_id = request.form.get('user_id', '')
    if recording_time is not '':
        app.logger.info("Recording time: %s" % recording_time)

    # Save file to disk
    # TODO load file directly instead of saving to disk
    request.files.get('audio_file').save(tmp_path)

    # Match the file
    match, nhash = afp.match(tmp_path)
    app.logger.info("Match: %s, hashes: %d" % (match, nhash))

    # Commit match to database
    if nhash > 0:
        table.put_item(Item=dict(match_id=match,
                                 user_id=user_id,
                                 hash_count=nhash,
                                 recording_time=recording_time,
                                 timestamp=datetime.now().strftime(dt_format)))

    return match if match is not None else ('', 204)


def reset_hashtable(connector):
    # TODO reset only last half of the table
    connector.hash_tab.reset()


def list_hashtable(connector):
    connector.hash_tab.list(app.logger.info)


# Start scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
