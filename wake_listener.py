#!/usr/bin/env python3
"""Listens continuously for 'Hey Jarvis' and triggers a command."""
import sounddevice as sd
import numpy as np
import subprocess
import time
from openwakeword.model import Model

SAMPLE_RATE = 16000
FRAME_SIZE = 1280   # 80ms chunks, openWakeWord's expected frame size
THRESHOLD = 0.5
COOLDOWN = 3

oww_model = Model(wakeword_models=["hey_jarvis_v0.1.tflite"])

last_trigger = 0.0

def run_command():
    global last_trigger
    print("Wake word detected -> starting command")
    subprocess.run(["/home/abinand/jarvis/venv/bin/python3", "/home/abinand/jarvis/jarvis_command.py"])
    last_trigger = time.time()
    oww_model.reset()   # clear internal state so old audio doesn't linger

def make_stream():
    return sd.InputStream(channels=1, samplerate=SAMPLE_RATE, blocksize=FRAME_SIZE, dtype="int16")

print("Jarvis is listening for 'Hey Jarvis'... Ctrl+C to stop.")
stream = make_stream()
stream.start()

try:
    while True:
        audio_chunk, _ = stream.read(FRAME_SIZE)
        audio_chunk = audio_chunk.flatten()

        prediction = oww_model.predict(audio_chunk)
        score = max(prediction.values())

        if score > THRESHOLD and time.time() - last_trigger > COOLDOWN:
            stream.stop()
            stream.close()
            run_command()
            stream = make_stream()
            stream.start()
except KeyboardInterrupt:
    stream.stop()
    stream.close()
