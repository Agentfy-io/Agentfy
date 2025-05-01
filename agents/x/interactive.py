import tweepy
import webbrowser
import asyncio
from dotenv import load_dotenv
from typing import Optional, Tuple, List, Dict
from config import settings
from common.utils.logging import setup_logger

logger = setup_logger(__name__)
load_dotenv()


def get_api_credentials(api_key: Optional[str] = None, api_secret: Optional[str] = None) -> Tuple[str, str]:
    return api_key or settings.x_api_key, api_secret or settings.x_api_secret


async def get_user_access_tokens(api_key: str, api_secret: str) -> Tuple[Optional[str], Optional[str]]:
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, callback="oob")
    auth_url = auth.get_authorization_url()
    logger.info("Please visit this URL to authorize the app:")
    logger.info(auth_url)
    webbrowser.open(auth_url)

    pin = input("Enter the PIN you received after authorizing the app: ").strip()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: auth.get_access_token(pin))

    return auth.access_token, auth.access_token_secret


async def authenticate() -> Tuple[Optional[tweepy.Client], Optional[tweepy.API]]:
    api_key, api_secret = get_api_credentials()
    access_token, access_token_secret = await get_user_access_tokens(api_key, api_secret)

    if not access_token or not access_token_secret:
        return None, None

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    v1_auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
    api_v1 = tweepy.API(v1_auth)
    return client, api_v1


async def post_tweets(messages: List[str]) -> Dict[str, str]:
    client, _ = await authenticate()
    if not client:
        return {"status": False, "message": "X Authentication failed. Please check your credentials."}
    for message in messages:
        if len(message) > 280:
            logger.error("Tweet exceeds 280 characters.")
            continue
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: client.create_tweet(text=message))
        logger.info(f"Tweet posted: ID {response.data['id']}")
    return {"status": True, "message": "All tweets posted."}


async def upload_media_and_posts(messages: List[str], media_paths: List[str]) -> Dict[str, str]:
    client, api_v1 = await authenticate()
    if not client or not api_v1:
        return {"status": False, "message": "X Authentication failed. Please check your credentials."}
    if len(messages) != len(media_paths):
        return {"status": False, "message": "Number of messages and media files do not match."}
    for message, media in zip(messages, media_paths):
        if len(message) > 280:
            logger.error("Tweet exceeds 280 characters.")
            continue
        loop = asyncio.get_running_loop()
        media_response = await loop.run_in_executor(None, lambda: api_v1.media_upload(media))
        response = await loop.run_in_executor(None, lambda: client.create_tweet(text=message, media_ids=[media_response.media_id]))
        logger.info(f"Tweet posted with media: ID {response.data['id']}")
    return {"status": True, "message": "All tweets with media posted."}


async def delete_tweets(tweet_ids: List[str]) -> Dict[str, str]:
    client, _ = await authenticate()
    if not client:
        return {"status": False, "message": "X Authentication failed. Please check your credentials."}
    for tweet_id in tweet_ids:
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: client.delete_tweet(tweet_id))
            logger.info(f"Tweet deleted: {tweet_id}")
        except Exception as e:
            logger.error(f"Delete tweet error: {str(e)}")
            return {"status": False, "message": f"Failed to delete tweet {tweet_id}: {e}"}
    return {"status": True, "message": "All tweets deleted."}


async def send_dm(recipient_ids: List[str], message: str) -> Dict[str, str]:
    client, _ = await authenticate()
    if not client:
        return {"status": False, "message": "X Authentication failed. Please check your credentials."}
    for recipient_id in recipient_ids:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: client.create_direct_message(participant_id=recipient_id, text=message))
        logger.info(f"DM sent to {recipient_id}")
    return {"status": True, "message": "All DMs sent."}


async def reply_to_tweets(tweet_ids: List[str], message: str) -> Dict[str, str]:
    client, _ = await authenticate()
    if not client:
        return {"status": False, "message": "X Authentication failed. Please check your credentials."}
    for tweet_id in tweet_ids:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: client.create_tweet(text=message, in_reply_to_tweet_id=tweet_id))
        logger.info(f"Replied to tweet {tweet_id}")
    return {"status": True, "message": "All replies sent."}


async def follow_users(user_ids: List[str]) -> Dict[str, str]:
    client, _ = await authenticate()
    if not client:
        return {"status": False, "message": "X Authentication failed. Please check your credentials."}
    for user_id in user_ids:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: client.follow_user(target_user_id=user_id))
        logger.info(f"Followed user {user_id}")
    return {"status": True, "message": "All users followed."}


async def like_tweets(tweet_ids: List[str]) -> Dict[str, str]:
    client, _ = await authenticate()
    if not client:
        return {"status": False, "message": "X Authentication failed. Please check your credentials."}
    for tweet_id in tweet_ids:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: client.like(tweet_id))
        logger.info(f"Liked tweet {tweet_id}")
    return {"status": True, "message": "All tweets liked."}


async def unlike_tweets(tweet_ids: List[str]) -> Dict[str, str]:
    client, _ = await authenticate()
    if not client:
        return {"status": False, "message": "X Authentication failed. Please check your credentials."}
    for tweet_id in tweet_ids:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: client.unlike(tweet_id))
        logger.info(f"Unliked tweet {tweet_id}")
    return {"status": True, "message": "All tweets unliked."}


async def retweet_tweets(tweet_ids: List[str]) -> Dict[str, str]:
    client, _ = await authenticate()
    if not client:
        return {"status": False, "message": "X Authentication failed. Please check your credentials."}
    for tweet_id in tweet_ids:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: client.retweet(tweet_id))
        logger.info(f"Retweeted {tweet_id}")
    return {"status": True, "message": "All tweets retweeted."}


async def main():
    result = await post_tweets(["Hello, X World! This is a Test! 🌍 #XAPI"])
    if result:
        logger.info("Tweets posted successfully.")
    else:
        logger.error("Failed to post tweets.")


if __name__ == "__main__":
    asyncio.run(main())