# -*- coding: utf-8 -*-
"""
@file: agentfy/common/models/messages.py
@desc: message models, including user input, validation result, security check result, etc.
@auth: Callmeiks
"""
from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)

class SecurityIssue(BaseModel):
    type: str
    details: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class FileInfo(BaseModel):
    filename: str
    file_path: str
    size: int
    file_content: Any


class UserMetadata(BaseModel):
    user_id: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = "web"
    ip_address: Optional[str] = None


class UserInput(BaseModel):
    text: Optional[str] = None
    files: List[FileInfo]
    metadata: UserMetadata


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[Any] = None
    sanitized_input: Optional[Dict[str, Any]] = None


class SecurityCheckResult(BaseModel):
    is_safe: bool
    detected_issues: List[SecurityIssue] = None
    mitigation_applied: bool = False


class FileValidationResult(BaseModel):
    is_allowed: bool
    file_type: str
    reason: Optional[str] = None


class ParameterInfo(BaseModel):
    name: str
    description: str
    type: str
    required: bool
    default: Optional[Any] = None


class PromptMessage(BaseModel):
    type: Literal["PARAMETER_REQUEST", "CLARIFICATION", "CONFIRMATION"]
    message: str
    parameters: List[ParameterInfo] = None
    suggestions: Optional[List[str]] = None


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sender: Literal["USER", "AGENT", "SYSTEM"] = Field(default="USER")
    receiver: Literal["USER", "AGENT", "SYSTEM"] = Field(default="AGENT")
    content: Any = None
    metadata: Dict[str, Any] = None


class FormattedOutput(BaseModel):
    type: str
    content: Any
    format: str = "json"
    metadata: Dict[str, Any] = None

if __name__ == "__main__":
    # Example usage
    chat = ChatMessage()
    chat.sender = "USER"
    chat.content = "Hello, how can I help you?"
    chat.metadata = {"language": "en", "context": "greeting"}
    print(chat)