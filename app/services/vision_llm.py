"""Vision LLM service using OpenRouter for detailed image analysis."""
import os
import base64
from pathlib import Path
from openai import OpenAI

DATA_DIR = Path(__file__).parent.parent.parent / "data"

def get_client():
    """Get configured OpenRouter client."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

def encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def analyze_frame_with_vision(video_id: str, question: str) -> dict:
    """
    Use Vision LLM to analyze video frames and answer questions.
    """
    frames_dir = DATA_DIR / video_id / "frames"

    if not frames_dir.exists():
        return {"error": "No frames found. Run visual analysis first."}

    frame_files = sorted(frames_dir.glob("frame_*.jpg"))

    if not frame_files:
        return {"error": "No frame images found."}

    try:
        client = get_client()

        # Build content with images
        content = [
            {
                "type": "text",
                "text": f"""Analyze these video frames and answer the following question:

Question: {question}

Please provide a detailed answer based on what you can see in the frames.
If the question is about clothing, costumes, or appearance, describe what the person(s) are wearing in detail."""
            }
        ]

        # Add images (limit to 3 to stay within limits)
        for frame_file in frame_files[:3]:
            base64_image = encode_image(str(frame_file))
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })

        response = client.chat.completions.create(
            model="allenai/molmo-2-8b:free",
            messages=[
                {"role": "user", "content": content}
            ]
        )

        return {
            "answer": response.choices[0].message.content,
            "frames_analyzed": min(len(frame_files), 3)
        }

    except Exception as e:
        return {"error": str(e)}

def describe_scene(video_id: str) -> dict:
    """Get a general description of what's happening in the video."""
    frames_dir = DATA_DIR / video_id / "frames"

    if not frames_dir.exists():
        return {"error": "No frames found. Run visual analysis first."}

    frame_files = sorted(frames_dir.glob("frame_*.jpg"))

    if not frame_files:
        return {"error": "No frame images found."}

    try:
        client = get_client()

        content = [
            {
                "type": "text",
                "text": """Describe what you see in these video frames:
1. What is the setting/location?
2. Who is visible and what are they wearing?
3. What appears to be happening?

Provide a concise but detailed description."""
            }
        ]

        for frame_file in frame_files[:3]:
            base64_image = encode_image(str(frame_file))
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })

        response = client.chat.completions.create(
            model="allenai/molmo-2-8b:free",
            messages=[
                {"role": "user", "content": content}
            ]
        )

        return {
            "description": response.choices[0].message.content,
            "frames_analyzed": min(len(frame_files), 3)
        }

    except Exception as e:
        return {"error": str(e)}
