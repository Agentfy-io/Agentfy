import requests
import time
from typing import Dict, List, Optional, Union, Any
import json
from config import settings
from common.ais.chatgpt import ChatGPT
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)


class XCleaner:
    """
    A class for cleaning and processing X data.
    raw_data = [{....},{...}....] (Dict)

    raw_data ---> panda dataframe

    list_keys = panda_dataframe.cols (提取所有的键）['user_id', 'tweet_id'.....]

    required_keys  = chatgpt (user_request, list_keys)

    cleaned_data = raw_data[keys] (panda)

    TODO
    1. 将raw data从list of dict转换成panda，
    2. 使用panda内置方法提取keys，存储再一个list里面
    3. 使用gpt来分析需要那些keys
    4. 使用panda和提取的keys来清洗，并且返回下一步所需要的数据

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


