import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from app.services.transcription import transcribe_audio, save_transcript

video_id = sys.argv[1]
data_dir = Path("data") / video_id
audio_path = data_dir / "audio.mp3"

print(f"Transcribing {audio_path} ...")
result = transcribe_audio(str(audio_path))

save_transcript(video_id, result, data_dir)
text_path = data_dir / f"{video_id}_transcript.txt"

segments_path = data_dir / f"{video_id}_segments.json"
with open(segments_path, "w") as f:
    json.dump(result["segments"], f, indent=2)

print(f"Saved: {text_path}")
print(f"Saved: {segments_path}")
print(f"Words: {len(result['text'].split())}")
