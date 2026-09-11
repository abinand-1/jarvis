#!/usr/bin/env python3
"""Prints live volume levels. Clap a few times and note how high the
number jumps -- you'll use that as THRESHOLD in clap_listener.py.
Ctrl+C to quit."""
import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000
BLOCK_SIZE = 1024

def callback(indata, frames, time_info, status):
    level = float(np.linalg.norm(indata)) * 10
    print(f"{level:7.2f}  {'#' * min(int(level), 60)}")

print("Listening -- make normal room noise, then clap. Ctrl+C to stop.")
with sd.InputStream(callback=callback, channels=1, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE):
    while True:
        sd.sleep(100)

