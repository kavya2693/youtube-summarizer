"""
YouTube Explorer Router - Handle YouTube search and discovery queries
"""
import os
import json
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from ..services.youtube_search import (
    search_youtube,
    get_video_details,
    get_trending_videos,
    search_channel_videos,
)

router = APIRouter(prefix="/api/youtube", tags=["youtube-explore"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []


@router.post("/search")
async def youtube_search(request: SearchRequest):
    """Direct YouTube search."""
    videos = await search_youtube(request.query, request.max_results)
    return {"videos": videos, "query": request.query}


@router.post("/trending")
async def youtube_trending(category: str = "all"):
    """Get trending videos."""
    videos = await get_trending_videos(category, max_results=10)
    return {"videos": videos, "category": category}


@router.get("/video/{video_id}")
async def video_details(video_id: str):
    """Get details for a specific video."""
    details = await get_video_details(video_id)
    if not details:
        raise HTTPException(status_code=404, detail="Video not found")
    return details


@router.post("/chat")
async def youtube_chat(request: ChatRequest):
    """
    Natural language chat interface for YouTube discovery.
    Uses LLM to understand intent and searches YouTube accordingly.
    """
    user_message = request.message.strip()

    # Use LLM to understand the query and extract search intent
    intent = await understand_query(user_message)

    # Execute the search based on intent
    if intent['type'] == 'search':
        videos = await search_youtube(intent['query'], max_results=intent.get('count', 5))
        response_text = format_search_response(videos, intent['query'])
    elif intent['type'] == 'channel':
        videos = await search_channel_videos(intent['channel'], max_results=5)
        response_text = format_channel_response(videos, intent['channel'])
    elif intent['type'] == 'trending':
        videos = await get_trending_videos(intent.get('category', 'all'))
        response_text = format_trending_response(videos, intent.get('category', 'all'))
    elif intent['type'] == 'details':
        details = await get_video_details(intent['video_id'])
        videos = [details] if details else []
        response_text = format_details_response(details)
    else:
        # Default search
        videos = await search_youtube(user_message, max_results=5)
        response_text = format_search_response(videos, user_message)

    return {
        "response": response_text,
        "videos": videos,
        "intent": intent
    }


async def understand_query(query: str) -> dict:
    """Use LLM to understand the user's YouTube query intent."""

    if not GROQ_API_KEY:
        # Fallback: simple keyword matching
        return simple_intent_detection(query)

    system_prompt = """You analyze YouTube search queries and extract the intent.
Return JSON with:
- type: "search" | "channel" | "trending" | "details"
- query: the search terms to use
- channel: channel name if looking for specific creator
- category: for trending (all, music, gaming, news, sports)
- count: number of results (default 5)

Examples:
"latest video from Eric Weinstein" -> {"type": "channel", "channel": "Eric Weinstein", "query": "Eric Weinstein latest"}
"trending music videos" -> {"type": "trending", "category": "music"}
"quantum physics explained" -> {"type": "search", "query": "quantum physics explained"}
"videos with most views today" -> {"type": "search", "query": "viral today most viewed"}

Return ONLY valid JSON, no explanation."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                # Parse JSON from response
                intent = json.loads(content.strip())
                return intent
    except Exception as e:
        print(f"LLM intent detection error: {e}")

    # Fallback to simple detection
    return simple_intent_detection(query)


def simple_intent_detection(query: str) -> dict:
    """Simple keyword-based intent detection fallback."""
    query_lower = query.lower()

    # Check for trending
    if any(word in query_lower for word in ['trending', 'viral', 'popular today']):
        category = 'all'
        if 'music' in query_lower:
            category = 'music'
        elif 'gaming' in query_lower or 'game' in query_lower:
            category = 'gaming'
        elif 'news' in query_lower:
            category = 'news'
        elif 'sport' in query_lower:
            category = 'sports'
        return {"type": "trending", "category": category}

    # Check for channel/creator search
    channel_keywords = ['from', 'by', "channel", "creator", "'s latest", "'s video"]
    for keyword in channel_keywords:
        if keyword in query_lower:
            return {"type": "search", "query": query}

    # Default to search
    return {"type": "search", "query": query}


def format_search_response(videos: list, query: str) -> str:
    """Format search results as a chat response."""
    if not videos:
        return f"I couldn't find any videos for '{query}'. Try a different search term."

    response = f"Here are the top results for **{query}**:\n\n"
    for i, video in enumerate(videos, 1):
        views = video.get('view_count_formatted', 'Unknown views')
        duration = video.get('duration', '')
        response += f"{i}. **{video['title']}**\n"
        response += f"   {video.get('channel', 'Unknown')} • {views} • {duration}\n\n"

    return response


def format_channel_response(videos: list, channel: str) -> str:
    """Format channel search results."""
    if not videos:
        return f"I couldn't find recent videos from '{channel}'."

    response = f"Recent videos from **{channel}**:\n\n"
    for i, video in enumerate(videos, 1):
        views = video.get('view_count_formatted', 'Unknown views')
        response += f"{i}. **{video['title']}**\n"
        response += f"   {views} views\n\n"

    return response


def format_trending_response(videos: list, category: str) -> str:
    """Format trending videos response."""
    if not videos:
        return "Couldn't fetch trending videos right now."

    cat_name = category.title() if category != 'all' else 'General'
    response = f"**Trending {cat_name} Videos:**\n\n"
    for i, video in enumerate(videos, 1):
        views = video.get('view_count_formatted', 'Unknown')
        response += f"{i}. **{video['title']}**\n"
        response += f"   {video.get('channel', '')} • {views} views\n\n"

    return response


def format_details_response(details: dict) -> str:
    """Format video details response."""
    if not details:
        return "Couldn't get video details."

    return f"""**{details['title']}**

**Channel:** {details.get('channel', 'Unknown')}
**Views:** {details.get('view_count_formatted', 'Unknown')}
**Likes:** {details.get('like_count_formatted', 'Unknown')}
**Uploaded:** {details.get('upload_date', 'Unknown')}
**Duration:** {details.get('duration', 'Unknown')}

{details.get('description', '')[:300]}..."""
