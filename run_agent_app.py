import time
import streamlit as st
import json
import os
import asyncio
import random
from typing import Any

from common.models.messages import UserInput, UserMetadata, FormattedOutput, ChatMessage
from core.memory.module import MemoryModule
from core.reasoning.module import ReasoningModule
from core.perception.module import PerceptionModule
from core.action.module import ActionModule
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)

# Initialize the core modules
memory_module = MemoryModule()
reasoning_module = ReasoningModule()
perception_module = PerceptionModule()
action_module = ActionModule()

# Set page config
st.set_page_config(
    page_title="Social Media Agent",
    page_icon="🤖",
    layout="wide"
)


# Function to get the agent registry
async def get_agent_registry():
    registry_path = os.getenv("AGENT_REGISTRY_PATH", "agents_registry.json")
    try:
        with open(registry_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Registry file not found at {registry_path}")
        return {}
    except json.JSONDecodeError:
        st.error(f"Invalid JSON in registry file at {registry_path}")
        return {}


# Process user input
async def process_user_input(user_input_text: str, uploaded_files=None) -> Any:
    try:
        # Create user ID from session state if not exists
        if "user_id" not in st.session_state:
            st.session_state.user_id = f"user_{random.randint(1000, 9999)}"

        user_id = st.session_state.user_id

        # Generate random 4-digit number for output file
        num = str(random.randint(1000, 9999))
        final_result = None
        status_placeholder = st.empty()
        output_format = ""

        # Process uploaded files if any
        files = []
        if uploaded_files:
            for file in uploaded_files:
                # Save the file temporarily
                file_path = f"temp_{file.name}"
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())

                files.append({
                    "path": file_path,
                    "name": file.name,
                    "type": file.type
                })

        # Construct user input object
        user_input = UserInput(
            text=user_input_text,
            files=files,
            metadata=UserMetadata(
                user_id=user_id,
                session_id=st.session_state.get("session_id", f"session_{random.randint(1000, 9999)}"),
                source="streamlit"
            )
        )

        # Validate the input
        with st.spinner("Validating your request..."):
            valid_result = await perception_module.validate_input(user_input)

        # If not valid, return formatted error message
        if not valid_result.is_valid:
            messages = "\n".join(error["message"] for error in valid_result.errors)
            output = await perception_module.format_output(messages, user_input_text, "text")
            await memory_module.add_chat_message(user_id, "SYSTEM", "USER", output.content)
            return output.content

        # Load memory and registry for reasoning
        chat_history = await memory_module.get_user_chat_history(user_input.metadata.user_id)
        agents_registry = await get_agent_registry()

        # Generate a workflow and prepare parameters with progress indicator
        with st.spinner("Generating and preparing workflow..."):
            workflow_definition, param_result = await reasoning_module.analyze_request_and_build_workflow(
                user_input_text, agents_registry, chat_history
            )

            # Update reasoning cost
            st.session_state.last_response_costs["input_cost"] += reasoning_cost.get('input_cost')
            st.session_state.last_response_costs["output_cost"] += reasoning_cost.get("output_cost")
            st.session_state.last_response_costs["total_cost"] += reasoning_cost.get("total_cost")

        # Execute the workflow with progress indicator
        async for update in action_module.execute_workflow(workflow_definition, param_result):
            status = update.status
            if status == "RUNNING":
                status_placeholder.markdown(update.message)
            elif status == "COMPLETED":
                status_placeholder.empty()
                final_result = update.output.output
            else:
                output, output_cost = await perception_module.format_output(update.errors, user_input_text)

                logger.info("output at workflow cost: %s", output_cost)

                # Update output cost
                st.session_state.last_response_costs["input_cost"] += output_cost.get('input_cost')
                st.session_state.last_response_costs["output_cost"] += output_cost.get("output_cost")
                st.session_state.last_response_costs["total_cost"] += output_cost.get("total_cost")

                st.session_state.total_costs["input_cost"] += st.session_state.last_response_costs['input_cost']
                st.session_state.total_costs["output_cost"] += st.session_state.last_response_costs["output_cost"]
                st.session_state.total_costs["total_cost"] += st.session_state.last_response_costs["total_cost"]

                await memory_module.add_chat_message(user_id, "AGENT", "USER", output.content)
                return output.content

        # Clean up temporary files
        for file_info in files:
            if os.path.exists(file_info["path"]):
                os.remove(file_info["path"])

        # check the output type
        if type(final_result) == dict or type(final_result) == list:
            output_format = "json"
        else:

        # On success, return the result
        output, output_cost = await perception_module.format_output(final_result, user_input_text)

        # Update output cost
        st.session_state.last_response_costs["input_cost"] += output_cost.get('input_cost')
        st.session_state.last_response_costs["output_cost"] += output_cost.get("output_cost")
        st.session_state.last_response_costs["total_cost"] += output_cost.get("total_cost")

        st.session_state.total_costs["input_cost"] += st.session_state.last_response_costs['input_cost']
        st.session_state.total_costs["output_cost"] += st.session_state.last_response_costs["output_cost"]
        st.session_state.total_costs["total_cost"] += st.session_state.last_response_costs["total_cost"]

        await memory_module.add_chat_message(user_id, "AGENT", "USER", output.content)

        logger.info(f"Workflow executed successfully!")
        return output.content

    except Exception as e:
        logger.exception("Error in process_user_input")
        error_message = f"Internal error occurred: {str(e)}"

        # Initialize modules with API keys if not already done
        if 'perception_module' not in locals():

        output, output_cost = await perception_module.format_output(error_message, user_input_text)
        logger.info("output cost: %s", output_cost)

        st.session_state.last_response_costs["input_cost"] += output_cost['input_cost']
        st.session_state.last_response_costs["output_cost"] += output_cost['output_cost']
        st.session_state.last_response_costs["total_cost"] += output_cost['total_cost']

        st.session_state.total_costs["input_cost"] += st.session_state.last_response_costs['input_cost']
        st.session_state.total_costs["output_cost"] += st.session_state.last_response_costs["output_cost"]
        st.session_state.total_costs["total_cost"] += st.session_state.last_response_costs["total_cost"]

        if "user_id" in st.session_state:
            # Initialize memory module if not already done
            if 'memory_module' not in locals():
                memory_module = MemoryModule()
            await memory_module.add_chat_message(st.session_state.user_id, "SYSTEM", "USER", output.content)
        return output.content


