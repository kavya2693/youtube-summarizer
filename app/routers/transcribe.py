from fastapi import APIRouter, UploadFile, File, HTTPException
from ..services.transcription import transcribe_audio
from pathlib import Path
import tempfile
import os

router = APIRouter(prefix="/api", tags=["transcribe"])


@router.post("/transcribe")
async def transcribe_upload(file: UploadFile = File(...)):
    """Transcribe an uploaded audio file using Groq Whisper API."""
    allowed = {".mp3", ".mp4", ".m4a", ".wav", ".webm", ".ogg", ".flac", ".opus"}
    ext = Path(file.filename).suffix.lower()

    if ext not in allowed:
        raise HTTPException(400, f"Unsupported format: {ext}. Use: {', '.join(allowed)}")

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = transcribe_audio(tmp_path)
        return {
            "filename": file.filename,
            "text": result["text"],
            "segments": result["segments"],
            "language": result["language"],
        }
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {str(e)}")
    finally:
        os.unlink(tmp_path)
