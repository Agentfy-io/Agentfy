import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, Union
from urllib.parse import quote
from config import settings

# Constants
API_KEY = settings.tikhub_api_key
BASE_URL = "https://api.tikhub.io/api/v1/instagram/web_app"
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


async def fetch_user_info_by_username(username: str) -> Dict:
    """
    Fetch user information by username, combining results from two endpoints.
    """
    results1 = await _make_request(f"fetch_user_info_by_username", {"username": username})
    results2 = await _make_request(f"fetch_user_info_by_username_v3", {"username": username})

    # Combine results
    combined_data = {}
    if "data" in results1:
        combined_data.update(results1.get("data", {}))
    if "data" in results2:
        combined_data.update(results2.get("data", {}).get("data", {}))

    return combined_data


async def fetch_user_info(identifier: str, id_type: str = "username") -> List[Dict]:
    """
    Fetch user information by username, user_id. (No url support yet)

    Args:
        identifier: Username, user_id, or profile URL
        id_type: Type of identifier ('username', 'user_id')
    """

    if id_type == "username":
        result = await fetch_user_info_by_username(identifier)
        return [result]
    elif id_type == "user_id":
        result = await _make_request(f"fetch_user_info_by_user_id", {"user_id": identifier})
        return [result]
    else:
        return []


async def fetch_user_followers(username: str, max_pages: int = 1) -> List[Dict]:
    """
    Fetch a user's followers by username with pagination.
    Each Page contains 50 items.

    Args:
        username: Instagram username
        max_pages: Maximum number of pages to fetch
    """
    endpoint = "fetch_user_followers_by_username"
    params = {"username": username}
    all_followers = []
    pagination_token = None

    for _ in range(max_pages):
        if pagination_token:
            params["pagination_token"] = pagination_token

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        followers = response.get("data", {}).get("data",{}).get("items", [])
        all_followers.extend(followers)

        pagination_token = response.get("data", {}).get("pagination_token")
        if not pagination_token:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_followers


async def fetch_user_following(username: str, max_pages: int = 1) -> List[Dict]:
    """
    Fetch accounts a user is following with pagination.
    Each Page contains 50 items.

    Args:
        username: Instagram username
        max_pages: Maximum number of pages to fetch
    """
    endpoint = "fetch_user_following_by_username"
    params = {"username": username}
    all_following = []
    pagination_token = None

    for _ in range(max_pages):
        if pagination_token:
            params["pagination_token"] = pagination_token

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        following = response.get("data", {}).get("data", {}).get("items", [])
        all_following.extend(following)

        pagination_token = response.get("data", {}).get("pagination_token")
        if not pagination_token:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_following


async def fetch_user_posts(user_id: str, max_pages: int = 1) -> List[Dict]:
    """
    Fetch user posts with pagination.

    Args:
        user_id: Instagram user ID
        max_pages: Maximum number of pages to fetch
    """
    endpoint = "fetch_user_posts_by_user_id"
    params = {"user_id": user_id}
    all_posts = []
    end_cursor = None

    for _ in range(max_pages):
        if end_cursor:
            params["end_cursor"] = end_cursor

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        post_info = response.get("data", {}).get("data", {}).get("user", {}).get("edge_owner_to_timeline_media", {})

        posts = post_info.get("edges", [])
        all_posts.extend(posts)

        page_info = post_info.get("page_info", {})
        has_next_page = page_info.get("has_next_page", False)
        end_cursor = page_info.get("end_cursor")

        if not has_next_page or not end_cursor:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_posts


