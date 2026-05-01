from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from ..models.schemas import (
    VideoProcessRequest,
    ProcessResponse,
    SummaryResponse
)
from ..services import youtube, transcription, summarizer, qa

router = APIRouter(prefix="/api", tags=["process"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"

video_store = {}

def process_video_task(url: str, video_id: str):
    """Background task to process video."""
    try:
        video_store[video_id]['status'] = 'downloading'
        info = youtube.download_audio(url)

        video_store[video_id]['status'] = 'transcribing'
        video_store[video_id]['title'] = info['title']

        # Transcribe via Groq Whisper API (cloud-based)
        transcript_result = transcription.transcribe_audio(info['audio_path'])

        transcription.save_transcript(video_id, transcript_result, DATA_DIR)
        video_store[video_id]['transcript'] = transcript_result['text']

        video_store[video_id]['status'] = 'summarizing'
        summary_result = summarizer.generate_summary(
            transcript_result['text'],
            info['title']
        )
        video_store[video_id]['summary'] = summary_result['summary']
        video_store[video_id]['key_takeaways'] = summary_result['key_takeaways']

        video_store[video_id]['status'] = 'indexing'
        qa.index_transcript(video_id, transcript_result['text'])

        video_store[video_id]['status'] = 'completed'

        youtube.cleanup_audio(video_id)

    except Exception as e:
        video_store[video_id]['status'] = 'error'
        video_store[video_id]['error'] = str(e)

@router.post("/process", response_model=ProcessResponse)
async def process_video(request: VideoProcessRequest, background_tasks: BackgroundTasks):
    """Start processing a YouTube video."""
    try:
        video_id = youtube.extract_video_id(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    video_store[video_id] = {
        'status': 'queued',
        'title': '',
        'transcript': '',
        'summary': '',
        'key_takeaways': [],
        'error': None,
    }

    background_tasks.add_task(process_video_task, request.url, video_id)

    return ProcessResponse(
        video_id=video_id,
        status='processing',
        message='Video processing started'
    )

@router.get("/status/{video_id}")
async def get_status(video_id: str):
    """Get processing status for a video."""
    if video_id not in video_store:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        'video_id': video_id,
        'status': video_store[video_id]['status'],
        'error': video_store[video_id].get('error'),
    }

@router.get("/summary/{video_id}", response_model=SummaryResponse)
async def get_summary(video_id: str):
    """Get summary and key takeaways for a processed video."""
    if video_id not in video_store:
        raise HTTPException(status_code=404, detail="Video not found")

    data = video_store[video_id]

    if data['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Video processing not complete. Current status: {data['status']}"
        )

    return SummaryResponse(
        video_id=video_id,
        title=data['title'],
        summary=data['summary'],
        key_takeaways=data['key_takeaways'],
        transcript=data['transcript']
    )
