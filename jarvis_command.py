#!/usr/bin/env python3
"""Records after a clap, holds a multi-turn conversation with memory,
self-awareness, and stricter routing, until the user ends it or goes silent."""
import subprocess
import time
import json
import os
from datetime import datetime
from faster_whisper import WhisperModel
import ollama

HOME = "/home/abinand/jarvis"
RECORD_SECONDS = 6
MODEL_NAME = "llama3.1:8b"
MAX_SILENT_TURNS = 2
MAX_HISTORY = 6
MAX_MEMORIES = 20
MEMORY_FILE = f"{HOME}/memory.json"

whisper_model = WhisperModel("small.en", device="cpu", compute_type="int8")

SELF_INFO = """You are Jarvis, a home assistant running locally on the user's WSL Ubuntu PC.
Your real current abilities: waking on a clap, holding a spoken multi-turn conversation,
scanning the home WiFi network for connected devices, telling the real time, remembering
things the user explicitly asks you to remember across sessions, and shutting yourself
down on voice command. You do NOT have weather, email, calendar, or smart home device
control yet. Be honest about what you can and can't do."""

def speak(text):
    subprocess.run([f"{HOME}/speak.sh", text])

def record():
    wav_path = "/tmp/jarvis_command.wav"
    proc = subprocess.Popen([
        "parecord", "--channels=1", "--rate=16000", "-d", "RDPSource", wav_path
    ])
    time.sleep(RECORD_SECONDS)
    proc.terminate()
    proc.wait()
    return wav_path

def transcribe(wav_path):
    segments, _ = whisper_model.transcribe(wav_path, vad_filter=True)
    return " ".join(seg.text for seg in segments).strip()

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_memory_item(text):
    memories = load_memory()
    memories.append(text)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memories, f, indent=2)

def format_memories(memories):
    if not memories:
        return ""
    recent = memories[-MAX_MEMORIES:]
    lines = "\n".join(f"- {m}" for m in recent)
    return f"\nThings you remember from past conversations:\n{lines}\n"

def scan_network_text():
    result = subprocess.run(
        ["arp-scan", "--interface=eth6", "--localnet"],
        capture_output=True, text=True
    )
    import re
    devices = []
    for line in result.stdout.splitlines():
        m = re.match(r"^(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]{17})\s+(.*)$", line)
        if m:
            devices.append(m.group(3).strip() or m.group(1))
    if not devices:
        return "I found no devices on the network."
    return f"I found {len(devices)} devices: " + ", ".join(devices)

def get_time_text():
    now = datetime.now()
    return f"It's {now.strftime('%I:%M %p')} right now."

def ask_llm_route(user_text):
    prompt = f"""You are Jarvis, a home assistant. The user said: "{user_text}"

Decide ONE action from this list and reply with ONLY that word, nothing else:
- SCAN (ONLY if they explicitly and clearly ask to scan the network, check wifi, or list connected devices - if in doubt, do NOT pick SCAN)
- TIME (ONLY if they explicitly ask what time it is)
- REMEMBER (the user says the word "remember" or "don't forget" anywhere in their sentence - this catches ANY sentence containing "remember", even "remember that my favorite color is blue" or "can you remember I like pizza")
- STOP (asking you to shut down completely / go to sleep / stop the service)
- DONE (asking to end this conversation, e.g. "that's all", "thanks that's it", "nothing else")
- CHAT (anything else - including vague, unclear, or general conversation - default to this if unsure)

Reply with exactly one word: SCAN, TIME, REMEMBER, STOP, DONE, or CHAT"""
    response = ollama.generate(model=MODEL_NAME, prompt=prompt)
    return response["response"].strip().upper()

def chat_reply(user_text, history, memories):
    history_text = ""
    for turn in history[-MAX_HISTORY:]:
        history_text += f"User: {turn['user']}\nJarvis: {turn['jarvis']}\n"

    memory_block = format_memories(memories)

    prompt = f"""{SELF_INFO}
{memory_block}
Recent conversation so far:
{history_text}
User: {user_text}

Reply in one or two short spoken sentences. Do not use lists, bullet points, or markdown -
this will be spoken aloud. You do NOT have access to real-time data like weather, emails,
or calendar - if asked, say so honestly rather than making something up."""
    response = ollama.generate(model=MODEL_NAME, prompt=prompt)
    return response["response"].strip()

def handle_command():
    speak("Yes sir")
    time.sleep(1.5)
    silent_turns = 0
    history = []
    memories = load_memory()

    while True:
        wav_path = record()
        text = transcribe(wav_path)
        print(f"Heard: {text}")

        if not text or len(text.split()) < 2:
            silent_turns += 1
            if silent_turns >= MAX_SILENT_TURNS:
                speak("Going back to standby.")
                return
            continue
        silent_turns = 0

        action = ask_llm_route(text)
        print(f"Routed to: {action}")

        if "STOP" in action:
            speak("Okay, going to sleep now.")
            subprocess.Popen(["sudo", "systemctl", "stop", "jarvis.service"])
            return

        if "DONE" in action:
            speak("Alright, standing by.")
            return

        if "SCAN" in action:
            reply = scan_network_text()
        elif "TIME" in action:
            reply = get_time_text()
        elif "REMEMBER" in action:
            save_memory_item(text)
            memories.append(text)
            reply = "Got it, I'll remember that."
        else:
            reply = chat_reply(text, history, memories)
            history.append({"user": text, "jarvis": reply})

        print(f"Jarvis: {reply}")
        speak(reply)
        time.sleep(1.5)

if __name__ == "__main__":
    handle_command()
