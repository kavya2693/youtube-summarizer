from pydantic import BaseModel
from typing import Optional, List

class VideoProcessRequest(BaseModel):
    url: str

class VideoInfo(BaseModel):
    video_id: str
    title: str
    duration: Optional[int] = None

class ProcessResponse(BaseModel):
    video_id: str
    status: str
    message: str

class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str

class SummaryResponse(BaseModel):
    video_id: str
    title: str
    summary: str
    key_takeaways: List[str]
    transcript: Optional[str] = None

class QuestionRequest(BaseModel):
    video_id: str
    question: str

class AnswerResponse(BaseModel):
    video_id: str
    question: str
    answer: str
    relevant_context: Optional[List[str]] = None
