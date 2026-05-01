"""Analysis router for object detection, classification, segmentation, and change detection."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..services import video_analysis
from ..services.youtube import extract_video_id, download_audio
import yt_dlp
from pathlib import Path

router = APIRouter(prefix="/api", tags=["analysis"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@router.get("/frames/{video_id}/{filename}")
async def get_frame_image(video_id: str, filename: str):
    """Serve annotated frame images."""
    frame_path = DATA_DIR / video_id / "annotated_frames" / filename
    if not frame_path.exists():
        raise HTTPException(status_code=404, detail="Frame not found")
    return FileResponse(str(frame_path), media_type="image/jpeg")

class VideoRequest(BaseModel):
    url: str

class AnalysisRequest(BaseModel):
    video_id: str

@router.post("/video/download")
async def download_video(request: VideoRequest):
    """Download video and prepare for analysis."""
    try:
        video_id = extract_video_id(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get video title
    title = 'Video'
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(request.url, download=False)
            title = info.get('title', 'Video')
    except Exception as e:
        print(f"Could not get video info: {e}")

    # Download video for frame analysis
    try:
        video_path = video_analysis.download_video_with_frames(request.url, video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")

    return {
        'video_id': video_id,
        'title': title,
        'status': 'ready'
    }

@router.post("/analysis/detect")
async def run_object_detection(request: AnalysisRequest):
    """Run YOLO object detection on video frames and return annotated images."""
    video_id = request.video_id

    # Check if video exists
    video_path = None
    for ext in ['mp4', 'webm', 'mkv']:
        path = DATA_DIR / f"{video_id}.{ext}"
        if path.exists():
            video_path = path
            break

    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found. Please download first.")

    # Run detection and get annotated frames
    result = video_analysis.detect_and_annotate_frames(video_id, num_frames=10)

    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])

    return result

@router.post("/analysis/classify")
async def run_classification(request: AnalysisRequest):
    """Classify detected objects into categories."""
    video_id = request.video_id

    # Check if video exists
    video_path = None
    for ext in ['mp4', 'webm', 'mkv']:
        path = DATA_DIR / f"{video_id}.{ext}"
        if path.exists():
            video_path = path
            break

    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")

    frames = video_analysis.extract_frames(str(video_path), num_frames=10)
    model = video_analysis.get_yolo_model()

    # Group detections by category
    categories = {
        'Vehicles': [],
        'People': [],
        'Aircraft': [],
        'Animals': [],
        'Objects': []
    }

    vehicle_classes = ['car', 'truck', 'bus', 'motorcycle', 'bicycle', 'train', 'boat']
    people_classes = ['person']
    aircraft_classes = ['airplane', 'aeroplane']
    animal_classes = ['bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe']

    detection_counts = {}

    for frame in frames:
        results = model(frame, verbose=False)
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])

                if confidence > 0.3:
                    if class_name not in detection_counts:
                        detection_counts[class_name] = {'count': 0, 'total_conf': 0}
                    detection_counts[class_name]['count'] += 1
                    detection_counts[class_name]['total_conf'] += confidence

    # Categorize
    for class_name, data in detection_counts.items():
        avg_conf = data['total_conf'] / data['count']
        item = {'name': class_name, 'confidence': avg_conf, 'count': data['count']}

        if class_name in vehicle_classes:
            categories['Vehicles'].append(item)
        elif class_name in people_classes:
            categories['People'].append(item)
        elif class_name in aircraft_classes:
            categories['Aircraft'].append(item)
        elif class_name in animal_classes:
            categories['Animals'].append(item)
        else:
            categories['Objects'].append(item)

    # Format response
    result_categories = []
    for cat_name, items in categories.items():
        if items:
            result_categories.append({
                'name': cat_name,
                'items': sorted(items, key=lambda x: x['count'], reverse=True)
            })

    return {
        'video_id': video_id,
        'categories': result_categories
    }

@router.post("/analysis/segment")
async def run_segmentation(request: AnalysisRequest):
    """Run basic segmentation analysis on video frames."""
    video_id = request.video_id

    video_path = None
    for ext in ['mp4', 'webm', 'mkv']:
        path = DATA_DIR / f"{video_id}.{ext}"
        if path.exists():
            video_path = path
            break

    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")

    frames = video_analysis.extract_frames(str(video_path), num_frames=5)

    import cv2
    import numpy as np

    # Simple color-based segmentation
    region_counts = {
        'Sky/Blue regions': 0,
        'Ground/Brown regions': 0,
        'Green/Vegetation': 0,
        'Dark/Shadow regions': 0,
        'Bright/Highlight regions': 0
    }

    total_pixels = 0

    for frame in frames:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        height, width = frame.shape[:2]
        pixels = height * width
        total_pixels += pixels

        # Sky (blue hue, high brightness)
        sky_mask = (h > 90) & (h < 130) & (s > 30) & (v > 100)
        region_counts['Sky/Blue regions'] += np.sum(sky_mask)

        # Green/Vegetation
        green_mask = (h > 35) & (h < 85) & (s > 40)
        region_counts['Green/Vegetation'] += np.sum(green_mask)

        # Ground/Brown
        brown_mask = (h > 10) & (h < 30) & (s > 30) & (s < 200)
        region_counts['Ground/Brown regions'] += np.sum(brown_mask)

        # Dark regions
        dark_mask = v < 50
        region_counts['Dark/Shadow regions'] += np.sum(dark_mask)

        # Bright regions
        bright_mask = v > 200
        region_counts['Bright/Highlight regions'] += np.sum(bright_mask)

    # Calculate percentages
    regions = []
    for name, count in region_counts.items():
        percentage = round((count / total_pixels) * 100, 1) if total_pixels > 0 else 0
        if percentage > 1:  # Only show significant regions
            regions.append({'name': name, 'percentage': percentage})

    regions.sort(key=lambda x: x['percentage'], reverse=True)

    return {
        'video_id': video_id,
        'frames_processed': len(frames),
        'regions': regions
    }

@router.post("/analysis/change")
async def run_change_detection(request: AnalysisRequest):
    """Detect changes between consecutive frames."""
    video_id = request.video_id

    video_path = None
    for ext in ['mp4', 'webm', 'mkv']:
        path = DATA_DIR / f"{video_id}.{ext}"
        if path.exists():
            video_path = path
            break

    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")

    frames = video_analysis.extract_frames(str(video_path), num_frames=10)

    if len(frames) < 2:
        raise HTTPException(status_code=400, detail="Not enough frames for change detection")

    import cv2
    import numpy as np

    changes = []
    total_motion = 0

    for i in range(1, len(frames)):
        prev_gray = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)

        # Calculate frame difference
        diff = cv2.absdiff(prev_gray, curr_gray)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

        # Calculate motion score
        motion = np.sum(thresh > 0) / thresh.size * 100
        total_motion += motion

        if motion > 5:  # Significant change
            if motion > 30:
                description = "Major scene change or fast motion"
            elif motion > 15:
                description = "Moderate movement detected"
            else:
                description = "Minor movement detected"

            changes.append({
                'frame': i + 1,
                'description': description,
                'motion_percent': round(motion, 1)
            })

    avg_motion = round(total_motion / (len(frames) - 1), 1) if len(frames) > 1 else 0

    return {
        'video_id': video_id,
        'total_changes': len(changes),
        'motion_score': avg_motion,
        'changes': changes[:10]  # Limit to 10 most significant
    }
