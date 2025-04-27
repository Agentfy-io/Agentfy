import asyncio
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
        base_url: Base URL for the API (app or web or billboard or xingtu)
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


# Video Functions
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


# Comment Functions
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


# Mix (Collection) Functions
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


# Music Functions
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


# Hashtag Functions
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


async def fetch_live_hot_search_list() -> List[Dict]:
    #TODO: need to be fixed
    """
    Fetch Douyin live hot search list.

    Returns:
        List of hot searches
    """
    result = await _make_request(BASE_URL_APP, "fetch_live_hot_search_list")
    return result.get("data", {}).get("word_list", [])


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


# Search Functions
async def fetch_general_search_result(keyword: str, count: int = 10, sort_type: int = 0,
                                      publish_time: int = 0, filter_duration: str = "0", search_range: str = "0",
                                      content_type: str = "0", max_pages: int = 1) -> List[Dict]:
    """
    Perform a general search on Douyin.

    Args:
        keyword: Search keyword
        count: Number of results per page
        sort_type: Sort type (0: comprehensive, 1: most likes, 2: latest)
        publish_time: Publish time filter (0: unlimited, 1: last day, 7: last week, 180: last half year)
        filter_duration: Duration filter (0: unlimited, 0-1: within 1 minute, 1-5: 1-5 minutes, 5-10000: more than 5 minutes)
        search_range: Search range (0: Unlimited 1: Recently viewed 2: Not yet viewed 3: Followed)
        content_type: Content type (0: Unlimited 1: Video 2: Album)
        max_pages: Maximum number of pages to fetch

    Returns:
        Search results
    """
    params = {
        "keyword": keyword,
        "count": count,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "search_range": search_range,
        "content_type": content_type
    }
    offset = 0
    search_id = ""
    all_results = []

    for _ in range(max_pages):
        params["search_id"] = search_id
        params["offset"] = offset
        response = await _make_request(BASE_URL_WEB, "fetch_general_search_result", params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        results = data.get("data", [])
        all_results.extend(results)

        search_id = data.get("extra", {}).get("logid", "")
        cursor = data.get("cursor", 0)
        has_more = data.get("has_more", False)

        if not has_more:
            break

        offset = cursor
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_video_search_result(keyword: str, sort_type: int = 0, publish_time: int = 0,
                                    filter_duration: str = "0", max_pages: int = 1, count: int = 10) -> List[Dict]:
    """
    Search for videos on Douyin with pagination.

    Args:
        keyword: Search keyword
        sort_type: Sort type (0: comprehensive, 1: most likes, 2: latest)
        publish_time: Publish time filter (0: unlimited, 1: last day, 7: last week, 180: last half year)
        filter_duration: Duration filter (0: unlimited, 0-1: within 1 minute, 1-5: 1-5 minutes, 5-10000: more than 5 minutes)
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of videos
    """
    endpoint = "fetch_video_search_result"
    params = {
        "keyword": keyword,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "count": count,
        "offset": 0
    }
    all_videos = []
    search_id = ""

    for _ in range(max_pages):
        if search_id:
            params["search_id"] = search_id

        response = await _make_request(BASE_URL_WEB, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        videos = data.get("data", [])
        all_videos.extend(videos)

        search_id = data.get("extra", {}).get("logid", "")
        cursor = data.get("cursor", 0)
        has_more = data.get("has_more", False)

        if not has_more:
            break

        params["offset"] = cursor
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_user_search_result(keyword: str, cursor: int = 0, fans_filter: str = "", user_type: str = "",
                                   max_pages: int = 1) -> List[Dict]:
    #TODO : this endpoint needs to be fixed or updated
    """
    Search for users on Douyin with pagination.

    Args:
        keyword: Search keyword
        cursor: Cursor for pagination
        fans_filter: Filter by number of fans (0_1k, 1k_1w, 1w_10w, 10w_100w, 100w_)
        user_type: Filter by user type (common_user, enterprise_user, personal_user)
        max_pages: Maximum number of pages to fetch

    Returns:
        List of users
    """
    endpoint = "fetch_user_search_result_v3"
    params = {"keyword": keyword, "cursor": cursor}

    if fans_filter:
        params["douyin_user_fans"] = fans_filter
    if user_type:
        params["douyin_user_type"] = user_type

    all_users = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_WEB, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        users = data.get("user_list", [])
        all_users.extend(users)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        cursor = data.get("cursor", 0)
        params["cursor"] = cursor
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_users


async def fetch_live_search_result(keyword: str, max_pages: int = 1, count: int = 20) -> List[Dict]:
    """
    Search for live streams on Douyin with pagination.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        count: Number of results per page

    Returns:
        List of live streams
    """
    endpoint = "fetch_live_search_result"
    params = {"keyword": keyword, "count": count, "offset": 0}
    all_lives = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_WEB, endpoint, params=params)

        if "error" in response:
            break

        data = response.get("data", {})
        lives = data.get("data", [])
        all_lives.extend(lives)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        params["offset"] = data.get("cursor", 0)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_lives


async def search_challenge(keyword: str, count: int = 20, cookie: str = "", max_pages: int = 1) -> List[Dict]:
    # TODO : it may requires a cookie
    """
    Search for challenges/hashtags on Douyin.

    Args:
        keyword: Search keyword
        count: Number of results per page
        cookie: User cookie for authenticated requests
        max_pages: Maximum number of pages to fetch

    Returns:
        List of challenges
    """
    data = {
        "keyword": keyword,
        "cursor": 0,
        "count": count
    }

    if cookie:
        data["cookie"] = cookie
    all_challenges = []

    for _ in range(max_pages):
        response = await _make_request(BASE_URL_WEB, "fetch_search_challenge", method="POST", data=data)

        if "error" in response:
            break

        data = response.get("data", {})
        challenges = data.get("challenge_list", [])
        all_challenges.extend(challenges)

        has_more = data.get("has_more", False)
        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)
        data["cursor"] = data.get("cursor", 0)

    return all_challenges


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


