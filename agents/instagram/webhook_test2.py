import traceback
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
import json
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, List, Any, Optional
from common.models.workflows import ParameterValidationResult, WorkflowDefinition
from config import settings
from core.perception.module import PerceptionModule
from core.memory.module import MemoryModule
from core.reasoning.module import ReasoningModule
from core.action.module import ActionModule
from common.models.messages import UserInput, ChatMessage
from common.exceptions.exceptions import SocialMediaAgentException
from agents.instagram.interactive import send_direct_message

# Configure logging to terminal and file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('webhooktest2.log'),  # Log to file for persistence
        logging.StreamHandler()  # Log to terminal
    ]
)

app = FastAPI()

"""
curl -X POST https://xxxxxx.ngrok-free.app/callback \
  -H "Content-Type: application/json" \
  -d '{"field":"messages","value":{"sender":{"id":"12334"},"recipient":{"id":"23245"},"timestamp":"1527459824","message":{"mid":"random_mid","text":"随机查找 1 个 Instagram 上参与度超过 1 万的热门 AI 产品"}}}'
"""



perception = PerceptionModule()
memory = MemoryModule()
reasoning = ReasoningModule()
action = ActionModule()

VERIFY_TOKEN = "Test123"

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

async def execute_workflow_task(workflow: WorkflowDefinition, user_id: str, param_validation: ParameterValidationResult):
    """Background task to execute a workflow."""
    try:
        # Execute workflow
        results = []
        async for r in action.execute_workflow(workflow, param_validation):
            results.append(r)
        
        result = results[-1].to_dict() if results else {"status": "ERROR", "output": {}}
        logging.info(f"execute_workflow_task result: {result}")

        # Add result to chat history
        output_message = f"Workflow completed with status: {result['status']}"
        if result["status"] == "COMPLETED":
            output_message += "\n\nResults summary:\n"
            for step_id, output in result["output"].items():
                output_message += f"- {workflow['steps'][int(step_id)]['description']}: Success\n"

        chat_message = ChatMessage(
            sender="AGENT",
            content=output_message,
            metadata={"workflow_id": workflow.workflow_id}
        )
        await memory.add_chat_message(user_id, "AGENT", "USER", chat_message)
        logging.info(f"execute_workflow_task output_message: {output_message}")
        send_direct_message(user_id, output_message)

    except Exception as e:
        # Log error
        print(f"Error executing workflow: {str(e)}")
        logging.error(f"Error in webhook_event:\n{traceback.format_exc()}")

        # Add errors to chat history
        chat_message = ChatMessage(
            sender="AGENT",
            content=f"Error executing workflow: {str(e)}",
            metadata={"workflow_id": workflow.workflow_id, "error": True}
        )
        await memory.add_chat_message(user_id, "AGENT", "USER", chat_message)

        

@app.get("/callback")
async def webhook_verify(hub_mode: str, hub_verify_token: str, hub_challenge: str):
    try:
        logging.info(f"Received GET request: hub.mode={hub_mode}, hub.verify_token={hub_verify_token}, hub.challenge={hub_challenge}")
        if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
            logging.info("Webhook verification successful")
            return hub_challenge
        else:
            logging.error("Verification failed: Invalid mode or token")
            return {"error": "Invalid mode or token"}, 403
    except Exception as e:
        logging.error(f"Error in webhook_verify: {str(e)}")
        return {"error": "Internal server error"}, 500

@app.post("/callback")
async def webhook_event(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        logging.info(f"Received POST request: {data}")
        
        message_field = data["field"]
        message_value = data["value"]
        message_text = message_value["message"]["text"]
        message_sender_id = message_value["sender"]["id"]

        user_input = UserInput(
            text=message_text,
            files=[],
            metadata={
                "user_id": message_sender_id,
                "session_id": message_sender_id,
                "source": "api"
            }
        )

        validation_result, _ = await perception.validate_input(user_input)
        logging.info(f"validation_result: {validation_result}")
        if not validation_result.is_valid:
            return {"status": "error", "errors": validation_result.errors}

        chat_history = await memory.get_user_chat_history(message_sender_id)
        chat_message = ChatMessage(
            sender="USER",
            content=message_text,
            metadata={"source": "api"}
        )
        await memory.add_chat_message(message_sender_id, "AGENT", "USER", chat_message)

        agent_registry = await get_agent_registry()
        workflow, param_result, reasoning_cost = await reasoning.analyze_request_and_build_workflow(
            user_input,
            agent_registry,
            chat_history
        )

        logging.info(f"workflow: {workflow.to_dict()}")
        if param_result.missing_required_parameters:
            return {
                "status": "PARAMETERS_REQUIRED",
                "missing_parameters": param_result.missing_required_parameters
            }

        background_tasks.add_task(execute_workflow_task, workflow, message_sender_id, param_result)

        return {
            "status": "PROCESSING",
            "workflow_id": workflow.workflow_id,
            "message": "Request is being processed"
        }

    except SocialMediaAgentException as e:
        logging.error(f"Error in webhook_event:\n{traceback.format_exc()}")
        return {"status": "error", "message": e.message, "details": e.details}

    except Exception as e:
        logging.error(f"Error in webhook_event: {str(e)}")
        logging.error(f"Error in webhook_event:\n{traceback.format_exc()}")
        return {"error": "Internal server error"}, 500

@app.get("/")
async def home():
    logging.info("Received request to root endpoint")
    return "Server is running!"

if __name__ == "__main__":
    import uvicorn
    # run on 127.0.0.1
    uvicorn.run(app, host="0.0.0.0", port=8000)