# Function to run async functions in Streamlit
def run_async(func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(func)
    loop.close()
    return result


# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome to the Social Media Agent! How can I help you today?"}]

# Initialize session state for user ID and session ID
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user_{random.randint(1000, 9999)}"
if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{random.randint(1000, 9999)}"

# Main app layout
st.title("Social Media Agent")

# Sidebar with chat history
with st.sidebar:
    st.header("Chat History")

    # Load user's chat history when app starts
    if "chat_history_loaded" not in st.session_state:
        chat_history = run_async(memory_module.get_user_chat_history(st.session_state.user_id))
        if chat_history:
            st.session_state.chat_history = chat_history
        else:
            st.session_state.chat_history = []
        st.session_state.chat_history_loaded = True

    # Display chat history in sidebar
    if not st.session_state.chat_history:
        st.info("No previous conversations found.")
    else:
        for i, chat_session in enumerate(st.session_state.chat_history):
            if i > 0:  # Add separator between chat sessions
                st.divider()

            # Show session timestamp
            st.caption(f"Session: {chat_session.get('timestamp', 'Unknown date')}")

            # Show preview of conversation (first few messages)
            messages = chat_session.get('messages', [])
            for j, msg in enumerate(messages[:3]):  # Show only first 3 messages as preview
                sender = msg.get('sender', 'Unknown')
                content = msg.get('content', '')
                if len(content) > 50:  # Truncate long messages
                    content = content[:50] + "..."

                if sender == "USER":
                    st.text(f"You: {content}")
                else:
                    st.text(f"Agent: {content}")

            # Show "View more" button if there are more messages
            if len(messages) > 3:
                st.button(f"View full conversation {i + 1}", key=f"view_conv_{i}")

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# File uploader
# uploaded_files = st.file_uploader("Upload files (optional)", accept_multiple_files=True)

# Accept user input
if prompt := st.chat_input("What can I help you with?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process the input and get response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Processing your request...")

        # Process user input
        response = run_async(process_user_input(prompt))

        # Display the response with a typing effect
        full_response = ""
        response_text = str(response)

        # Create a typing effect
        for i in range(0, len(response_text), 5):
            chunk = response_text[i:i + 5]
            full_response += chunk
            message_placeholder.markdown(full_response + "▌")
            time.sleep(0.02)  # A faster typing effect for longer responses

        message_placeholder.markdown(full_response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response_text})

# Footer
# st.markdown("---")
# st.caption("© 2025 Social Media Agent - Powered by AI")