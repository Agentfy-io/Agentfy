# -*- coding: utf-8 -*-
"""
@file: agentfy/core/youtube/interactive.py
@desc: YouTube API interaction class using google-api-python-client.
@auth(s): Callmeiks
"""
import os
import pickle
import asyncio
from typing import Optional, Tuple, Dict, Any, List

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

from config import settings
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)

# YouTube API scopes
# See: https://developers.google.com/youtube/v3/guides/auth/installed-apps
SCOPES = [
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtubepartner'
]


class YouTubeInteractive:
    """
    A class to handle interactions with the YouTube API using google-api-python-client.
    """

    def __init__(self, client_id: str = None, client_secret: str = None, api_key: str = None):
        """
        Initialize the YouTube client with API credentials.

        Args:
            client_id: The OAuth client ID
            client_secret: The OAuth client secret
            api_key: The YouTube API key for non-authenticated requests
        """
        # Load environment variables if not provided
        load_dotenv()

        # Use provided credentials or get from settings
        self.client_id = client_id or settings.youtube_client_id
        self.client_secret = client_secret or settings.youtube_client_secret
        self.api_key = api_key or settings.youtube_api_key

        # Store credentials as a dict for OAuth flow
        self.client_config = {
            "web": {
                "client_id": self.client_id,
                "project_id": "social-media-agent-455511",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": self.client_secret
            }
        }

        self.credentials = None
        self.client = None
        self.user_info = None

    async def authenticate(self) -> bool:
        """
        Authenticate the client using OAuth2.

        Returns:
            True if authentication was successful, False otherwise
        """
        try:

            # If credentials don't exist or are expired, get new ones
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, lambda: self.credentials.refresh(Request()))
                else:
                    # Since we're using web application credentials that redirect to localhost,
                    # we should use run_local_server which will capture that redirect
                    flow = InstalledAppFlow.from_client_config(
                        self.client_config,
                        SCOPES,
                        redirect_uri='http://localhost:8080'
                    )

                    logger.info("Please sign in with your YouTube account when the browser opens")

                    # Use asyncio to run the blocking auth flow in the executor
                    # This will start a local web server at localhost:8080 to catch the redirect
                    loop = asyncio.get_running_loop()
                    self.credentials = await loop.run_in_executor(
                        None,
                        lambda: flow.run_local_server(port=8080, prompt='consent')
                    )

            # Build the YouTube API client
            self.client = build('youtube', 'v3', credentials=self.credentials)

            # Get user info to verify authentication
            loop = asyncio.get_running_loop()
            channels_response = await loop.run_in_executor(
                None,
                lambda: self.client.channels().list(
                    part="snippet,contentDetails,brandingSettings",
                    mine=True
                ).execute()
            )

            # Check if the authenticated user has a channel
            if not channels_response.get('items'):
                logger.error("No channel found for the authenticated user, some features may not work.")
            else:
                self.user_info = channels_response['items'][0]
                logger.info(f"Logged in as: {self.user_info['snippet']['title']}, Channel ID: {self.user_info['id']}")

            return True

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    async def upload_video(self,
                           video_path: str,
                           title: str,
                           description: str,
                           tags: List[str] = None,
                           category_id: str = "22",
                           privacy_status: str = "private") -> Optional[str]:
        """
        Upload a video to YouTube.

        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags for the video
            category_id: YouTube category ID (default: 22 - People & Blogs)
            privacy_status: Video privacy setting (private, public, unlisted)

        Returns:
            Video ID if successful, None otherwise
        """
        if not os.path.exists(video_path):
            logger.error(f"Error: Video file {video_path} does not exist.")
            return None

        if not tags:
            tags = []

        try:
            # Set up the video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False,
                }
            }

            # Create a MediaFileUpload object
            media_file = MediaFileUpload(video_path, resumable=True)

            # Use asyncio to run the blocking upload in the executor
            loop = asyncio.get_running_loop()
            request = self.client.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media_file
            )

            # Execute the upload request
            response = await loop.run_in_executor(None, request.execute)

            video_id = response.get('id')
            logger.info(f"Successfully uploaded video '{title}' with Video ID: {video_id}")
            return video_id

        except HttpError as e:
            logger.error(f"Error uploading video: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during video upload: {str(e)}")
            return None

    async def update_video(self,
                           video_id: str,
                           title: str = None,
                           description: str = None,
                           tags: List[str] = None,
                           category_id: str = None,
                           privacy_status: str = None) -> bool:
        """
        Update an existing YouTube video's metadata.

        Args:
            video_id: The ID of the video to update
            title: New video title (optional)
            description: New video description (optional)
            tags: New list of tags (optional)
            category_id: New YouTube category ID (optional)
            privacy_status: New privacy setting (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the current video data first
            loop = asyncio.get_running_loop()
            video_response = await loop.run_in_executor(
                None,
                lambda: self.client.videos().list(
                    part="snippet,status",
                    id=video_id
                ).execute()
            )

            if not video_response['items']:
                logger.error(f"Video with ID {video_id} not found.")
                return False

            # Get the current video data
            video_snippet = video_response['items'][0]['snippet']
            video_status = video_response['items'][0]['status']

            # Prepare the update data by using existing data as defaults
            update_snippet = {
                'title': title if title is not None else video_snippet.get('title', ''),
                'description': description if description is not None else video_snippet.get('description', ''),
                'tags': tags if tags is not None else video_snippet.get('tags', []),
                'categoryId': category_id if category_id is not None else video_snippet.get('categoryId', '22'),
            }

            update_status = {
                'privacyStatus': privacy_status if privacy_status is not None else video_status.get('privacyStatus',
                                                                                                    'private'),
            }

            # Create the update request
            request = self.client.videos().update(
                part="snippet,status",
                body={
                    'id': video_id,
                    'snippet': update_snippet,
                    'status': update_status
                }
            )

            # Execute the update request
            await loop.run_in_executor(None, request.execute)
            logger.info(f"Successfully updated video with ID: {video_id}")
            return True

        except HttpError as e:
            logger.error(f"Error updating video: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during video update: {str(e)}")
            return False

    async def create_caption_track(self,
                                   video_id: str,
                                   language: str,
                                   caption_file: str,
                                   name: str = None,
                                   is_draft: bool = False) -> bool:
        """
        Add a caption track to a video.

        Args:
            video_id: The ID of the video to add captions to
            language: The language code of the captions (e.g., 'en', 'es')
            caption_file: Path to the caption file (srt, sbv, etc.)
            name: Optional name for the caption track
            is_draft: Whether the captions are in draft status

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(caption_file):
            logger.error(f"Error: Caption file {caption_file} does not exist.")
            return False

        try:
            loop = asyncio.get_running_loop()

            # Define caption metadata
            caption_meta = {
                'snippet': {
                    'videoId': video_id,
                    'language': language,
                    'name': name or f"{language.upper()} captions",
                    'isDraft': is_draft
                }
            }

            # 1. Insert the caption metadata
            insert_response = await loop.run_in_executor(
                None,
                lambda: self.client.captions().insert(
                    part='snippet',
                    body=caption_meta
                ).execute()
            )

            # 2. Upload the caption file
            caption_id = insert_response['id']
            media = MediaFileUpload(caption_file, mimetype='application/octet-stream')

            upload_response = await loop.run_in_executor(
                None,
                lambda: self.client.captions().update(
                    part='snippet',
                    body=caption_meta,
                    id=caption_id,
                    media_body=media
                ).execute()
            )

            logger.info(f"Successfully added {language} captions to video ID: {video_id}")
            return True

        except HttpError as e:
            logger.error(f"Error adding caption track: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during caption upload: {str(e)}")
            return False

    async def reply_to_comment(self, parent_comment_id: str, comment_text: str) -> bool:
        """
        Reply to a comment on a YouTube video.

        Args:
            parent_comment_id: The ID of the comment to reply to
            comment_text: The content of the reply

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()

            # Create the comment body
            comment_body = {
                'snippet': {
                    'parentId': parent_comment_id,
                    'textOriginal': comment_text
                }
            }

            # Execute the comment insert
            response = await loop.run_in_executor(
                None,
                lambda: self.client.comments().insert(
                    part='snippet',
                    body=comment_body
                ).execute()
            )

            logger.info(f"Successfully replied to comment {parent_comment_id}")
            return True

        except HttpError as e:
            logger.error(f"Error replying to comment: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during comment reply: {str(e)}")
            return False

    async def delete_comment(self, comment_id: str) -> bool:
        """
        Delete a comment.

        Args:
            comment_id: The ID of the comment to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()

            # Execute the comment delete
            await loop.run_in_executor(
                None,
                lambda: self.client.comments().delete(
                    id=comment_id
                ).execute()
            )

            logger.info(f"Successfully deleted comment ID: {comment_id}")
            return True

        except HttpError as e:
            logger.error(f"Error deleting comment: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during comment deletion: {str(e)}")
            return False

    async def add_to_playlist(self, playlist_id: str, video_id: str, position: int = 0) -> bool:
        """
        Add a video to a playlist.

        Args:
            playlist_id: The ID of the playlist
            video_id: The ID of the video to add
            position: Position in the playlist (0 = at the end)

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()

            # Create the playlist item body
            playlist_item_body = {
                'snippet': {
                    'playlistId': playlist_id,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    },
                    'position': position
                }
            }

            # Execute the playlist item insert
            response = await loop.run_in_executor(
                None,
                lambda: self.client.playlistItems().insert(
                    part='snippet',
                    body=playlist_item_body
                ).execute()
            )

            logger.info(f"Successfully added video {video_id} to playlist {playlist_id}")
            return True

        except HttpError as e:
            logger.error(f"Error adding video to playlist: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during playlist addition: {str(e)}")
            return False

    async def create_playlist(self, title: str, description: str = '', privacy_status: str = 'private') -> Optional[str]:
        """
        Create a new playlist.

        Args:
            title: The title of the playlist
            description: The description of the playlist
            privacy_status: The privacy status of the playlist (private, public, unlisted)

        Returns:
            Playlist ID if successful, None otherwise
        """
        try:
            loop = asyncio.get_running_loop()

            # Create the playlist body
            playlist_body = {
                'snippet': {
                    'title': title,
                    'description': description
                },
                'status': {
                    'privacyStatus': privacy_status
                }
            }

            # Execute the playlist insert
            response = await loop.run_in_executor(
                None,
                lambda: self.client.playlists().insert(
                    part='snippet,status',
                    body=playlist_body
                ).execute()
            )

            playlist_id = response.get('id')
            logger.info(f"Successfully created playlist '{title}' with ID: {playlist_id}")
            return playlist_id

        except HttpError as e:
            logger.error(f"Error creating playlist: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during playlist creation: {str(e)}")
            return None

    async def rate_video(self, video_id: str, rating: str = 'like') -> bool:
        """
        Rate a video (like, dislike, or remove rating).

        Args:
            video_id: The ID of the video to rate
            rating: The rating to set ('like', 'dislike', or 'none')

        Returns:
            True if successful, False otherwise
        """
        if rating not in ['like', 'dislike', 'none']:
            logger.error("Invalid rating. Must be 'like', 'dislike', or 'none'.")
            return False

        try:
            loop = asyncio.get_running_loop()

            # Execute the video rate request
            await loop.run_in_executor(
                None,
                lambda: self.client.videos().rate(
                    id=video_id,
                    rating=rating
                ).execute()
            )

            logger.info(f"Successfully rated video {video_id} as {rating}")
            return True

        except HttpError as e:
            logger.error(f"Error rating video: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during video rating: {str(e)}")
            return False

    async def subscribe_to_channel(self, channel_id: str) -> bool:
        """
        Subscribe to a channel.

        Args:
            channel_id: The ID of the channel to subscribe to

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()

            # Create the subscription body
            subscription_body = {
                'snippet': {
                    'resourceId': {
                        'kind': 'youtube#channel',
                        'channelId': channel_id
                    }
                }
            }

            # Execute the subscription insert
            response = await loop.run_in_executor(
                None,
                lambda: self.client.subscriptions().insert(
                    part='snippet',
                    body=subscription_body
                ).execute()
            )

            logger.info(f"Successfully subscribed to channel {channel_id}")
            return True

        except HttpError as e:
            logger.error(f"Error subscribing to channel: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during channel subscription: {str(e)}")
            return False

    async def report_abuse(self, video_id: str, reason_id: str, secondary_reason_id: str = None,
                           comment: str = None) -> bool:
        """
        Report a video for abuse.

        Args:
            video_id: The ID of the video to report
            reason_id: The reason for reporting
                (pornography, hatred, harmful_dangerous_acts, harassment_cyberbullying,
                 spam_deceptive_practices, child_abuse, violent_repulsive, copyright,
                 privacy, impersonation, trademark)
            secondary_reason_id: Additional specificity for the report (optional)
            comment: Additional comments about the abuse (optional)

        Returns:
            True if successful, False otherwise
        """
        valid_reasons = [
            'pornography', 'hatred', 'harmful_dangerous_acts', 'harassment_cyberbullying',
            'spam_deceptive_practices', 'child_abuse', 'violent_repulsive', 'copyright',
            'privacy', 'impersonation', 'trademark'
        ]

        if reason_id not in valid_reasons:
            logger.error(f"Invalid reason_id. Must be one of: {', '.join(valid_reasons)}")
            return False

        try:
            loop = asyncio.get_running_loop()

            # Create the abuse report body
            report_body = {
                'videoId': video_id,
                'reasonId': reason_id
            }

            if secondary_reason_id:
                report_body['secondaryReasonId'] = secondary_reason_id

            if comment:
                report_body['comments'] = comment

            # Execute the video abuse report
            await loop.run_in_executor(
                None,
                lambda: self.client.videos().reportAbuse(
                    body=report_body
                ).execute()
            )

            logger.info(f"Successfully reported video {video_id} for abuse")
            return True

        except HttpError as e:
            logger.error(f"Error reporting video abuse: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during abuse reporting: {str(e)}")
            return False


async def main():
    # Initialize the YouTube client
    client = YouTubeInteractive()

    # Authenticate the client
    authenticated = await client.authenticate()

    if authenticated:
        # Example: Upload a video
        video_id = await client.upload_video(
            video_path="video_0.mp4",
            title="Test Video",
            description="This is a test video uploaded via the YouTube API",
            tags=["test", "api", "youtube"],
            privacy_status="private"
        )

        # Example: Update the video
        if video_id:
            await client.update_video(
                video_id=video_id,
                title="Updated Test Video",
                description="This is an updated test video description",
                tags=["updated", "api", "youtube"]
            )

        # Example:comment reply
        # await client.reply_to_comment(
        #     parent_comment_id="COMMENT_ID",
        #     comment_text="This is a reply to a comment"
        # )

        # create a playlist
        playlist_id = await client.create_playlist(
            title="Test Playlist",
            description="This is a test playlist created via the YouTube API",
            privacy_status="private"
        )

        # set the playList to public
        if playlist_id:
            await client.update_video(
                video_id=video_id,
                privacy_status="public"
            )


if __name__ == "__main__":
    asyncio.run(main())