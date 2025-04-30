import base64
import time
from datetime import datetime
from io import StringIO, BytesIO

import pandas as pd
import streamlit as st
import json
import os
import asyncio
import random
import requests
from typing import Any, Dict, List
import smtplib
from email.mime.text import MIMEText

from common.models.messages import UserInput, UserMetadata, FormattedOutput, ChatMessage
from core.memory.module import MemoryModule
from core.reasoning.module import ReasoningModule
from core.perception.module import PerceptionModule
from core.action.module import ActionModule
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)

# Set page config
st.set_page_config(
    page_title="Agentfy - Social Media Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply some basic theming
st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 1rem;
        }
        .subheader {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session states
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "api_keys" not in st.session_state:
    st.session_state.api_keys = {
        "tikhub": "",
        "openai": "",
        "claude": ""
    }

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": "Welcome to Agentfy! I'm your Social Media Agent ready to help with your social media automation tasks."}
    ]

if "user_id" not in st.session_state:
    st.session_state.user_id = f"user_123"

if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{random.randint(1000, 9999)}"

if "chat_history_loaded" not in st.session_state:
    st.session_state.chat_history_loaded = False

if "show_settings" not in st.session_state:
    st.session_state.show_settings = False

if "total_costs" not in st.session_state:
    st.session_state.total_costs = {
        "input_cost": 0.0,
        "output_cost": 0.0,
        "total_cost": 0.0
    }

if "last_response_costs" not in st.session_state:
    st.session_state.last_response_costs = {
        "input_cost": 0.0,
        "output_cost": 0.0,
        "total_cost": 0.0
    }


# Function to validate TikHub API key
def validate_tikhub_api_key(api_key):
    try:
        response = requests.get(
            "https://api.tikhub.io/api/v1/tikhub/user/get_user_info",
            headers={"Authorization": f"Bearer {api_key}"}
        )

        if response.status_code == 200:
            data = response.json()
            user_data = data.get("user_data", {})
            return (
                    user_data.get("email_verified", False) and
                    not user_data.get("account_disabled", True)
            )
        return False
    except Exception as e:
        logger.error(f"Error validating TikHub API key: {str(e)}")
        return False


