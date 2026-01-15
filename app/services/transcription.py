import whisper
from pathlib import Path
from typing import Optional

_model: Optional[whisper.Whisper] = None

def get_model():
    """Load Whisper model (lazy loading)."""
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model

def transcribe_audio(audio_path: str) -> dict:
    """Transcribe audio file using Whisper."""
    model = get_model()

    result = model.transcribe(
        audio_path,
        fp16=False,
        language='en',
    )

    segments = []
    for segment in result.get('segments', []):
        segments.append({
            'start': segment['start'],
            'end': segment['end'],
            'text': segment['text'].strip(),
        })

    return {
        'text': result['text'],
        'segments': segments,
        'language': result.get('language', 'en'),
    }

def save_transcript(video_id: str, transcript: dict, data_dir: Path):
    """Save transcript to file."""
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
