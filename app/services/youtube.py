import os
import re
import yt_dlp
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"

def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Could not extract video ID from URL")

def download_audio(url: str) -> dict:
    """Download audio from YouTube video and return metadata."""
    video_id = extract_video_id(url)
    output_path = DATA_DIR / f"{video_id}.mp3"

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(DATA_DIR / f"{video_id}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    return {
        'video_id': video_id,
        'title': info.get('title', 'Unknown'),
        'duration': info.get('duration'),
        'audio_path': str(output_path),
    }

def get_audio_path(video_id: str) -> str:
    """Get the path to a downloaded audio file."""
    return str(DATA_DIR / f"{video_id}.mp3")

def cleanup_audio(video_id: str):
    """Remove downloaded audio file."""
    audio_path = DATA_DIR / f"{video_id}.mp3"
    if audio_path.exists():
        audio_path.unlink()
