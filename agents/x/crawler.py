import requests
import time
from typing import Dict, List, Optional, Union, Any
import json
from config import settings
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)


class XCrawler:
    """
    A crawler class for X data using the TikHub API.
    Includes methods for searching tweets, fetching user tweets, trending topics,
    and user followers with pagination support.
    """

    def __init__(self):
        """
        Initialize the TwitterCrawler with API key and base URL.

        Args:
            api_key: The API key for authorization
            base_url: Base URL for the API endpoints
        """
        self.api_key = settings.tikhub_api_key
        self.base_url = "https://api.tikhub.io/api/v1/twitter/web"
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.rate_limit_delay = 1  # Default delay between requests in seconds

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a GET request to the specified endpoint with parameters.

        Args:
            endpoint: API endpoint to request
            params: URL parameters for the request

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return {"error": str(e)}

    def fetch_search_posts(self, keyword: str, search_type: str = "Top", max_pages: int = 1) -> List[Dict]:
        """
        Search tweets based on keyword.

        Args:
            keyword: Search keyword
            search_type: Type of search ("Top", "Latest", etc.)
            max_pages: Maximum number of pages to fetch

        Returns:
            List of tweets from search results
        """
        endpoint = "fetch_search_timeline"                                                                                               
        params = {
            "keyword": keyword,
            "search_type": search_type
        }

        all_results = []
        current_page = 0
        cursor = None

        while current_page < max_pages:
            if cursor:
                params["cursor"] = cursor

            response = self._make_request(endpoint, params)

            if "error" in response:
                break

            # Extract tweets from response
            if "data" in response:
                tweets = response.get("data", {}).get("timeline", [])
                all_results.extend(tweets)

                # Get next cursor for pagination
                cursor = response.get("data", {}).get("next_cursor", None)
                if not cursor:
                    break  # No more pages

                current_page += 1
                time.sleep(self.rate_limit_delay)
            else:
                break

        return all_results

    def fetch_user_tweets(self, screen_name: str, cursor: Optional[str] = None,
                          max_pages: int = 1) -> List[Dict]:
        """
        Fetch tweets posted by a specific user.

        Args:
            screen_name: Twitter handle without '@'
            cursor: Pagination cursor
            max_pages: Maximum number of pages to fetch

        Returns:
            List of user's tweets
        """
        endpoint = "fetch_user_post_tweet"
        params = {"screen_name": screen_name}

        all_tweets = []
        current_page = 0

        while current_page < max_pages:
            if cursor:
                params["cursor"] = cursor

            response = self._make_request(endpoint, params)

            if "error" in response:
                break

            # Extract tweets from response
            if "data" in response:
                pinned_tweets = response.get("data", {}).get("tweets", [])
                all_tweets.extend(pinned_tweets)

                tweets = response.get("data", {}).get("timeline", [])
                all_tweets.extend(tweets)

                # Get next cursor for pagination
                cursor = response.get("data", {}).get("next_cursor", None)
                if not cursor:
                    break  # No more pages

                current_page += 1
                time.sleep(self.rate_limit_delay)
            else:
                break

        return all_tweets

    def fetch_tweets_comments(self, tweet_id: str, cursor: Optional[str] = None,
                              max_pages: int = 1) -> List[Dict]:
        """
        Fetch comments for a specific tweet.

        Args:
            tweet_id: ID of the tweet to fetch comments for
            cursor: Pagination cursor
            max_pages: Maximum number of pages to fetch

        Returns:
            List of comments for the tweet
        """
        endpoint = "fetch_tweet_comments"
        params = {"tweet_id": tweet_id}
        all_comments = []
        current_page = 0
        while current_page < max_pages:
            if cursor:
                params["cursor"] = cursor

            response = self._make_request(endpoint, params)

            if "error" in response:
                break

            # Extract comments from response
            if "data" in response:
                comments = response.get("data", {}).get("comments", [])
                all_comments.extend(comments)

                # Get next cursor for pagination
                cursor = response.get("data", {}).get("next_cursor", None)
                if not cursor:
                    break
                current_page += 1
                time.sleep(self.rate_limit_delay)
            else:
                break
        return all_comments


    def fetch_trending_topics(self, country: str = "UnitedStates") -> List[Dict]:
        """
        Fetch trending topics for a specific country.

        Args:
            country: Country name to fetch trends for

        Returns:
            List of trending topics
        """
        endpoint = "fetch_trending"
        params = {"country": country}

        response = self._make_request(endpoint, params)

        if "error" in response:
            return []

        # Extract trending topics from response
        if "data" in response:
            return response.get("data", {}).get("trends", [])

        return []

    def fetch_user_followers(self, screen_name: str, cursor: Optional[str] = None,
                             max_pages: int = 1) -> List[Dict]:
        """
        Fetch followers of a specific user.

        Args:
            screen_name: Twitter handle without '@'
            cursor: Pagination cursor
            max_pages: Maximum number of pages to fetch

        Returns:
            List of user's followers
        """
        endpoint = "fetch_user_followers"
        params = {"screen_name": screen_name}

        all_followers = []
        current_page = 0

        while current_page < max_pages:
            if cursor:
                params["cursor"] = cursor

            response = self._make_request(endpoint, params)

            if "error" in response:
                break

            # Extract followers from response
            if "data" in response:
                followers = response.get("data", {}).get("followers", [])
                all_followers.extend(followers)

                # Get next cursor for pagination
                cursor = response.get("data", {}).get("next_cursor", None)
                has_more = response.get("data", {}).get("more_users", False)
                if not cursor or not has_more:
                    break  # No more pages

                current_page += 1
                time.sleep(self.rate_limit_delay)
            else:
                break

        return all_followers

    def save_to_json(self, data: Any, filename: str) -> None:
        """
        Save data to a JSON file.

        Args:
            data: Data to save
            filename: Output filename
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Data saved to {filename}")


# Example usage:
if __name__ == "__main__":

    crawler = XCrawler()

    start = time.time()

    # Example 1: Search tweets about Elon Musk
    tweets = crawler.fetch_search_posts(keyword="Elon Musk", max_pages=2)
    crawler.save_to_json(tweets, "elon_musk_tweets.json")

    print(f"Time taken for search: {time.time() - start} seconds")
    start = time.time()

    # Example 2: Fetch Elon Musk's tweets
    elon_tweets = crawler.fetch_user_tweets(screen_name="elonmusk", max_pages=2)
    crawler.save_to_json(elon_tweets, "elonmusk_tweets.json")
    print(f"Time taken for user tweets: {time.time() - start} seconds")
    start = time.time()

    # Example 3: Fetch trending topics in the United States
    trends = crawler.fetch_trending_topics(country="UnitedStates")
    crawler.save_to_json(trends, "us_trends.json")
    print(f"Time taken for trends: {time.time() - start} seconds")
    start = time.time()

    # Example 4: Fetch Elon Musk's followers
    followers = crawler.fetch_user_followers(screen_name="elonmusk", max_pages=1)
    crawler.save_to_json(followers, "elonmusk_followers.json")
    print(f"Time taken for followers: {time.time() - start} seconds")

