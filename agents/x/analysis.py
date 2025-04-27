import asyncio
import json
import pandas as pd
from typing import List, Dict, Any, Optional

from common.ais.chatgpt import ChatGPT
from common.ais.claude import Claude
from common.utils.logging import setup_logger

import pandasai as pai
from flatten_json import flatten

from config import settings

logger = setup_logger(__name__)

pai.api_key.set(settings.pandas_ai_api_key)

claude = Claude()

async def clean_raw_data(user_request: str, x_data: List[Dict], next_step: Optional[str] = None) -> Any:
    """
    Clean raw x data dynamically based on user's request.
    Step 1: Use ChatGPT to generate a PandasAI prompt.
    Step 2: Use pandasai (pai.DataFrame) to process the data according to the prompt.

    Args:
        user_request: Description of the data cleaning request.
        x_data: Raw x data (list of dicts).
        next_step: Description of the next step and its expected parameters.

    Returns:
        Cleaned data (could be a list, dict, DataFrame, or any type depending on user request).
    """
    # use flatten_json to flatten the data
    try:
        # Flatten + build DataFrame
        data_flattened = [flatten(d) for d in x_data]
        df_raw = pd.DataFrame(data_flattened)

        # Treat effectively empty structures as NA
        df_raw = df_raw.applymap(lambda v: pd.NA if v is None or (isinstance(v, (str, list, dict)) and not v) else v)

        # Drop columns that are mostly empty
        min_non_null_ratio = 0.80
        valid_cols = df_raw.columns[df_raw.notna().mean() >= min_non_null_ratio]

    except Exception as e:
        logger.error(f"Failed to create DataFrame: {e}")
        return None

    # Ask ChatGPT to generate a smart PandasAI prompt
    system_prompt = (
        "Role: Social Media *Key Interpreter* + **PandasAI** Prompt Engineer.\n\n"
        "Task: Deliver **one JSON**:\n"
        '{\n'
        '  "pandasai_prompt": "<instruction>",\n'
        '  "selected_columns": ["<col1>", "<col2>", ...]\n'
        '}\n\n'
        "Process:\n"
        "1. Review the complete list of available flattened columns (keys joined by underscores '_').\n"
        "2. For each key:\n"
        "   - Interpret its meaning in the context of social media data (e.g., user profile, engagement stats, post metadata).\n"
        "   - If a key seems ambiguous, try your best to interpret it based on typical social media conventions and possible user intent.\n"
        "   - Determine if it is relevant to the user's request, even if the match is loose, partial, or uses informal terms.\n"
        "3. Put all selected matching keys into a list.\n"
        "4. Generate a PandasAI prompt that filters the DataFrame based on these selected columns, applying only numeric, datetime, or structured categorical filters.\n\n"
        "⚠️ Constraints:\n"
        "- Do NOT perform any text-based filtering like keyword search, substring matching, or regular expression matching.\n"
        "- Only structured data filtering is allowed (e.g., numeric comparisons, date ranges, categorical equality).\n\n"
        "🎯 Goal: Map user intent to the most relevant data fields and create a precise PandasAI instruction for filtering.\n"
        "📦 Output only the JSON. No additional text, explanations, or commentary."
    )

    user_prompt = (
        f"User request:\n{user_request}\n\n"
        f"Available columns:\n{valid_cols}\n\n"
        f"Next step:\n{next_step}\n\n"
        "Now build the instruction text for pandasai."
    )

    try:
        response = await claude.chat(system_prompt, user_prompt)
        result = response["choices"][0]["message"]["content"]
        result = json.loads(result)
        pandasai_prompt = result["pandasai_prompt"]
        logger.info(f"Generated PandasAI prompt: {pandasai_prompt}")
        selected_columns = result["selected_columns"]
    except Exception as e:
        logger.error(f"Failed to generate PandasAI prompt: {e}")
        return None

    # Keep only the columns ChatGPT picked
    df_selected = df_raw[selected_columns]

    # Use pandasai DataFrame to execute the prompt
    try:
        df = pai.DataFrame(df_selected)
        cleaned_output = df.chat(pandasai_prompt)
        logger.info("PandasAI data cleaning completed successfully.")
    except Exception as e:
        logger.error(f"PandasAI execution failed: {e}")
        return None

    return cleaned_output


async def main() -> None:
    # 1 ) Load local JSON file
    with open("test1.json", "r", encoding="utf-8") as f:
        x_data: List[Dict[str, Any]] = json.load(f)
        print(f"Loaded {len(x_data)} records from test1.json")

    # 2 ) Define the user request
    user_request = (
        "Please find users on X who are interested in AI Agents and send me back "
        "the corresponding user name and link to that tweet."
    )

    # 3 ) Invoke the cleaning pipeline
    cleaned_output = await clean_raw_data(user_request, x_data)

    # 4 ) Show the result
    print("\n=== Cleaned Output ===")
    print(cleaned_output)

if __name__ == "__main__":
    asyncio.run(main())
