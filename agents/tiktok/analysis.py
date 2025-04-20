import json
import pandas as pd
from typing import List, Dict, Any

from common.ais.chatgpt import ChatGPT
from common.utils.logging import setup_logger

import pandasai as pai

from config import settings

logger = setup_logger(__name__)

pai.api_key.set(settings.pandas_api_key)

async def clean_raw_data(user_request: str, tiktok_data: List[Dict], next_step: str = None) -> Any:
    """
    Clean raw x data dynamically based on user's request.
    Step 1: Use ChatGPT to generate a PandasAI prompt.
    Step 2: Use pandasai (pai.DataFrame) to process the data according to the prompt.

    Args:
        user_request: Description of the data cleaning request.
        tiktok_data: Raw x data (list of dicts).
        next_step: Description of the next step and its expected parameters.

    Returns:
        Cleaned data (could be a list, dict, DataFrame, or any type depending on user request).
    """
    # Convert raw data to pandas DataFrame
    try:
        df_raw = pd.json_normalize(tiktok_data)
        df_raw.columns = df_raw.columns.str.replace(r'\W+', '_', regex=True)  # <=== ✨ 加这一行
    except Exception as e:
        logger.error(f"Failed to create DataFrame: {e}")
        return None

    logger.info(df_raw.columns.tolist())

    # Prepare for pandasai
    df = pai.DataFrame(df_raw)

    # Ask ChatGPT to generate a smart PandasAI prompt
    system_prompt = (
        "You are a prompt engineer specializing in generating instructions for pandasai (an AI tool for DataFrames). "
        "Your task is to create a clear, direct instruction for pandasai to select specific column(s) and filter rows, "
        "based only on numeric comparisons (>, <, >=, <=, ==) according to (1) user request, (2) available data columns, and (3) an optional next step.\n\n"
        "Constraints:\n"
        "- Always explicitly mention the selected column(s) from the available columns.\n"
        "- Only numeric/date filtering is allowed; do not perform any text matching, substring search, or regular expression operations.\n"
        "- If user request involves non-numeric columns, politely ignore and focus only on numeric or date column filtering.\n"
        "- Keep the generated instruction actionable and concise.\n"
        "- Output ONLY the pure instruction text without any extra commentary or explanations."
    )

    user_prompt = (
        f"User request:\n{user_request}\n\n"
        f"Available columns:\n{df_raw.columns.tolist()}\n\n"
        f"Next step:\n{next_step}\n\n"
        "Now build the instruction text for pandasai."
    )

    chatgpt = ChatGPT()

    try:
        response = await chatgpt.chat(system_prompt, user_prompt)
        pandasai_prompt = response['response']["choices"][0]["message"]["content"].strip()
        logger.info(f"Generated PandasAI prompt: {pandasai_prompt}")
    except Exception as e:
        logger.error(f"Failed to generate PandasAI prompt: {e}")
        return None

    # Use pandasai DataFrame to execute the prompt
    try:
        cleaned_output = df.chat(pandasai_prompt)
        logger.info("PandasAI data cleaning completed successfully.")
    except Exception as e:
        logger.error(f"PandasAI execution failed: {e}")
        return None

    # logger.info(f"Cleaned output: {cleaned_output}")

    return cleaned_output
