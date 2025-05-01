import asyncio
import datetime

import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, Union
from config import settings
from common.utils.logging import setup_logger

logger = setup_logger(__name__)

# Constants
TIKHUB_API_KEY = ""
BASE_URL_APP = "https://api.tikhub.io/api/v1/douyin/app/v3"
BASE_URL_WEB = "https://api.tikhub.io/api/v1/douyin/web"
BASE_URL_BILLBOARD = "https://api.tikhub.io/api/v1/douyin/billboard"
BASE_URL_XINGTU = "https://api.tikhub.io/api/v1/douyin/xingtu"
BASE_URL_SEARCH = "https://api.tikhub.io/api/v1/douyin/search"
HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TIKHUB_API_KEY}"
}
RATE_LIMIT_DELAY = 1


async def _make_request(base_url: str, endpoint: str, method: str = "GET", params: Optional[Dict] = None,
                        data: Optional[Dict] = None) -> Dict:
    """
    Make a request to the TikHub API.

    Args:
        base_url: Base URL for the API (app or web or billboard or xingtu or search)
        endpoint: API endpoint
        method: HTTP method (GET or POST)
        params: Query parameters for GET requests
        data: JSON data for POST requests

    Returns:
        Response JSON as dictionary
    """
    url = f"{base_url}/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            if method.upper() == "GET":
                async with session.get(url, headers=HEADERS, params=params) as response:
                    response.raise_for_status()
                    return await response.json()
            elif method.upper() == "POST":
                async with session.post(url, headers=HEADERS, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Request error: {e}")
        return {"error": str(e)}


# DOUYIN WEB API & APP API
async def fetch_video_by_id(aweme_id: str) -> List[Dict]:
    """
    Fetch detailed information about a specific video by its ID.

    Args:
        aweme_id: Douyin video ID

    Returns:
        Video details as dictionary
    """
    # Try v1 endpoint first
    result = await _make_request(BASE_URL_APP, "fetch_one_video_v2", params={"aweme_id": aweme_id})

    # If v1 fails, try v2
    if "error" in result:
        logger.info("V1 endpoint failed, trying V2 endpoint")
        result = await _make_request(BASE_URL_APP, "fetch_one_video", params={"aweme_id": aweme_id})

    return [result.get("data", {}).get("aweme_detail", {})]


async def fetch_video_by_share_url(share_url: str) -> List[Dict]:
    """
    Fetch detailed information about a specific video by its share URL.

    Args:
        share_url: Douyin video share URL

    Returns:
        Video details as dictionary
    """
    result = await _make_request(BASE_URL_APP, "fetch_one_video_by_share_url", params={"share_url": share_url})
    return [result.get("data", {}).get("aweme_detail", {})]


async def fetch_multiple_videos(aweme_ids: List[str]) -> List[Dict]:
    """
    Fetch detailed information about multiple videos by their IDs.

    Args:
        aweme_ids: List of Douyin video IDs

    Returns:
        List of video details
    """
    result = await _make_request(BASE_URL_APP, "fetch_multi_video", method="POST", data={"aweme_ids": aweme_ids})
    return result.get("data", {}).get("aweme_details", [])


async def fetch_video_statistics(aweme_ids: str) -> List[Dict]:
    """
    Fetch statistics for one video.

    Args:
        aweme_ids: Single video ID

    Returns:
        Video statistics
    """
    # check if there's only one ID
    result = await _make_request(BASE_URL_APP, "fetch_video_statistics",
                                 params={"aweme_ids": aweme_ids})

    return result.get("data", {}).get("statistics_list",[])


async def fetch_multiple_video_statistics(aweme_ids: str) -> List[Dict]:
    """
    Fetch statistics for one or multiple videos.

    Args:
        aweme_ids: Single video ID or list of video IDs (max 2 for single endpoint)

    Returns:
        Video statistics
    """
    result = await _make_request(BASE_URL_APP, "fetch_multi_video_statistics",
                                 params={"aweme_ids": aweme_ids})

    return result.get("data", {}).get("statistics_list",[])


async def fetch_user_profile(sec_user_id: Optional[str] = None, uid: Optional[str] = None,
                             short_id: Optional[str] = None) -> List[Dict]:
    """
    Fetch a user's profile information using various identifiers.

    Args:
        sec_user_id: User's sec_user_id
        uid: User's UID
        short_id: User's short ID

    Returns:
        User profile information
    """
    if sec_user_id:
        # Prefer app API for more complete data
        result = await _make_request(BASE_URL_APP, "handler_user_profile", params={"sec_user_id": sec_user_id})
        # If app fails, try web API
        if "error" in result:
            result = await _make_request(BASE_URL_WEB, "handler_user_profile_v4", params={"sec_user_id": sec_user_id})
            user_info = result.get("data", {}).get("user", {})
            user_live_info = result.get("data", {}).get("live_user", {})
            user_info.update(user_live_info)
            return [user_info]
        else:
            return [result.get("data", {}).get("user", {})]
    elif uid:
        result = await _make_request(BASE_URL_WEB, "fetch_user_profile_by_uid", params={"uid": uid})
        return [result.get("data", {}).get("data", {})]
    elif short_id:
        result = await _make_request(BASE_URL_WEB, "fetch_user_profile_by_short_id", params={"short_id": short_id})
        return [result.get("data", {}).get("data", {}).get("users", {})]

    return []


async def fetch_user_fans(sec_user_id: str, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Fetch user's fans with pagination.

    Args:
        sec_user_id: User's sec_user_id
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of users
    """
    endpoint = "fetch_user_fans_list"
    params = {"sec_user_id": sec_user_id, "count": count}
    all_fans = []
    max_time = "0"

    for _ in range(max_pages):
        params["max_time"] = max_time
        response = await _make_request(BASE_URL_APP, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        fans = data.get("followers", [])
        all_fans.extend(fans)

        if not fans:
            break

        max_time = data.get("max_time", "0")
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_fans


async def fetch_user_following(sec_user_id: str, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Fetch users followed by a user with pagination.

    Args:
        sec_user_id: User's sec_user_id
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of users
    """
    endpoint = "fetch_user_following_list"
    params = {"sec_user_id": sec_user_id, "count": count, "source_type": 1}
    all_following = []
    max_time = "0"

    for _ in range(max_pages):
        params["max_time"] = max_time
        response = await _make_request(BASE_URL_WEB, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        following = data.get("followings", [])
        all_following.extend(following)

        max_time = data.get("max_time", "0")
        has_more = data.get("has_more", False)
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_following


async def fetch_user_post_videos(sec_user_id: str, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Fetch videos posted by a user with pagination.

    Args:
        sec_user_id: User's sec_user_id
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of videos
    """
    endpoint = "fetch_user_post_videos"
    params = {"sec_user_id": sec_user_id, "count": count}
    all_videos = []
    max_cursor = 0

    for _ in range(max_pages):
        params["max_cursor"] = max_cursor
        response = await _make_request(BASE_URL_APP, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        videos = data.get("aweme_list", [])
        all_videos.extend(videos)

        max_cursor = data.get("max_cursor", 0)
        has_more = data.get("has_more", False)
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_user_like_videos(sec_user_id: str, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Fetch videos liked by a user with pagination.

    Args:
        sec_user_id: User's sec_user_id
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of videos
    """
    endpoint = "fetch_user_like_videos"
    params = {"sec_user_id": sec_user_id, "count": count}
    all_videos = []
    max_cursor = 0

    for _ in range(max_pages):
        params["max_cursor"] = max_cursor
        response = await _make_request(BASE_URL_APP, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        videos = data.get("aweme_list", [])
        all_videos.extend(videos)

        max_cursor = data.get("max_cursor", 0)
        has_more = data.get("has_more", False)
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos



async def fetch_video_comments(aweme_id: str, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Fetch comments on a video with pagination.

    Args:
        aweme_id: ID of the video
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of comments
    """
    endpoint = "fetch_video_comments"
    params = {"aweme_id": aweme_id, "count": count}
    all_comments = []
    cursor = 0

    for _ in range(max_pages):
        params["cursor"] = cursor
        response = await _make_request(BASE_URL_APP, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        comments = data.get("comments", [])
        all_comments.extend(comments)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        cursor = data.get("cursor", 0)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_comments


async def fetch_comment_replies(item_id: str, comment_id: str, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Fetch replies to a comment with pagination.

    Args:
        item_id: ID of the video
        comment_id: ID of the comment
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of replies
    """
    endpoint = "fetch_video_comment_replies"
    params = {"item_id": item_id, "comment_id": comment_id, "count": count}
    all_replies = []
    cursor = 0

    for _ in range(max_pages):
        params["cursor"] = cursor
        response = await _make_request(BASE_URL_APP, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        replies = data.get("comments", [])
        all_replies.extend(replies)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        cursor = data.get("cursor", 0)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_replies


async def fetch_mix_detail(mix_id: str) -> List[Dict]:
    """
    Fetch information about a video mix/collection.

    Args:
        mix_id: ID of the mix

    Returns:
        Mix details
    """
    result = await _make_request(BASE_URL_APP, "fetch_video_mix_detail", params={"mix_id": mix_id})
    return [result.get("data", {}).get("mix_info", {})]


async def fetch_mix_videos(mix_id: str, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Fetch videos in a mix/collection with pagination.

    Args:
        mix_id: ID of the mix
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of videos
    """
    endpoint = "fetch_video_mix_post_list"
    params = {"mix_id": mix_id, "count": count}
    all_videos = []
    cursor = 0

    for _ in range(max_pages):
        params["cursor"] = cursor
        response = await _make_request(BASE_URL_APP, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        videos = data.get("aweme_list", [])
        all_videos.extend(videos)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        cursor = data.get("cursor", 0)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos



async def fetch_music_detail(music_id: str) -> List[Dict]:
    """
    Fetch information about a music track.

    Args:
        music_id: ID of the music

    Returns:
        Music details
    """
    result = await _make_request(BASE_URL_APP, "fetch_music_detail", params={"music_id": music_id})
    return [result.get("data", {}).get("music_info", {})]



async def fetch_music_videos(music_id: str, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Fetch videos using a specific music track with pagination.

    Args:
        music_id: ID of the music
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of videos
    """
    endpoint = "fetch_music_video_list"
    params = {"music_id": music_id, "count": count}
    all_videos = []
    cursor = 0

    for _ in range(max_pages):
        params["cursor"] = cursor
        response = await _make_request(BASE_URL_APP, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        videos = data.get("aweme_list", [])
        all_videos.extend(videos)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        cursor = data.get("cursor", 0)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos



async def fetch_hashtag_detail(ch_id: str) -> List[Dict]:
    """
    Fetch information about a hashtag.

    Args:
        ch_id: ID of the hashtag

    Returns:
        Hashtag details
    """
    result = await _make_request(BASE_URL_APP, "fetch_hashtag_detail", params={"ch_id": ch_id})
    return [result.get("data", {}).get("ch_info", {})]


async def fetch_hashtag_videos(ch_id: str, sort_type: int = 0, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Fetch videos with a specific hashtag with pagination.

    Args:
        ch_id: ID of the hashtag
        sort_type: Sorting type (0: comprehensive, 1: most likes, 2: latest)
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of videos
    """
    endpoint = "fetch_hashtag_video_list"
    params = {"ch_id": ch_id, "sort_type": sort_type, "count": count}
    all_videos = []
    cursor = 0

    for _ in range(max_pages):
        params["cursor"] = cursor
        response = await _make_request(BASE_URL_APP, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        videos = data.get("mix_list", [])
        all_videos.extend(videos)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        cursor = data.get("cursor", 0)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos



# Search Functions
async def fetch_search_suggest(keyword: str, sort_type: int = 0, publish_time: int = 0,
                                  filter_duration: int = 0, content_type: int = 0) -> List[Dict]:
    """

Fetch keyword suggestion results from Douyin App.

    Args:
        keyword: Search keyword
        sort_type: Sort type (usually 0)
        publish_time: Filter by publish time (usually 0)
        filter_duration: Filter by duration (usually 0)
        content_type: Content type filter (usually 0)

    Returns:
        List of hashtag suggestions
    """
    endpoint = "fetch_search_suggest"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }

    response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

    if "error" in response:
        return []

    data_obj = response.get("data", {})
    results = data_obj.get("sug_list", [])
    return results


async def fetch_general_search_v3(keyword: str, max_pages: int = 1,
                                  sort_type: int = 0, publish_time: int = 0,
                                  filter_duration: Union[int, str] = 0,
                                  content_type: int = 0) -> List[Dict]:
    """
    Fetch general search results from Douyin App (V3 version).

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (0=comprehensive, 1=most likes, 2=latest)
        publish_time: Filter by publish time (0=any, 1=last day, 7=last week, 180=last half year)
        filter_duration: Filter by video duration (0=any, "0-1"=under 1min, "1-5"=1-5min, "5-10000"=over 5min)
        content_type: Content type filter (0=any, 1=video, 2=image, 3=article)

    Returns:
        List of search results
    """
    endpoint = "fetch_general_search_v3"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }
    all_results = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", {})
        results = data_obj.get("data", [])
        all_results.extend(results)

        # Get cursor and search_id for next page
        data["cursor"] = data_obj.get("cursor", 0)
        has_more = data_obj.get("has_more", False)
        data["search_id"] = data_obj.get("extra", {}).get("logid", "")

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_video_search_v2(keyword: str, max_pages: int = 1,
                                sort_type: int = 0, publish_time: int = 0,
                                filter_duration: Union[int, str] = 0,
                                content_type: int = 0) -> List[Dict]:
    """
    Fetch video search results from Douyin App (V2 version).

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (0=comprehensive, 1=most likes, 2=latest)
        publish_time: Filter by publish time (0=any, 1=last day, 7=last week, 180=last half year)
        filter_duration: Filter by video duration (0=any, "0-1"=under 1min, "1-5"=1-5min, "5-10000"=over 5min)
        content_type: Content type filter (usually 0)

    Returns:
        List of video search results
    """
    endpoint = "fetch_video_search_v2"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }
    all_results = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", {})
        results = data_obj.get("business_data", [])
        all_results.extend(results)

        business_config = data_obj.get("business_config", {})
        data["cursor"] = business_config.get("next_page",{}).get("cursor", 0)
        data["search_id"] = business_config.get("next_page",{}).get("search_id", "")
        has_more = business_config.get("has_more", False)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_multi_search(keyword: str, max_pages: int = 1,
                             sort_type: int = 0, publish_time: int = 0,
                             filter_duration: Union[int, str] = 0,
                             content_type: int = 0) -> List[Dict]:
    """
    Fetch multi-type search results from Douyin App.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (0=comprehensive, 1=most likes, 2=latest)
        publish_time: Filter by publish time (0=any, 1=last day, 7=last week, 180=last half year)
        filter_duration: Filter by video duration (0=any, "0-1"=under 1min, "1-5"=1-5min, "5-10000"=over 5min)
        content_type: Content type filter (0=any, 1=video, 2=image, 3=article)

    Returns:
        List of multi-type search results
    """
    endpoint = "fetch_multi_search"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }
    all_results = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", [])
        for item in data_obj:
            if isinstance(item, dict):
                if "business_data" in item:
                    all_results.extend(item["business_data"])
                    business_config = item["business_config"]
                    has_more = business_config.get("has_more", False)
                    if not has_more:
                        break
                    data["cursor"] = business_config.get("next_page",{}).get("cursor", 0)
                    data["search_id"] = business_config.get("next_page",{}).get("search_id", "")

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results



async def fetch_user_search(keyword: str, max_pages: int = 1,
                            douyin_user_fans: str = "", douyin_user_type: str = "") -> List[Dict]:
    """
    Fetch user search results from Douyin App.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        douyin_user_fans: Filter by fan count
            (""=any, "0_1k"=under 1k, "1k_1w"=1k-10k, "1w_10w"=10k-100k,
             "10w_100w"=100k-1M, "100w_"=over 1M)
        douyin_user_type: Filter by user type
            (""=any, "common_user"=normal, "enterprise_user"=business, "personal_user"=verified)

    Returns:
        List of user search results
    """
    endpoint = "fetch_user_search"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "douyin_user_fans": douyin_user_fans,
        "douyin_user_type": douyin_user_type,
        "search_id": ""
    }
    all_results = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", {})
        results = data_obj.get("user_list", [])
        all_results.extend(results)

        # Get cursor and search_id for next page
        data["cursor"] = data_obj.get("cursor", 0)
        data["search_id"] = data_obj.get("extra", {}).get("log_id", "")
        has_more = data_obj.get("has_more", False)

        # Check if there are more results
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results



async def fetch_image_search(keyword: str, max_pages: int = 1,
                             sort_type: int = 0, publish_time: int = 0,
                             filter_duration: int = 0, content_type: int = 2) -> List[Dict]:
    """
    Fetch image search results from Douyin App.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (0=comprehensive, 1=most likes, 2=latest)
        publish_time: Filter by publish time (0=any, 1=last day, 7=last week, 180=last half year)
        filter_duration: Filter by duration (usually 0)
        content_type: Content type filter (should be 2 for images)

    Returns:
        List of image search results
    """
    endpoint = "fetch_image_search"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }
    all_results = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", {})
        results = data_obj.get("business_data", [])
        all_results.extend(results)

        # Get cursor and search_id for next page
        business_config = data_obj.get("business_config", {})
        data["cursor"] = business_config.get("next_page", {}).get("cursor", 0)
        data["search_id"] = business_config.get("next_page",{}).get("search_id", "")
        has_more = business_config.get("has_more", False)

        # Check if there are more results
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results



async def fetch_live_search(keyword: str, max_pages: int = 1,
                            sort_type: int = 0, publish_time: int = 0,
                            filter_duration: int = 0, content_type: int = 0) -> List[Dict]:
    """
    Fetch live stream search results from Douyin App.
    Tries V2 endpoint first, falls back to V1 if V2 fails.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (0=comprehensive, 1=most likes, 2=latest)
        publish_time: Filter by publish time (0=any, 1=last day, 7=last week, 180=last half year)
        filter_duration: Filter by duration (usually 0)
        content_type: Content type filter (usually 0)

    Returns:
        List of live stream search results
    """
    endpoint_v2 = "fetch_live_search_v2"
    # endpoint_v1 = "fetch_live_search_v1" // V1 endpoint is not used
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }
    all_results = []

    for _ in range(max_pages):

        response = await _make_request(BASE_URL_SEARCH, endpoint_v2, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", {})
        results = data_obj.get("business_data", [])
        all_results.extend(results)

        # Get cursor and search_id for next page
        business_config = data_obj.get("business_config", {})
        data["cursor"] = business_config.get("next_page", {}).get("cursor", 0)
        data["search_id"] = business_config.get("next_page",{}).get("search_id", "")
        has_more = business_config.get("has_more", False)

        # Check if there are more results
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_challenge_search(keyword: str, max_pages: int = 1,
                                 sort_type: int = 0, publish_time: int = 0,
                                 filter_duration: int = 0, content_type: int = 0) -> List[Dict]:
    """
    Fetch hashtag/challenge search results from Douyin App using V2 API.
    Supports searching by keyword and returns detailed challenge information,
    including name, cover image, view count, and participant count.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (usually 0)
        publish_time: Filter by publish time (usually 0)
        filter_duration: Filter by duration (usually 0)
        content_type: Content type filter (usually 0)

    Returns:
        List of hashtag search results
    """
    endpoint_v2 = "fetch_challenge_search_v2"
    # endpoint_v1 = "fetch_challenge_search_v1" // V1 endpoint is not used
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }
    all_results = []

    # Try V2 endpoint
    try_v2 = True

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_SEARCH, endpoint_v2, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", {})
        results = data_obj.get("business_data", [])
        all_results.extend(results)

        # Get cursor and search_id for next page
        business_config = data_obj.get("business_config", {})
        data["cursor"] = business_config.get("next_page", {}).get("cursor", 0)
        data["search_id"] = business_config.get("next_page",{}).get("search_id", "")
        has_more = business_config.get("has_more", False)

        # Check if there are more results
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_challenge_suggest(keyword: str, max_pages: int = 1,
                                  sort_type: int = 0, publish_time: int = 0,
                                  filter_duration: int = 0, content_type: int = 0) -> List[Dict]:
    """
    Fetch hashtag/challenge suggestions from Douyin App based on the input keyword.
    Returns a list of related hashtags including name and view count.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (usually 0)
        publish_time: Filter by publish time (usually 0)
        filter_duration: Filter by duration (usually 0)
        content_type: Content type filter (usually 0)

    Returns:
        List of hashtag suggestions
    """
    endpoint = "fetch_challenge_suggest"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }

    response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

    if "error" in response:
        return []

    data_obj = response.get("data", {})
    results = data_obj.get("sug_list", [])
    return results


async def fetch_experience_search(keyword: str, max_pages: int = 1,
                                  sort_type: int = 0, publish_time: int = 0,
                                  filter_duration: Union[int, str] = 0,
                                  content_type: int = 0) -> List[Dict]:
    """
    Fetch experience (knowledge/tutorial) content search results from Douyin App.
    Retrieves video results related to knowledge sharing, tutorials, or tips based on the input keyword.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (0=comprehensive, 1=most likes, 2=latest)
        publish_time: Filter by publish time (0=any, 1=last day, 7=last week, 180=last half year)
        filter_duration: Filter by video duration (0=any, "0-1"=under 1min, "1-5"=1-5min, "5-10000"=over 5min)
        content_type: Content type filter (usually 0)

    Returns:
        List of experience search results
    """
    endpoint = "fetch_experience_search"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }
    all_results = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", {})
        results = data_obj.get("business_data", [])
        all_results.extend(results)

        # Get cursor and search_id for next page
        business_config = data_obj.get("business_config", {})
        data["cursor"] = business_config.get("next_page", {}).get("cursor", 0)
        data["search_id"] = business_config.get("next_page",{}).get("search_id", "")
        has_more = business_config.get("has_more", False)

        # Check if there are more results
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_music_search(keyword: str, max_pages: int = 1,
                             sort_type: int = 0, publish_time: int = 0,
                             filter_duration: int = 0, content_type: int = 0) -> List[Dict]:
    """
    Fetch music search results from Douyin App.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (usually 0)
        publish_time: Filter by publish time (usually 0)
        filter_duration: Filter by duration (usually 0)
        content_type: Content type filter (usually 0)

    Returns:
        List of music search results
    """
    endpoint = "fetch_music_search"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }
    all_results = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", {})
        results = data_obj.get("music_info_list", [])
        all_results.extend(results)

        # Get cursor and search_id for next page
        data["cursor"] = data_obj.get("cursor", 0)
        data["search_id"] = data_obj.get("extra",{}).get("logid", "")
        has_more = data_obj.get("has_more", False)

        # Check if there are more results
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_discuss_search(keyword: str, max_pages: int = 1,
                               sort_type: int = 0, publish_time: int = 0,
                               filter_duration: Union[int, str] = 0,
                               content_type: int = 0) -> List[Dict]:
    """
    Fetch discussion/Q&A content search results from Douyin App.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        sort_type: Sort type (0=comprehensive, 1=most likes, 2=latest)
        publish_time: Filter by publish time (0=any, 1=last day, 7=last week, 180=last half year)
        filter_duration: Filter by video duration (0=any, "0-1"=under 1min, "1-5"=1-5min, "5-10000"=over 5min)
        content_type: Content type filter (0=any, 1=video, 2=image, 3=article)

    Returns:
        List of discussion search results
    """
    endpoint = "fetch_discuss_search"
    data = {
        "keyword": keyword,
        "cursor": 0,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": ""
    }
    all_results = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)

        if "error" in response:
            break

        data_obj = response.get("data", {})
        results = data_obj.get("business_data", [])
        all_results.extend(results)

        # Get cursor and search_id for next page
        business_config = data_obj.get("business_config", {})
        data["cursor"] = business_config.get("next_page", {}).get("cursor", 0)
        data["search_id"] = business_config.get("next_page",{}).get("search_id", "")
        has_more = business_config.get("has_more", False)

        # Check if there are more results
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_school_search(keyword: str) -> List[Dict]:
    """
    Fetch school search results from Douyin App.

    Args:
        keyword: Search keyword (school name or region), China Only
        max_pages: Maximum number of pages to fetch

    Returns:
        List of school search results
    """
    endpoint = "fetch_school_search"
    data = {
        "keyword": keyword,
        "cursor": 0
    }

    response = await _make_request(BASE_URL_SEARCH, endpoint, method="POST", data=data)
    all_schools = response.get("data", {}).get("schools", [])

    return all_schools


# Hot Search Functions
async def fetch_hot_search_list(board_type: int = 0, board_sub_type: str = "") -> List[Dict]:
    """
    Fetch Douyin hot search list.

    Args:
        board_type: Board type (0: hot search, 2: other)
        board_sub_type: Board subtype for board_type=2, [seeding, 2, 4, hotspot_challenge]

    Returns:
        List of hot searches
    """
    params = {"board_type": board_type}

    if board_sub_type:
        if board_type == 2:
            params["board_sub_type"] = board_sub_type
        else:
            raise ValueError("board_sub_type is only valid when board_type is 2")

    result = await _make_request(BASE_URL_APP, "fetch_hot_search_list", params=params)
    return [result.get("data", {}).get("data", {})]


async def fetch_music_hot_search_list() -> List[Dict]:
    #TODO: need a pagination
    """
    Fetch Douyin music hot search list.

    Returns:
        List of hot music searches
    """
    result = await _make_request(BASE_URL_APP, "fetch_music_hot_search_list")
    return result.get("data", {}).get("music_list", [])


async def fetch_brand_hot_search_list() -> List[Dict]:
    """
    Fetch Douyin brand hot search list.

    Returns:
        List of hot brand searches
    """
    result = await _make_request(BASE_URL_APP, "fetch_brand_hot_search_list")
    return result.get("data", {}).get("category_list", [])


async def fetch_brand_hot_search_list_detail(category_id: str) -> List[Dict]:
    #TODO: seems unnecessary.
    """
    Fetch Douyin brand hot search list detail.

    Returns:
        Detailed list of hot brand searches
    """
    params = {"category_id": category_id}
    result = await _make_request(BASE_URL_APP, "fetch_brand_hot_search_list_detail", params=params)
    return [result.get("data", {}).get("weekly_info", {})]


# URL and QR Code Functions
async def generate_short_url(url: str) -> str:
    """
    Generate a Douyin short URL.

    Args:
        url: Original URL

    Returns:
        Short URL
    """
    result = await _make_request(BASE_URL_APP, "generate_douyin_short_url", params={"url": url})
    return result.get("data", {}).get("short_url", "")


async def generate_video_share_qrcode(object_id: str) -> str:
    """
    Generate a QR code for sharing a Douyin video.

    Args:
        object_id: Video ID

    Returns:
        QR code URL
    """
    result = await _make_request(BASE_URL_APP, "generate_douyin_video_share_qrcode", params={"object_id": object_id})
    return result.get("data", {}).get("qrcode_url", {}).get("url_list", [])[0]


# Live Stream Functions
async def fetch_live_stream(webcast_id: Optional[str] = None, sec_uid: Optional[str] = None,
                            room_id: Optional[str] = None, url: Optional[str] = None) -> List[Dict]:
    """
    Fetch information about a live stream using various identifiers.

    Args:
        webcast_id: Live room webcast ID
        sec_uid: User's sec_uid
        room_id: Live room ID
        url: Live room URL

    Returns:
        Live stream information
    """
    if not (webcast_id or sec_uid or room_id) and not url:
        raise ValueError("At least one of webcast_id, sec_uid, room_id or url must be provided.")

    # Extract IDs from URL if provided
    if url and not (webcast_id or sec_uid or room_id):
        if "live/" in url:
            webcast_id = url.split("live/")[-1].split("?")[0]
        elif "user/" in url:
            sec_uid = url.split("user/")[-1].split("?")[0]


    if webcast_id:
        result = await _make_request(BASE_URL_WEB, "fetch_user_live_videos", params={"webcast_id": webcast_id})
    elif sec_uid:
        result = await _make_request(BASE_URL_WEB, "fetch_user_live_videos_by_sec_uid", params={"sec_uid": sec_uid})
    elif room_id:
        result = await _make_request(BASE_URL_WEB, "fetch_user_live_videos_by_room_id_v2", params={"room_id": room_id})

    return [result.get("data", {}).get("data", {})]


async def fetch_live_gift_ranking(room_id: str) -> List[Dict]:
    """
    Fetch gift ranking for a live stream.

    Args:
        room_id: Live room ID
        rank_type: Ranking type (default 30)

    Returns:
        Gift ranking information
    """
    params = {
        "room_id": room_id,
        "rank_type": 30
    }
    result = await _make_request(BASE_URL_WEB, "fetch_live_gift_ranking", params=params)
    return [result.get("data", {}).get("data", {})]


# Helper Functions
async def get_sec_user_id(url: str) -> str:
    """
    Extract sec_user_id from a user profile URL.

    Args:
        url: User profile URL

    Returns:
        sec_user_id
    """
    result = await _make_request(BASE_URL_WEB, "get_sec_user_id", params={"url": url})
    return result.get("data", "")


async def get_all_sec_user_ids(urls: List[str]) -> List[str]:
    """
    Extract sec_user_ids from multiple user profile URLs.

    Args:
        urls: List of user profile URLs (max 10)

    Returns:
        List of sec_user_ids with corresponding URLs
    """
    if len(urls) > 10:
        raise ValueError("Maximum 10 URLs are allowed.")

    if isinstance(urls, List):
        raise ValueError("urls should be a list of strings.")

    result = await _make_request(BASE_URL_WEB, "get_all_sec_user_id", method="POST", data={"url": urls[:10]})
    return result.get("data", [])


async def get_aweme_id(url: str) -> str:
    """
    Extract aweme_id from a video URL.

    Args:
        url: Video URL

    Returns:
        aweme_id
    """
    result = await _make_request(BASE_URL_WEB, "get_aweme_id", params={"url": url})
    return result.get("data", "")


async def get_all_aweme_ids(urls: List[str]) -> List[str]:
    """
    Extract aweme_ids from multiple video URLs, up to 20 URLs.

    Args:
        urls: List of video URLs

    Returns:
        List of aweme_ids with corresponding URLs
    """
    if len(urls) > 20:
        raise ValueError("Maximum 20 URLs are allowed.")

    if isinstance(urls, List):
        raise ValueError("urls should be a list of strings.")

    result = await _make_request(BASE_URL_WEB, "get_all_aweme_id", method="POST", data={"url": urls})
    return result.get("data", [])


async def get_webcast_id(url: str) -> str:
    """
    Extract webcast_id from a live room URL.

    Args:
        url: Live room URL

    Returns:
        webcast_id
    """
    result = await _make_request(BASE_URL_WEB, "get_webcast_id", params={"url": url})
    return result.get("data", "")


async def get_all_webcast_ids(urls: List[str]) -> List[str]:
    """
    Extract webcast_ids from multiple live room URLs.

    Args:
        urls: List of live room URLs (max 20)

    Returns:
        List of webcast_ids with corresponding URLs
    """
    if len(urls) > 20:
        raise ValueError("Maximum 20 URLs are allowed.")
    if isinstance(urls, List):
        raise ValueError("urls should be a list of strings.")

    result = await _make_request(BASE_URL_WEB, "get_all_webcast_id", method="POST", data={"urls": urls[:20]})
    return result.get("data", [])


async def webcast_id_to_room_id(webcast_id: str) -> str:
    """
    Convert webcast_id to room_id.

    Args:
        webcast_id: Webcast ID

    Returns:
        Room ID
    """
    result = await _make_request(BASE_URL_WEB, "webcast_id_2_room_id", params={"webcast_id": webcast_id})
    return result.get("data", {}).get("room_id", "")


# Other Video Feed Functions
async def fetch_series_aweme(count: int = 16, content_type: int = 0, cookie: str = "", max_pages: int = 1) -> List[Dict]:
    """
    Fetch series videos (short dramas).

    Args:
        count: Number of results per page
        content_type: 子类型，默认为0
        0: 热榜
        101: 甜宠
        102: 搞笑
        104: 正能量
        105: 成长
        106: 悬疑
        109: 家庭
        110: 都市
        112: 奇幻
        113: 玄幻
        114: 职场
        115: 青春
        116: 古装
        117: 动作
        119: 逆袭
        124: 其他
        cookie: User cookie for authenticated requests
        max_pages: Maximum number of pages to fetch

    Returns:
        List of series videos
    """
    endpoint = "fetch_series_aweme"
    params = {"count": count, "content_type": content_type}

    if cookie:
        params["cookie"] = cookie

    all_videos = []
    offset = 0

    for _ in range(max_pages):
        params["offset"] = offset
        response = await _make_request(BASE_URL_WEB, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        videos = data.get("card_list", [])
        all_videos.extend(videos)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        offset = data.get("offset", 0)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_category_recommendation_videos(category: str, count: int = 16, max_pages: int = 1, cookie: str = "") -> List[Dict]:
    """
    Fetch recommendation videos by category (knowledge, game, cartoon, music, food).

    Args:
        category: Category name (knowledge, game, cartoon, music, food)
        count: Number of results per page
        max_pages: Maximum number of pages to fetch
        cookie: User cookie for authenticated requests

    Returns:
        List of videos
    """
    # Map category to endpoint
    category_endpoints = {
        "knowledge": "fetch_knowledge_aweme",
        "game": "fetch_game_aweme",
        "cartoon": "fetch_cartoon_aweme",
        "music": "fetch_music_aweme",
        "food": "fetch_food_aweme"
    }

    if category not in category_endpoints:
        return []

    endpoint = category_endpoints[category]
    params = {"count": count, "refresh_index": 1}

    if cookie:
        params["cookie"] = cookie

    all_videos = []
    refresh_index = 1

    for _ in range(max_pages):
        params["refresh_index"] = refresh_index
        response = await _make_request(BASE_URL_WEB, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        videos = data.get("aweme_list", [])
        all_videos.extend(videos)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        refresh_index += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


# Home Feed and Related Videos
async def fetch_home_feed(max_pages: int =1) -> List[Dict]:
    """
    Fetch Douyin home feed recommendations.

    Returns:
        List of recommended videos
    """
    params = {
        "count": 20,
        "refresh_index": 1
    }
    all_videos = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_WEB, "fetch_home_feed", params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        videos = data.get("aweme_list", [])
        all_videos.extend(videos)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        params["refresh_index"] = params["refresh_index"] + 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_related_posts(aweme_id: str, count: int = 20, max_pages: int = 1) -> List[Dict]:
    """
    Fetch videos related to a specific video.

    Args:
        aweme_id: Video ID
        count: Number of results per page
        max_pages: Maximum number of pages to fetch

    Returns:
        List of related videos
    """
    endpoint = "fetch_related_posts"
    params = {"aweme_id": aweme_id, "count": count}
    all_videos = []
    refresh_index = 1

    for _ in range(max_pages):
        params["refresh_index"] = refresh_index
        response = await _make_request(BASE_URL_WEB, endpoint, params=params)

        if "error" in response:
            break

        videos = response.get("data", {}).get("aweme_list", [])
        all_videos.extend(videos)

        has_more = response.get("data", {}).get("has_more", False)
        if not has_more:
            break

        refresh_index += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


# User Collections and Additional Video Functions
async def fetch_user_collections(collects_id: str, max_cursor: int = 0, count: int = 20) -> Dict:
    #TODO: have not test yet, need a collects_id
    """
    Fetch user collection data.

    Args:
        collects_id: Collection ID
        max_cursor: Maximum cursor for pagination
        count: Number of results

    Returns:
        Collection data
    """
    params = {
        "collects_id": collects_id,
        "max_cursor": max_cursor,
        "count": count
    }

    result = await _make_request(BASE_URL_WEB, "fetch_user_collects_videos", params=params)
    return result.get("data", {})


async def fetch_user_mix_videos(collection_url: Optional[str]="", mix_id: Optional[str]="", max_cursor: int = 0, count: int = 20) -> Dict:
    """
    Fetch user mix video data.

    Args:
        collection_url: Collection URL
        mix_id: Mix ID
        max_cursor: Maximum cursor for pagination
        count: Number of results

    Returns:
        Mix video data
    """
    if not (collection_url or mix_id):
        raise ValueError("At least one of collection_url or mix_id must be provided.")

    if collection_url:
        # https://www.douyin.com/collection/7348687990509553679 中的 7348687990509553679
        mix_id = collection_url.split("collection/")[-1]

    params = {
        "mix_id": mix_id,
        "max_cursor": max_cursor,
        "counts": count
    }

    result = await _make_request(BASE_URL_WEB, "fetch_user_mix_videos", params=params)
    return result.get("data", {})


# Cookie and Token Generation Functions
async def fetch_guest_cookie(user_agent: str = "") -> str:
    """
    Fetch guest cookie for Douyin web.
    For Example: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36

    Args:
        user_agent: User agent string

    Returns:
        Guest cookie
    """
    result = await _make_request(BASE_URL_WEB, "fetch_douyin_web_guest_cookie", params={"user_agent": user_agent})
    return result.get("data", {}).get("cookie", "")


async def generate_ms_token() -> str:
    """
    Generate real msToken.

    Returns:
        msToken
    """
    result = await _make_request(BASE_URL_WEB, "generate_real_msToken")
    return result.get("data", {}).get("msToken", "")


async def generate_ttwid() -> str:
    """
    Generate ttwid.

    Returns:
        ttwid
    """
    result = await _make_request(BASE_URL_WEB, "generate_ttwid")
    return result.get("data", {}).get("ttwid", "")


async def generate_verify_fp() -> str:
    """
    Generate verify_fp.

    Returns:
        verify_fp
    """
    result = await _make_request(BASE_URL_WEB, "generate_verify_fp")
    return result.get("data", {}).get("verify_fp", "")


async def generate_s_v_web_id() -> str:
    """
    Generate s_v_web_id.

    Returns:
        s_v_web_id
    """
    result = await _make_request(BASE_URL_WEB, "generate_s_v_web_id")
    return result.get("data", {}).get("s_v_web_id", "")


async def generate_x_bogus(url: str, user_agent: str ) -> str:
    """
    Generate X-Bogus parameter.

    Args:
        url: API URL, https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=7148736076176215311&device_platform=webapp&aid=6383&channel=channel_pc_web&pc_client_type=1&version_code=170400&version_name=17.4.0&cookie_enabled=true&screen_width=1920&screen_height=1080&browser_language=zh-CN&browser_platform=Win32&browser_name=Edge&browser_version=117.0.2045.47&browser_online=true&engine_name=Blink&engine_version=117.0.0.0&os_name=Windows&os_version=10&cpu_core_num=128&device_memory=10240&platform=PC&downlink=10&effective_type=4g&round_trip_time=100
        user_agent: User agent string, Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36


    Returns:
        X-Bogus value
    """
    data = {
        "url": url,
        "user_agent": user_agent
    }

    result = await _make_request(BASE_URL_WEB, "generate_x_bogus", method="POST", data=data)
    return result.get("data", {}).get("x_bogus", "")


async def generate_a_bogus(url: str, data: str = "",
                           user_agent: str = "",
                           index_0: int = 0, index_1: int = 1, index_2: int = 14) -> str:
    """
    Generate A-Bogus parameter.

    Args:
        url: API URL https://www.douyin.com/aweme/v1/web/general/search/single/?device_platform=webapp&aid=6383&channel=channel_pc_web&search_channel=aweme_general&enable_history=1&keyword=%E4%B8%AD%E5%8D%8E%E5%A8%98&search_source=normal_search&query_correct_type=1&is_filter_search=0&from_group_id=7346905902554844468&offset=0&count=15&need_filter_settings=1&pc_client_type=1&version_code=190600&version_name=19.6.0&cookie_enabled=true&screen_width=1280&screen_height=800&browser_language=zh-CN&browser_platform=Win32&browser_name=Firefox&browser_version=124.0&browser_online=true&engine_name=Gecko&engine_version=124.0&os_name=Windows&os_version=10&cpu_core_num=16&device_memory=&platform=PC&webid=7348962975497324070&msToken=YCTVM6YGmjFdIpQAN9ykXLBXiSiuHdZkOkEQWTeqVOHBEPmOcM0lNwE0Kd9vgHPMPigSndZDHfAq9k-6lDmH3Jqz6mHHxmn-BzQjmLMIfLIPgirgnOixM9x4PwgcNQ%3D%3D
        data: Request payload (empty string for GET requests)
        user_agent: User agent string, Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36
        index_0: First value of encrypted plaintext list, 0
        index_1: Second value of encrypted plaintext list, 1
        index_2: Third value of encrypted plaintext list, 15

    Returns:
        A-Bogus value
    """
    req_data = {
        "url": url,
        "data": data,
        "user_agent": user_agent,
        "index_0": index_0,
        "index_1": index_1,
        "index_2": index_2
    }

    result = await _make_request(BASE_URL_WEB, "generate_a_bogus", method="POST", data=req_data)
    return result.get("data", {}).get("a_bogus", "")



async def fetch_video_danmaku(item_id: str, duration: int, start_time: int = 0, end_time: Optional[int] = None) -> List[Dict]:
    """
    Fetch video danmaku (comment overlay).

    Args:
        item_id: Video ID
        duration: Video total duration in seconds
        start_time: Start time in seconds
        end_time: End time in seconds (defaults to duration if not provided)

    Returns:
        List of danmaku comments
    """
    if end_time is None:
        end_time = duration

    params = {
        "item_id": item_id,
        "duration": duration,
        "start_time": start_time,
        "end_time": end_time
    }

    result = await _make_request(BASE_URL_WEB, "fetch_one_video_danmaku", params=params)
    return result.get("data", {}).get("danmaku_list", [])



async def fetch_challenge_posts(challenge_id: str, sort_type: int, cookie: Optional[str], count: int = 20, max_pages: int = 1) -> List[Dict]:
    """
    Fetch posts for a challenge/hashtag.

    Args:
        challenge_id: Challenge ID
        sort_type: Sorting type (0: Comprehensive sorting 1: Hottest sorting 2: Latest sorting)
        cookie: User provided Cookie, used to get more data, this is optional
        count: Number of results in each page
        max_pages: Maximum number of pages to fetch

    Returns:
        Challenge posts data
    """
    data = {
        "challenge_id": challenge_id,
        "sort_type": sort_type,
        "cursor": 0,
        "count": count
    }
    all_posts = []

    for _ in range(max_pages):
        if cookie:
            data["cookie"] = cookie

        response = await _make_request(BASE_URL_WEB, "fetch_challenge_posts", method="POST", data=data)

        if "error" in response:
            break

        data = response.get("data", {})
        posts = data.get("aweme_list", [])
        all_posts.extend(posts)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        data["cursor"] = data.get("cursor", 0)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_posts


# XingTu Functions - for influencer/KOL analytics
async def get_xingtu_kolid(uid: Optional[str] = None, sec_user_id: Optional[str] = None,
                           unique_id: Optional[str] = None) -> str:
    """
    Get XingTu kolid by Douyin identifier (uid, sec_user_id, or unique_id).

    Args:
        uid: Douyin user ID
        sec_user_id: Douyin sec_user_id
        unique_id: Douyin unique_id (username)

    Returns:
        XingTu kolid

    Note:
        At least one parameter must be provided.
        If multiple parameters are provided, sec_user_id is prioritized, followed by uid, and then unique_id.
    """
    if sec_user_id:
        result = await _make_request(BASE_URL_XINGTU, "get_xingtu_kolid_by_sec_user_id",
                                     params={"sec_user_id": sec_user_id})
    elif uid:
        result = await _make_request(BASE_URL_XINGTU, "get_xingtu_kolid_by_uid",
                                     params={"uid": uid})
    elif unique_id:
        result = await _make_request(BASE_URL_XINGTU, "get_xingtu_kolid_by_unique_id",
                                     params={"unique_id": unique_id})
    else:
        return ""

    return result.get("data", {}).get("core_user_id", "")


async def fetch_kol_base_info(kol_id: str, platform_channel: str = "_1") -> List[Dict]:
    """
    Get KOL base information.

    Args:
        kol_id: XingTu KOL ID
        platform_channel: Platform channel (_1: Douyin Video, _10: Douyin Live)

    Returns:
        KOL base information
    """
    params = {
        "kolId": kol_id,
        "platformChannel": platform_channel
    }

    result = await _make_request(BASE_URL_XINGTU, "kol_base_info_v1", params=params)
    return [result.get("data", {})]


async def fetch_kol_audience_portrait(kol_id: str) -> List[Dict]:
    """
    Get KOL audience portrait data.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL audience portrait data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_audience_portrait_v1", params={"kolId": kol_id})
    return result.get("data", {}).get("distributions", [])


async def fetch_kol_fans_portrait(kol_id: str) -> Dict:
    #TODO : this endpoint needs to be fixed or updated
    """
    Get KOL fans portrait data.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL fans portrait data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_fans_portrait_v1", params={"kolId": kol_id})
    return result.get("data", {})


async def fetch_kol_service_price(kol_id: str, platform_channel: str = "_1") -> List[Dict]:
    """
    Get KOL service pricing information.

    Args:
        kol_id: XingTu KOL ID
        platform_channel: Platform channel (_1: Douyin Video, _10: Douyin Live)

    Returns:
        KOL service pricing information
    """
    params = {
        "kolId": kol_id,
        "platformChannel": platform_channel
    }

    result = await _make_request(BASE_URL_XINGTU, "kol_service_price_v1", params=params)

    # only keep the industry tags and price_info
    result = result.get("data", {})
    clean_result = {"industry_tags": result.get("industry_tags", []), "price_info": result.get("price_info", [])}
    return [clean_result ]


async def fetch_kol_data_overview(kol_id: str, type_: str = "_1", range_: str = "_2", flow_type: int = 1) -> List[Dict]:
    """
    Get KOL data overview.

    Args:
        kol_id: XingTu KOL ID
        type_: Type (_1: Personal video, _2: XingTu video)
        range_: Range (_2: Last 30 days, _3: Last 90 days)
        flow_type: Flow type (1: Default)

    Returns:
        KOL data overview
    """
    params = {
        "kolId": kol_id,
        "_type": type_,
        "_range": range_,
        "flowType": flow_type
    }

    result = await _make_request(BASE_URL_XINGTU, "kol_data_overview_v1", params=params)
    return [result.get("data", {})]


async def search_kol(keyword: str, platform_source: str = "_1", max_page: int = 1) -> List[Dict]:
    """
    Search for KOLs by keyword.

    Args:
        keyword: Search keyword
        platform_source: Platform source (_1: Douyin, _2: Toutiao, _3: Xigua)
        max_page: Maximum number of pages to fetch

    Returns:
        List of KOLs
    """
    params = {
        "keyword": keyword,
        "platformSource": platform_source,
        "page": 1
    }
    all_kols = []

    for _ in range(max_page):
        result = await _make_request(BASE_URL_XINGTU, "kol_search_v1", params=params)
        data = result.get("data", {}).get("authors", [])
        all_kols.extend(data)

        has_more = result.get("data", {}).get("pagination", {}).get("has_more", False)
        if not has_more:
            break

        params["page"] += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_kols


async def fetch_kol_count_by_keyword(keyword: str, platform_source: str = "_1") -> int:
    """
    Get total KOL count related to a keyword.

    Args:
        keyword: Search keyword
        platform_source: Platform source (_1: Douyin, _2: Toutiao, _3: Xigua)

    Returns:
        KOL count
    """
    params = {
        "keyword": keyword,
        "platformSource": platform_source
    }

    result = await _make_request(BASE_URL_XINGTU, "kol_search_v1", params=params)
    return result.get("data", {}).get("pagination", {}).get("total_count", 0)


async def fetch_kol_conversion_ability(kol_id: str, range_: str = "_1") -> List[Dict]:
    #TODO: code is 200, but data is empty
    """
    Get KOL conversion ability analysis.

    Args:
        kol_id: XingTu KOL ID
        range_: Time range (_1: Last 7 days, _2: Last 30 days, _3: Last 90 days)

    Returns:
        KOL conversion ability analysis
    """
    params = {
        "kolId": kol_id,
        "_range": range_
    }

    result = await _make_request(BASE_URL_XINGTU, "kol_conversion_ability_analysis_v1", params=params)
    return [result.get("data", {})]


async def fetch_kol_video_performance(kol_id: str, only_assign: bool = False) -> List[Dict]:
    # TODO: code is 200, but data is empty
    """
    Get KOL video performance data.

    Args:
        kol_id: XingTu KOL ID
        only_assign: Whether to only show assigned works (True) or all works (False)

    Returns:
        KOL video performance data
    """
    params = {
        "kolId": kol_id,
        "onlyAssign": only_assign
    }

    result = await _make_request(BASE_URL_XINGTU, "kol_video_performance_v1", params=params)
    return [result.get("data", {})]


async def fetch_kol_xingtu_index(kol_id: str) -> List[Dict]:
    """
    This dataset represents key performance metrics for a Key Opinion Leader (KOL) influencer, showing their engagement indices, ranking percentiles, and advertising cost expectations compared to industry averages.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL XingTu index data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_xingtu_index_v1", params={"kolId": kol_id})
    return [result.get("data", {})]


async def fetch_kol_convert_video_display(kol_id: str, detail_type: str = "_1", page: int = 1) -> Dict:
    #TODO: code is 200, but data is empty
    """
    Get KOL conversion video display data.

    Args:
        kol_id: XingTu KOL ID
        detail_type: Detail type (_1: Video data, _2: Product data)
        page: Page number

    Returns:
        KOL conversion video display data
    """
    params = {
        "kolId": kol_id,
        "detailType": detail_type,
        "page": page
    }

    result = await _make_request(BASE_URL_XINGTU, "kol_convert_video_display_v1", params=params)
    return result.get("data", {})


async def fetch_kol_link_struct(kol_id: str) -> List[Dict]:
    """
    Get analysis of a specific KOL influencer specializing in product recommendations,
    showing their engagement metrics and performance across different content categories compared to industry standards.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL link structure data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_link_struct_v1", params={"kolId": kol_id})
    return [result.get("data", {})]


async def fetch_kol_touch_distribution(kol_id: str) -> List[Dict]:
    """
    Get KOL touch distribution data (user sources).

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL touch distribution data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_touch_distribution_v1", params={"kolId": kol_id})
    return [result.get("data", {})]


async def fetch_kol_cp_info(kol_id: str) -> List[Dict]:
    """
    Get KOL cost-performance analysis data, including the Price of different length （CPM）, and expect video views.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL cost-performance analysis data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_cp_info_v1", params={"kolId": kol_id})
    return [result.get("data", {})]


async def fetch_kol_rec_videos(kol_id: str) -> List[Dict]:
    """
    Get KOL's best performance videos and content performance.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL recommended videos and content performance
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_rec_videos_v1", params={"kolId": kol_id})
    return result.get("data", {}).get("masterpiece_videos", [])


async def fetch_kol_daily_fans(kol_id: str, start_date: str, end_date: str) -> List[Dict]:
    """
    Get Douyin KOL daily fans trend data and KOL's fan growth trajectory,
    "daily" shows the total fan count on each date, while "delta" shows the changes in fan numbers between consecutive dates

    Args:
        kol_id: XingTu KOL ID
        start_date: Start date (format: YYYY-MM-DD)
        end_date: End date (format: YYYY-MM-DD)

    Returns:
        KOL daily fans trend data
    """
    params = {
        "kolId": kol_id,
        "startDate": start_date,
        "endDate": end_date
    }

    result = await _make_request(BASE_URL_XINGTU, "kol_daily_fans_v1", params=params)
    return [result.get("data", {})]


async def fetch_author_hot_comment_tokens(kol_id: str) -> List[Dict]:
    """
    Get author hot comment tokens analysis, which shows the most frequently used words in the author's hot comments,

    Args:
        kol_id: XingTu KOL ID

    Returns:
        Author hot comment tokens analysis
    """
    result = await _make_request(BASE_URL_XINGTU, "author_hot_comment_tokens_v1", params={"kolId": kol_id})
    return result.get("data", {}).get("hot_comment_tokens", [])


async def fetch_author_content_hot_comment_keywords(kol_id: str) -> List[Dict]:
    """
    Get author content hot comment keywords analysis.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        Author content hot comment keywords analysis
    """
    result = await _make_request(BASE_URL_XINGTU, "author_content_hot_comment_keywords_v1",
                                 params={"kolId": kol_id})
    result = result.get("data", {})

    cleaned_result = {
        "keyword_item_distribution": result.get("keyword_item_distribution", {}),
        "keyword_map": result.get("keyword_map", {})
    }
    return [cleaned_result]


# BILLBOARD Functions
async def fetch_city_list() -> List[Dict]:
    """
    Get Chinese city list

    Returns:
        City list data, each city contains:
        {
            "value": int,  # City code
            "label": str   # City name
        }
    """
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_city_list")
    return result.get("data", {}).get("data", [])


async def fetch_content_tag() -> List[Dict]:
    """
    Get vertical content tags

    Returns:
        Content tag list, each tag contains:
        {
            "label": str,     # Category name
            "value": int,     # Category ID
            "count": int,     # Count
            "children": List[Dict]  # Subcategory list
        }
    """
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_content_tag")
    return result.get("data", {}).get("data", [])


async def fetch_hot_category_list(billboard_type: str = "total", snapshot_time: str = "",
                                  start_date: str = "", end_date: str = "", keyword: str = "") -> List[Dict]:
    """
    Get hot category list

    Args:
        billboard_type (str, optional): Billboard type, options:
            - "total": Hot total list (default)
            - "rise": Rising hot list
            - "city": Same city hot list
        snapshot_time (str, optional): Snapshot time, format: YYYYMMDDHHMMSS, default empty string
        start_date (str, optional): Start date, format: YYYY-MM-DD, default empty string
        end_date (str, optional): End date, format: YYYY-MM-DD, default empty string
        keyword (str, optional): Search keyword, supports fuzzy search, default empty string

    Returns:
        List[Dict]: Hot category list data, each category contains:
        [
            {
                "label": str,      # Category name, such as "Food", "Travel", etc.
                "value": List[int], # Category ID array, may contain one or more IDs
                "num": int         # Number of hot spots in this category
            },
            ...
        ]

    """
    data = {
        "billboard_type": billboard_type,
        "snapshot_time": snapshot_time,
        "start_date": start_date,
        "end_date": end_date,
        "keyword": keyword
    }
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_category_list", method="GET", params=data)
    return result.get("data", {}).get("data", [])


async def fetch_hot_rise_list(page=1, page_size=50, order="rank", sentence_tag="", keyword=""):
    """
    Get rising hot list

    Parameters:
        page (int): Page number, starting from 1
        page_size (int): Items per page, default 50
        order (str): Sort method, options:
            - "rank": Sort by popularity (default)
            - "rank_diff": Sort by rank change
        sentence_tag (str): Hot category tag, get from hot category list, multiple categories separated by comma, empty for all
        keyword (str): Hot search keyword, supports fuzzy search

    Returns:
        dict: Dictionary containing the following fields
            - code (int): Status code, 0 means success
            - data (dict): Data object
                - list (list): Hot list, each hot item contains:
                    - rank (int): Current rank
                    - rank_diff (float): Rank change
                    - sentence (str): Hot content
                    - sentence_id (int): Hot ID
                    - create_at (int): Creation timestamp
                    - hot_score (int): Hot score
                    - video_count (int): Related video count
                    - sentence_tag (int): Category tag ID
                    - city_code (int): City code
                    - trends (list): Hot trend data array, each trend data point contains:
                        - datetime (str): Time point
                        - hot_score (int): Hot score at this time point
                    - index (int): Index
                    - SnapshotSubType (str): Snapshot subtype
                    - city_name (str): City name
                    - sentence_tag_name (str): Category tag name
                    - SnapshotType (int): Snapshot type
                    - SnapshotID (int): Snapshot ID
                    - first_item_cover_url (str): Cover URL
                    - is_favorite (bool): Whether favorited
                    - item_list (list): Item list
                    - item_list_i64 (list): Item list (64-bit integers)
                    - recommend_type (any): Recommend type
                    - related_event (any): Related event
                    - allow_publish (bool): Whether publishing is allowed
                    - label_name (str): Label name
                    - label (int): Label value
                - total (int): Total records
                - page (int): Current page
                - page_size (int): Page size
            - last_update_time (str): Last update time

    Example:
        >>> result = fetch_hot_rise_list(page=1, page_size=20)
        >>> print(result['data']['list'][0]['hot_score'])
        4633009
    """
    data = {
        "page": str(page),
        "page_size": str(page_size),
        "order": order,
        "sentence_tag": sentence_tag,
        "keyword": keyword
    }
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_rise_list", method="GET", params=data)
    return result.get("data", {}).get("data", {})


async def fetch_hot_city_list(page: int = 1, page_size: int = 10, order: str = "rank",
                              city_code: str = "", sentence_tag: str = "", keyword: str = "") -> Dict:
    """
    Get same city hot list

    Purpose:
        Get hot list data for specified city or all cities, supports pagination, sorting and filtering.

    Args:
        page (int, optional): Page number, starting from 1, default 1
        page_size (int, optional): Items per page, range 1-50, default 10
        order (str, optional): Sort method, options:
            - "rank": Sort by popularity (default)
            - "rank_diff": Sort by rank change
        city_code (str, optional): City code, get from city list, empty string means all cities
        sentence_tag (str, optional): Hot category tag, get from hot category list, multiple categories separated by comma, empty for all
        keyword (str, optional): Hot search keyword, supports fuzzy search

    Returns:
        Dict: Same city hot list data, containing pagination info and hot list:
        {
            "page": {
                "page": int,        # Current page
                "page_size": int,   # Items per page
                "total": int        # Total records
            },
            "objs": [              # Hot list
                {
                    "rank": int,                    # Current rank
                    "rank_diff": float,             # Rank change
                    "sentence": str,                # Hot content
                    "sentence_id": int,             # Hot ID
                    "create_at": int,               # Creation timestamp
                    "hot_score": int,               # Hot score
                    "video_count": int,             # Related video count
                    "sentence_tag": int,            # Category tag ID
                    "city_code": int,               # City code
                    "city_name": str,               # City name
                    "sentence_tag_name": str,       # Category tag name
                    "trends": [                     # Hot trend data
                        {
                            "datetime": str,        # Time point
                            "hot_score": int        # Hot score at this time
                        }
                    ]
                }
            ],
            "last_update_time": str                 # Data last update time
        }
    """
    data = {
        "page": str(page),
        "page_size": str(page_size),
        "order": order,
        "city_code": city_code,
        "sentence_tag": sentence_tag,
        "keyword": keyword
    }
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_city_list", method="GET", params=data)
    return result.get("data", {}).get("data", {})


async def fetch_hot_challenge_list(page=1, page_size=50, keyword=""):
    """
    Get hot challenge list

    Parameters:
        page (int): Page number, starting from 1
        page_size (int): Items per page, default 50
        keyword (str): Search keyword, optional

    Returns:
        dict: Dictionary containing the following fields
            - code (int): Status code, 0 means success
            - data (dict): Data object
                - list (list): Challenge list, each challenge item contains:
                    - index (int): Index
                    - SnapshotSubType (str): Snapshot subtype, e.g.: "hotspot_challenge"
                    - SnapshotType (int): Snapshot type, e.g.: 2
                    - SnapshotID (int): Snapshot ID
                    - trends (list): Hot trend data array, each trend data point contains:
                        - datetime (str): Time point, format: YYYYMMDDHHMMSS
                        - hot_score (int): Hot score at this time point
                    - city_name (str): City name
                    - sentence_tag_name (str): Category tag name
                    - first_item_cover_url (str): Cover URL
                    - is_favorite (bool): Whether favorited
                    - item_list (list): Item list
                    - item_list_i64 (list): Item list (64-bit integers)
                    - recommend_type (any): Recommend type
                    - related_event (any): Related event
                    - allow_publish (bool): Whether publishing is allowed
                    - label_name (str): Label name
                    - label (int): Label value
                - total (int): Total records
                - page (int): Current page
                - page_size (int): Page size
            - last_update_time (str): Last update time, format: YYYYMMDDHHMMSS
    """
    data = {
        "page": str(page),
        "page_size": str(page_size),
        "keyword": keyword
    }
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_challenge_list", method="GET", params=data)
    return result.get("data", {}).get("data", {})


async def fetch_hot_total_list(page=1, page_size=50, type="snapshot", snapshot_time="",
                               start_date="", end_date="", sentence_tag="", keyword=""):
    """
    Get hot total list

    Purpose:
        Get Douyin platform's hot total list data, supports viewing by time point or time range.

    Parameters:
        page (int): Page number, starting from 1
        page_size (int): Items per page, default 50
        type (str): Snapshot type
            - "snapshot": View by time point (default)
            - "range": View by time range
        snapshot_time (str): Snapshot time, format: yyyyMMddHHmmss, only valid when type="snapshot"
        start_date (str): Snapshot start time, format: yyyyMMdd, only valid when type="range"
        end_date (str): Snapshot end time, format: yyyyMMdd, only valid when type="range"
        sentence_tag (str): Hot category tag, get from hot category list, multiple categories separated by comma, empty for all
        keyword (str): Hot search keyword, supports fuzzy search

    Returns:
        dict: Dictionary containing the following fields
            - page (dict): Pagination info
                - page (int): Current page
                - page_size (int): Page size
                - total (int): Total records
            - objs (list): Hot list, each hot item contains:
                - rank (int): Current rank
                - sentence (str): Hot content
                - sentence_id (int): Hot ID
                - create_at (int): Creation timestamp
                - hot_score (int): Hot score
                - video_count (int): Related video count
                - sentence_tag (int): Category tag ID
                - city_code (int): City code
                - trends (list): Hot trend data array, each trend data point contains:
                    - datetime (str): Time point, format: yyyy-MM-dd or yyyy-MM-dd HH
                    - hot_score (int): Hot score at this time point
                - index (int): Index
                - SnapshotSubType (str): Snapshot subtype
                - city_name (str): City name
                - sentence_tag_name (str): Category tag name
                - SnapshotType (int): Snapshot type
                - SnapshotID (int): Snapshot ID
                - first_item_cover_url (str): Cover URL
                - is_favorite (bool): Whether favorited
                - item_list (any): Item list
                - item_list_i64 (any): Item list (64-bit integers)
                - recommend_type (any): Recommend type
                - related_event (any): Related event
                - allow_publish (bool): Whether publishing is allowed
                - label_name (str): Label name
                - label (int): Label value
            - last_update_time (str): Last update time
    """
    data = {
        "page": page,
        "page_size": page_size,
        "type": type,
        "snapshot_time": snapshot_time,
        "start_date": start_date,
        "end_date": end_date,
        "sentence_tag": sentence_tag,
        "keyword": keyword
    }
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_list", method="GET", params=data)
    return result.get("data", {}).get("data", {})


async def fetch_hot_calendar_list(city_code: str = "", category_code: str = "",
                                  start_date: int = 0, end_date: int = 0) -> Dict:
    """
    Get activity calendar

    Purpose:
        Get activity calendar data within specified time range, optionally filter by city and category.
        Note: All parameters are optional, if no parameters provided, will return all activity calendar data.

    Parameters:
        city_code (str, optional): City code, get from city list, empty string means all cities
        category_code (str, optional): Hot category code, get from hot category list, empty string means all categories
        start_date (int, optional): Start timestamp, 10-digit timestamp format, 0 means no start time limit
        end_date (int, optional): End timestamp, 10-digit timestamp format, 0 means no end time limit

    Returns:
        Dict: Dictionary containing the following fields
            - event_list (List[Dict]): Activity list, each activity contains:
                - id (int): Activity ID
                - parent_id (int): Parent activity ID
                - hot_title (str): Activity title
                - start_date (int): Start timestamp
                - end_date (int): End timestamp
                - level_code (int): Activity level
                - category_name (str): Category name, such as "Food", "Travel", "Topic Interaction", etc.
                - city_name (str): City name
                - event_ids (List[int]): Related activity ID list
                - cover_url (str): Cover image URL
                - event_status (int): Activity status, -1 means ended, 0 means ongoing, 1 means not started
                - publish_cnt (int): Publish count
                - is_favorite (int): Whether favorited
                - tags (List): Tag list
                - sentence_id (int): Related sentence ID
                - sentence_type (int): Sentence type
                - sentence_rank (int): Sentence rank
                - sentence (str): Sentence content
                - timeline (any): Timeline data
                - related_topics (str): Related topics
            - topic_list (List[Dict]): Topic list, each topic contains:
                - id (int): Topic ID
                - parent_id (int): Parent topic ID
                - hot_title (str): Topic title
                - start_date (int): Start timestamp
                - end_date (int): End timestamp
                - level_code (int): Topic level
                - event_ids (List[int]): Related activity ID list
                - event_status (int): Topic status
    """
    data = {
        "city_code": city_code,
        "category_code": category_code,
        "start_date": start_date,
        "end_date": end_date
    }
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_calendar_list", method="POST", data=data)
    return result.get("data", {}).get("data", {})


async def fetch_hot_calendar_detail(calendar_id: int) -> Dict:
    """
    Get activity calendar detail

    Purpose:
        Get detailed calendar information for specified activity ID.

    Parameters:
        calendar_id (int): Activity ID, get from activity calendar list

    Returns:
        Dict: Activity detail data, containing the following fields:
            - id (int): Activity ID
            - parent_id (int): Parent activity ID
            - hot_title (str): Activity title
            - start_date (int): Start timestamp
            - end_date (int): End timestamp
            - level_code (int): Activity level
            - category_name (str): Category name, such as "Food"
            - city_name (str): City name
            - event_ids (List[int]): Related activity ID list
            - cover_url (str): Cover image URL
            - event_status (int): Activity status
            - publish_cnt (int): Publish count
            - is_favorite (int): Whether favorited
            - tags (List): Tag list
            - sentence_id (int): Related sentence ID
            - sentence_type (int): Sentence type
            - sentence_rank (int): Sentence rank
            - sentence (str): Sentence content
            - timeline (List[Dict]): Timeline data
            - publish_start_time (str): Activity publish start time, format: YYYY-MM-DD HH:mm:ss
            - publish_end_time (str): Activity publish end time, format: YYYY-MM-DD HH:mm:ss
            - activity_desc (str): Activity description
            - related_topics (List[str]): Related topic list
            - challenge_info (List[Dict]): Challenge info list
                - id (str): Challenge ID
                - name (str): Challenge name
            - activity_reward (str): Activity reward
            - example_videos (List): Example video list
    """
    params = {
        "calendar_id": calendar_id
    }
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_calendar_detail", method="GET", params=params)
    return result.get("data", {}).get("data", {})


async def fetch_hot_user_portrait_list(aweme_id: str, option: int) -> List[Dict]:
    """
    Get work like audience portrait

    Purpose:
        Get like audience portrait data for specified work, supports multiple portrait dimension analysis.

    Parameters:
        aweme_id (str): Work ID
        option (int): Portrait option, options:
            1: Phone price distribution
            2: Gender distribution
            3: Age distribution
            4: Region distribution - province
            5: Region distribution - city
            6: City level
            7: Phone brand distribution

    Returns:
        List[Dict]: Audience portrait data list, each data item contains:
            - name (str): Category name
            - value (int): Value
            - ratio (float): Ratio

    Note:
        This API is no longer available
    """
    data = {
        "aweme_id": aweme_id,
        "option": option
    }
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_user_portrait_list", method="GET", params=data)
    return result.get("data", {}).get("data", [])


async def fetch_hot_comment_word_list(aweme_id: str) -> List[Dict]:
    """
    Get work comment analysis - word cloud weight

    Args:
        aweme_id: Work ID

    Returns:
        List[Dict]: Word cloud data list, each word cloud item contains:
            {
                "word_seg": str,    # Word segmentation result
                "value": int,       # Occurrence count
                "related_comment": str  # Related comment
            }
    """
    params = {
        "aweme_id": aweme_id
    }
    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_comment_word_list", method="GET", params=params)

    # Preprocess return data
    if result.get("code") == 200 and result.get("data", {}).get("code") == 0:
        return result["data"]["data"]
    return []


async def fetch_hot_item_trends_list(aweme_id: str, option: int, date_window: int) -> List[Dict]:
    """
    Get work data trends

    Purpose:
        Get data trends for specified work, including like count, share count, comment count and other metrics, supports viewing by hour or by day.

    Args:
        aweme_id (str): Work ID
        option (int): Data option
            - 7: Like count
            - 8: Share count
            - 9: Comment count
        date_window (int): Time window
            - 1: By hour
            - 2: By day

    Returns:
        List[Dict]: The data trend list for a specific video, with count and time point for each data point
    """
    data = {
        "aweme_id": aweme_id,
        "option": option,
        "date_window": date_window
    }

    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_item_trends_list", method="GET", params=data)
    return result.get("data", {}).get("data", [])


# Account related interfaces
async def fetch_hot_account_list(date_window: int = 24, page_num: int = 1, page_size: int = 20,
                                 query_tag: Optional[Dict] = None) -> List[Dict]:
    """
    Get hot accounts

    Purpose:
        Get hot Douyin accounts within specified time window, supports filtering by vertical category tags.

    Args:
        date_window (int, optional): Time window, unit hours, default 24 hours
        page_num (int, optional): Page number, default 1
        page_size (int, optional): Items per page, default 20
        query_tag (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
                "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all

    Returns:
        List[Dict]: Hot account list, each account contains:
        {
            "monitor_id": int,          # Monitor ID
            "user_id": str,             # User ID
            "nick_name": str,           # Nickname
            "avatar_url": str,          # Avatar URL
            "fans_cnt": int,            # Fans count
            "like_cnt": int,            # Like count
            "publish_cnt": int,         # Publish count
            "new_like_cnt": int,        # New like count
            "new_fans_cnt": int,        # New fans count
            "second_tag_name": str,     # Second-level tag name
            "monitor_status": int,      # Monitor status
            "target_type": int,         # Target type
            "target_cnt": int,          # Target count
            "monitor_period": int,      # Monitor period
            "notice_type": int,         # Notice type
            "notice_hour": int,         # Notice hour
            "new_item_monitor": int,    # New item monitor
            "new_item_target_type": int,# New item target type
            "new_item_target_cnt": int, # New item target count
            "fans_trends": List[Dict],  # Fans trend data, each data point contains:
                {
                    "DateTime": str,    # Date time
                    "Value": int        # Fans change value
                }
            "fans_incr_rate": float,    # Fans growth rate
            "nexus_id": int,            # Related ID
            "group_id": int,            # Group ID
            "group_name": str,          # Group name
            "sec_uid": str,             # Secure user ID
            "signature": str,           # Signature
            "is_verified": bool,        # Whether verified
            "verify_info": str,         # Verify info
            "total_play_cnt": int,      # Total play count
            "total_share_cnt": int,     # Total share count
            "total_comment_cnt": int,   # Total comment count
            "new_play_cnt": int,        # New play count
            "new_share_cnt": int,       # New share count
            "new_comment_cnt": int,     # New comment count
            "first_tag_name": str,      # First-level tag name
            "third_tag_name": str,      # Third-level tag name
            "city_name": str,           # City name
            "province_name": str,       # Province name
            "age_range": str,           # Age range
            "gender": str,              # Gender
            "device_type": str,         # Device type
            "device_price": str,        # Device price
            "device_brand": str,        # Device brand
            "fans_gender_ratio": Dict,  # Fans gender ratio
                {
                    "male": float,      # Male ratio
                    "female": float     # Female ratio
                }
            "fans_age_ratio": Dict,     # Fans age ratio
                {
                    "age_range": str,   # Age range
                    "ratio": float      # Ratio
                }
            "fans_city_ratio": Dict,    # Fans city ratio
                {
                    "city_name": str,   # City name
                    "ratio": float      # Ratio
                }
            "fans_province_ratio": Dict,# Fans province ratio
                {
                    "province_name": str,# Province name
                    "ratio": float      # Ratio
                }
            "fans_device_ratio": Dict,  # Fans device ratio
                {
                    "device_type": str, # Device type
                    "ratio": float      # Ratio
                }
            "fans_price_ratio": Dict,   # Fans device price ratio
                {
                    "price_range": str, # Price range
                    "ratio": float      # Ratio
                }
            "fans_brand_ratio": Dict,   # Fans device brand ratio
                {
                    "brand_name": str,  # Brand name
                    "ratio": float      # Ratio
                }
        }
    """
    data = {
        "date_window": date_window,
        "page_num": page_num,
        "page_size": page_size
    }

    if query_tag:
        data["query_tag"] = query_tag

    result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_account_list", method="POST", data=data)
    return result.get("data", {}).get("data", [])


async def fetch_hot_account_search_list(keyword: str = "", max_pages: int = 1) -> List[Dict]:
    """
    Get search username or Douyin ID

    Purpose:
        Search Douyin users by keyword, supports username and Douyin ID search.
        Automatically handles pagination, returns all search results.

    Args:
        keyword (str, optional): Search username or Douyin ID, default empty string
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: User list, each user contains:
        {
            "user_id": str,           # User ID
            "nick_name": str,         # Nickname
            "avatar_url": str,        # Avatar URL
            "fans_cnt": int,          # Fans count
            "like_cnt": int,          # Like count
            "publish_cnt": int,       # Publish count
            "signature": str,         # Signature
            "is_verified": bool,      # Whether verified
            "verify_info": str,       # Verify info
            "sec_uid": str           # Secure user ID
        }
    """
    all_users = []
    cursor = "0"

    for _ in range(max_pages):
        params = {
            "keyword": keyword,
            "cursor": cursor
        }
        result = await _make_request(BASE_URL_BILLBOARD,"fetch_hot_account_search_list", method="GET", params=params)

        if "error" in result:
            break

        data = result.get("data", {}).get("data", {})
        user_list = data.get("user_list", [])
        all_users.extend(user_list)

        cursor = data.get("cursor", "0")
        if not data.get("has_more", False):
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_users


async def fetch_hot_account_trends_list(sec_uid: str, option: int, date_window: int) -> List[Dict]:
    """
    Get account fans data trends

    Purpose:
        Get fans data trends for specified account, including new like count, new item count, new comment count, new share count and other metrics.

    Args:
        sec_uid (str): User sec_id
        option (int): Data option
            - 2: New like count
            - 3: New item count
            - 4: New comment count
            - 5: New share count
        date_window (int): Time window
            - 1: By hour
            - 2: By day

    Returns:
        List[Dict]: Account fans data trends list, each trend data point contains:
        [
            {
                "date": str,    # Time point, format: YYYY-MM-DD HH:MM:SS
                "value": str    # Corresponding metric value
            },
            ...
        ]
    """
    params = {
        "sec_uid": sec_uid,
        "option": option,
        "date_window": date_window
    }
    result = await _make_request(BASE_URL_BILLBOARD,"fetch_hot_account_trends_list", method="GET", params=params)
    return result.get("data", {}).get("data", [])


async def fetch_hot_account_item_analysis_list(sec_uid: str, day: int = 7) -> List[Dict]:
    """
    Get account item analysis

    Args:
        sec_uid (str): User sec_id
        day (int, optional): Analysis days, default 7 days

    Returns:
        Dict: Account item analysis data, containing the following fields:
            - UserID (int): User ID
            - avg_aweme_count (float): Average publish count
            - avg_comment_count (float): Average comment count
            - avg_share_count (float): Average share count
            - avg_follower_count (float): Average fans growth count
            - avg_like_count (float): Average like count
            - avg_aweme_count_c (float): Average publish count chain ratio
            - avg_comment_count_c (float): Average comment count chain ratio
            - avg_share_count_c (float): Average share count chain ratio
            - avg_follower_count_c (float): Average fans growth count chain ratio
            - avg_like_count_c (float): Average like count chain ratio
            - percentile_aweme_count (int): Publish count percentile
            - percentile_comment_count (int): Comment count percentile
            - percentile_share_count (int): Share count percentile
            - percentile_follower_count (int): Fans growth count percentile
            - percentile_like_count (int): Like count percentile
            - percentile_aweme_count_c (float): Publish count chain ratio percentile
            - percentile_comment_count_c (float): Comment count chain ratio percentile
            - percentile_share_count_c (float): Share count chain ratio percentile
            - percentile_follower_count_c (float): Fans growth count chain ratio percentile
            - percentile_like_count_c (float): Like count chain ratio percentile
            - BaseResp (object): Base response info
    """
    params = {
        "sec_uid": sec_uid,
        "day": day
    }
    result = await _make_request(BASE_URL_BILLBOARD,"fetch_hot_account_item_analysis_list", method="GET", params=params)
    return result.get("data", {}).get("data", [])


async def fetch_hot_account_fans_portrait_list(sec_uid: str, option: str = "2") -> Dict:
    """
    Get fans portrait

    Args:
        sec_uid (str): User sec_id
        option (str, optional): Portrait option, default "2" means gender distribution
            - "2": Gender distribution
            - "3": Age distribution
            - "4": Region distribution - province
            - "5": Region distribution - city
            - "7": Phone brand distribution

    Returns:
        Dict: Fans portrait data, containing the following structure:
            {
                "user_id": str,                # User ID
                "option": str,                 # Query option
                "portrait": {                  # Portrait data
                    "portrait_data": [         # Portrait data list
                        {
                            "value": float,    # Value (ratio)
                            "name": str        # Category name
                        },
                        ...
                    ],
                    "key": str                 # Main category
                },
                "portrait_tgi": {              # TGI index data (Target Group Index)
                    "portrait_data": [         # TGI data list
                        {
                            "value": float,    # TGI value
                            "name": str        # Category name
                        },
                        ...
                    ],
                    "key": str                 # Main category
                }
            }
    """
    params = {
        "sec_uid": sec_uid,
        "option": option
    }
    result = await _make_request(BASE_URL_BILLBOARD,"fetch_hot_account_fans_portrait_list", method="GET", params=params)
    return result.get("data", {})


async def fetch_hot_account_fans_interest_account_list(sec_uid: str) -> List[Dict]:
    """
    Get fans common followers 20 users

    Args:
        sec_uid (str): User sec_id

    Returns:
        List[Dict]: Fans common followers data list, each user contains:
            - monitor_id (int): Monitor ID
            - user_id (str): User ID
            - nick_name (str): Nickname
            - avatar_url (str): Avatar URL
            - fans_cnt (int): Fans count
            - like_cnt (int): Like count
            - publish_cnt (int): Publish count
            - new_like_cnt (int): New like count
            - new_fans_cnt (int): New fans count
            - second_tag_name (str): Second-level tag name
            - monitor_status (int): Monitor status
            - target_type (int): Target type
            - target_cnt (int): Target count
            - monitor_period (int): Monitor period
            - notice_type (int): Notice type
            - notice_hour (int): Notice hour
            - new_item_monitor (int): New item monitor
            - new_item_target_type (int): New item target type
            - new_item_target_cnt (int): New item target count
            - fans_trends (List[Dict]): Fans trend data, each data point contains:
                {
                    "DateTime": str,    # Date time, format: YYYY-MM-DD
                    "Value": int        # Fans change value
                }
            - fans_incr_rate (float): Fans growth rate
            - nexus_id (int): Related ID
            - group_id (int): Group ID
            - group_name (str): Group name
    """
    params = {
        "sec_uid": sec_uid
    }
    result = await _make_request(BASE_URL_BILLBOARD,"fetch_hot_account_fans_interest_account_list", method="GET", params=params)
    return result.get("data", {}).get("data", [])


async def fetch_hot_account_fans_interest_topic_list(sec_uid: str) -> List[Dict]:
    """
    Get fans interested in topics in the past 3 days 10 topics

    Args:
        sec_uid (str): User sec_id

    Returns:
        List[Dict]: Fans interest topic data list, each topic contains:
            - challenge_base_info (Dict): Topic basic information
                - challenge_id (str): Topic ID
                - challenge_name (str): Topic name
                - play_cnt (int): Total video playback count of topic
                - publish_cnt (int): Number of videos published under topic
                - cover_url (str): Topic cover URL
                - avg_play_cnt (int): Average playback count
                - create_time (int): Creation timestamp
                - challenge_type (int): Topic type
                - fancy_qrcode (str): Topic QR code URL
            - challenge_data (Dict): Topic data statistics
                - challenge_id (int): Topic ID
                - hot_score (int): Hot score
                - like_cnt (int): Like count
                - comment_cnt (int): Comment count
                - play_cnt (int): Playback count
                - publish_cnt (int): Publish count
                - plav_avg (float): Average data
            - trends (List[Dict]): Hot trend data, each data point contains:
                - datetime (int): Timestamp
                - value (int): Hot score at this time point
    """
    params = {
        "sec_uid": sec_uid
    }
    result = await _make_request(BASE_URL_BILLBOARD,"fetch_hot_account_fans_interest_topic_list", method="GET", params=params)
    return result.get("data", {}).get("data", [])


async def fetch_hot_account_fans_interest_search_list(sec_uid: str) -> List[Dict]:
    """
    Get fans' search terms in the past 3 days

    Args:
        sec_uid (str): User sec_id

    Returns:
        List[Dict]: Fans search term data list, each search term contains:
            - word (str): Search term
            - hot_score (int): Hot score
    """
    params = {
        "sec_uid": sec_uid
    }
    result = await _make_request(BASE_URL_BILLBOARD,"fetch_hot_account_fans_interest_search_list", method="GET", params=params)
    return result.get("data", {}).get("data", [])


# Total list related interfaces
async def fetch_hot_total_video_list(page: int = 1, page_size: int = 10, date_window: int = 1,
                                     tags: Optional[Dict] = None, max_pages: int = 1) -> List[Dict]:
    """
    Get video list

    Purpose:
        Get video list data within specified time window, supports filtering by vertical category tags.

    Args:
        page (int, optional): Starting page number, default 1
        page_size (int, optional): Items per page, default 10
        date_window (int, optional): Time window
            - 1: By hour
            - 2: By day
        tags (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
                "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: Video list data list, each video contains:
            - item_id (str): Video ID
            - item_title (str): Video title
            - item_cover_url (str): Video cover URL
            - item_duration (int): Video duration (milliseconds)
            - item_url (str): Video playback address
            - nick_name (str): Author nickname
            - avatar_url (str): Author avatar URL
            - fans_cnt (int): Author fans count
            - play_cnt (int): Playback count
            - like_cnt (int): Like count
            - follow_cnt (int): New follow count
            - follow_rate (float): Follow conversion rate
            - like_rate (float): Like rate
            - publish_time (int): Publish timestamp
            - score (int): Hot score
            - media_type (int): Media type
            - favorite_id (int): Favorite ID
            - is_favorite (bool): Whether favorited
            - image_cnt (int): Number of images (if it's a text and image work)
    """
    all_videos = []

    for current_page in range(page, page + max_pages):
        data = {
            "page": current_page,
            "page_size": page_size,
            "date_window": date_window
        }

        if tags:
            data["tags"] = tags

        result = await _make_request(BASE_URL_BILLBOARD,"fetch_hot_total_video_list", method="POST", data=data)
        videos = result.get("data", {}).get("data", {}).get("objs", [])

        if not videos:
            break

        all_videos.extend(videos)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_hot_total_low_fan_list(page: int = 1, page_size: int = 10, date_window: int = 1,
                                       tags: Optional[Dict] = None, max_pages: int = 1) -> List[Dict]:
    """
    Get low-fan hit list

    Purpose:
        Get low-fan hit video list data within specified time window, supports filtering by vertical category tags.

    Args:
        page (int, optional): Starting page number, default 1
        page_size (int, optional): Items per page, default 10
        date_window (int, optional): Time window
            - 1: By hour
            - 2: By day
        tags (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
                "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: Low-fan hit video list, each video contains:
            - item_id (str): Video ID
            - item_title (str): Video title
            - item_cover_url (str): Video cover URL
            - item_duration (int): Video duration (milliseconds)
            - item_url (str): Video playback address
            - nick_name (str): Author nickname
            - avatar_url (str): Author avatar URL
            - fans_cnt (int): Author fans count
            - play_cnt (int): Playback count
            - like_cnt (int): Like count
            - follow_cnt (int): New follow count
            - follow_rate (float): Follow conversion rate
            - like_rate (float): Like rate
            - publish_time (int): Publish timestamp
            - score (int): Hot score
            - media_type (int): Media type
            - is_favorite (bool): Whether favorited
            - image_cnt (int): Number of images (if it's a text and image work)
    """
    all_videos = []

    for current_page in range(page, page + max_pages):
        data = {
            "page": current_page,
            "page_size": page_size,
            "date_window": date_window
        }

        if tags:
            data["tags"] = tags

        result = await _make_request(BASE_URL_BILLBOARD,"fetch_hot_total_low_fan_list", method="POST", data=data)
        videos = result.get("data", {}).get("data", {}).get("objs", [])

        if not videos:
            break

        all_videos.extend(videos)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_hot_total_high_play_list(page: int = 1, page_size: int = 10, date_window: int = 1,
                                         tags: Optional[Dict] = None, max_pages: int = 1) -> List[Dict]:
    """
    Get high-completion rate list

    Purpose:
        Get high-completion rate video list data within specified time window, supports filtering by vertical category tags.

    Args:
        page (int, optional): Starting page number, default 1
        page_size (int, optional): Items per page, default 10
        date_window (int, optional): Time window
            - 1: By hour
            - 2: By day
        tags (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
                "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: High-completion rate video list, each video contains:
            - item_id (str): Video ID
            - item_title (str): Video title
            - item_cover_url (str): Video cover URL
            - item_duration (int): Video duration (milliseconds)
            - item_url (str): Video playback address
            - nick_name (str): Author nickname
            - avatar_url (str): Author avatar URL
            - fans_cnt (int): Author fans count
            - play_cnt (int): Playback count
            - like_cnt (int): Like count
            - follow_cnt (int): New follow count
            - follow_rate (float): Follow conversion rate
            - like_rate (float): Like rate
            - publish_time (int): Publish timestamp
            - score (int): Hot score
            - media_type (int): Media type
            - favorite_id (int): Favorite ID
            - is_favorite (bool): Whether favorited
            - image_cnt (int): Number of images (if it's a text and image work)
    """
    all_videos = []
    current_page = page

    while current_page < page + max_pages:
        data = {
            "page": current_page,
            "page_size": page_size,
            "date_window": date_window
        }

        if tags:
            data["tags"] = json.dumps(tags)

        response = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_high_play_list", method="POST", data=data)

        if not response or "data" not in response:
            break

        data = response["data"]
        if not data or "code" != 0 or "data" not in data:
            break

        video_data = data["data"]
        if not video_data or "objs" not in video_data:
            break

        all_videos.extend(video_data["objs"])
        current_page += 1

        if current_page >= page + max_pages:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_hot_total_high_like_list(page: int = 1, page_size: int = 10, date_window: int = 1,
                                         tags: Optional[Dict] = None, max_pages: int = 1) -> List[Dict]:
    """
    Get high-like rate list

    Purpose:
        Get high-like rate video list data within specified time window, supports filtering by vertical category tags.
        This interface supports paging query, and the maximum number of pages can be specified through the max_pages parameter.

    Args:
        page (int, optional): Starting page number, starting from 1, default 1
        page_size (int, optional): Items per page, default 10
        date_window (int, optional): Time window
            - 1: By hour
            - 2: By day
        tags (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
                "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: High-like rate video list, each video contains:
        {
            "item_id": str,             # Video ID
            "item_title": str,          # Video title
            "item_cover_url": str,      # Video cover URL
            "item_duration": int,       # Video duration (milliseconds)
            "nick_name": str,           # Author nickname
            "avatar_url": str,          # Author avatar URL
            "fans_cnt": int,            # Author fans count
            "play_cnt": int,            # Playback count
            "publish_time": int,        # Publish timestamp
            "score": int,               # Hot score
            "item_url": str,            # Video playback address
            "like_cnt": int,            # Like count
            "follow_cnt": int,          # New follow count
            "follow_rate": float,       # Follow conversion rate (New follow count / Playback count)
            "like_rate": float,         # Like rate (Like count / Playback count)
            "media_type": int,          # Media type, 4 represents video, 2 represents text and image
            "favorite_id": int,         # Favorite ID
            "is_favorite": bool,        # Whether favorited
            "image_cnt": int            # Number of images (if it's a text and image work)
        }

    """
    all_videos = []
    current_page = page

    for _ in range(max_pages):
        data = {
            "page": str(current_page),
            "page_size": str(page_size),
            "date_window": str(date_window)
        }

        if tags:
            data["tags"] = json.dumps(tags)

        response = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_high_like_list", method="POST", data=data)

        # Use a more lenient response handling
        if "error" in response:
            break

        api_data = response.get("data", {})
        video_data = api_data.get("data", {})
        videos = video_data.get("objs", [])

        all_videos.extend(videos)

        # Check if there are more pages
        page_info = video_data.get("page", {})
        total_pages = (page_info.get("total", 0) + page_size - 1) // page_size
        if current_page >= total_pages:
            break

        current_page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_hot_total_high_fan_list(page: int = 1, page_size: int = 10, date_window: int = 1,
                                        tags: Optional[Dict] = None, max_pages: int = 1) -> List[Dict]:
    """
    Get high-growth rate list

    Purpose:
        Get high-growth rate video list data within specified time window, supports filtering by vertical category tags.

    Args:
        page (int, optional): Page number, starting from 1, default 1
        page_size (int, optional): Items per page, range 1-50, default 10
        date_window (int, optional): Time window
            - 1: By hour
            - 2: By day
        tags (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
        "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: High-growth rate video list, each video contains:
        {
            "item_id": str,             # Video ID
            "item_title": str,          # Video title
            "item_cover_url": str,      # Video cover URL
            "item_duration": int,       # Video duration (milliseconds)
            "nick_name": str,           # Author nickname
            "avatar_url": str,          # Author avatar URL
            "fans_cnt": int,            # Author fans count
            "play_cnt": int,            # Playback count
            "publish_time": int,        # Publish timestamp
            "score": int,               # Hot score
            "item_url": str,            # Video playback address
            "like_cnt": int,            # Like count
            "follow_cnt": int,          # New follow count
            "follow_rate": float,       # Follow conversion rate (New follow count / Playback count)
            "like_rate": float,         # Like rate (Like count / Playback count)
            "media_type": int,          # Media type, 4 represents video, 2 represents text and image
            "favorite_id": int,         # Favorite ID
            "is_favorite": bool,        # Whether favorited
            "image_cnt": int            # Number of images (if it's a text and image work)
        }

    """
    all_items = []
    current_page = page
    for _ in range(max_pages):
        params = {"page": str(current_page), "page_size": str(page_size), "date_window": str(date_window)}
        if tags: params["tags"] = json.dumps(tags)
        resp = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_high_fan_list", method="POST", data=params)
        if resp.get("code") != 200 or resp.get("data", {}).get("code") != 0: break
        objs = resp["data"]["data"].get("objs", [])
        if not objs: break
        all_items.extend(objs)
        current_page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)
    return all_items


async def fetch_hot_total_topic_list(page: int = 1, page_size: int = 10, date_window: int = 1,
                                     tags: Optional[Dict] = None, max_pages: int = 1) -> List[Dict]:
    """
    Get topic list

    Purpose:
        Get hot topic list data within specified time window, supports filtering by vertical category tags.

    Args:
        page (int, optional): Page number, starting from 1, default 1
        page_size (int, optional): Items per page, range 1-50, default 10
        date_window (int, optional): Time window
            - 1: By hour
            - 2: By day
        tags (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
                "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: Hot topic list, each topic contains:
        {
            "challenge_id": str,         # Topic ID
            "challenge_name": str,       # Topic name
            "play_cnt": int,             # Total playback count of videos under topic
            "publish_cnt": int,          # Number of videos published under topic
            "cover_url": str,            # Topic cover URL
            "score": int,                # Hot score
            "avg_play_cnt": int,         # Average playback count (play_cnt / publish_cnt)
            "create_time": int,          # Topic creation timestamp
            "origin_trend_str": str,     # Original trend data string
            "trends": List[Dict],        # Hot trend data, each trend data point contains:
                {
                    "date": str,         # Time point, format: YYYY-MM-DD HH
                    "value": int         # Corresponding hot value
                }
            "challenge_type": int,       # Topic type
            "item_list": List,           # Related video list
            "is_favorite": bool,         # Whether favorited
            "is_recommend": bool,        # Whether recommended
            "show_rank": int,            # Display ranking
            "real_rank": int,            # Actual ranking
            "origin_rank": int,          # Original ranking
            "related_event": Any         # Related event
        }

    Note:
        All parameters are optional, if not provided will use default values:
        - page: Default 1
        - page_size: Default 10
        - date_window: Default 1 (By hour)
        - tags: Default None (All categories)
        - max_pages: Default 1 (Only get one page of data)
    """
    all_items = []
    current_page = page
    for _ in range(max_pages):
        params = {"page": str(current_page), "page_size": str(page_size), "date_window": str(date_window)}
        if tags: params["tags"] = json.dumps(tags)
        resp = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_topic_list", method="POST", data=params)
        if resp.get("code") != 200 or resp.get("data", {}).get("code") != 0: break
        objs = resp["data"]["data"].get("objs", [])
        if not objs: break
        all_items.extend(objs)
        current_page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)
    return all_items


async def fetch_hot_total_high_topic_list(page: int = 1, page_size: int = 10, date_window: int = 1,
                                          tags: Optional[Dict] = None, max_pages: int = 1) -> List[Dict]:
    """
    Get hot topic list with rapid growth

    Purpose:
        Get hot topic list with the fastest growth within specified time window, supports filtering by vertical category tags.

    Args:
        page (int, optional): Page number, starting from 1, default 1
        page_size (int, optional): Items per page, range 1-50, default 10
        date_window (int, optional): Time window
            - 1: By hour
            - 2: By day
        tags (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
                "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: Hot topic list with rapid growth, each topic contains:
        {
            "challenge_id": str,           # Topic ID
            "challenge_name": str,         # Topic name
            "challenge_desc": str,         # Topic description
            "cover_url": str,              # Topic cover URL
            "user_count": int,             # Number of users participating
            "view_count": int,             # View count
            "score": int,                  # Hot score
            "rank": int,                   # Current ranking
            "rank_diff": float,            # Ranking change
            "trends": List[Dict],          # Hot trend data, each trend data point contains:
                {
                    "datetime": str,       # Time point
                    "hot_score": int       # Hot score
                }
            "video_count": int,            # Number of videos
            "sentence_tag": int,           # Category tag ID
            "sentence_tag_name": str,      # Category tag name
            "is_favorite": bool,           # Whether favorited
            "favorite_id": int,            # Favorite ID
            "SnapshotID": int,             # Snapshot ID
            "SnapshotType": int,           # Snapshot type
            "SnapshotSubType": str         # Snapshot subtype
        }

    Note:
        All parameters are optional, if not provided will use default values:
        - page: Default 1
        - page_size: Default 10
        - date_window: Default 1 (By hour)
        - tags: Default None (All categories)
        - max_pages: Default 1 (Only get one page of data)
    """
    all_items = []
    current_page = page
    for _ in range(max_pages):
        params = {"page": str(current_page), "page_size": str(page_size), "date_window": str(date_window)}
        if tags: params["tags"] = json.dumps(tags)
        resp = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_high_topic_list", method="POST", data=params)
        if resp.get("code") != 200 or resp.get("data", {}).get("code") != 0: break
        objs = resp["data"]["data"].get("objs", [])
        if not objs: break
        all_items.extend(objs)
        current_page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)
    return all_items


async def fetch_hot_total_search_list(page: int = 1, page_size: int = 10, date_window: int = 1,
                                      tags: Optional[Dict] = None, max_pages: int = 1) -> List[Dict]:
    """
    Get search list

    Purpose:
        Get hot search term list data within specified time window, supports filtering by vertical category tags.
        This interface supports paging query, and the maximum number of pages can be specified through the max_pages parameter.

    Args:
        page (int, optional): Page number, starting from 1, default 1
        page_size (int, optional): Items per page, range 1-50, default 10
        date_window (int, optional): Time window
            - 1: By hour
            - 2: By day
        tags (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
                "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: Hot search term list, each search term contains:
        {
            "key_word": str,          # Search keyword
            "search_score": int,      # Search score/index
            "trends": List[Dict]      # Search hot trend data, each data point contains:
                {
                    "date": str,      # Time point, format: "YYYY-MM-DD HH:MM:SS"
                    "value": int      # Hot value at this time point
                }
        }
    """
    all_items = []
    current_page = page
    for _ in range(max_pages):
        params = {
            "page": str(current_page),
            "page_size": str(page_size),
            "date_window": str(date_window)
        }
        if tags:
            params["tags"] = json.dumps(tags)

        resp = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_search_list", method="POST", data=params)

        # Use a more lenient response handling
        if "error" in resp:
            print(f"API request error: {resp['error']}")
            break

        if resp.get("code") != 200:
            print(f"API status code error: {resp.get('code')}")
            break

        api_data = resp.get("data", {})
        if api_data.get("code") != 0:
            print(f"Business status code error: {api_data.get('code')}")
            break

        result_data = api_data.get("data", {})
        search_list = result_data.get("search_list", [])

        if not search_list:
            print("No more data")
            break

        all_items.extend(search_list)
        current_page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)
    return all_items


async def fetch_hot_total_high_search_list(page: int = 1, page_size: int = 10, date_window: int = 1,
                                           tags: Optional[Dict] = None, max_pages: int = 1) -> List[Dict]:
    """
    Get hot search list with rapid growth

    Purpose:
        Get hot search term list with the fastest growth within specified time window, supports filtering by vertical category tags.
        This interface supports paging query, and the maximum number of pages can be specified through the max_pages parameter.

    Args:
        page (int, optional): Page number, starting from 1, default 1
        page_size (int, optional): Items per page, range 1-50, default 10
        date_window (int, optional): Time window
            - 1: By hour
            - 2: By day
        tags (Dict, optional): Sub-level vertical category tags, format as follows:
            {
                "value": "Top-level vertical category tag id",
                "children": [
                    {"value": "Sub-level vertical category tag id"},
                    {"value": "Sub-level vertical category tag id"}
                ]
            }
            None means get all
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: Hot search term list with rapid growth, each search term contains:
        {
            "key_word": str,           # Search keyword
            "search_score": int,       # Search score/hot index
            "trends": List[Dict],      # Search hot trend data, each data point contains:
                {
                    "date": str,       # Time point, format: "YYYY-MM-DD HH:MM:SS"
                    "value": int       # Hot value at this time point
                }
        }

    """
    all_items = []
    current_page = page
    for _ in range(max_pages):
        params = {
            "page": str(current_page),
            "page_size": str(page_size),
            "date_window": str(date_window)
        }
        if tags:
            params["tags"] = json.dumps(tags)

        resp = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_high_search_list", method="POST", data=params)

        # Use a more lenient response handling
        if "error" in resp:
            print(f"API request error: {resp['error']}")
            break

        if resp.get("code") != 200:
            print(f"API status code error: {resp.get('code')}")
            break

        api_data = resp.get("data", {})
        if api_data.get("code") != 0:
            print(f"Business status code error: {api_data.get('code')}")
            break

        result_data = api_data.get("data", {})
        search_list = result_data.get("search_list", [])

        if not search_list:
            print("No more data")
            break

        all_items.extend(search_list)
        current_page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)
    return all_items


async def fetch_hot_total_hot_word_list(page: int = 1, page_size: int = 10, max_pages: int = 1) -> List[Dict]:
    """
    Get all content words

    Purpose:
        Get Douyin platform's hot content vocabulary list, supports paging retrieval.

    Args:
        page (int, optional): Page number, starting from 1, default 1
        page_size (int, optional): Items per page, range 1-50, default 10
        max_pages (int, optional): Maximum pages to get, default 1

    Returns:
        List[Dict]: Content word list, each content word contains:
        {
            "title": str,               # Content word title
            "is_favorite": bool,        # Whether favorited
            "favorite_id": int,         # Favorite ID
            "score": int,               # Hot score
            "rising_ratio": int,        # Rising rate
            "rising_speed": str,        # Rising speed
            "id": str,                  # Content word ID
            "query_day": str,           # Query date, format: YYYYMMDD
            "trends": List[Dict],       # Hot trend data
                {
                    "date": str,        # Date, format: YYYYMMDD
                    "value": float      # Hot value
                }
        }

    Note:
        All parameters are optional, if not provided will use default values:
        - page: Default 1
        - page_size: Default 10
        - max_pages: Default 1 (Only get one page of data)
    """
    all_words = []
    current_page = page

    for _ in range(max_pages):
        params = {
            "page": str(current_page),
            "page_size": str(page_size)
        }

        resp = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_hot_word_list", method="POST", data=params)

        # Use a more lenient response handling
        if "error" in resp:
            print(f"API request error: {resp['error']}")
            break

        if resp.get("code") != 200:
            print(f"API status code error: {resp.get('code')}")
            break

        api_data = resp.get("data", {})
        if api_data.get("code") != 0:
            print(f"Business status code error: {api_data.get('code')}")
            break

        result_data = api_data.get("data", {})
        word_list = result_data.get("word_list", [])

        if not word_list:
            print("No more data")
            break

        all_words.extend(word_list)
        current_page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_words


async def fetch_hot_total_hot_word_detail_list(keyword: Optional[str] = None, word_id: Optional[str] = None,
                                               query_day: Optional[str] = None) -> Dict:
    """
    Get content word details

    Purpose:
        Get detailed information and related data for specified content word.

    Args:
        keyword (Optional[str], optional): Search keyword
        word_id (Optional[str], optional): Content word id
        query_day (Optional[str], optional): Query date, format: YYYYMMDD.

    Returns:
        Dict: Content word details data, possibly empty. The API returns an object instead of a list, and the specific structure depends on the API response.

    Note:
        This API may return an empty object, indicating that no details can be found for the specified content word.

    Warning:
        This interface may have issues, tests show that even with correct parameters provided, it often returns empty data.
        It is recommended to handle errors when using this interface and consider using alternative interfaces.
    """
    if not keyword and not word_id:
        raise ValueError("Must provide either keyword or word_id")

    # If query date is not provided, use current date
    if query_day is None:
        query_day = datetime.datetime.now().strftime("%Y%m%d")

    params = {
        "query_day": query_day
    }

    if keyword:
        params["keyword"] = keyword
    if word_id:
        params["word_id"] = word_id

    try:
        result = await _make_request(BASE_URL_BILLBOARD, "fetch_hot_total_hot_word_detail_list", method="GET", params=params)
        # Return data object, even if it's empty
        return result.get("data", {}).get("data", {})
    except aiohttp.ClientError as e:
        print(f"Request error: {e}")
        return {}


async def save_to_json(data: Any, filename: str) -> None:
    """
    Save data to a JSON file.

    Args:
        data: Data to save
        filename: Output filename
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Data saved to {filename}")


# Example usage
async def main():
    start = time.time()

    # Example of a single operation
    videos = await fetch_video_search_v2(keyword="春节",max_pages=1)
    await save_to_json(videos, "chinese_new_year_videos.json")

    # Example of running multiple operations concurrently
    tasks = [
        fetch_hot_search_list(),
        fetch_user_profile(sec_user_id="MS4wLjABAAAADUbFnxuw3MRvLMPDJXOMS4F_O3-wc_2pR5FdDybwOdQ"),
        fetch_home_feed()
    ]
    results = await asyncio.gather(*tasks)
    hot_searches, user_profile, home_feed = results

    print(f"Total time: {time.time() - start:.2f}s")


# Running the async main function
if __name__ == "__main__":
    asyncio.run(main())