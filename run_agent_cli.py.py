import json
import os
import asyncio
import random
from typing import List, Dict, Any, Optional

from common.models.messages import UserInput, UserMetadata, FormattedOutput, ChatMessage
from core.memory.module import MemoryModule
from core.reasoning.module import ReasoningModule
from core.perception.module import PerceptionModule
from core.action.module import ActionModule
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)

# 1. Initialize the core modules
memory_module = MemoryModule()
reasoning_module = ReasoningModule()
perception_module = PerceptionModule()
action_module = ActionModule()
user_id = "user_123"

# Load agent registry from a local JSON file
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

# Process one user input
async def process_user_input(user_input_text: str) -> Any:
    try:
        # Construct a user input object
        user_input = UserInput(
            text=user_input_text,
            files=[],
            metadata=UserMetadata(
                user_id=user_id,
                session_id="session_456",
                source="terminal"
            )
        )
        #generate random 4 digit number
        num = str(random.randint(1000, 9999))

        # Validate the input
        valid_result = await perception_module.validate_input(user_input)

        # If not valid, return formatted error message
        if not valid_result.is_valid:
            messages = "\n".join(error["message"] for error in valid_result.errors)
            output = await perception_module.format_output(messages, "text")
            await memory_module.add_chat_message(user_id, "SYSTEM", "USER", output.content)
            return f"Your request is invalid. Please check the input format. (Error hint: {messages})"

        # Load memory and registry for reasoning
        chat_history = await memory_module.get_user_chat_history(user_input.metadata.user_id)
        agents_registry = await get_agent_registry()

        # Generate a workflow and prepare parameters
        workflow_definition, param_result = await reasoning_module.analyze_request_and_build_workflow(
            user_input_text, agents_registry, chat_history
        )

        # Execute the workflow
        execution_result = await action_module.execute_workflow(
            workflow_definition, param_result
        )

        # If execution failed, return error message
        if execution_result.status != "COMPLETED":
            output = await perception_module.format_output(execution_result.errors, "text")
            await memory_module.add_chat_message(user_id, "AGENT", "USER", output.content)
            return f"Your request could not be completed. Please try again later. (Error hint: STEP_EXECUTION_ERROR)"

        # On success, return the result
        output = await perception_module.format_output(execution_result.output, "json")
        await memory_module.add_chat_message(user_id, "AGENT", "USER", output.content)

        result = {"status": "success", "workflow": workflow_definition.to_dict(), "execution_result": execution_result.to_dict()}
        #save as json file
        with open(f"output_{num}.json", "w") as f:
            json.dump(result, f, indent=4)
        logger.info(f"Workflow executed successfully. Output saved to output_{num}.json")
        return output

    except Exception as e:
        logger.exception("Error in process_user_input")
        error_message = f"Internal error occurred: {str(e)}"
        output = await perception_module.format_output(error_message, "text")
        await memory_module.add_chat_message(user_id, "SYSTEM", "USER", output.content)
        return output

# Run continuous dialogue in terminal
async def main():
    print("🤖 Welcome to the Social Media Agent Terminal Interface!")
    print("Type 'exit' to quit.\n")

    while True:
        # Get user input from terminal
        user_text = input("👤 You: ").strip()

        if user_text.lower() in ["exit", "quit"]:
            print("👋 Session ended.")
            break

        # Process input and return result
        result = await process_user_input(user_text)
        print(f"🤖 Agent: {result}\n")

if __name__ == "__main__":
    asyncio.run(main())
