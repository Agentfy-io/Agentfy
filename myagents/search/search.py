import re
from exa_py import Exa
from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX


@function_tool(
    name_override="search_tool", 
    description_override="Search the web and find the most relevant information."
)
async def search_tool(query: str, num_results: int = None) -> str:    
    # Handle default value inside the function
    if num_results is None:
        num_results = 2
        
    exa = Exa(api_key = "20157907-df8c-4444-a0a2-12e65875ee20")   

    raw_result = exa.search_and_contents(
        query,
        text=True,
        num_results=num_results
    )
    
    # Extract only the IDs from the search results
    try:
        # First, see if we can access the results directly as attributes
        if hasattr(raw_result, 'results'):
            results = raw_result.results
        elif hasattr(raw_result, 'data') and hasattr(raw_result.data, 'results'):
            results = raw_result.data.results
        else:
            # Try converting to a dictionary if it supports it
            try:
                result_dict = vars(raw_result)
                if 'data' in result_dict and 'results' in result_dict['data']:
                    results = result_dict['data']['results']
                else:
                    # Fallback: just return the string representation
                    return f"Results: {str(raw_result)}"
            except:
                # Last resort: just return the string representation
                return f"Results: {str(raw_result)}"
        
        if not results or len(results) == 0:
            return "No results found."
            
        # Extract and format IDs
        extracted_ids = []
        for i, result in enumerate(results, 1):
            # Try to get the ID attribute or fall back to a different approach
            if hasattr(result, 'id'):
                result_id = result.id
            elif hasattr(result, 'url'):
                result_id = result.url
            else:
                # Try dictionary access
                try:
                    result_dict = vars(result)
                    result_id = result_dict.get('id', 'No ID available')
                except:
                    result_id = "No ID available"
                    
            extracted_ids.append(f"{i}. {result_id}")
        
        return "\n".join(extracted_ids)
    except Exception as e:
        # If there's any error processing the results, return the error and the raw result type
        return f"Error extracting ids: {str(e)}\nType of raw_result: {type(raw_result)}"


search_agent = Agent(
    name="Search Agent",
    handoff_description="A helpful agent that can search the web and find the most relevant information.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a search agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer.
    2. Use the search tool to search the web and find the most relevant information. Do not rely on your own knowledge.
    3. If you cannot answer the question, transfer back to the triage agent.""",
    tools=[search_tool],
)