async def fetch_user_reels(identifier: str, max_pages: int = 1, id_type: str = "user_id") -> List[Dict]:
    """
    Fetch user reels with pagination.

    Args:
        identifier: User ID or username
        max_pages: Maximum number of pages to fetch
        id_type: Type of identifier ('user_id' or 'username')
    """
    if id_type == "user_id":
        endpoint = "fetch_user_reels_by_user_id"
        params = {"user_id": identifier}
    elif id_type == "username":
        endpoint = "fetch_user_reels_by_username"
        params = {"username": identifier}
    else:
        return []

    all_reels = []
    max_id = None

    for _ in range(max_pages):
        if max_id:
            params["max_id"] = max_id

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        reels = response.get("data", {}).get("items", [])
        all_reels.extend(reels)

        more_available = response.get("data", {}).get("paging_info", {}).get("more_available", False)
        max_id = response.get("data", {}).get("paging_info", {}).get("max_id")

        if not more_available or not max_id:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_reels


async def fetch_user_stories(username: str) -> List[Dict]:
    """
    Fetch a user's stories by username.

    Args:
        username: Instagram username
    """
    result = await _make_request("fetch_user_stories_by_username", {"username": username})
    return result.get("data", {}).get("data", {}).get("items", [])


async def fetch_user_highlights(username: str) -> List[Dict]:
    """
    Fetch a user's highlights by username.

    Args:
        username: Instagram username
    """
    result = await _make_request("fetch_user_highlights_by_username", {"username": username})
    return result.get("data", {}).get("data", {}).get("items", [])


async def fetch_user_posts_and_reels(identifier: str, max_pages: int = 1, id_type: str = "username") -> List[Dict]:
    """
    Fetch user posts and reels with pagination.

    Args:
        identifier: Username or profile URL
        max_pages: Maximum number of pages to fetch
        id_type: Type of identifier ('username' or 'url')
    """
    if id_type == "username":
        endpoint = "fetch_user_posts_and_reels_by_username"
        params = {"username": identifier}
    elif id_type == "url":
        endpoint = "fetch_user_posts_and_reels_by_url"
        params = {"url": identifier}
    else:
        return []

    all_items = []
    pagination_token = None

    for _ in range(max_pages):
        if pagination_token:
            params["pagination_token"] = pagination_token

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        items = response.get("data", {}).get("data", {}).get("items", [])
        all_items.extend(items)

        pagination_token = response.get("data", {}).get("pagination_token")
        if not pagination_token:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_items


async def fetch_user_tagged_posts(identifier: str, count: int = 12, max_pages: int = 1, id_type: str = "user_id") -> List[Dict]:
    """
    Fetch posts where a user is tagged with pagination.

    Args:
        identifier: User ID or username
        count: Number of posts per page
        max_pages: Maximum number of pages to fetch
        id_type: Type of identifier ('user_id' or 'username')
    """
    if id_type == "user_id":
        endpoint = "fetch_user_tagged_posts_by_user_id"
        params = {"user_id": identifier, "count": count}
        cursor_field = "end_cursor"
        has_more_field = "has_next_page"
    elif id_type == "username":
        endpoint = "fetch_user_tagged_posts_by_username"
        params = {"username": identifier}
        cursor_field = "pagination_token"
        has_more_field = None  # Username version may use different pagination logic
    else:
        return []

    all_posts = []
    cursor = None

    for _ in range(max_pages):
        if cursor:
            params[cursor_field] = cursor

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        if id_type == "user_id":
            post_info = response.get("data", {}).get("data", {}).get("user", {}).get("edge_user_to_photos_of_you", {})
            posts = post_info.get("edges", [])
            page_info = post_info.get("page_info", {})
            has_more = page_info.get(has_more_field, False)
            cursor = page_info.get(cursor_field)
        else:  # username
            posts = response.get("data", {}).get("data", {}).get("items", [])
            cursor = response.get("data", {}).get(cursor_field)
            has_more = cursor is not None

        all_posts.extend(posts)

        if not has_more or not cursor:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_posts


async def fetch_similar_accounts(identifier: str, id_type: str = "username") -> List[Dict]:
    """
    Fetch similar accounts by username or user ID. (No URL support yet)

    Args:
        identifier: Username or user ID
        id_type: Type of identifier ('username' or 'userid')
    """
    if id_type == "username":
        result = await _make_request("fetch_similar_accounts_by_username", {"username": identifier})
        return result.get("data", {}).get("data", {}).get("items", [])
    elif id_type == "userid":
        result = await _make_request("fetch_similar_accounts_by_userid", {"userid": identifier})
        return result.get("data", {}).get("data", {}).get("items", [])
    else:
        return []


