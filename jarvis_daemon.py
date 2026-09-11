#!/usr/bin/env python3
"""Persistent daemon for Jarvis with Routing, Fast-Path, Universal App Launching, Web Search, and Streaming TTS."""

import os
import re
import json
import time
import queue
import threading
import subprocess
from datetime import datetime

import numpy as np
import sounddevice as sd
import webrtcvad
import ollama
from faster_whisper import WhisperModel
from openwakeword.model import Model

# Web search module
try:
    from web_search import search_web
except ImportError:
    def search_web(q):
        return "Web search module is not available."

# --- Configuration & Constants ---
HOME = os.path.expanduser("~/jarvis")
MEMORY_FILE = os.path.join(HOME, "memory.json")
MODEL_NAME = "llama3.1:8b"
PIPER_MODEL = os.path.join(HOME, "voices/en_US-lessac-medium.onnx")

SAMPLE_RATE = 16000
VAD_FRAME_MS = 30
VAD_CHUNK_SAMPLES = int(SAMPLE_RATE * (VAD_FRAME_MS / 1000.0))
OWW_CHUNK_SAMPLES = 1280

WHISPER_PROMPT = "Open Spotify, WhatsApp, Netflix, YouTube, Chrome, Settings, Calculator, Terminal, Camera, After Effects."

# --- Precompiled Regex Patterns for Performance ---
WAKE_WORD_CLEANUP = re.compile(r'^(hey\s+jarvis|jarvis)[\s,]*', re.IGNORECASE)
ACTION_OPEN = re.compile(r'^(open|launch|start|run)\s+', re.IGNORECASE)
ACTION_SEARCH = re.compile(r'^(search for|search the web for|look up|who is|what is|when did|how many|what are)\s+', re.IGNORECASE)
SEARCH_PREFIX_CLEANUP = re.compile(r'^(search for|search the web for|look up)\s+', re.IGNORECASE)
PUNCTUATION_STRIP = re.compile(r'[^\w\s]')

# --- Model Initialization ---
print("Loading OpenWakeWord...")
oww_model = Model(wakeword_models=["hey_jarvis_v0.1.tflite"])

print("Loading Faster-Whisper (small, int8)...")
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")

vad = webrtcvad.Vad(2)


# --- Helper Functions ---
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory_item(text):
    memories = load_memory()
    memories.append(text)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memories, f, indent=2)

def scan_network_text():
    try:
        result = subprocess.run(
            ["sudo", "arp-scan", "--interface=eth6", "--localnet"],
            capture_output=True, text=True, check=True
        )
        devices = [
            m.group(3).strip() or m.group(1) 
            for line in result.stdout.splitlines() 
            if (m := re.match(r"^(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]{17})\s+(.*)$", line))
        ]
        if not devices:
            return "I found no devices on the network."
        return f"I found {len(devices)} devices: " + ", ".join(devices)
    except subprocess.CalledProcessError:
        return "I don't have permission to scan the network, or the interface is down."

def get_time_text():
    return f"It's {datetime.now().strftime('%I:%M %p')} right now."

