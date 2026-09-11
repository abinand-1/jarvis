from faster_whisper import WhisperModel
import sys

model = WhisperModel("base.en", device="cpu", compute_type="int8")
segments, _ = model.transcribe(sys.argv[1])
for seg in segments:
    print(seg.text)
