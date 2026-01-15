from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .routers import process, chat, visual

app = FastAPI(
    title="YouTube Video Summarizer",
    description="Summarize YouTube videos and ask questions about them",
    version="1.0.0"
)

app.include_router(process.router)
app.include_router(chat.router)
app.include_router(visual.router)

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
