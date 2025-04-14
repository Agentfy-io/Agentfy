import requests
import time
import json
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


def _make_request(endpoint: str, params: Optional[Dict] = None) -> Dict:
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return {"error": str(e)}


def fetch_search_posts(keyword: str, search_type: str = "Top", max_pages: int = 1) -> List[Dict]:
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

        response = _make_request(endpoint, params)
        if "error" in response:
            break

        tweets = response.get("data", {}).get("timeline", [])
        all_results.extend(tweets)
        cursor = response.get("data", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(RATE_LIMIT_DELAY)

    return all_results


def fetch_user_tweets(screen_name: str, cursor: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
    endpoint = "fetch_user_post_tweet"
    params = {"screen_name": screen_name}
    all_tweets = []

    for _ in range(max_pages):
        if cursor:
            params["cursor"] = cursor

        response = _make_request(endpoint, params)
        if "error" in response:
            break

        data = response.get("data", {})
        all_tweets.extend(data.get("tweets", []))
        all_tweets.extend(data.get("timeline", []))

        cursor = data.get("next_cursor")
        if not cursor:
            break
        time.sleep(RATE_LIMIT_DELAY)

    return all_tweets


def fetch_tweets_comments(tweet_id: str, cursor: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
    endpoint = "fetch_tweet_comments"
    params = {"tweet_id": tweet_id}
    all_comments = []

    for _ in range(max_pages):
        if cursor:
            params["cursor"] = cursor

        response = _make_request(endpoint, params)
        if "error" in response:
            break

        comments = response.get("data", {}).get("comments", [])
        all_comments.extend(comments)

        cursor = response.get("data", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(RATE_LIMIT_DELAY)

    return all_comments


def fetch_trending_topics(country: str = "UnitedStates") -> List[Dict]:
    endpoint = "fetch_trending"
    params = {"country": country}
    response = _make_request(endpoint, params)
    if "error" in response:
        return []
    return response.get("data", {}).get("trends", [])


def fetch_user_followers(screen_name: str, cursor: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
    endpoint = "fetch_user_followers"
    params = {"screen_name": screen_name}
    all_followers = []

    for _ in range(max_pages):
        if cursor:
            params["cursor"] = cursor

        response = _make_request(endpoint, params)
        if "error" in response:
            break

        followers = response.get("data", {}).get("followers", [])
        all_followers.extend(followers)

        cursor = response.get("data", {}).get("next_cursor")
        has_more = response.get("data", {}).get("more_users", False)
        if not cursor or not has_more:
            break
        time.sleep(RATE_LIMIT_DELAY)

    return all_followers


def save_to_json(data: Any, filename: str) -> None:
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Data saved to {filename}")


# Optional test usage
if __name__ == "__main__":
    start = time.time()

    tweets = fetch_search_posts(keyword="Elon Musk", max_pages=2)
    save_to_json(tweets, "elon_musk_tweets.json")
    print(f"Search time: {time.time() - start:.2f}s")
