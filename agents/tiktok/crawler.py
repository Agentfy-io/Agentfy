import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, Union
from urllib.parse import quote
from config import settings

# Constants
API_KEY = settings.tikhub_api_key
APP_BASE_URL = "https://api.tikhub.io/api/v1/tiktok/app/v3"
WEB_BASE_URL = "https://api.tikhub.io/api/v1/tiktok/web"
HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
RATE_LIMIT_DELAY = 1  # Seconds between requests to avoid rate limiting


async def _make_app_request(endpoint: str, params: Optional[Dict] = None) -> Dict:
    """Make an async HTTP request to the TikHub API."""
    url = f"{APP_BASE_URL}/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, params=params) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        print(f"Request error: {e}")
        return {"error": str(e)}


async def _make_web_request(endpoint: str, params: Optional[Dict] = None) -> Dict:
    """Make an async HTTP request to the TikHub API."""
    url = f"{WEB_BASE_URL}/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, params=params) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        print(f"Request error: {e}")
        return {"error": str(e)}


async def url_to_sec_user_id(url: str) -> str:
    """
    Convert a TikTok profile URL to sec_user_id.

    Args:
        url: TikTok profile URL
    """
    result = await _make_web_request("get_sec_user_id", {"url": url})
    return result.get("data", "")


async def url_to_aweme_id(url: str) -> str:
    """
    Convert a TikTok video URL to aweme_id.
    Args:
        url: TikTok video URL
    """
    result = await _make_app_request("get_aweme_id", {"url": url})
    return result.get("data", "")


async def url_to_room_id(url: str) -> str:
    """
    Convert a TikTok live room URL to room_id.

    Args:
        url: TikTok live room URL
    """
    result = await _make_app_request("get_live_room_id", {"live_room_url": url})
    return result.get("data", {}).get("room_id", "")


async def url_to_share_link(url: str) -> str:
    """
    Generate a short link for sharing.

    Args:
        url: Original web URL to be shortened
    """
    result = await _make_app_request("fetch_share_link", {"url": url})
    return result.get("data", {}).get("shorten_url", "")


async def fetch_shop_id_by_share_link(share_link: str) -> str:
    """
    Get TikTok shop ID from a share link.

    Args:
        share_link: TikTok shop share link
    """
    result = await _make_app_request("fetch_shop_id_by_share_link", {"share_link": quote(share_link)})
    return result.get("data", {}).get("shop_id", "")


async def fetch_product_id_by_share_link(share_link: str) -> str:
    """
    Get TikTok product ID from a share link.

    Args:
        share_link: TikTok product share link
    """
    result = await _make_app_request("fetch_product_id_by_share_link", {"share_link": quote(share_link)})
    return result.get("data", {}).get("product_id", "")


async def fetch_one_video(identifier: str, id_type: str = "share_url") -> List[Dict]:
    """
    Fetch a single video by TikTok video ID or share URL.

    Args:
        identifier: TikTok video ID or share URL
        id_type: Type of identifier ('aweme_id' or 'share_url' or 'web_url')
    """
    if id_type == "aweme_id":
        result = await _make_app_request("fetch_one_video_v2", {"aweme_id": identifier})
        return [result.get("data", {})]
    elif id_type == "share_url":
        result = await _make_app_request("fetch_one_video_by_share_url", {"share_url": identifier})
        return result.get("data", {}).get("aweme_list", [])
    elif id_type == "web_url":
        aweme_id = await url_to_aweme_id(identifier)
        result = await _make_app_request("fetch_one_video_v2", {"aweme_id": aweme_id})
        return [result.get("data", {})]
    else:
        return []


async def fetch_user_profile(sec_user_id: Optional[str] = None,
                             user_id: Optional[str] = None,
                             unique_id: Optional[str] = None,
                             url: Optional[str] = None) -> List[Dict]:
    """
    Fetch user profile information.

    Args:
        sec_user_id: User's sec_user_id (highest priority)
        user_id: User's uid (medium priority)
        unique_id: User's username (lowest priority)
        url: User's profile URL (optional, will be converted to sec_user_id)

    Note:
        At least one parameter must be provided.
        Priority: sec_user_id > user_id > unique_id
    """
    params = {}
    if sec_user_id:
        params["sec_user_id"] = sec_user_id
    elif user_id:
        params["user_id"] = user_id
    elif unique_id:
        params["unique_id"] = unique_id
    elif url:
        sec_user_id = await url_to_sec_user_id(url)
        params["sec_user_id"] = sec_user_id
    else:
        return []

    result = await _make_app_request("handler_user_profile", params)
    return [result.get("data", {}).get("user", {})]


