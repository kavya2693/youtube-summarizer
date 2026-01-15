#!/bin/bash

# YouTube Summarizer - Startup Script
cd "$(dirname "$0")"

# Load API keys from .env file if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Get local IP for network access
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

echo "============================================"
echo "   YouTube Video Summarizer"
echo "============================================"
echo ""
echo "Starting server..."
echo ""
echo "Access locally:     http://localhost:8000"
echo "Access on network:  http://$LOCAL_IP:8000"
echo "                    (use this URL on your phone)"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================"
echo ""

# Start server accessible on network
uvicorn app.main:app --host 0.0.0.0 --port 8000
