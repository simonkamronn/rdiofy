from flask import Flask, request
from audfprint_connector import Connector
from datetime import datetime
import pytz
import logging
from recording import radiorec
import time
from multiprocessing import Process, Queue
from audfprint.audio_read import buf_to_float
import numpy as np
# import wave
# import contextlib
from gevent.pywsgi import WSGIServer

dt_format = '%Y-%m-%d %H:%M:%S'
logging.basicConfig()


class Config(object):
    DEBUG = False

# Application setup
app = Flask(__name__)
app.config.from_object(Config())
app.logger.setLevel(logging.INFO)  # use the native logger in flask


def consumer(task_queue):
    # Create connector to audfprint
    afp = Connector()
    app.logger.info("Consumer started")
    
    while True:
        task, data = task_queue.get()  # Blocking

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
        app.logger.info("Ingesting %s" % (station + '.' + cur_dt))
        afp.ingest_array(array, station + '.' + cur_dt)
        print('Ingested object')


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
    for n in recording_processes.keys():
        (p, radio_station) = recording_processes[n]
        app.logger.info("Starting recording: %s" % p.name)
        p.start()

    while True:
        # If they shut down, restart
        for n in recording_processes.keys():
            (p, radio_station) = recording_processes[n]
            if not p.is_alive():
                app.logger.info("Restarting recording: %s" % p.name)
                p.join(1)  # Tidy up?
                del recording_processes[n]  # Delete from dict
                # Define new process
                p = Process(target=radiorec.record_stream,
                            args=(radio_station, queue),
                            name=radio_station.get('name', ''))
                p.start()
                recording_processes[n] = (p, radio_station)

            # Wait a bit before retrying
            time.sleep(1)


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

    # radio_stations = []

    # Define queues
    task_queue = Queue()

    # Define a producer queue/process
    producer_process = Process(target=keep_recording, args=(task_queue, radio_stations), name='producer')
    producer_process.start()

    # Define consumer process
    consumer_process = Process(target=consumer, args=(task_queue,), name='consumer')
    consumer_process.start()

    # Dev server
    # app.run(host='0.0.0.0', port=5000, use_reloader=False)

    http_server = WSGIServer(('', 5000), app)
    http_server.serve_forever()

    try:
        [p.join(1) for p in [producer_process, consumer_process]]
    except KeyboardInterrupt:
        print('Exiting')