async def fetch_user_post_videos(sec_user_id: Optional[str] = None,
                                 unique_id: Optional[str] = None,
                                 url: Optional[str] = None,
                                 max_pages: int = 1,
                                 count: int = 20,
                                 sort_type: int = 0) -> List[Dict]:
    """
    Fetch videos posted by a user with pagination.

    Args:
        sec_user_id: User's sec_user_id (higher priority)
        unique_id: User's username (lower priority)
        url: User's profile URL (optional, will be converted to sec_user_id)
        max_pages: Maximum number of pages to fetch
        count: Number of videos per page
        sort_type: Sort type (0-Latest, 1-Hot)

    Note:
        At least one identifier (sec_user_id or unique_id) must be provided.
    """
    if not sec_user_id and not unique_id:
        return []

    params = {
        "count": count,
        "sort_type": sort_type
    }

    if sec_user_id:
        params["sec_user_id"] = sec_user_id
    elif unique_id:
        params["unique_id"] = unique_id
    elif url:
        sec_user_id = await url_to_sec_user_id(url)
        params["sec_user_id"] = sec_user_id
    else:
        return []

    all_videos = []
    max_cursor = 0  # Start with 0 for the first page

    for _ in range(max_pages):
        params["max_cursor"] = max_cursor

        response = await _make_app_request("fetch_user_post_videos", params)
        if "error" in response:
            break

        videos = response.get("data", {}).get("aweme_list", [])
        all_videos.extend(videos)

        # Get max_cursor for the next page
        max_cursor = response.get("data", {}).get("max_cursor", 0)
        has_more = response.get("data", {}).get("has_more", 0)

        if not has_more or max_cursor == 0:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_user_like_videos(sec_user_id: Optional[str] = None,
                                 url: Optional[str] = None,
                                 max_pages: int = 1,
                                 count: int = 20) -> List[Dict]:
    """
    Fetch videos liked by a user with pagination.

    Args:
        sec_user_id: User's sec_user_id
        url: User's profile URL (optional, will be converted to sec_user_id)
        max_pages: Maximum number of pages to fetch
        count: Number of videos per page
    """
    params = {
        "sec_user_id": sec_user_id,
        "counts": count
    }

    if sec_user_id is None and url:
        sec_user_id = await url_to_sec_user_id(url)
        params["sec_user_id"] = sec_user_id

    all_videos = []
    max_cursor = 0  # Start with 0 for the first page

    for _ in range(max_pages):
        params["max_cursor"] = max_cursor

        response = await _make_app_request("fetch_user_like_videos", params)
        if "error" in response:
            break

        videos = response.get("data", {}).get("aweme_list", [])
        all_videos.extend(videos)

        # Get max_cursor for the next page
        max_cursor = response.get("data", {}).get("max_cursor", 0)
        has_more = response.get("data", {}).get("has_more", 0)

        if not has_more or max_cursor == 0:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_video_comments(aweme_id: Optional[str] = None,
                               url: Optional[str] = None,
                               max_pages: int = 1,
                               count: int = 20) -> List[Dict]:
    """
    Fetch comments on a video with pagination.

    Args:
        aweme_id: TikTok video ID
        url: TikTok video URL (optional, will be converted to aweme_id)
        max_pages: Maximum number of pages to fetch
        count: Number of comments per page
    """
    params = {
        "aweme_id": aweme_id,
        "count": count
    }

    if aweme_id is None and url:
        aweme_id = await url_to_aweme_id(url)
        params["aweme_id"] = aweme_id

    all_comments = []
    cursor = 0  # Start with 0 for the first page

    for _ in range(max_pages):
        params["cursor"] = cursor

        response = await _make_app_request("fetch_video_comments", params)
        if "error" in response:
            break

        comments = response.get("data", {}).get("comments", [])
        all_comments.extend(comments)

        # Get cursor for the next page
        has_more = response.get("data", {}).get("has_more", False)
        cursor = response.get("data", {}).get("cursor", 0)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_comments


