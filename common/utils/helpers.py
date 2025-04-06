# -*- coding: utf-8 -*-
"""
@file: agentfy/common/utils/helpers.py
@desc: customized exceptions
@auth: Callmeiks
"""
import json
import uuid
import time
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


def safe_json_dumps(obj: Any) -> str:
    """Safely convert object to JSON string."""
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return json.dumps({"error": "Object could not be serialized to JSON"})


def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """Safely parse JSON string."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON string"}


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate string to max_length characters."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def hash_content(content: str) -> str:
    """Hash content using SHA-256."""
    return hashlib.sha256(content.encode()).hexdigest()


def retry(func, max_retries: int = 3, retry_delay: int = 1,
          backoff_factor: float = 2.0, exceptions: tuple = (Exception,)):
    """Retry a function call with exponential backoff."""

    def wrapper(*args, **kwargs):
        current_retry = 0
        current_delay = retry_delay

        while True:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                current_retry += 1
                if current_retry > max_retries:
                    raise e

                time.sleep(current_delay)
                current_delay *= backoff_factor

    return wrapper


def parse_webhook_url(url: str) -> Dict[str, str]:
    """Parse a webhook URL to extract platform and other information."""
    # This is a simplified example - in a real system this would be more robust
    if "tiktok" in url.lower():
        return {"platform": "tiktok"}
    elif "twitter" in url.lower() or "x.com" in url.lower():
        return {"platform": "twitter"}
    elif "instagram" in url.lower():
        return {"platform": "instagram"}
    elif "facebook" in url.lower():
        return {"platform": "facebook"}
    elif "youtube" in url.lower():
        return {"platform": "youtube"}
    else:
        return {"platform": "unknown"}


def merge_dictionaries(dict1: Dict[str, Any], dict2: Dict[str, Any],
                       prefer_dict2: bool = True) -> Dict[str, Any]:
    """Merge two dictionaries, with conflict resolution."""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dictionaries(result[key], value, prefer_dict2)
        elif key not in result or prefer_dict2:
            result[key] = value

    return result


def deep_get(dictionary: Dict[str, Any], keys: str, default: Any = None) -> Any:
    """Get a value from a nested dictionary using dot notation."""
    keys = keys.split('.')
    for key in keys:
        if not isinstance(dictionary, dict):
            return default
        dictionary = dictionary.get(key, {})
    return dictionary if dictionary != {} else default