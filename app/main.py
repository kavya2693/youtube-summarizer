import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import process, chat, visual, analysis, youtube_explore, transcribe

app = FastAPI(
    title="Video Intelligence",
    description="AI-powered video analysis: Object Detection, Classification, Segmentation & More",
    version="2.0.0"
)

app.include_router(process.router)
app.include_router(chat.router)
app.include_router(visual.router)
app.include_router(analysis.router)
app.include_router(youtube_explore.router)
app.include_router(transcribe.router)

static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse(str(static_dir / "index.html"))

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
