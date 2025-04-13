import requests
import time
from typing import Dict, List, Optional, Union, Any
import json
from config import settings
from common.ais.chatgpt import ChatGPT
from common.utils.logging import setup_logger
import pandas as pd

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
        # Convert raw data to pandas DataFrame
        logger.info("starting to clean data")
        df = pd.DataFrame(tweet_data)
        list_keys = df.columns.tolist()
        logger.info(f"Extracted keys from data: {list_keys}")
        # let chatgpt clean the data based on user_request
        system_prompt = (
            "You are a data preprocessing assistant specialized in cleaning structured data. "
            "Given a user's intent and a list of column names (keys), your task is to decide which keys are relevant for further analysis. "
            "You will not clean the actual values, only determine the subset of keys to retain. "
            "Output a JSON list of relevant keys based strictly on the user request. "
            "Do not add explanation or extra text—only return the JSON list."
        )
        user_prompt = (
            f"The user wants to clean and filter tweet data with the following intent:\n\n"
            f"{user_request}\n\n"
            f"Here are the available keys in the data:\n{list_keys}\n\n"
            f"Please return a JSON array (e.g., [\"key1\", \"key2\"]) containing only the keys relevant to the user's request."
        )

        response = await self.chatgpt.chat(system_prompt, user_prompt)

        tweet_data = response['response']["choices"][0]["message"]["content"].stripe()
        tweet_data = json.loads(tweet_data)

        return tweet_data