async def fetch_video_search_results(keyword: str,
                                     max_pages: int = 1,
                                     count: int = 20,
                                     sort_type: int = 0,
                                     publish_time: int = 0) -> List[Dict]:
    """
    Fetch video search results with pagination.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        count: Number of results per page
        sort_type: Sort type (0-Latest, 1-Hot)
        publish_time: Filter by publish time (0-All time, 1-Last day, 7-Last week,
                     30-Last month, 90-Last 3 months, 180-Last 6 months)
    """
    params = {
        "keyword": keyword,
        "count": count,
        "sort_type": sort_type,
        "publish_time": publish_time
    }

    all_results = []
    offset = 0

    for page in range(max_pages):
        params["offset"] = offset

        response = await _make_app_request("fetch_video_search_result", params)
        if "error" in response:
            break

        videos = response.get("data", {}).get("data", [])
        all_results.extend(videos)

        has_more = response.get("data", {}).get("has_more", False)
        offset = response.get("data", {}).get("cursor", 0)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_user_search_results(keyword: str,
                                    max_pages: int = 1,
                                    count: int = 20,
                                    user_search_follower_count: Optional[str] = None,
                                    user_search_profile_type: Optional[str] = None,
                                    user_search_other_pref: Optional[str] = None) -> List[Dict]:
    """
    Fetch user search results with pagination.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        count: Number of results per page
        user_search_follower_count: Empty-Unlimited, ZERO_TO_ONE_K = 0-1K, ONE_K_TO_TEN_K-1K = 1K-10K, TEN_K_TO_ONE_H_K = 10K-100K, ONE_H_K_PLUS = 100K and above
        user_search_profile_type: Empty-Unlimited, VERIFIED = Verified user
        user_search_other_pref: USERNAME = Sort by username relevance
    """
    params = {
        "keyword": keyword,
        "count": count,
        "user_search_follower_count": user_search_follower_count,
        "user_search_profile_type": user_search_profile_type,
        "user_search_other_pref": user_search_other_pref
    }

    all_results = []
    offset = 0

    for page in range(max_pages):
        params["offset"] = offset

        response = await _make_app_request("fetch_user_search_result", params)
        if "error" in response:
            break

        users = response.get("data", {}).get("user_list", [])
        all_results.extend(users)

        has_more = response.get("data", {}).get("has_more", False)
        offset = response.get("data", {}).get("cursor", 0)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_music_search_results(keyword: str,
                                     max_pages: int = 1,
                                     count: int = 20,) -> List[Dict]:
    """
    Fetch music search results with pagination.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        count: Number of results per page
    """
    params = {
        "keyword": keyword,
        "count": count,
    }

    all_results = []
    offset = 0

    for page in range(max_pages):
        params["offset"] = offset

        response = await _make_app_request("fetch_music_search_result", params)
        if "error" in response:
            break

        music_list = response.get("data", {}).get("music", [])
        all_results.extend(music_list)

        has_more = response.get("data", {}).get("has_more", False)
        offset = response.get("data", {}).get("cursor", 0)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_hashtag_search_results(keyword: str,
                                       max_pages: int = 1,
                                       count: int = 20) -> List[Dict]:
    """
    Fetch hashtag search results with pagination.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        count: Number of results per page
    """
    params = {
        "keyword": keyword,
        "count": count,
    }

    all_results = []
    offset = 0

    for page in range(max_pages):
        params["offset"] = offset

        response = await _make_app_request("fetch_hashtag_search_result", params)
        if "error" in response:
            break

        challenge_list = response.get("data", {}).get("challenge_list", [])
        all_results.extend(challenge_list)

        has_more = response.get("data", {}).get("has_more", False)
        offset = response.get("data", {}).get("cursor", 0)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_live_search_results(keyword: str,
                                    max_pages: int = 1,
                                    count: int = 20) -> List[Dict]:
    """
    Fetch live search results with pagination.

    Args:
        keyword: Search keyword
        max_pages: Maximum number of pages to fetch
        count: Number of results per page
    """
    params = {
        "keyword": keyword,
        "count": count,
    }

    all_results = []
    offset = 0

    for page in range(max_pages):
        params["offset"] = offset

        response = await _make_app_request("fetch_live_search_result", params)
        if "error" in response:
            break

        live_list = response.get("data", {}).get("data", [])
        all_results.extend(live_list)

        has_more = response.get("data", {}).get("has_more", False)
        offset = response.get("data", {}).get("cursor", 0)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_music_detail(music_id: str) -> Dict:
    """
    Fetch details about a music track.

    Args:
        music_id: TikTok music ID
    """
    result = await _make_app_request("fetch_music_detail", {"music_id": music_id})
    return result.get("data", {}).get("music_info", {})


