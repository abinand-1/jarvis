#!/bin/bash
VENV_PY="$HOME/jarvis/venv/bin/python3"
VOICE_DIR="$HOME/jarvis/voices"
VOICE="en_US-lessac-medium"
TEXT="$1"

"$VENV_PY" -m piper -m "$VOICE" --data-dir "$VOICE_DIR" -f /tmp/jarvis_speech.wav -- "$TEXT"
paplay /tmp/jarvis_speech.wav