async def fetch_city_list() -> List[Dict]:
    """
    Fetch Douyin city list.

    Returns:
        List of cities
    """
    result = await _make_request(BASE_URL_WEB, "fetch_city_list")
    return result.get("data", [])


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


# Danmaku (Comment Overlay) Function
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


# Challenge (Hashtag) Posts
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


async def fetch_kol_base_info(kol_id: str, platform_channel: str = "_1") -> Dict:
    #TODO : this endpoint needs to be fixed or updated
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
    return result.get("data", {})


async def fetch_kol_audience_portrait(kol_id: str) -> Dict:
    #TODO : this endpoint needs to be fixed or updated
    """
    Get KOL audience portrait data.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL audience portrait data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_audience_portrait_v1", params={"kolId": kol_id})
    return result.get("data", {})


async def fetch_kol_fans_portrait(kol_id: str) -> Dict:
    """
    Get KOL fans portrait data.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL fans portrait data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_fans_portrait_v1", params={"kolId": kol_id})
    return result.get("data", {})


async def fetch_kol_service_price(kol_id: str, platform_channel: str = "_1") -> Dict:
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
    return result.get("data", {})


async def fetch_kol_data_overview(kol_id: str, type_: str = "_1", range_: str = "_2", flow_type: int = 1) -> Dict:
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
    return result.get("data", {})


async def search_kol(keyword: str, platform_source: str = "_1", page: int = 1) -> List[Dict]:
    """
    Search for KOLs by keyword.

    Args:
        keyword: Search keyword
        platform_source: Platform source (_1: Douyin, _2: Toutiao, _3: Xigua)
        page: Page number (starting from 1)

    Returns:
        List of KOLs
    """
    params = {
        "keyword": keyword,
        "platformSource": platform_source,
        "page": page
    }

    result = await _make_request(BASE_URL_XINGTU, "search_kol_v1", params=params)
    return result.get("data", {}).get("kols", [])


async def fetch_kol_conversion_ability(kol_id: str, range_: str = "_1") -> Dict:
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
    return result.get("data", {})


async def fetch_kol_video_performance(kol_id: str, only_assign: bool = False) -> Dict:
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
        "onlyAssign": str(only_assign).lower()
    }

    result = await _make_request(BASE_URL_XINGTU, "kol_video_performance_v1", params=params)
    return result.get("data", {})


async def fetch_kol_xingtu_index(kol_id: str) -> Dict:
    """
    Get KOL XingTu index data.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL XingTu index data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_xingtu_index_v1", params={"kolId": kol_id})
    return result.get("data", {})


async def fetch_kol_convert_video_display(kol_id: str, detail_type: str = "_1", page: int = 1) -> Dict:
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


async def fetch_kol_link_struct(kol_id: str) -> Dict:
    """
    Get KOL link structure data.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL link structure data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_link_struct_v1", params={"kolId": kol_id})
    return result.get("data", {})


async def fetch_kol_touch_distribution(kol_id: str) -> Dict:
    """
    Get KOL touch distribution data (user sources).

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL touch distribution data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_touch_distribution_v1", params={"kolId": kol_id})
    return result.get("data", {})


async def fetch_kol_cp_info(kol_id: str) -> Dict:
    """
    Get KOL cost-performance analysis data.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL cost-performance analysis data
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_cp_info_v1", params={"kolId": kol_id})
    return result.get("data", {})


async def fetch_kol_rec_videos(kol_id: str) -> Dict:
    """
    Get KOL recommended videos and content performance.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        KOL recommended videos and content performance
    """
    result = await _make_request(BASE_URL_XINGTU, "kol_rec_videos_v1", params={"kolId": kol_id})
    return result.get("data", {})


async def fetch_kol_daily_fans(kol_id: str, start_date: str, end_date: str) -> Dict:
    """
    Get KOL daily fans trend data.

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
    return result.get("data", {})


async def fetch_author_hot_comment_tokens(kol_id: str) -> Dict:
    """
    Get author hot comment tokens analysis.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        Author hot comment tokens analysis
    """
    result = await _make_request(BASE_URL_XINGTU, "author_hot_comment_tokens_v1", params={"kolId": kol_id})
    return result.get("data", {})


async def fetch_author_content_hot_comment_keywords(kol_id: str) -> Dict:
    """
    Get author content hot comment keywords analysis.

    Args:
        kol_id: XingTu KOL ID

    Returns:
        Author content hot comment keywords analysis
    """
    result = await _make_request(BASE_URL_XINGTU, "author_content_hot_comment_keywords_v1",
                                 params={"kolId": kol_id})
    return result.get("data", {})


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
    videos = await fetch_video_search_result(keyword="Chinese New Year", max_pages=2)
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