async def fetch_music_video_list(music_id: str,
                                 max_pages: int = 1,
                                 count: int = 10) -> List[Dict]:
    """
    Fetch videos using a specific music track with pagination.

    Args:
        music_id: TikTok music ID
        max_pages: Maximum number of pages to fetch
        count: Number of videos per page
    """
    params = {
        "music_id": music_id,
        "count": count
    }

    all_videos = []
    cursor = 0

    for _ in range(max_pages):
        params["cursor"] = cursor

        response = await _make_app_request("fetch_music_video_list", params)
        if "error" in response:
            break

        videos = response.get("data", {}).get("aweme_list", [])
        all_videos.extend(videos)

        has_more = response.get("data", {}).get("has_more", False)
        cursor = response.get("data", {}).get("cursor", 0)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_hashtag_detail(ch_id: str) -> List[Dict]:
    """
    Fetch details about a hashtag.

    Args:
        ch_id: TikTok challenge/hashtag ID
    """
    result = await _make_app_request("fetch_hashtag_detail", {"ch_id": ch_id})
    return [result.get("data", {}).get("ch_info", {})]


async def fetch_hashtag_video_list(ch_id: str,
                                   max_pages: int = 1,
                                   count: int = 10) -> List[Dict]:
    """
    Fetch videos using a specific hashtag with pagination.

    Args:
        ch_id: TikTok challenge/hashtag ID
        max_pages: Maximum number of pages to fetch
        count: Number of videos per page
    """
    params = {
        "ch_id": ch_id,
        "count": count
    }

    all_videos = []
    cursor = 0

    for _ in range(max_pages):
        params["cursor"] = cursor

        response = await _make_app_request("fetch_hashtag_video_list", params)
        if "error" in response:
            break

        videos = response.get("data", {}).get("aweme_list", [])
        all_videos.extend(videos)

        has_more = response.get("data", {}).get("has_more", False)
        cursor = response.get("data", {}).get("cursor", 0)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_videos


async def fetch_user_follower_list(sec_user_id: Optional[str] = None,
                                   url: Optional[str] = None,
                                   max_pages: int = 1,
                                   count: int = 20) -> List[Dict]:
    """
    Fetch a user's followers with pagination.

    Args:
        sec_user_id: User's sec_user_id
        url: User's profile URL (optional, will be converted to sec_user_id)
        max_pages: Maximum number of pages to fetch
        count: Number of followers per page
    """
    params = {
        "sec_user_id": sec_user_id,
        "count": count,
        "min_time": 0  # Initial min_time is 0
    }

    if sec_user_id is None and url:
        sec_user_id = await url_to_sec_user_id(url)
        params["sec_user_id"] = sec_user_id

    all_followers = []
    page_token = None

    for _ in range(max_pages):
        if page_token:
            params["page_token"] = page_token

        response = await _make_app_request("fetch_user_follower_list", params)
        if "error" in response:
            break

        followers = response.get("data", {}).get("followers", [])
        all_followers.extend(followers)

        page_token = response.get("data", {}).get("next_page_token")
        has_more = response.get("data", {}).get("has_more", False)

        if not has_more or not page_token:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_followers


