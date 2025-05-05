import requests
import time
from typing import Dict, List, Optional, Union, Any
import json
import sys
import os

import dotenv

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

dotenv.load_dotenv()

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
        self.api_key = os.getenv("TIKHUB_API_KEY")
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


# Initialize crawler instance
crawler = XCrawler()


# Function tools for X Agent

@function_tool(
    name_override="search_x_tool", 
    description_override="Search X (Twitter) for posts containing specific keywords."
)
async def search_x_tool(keyword: str, search_type: str = None, max_pages: int = None) -> str:
    # Set default values
    if search_type is None:
        search_type = "Top"
    if max_pages is None:
        max_pages = 1
    
    try:
        # Use the crawler to search posts
        posts = crawler.fetch_search_posts(keyword, search_type, max_pages)
        
        if not posts:
            return "No posts found for the given keyword."
        
        # Format the results as a string with each post separated by newlines
        formatted_posts = []
        for i, post in enumerate(posts, 1):
            tweet_id = post.get("tweet_id", "N/A")
            user = post.get("user", {}).get("screen_name", "unknown")
            text = post.get("text", "No content")
            likes = post.get("favorite_count", 0)
            retweets = post.get("retweet_count", 0)
            
            formatted_post = (
                f"--- Post {i} ---\n"
                f"ID: {tweet_id}\n"
                f"User: @{user}\n"
                f"Content: {text}\n"
                f"Likes: {likes} | Retweets: {retweets}\n"
            )
            formatted_posts.append(formatted_post)
        
        return "\n".join(formatted_posts)
    except Exception as e:
        return f"Error searching X posts: {str(e)}"


@function_tool(
    name_override="get_user_tweets_tool", 
    description_override="Get tweets from a specific X (Twitter) user."
)
async def get_user_tweets_tool(screen_name: str, max_pages: int = None) -> str:
    if max_pages is None:
        max_pages = 1
    
    try:
        # Remove @ symbol if present
        if screen_name.startswith('@'):
            screen_name = screen_name[1:]
            
        # Use the crawler to fetch user tweets
        tweets = crawler.fetch_user_tweets(screen_name, max_pages=max_pages)
        
        if not tweets:
            return f"No tweets found for user @{screen_name}."
        
        # Format the results as a string with each tweet separated by newlines
        formatted_tweets = []
        for i, tweet in enumerate(tweets, 1):
            tweet_id = tweet.get("tweet_id", "N/A")
            text = tweet.get("text", "No content")
            likes = tweet.get("favorite_count", 0)
            retweets = tweet.get("retweet_count", 0)
            created_at = tweet.get("created_at", "Unknown date")
            
            formatted_tweet = (
                f"--- Tweet {i} ---\n"
                f"ID: {tweet_id}\n"
                f"Posted: {created_at}\n"
                f"Content: {text}\n"
                f"Likes: {likes} | Retweets: {retweets}\n"
            )
            formatted_tweets.append(formatted_tweet)
        
        return "\n".join(formatted_tweets)
    except Exception as e:
        return f"Error fetching user tweets: {str(e)}"


@function_tool(
    name_override="get_tweet_comments_tool", 
    description_override="Get comments/replies to a specific X (Twitter) post by its ID."
)
async def get_tweet_comments_tool(tweet_id: str, max_pages: int = None) -> str:
    if max_pages is None:
        max_pages = 1
    
    try:
        # Use the crawler to fetch tweet comments
        comments = crawler.fetch_tweets_comments(tweet_id, max_pages=max_pages)
        
        if not comments:
            return f"No comments found for tweet ID {tweet_id}."
        
        # Format the results as a string with each comment separated by newlines
        formatted_comments = []
        for i, comment in enumerate(comments, 1):
            comment_id = comment.get("tweet_id", "N/A")
            user = comment.get("user", {}).get("screen_name", "unknown")
            text = comment.get("text", "No content")
            likes = comment.get("favorite_count", 0)
            retweets = comment.get("retweet_count", 0)
            
            formatted_comment = (
                f"--- Comment {i} ---\n"
                f"ID: {comment_id}\n"
                f"User: @{user}\n"
                f"Content: {text}\n"
                f"Likes: {likes} | Retweets: {retweets}\n"
            )
            formatted_comments.append(formatted_comment)
        
        return "\n".join(formatted_comments)
    except Exception as e:
        return f"Error fetching tweet comments: {str(e)}"


@function_tool(
    name_override="get_trending_topics_tool", 
    description_override="Get trending topics on X (Twitter) for a specific country."
)
async def get_trending_topics_tool(country: str = None) -> str:
    if country is None:
        country = "UnitedStates"
    
    try:
        # Use the crawler to fetch trending topics
        trends = crawler.fetch_trending_topics(country)
        
        if not trends:
            return f"No trending topics found for {country}."
        
        # Format the results as a string with each trend separated by newlines
        formatted_trends = []
        for i, trend in enumerate(trends, 1):
            name = trend.get("name", "N/A")
            tweet_volume = trend.get("tweet_volume", "Unknown")
            
            formatted_trend = (
                f"{i}. {name} (Volume: {tweet_volume})"
            )
            formatted_trends.append(formatted_trend)
        
        return f"Trending topics in {country}:\n" + "\n".join(formatted_trends)
    except Exception as e:
        return f"Error fetching trending topics: {str(e)}"


# Create the X Agent
x_agent = Agent(
    name="X Agent",
    handoff_description="A helpful agent that can search and retrieve information from X (formerly Twitter).",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an X platform agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the customer's request related to X (Twitter).
    2. Choose the appropriate tool:
       - Use search_x_tool to find posts about specific topics or keywords
       - Use get_user_tweets_tool to retrieve tweets from a specific user
       - Use get_tweet_comments_tool to get replies to a specific tweet
       - Use get_trending_topics_tool to see what's trending
    3. Present the information to the customer in a clear, helpful format.
    4. If you cannot answer the question, transfer back to the triage agent.""",
    tools=[search_x_tool, get_user_tweets_tool, get_tweet_comments_tool, get_trending_topics_tool],
)

# This will be set from agents-triage.py when that file imports this one
# x_agent.handoffs will be initialized later when triage_agent becomes available