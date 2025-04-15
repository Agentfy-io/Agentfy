# social_media_agent/core/memory/module.py
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json
import uuid

from common.models.messages import ChatMessage
from common.models.workflows import WorkflowDefinition
from common.exceptions.exceptions import RecordNotFoundError, StorageError
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)

class MemoryModule:
    """
    Memory Module for storing and retrieving data such as chat history,
    workflow history, user preferences, and agent knowledge.
    Uses in-memory storage instead of a database.

    FOR REFERENCE ONLY！ ！ ！ This module is designed to be a placeholder ！ ！ ！
    """

    def __init__(self):
        """Initialize the memory module with in-memory storage."""
        # In-memory storage for different data types
        self.chat_history = {}  # user_id -> list of messages

    # Chat History Methods

    async def get_user_chat_history(self, user_id: str, limit: int = 50) -> List[ChatMessage]:
        """
        Get chat history for a user.

        Args:
            user_id: The user ID
            limit: Maximum number of messages to retrieve

        Returns:
            List[ChatMessage]: List of chat messages

        Raises:
            RecordNotFoundError: If user has no chat history
        """
        try:
            logger.info(f"Getting chat history for user {user_id}")

            if user_id not in self.chat_history or not self.chat_history[user_id]:
                # Return empty list instead of raising error for new users
                return []

            # Return most recent messages first
            messages = self.chat_history[user_id][-limit:]
            return messages

        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            raise RecordNotFoundError(f"Chat history not found for user: {user_id}", {"details": str(e)})

    async def add_chat_message(self, user_id: str, sender:str, receiver:str, message: Any) -> str:
        """
        Add a message to the chat history.

        Args:
            user_id: The user ID
            sender: The sender of the message
            receiver: The receiver of the message
            message: The chat message to add

        Returns:
            str: The ID of the added message

        Raises:
            StorageError: If message storage fails
        """
        try:
            # Convert message to ChatMessage if not already
            if not isinstance(message, ChatMessage):
                message = ChatMessage(
                    id=str(uuid.uuid4()),
                    sender=sender,
                    receiver=receiver,
                    content=message,
                    metadata={
                        "user_id": user_id
                    }
                )

            # Initialize chat history for user if it doesn't exist
            if user_id not in self.chat_history:
                self.chat_history[user_id] = []

            # Add message to chat history
            self.chat_history[user_id].append(message)

            logger.info(f"Added message {message.id} to chat history for user {user_id}")

            return message.id

        except Exception as e:
            logger.error(f"Error adding chat message: {str(e)}")
            raise StorageError(f"Failed to store chat message for user {user_id}", {"details": str(e)})

    async def search_chat_history(self, user_id: str, query: str) -> List[ChatMessage]:
        """
        Search chat history for a user.

        Args:
            user_id: The user ID
            query: Search query string

        Returns:
            List[ChatMessage]: List of matching chat messages
        """
        try:
            logger.info(f"Searching chat history for user {user_id} with query '{query}'")

            if user_id not in self.chat_history:
                return []

            # Simple search implementation
            results = []
            for message in self.chat_history[user_id]:
                if query.lower() in str(message.content).lower():
                    results.append(message)

            return results

        except Exception as e:
            logger.error(f"Error searching chat history: {str(e)}")
            return []
