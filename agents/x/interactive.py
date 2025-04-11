# -*- coding: utf-8 -*-
"""
@file: agentfy/core/x/interactive.py
@desc: X (formerly Twitter) API interaction class using tweepy.
@auth(s): Callmeiks
"""
import tweepy
import webbrowser
import asyncio
from dotenv import load_dotenv
from typing import Tuple, Optional, Dict, Any
from config import settings
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)


class XInteractive:
    """
    A class to handle interactions with the X (formerly Twitter) API using tweepy.
    """

    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initialize the X client with API credentials.

        Args:
            api_key: The X API key
            api_secret: The X API secret
        """
        # Load environment variables if not provided
        load_dotenv()

        self.api_key = api_key or settings.x_api_key
        self.api_secret = api_secret or settings.x_api_secret

        self.client = None
        self.api = None  # For v1.1 API (needed for media uploads)
        self.user = None

    async def get_user_access_tokens(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Guide the user through the OAuth process to obtain access tokens.

        Returns:
            Tuple containing the access token and access token secret
        """
        try:
            auth = tweepy.OAuth1UserHandler(self.api_key, self.api_secret, callback="oob")
            auth_url = auth.get_authorization_url()
            logger.info("Please visit this URL to authorize the app:")
            logger.info(auth_url)
            webbrowser.open(auth_url)

            # This input operation is blocking, but it's necessary for user interaction
            pin = input("Enter the PIN you received after authorizing the app: ").strip()

            # Use asyncio to run the blocking get_access_token in the executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: auth.get_access_token(pin))

            logger.info("Successfully obtained access tokens!")
            return auth.access_token, auth.access_token_secret
        except tweepy.TweepyException as e:
            logger.error(f"Error during authentication: {str(e)}")
            return None, None
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            return None, None

    async def authenticate(self, access_token: str = None, access_token_secret: str = None) -> bool:
        """
        Authenticate the client with the provided or previously obtained tokens.

        Args:
            access_token: The user's access token
            access_token_secret: The user's access token secret

        Returns:
            True if authentication was successful, False otherwise
        """
        if not access_token or not access_token_secret:
            access_token, access_token_secret = await self.get_user_access_tokens()

        if not access_token or not access_token_secret:
            logger.error("Failed to authenticate. Cannot proceed.")
            return False

        # Set up v2 client
        self.client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        # Setup v1.1 API for media uploads
        auth = tweepy.OAuth1UserHandler(
            self.api_key,
            self.api_secret,
            access_token,
            access_token_secret
        )
        self.api = tweepy.API(auth)

        # Verify user - use asyncio to run the blocking API call in the executor
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: self.client.get_me())
            self.user = response.data
            logger.info(f"Logged in as: @{self.user.username}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error verifying user: {str(e)}")
            return False

    async def post_tweet(self, message: str) -> bool:
        """
        Post a tweet using the v2 API.

        Args:
            message: The tweet content (max 280 characters)

        Returns:
            True if successful, False otherwise
        """
        if len(message) > 280:
            logger.error("Error: Message exceeds 280 characters.")
            return False

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.create_tweet(text=message)
            )
            logger.info(f"Successfully posted: '{message}' with Tweet ID: {response.data['id']}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error posting to X: {str(e)}")
            return False

    async def upload_media_and_post(self, message: str, media_path: str) -> bool:
        """
        Upload media and post a tweet with it.

        Args:
            message: The tweet content
            media_path: Path to the media file to upload

        Returns:
            True if successful, False otherwise
        """
        if len(message) > 280:
            logger.error("Error: Message exceeds 280 characters.")
            return False

        try:
            loop = asyncio.get_running_loop()

            # Media upload (blocking)
            media = await loop.run_in_executor(
                None,
                lambda: self.api.media_upload(filename=media_path)
            )

            # Create tweet with media
            response = await loop.run_in_executor(
                None,
                lambda: self.client.create_tweet(text=message, media_ids=[media.media_id])
            )

            logger.info(f"Posted with media: '{message}' - Tweet ID: {response.data['id']}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error uploading media or posting: {str(e)}")
            return False

    async def delete_tweet(self, tweet_id: str) -> bool:
        """
        Delete a tweet with the specified ID.

        Args:
            tweet_id: The ID of the tweet to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.delete_tweet(tweet_id)
            )
            logger.info(f"Successfully deleted Tweet ID {tweet_id}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error deleting tweet: {str(e)}")
            return False

    async def send_dm(self, recipient_id: str, message: str) -> bool:
        """
        Send a direct message to a specified user ID.

        Args:
            recipient_id: The recipient's user ID
            message: The DM content (max 280 characters)

        Returns:
            True if successful, False otherwise
        """
        if len(message) > 280:
            logger.error("Error: Message exceeds 280 characters.")
            return False

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.create_direct_message(participant_id=recipient_id, text=message)
            )
            logger.info(f"Successfully sent DM to user ID {recipient_id}: '{message}'")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error sending DM: {str(e)}")
            return False

    async def reply_to_tweet(self, tweet_id: str, message: str) -> bool:
        """
        Reply to a tweet with the specified tweet ID.

        Args:
            tweet_id: The ID of the tweet to reply to
            message: The reply content (max 280 characters)

        Returns:
            True if successful, False otherwise
        """
        if len(message) > 280:
            logger.error("Error: Message exceeds 280 characters.")
            return False

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.create_tweet(
                    text=message,
                    in_reply_to_tweet_id=tweet_id
                )
            )
            logger.info(
                f"Successfully replied to Tweet ID {tweet_id}: '{message}' with Reply ID: {response.data['id']}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error replying to tweet: {str(e)}")
            return False

    async def follow_user(self, target_user_id: str) -> bool:
        """
        Follow a user with the specified ID.

        Args:
            target_user_id: The ID of the user to follow

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.follow_user(target_user_id=target_user_id)
            )
            logger.info(f"Successfully followed user ID {target_user_id}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error following user: {str(e)}")
            return False

    async def like_tweet(self, tweet_id: str) -> bool:
        """
        Like a tweet with the specified ID.

        Args:
            tweet_id: The ID of the tweet to like

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.like(tweet_id)
            )
            logger.info(f"Successfully liked Tweet ID {tweet_id}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error liking tweet: {str(e)}")
            return False

    async def unlike_tweet(self, tweet_id: str) -> bool:
        """
        Unlike a tweet with the specified ID.

        Args:
            tweet_id: The ID of the tweet to unlike

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.unlike(tweet_id)
            )
            logger.info(f"Successfully unliked Tweet ID {tweet_id}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error unliking tweet: {str(e)}")
            return False

    async def retweet(self, tweet_id: str) -> bool:
        """
        Retweet a tweet with the specified ID.

        Args:
            tweet_id: The ID of the tweet to retweet

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.retweet(tweet_id)
            )
            logger.info(f"Successfully retweeted Tweet ID {tweet_id}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Error retweeting: {str(e)}")
            return False


async def main():
    # Initialize the X client
    client = XInteractive()
    # Authenticate the client
    authenticated = await client.authenticate()

    if authenticated:
        # Post a tweet
        message = "Hello, X World! 🌍 #XAPI"
        posted = await client.post_tweet(message)


if __name__ == "__main__":
    asyncio.run(main())