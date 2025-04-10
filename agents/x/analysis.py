import requests
import time
from typing import Dict, List, Optional, Union, Any
import json
from config import settings
from common.ais.chatgpt import ChatGPT


class XCleaner:
    """
    A class for cleaning and processing X data.
    """
    def __init__(self):
        """
        Initialize the XCleaner.
        """
        self.chatgpt = ChatGPT()

    async def clean_raw_data(self, user_request:str, tweet_data: List[Dict]) -> List[Any]:
        """
        Clean and process the data.

        Args:
            user_request: User's request for data cleaning.
            data: List of dictionaries containing tweet data.

        Returns:
            Cleaned data as a list of dictionaries.
        """

        # let chatgpt clean the data based on user_request
        system_prompt = "You are a data cleaning assistant. Your job is to clean the data based on the user's request, and return the cleaned data in json."
        user_prompt = f"Please clean the following data based on the user's request: {user_request}\nData: {tweet_data}"
        response = await self.chatgpt.chat(system_prompt, user_prompt)

        tweet_data = response['response']["choices"][0]["message"]["content"]
        tweet_data = json.loads(tweet_data)

        return tweet_data



# Example usage:
if __name__ == "__main__":

    x_cleaner = XCleaner()
    user_request = "Please clean the data by removing any duplicates and irrelevant information."
    data = [
        {"tweet": "Hello World!", "user": "user1"},
        {"tweet": "Hello World!", "user": "user1"},
        {"tweet": "Goodbye World!", "user": "user2"}
    ]

    cleaned_data = x_cleaner.clean_data(user_request, data)
    print(cleaned_data)

