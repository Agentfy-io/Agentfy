# -*- coding: utf-8 -*-
"""
@file: agentfy/common/security/sanitizers.py
@desc: customized exceptions
@auth: Callmeiks
"""
import re
import html
from typing import Any, Dict, List, Optional, Union
from ..models.messages import UserInput


class InputSanitizer:
    """Sanitizer for cleaning user input."""

    def sanitize_text(self, text: str) -> str:
        """Sanitize text input to prevent security issues."""
        if not text:
            return ""

        # HTML escape to prevent XSS
        sanitized = html.escape(text)

        # Remove or neutralize potential SQL injection patterns
        sanitized = re.sub(r'--', '&#45;&#45;', sanitized)
        sanitized = re.sub(r'\/\*.*\*\/', '', sanitized)
        sanitized = re.sub(r';(\s)*(SELECT|INSERT|UPDATE|DELETE|DROP)',
                           '; ', sanitized, flags=re.IGNORECASE)

        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        return sanitized

    def sanitize_file_name(self, filename: str) -> str:
        """Sanitize a filename to prevent path traversal and other issues."""
        if not filename:
            return ""

        # Remove directory traversal sequences
        sanitized = re.sub(r'\.\.', '', filename)

        # Remove any path separators
        sanitized = re.sub(r'[/\\]', '_', sanitized)

        # Remove any potentially dangerous characters
        sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', sanitized)

        return sanitized

    def sanitize_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize values in a JSON object."""
        if not json_data:
            return {}

        sanitized_data = {}

        for key, value in json_data.items():
            if isinstance(value, str):
                sanitized_data[key] = self.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized_data[key] = self.sanitize_json(value)
            elif isinstance(value, list):
                sanitized_data[key] = [
                    self.sanitize_json(item) if isinstance(item, dict)
                    else self.sanitize_text(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized_data[key] = value

        return sanitized_data

    def sanitize_input(self, input_data: UserInput) -> Dict[str, Any]:
        """Sanitize user input data."""
        sanitized_data = {
            "metadata": input_data.metadata.dict()
        }

        # Sanitize text if present
        if input_data.text:
            sanitized_data["text"] = self.sanitize_text(input_data.text)

        # Sanitize files if present
        if input_data.files:
            sanitized_files = []
            for file_info in input_data.files:
                sanitized_file = file_info.dict()
                sanitized_file["filename"] = self.sanitize_file_name(file_info.filename)
                sanitized_files.append(sanitized_file)
            sanitized_data["files"] = sanitized_files

        return sanitized_data


class FileValidator:
    """Validator for checking file types and content."""

    # Allowed file extensions by category
    ALLOWED_EXTENSIONS = {
        "image": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"],
        "document": [".pdf", ".txt", ".doc", ".docx", ".xls", ".xlsx", ".csv"],
        "media": [".mp4", ".mp3", ".avi", ".mov", ".wav"],
        "archive": [".zip", ".rar", ".7z"],
    }

    # Maximum file sizes by category (in bytes)
    MAX_FILE_SIZES = {
        "image": 10 * 1024 * 1024,  # 10 MB
        "document": 20 * 1024 * 1024,  # 20 MB
        "media": 100 * 1024 * 1024,  # 100 MB
        "archive": 50 * 1024 * 1024,  # 50 MB
    }

    def get_file_category(self, file_type: str) -> Optional[str]:
        """Get the category of a file based on its extension."""
        extension = f".{file_type.lower().split('.')[-1]}"

        for category, extensions in self.ALLOWED_EXTENSIONS.items():
            if extension in extensions:
                return category

        return None

    def is_file_type_allowed(self, file_type: str) -> bool:
        """Check if the file type is allowed."""
        return self.get_file_category(file_type) is not None

    def check_file_size(self, file_size: int, file_type: str) -> bool:
        """Check if the file size is within the allowed limit."""
        category = self.get_file_category(file_type)
        if not category:
            return False

        max_size = self.MAX_FILE_SIZES.get(category, 0)
        return file_size <= max_size

    def validate_file(self, filename: str, file_size: int) -> Dict[str, Any]:
        """Validate a file based on its name and size."""
        result = {
            "is_allowed": False,
            "file_type": filename.split(".")[-1] if "." in filename else "unknown",
            "reason": None
        }

        # Check if file type is allowed
        if not self.is_file_type_allowed(filename):
            result["reason"] = f"File type not allowed: {result['file_type']}"
            return result

        # Check if file size is within limit
        if not self.check_file_size(file_size, filename):
            category = self.get_file_category(result["file_type"])
            max_size_mb = self.MAX_FILE_SIZES.get(category, 0) / (1024 * 1024)
            result["reason"] = f"File size exceeds maximum allowed ({max_size_mb} MB)"
            return result

        # If all checks pass, file is allowed
        result["is_allowed"] = True
        return result