async def fetch_user_following_list(sec_user_id: Optional[str] = None,
                                    url: Optional[str] = None,
                                    max_pages: int = 1,
                                    count: int = 20) -> List[Dict]:
    """
    Fetch accounts a user is following with pagination.

    Args:
        sec_user_id: User's sec_user_id
        url: User's profile URL (optional, will be converted to sec_user_id)
        max_pages: Maximum number of pages to fetch
        count: Number of following accounts per page
    """
    params = {
        "sec_user_id": sec_user_id,
        "count": count
    }

    if sec_user_id is None and url:
        sec_user_id = await url_to_sec_user_id(url)
        params["sec_user_id"] = sec_user_id

    all_following = []
    page_token = None

    for _ in range(max_pages):
        if page_token:
            params["page_token"] = page_token

        response = await _make_app_request("fetch_user_following_list", params)
        if "error" in response:
            break

        following = response.get("data", {}).get("followings", [])
        all_following.extend(following)

        page_token = response.get("data", {}).get("next_page_token")
        has_more = response.get("data", {}).get("has_more", False)

        if not has_more or not page_token:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_following


async def fetch_live_room_info(room_id: Optional[str] = None, url: Optional[str] = None) -> List[Dict]:
    """
    Fetch information about a TikTok live room.

    Args:
        room_id: TikTok live room ID
        url: TikTok live room URL (optional, will be converted to room_id)
    """
    if room_id is None and url:
        room_id = await url_to_room_id(url)
    if room_id is None and url is None:
        return []

    result = await _make_app_request("fetch_live_room_info", {"room_id": room_id})
    return [result.get("data", {}).get("data", {})]


async def check_live_room_online(room_id: Optional[str] = None, url: Optional[str] = None) -> bool:
    """
    Check if a live room is currently online.

    Args:
        room_id: TikTok live room ID
        url: TikTok live room URL (optional, will be converted to room_id)
    """
    if room_id is None and url:
        room_id = await url_to_room_id(url)
    if room_id is None and url is None:
        return False

    result = await _make_app_request("check_live_room_online", {"room_id": room_id})
    return result.get("data", {}).get("data", [])[0].get("alive", False)


async def fetch_location_search(keyword: str, count: int = 10, max_pages: int = 1) -> List[Dict]:
    """
    Search for locations by keyword.

    Args:
        keyword: Location keyword
        count: Number of results per page
        max_pages: Maximum number of pages to fetch
    """
    params = {
        "keyword": keyword,
        "count": count
    }

    all_locations = []
    cursor = 0

    for _ in range(max_pages):
        params["cursor"] = cursor

        response = await _make_app_request("fetch_location_search", params)
        if "error" in response:
            break

        locations = response.get("data", {}).get("poi_info", {}).get("poi_info", [])
        all_locations.extend(locations)

        has_more = response.get("data", {}).get("has_more", False)
        cursor = response.get("data", {}).get("cursor", 0)

        if not has_more:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)
    return all_locations


async def fetch_product_detail(product_id: Optional[str] = None, product_url: Optional[str] = None, region: str = "US") -> List[Dict]:
    """
    Get detailed information about a TikTok Shop product.

    Args:
        product_id: TikTok product ID
        product_url: TikTok product URL
        region: Region code (default: "US")
    """
    if product_url:
        product_id = await fetch_product_id_by_share_link(product_url)
    if product_id is None and product_url is None:
        return []

    result = await _make_app_request("fetch_product_detail_v3", {"product_id": product_id, "region": region})

    return [result.get("data", {})]


