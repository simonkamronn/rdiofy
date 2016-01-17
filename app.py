from flask import Flask, request
from audfprint_connector import Connector
from datetime import datetime
import pytz
import logging
from recording import radiorec
import boto3
import time
from multiprocessing import Process, Queue
from Queue import Empty
from audfprint.audio_read import buf_to_float
import numpy as np
import wave
import contextlib

dt_format = '%Y-%m-%d %H:%M:%S'

# Initialize logging for APScheduler
logging.basicConfig()

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', endpoint_url="https://dynamodb.eu-central-1.amazonaws.com")
table = dynamodb.Table('audio_matches')


class Config(object):
    DEBUG = False

# Application setup
app = Flask(__name__)
app.config.from_object(Config())
app.logger.setLevel(logging.INFO)  # use the native logger in flask


def consumer(task_queue, result_queue):
    # Create connector to audfprint
    afp = Connector()
    
    while True:
        task, data = task_queue.get()

        if 'match' in task:
            tmp_file = data
            match_station, nhashaligned = afp.match_file(tmp_file)
            app.logger.info("Match: %s, hashes: %d" % (match_station, nhashaligned))

            # Send result back to requester
            result_queue.put((nhashaligned, match_station))

        if 'ingest' in task:
            array, station = data
            cur_dt = datetime.now(pytz.timezone('Europe/Copenhagen')).strftime(dt_format)

            # # Save to file
            # file_name = 'recordings/%s_%s.wav' % (station, cur_dt.replace(':', ''))
            # with contextlib.closing(wave.open(file_name, 'w')) as of:
            #     of.setframerate(afp.sample_rate)
            #     of.setnchannels(1)
            #     of.setsampwidth(2)
            #     for buf in array:
            #         of.writeframes(buf)

            # Convert array
            array = np.ascontiguousarray(np.concatenate(
                    [buf_to_float(buf, dtype=np.float32) for buf in array]
                ), dtype=np.float32)

            # Ingest into table
            afp.ingest_array(array, station + '.' + cur_dt)


def keep_recording(queue, stations):
    app.logger.info("Starting main process")

    # Define producer processes
    recording_processes = [Process(target=radiorec.record_stream,
                                   args=(radio_station, queue),
                                   name=radio_station.get('name', ''))
                           for radio_station in stations]
    # Run processes
    for p in recording_processes:
        app.logger.info("Starting recording: %s" % p.name)
        p.start()

    while True:
        # If they shut down, restart with join
        for p in recording_processes:
            if not p.is_alive():
                app.logger.info("Restarting recording: %s" % p.name)
                p.join()


@app.route('/match/', methods=['POST'])
def station_match():
    recording_time = request.form.get('recording_time', '')
    user_id = request.form.get('user_id', '')
    file_type = request.form.get('file_type', 'wav')
    app.logger.info("Recording time: %s" % recording_time)

    # Save file to disk
    # TODO load file directly instead of saving to disk
    tmp_file = 'tmp_audio' + '.' + file_type
    request.files.get('audio_file').save(tmp_file)

    # Wait a second for the file to be saved
    time.sleep(1)

    # Pass task to task queue
    task_queue.put(('match', tmp_file))

    # Wait for response
    try:
        nhash, match = result_queue.get(timeout=60)
    except Empty:
        nhash, match = 0, ''

    # Commit match to database
    if nhash > 0:
        station, match_time = match.split('.')
        table.put_item(Item=dict(match_id=station,
                                 user_id=user_id,
                                 hash_count=int(nhash),
                                 match_time=match_time,
                                 recording_time=recording_time,
                                 timestamp=datetime.now(pytz.timezone('Europe/Copenhagen')).strftime(dt_format)))

    return match if match is not None else ('', 204)


def reset_hashtable(connector):
    # TODO reset only last half of the table
    connector.hash_tab.reset()


def list_hashtable(connector):
    connector.hash_tab.list(app.logger.info)


if __name__ == '__main__':
    # Setup radio recording
    radio_stations = [
        {'name': 'P2',
         'url': 'http://live-icy.gss.dr.dk/A/A04L.mp3'},
        {'name': 'P3',
         'url': 'http://live-icy.gss.dr.dk/A/A05L.mp3'},
        {'name': 'P4_Kobenhavn',
         'url': 'http://live-icy.gss.dr.dk/A/A08L.mp3'}]

    # Define queues
    task_queue = Queue()
    result_queue = Queue()

    # Define a producer queue/process
    producer_process = Process(target=keep_recording, args=(task_queue, radio_stations))
    producer_process.start()

    # Define consumer process
    audfprint_process = Process(target=consumer, args=(task_queue, result_queue))
    audfprint_process.start()

    app.run(host='0.0.0.0', port=5000, use_reloader=False)
