"""
YouTube Search Service - Search YouTube videos using natural language queries
"""
import os
import re
import json
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Use yt-dlp for searching YouTube
import yt_dlp


async def search_youtube(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search YouTube for videos matching the query.
    Returns list of video results with metadata.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': 'ytsearch',
    }

    search_query = f"ytsearch{max_results}:{query}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(search_query, download=False)

        videos = []
        if results and 'entries' in results:
            for entry in results['entries']:
                if entry:
                    video = {
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Unknown'),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                        'channel': entry.get('channel', entry.get('uploader', 'Unknown')),
                        'duration': format_duration(entry.get('duration')),
                        'view_count': entry.get('view_count'),
                        'view_count_formatted': format_views(entry.get('view_count')),
                        'thumbnail': entry.get('thumbnail', f"https://i.ytimg.com/vi/{entry.get('id', '')}/hqdefault.jpg"),
                    }
                    videos.append(video)

        return videos
    except Exception as e:
        print(f"YouTube search error: {e}")
        return []


async def get_video_details(video_id: str) -> Optional[Dict]:
    """Get detailed info for a specific video."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'description': info.get('description', '')[:500],
            'channel': info.get('channel', info.get('uploader')),
            'upload_date': format_upload_date(info.get('upload_date')),
            'duration': format_duration(info.get('duration')),
            'view_count': info.get('view_count'),
            'view_count_formatted': format_views(info.get('view_count')),
            'like_count': info.get('like_count'),
            'like_count_formatted': format_views(info.get('like_count')),
            'comment_count': info.get('comment_count'),
            'thumbnail': info.get('thumbnail'),
            'url': f"https://www.youtube.com/watch?v={video_id}",
        }
    except Exception as e:
        print(f"Video details error: {e}")
        return None


async def get_trending_videos(category: str = "all", max_results: int = 10) -> List[Dict]:
    """Get trending videos. Categories: all, music, gaming, news, sports"""
    # Map categories to search terms that find trending content
    category_queries = {
        'all': 'trending today viral',
        'music': 'music video trending 2024',
        'gaming': 'gaming trending popular',
        'news': 'breaking news today',
        'sports': 'sports highlights trending',
    }

    query = category_queries.get(category, category_queries['all'])
    return await search_youtube(query, max_results)


async def search_channel_videos(channel_name: str, max_results: int = 5) -> List[Dict]:
    """Search for recent videos from a specific channel/creator."""
    query = f"{channel_name} latest video"
    return await search_youtube(query, max_results)


def format_duration(seconds) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    if not seconds:
        return "Unknown"

    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
    except:
        return "Unknown"


def format_views(count: Optional[int]) -> str:
    """Format view count to human readable (1.2M, 500K, etc)."""
    if not count:
        return "Unknown"

    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    elif count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def format_upload_date(date_str: Optional[str]) -> str:
    """Format upload date from YYYYMMDD to readable format."""
    if not date_str:
        return "Unknown"

    try:
        date = datetime.strptime(date_str, "%Y%m%d")
        now = datetime.now()
        diff = now - date

        if diff.days == 0:
            return "Today"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif diff.days < 365:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
    except:
        return date_str
