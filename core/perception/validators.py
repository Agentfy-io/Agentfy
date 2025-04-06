# -*- coding: utf-8 -*-
"""
@file: agentfy/core/perception/validators.py
@desc: customized exceptions
@auth: Callmeiks
"""
from typing import Dict, List, Any, Optional
import re
import mimetypes
from common.utils.logging import get_logger
from common.models.messages import FileValidationResult

logger = get_logger(__name__)


class ContentValidator:
    """Validator for content specific validation rules."""

    # Character limits
    MAX_TEXT_LENGTH = 10000  # 10k chars
    MIN_TEXT_LENGTH = 1  # at least 1 char

    # Regex patterns for social media handles
    TIKTOK_HANDLE_PATTERN = r'^@[a-zA-Z0-9_.]{1,24}$'
    TWITTER_HANDLE_PATTERN = r'^@[a-zA-Z0-9_]{1,15}$'
    INSTAGRAM_HANDLE_PATTERN = r'^@[a-zA-Z0-9_.]{1,30}$'

    # Regex for URLs
    URL_PATTERN = r'^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$'

    def validate_text_length(self, text: str) -> Dict[str, Any]:
        """Validate text length is within acceptable limits."""
        if not text:
            return {
                "valid": False,
                "reason": "Text cannot be empty"
            }

        if len(text) < self.MIN_TEXT_LENGTH:
            return {
                "valid": False,
                "reason": f"Text must be at least {self.MIN_TEXT_LENGTH} characters"
            }

        if len(text) > self.MAX_TEXT_LENGTH:
            return {
                "valid": False,
                "reason": f"Text exceeds maximum length of {self.MAX_TEXT_LENGTH} characters"
            }

        return {"valid": True}

    def validate_social_media_handle(self, handle: str, platform: str) -> Dict[str, Any]:
        """Validate a social media handle for the specified platform."""
        if not handle:
            return {
                "valid": False,
                "reason": "Handle cannot be empty"
            }

        platform = platform.lower()

        if platform == "tiktok":
            pattern = self.TIKTOK_HANDLE_PATTERN
            max_length = 24
        elif platform == "twitter" or platform == "x":
            pattern = self.TWITTER_HANDLE_PATTERN
            max_length = 15
        elif platform == "instagram":
            pattern = self.INSTAGRAM_HANDLE_PATTERN
            max_length = 30
        else:
            return {
                "valid": False,
                "reason": f"Unsupported platform: {platform}"
            }

        # Add @ if missing
        if not handle.startswith('@'):
            handle = '@' + handle

        if len(handle) > max_length + 1:  # +1 for the @ symbol
            return {
                "valid": False,
                "reason": f"Handle too long for {platform}, maximum is {max_length} characters"
            }

        if not re.match(pattern, handle):
            return {
                "valid": False,
                "reason": f"Invalid {platform} handle format: {handle}"
            }

        return {"valid": True, "normalized_handle": handle}

    def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate a URL."""
        if not url:
            return {
                "valid": False,
                "reason": "URL cannot be empty"
            }

        if not re.match(self.URL_PATTERN, url):
            return {
                "valid": False,
                "reason": f"Invalid URL format: {url}"
            }

        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        return {"valid": True, "normalized_url": url}

    def validate_hashtags(self, hashtags: List[str]) -> Dict[str, Any]:
        """Validate a list of hashtags."""
        if not hashtags:
            return {"valid": True, "hashtags": []}

        valid_hashtags = []
        invalid_hashtags = []

        for tag in hashtags:
            # Remove # if present
            tag = tag.strip()
            if tag.startswith('#'):
                tag = tag[1:]

            # Empty hashtag
            if not tag:
                invalid_hashtags.append('#')
                continue

            # Check for spaces or special chars (except underscore)
            if ' ' in tag or not re.match(r'^[a-zA-Z0-9_]+$', tag):
                invalid_hashtags.append(f'#{tag}')
                continue

            valid_hashtags.append(f'#{tag}')

        if invalid_hashtags:
            return {
                "valid": False,
                "reason": f"Invalid hashtags: {', '.join(invalid_hashtags)}",
                "valid_hashtags": valid_hashtags
            }

        return {"valid": True, "hashtags": valid_hashtags}