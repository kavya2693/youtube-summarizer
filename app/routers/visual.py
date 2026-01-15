from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from ..services import video_analysis, vision_llm
from ..services.youtube import extract_video_id

router = APIRouter(prefix="/api", tags=["visual"])

# Store for visual analysis results
visual_store = {}

class VisualAnalysisRequest(BaseModel):
    url: str

class VisualQuestionRequest(BaseModel):
    video_id: str
    question: str

def analyze_video_task(url: str, video_id: str):
    """Background task to download and analyze video frames."""
    try:
        visual_store[video_id]['status'] = 'downloading_video'

        # Download video with frames (not just audio)
        video_path = video_analysis.download_video_with_frames(url, video_id)

        visual_store[video_id]['status'] = 'analyzing'

        # Analyze frames
        result = video_analysis.analyze_video_frames(video_id)

        if 'error' in result:
            visual_store[video_id]['status'] = 'error'
            visual_store[video_id]['error'] = result['error']
        else:
            visual_store[video_id]['status'] = 'completed'
            visual_store[video_id]['result'] = result

    except Exception as e:
        visual_store[video_id]['status'] = 'error'
        visual_store[video_id]['error'] = str(e)

@router.post("/visual/analyze")
async def analyze_visual(request: VisualAnalysisRequest, background_tasks: BackgroundTasks):
    """Start visual analysis of a YouTube video."""
    try:
        video_id = extract_video_id(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    visual_store[video_id] = {
        'status': 'queued',
        'result': None,
        'error': None,
    }

    background_tasks.add_task(analyze_video_task, request.url, video_id)

    return {
        'video_id': video_id,
        'status': 'processing',
        'message': 'Visual analysis started'
    }

@router.get("/visual/status/{video_id}")
async def get_visual_status(video_id: str):
    """Get visual analysis status."""
    if video_id not in visual_store:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        'video_id': video_id,
        'status': visual_store[video_id]['status'],
        'error': visual_store[video_id].get('error'),
    }

@router.get("/visual/result/{video_id}")
async def get_visual_result(video_id: str):
    """Get visual analysis result."""
    if video_id not in visual_store:
        raise HTTPException(status_code=404, detail="Video not found")

    data = visual_store[video_id]

    if data['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not complete. Status: {data['status']}"
        )

    return data['result']

@router.post("/visual/ask")
async def ask_visual_question(request: VisualQuestionRequest):
    """Answer a visual question about the video using Vision LLM."""
    video_id = request.video_id
    question = request.question

    if video_id not in visual_store:
        raise HTTPException(status_code=404, detail="Video not analyzed. Run /visual/analyze first.")

    data = visual_store[video_id]

    if data['status'] != 'completed':
        raise HTTPException(status_code=400, detail=f"Analysis not complete. Status: {data['status']}")

    # Use Vision LLM for detailed analysis
    try:
        result = vision_llm.analyze_frame_with_vision(video_id, question)

        if 'error' in result:
            # Fall back to basic analysis if Vision LLM fails
            return await basic_visual_answer(video_id, question, data['result'])

        return {
            'video_id': video_id,
            'question': request.question,
            'answer': result['answer'],
            'frames_analyzed': result.get('frames_analyzed', 0),
            'method': 'vision_llm'
        }
    except Exception as e:
        # Fall back to basic analysis
        return await basic_visual_answer(video_id, question, data['result'])

async def basic_visual_answer(video_id: str, question: str, result: dict):
    """Fallback to basic YOLO-based analysis."""
    question_lower = question.lower()
    answer = ""

    if 'shirt' in question_lower and 'color' in question_lower:
        color = result.get('dominant_shirt_color', 'unknown')
        answer = f"The person is wearing a {color} shirt."

    elif 'color' in question_lower and ('wearing' in question_lower or 'clothes' in question_lower):
        color = result.get('dominant_shirt_color', 'unknown')
        answer = f"The dominant clothing color detected is {color}."

    elif 'person' in question_lower or 'people' in question_lower or 'someone' in question_lower:
        count = result.get('persons_detected', 0)
        if count > 0:
            answer = f"Yes, {count} person detection(s) were made across {result.get('frames_analyzed', 0)} frames."
        else:
            answer = "No persons were detected in the analyzed frames."

    elif 'frame' in question_lower:
        answer = f"{result.get('frames_analyzed', 0)} frames were analyzed from the video."

    else:
        color = result.get('dominant_shirt_color', 'unknown')
        persons = result.get('persons_detected', 0)
        answer = f"Visual analysis found {persons} person detection(s). Dominant shirt color: {color}. For detailed answers, set up GEMINI_API_KEY."

    return {
        'video_id': video_id,
        'question': question,
        'answer': answer,
        'analysis_data': result,
        'method': 'basic'
    }

@router.post("/visual/describe")
async def describe_video_scene(request: VisualQuestionRequest):
    """Get a detailed description of the video scene using Vision LLM."""
    video_id = request.video_id

    if video_id not in visual_store:
        raise HTTPException(status_code=404, detail="Video not analyzed. Run /visual/analyze first.")

    data = visual_store[video_id]

    if data['status'] != 'completed':
        raise HTTPException(status_code=400, detail=f"Analysis not complete. Status: {data['status']}")

    try:
        result = vision_llm.describe_scene(video_id)

        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])

        return {
            'video_id': video_id,
            'description': result['description'],
            'frames_analyzed': result.get('frames_analyzed', 0)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