async def fetch_shop_product_list(seller_id: Optional[str] = None,
                                  share_url: Optional[str] = None,
                                  page_size: int = 10,
                                  sort_field: int = 1,
                                  sort_order: int = 0,
                                  max_pages: int = 1) -> List[Dict]:
    """
    Get a list of products from a TikTok Shop with pagination.

    Args:
        seller_id: TikTok seller ID
        share_url: TikTok shop share URL (optional, will be converted to seller_id)
        page_size: Number of products per page
        sort_field: Sort field (1-Default)
        sort_order: Sort order (0-Ascending, 1-Descending)
        max_pages: Maximum number of pages to fetch
    """
    params = {
        "seller_id": seller_id,
        "page_size": page_size,
        "sort_field": sort_field,
        "sort_order": sort_order
    }

    if share_url:
        seller_id = await fetch_shop_id_by_share_link(share_url)
        params["seller_id"] = seller_id

    if seller_id is None and share_url is None:
        return []

    all_products = []
    scroll_params = has_more = None

    for _ in range(max_pages):
        params["scroll_params"] = scroll_params

        response = await _make_app_request("fetch_shop_product_list_v2", params)
        if "error" in response:
            break

        data = response.get("data", {})

        for element in data:
            if isinstance(element, Dict):
                products = element.get("data", {}).get("products_list", [])
                all_products.extend(products)
                scroll_params = element.get("data", {}).get("next_scroll_param")
                has_more = element.get("data", {}).get("has_more", False)

        if not has_more or not scroll_params:
            break

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_products


async def fetch_shop_product_category(seller_id: Optional[str] = None, share_url: Optional[str] = None,) -> List[Dict]:
    """
    Get product categories from a TikTok Shop.

    Args:
        seller_id: TikTok seller ID
        share_url: TikTok shop share URL (optional, will be converted to seller_id)
    """
    if share_url:
        seller_id = await fetch_shop_id_by_share_link(share_url)
    if seller_id is None and share_url is None:
        return []
    result = await _make_app_request("fetch_shop_product_category", {"seller_id": seller_id})
    return result.get("data", {}).get("data", {}).get("category_list", [])


async def fetch_creator_info(creator_uid: str) -> List[Dict]:
    """
    Get information about a TikTok creator.

    Args:
        creator_uid: TikTok creator user ID
    """
    result = await _make_app_request("fetch_creator_info", {"creator_uid": creator_uid})
    return [result.get("data", {}).get("data", {}).get("creator_info", {})]


"""
async def fetch_live_daily_rank(anchor_id: str,
                                room_id: str,
                                rank_type: int = 8,
                                region_type: int = 1,
                                gap_interval: int = 0) -> Dict:
    
    Get daily ranking information for a live room.

    Args:
        anchor_id: Live anchor user ID
        room_id: Live room ID
        rank_type: Ranking type (8-Default)
        region_type: Region type (1-Default)
        gap_interval: Gap interval (0-Default)
    
    params = {
        "anchor_id": anchor_id,
        "room_id": room_id,
        "rank_type": rank_type,
        "region_type": region_type,
        "gap_interval": gap_interval
    }

    return await _make_app_request("fetch_live_daily_rank", params)
"""

async def save_to_json(data: Any, filename: str) -> None:
    """Save data to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Data saved to {filename}")


# Example usage
async def main():
    start = time.time()

    # Example: Fetch a single video
    video = await fetch_one_video("7463308759842966791")
    await save_to_json(video, "tiktok_video.json")

    # Example: Fetch user profile and their videos
    user = await fetch_user_profile(sec_user_id="MS4wLjABAAAAv7iSuuXDJGDvJkmH_vz1qkDZYo1apxgzaxdBSeIuPiM")
    await save_to_json(user, "tiktok_user.json")

    user_videos = await fetch_user_post_videos(
        sec_user_id="MS4wLjABAAAAv7iSuuXDJGDvJkmH_vz1qkDZYo1apxgzaxdBSeIuPiM",
        max_pages=2
    )
    await save_to_json(user_videos, "tiktok_user_videos.json")

    # Example: Search for videos
    search_results = await fetch_video_search_results(
        keyword="funny",
        max_pages=2,
        count=10,
        sort_type=0,
        publish_time=0
    )
    await save_to_json(search_results, "tiktok_search_results.json")

    # Example: Fetch multiple types of data concurrently
    tasks = [
        fetch_hashtag_detail("7551"),
        fetch_music_detail("6943027371519772674"),
        fetch_location_search("New York")
    ]

    results = await asyncio.gather(*tasks)
    hashtag, music, locations = results

    await save_to_json(hashtag, "tiktok_hashtag.json")
    await save_to_json(music, "tiktok_music.json")
    await save_to_json(locations, "tiktok_locations.json")

    print(f"Total time: {time.time() - start:.2f}s")


# Running the async main function
if __name__ == "__main__":
    asyncio.run(main())