# Function to send feedback email
def send_feedback_email(feedback_text, user_id):
    try:
        # In production, use actual SMTP settings
        # Here's a placeholder that logs the email content
        logger.info(f"Feedback email from {user_id}: {feedback_text}")
        st.success("Feedback sent successfully! Thank you for your input.")
        return True
    except Exception as e:
        logger.error(f"Error sending feedback email: {str(e)}")
        st.error("Failed to send feedback. Please try again later.")
        return False


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
        user_id = st.session_state.user_id

        # Initialize modules with API keys
        memory_module = MemoryModule()
        reasoning_module = ReasoningModule(api_keys=st.session_state.api_keys)
        perception_module = PerceptionModule(api_keys=st.session_state.api_keys)
        action_module = ActionModule(api_keys=st.session_state.api_keys)

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

                # Add to files list
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
                session_id=st.session_state.session_id,
                source="streamlit"
            )
        )

        # Validate the input
        with st.spinner("Validating your request..."):
            valid_result, perception_cost = await perception_module.validate_input(user_input)

            # Update input cost
            st.session_state.last_response_costs["input_cost"] = perception_cost.get('input_cost')
            st.session_state.last_response_costs["output_cost"] = perception_cost.get("output_cost")
            st.session_state.last_response_costs["total_cost"] = perception_cost.get("total_cost")

        # If not valid, return formatted error message
        if not valid_result.is_valid:
            messages = "\n".join(error["message"] for error in valid_result.errors)
            output, output_cost = await perception_module.format_output(messages, user_input_text)

            # Update last_response_costs
            st.session_state.last_response_costs["input_cost"] += output_cost.get('input_cost')
            st.session_state.last_response_costs["output_cost"] += output_cost.get("output_cost")
            st.session_state.last_response_costs["total_cost"] += output_cost.get("total_cost")

            st.session_state.total_costs["input_cost"] += st.session_state.last_response_costs['input_cost']
            st.session_state.total_costs["output_cost"] += st.session_state.last_response_costs["output_cost"]
            st.session_state.total_costs["total_cost"] += st.session_state.last_response_costs["total_cost"]

            await memory_module.add_chat_message(user_id, "SYSTEM", "USER", output.content)
            return output.content

        # Load memory and registry for reasoning
        chat_history = await memory_module.get_user_chat_history(user_input.metadata.user_id)
        agents_registry = await get_agent_registry()

        # Generate a workflow and prepare parameters with progress indicator
        with st.spinner("Generating and preparing workflow..."):
            workflow_definition, param_result, reasoning_cost = await reasoning_module.analyze_request_and_build_workflow(
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
            perception_module = PerceptionModule(api_keys=st.session_state.api_keys)

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


# Authentication Gate
if not st.session_state.authenticated:
    st.markdown("""
    <div style='text-align: center'>
        <h1>Welcome to Agentfy</h1>
        <h3>Your AI-powered Social Media Agent</h3>
    </div>
    """, unsafe_allow_html=True)

    # Display logo with rounded corners
    logo_path = "images/logo2.jpg"
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()

    st.markdown(f"""
        <div style="text-align: center; padding-bottom: 1rem;">
            <img src="data:image/jpeg;base64,{logo_base64}" 
                 alt="Agentfy Logo" width="250" height="250"
                 style="border-radius: 20px; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
        </div>
    """, unsafe_allow_html=True)

    # Create a centered container
    _, center_col, _ = st.columns([1, 2, 1])

    with center_col:

        # Add some space
        st.write("")

        # Centered login container
        with st.container():
            # Centered sign in text
            st.markdown("<h4 style='text-align: center;'>Sign In</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;'>Please enter your TikHub API key to continue</p>",
                        unsafe_allow_html=True)

            # Form with centered elements
            with st.form("auth_form", clear_on_submit=False):
                api_key = st.text_input(
                    "TikHub API Key",
                    type="password",
                    placeholder="Enter your API key here"
                )

                # Centered button
                cols = st.columns([3, 2, 3])
                with cols[1]:
                    submit_button = st.form_submit_button("Verify & Continue")

                if submit_button:
                    if not api_key:
                        st.warning("Please enter your API key")
                    else:
                        with st.spinner("Verifying API key..."):
                            if validate_tikhub_api_key(api_key):
                                st.success("API key verified successfully!")
                                st.balloons()
                                time.sleep(2)
                                st.session_state.authenticated = True
                                st.session_state.api_keys["tikhub"] = api_key
                                st.rerun()
                            else:
                                st.error("Invalid API key or your account is not verified. Please check and try again.")

            # Centered help text
            st.markdown(
                "<div style='text-align: center;'>Don't have a TikHub API key? <a href='https://tikhub.io/register' target='_blank'>Sign up here</a></div>",
                unsafe_allow_html=True)

            # Add more descriptive text at the bottom
            st.write("")
            st.markdown(
                "<p style='text-align: center; font-size: 0.8rem; color: #666;'>Agentfy uses the Model Context Protocol (MCP) to coordinate agents for social media tasks.</p>",
                unsafe_allow_html=True)
else:
    # Main Application Layout

    # Sidebar Configuration
    with st.sidebar:
        st.markdown("<h2 class='subheader'>API Configuration</h2>", unsafe_allow_html=True)

        # API Keys Section
        with st.expander("API Keys", expanded=True):
            # Create a form for API keys
            with st.form("api_keys_form"):
                # TikHub API Key (already verified)
                tikhub_key = st.text_input(
                    "TikHub API Key",
                    value=st.session_state.api_keys["tikhub"],
                    type="password",
                    placeholder="Already verified"
                )

                # OpenAI API Key
                openai_key = st.text_input(
                    "OpenAI API Key",
                    value=st.session_state.api_keys["openai"],
                    type="password",
                    placeholder="Enter your OpenAI API key"
                )

                # Claude API Key
                claude_key = st.text_input(
                    "Claude API Key",
                    value=st.session_state.api_keys["claude"],
                    type="password",
                    placeholder="Enter your Claude API key"
                )

                # Save button
                save_button = st.form_submit_button("Save API Keys", use_container_width=True)

                if save_button:
                    # Update session state with new values
                    st.session_state.api_keys["tikhub"] = tikhub_key if tikhub_key else st.session_state.api_keys[
                        "tikhub"]
                    st.session_state.api_keys["openai"] = openai_key
                    st.session_state.api_keys["claude"] = claude_key

                    # Show success message
                    st.success("API keys saved successfully!")

                    # Add a small delay to show the success message
                    time.sleep(1.5)

                    # Refresh the page to apply changes
                    st.rerun()

        st.divider()

        # Chat History Section
        st.markdown("<h2 class='subheader'>Chat History</h2>", unsafe_allow_html=True)

        # Load user's chat history when app starts
        if not st.session_state.chat_history_loaded:
            memory_module = MemoryModule()
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
            # Create a scrollable container for chat history
            with st.container():
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

                    # Show "View full conversation" button if there are more messages
                    if len(messages) > 3:
                        st.button(f"View session {i + 1}", key=f"view_conv_{i}")

        for _ in range(20):
            st.write("")
        st.divider()

        # Settings & Feedback Button
        if st.button("Settings & Feedback"):
            st.session_state.show_settings = not st.session_state.show_settings
            st.rerun()

    # Main Content Area
    if st.session_state.show_settings:
        # Settings & Feedback Form
        st.markdown("<h1 class='main-header'>User Feedback</h1>", unsafe_allow_html=True)
        st.markdown("We appreciate your feedback! Please share your thoughts or suggestions to help us improve.")

        with st.form("feedback_form"):
            feedback_text = st.text_area("Your Feedback", height=200)
            submitted = st.form_submit_button("Submit Feedback")

            if submitted and feedback_text:
                success = send_feedback_email(feedback_text, st.session_state.user_id)
                if success:
                    st.session_state.show_settings = False
                    st.rerun()

        # Back to Chat button
        if st.button("Back to Chat"):
            st.session_state.show_settings = False
            st.rerun()
    else:
        # Chat Interface
        st.markdown("<h1 class='main-header'>Agentfy Social Media Assistant</h1>", unsafe_allow_html=True)

        # Display Total Costs
        with st.expander("Session Cost Tracker", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Input Cost", f"${st.session_state.total_costs['input_cost']:.4f}")
            with col2:
                st.metric("Total Output Cost", f"${st.session_state.total_costs['output_cost']:.4f}")
            with col3:
                st.metric("Total Cost", f"${st.session_state.total_costs['total_cost']:.4f}")

        # Display chat messages from history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                data = message.get("data")
                if data is not None and isinstance(data, pd.DataFrame):
                    st.dataframe(data, use_container_width=True)

        # File uploader
        uploaded_files = st.file_uploader("Upload files (optional)", accept_multiple_files=True)

        # User input
        if prompt := st.chat_input("How can I help with your social media tasks?"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)

            # Display assistant message container
            with st.chat_message("assistant"):
                message_placeholder = st.empty()

                # Reset last response costs
                st.session_state.last_response_costs = {
                    "input_cost": 0.0,
                    "output_cost": 0.0,
                    "total_cost": 0.0
                }

                # Process user input and get response
                response = run_async(process_user_input(prompt, uploaded_files))
                opener = response.get("opener", "")
                data_md = response.get("data")

                # Typing effect for opener
                full_opener = ""
                for i in range(0, len(opener), 5):
                    full_opener += opener[i:i + 5]
                    message_placeholder.markdown(full_opener + "▌")
                    time.sleep(0.01)
                message_placeholder.markdown(full_opener)

                # After opener, show result data
                if data_md is not None:
                    st.markdown("---")
                    st.markdown("### Result Preview (You can download the complete dataset below.)")

                    if data_md is not None:
                        st.dataframe(data_md, use_container_width=True)
                    else:
                        # If not parsable, just render markdown
                        st.markdown(data_md, unsafe_allow_html=True)

            # Update full assistant message to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": opener + "\n\n",
                "data": data_md if data_md is not None else "",
                "cost": st.session_state.last_response_costs.copy()
            })

            st.rerun()

# Footer
# st.markdown("---")
# st.caption("© 2025 Agentfy - Powered by Model Context Protocol (MCP)")
