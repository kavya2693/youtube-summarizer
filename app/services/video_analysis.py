import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from typing import List, Dict, Optional
from collections import Counter

DATA_DIR = Path(__file__).parent.parent.parent / "data"

_model: Optional[YOLO] = None

def get_yolo_model():
    """Load YOLO model (lazy loading)."""
    global _model
    if _model is None:
        _model = YOLO('yolov8n.pt')  # Nano model - fast and lightweight
    return _model

def extract_frames(video_path: str, num_frames: int = 5) -> List[np.ndarray]:
    """Extract evenly spaced frames from video."""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames == 0:
        cap.release()
        return []

    frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames = []

    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
    return frames

def detect_persons(frame: np.ndarray) -> List[Dict]:
    """Detect persons in frame using YOLO."""
    model = get_yolo_model()
    results = model(frame, verbose=False)

    persons = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            if int(box.cls[0]) == 0:  # Class 0 is 'person'
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                persons.append({
                    'bbox': (x1, y1, x2, y2),
                    'confidence': confidence
                })

    return persons

def get_dominant_color(image: np.ndarray, k: int = 3) -> tuple:
    """Get dominant color from image region using k-means."""
    pixels = image.reshape(-1, 3)
    pixels = np.float32(pixels)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

    label_counts = Counter(labels.flatten())
    dominant_label = label_counts.most_common(1)[0][0]
    dominant_color = centers[dominant_label]

    return tuple(map(int, dominant_color))

def bgr_to_color_name(bgr: tuple) -> str:
    """Convert BGR color to human-readable color name."""
    b, g, r = bgr

    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = hsv

    # Check for grayscale colors first
    if s < 30:
        if v < 50:
            return "black"
        elif v < 150:
            return "gray"
        else:
            return "white"

    # Color ranges in HSV
    if h < 10 or h > 170:
        return "red"
    elif h < 25:
        return "orange"
    elif h < 35:
        return "yellow"
    elif h < 85:
        return "green"
    elif h < 130:
        return "blue"
    elif h < 160:
        return "purple"
    else:
        return "pink"

def analyze_shirt_color(frame: np.ndarray, person_bbox: tuple) -> Dict:
    """Analyze shirt color from detected person."""
    x1, y1, x2, y2 = person_bbox
    person_height = y2 - y1
    person_width = x2 - x1

    # Estimate shirt region (upper body, roughly 20-50% from top)
    shirt_y1 = y1 + int(person_height * 0.15)
    shirt_y2 = y1 + int(person_height * 0.45)
    shirt_x1 = x1 + int(person_width * 0.2)
    shirt_x2 = x2 - int(person_width * 0.2)

    # Ensure valid region
    shirt_y1 = max(0, shirt_y1)
    shirt_y2 = min(frame.shape[0], shirt_y2)
    shirt_x1 = max(0, shirt_x1)
    shirt_x2 = min(frame.shape[1], shirt_x2)

    if shirt_y2 <= shirt_y1 or shirt_x2 <= shirt_x1:
        return {'color': 'unknown', 'rgb': (0, 0, 0)}

    shirt_region = frame[shirt_y1:shirt_y2, shirt_x1:shirt_x2]

    if shirt_region.size == 0:
        return {'color': 'unknown', 'rgb': (0, 0, 0)}

    dominant_bgr = get_dominant_color(shirt_region)
    color_name = bgr_to_color_name(dominant_bgr)

    # Convert BGR to RGB for display
    rgb = (dominant_bgr[2], dominant_bgr[1], dominant_bgr[0])

    return {
        'color': color_name,
        'rgb': rgb
    }

def analyze_video_frames(video_id: str) -> Dict:
    """Analyze video frames for visual content."""
    video_path = DATA_DIR / f"{video_id}.mp4"

    # Try different extensions
    if not video_path.exists():
        video_path = DATA_DIR / f"{video_id}.webm"
    if not video_path.exists():
        # Video might have been converted to mp3, need to re-download as video
        return {'error': 'Video file not found. Need to re-download with video.'}

    frames = extract_frames(str(video_path), num_frames=5)

    if not frames:
        return {'error': 'Could not extract frames from video'}

    # Save frames to disk for Vision LLM
    frames_dir = DATA_DIR / video_id / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for i, frame in enumerate(frames):
        frame_path = frames_dir / f"frame_{i+1}.jpg"
        cv2.imwrite(str(frame_path), frame)

    all_detections = []
    shirt_colors = []

    for i, frame in enumerate(frames):
        persons = detect_persons(frame)

        for person in persons:
            shirt_info = analyze_shirt_color(frame, person['bbox'])
            shirt_colors.append(shirt_info['color'])

            all_detections.append({
                'frame': i + 1,
                'person_confidence': person['confidence'],
                'shirt_color': shirt_info['color'],
                'shirt_rgb': shirt_info['rgb']
            })

    # Get most common shirt color
    if shirt_colors:
        color_counts = Counter(shirt_colors)
        most_common_color = color_counts.most_common(1)[0][0]
    else:
        most_common_color = 'unknown'

    return {
        'video_id': video_id,
        'frames_analyzed': len(frames),
        'persons_detected': len(all_detections),
        'dominant_shirt_color': most_common_color,
        'detections': all_detections
    }

def download_video_with_frames(url: str, video_id: str) -> str:
    """Download video (not just audio) for frame analysis."""
    import yt_dlp

    output_path = DATA_DIR / f"{video_id}.mp4"

    ydl_opts = {
        'format': 'best[height<=720]',  # Limit to 720p for faster processing
        'outtmpl': str(DATA_DIR / f"{video_id}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Find the downloaded file
    for ext in ['mp4', 'webm', 'mkv']:
        path = DATA_DIR / f"{video_id}.{ext}"
        if path.exists():
            return str(path)

    return str(output_path)
