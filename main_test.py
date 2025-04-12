import json
import os
import asyncio
from typing import List, Dict, Any, Optional

from common.models.messages import UserInput, UserMetadata
from core.memory.module import MemoryModule
from core.reasoning.module import ReasoningModule
from core.perception.module import PerceptionModule


# Load agent registry
async def get_agent_registry():
    registry_path = os.getenv("AGENT_REGISTRY_PATH", "agents_registry.json")
    try:
        with open(registry_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Registry file not found at {registry_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Invalid JSON in registry file at {registry_path}")
        return {}


# Added error handling and logging
async def process_user_input(user_input_text: str) -> Dict[str, Any]:
    try:
        # 1. Initialize the modules
        memory_module = MemoryModule()
        reasoning_module = ReasoningModule()
        perception_module = PerceptionModule()

        # 2. Create a user input object
        user_input = UserInput(
            text=user_input_text,
            files=[],
            metadata=UserMetadata(
                user_id="user_123",
                session_id="session_456",
                source="api"
            )
        )

        # 3. Process the user input
        valid_result = await perception_module.validate_input(user_input)

        if not valid_result.is_valid:
            print(f"Validation failed: {valid_result.error_message}")
            return {"success": False, "error": valid_result.error_message}

        # 4. If valid, proceed to memory and reasoning
        if valid_result.is_valid:
            # 5. get user chat history
            chat_history = await memory_module.get_user_chat_history(user_input.metadata.user_id)

            # 6. get agents registry
            agents_registry = await get_agent_registry()

            # 7. get workflow definition
            workflow_definition, param_result = await reasoning_module.analyze_request_and_build_workflow(
                user_input_text,
                agents_registry,
                chat_history
            )
            # 8. Execute the workflow

            # 9. Store the results in memory

            return {"success": True, "workflow": workflow_definition.workflow_id, "params": param_result.is_valid}

    except Exception as e:
        print(f"Error processing user input: {str(e)}")
        return {"success": False, "error": str(e)}


async def main():
    user_input_list = [
        "dm users who are interested in supporting donald trump on X, and this is the message i want to dm them: 'hey, i am a big fan of donald trump and i want to support him in the upcoming elections. do you want to join me?'",
    ]

    results = []
    for input_text in user_input_list:
        result = await process_user_input(input_text)
        results.append(result)
        print(f"Result: {json.dumps(result, indent=2)}")

    return results


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())