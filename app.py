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
# import wave
# import contextlib
import hashlib
import json
from gevent.pywsgi import WSGIServer

dt_format = '%Y-%m-%d %H:%M:%S'
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
        task, data = task_queue.get()  # Blocking

        if 'match' in task:
            tmp_file = data
            max_hashes = 0
            match_station = match_time = None

            matches = afp.match_file(tmp_file)
            for station in matches.keys():
                n_total_hashes = np.sum(matches[station]['hashes'])
                if n_total_hashes > max_hashes:
                    max_hashes = n_total_hashes
                    match_station = station
                    match_time = matches[station]['time'][np.argmax(matches[station]['hashes'])]
                    
                for i in range(len(matches[station]['hashes'])):
                    app.logger.info("Match: %s, hashes: %d, time: %s" % (station, matches[station]['hashes'][i], matches[station]['time'][i]))
            
            # Send result back to requester
            result_queue.put((max_hashes, match_station, match_time))

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

    recording_processes = dict()
    # Define producer processes
    for n, radio_station in enumerate(stations):
        recording_processes[n] = (Process(target=radiorec.record_stream,
                                          args=(radio_station, queue),
                                          name=radio_station.get('name', '')), 
                                  radio_station)
    # Run processes
    for n in recording_processes:
        (p, radio_station) = recording_processes[n]
        app.logger.info("Starting recording: %s" % p.name)
        p.start()

    while True:
        # If they shut down, restart
        for n in recording_processes:
            (p, radio_station) = recording_processes[n]
            if not p.is_alive():
                app.logger.info("Restarting recording: %s" % p.name)
                p.join()  # Tidy up?
                del recording_processes[n]  # Delete from dict
                # Define new process
                p = Process(target=radiorec.record_stream,
                            args=(radio_station, queue),
                            name=radio_station.get('name', ''))
                p.start()
                recording_processes[n] = (p, radio_station)
                
            # Wait a bit before retrying
            time.sleep(10)
                

@app.route('/match/', methods=['POST'])
def station_match():
    recording_time = request.form.get('recording_time', '')
    user_id = request.form.get('user_id', '')
    file_type = request.form.get('file_type', 'wav')
    app.logger.info("Recording time: %s" % recording_time)

    # Save file to disk
    # TODO load file directly instead of saving to disk
    tmp_file = 'tmp_audio' + '.' + file_type
    try:
        request.files.get('audio_file').save(tmp_file)
    except AttributeError:
        app.logger.info("No file attached")
        
    # Wait a few second for the file to be saved
    time.sleep(5)

    # Pass task to task queue
    task_queue.put(('match', tmp_file))

    # Wait for response
    try:
        hash_count, station, match_time = result_queue.get(timeout=60)
    except Empty:
        hash_count, station = 0, ''

    # Commit match to database
    if hash_count > 4:
        # Generate unique id
        id = hashlib.md5(user_id + station + match_time).hexdigest()
    
        table.put_item(Item=dict(id=id,
                                 station=station,
                                 user_id=user_id,
                                 hash_count=int(hash_count),
                                 match_time=match_time,
                                 recording_time=recording_time,
                                 timestamp=datetime.now(pytz.timezone('Europe/Copenhagen')).strftime(dt_format),
                                 user_answer="None"))

        return json.dumps({'station': station, 
                            'match_time': match_time, 
                            'hash_count': hash_count, 
                            'id': id}) 
    return ('', 204)


def reset_hashtable(connector):
    # TODO reset only last half of the table
    connector.hash_tab.reset()


def list_hashtable(connector):
    connector.hash_tab.list(app.logger.info)


@app.route('/answer/', methods=['POST'])
def match_answer():
    id = request.form.get('id', 'None')
    answer = request.form.get('answer', 'None')
    
    if id is not 'None':
        table.update_item(
            Key={
                'id': id
            },
            UpdateExpression='SET user_answer = :val1',
            ExpressionAttributeValues={
                ':val1': answer
            }
        )
    
    app.logger.info("answer: %s" % answer)
    return 'OK'
    

@app.route('/', methods=['GET'])
def hello():
    return 'Hello'


if __name__ == '__main__':
    # Setup radio recording
    radio_stations = [
        {'name': 'P1',
         'url': 'http://live-icy.gss.dr.dk/A/A03H.mp3'},
        {'name': 'P2',
         'url': 'http://live-icy.gss.dr.dk/A/A04H.mp3'},
        {'name': 'P3',
         'url': 'http://live-icy.gss.dr.dk/A/A05H.mp3'},
        {'name': 'P4_Kobenhavn',
         'url': 'http://live-icy.gss.dr.dk/A/A08H.mp3'},
        {'name': 'P5',
         'url': 'http://live-icy.gss.dr.dk/A/A25H.mp3'},
        {'name': 'P6',
         'url': 'http://live-icy.gss.dr.dk/A/A29H.mp3'},
        {'name': 'P7',
         'url': 'http://live-icy.gss.dr.dk/A/A21H.mp3'},
        {'name': 'P8',
         'url': 'http://live-icy.gss.dr.dk/A/A22H.mp3'}]

    # Define queues
    task_queue = Queue()
    result_queue = Queue()

    # Define a producer queue/process
    producer_process = Process(target=keep_recording, args=(task_queue, radio_stations))
    producer_process.start()

    # Define consumer process
    audfprint_process = Process(target=consumer, args=(task_queue, result_queue))
    audfprint_process.start()

    # Dev server
    # app.run(host='0.0.0.0', port=5000, use_reloader=False)

    http_server = WSGIServer(('', 5000), app)
    http_server.serve_forever()