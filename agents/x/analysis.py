import json
import pandas as pd
from typing import List, Dict, Any

from common.ais.chatgpt import ChatGPT
from common.utils.logging import setup_logger

logger = setup_logger(__name__)


async def clean_raw_data(user_request: str, tweet_data: List[Dict], next_step: str ) -> List[Any]:
    """
    Clean raw tweet data based on user's request using GPT to select relevant keys.

    Args:
        user_request: User's request for data cleaning.
        tweet_data: Raw tweet data (list of dictionaries).
        next_step: The next step in the workflow that requires specific parameters.

    Returns:
        Cleaned data (list of dictionaries with only relevant keys).
    """
    # Convert raw data to DataFrame, make sure nested structures are flattened
    try:
        df = pd.json_normalize(tweet_data)
    except Exception as e:
        logger.error(f"Failed to create DataFrame: {e}")
        return []

    # Get the list of keys (columns) in the DataFrame
    list_keys = df.columns.tolist()

    # Generate GPT prompts
    system_prompt = (
        "You are a data cleaning assistant. Your task is to determine which key(s) from tweet data are needed for the next step in a processing workflow. "
        "You will be given: (1) a user request, (2) a list of available keys from the data, and (3) a dictionary describing the next step and its expected parameters. "
        "Select only the key or keys that are relevant to both the user’s intent and the requirements of the next step. "
        "Determine how many keys to select based on the type of the next step’s parameter: "
        "if it expects a List[str] or List[int] or List[bool] or List[float], then select one key; "
        "if it expects a List[Dict], then select multiple keys corresponding to fields in the dict. "
        "Your response must be a pure JSON list of the selected keys, with no explanations or extra text."
    )

    user_prompt = (
        f"User request: {user_request}\n\n"
        f"Available keys: {list_keys}\n\n"
        f"Next step and required parameters: {next_step}\n\n"
        f"Please return a JSON array (e.g., [\"key1\", \"key2\"]) of relevant key or keys."
    )

    # Call GPT
    chatgpt = ChatGPT()
    response = await chatgpt.chat(system_prompt, user_prompt)
    content = response['response']["choices"][0]["message"]["content"].strip()

    try:
        relevant_keys = json.loads(content)
        logger.info(f"GPT selected keys: {relevant_keys}")
    except json.JSONDecodeError:
        logger.error("Failed to parse GPT response as JSON list")
        return []

    # Return cleaned data
    if len(relevant_keys) == 1:
        # Return a list of strings for the single relevant key
        cleaned_df = df[relevant_keys[0]].fillna("").astype(str).tolist()
    else:
        # Return a list of dicts with only relevant keys
        cleaned_df = df[relevant_keys].fillna("").to_dict(orient="records")

    return cleaned_df
