from fastapi import APIRouter, HTTPException
from ..models.schemas import QuestionRequest, AnswerResponse
from ..services import qa
from .process import video_store

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question about a processed video."""
    video_id = request.video_id

    if video_id not in video_store:
        raise HTTPException(status_code=404, detail="Video not found. Please process the video first.")

    data = video_store[video_id]

    if data['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Video processing not complete. Current status: {data['status']}"
        )

    result = qa.answer_question(
        video_id=video_id,
        question=request.question,
        title=data.get('title', '')
    )

    return AnswerResponse(
        video_id=video_id,
        question=request.question,
        answer=result['answer'],
        relevant_context=result['relevant_context']
    )
