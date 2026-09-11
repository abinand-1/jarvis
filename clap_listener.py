#!/usr/bin/env python3
"""Listens for a loud clap and triggers an action."""
import sounddevice as sd
import numpy as np
import subprocess
import time

THRESHOLD = 10.0
COOLDOWN = 3
SAMPLE_RATE = 16000
BLOCK_SIZE = 1024

last_trigger = 0.0
clap_flag = False

def callback(indata, frames, time_info, status):
    global last_trigger, clap_flag
    level = float(np.linalg.norm(indata)) * 10
    if level > THRESHOLD and time.time() - last_trigger > COOLDOWN:
        last_trigger = time.time()
        clap_flag = True

def make_stream():
    s = sd.InputStream(callback=callback, channels=1, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE)
    s.start()
    return s

stream = make_stream()

print("Jarvis is listening for claps... Ctrl+C to stop.")
try:
    while True:
        if clap_flag:
            clap_flag = False
            print("Clap detected -> starting command")
            stream.stop()
            stream.close()
            subprocess.run(["/home/abinand/jarvis/venv/bin/python3", "/home/abinand/jarvis/jarvis_command.py"])
            stream = make_stream()   # fresh stream instead of reusing the old one
        time.sleep(0.1)
except KeyboardInterrupt:
    stream.stop()
    stream.close()
