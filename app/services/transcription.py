import os
from pathlib import Path
from typing import Optional
from groq import Groq


def get_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")
    return Groq(api_key=api_key)


def transcribe_audio(audio_path: str) -> dict:
    """Transcribe audio file using Groq's Whisper API."""
    client = get_client()

    with open(audio_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            language="en",
            response_format="verbose_json",
        )

    segments = []
    if hasattr(result, 'segments') and result.segments:
        for seg in result.segments:
            segments.append({
                'start': seg.get('start', 0) if isinstance(seg, dict) else getattr(seg, 'start', 0),
                'end': seg.get('end', 0) if isinstance(seg, dict) else getattr(seg, 'end', 0),
                'text': (seg.get('text', '') if isinstance(seg, dict) else getattr(seg, 'text', '')).strip(),
            })

    return {
        'text': result.text,
        'segments': segments,
        'language': 'en',
    }


def save_transcript(video_id: str, transcript: dict, data_dir: Path):
    """Save transcript to file."""
    data_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = data_dir / f"{video_id}_transcript.txt"
    with open(transcript_path, 'w') as f:
        f.write(transcript['text'])
    return str(transcript_path)


def load_transcript(video_id: str, data_dir: Path) -> Optional[str]:
    """Load transcript from file if exists."""
    transcript_path = data_dir / f"{video_id}_transcript.txt"
    if transcript_path.exists():
        with open(transcript_path, 'r') as f:
            return f.read()
    return None
