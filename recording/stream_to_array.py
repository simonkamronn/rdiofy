from __future__ import print_function
import audioread
from audioread import ffdec
import sys
import numpy as np
import wave
import contextlib

URL = 'http://live-icy.gss.dr.dk/A/A08L.mp3'

try:
    with ffdec.FFmpegAudioFile(URL, block_size=65536) as f:
        print('Input file: %i channels at %i Hz; %.1f seconds.' %
              (f.channels, f.samplerate, f.duration), file=sys.stderr)
        print('Backend:', str(type(f).__module__).split('.')[1], file=sys.stderr)

        with contextlib.closing(wave.open('temp' + '.wav', 'w')) as of:
                of.setnchannels(1)
                of.setframerate(11025)
                of.setsampwidth(2)

                data = np.empty((0))
                for i, buf in enumerate(f):
                    print(np.frombuffer(buf, np.int16).shape)
                    of.writeframes(buf)
                    if i == 5:
                        break

except audioread.DecodeError:
    print("File could not be decoded.", file=sys.stderr)
    sys.exit(1)
