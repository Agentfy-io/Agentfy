from __future__ import annotations as _annotations

import asyncio
import sys
import os
import uuid

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    trace,
    InputGuardrailTripwireTriggered,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

# Import our custom agents
from myagents.search.search import search_agent
from myagents.tmdb.movie import movie_agent
from myagents.x.crawler import x_agent
from validator.guardrails import math_guardrail, politics_guardrail

# Create a triage agent
triage_agent = Agent(
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate specialized agent.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a helpful triaging agent. You can direct customers to specialized agents based on their needs.
    
    # Available specialized agents:
    1. Search Agent - For general web searches and finding information online
    2. Movie Database Agent - For movie-related queries, including finding information about specific movies
    3. X Agent - For X (Twitter) related queries, including finding information about specific users, tweets, and trending topics
    
    # Routine:
    1. Identify the customer's request.
    2. If it's related to movies or films, hand off to the Movie Database Agent.
    3. If it's related to X (Twitter), hand off to the X Agent.
    4. If it's a general information request or web search, hand off to the Search Agent.    
    5. For any other request, try to help directly or suggest which specialized agent would be most appropriate.""",
    handoffs=[search_agent, movie_agent, x_agent],
    input_guardrails=[math_guardrail, politics_guardrail],
)

# Setup cross-references between agents for handoffs
search_agent.handoffs.append(triage_agent)
movie_agent.handoffs.append(triage_agent)
x_agent.handoffs.append(triage_agent)

async def main():
    current_agent = triage_agent
    input_items: list[TResponseInputItem] = []
    context = {}  # No need for specific context in this demo

    # Use a random UUID for the conversation ID
    conversation_id = uuid.uuid4().hex[:16]

    print("Welcome to the AI Agent Demo!")
    print("You can:")
    print("- Ask general questions to be handled by the triage agent")
    print("- Get movie information with the movie agent")
    print("- Search X (Twitter) with the X agent")
    print("- Search the web with the search agent")
    print("- Type 'exit' to quit")
    print()

    while True:
        user_input = input("Enter your message: ")
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
            
        with trace("AI Agent Demo", group_id=conversation_id):
            input_items.append({"content": user_input, "role": "user"})
            try:
                result = await Runner.run(current_agent, input_items)
            except InputGuardrailTripwireTriggered:
                print("Guardrail tripped - as expected!")
                continue

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    print(
                        f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            input_items = result.to_input_list()
            current_agent = result.last_agent


if __name__ == "__main__":
    asyncio.run(main())
