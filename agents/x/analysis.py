import requests
import time
from typing import Dict, List, Optional, Union, Any
import json
from common.ais.chatgpt import ChatGPT
import pandas as pd
import dask.dataframe as dd
import re
import ast


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

        # Step 1: Convert raw data to DataFrame
        df = pd.DataFrame(tweet_data)

        # Step 2: Extract all keys (column names) from the DataFrame
        list_keys = df.columns.tolist()
        print(list_keys)

        # Step 3: Use ChatGPT to determine required keys based on user request
        system_prompt = "You are a data cleaning assistant. Your job is to analyze the data and determine which keys are required based on the user's request."
        user_prompt = f"Analyze the following data to return the list element as a list based on the user request: {user_request}\nData keys: {list_keys}"
        response = await self.chatgpt.chat(system_prompt, user_prompt)

        # Step 1: 提取字符串中的 required_keys
        content = response['response']['choices'][0]['message']['content']

        # 使用正则表达式提取代码块中的内容
        match = re.search(r"```python\n(.+?)\n```", content, re.DOTALL)
        if match:
            # 提取到的字符串形式的列表
            keys_str = match.group(1)
            # 使用 ast.literal_eval 将字符串解析为 Python 列表
            required_keys = ast.literal_eval(keys_str)
        else:
            required_keys = []

        print("Extracted required_keys:", required_keys)

        # Step 4: Clean data using the required keys
        # 使用 Dask 进行并行处理
        dask_df = dd.from_pandas(df, npartitions=4)
        cleaned_dask_df = dask_df[required_keys]
        cleaned_df = cleaned_dask_df.compute()

        # Convert cleaned DataFrame back to list of dictionaries
        cleaned_data = cleaned_df.to_dict(orient='records')

        return cleaned_data




