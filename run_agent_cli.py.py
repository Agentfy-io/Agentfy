import json
import os
import asyncio
import random
from typing import Dict, Any, Optional, List

from common.models.messages import UserInput, UserMetadata
from core.memory.module import MemoryModule
from core.reasoning.module import ReasoningModule
from core.perception.module import PerceptionModule
from core.action.module import ActionModule
from common.utils.logging import setup_logger
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Set up logger
logger = setup_logger(__name__)

# Initialize core modules
memory_module = MemoryModule()
reasoning_module = ReasoningModule()
perception_module = PerceptionModule()
action_module = ActionModule()


# Load agent registry
async def get_agent_registry() -> Dict:
    """
    Load agent registry from local JSON file.
    Returns:
        Dictionary representing available agents.
    """
    registry_path = os.getenv("AGENT_REGISTRY_PATH", "agents_registry.json")
    try:
        with open(registry_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Registry file not found at {registry_path}")
        return {}
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON format in registry file at {registry_path}")
        return {}


# Main processing logic
async def process_user_input(user_input_text: str) -> Any:
    """
    Process user input from terminal and return result.

    Args:
        user_input_text: Raw string from user.
    Returns:
        Final response from the agent.
    """
    user_id = f"user_{random.randint(1000, 9999)}"
    session_id = f"session_{random.randint(1000, 9999)}"
    final_result = None

    try:
        # Build user input
        user_input = UserInput(
            text=user_input_text,
            files=[],
            metadata=UserMetadata(
                user_id=user_id,
                session_id=session_id,
                source="terminal"
            )
        )

        # Step 1: Validate input
        valid_result = await perception_module.validate_input(user_input)
        if not valid_result.is_valid:
            messages = "\n".join(error["message"] for error in valid_result.errors)
            output = await perception_module.format_output(messages, user_input_text,"text")
            await memory_module.add_chat_message(user_id, "SYSTEM", "USER", output.content)
            return f"❌ Invalid input:\n{messages}"

        # Step 2: Get chat history & agent registry
        chat_history = await memory_module.get_user_chat_history(user_id)
        agents_registry = await get_agent_registry()

        # Step 3: Build workflow
        workflow_definition, param_result = await reasoning_module.analyze_request_and_build_workflow(
            user_input_text, agents_registry, chat_history
        )

        # Step 4: Execute step-by-step with feedback
        async for update in action_module.execute_workflow(workflow_definition, param_result):
            if update.status == "RUNNING":
                continue
            elif update.status == "COMPLETED":
                final_result = update
            else:
                output = await perception_module.format_output(update.errors, user_input_text, "text")
                await memory_module.add_chat_message(user_id, "AGENT", "USER", output.content)
                return output.content

        # check the output type
        if type(final_result) == dict or type(final_result) == list:
            output_format = "json"
        else:
            output_format = "text"

        # Step 5: Format output and store logs
        output = await perception_module.format_output(final_result.output, user_input_text, output_format)
        await memory_module.add_chat_message(user_id, "AGENT", "USER", output.content)

        # Save workflow output to file
        filename = f"output_{random.randint(1000, 9999)}.json"
        with open(filename, "w") as f:
            json.dump({
                "status": "success",
                "workflow": workflow_definition.to_dict(),
                "execution_result": final_result.to_dict()
            }, f, indent=4)
        logger.info(f"✅ Workflow executed successfully. Saved to `{filename}`")

        return output.content

    except Exception as e:
        logger.exception("❌ Error in process_user_input")
        error_message = f"Internal error occurred: {str(e)}"
        output = await perception_module.format_output(error_message, user_input_text,"text")
        await memory_module.add_chat_message(user_id, "SYSTEM", "USER", output.content)
        return output.content


# Terminal interface
async def main():
    print("\n🤖 Welcome to the Social Media Agent Terminal!")
    print("Type your request below. Type 'exit' to quit.\n")

    while True:
        user_text = input("👤 You: ").strip()
        if user_text.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        response = await process_user_input(user_text)
        print(f"\n🤖 Agent: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