async def search_reels_by_keyword(keyword: str) -> List[Dict]:
    """
    Search for reels by keyword.

    Args:
        keyword: Search term
    """
    result = await _make_request("fetch_search_reels_by_keyword_v2", {"keyword": keyword})
    return result.get("data", {}).get("data", {}).get("items", [])


async def search_hashtags_by_keyword(keyword: str) -> List[Dict]:
    """
    Search for hashtags by keyword. Tries two different endpoints.
    The first one is the preferred one, and the second one is a fallback.

    Args:
        keyword: Search term
    """
    # Try first endpoint
    results = await _make_request("fetch_search_hashtags_by_keyword_v2", {"keyword": keyword})

    # If first endpoint fails, try second endpoint
    if "error" in results or not results.get("data"):
        results = await _make_request("fetch_search_hashtags_by_keyword", {"keyword": keyword})
        results = results.get("data", {}).get("data", {}).get("items", [])
    else:
        results = results.get("data", {}).get("data", {}).get("items", [])
    return results


async def search_hashtag_posts_by_keyword(keyword: str, feed_type: str = "top", max_pages: int = 1) -> List[Dict]:
    """
    Fetch posts for a hashtag with pagination.

    Args:
        keyword: Hashtag keyword (without #)
        feed_type: Type of feed ('top' or 'recent' or 'clips')
        max_pages: Maximum number of pages to fetch
    """
    endpoint = "fetch_hashtag_posts_by_keyword"
    params = {"keyword": keyword, "feed_type": feed_type}
    all_posts = []
    pagination_token = None

    for _ in range(max_pages):
        if pagination_token:
            params["pagination_token"] = pagination_token

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        posts = response.get("data", {}).get("posts", [])
        all_posts.extend(posts)

        pagination_token = response.get("data", {}).get("pagination_token")
        if not pagination_token:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_posts


async def search_audios_by_keyword(keyword: str) -> List[Dict]:
    """
    Search for audio tracks by keyword.

    Args:
        keyword: Search term
    """
    result = await _make_request("fetch_search_audios_by_keyword_v2", {"keyword": keyword})
    return result.get("data", {}).get("data", {}).get("items", [])


async def search_locations_by_keyword(keyword: str) -> List[Dict]:
    """
    Search for locations by keyword.

    Args:
        keyword: Search term
    """
    result = await _make_request("fetch_search_locations_by_keyword_v2", {"keyword": keyword})
    return result.get("data", {}).get("data", {}).get("items", [])


async def search_users_by_keyword(keyword: str) -> List[Dict]:
    """
    Search for users by keyword, trying v1 first and falling back to v2 if needed.

    Args:
        keyword: Search term
    """
    # Try v1 endpoint first
    response = await _make_request("fetch_search_users_by_keyword", {"keyword": keyword})

    # If v1 doesn't work (error or empty results), try v2
    if "error" in response or not response.get("data") or not response.get("data", {}).get("users", []):
        response = await _make_request("fetch_search_users_by_keyword_v2", {"keyword": keyword})
        response = response.get("data", {}).get("data", {}).get("items", [])
    else:
        response = response.get("data", {}).get("users", [])

    return response


async def fetch_post_info(identifier: str, id_type: str = "url") -> List[Dict]:
    """
    Fetch general information about a post by URL or post ID.

    Args:
        identifier: Post URL or post ID
        id_type: Type of identifier ('url' or 'post_id')
    """
    if id_type == "url":
        result = await _make_request("fetch_post_info_by_url", {"url": identifier})
        return [result.get("data", {})]
    elif id_type == "post_id":
        result = await _make_request("fetch_post_info_by_post_id", {"post_id": identifier})
        return [result.get("data", {})]
    else:
        return []