def open_any_app(user_text):
    # Strip trigger verbs and Whisper punctuation natively via precompiled regex
    app_name = ACTION_OPEN.sub('', user_text).strip()
    app_name = PUNCTUATION_STRIP.sub('', app_name).strip()

    if not app_name:
        return "Which application would you like me to open?"

    # Query Windows Start Menu via PowerShell
    ps_script = f"""
    $app = Get-StartApps | Where-Object {{ $_.Name -match '{app_name}' }} | Select-Object -First 1
    if ($app) {{
        Start-Process explorer.exe -ArgumentList "shell:AppsFolder\\$($app.AppID)"
        exit 0
    }} else {{
        exit 1
    }}
    """
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if res.returncode == 0:
            return f"Opening {app_name}."
    except Exception:
        pass

    # Fallback to native Linux binary inside WSL
    try:
        subprocess.Popen([app_name.lower()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Opening {app_name} on Linux."
    except FileNotFoundError:
        return f"Could not find an application named {app_name}."

def speak_streaming(llm_stream):
    piper_cmd = [os.path.join(HOME, "venv/bin/python3"), "-m", "piper", "-m", PIPER_MODEL, "--output-raw"]
    pacat_cmd = ["pacat", "--rate=22050", "--channels=1", "--format=s16le"]
    
    piper_proc = subprocess.Popen(piper_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    pacat_proc = subprocess.Popen(pacat_cmd, stdin=piper_proc.stdout)

    buffer = ""
    for chunk in llm_stream:
        text = chunk['message']['content']
        buffer += text
        print(text, end="", flush=True)
        
        # Flush on sentence boundaries to minimize TTS latency
        if any(punct in buffer for punct in ['.', '?', '!']):
            piper_proc.stdin.write(buffer.encode('utf-8'))
            piper_proc.stdin.flush()
            buffer = ""
            
    if buffer.strip():
        piper_proc.stdin.write(buffer.encode('utf-8'))
        
    piper_proc.stdin.close()
    piper_proc.wait()
    pacat_proc.wait()
    print()


# --- Core Routing & Processing ---
def ask_llm_route(user_text):
    prompt = f"""You are Jarvis, a home assistant. The user said: "{user_text}"

Decide ONE action from this list and reply with ONLY that word:
- SCAN (network scan)
- TIME (check current time)
- REMEMBER (save a memory)
- STOP (shut down service)
- DONE (end conversation)
- OPEN (explicitly ask to open/launch an app)
- SEARCH (look up info, search web, factual questions)
- CHAT (default)

Reply with exactly one word: SCAN, TIME, REMEMBER, STOP, DONE, OPEN, SEARCH, or CHAT"""
    response = ollama.generate(model=MODEL_NAME, prompt=prompt)
    return response["response"].strip().upper()

def process_interaction(user_text):
    if not user_text.strip():
        return
        
    # Clean up wake word bleed automatically
    cleaned_text = WAKE_WORD_CLEANUP.sub('', user_text).strip()
    print(f"\nUser: {cleaned_text}")

    # Fast-Path deterministic commands
    if ACTION_OPEN.match(cleaned_text):
        action = "OPEN"
    elif ACTION_SEARCH.match(cleaned_text):
        action = "SEARCH"
    else:
        action = ask_llm_route(cleaned_text)

    print(f"[Routed to: {action}]")

    if "STOP" in action:
        speak_streaming([{'message': {'content': "Going to sleep now. Goodbye."}}])
        subprocess.Popen(["sudo", "systemctl", "stop", "jarvis.service"])
        os._exit(0)
        
    elif "DONE" in action:
        speak_streaming([{'message': {'content': "Standing by."}}])
        return
        
    elif "OPEN" in action:
        reply = open_any_app(cleaned_text)
        print(f"Jarvis: {reply}")
        speak_streaming([{'message': {'content': reply}}])
        return
        
    elif "SEARCH" in action:
        query = SEARCH_PREFIX_CLEANUP.sub('', cleaned_text).strip()
        print(f"[Scraping Web for: {query}...]")
        scraped_data = search_web(query)
        
        prompt = f"You are Jarvis. User asked: '{cleaned_text}'. Using this web data: '{scraped_data}', reply in one or two concise, natural spoken sentences."
        llm_stream = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}], stream=True)
        print("Jarvis: ", end="")
        speak_streaming(llm_stream)
        return
        
    elif "SCAN" in action:
        reply = scan_network_text()
        print(f"Jarvis: {reply}")
        speak_streaming([{'message': {'content': reply}}])
        return
        
    elif "TIME" in action:
        reply = get_time_text()
        print(f"Jarvis: {reply}")
        speak_streaming([{'message': {'content': reply}}])
        return
        
    elif "REMEMBER" in action:
        save_memory_item(cleaned_text)
        reply = "Got it, I'll remember that."
        print(f"Jarvis: {reply}")
        speak_streaming([{'message': {'content': reply}}])
        return

    # Fallback to general chat
    memories = load_memory()
    prompt = f"You are Jarvis. Be concise. Past context: {memories}. User: {cleaned_text}"
    llm_stream = ollama.chat(
        model=MODEL_NAME,
        messages=[{'role': 'user', 'content': prompt}],
        stream=True
    )
    print("Jarvis: ", end="")
    speak_streaming(llm_stream)


# --- Voice Processing Loop ---
def record_until_silence():
    print("\n[Listening...]")
    q = queue.Queue()
    def vad_callback(indata, frames, time_info, status):
        q.put(bytes(indata))
        
    stream = sd.RawInputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype='int16',
        blocksize=VAD_CHUNK_SAMPLES, callback=vad_callback
    )
    
    frames = []
    silent_chunks = 0
    max_silent_chunks = int(1500 / VAD_FRAME_MS)
    has_spoken = False
    
    with stream:
        while True:
            frame = q.get()
            if vad.is_speech(frame, SAMPLE_RATE):
                has_spoken = True
                silent_chunks = 0
                frames.append(frame)
            elif has_spoken:
                silent_chunks += 1
                frames.append(frame)
                if silent_chunks > max_silent_chunks:
                    break
                    
    audio_data = b"".join(frames)
    return np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

def voice_listener_loop():
    q = queue.Queue()
    def oww_callback(indata, frames, time_info, status):
        q.put(bytes(indata))
        
    while True:
        try:
            stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype='int16',
                blocksize=OWW_CHUNK_SAMPLES, callback=oww_callback
            )
            with stream:
                triggered = False
                while not triggered:
                    frame = q.get()
                    prediction = oww_model.predict(np.frombuffer(frame, dtype=np.int16))
                    if max(prediction.values()) > 0.5:
                        oww_model.reset()
                        triggered = True

            print("\n[Wake Word Detected]")
            user_audio = record_until_silence()

            segments, _ = whisper_model.transcribe(
                user_audio,
                vad_filter=True,
                initial_prompt=WHISPER_PROMPT
            )
            user_text = " ".join(seg.text for seg in segments).strip()
            process_interaction(user_text)
            print("\nJarvis is online. Waiting for wake word or type below...")
            
        except Exception as e:
            print(f"Voice loop error: {e}")
            time.sleep(1)


# --- Entry Point ---
if __name__ == "__main__":
    print("Starting Jarvis Daemon (Voice, Text, Fast-Path, Tools, App Launching, Web Search)...")
    voice_thread = threading.Thread(target=voice_listener_loop, daemon=True)
    voice_thread.start()
    print("Jarvis is online. Say 'Hey Jarvis' or type a message below and press Enter.")
    
    try:
        while True:
            text_input = input("\nYou (text): ")
            if text_input.strip():
                process_interaction(text_input)
    except KeyboardInterrupt:
        print("\nShutting down.")
