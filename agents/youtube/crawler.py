import asyncio
import aiohttp
import json
import re
import time
from typing import Dict, List, Optional, Any, Union
from urllib.parse import quote, urlparse, parse_qs

from config import settings

# Constants
API_KEY = settings.tikhub_api_key
BASE_URL = "https://api.tikhub.io/api/v1/youtube/web"
HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
RATE_LIMIT_DELAY = 1  # Seconds between requests to avoid rate limiting


async def _make_request(endpoint: str, params: Optional[Dict] = None) -> Dict:
    """Make an async HTTP request to the TikHub API."""
    url = f"{BASE_URL}/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, params=params) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        print(f"Request error: {e}")
        return {"error": str(e)}


def extract_video_id(video_id_or_url: str) -> str:
    """
    Extract the video ID from a YouTube URL or return the ID if already provided.

    Args:
        video_id_or_url: YouTube video ID or full URL

    Returns:
        YouTube video ID
    """
    # Check if it's already just a video ID (typically 11 characters)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', video_id_or_url):
        return video_id_or_url

    # Try to extract from URL
    try:
        if "youtu.be" in video_id_or_url:
            # Handle youtu.be URLs
            path = urlparse(video_id_or_url).path
            return path.strip("/")
        else:
            # Handle youtube.com URLs
            parsed_url = urlparse(video_id_or_url)
            return parse_qs(parsed_url.query)['v'][0]
    except Exception:
        # Return as is if we can't parse it
        return ""


async def get_video_info(video_id_or_url: str) -> [Dict]:
    """
    Get information about a YouTube video.

    Args:
        video_id_or_url: YouTube video ID or URL
    """
    video_id = extract_video_id(video_id_or_url)
    result = await _make_request("get_video_info", {"video_id": video_id})
    return [result.get("data", {})]


async def get_video_subtitles(video_id_or_url: str) -> List[Dict]:
    """
    Get subtitles/closed captions for a YouTube video.

    Args:
        video_id_or_url: YouTube video ID or URL
    """
    video_id = extract_video_id(video_id_or_url)
    result = await _make_request("get_video_subtitles", {"video_id": video_id})
    result = result.get("data", {})

    if result.get("is_available"):
        return result.get("subtitles", [])
    else:
        return []


async def get_video_comments(video_id_or_url: str,
                             lang: str = "en-US",
                             sort_by: str = "top",
                             max_pages: int = 1) -> List[Dict]:
    """
    Get comments on a YouTube video with pagination.

    Args:
        video_id_or_url: YouTube video ID or URL
        lang: Language code
        sort_by: Sort method ('top' or 'newest')
        max_pages: Maximum number of pages to fetch
    """
    video_id = extract_video_id(video_id_or_url)
    params = {
        "video_id": video_id,
        "lang": lang,
        "sortBy": sort_by
    }

    all_comments = []
    next_token = None

    for _ in range(max_pages):
        if next_token:
            params["nextToken"] = next_token

        response = await _make_request("get_video_comments_v2", params)
        if "error" in response:
            break

        comments = response.get("data", {}).get("items", [])
        all_comments.extend(comments)

        next_token = response.get("data", {}).get("nextToken")
        if not next_token:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_comments


async def get_relate_video(video_id_or_url: str, max_pages: int = 1) -> List[Dict]:
    """
    Get related videos for a YouTube video with pagination.

    Args:
        video_id_or_url: YouTube video ID or URL
        max_pages: Maximum number of pages to fetch
    """
    video_id = extract_video_id(video_id_or_url)
    params = {"video_id": video_id}

    all_videos = []
    continuation_token = None

    for _ in range(max_pages):
        if continuation_token:
            params["continuation_token"] = continuation_token

        response = await _make_request("get_relate_video", params)
        if "error" in response:
            break

        videos = response.get("data", {}).get("videos", [])
        all_videos.extend(videos)

        continuation_token = response.get("data", {}).get("continuation_token")
        if not continuation_token:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def search_video(query: str,
                       language_code: str = "en",
                       order_by: str = "this_month",
                       country_code: str = "us",
                       max_pages: int = 1) -> List[Dict]:
    """
    Search for YouTube videos with pagination.

    Args:
        query: Search query
        language_code: Language code (e.g., "en")
        order_by: Sort order (last_hour, today, this_week, this_month, this_year)
        country_code: Country code (e.g., "us")
        max_pages: Maximum number of pages to fetch
    """
    params = {
        "search_query": query,
        "language_code": language_code,
        "order_by": order_by,
        "country_code": country_code
    }

    all_videos = []
    continuation_token = None

    for _ in range(max_pages):
        if continuation_token:
            params["continuation_token"] = continuation_token

        response = await _make_request("search_video", params)
        if "error" in response:
            break

        videos = response.get("data", {}).get("videos", [])
        all_videos.extend(videos)

        continuation_token = response.get("data", {}).get("continuation_token")
        if not continuation_token:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def get_channel_id(channel_name: str) -> str:
    """
    Get channel ID from a channel name.

    Args:
        channel_name: YouTube channel name
    """
    result = await _make_request("get_channel_id", {"channel_name": channel_name})
    return result.get("data", {}).get("channel_id")


async def get_channel_info(channel_id: str) -> List[Dict]:
    """
    Get information about a YouTube channel.

    Args:
        channel_id: YouTube channel ID
    """
    result = await _make_request("get_channel_info", {"channel_id": channel_id})
    return [result.get("data", {})]