async def fetch_post_details(identifier: str, id_type: str = "url") -> List[Dict]:
    """
    Fetch detailed information about a post by URL or code (not supporting post_id)

    Args:
        identifier: Post URL or post ID
        id_type: Type of identifier ('url' or 'post_id')
    """
    if id_type == "url":
        result = await _make_request("fetch_post_details_by_url", {"url": identifier})
        return [result.get("data", {}).get("data", {})]
    elif id_type == "code":
        result = await _make_request("fetch_post_details_by_cide", {"url": identifier})
        return [result.get("data", {}).get("data", {})]
    else:
        return []


async def fetch_music_related_posts(music_id: str) -> List[Dict]:
    """
    Fetch posts that are related to this music

    Args:
        music_id: Music ID
    """
    result = await _make_request("fetch_music_info_by_music_id", {"music_id": music_id})
    return result.get("data", {}).get("items", [])


async def fetch_location_posts(location_id: str, max_pages: int = 1, type: str ="recent") -> List[Dict]:
    """
    Fetch posts from a specific location with pagination.

    Args:
        location_id: Location ID
        max_pages: Maximum number of pages to fetch
        type: Type of feed ('recent' or 'ranked')
    """
    endpoint = "fetch_location_posts_by_location_id"
    params = {"location_id": location_id}
    all_posts = []
    max_id = None

    for _ in range(max_pages):
        if max_id:
            params["max_id"] = max_id

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        posts_info = None
        if type == "recent":
            posts_info = response.get("data", {}).get("native_location_data", {}).get("recent", {})
        elif type == "ranked":
            posts_info = response.get("data", {}).get("native_location_data", {}).get("ranked", {})

        posts = posts_info.get("sections", [])
        all_posts.extend(posts)

        more_available = posts_info.get("more_available", False)
        if not more_available:
            break
        max_id = posts_info.get("next_max_id")
        if not max_id:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_posts


async def fetch_post_comments(url: str, sort_type: str = "recent", max_pages: int = 1) -> List[Dict]:
    """
    Fetch comments on a post with pagination.
    Each page contains 5 items.

    Args:
        url: Post URL
        sort_type: Sort order ('recent' or 'top')
        max_pages: Maximum number of pages to fetch
    """
    endpoint = "fetch_post_comments_by_url"
    params = {"url": quote(url), "sort_type": sort_type}
    all_comments = []
    pagination_token = None

    for _ in range(max_pages):
        if pagination_token:
            params["pagination_token"] = pagination_token

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        comments = response.get("data", {}).get("data", {}).get("items", [])
        all_comments.extend(comments)

        pagination_token = response.get("data", {}).get("pagination_token")
        if not pagination_token:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_comments


async def fetch_post_likes(url: str) -> List[Dict]:
    """
    Fetch likes on a post by URL.

    Args:
        url: Post URL
    """
    result = await _make_request("fetch_post_likes_by_url", {"url": quote(url)})
    return result.get("data", {}).get("data", {}).get("items", [])


async def save_to_json(data: Any, filename: str) -> None:
    """Save data to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Data saved to {filename}")


# Example usage
async def main():
    start = time.time()

    # Example: Fetch user information
    user_info = await fetch_user_info_by_username("instagram")
    await save_to_json(user_info, "instagram_profile.json")

    # Example: Fetch user posts
    if "data" in user_info and "id" in user_info["data"]:
        user_id = user_info["data"]["id"]
        posts = await fetch_user_posts(user_id, count=20)
        await save_to_json(posts, "instagram_posts.json")

    # Example: Fetch multiple data concurrently
    tasks = [
        fetch_user_reels("instagram", id_type="username"),
    ]

    results = await asyncio.gather(*tasks)
    reels= results

    await save_to_json(reels, "instagram_reels.json")

    print(f"Total time: {time.time() - start:.2f}s")


# Running the async main function
if __name__ == "__main__":
    asyncio.run(main())