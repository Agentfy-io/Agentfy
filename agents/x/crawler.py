import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from config import settings
from common.utils.logging import setup_logger

logger = setup_logger(__name__)

# Constants
API_KEY = settings.tikhub_api_key
BASE_URL = "https://api.tikhub.io/api/v1/twitter/web"
HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
RATE_LIMIT_DELAY = 1


async def _make_request(endpoint: str, params: Optional[Dict] = None) -> Dict:
    url = f"{BASE_URL}/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, params=params) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Request error: {e}")
        return {"error": str(e)}


async def fetch_search_posts(keyword: str, search_type: str = "Top", max_pages: int = 1) -> List[Dict]:
    endpoint = "fetch_search_timeline"
    params = {
        "keyword": keyword,
        "search_type": search_type
    }
    all_results = []
    cursor = None

    for _ in range(max_pages):
        if cursor:
            params["cursor"] = cursor

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        tweets = response.get("data", {}).get("timeline", [])
        all_results.extend(tweets)
        cursor = response.get("data", {}).get("next_cursor")
        if not cursor:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_results


async def fetch_user_tweets(screen_name: str, cursor: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
    endpoint = "fetch_user_post_tweet"
    params = {"screen_name": screen_name}
    all_tweets = []

    for _ in range(max_pages):
        if cursor:
            params["cursor"] = cursor

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        data = response.get("data", {})
        all_tweets.extend(data.get("tweets", []))
        all_tweets.extend(data.get("timeline", []))

        cursor = data.get("next_cursor")
        if not cursor:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_tweets


async def fetch_tweets_comments(tweet_id: str, cursor: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
    endpoint = "fetch_tweet_comments"
    params = {"tweet_id": tweet_id}
    all_comments = []

    for _ in range(max_pages):
        if cursor:
            params["cursor"] = cursor

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        comments = response.get("data", {}).get("comments", [])
        all_comments.extend(comments)

        cursor = response.get("data", {}).get("next_cursor")
        if not cursor:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_comments


async def fetch_trending_topics(country: str = "UnitedStates") -> List[Dict]:
    endpoint = "fetch_trending"
    params = {"country": country}
    response = await _make_request(endpoint, params)
    if "error" in response:
        return []
    return response.get("data", {}).get("trends", [])


async def fetch_user_followers(screen_name: str, cursor: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
    endpoint = "fetch_user_followers"
    params = {"screen_name": screen_name}
    all_followers = []

    for _ in range(max_pages):
        if cursor:
            params["cursor"] = cursor

        response = await _make_request(endpoint, params)
        if "error" in response:
            break

        followers = response.get("data", {}).get("followers", [])
        all_followers.extend(followers)

        cursor = response.get("data", {}).get("next_cursor")
        has_more = response.get("data", {}).get("more_users", False)
        if not cursor or not has_more:
            break
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_followers


async def save_to_json(data: Any, filename: str) -> None:
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Data saved to {filename}")


# Example usage
async def main():
    start = time.time()

    # Example of a single operation
    tweets = await fetch_search_posts(keyword="Elon Musk", max_pages=2)
    await save_to_json(tweets, "elon_musk_tweets.json")

    # Example of running multiple operations concurrently
    tasks = [
        fetch_search_posts(keyword="Elon Musk", max_pages=1),
        fetch_trending_topics(),
        fetch_user_tweets(screen_name="elonmusk", max_pages=1)
    ]
    results = await asyncio.gather(*tasks)
    search_results, trending_topics, user_tweets = results

    print(f"Total time: {time.time() - start:.2f}s")


# Running the async main function
if __name__ == "__main__":
    asyncio.run(main())