async def get_channel_videos(channel_id: str,
                             lang: str = "en-US",
                             sort_by: str = "newest",
                             content_type: str = "videos",
                             max_pages: int = 1) -> List[Dict]:
    """
    Get videos from a YouTube channel with pagination.

    Args:
        channel_id: YouTube channel ID or name (with @ for names)
        lang: Language code
        sort_by: Sort method ("newest", "oldest", "mostPopular")
        content_type: Content type ("videos", "shorts", "live")
        max_pages: Maximum number of pages to fetch
    """
    params = {
        "channel_id": channel_id,
        "lang": lang,
        "sortBy": sort_by,
        "contentType": content_type
    }

    all_videos = []
    next_token = None

    for _ in range(max_pages):
        if next_token:
            params["nextToken"] = next_token

        response = await _make_request("get_channel_videos_v2", params)
        if "error" in response:
            break

        videos = response.get("data", {}).get("items", [])
        all_videos.extend(videos)

        next_token = response.get("data", {}).get("nextToken")
        if not next_token:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def get_channel_short_videos(channel_id: str, max_pages: int = 1) -> List[Dict]:
    """
    Get short videos from a YouTube channel with pagination.

    Args:
        channel_id: YouTube channel ID
        max_pages: Maximum number of pages to fetch
    """
    params = {"channel_id": channel_id}

    all_shorts = []
    continuation_token = None

    for _ in range(max_pages):
        if continuation_token:
            params["continuation_token"] = continuation_token

        response = await _make_request("get_channel_short_videos", params)
        if "error" in response:
            break

        shorts = response.get("data", {}).get("videos", [])
        all_shorts.extend(shorts)

        continuation_token = response.get("data", {}).get("continuation_token")
        if not continuation_token:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_shorts


async def search_channel(channel_id: str,
                         query: str,
                         language_code: str = "en",
                         country_code: str = "us",
                         max_pages: int = 1) -> List[Dict]:
    """
    Search for videos within a specific channel with pagination.

    Args:
        channel_id: YouTube channel ID
        query: Search query
        language_code: Language code (e.g., "en")
        country_code: Country code (e.g., "us")
        max_pages: Maximum number of pages to fetch
    """
    params = {
        "channel_id": channel_id,
        "search_query": query,
        "language_code": language_code,
        "country_code": country_code
    }

    all_videos = []
    continuation_token = None

    for _ in range(max_pages):
        if continuation_token:
            params["continuation_token"] = continuation_token

        response = await _make_request("search_channel", params)
        if "error" in response:
            break

        videos = response.get("data", {}).get("videos", [])
        all_videos.extend(videos)

        continuation_token = response.get("data", {}).get("continuation_token")
        if not continuation_token:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def get_trending_videos(language_code: str = "en",
                              country_code: str = "us",
                              section: str = "Now") -> List[Dict]:
    """
    Get trending videos on YouTube.

    Args:
        language_code: Language code (e.g., "en")
        country_code: Country code (e.g., "us")
        section: Trending section ("Now", "Music", "Gaming", "Movies")
    """
    params = {
        "language_code": language_code,
        "country_code": country_code,
        "section": section
    }

    response = await _make_request("get_trending_videos", params)
    if "error" in response:
        return []

    return response.get("data", {}).get("videos", [])


async def save_to_json(data: Any, filename: str) -> None:
    """Save data to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Data saved to {filename}")


# Example usage
async def main():
    start = time.time()

    # Example: Get video info (using URL)
    video_info = await get_video_info("https://www.youtube.com/watch?v=LuIL5JATZsc")
    
    await save_to_json(video_info, "youtube_video_info.json")

    # Example: Get video subtitles
    subtitles = await get_video_subtitles("LuIL5JATZsc")
    await save_to_json(subtitles, "youtube_subtitles.json")

    # Example: Get video comments with pagination
    comments = await get_video_comments("LuIL5JATZsc", max_pages=2)
    await save_to_json(comments, "youtube_comments.json")

    # Example: Get channel info and videos
    channel_info = await get_channel_info("UCXuqSBlHAE6Xw-yeJA0Tunw")  # Linus Tech Tips
    await save_to_json(channel_info, "youtube_channel_info.json")

    channel_videos = await get_channel_videos("UCXuqSBlHAE6Xw-yeJA0Tunw", max_pages=2)
    await save_to_json(channel_videos, "youtube_channel_videos.json")

    # Example: Search for videos
    search_results = await search_video("Minecraft tutorial", max_pages=2)
    await save_to_json(search_results, "youtube_search_results.json")

    # Example: Get trending videos
    trending = await get_trending_videos()
    await save_to_json(trending, "youtube_trending.json")

    # Example: Running multiple operations concurrently
    tasks = [
        get_relate_video("4QFg1rTL6d4", max_pages=1),
        get_channel_short_videos("UCXuqSBlHAE6Xw-yeJA0Tunw", max_pages=1),
        search_channel("UCXuqSBlHAE6Xw-yeJA0Tunw", "AMD")
    ]

    results = await asyncio.gather(*tasks)
    related_videos, shorts, channel_search = results

    await save_to_json(related_videos, "youtube_related.json")
    await save_to_json(shorts, "youtube_shorts.json")
    await save_to_json(channel_search, "youtube_channel_search.json")

    print(f"Total time: {time.time() - start:.2f}s")

# Running the async main function
if __name__ == "__main__":
    asyncio.run(main())