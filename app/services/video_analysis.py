import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter

# Lazy imports for heavy CV dependencies (may not be available on all deployments)
cv2 = None
YOLO = None

def _ensure_cv2():
    global cv2
    if cv2 is None:
        import cv2 as _cv2
        cv2 = _cv2
    return cv2

def _ensure_yolo():
    global YOLO
    if YOLO is None:
        from ultralytics import YOLO as _YOLO
        YOLO = _YOLO
    return YOLO

DATA_DIR = Path(__file__).parent.parent.parent / "data"

_model: Optional[YOLO] = None

def get_yolo_model():
    """Load YOLO model (lazy loading)."""
    global _model
    if _model is None:
        YOLOClass = _ensure_yolo()
        _model = YOLOClass('yolov8n.pt')  # Nano model - fast and lightweight
    return _model

# Color palette for different object classes (BGR format)
CLASS_COLORS = {
    'person': (0, 255, 0),      # Green
    'airplane': (255, 100, 0),   # Blue-ish
    'car': (0, 165, 255),        # Orange
    'truck': (0, 100, 255),      # Dark Orange
    'bird': (255, 255, 0),       # Cyan
    'cat': (255, 0, 255),        # Magenta
    'dog': (128, 0, 255),        # Purple
    'boat': (255, 200, 0),       # Light Blue
    'default': (0, 255, 255)     # Yellow
}

def get_color_for_class(class_name: str) -> tuple:
    """Get color for a given class name."""
    return CLASS_COLORS.get(class_name, CLASS_COLORS['default'])

def extract_frames(video_path: str, num_frames: int = 5) -> List[np.ndarray]:
    """Extract evenly spaced frames from video."""
    _ensure_cv2()
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

    _ensure_cv2()
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
    _ensure_cv2()
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

def detect_and_annotate_frames(video_id: str, num_frames: int = 10, confidence_threshold: float = 0.3) -> Dict:
    """Detect objects in frames and save annotated images with bounding boxes."""
    # Find video file
    video_path = None
    for ext in ['mp4', 'webm', 'mkv']:
        path = DATA_DIR / f"{video_id}.{ext}"
        if path.exists():
            video_path = path
            break

    if not video_path:
        return {'error': 'Video not found'}

    # Create output directory for annotated frames
    frames_dir = DATA_DIR / video_id / "annotated_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Extract frames
    frames = extract_frames(str(video_path), num_frames=num_frames)
    if not frames:
        return {'error': 'Could not extract frames'}

    model = get_yolo_model()
    all_detections = {}
    frame_results = []
    total_objects = 0

    for i, frame in enumerate(frames):
        frame_detections = []
        annotated_frame = frame.copy()

        # Run YOLO detection
        results = model(frame, verbose=False)

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])

                if confidence > confidence_threshold:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    # Get color for this class
                    color = get_color_for_class(class_name)

                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

                    # Draw label background
                    label = f"{class_name}: {confidence:.0%}"
                    (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(annotated_frame, (x1, y1 - label_h - 10), (x1 + label_w + 5, y1), color, -1)

                    # Draw label text
                    cv2.putText(annotated_frame, label, (x1 + 2, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    # Track detections
                    if class_name not in all_detections:
                        all_detections[class_name] = 0
                    all_detections[class_name] += 1
                    total_objects += 1

                    frame_detections.append({
                        'class': class_name,
                        'confidence': confidence,
                        'bbox': [x1, y1, x2, y2]
                    })

        # Save annotated frame
        frame_filename = f"frame_{i+1}.jpg"
        frame_path = frames_dir / frame_filename
        cv2.imwrite(str(frame_path), annotated_frame)

        frame_results.append({
            'frame_number': i + 1,
            'image_path': f"/api/frames/{video_id}/{frame_filename}",
            'detections': frame_detections
        })

    return {
        'video_id': video_id,
        'frames_processed': len(frames),
        'total_objects': total_objects,
        'unique_classes': len(all_detections),
        'detection_summary': all_detections,
        'frames': frame_results
    }


def download_video_with_frames(url: str, video_id: str) -> str:
    """Download video (not just audio) for frame analysis."""
    import yt_dlp

    output_path = DATA_DIR / f"{video_id}.mp4"

    # Remove any existing partial downloads
    for ext in ['mp4', 'webm', 'mkv', 'part']:
        path = DATA_DIR / f"{video_id}.{ext}"
        if path.exists():
            path.unlink()

    ydl_opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'outtmpl': str(DATA_DIR / f"{video_id}.%(ext)s"),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': False,
        'retries': 3,
        'fragment_retries': 3,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise Exception(f"Failed to download video: {str(e)}")

    # Find the downloaded file
    for ext in ['mp4', 'webm', 'mkv']:
        path = DATA_DIR / f"{video_id}.{ext}"
        if path.exists() and path.stat().st_size > 0:
            return str(path)

    raise Exception("Video download failed - no valid video file created")
