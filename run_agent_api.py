from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
import json
import os
from typing import Dict, List, Any, Optional

# Import your modules
from core.perception.module import PerceptionModule
from core.memory.module import MemoryModule
from core.reasoning.module import ReasoningModule
from core.action.module import ActionModule
from common.models.messages import UserInput, ChatMessage
from common.exceptions.exceptions import SocialMediaAgentException

app = FastAPI(title="Social Media Agent API")


# Models for API requests and responses
class ProcessRequestModel(BaseModel):
    text: str
    files: Optional[List[Dict[str, Any]]] = None
    user_id: str
    session_id: Optional[str] = None


class WorkflowStatusModel(BaseModel):
    workflow_id: str


class ParameterUpdateModel(BaseModel):
    workflow_id: str
    parameters: Dict[str, Any]


# Module instances
perception = PerceptionModule()
memory = MemoryModule()
reasoning = ReasoningModule()
action = ActionModule()


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

@app.post("/process")
async def process_request(request: ProcessRequestModel, background_tasks: BackgroundTasks):
    """Process a user request and build a workflow."""
    try:
        # 1. Create UserInput model
        user_input = UserInput(
            text=request.text,
            files=request.files,
            metadata={
                "user_id": request.user_id,
                "session_id": request.session_id or request.user_id,
                "timestamp": None,  # Will be set by the model
                "source": "api"
            }
        )

        # 2. Validate and sanitize input
        validation_result = await perception.validate_input(user_input)
        if not validation_result.is_valid:
            return {"status": "error", "errors": validation_result.errors}

        # 2. Get chat history
        chat_history = await memory.get_user_chat_history(request.user_id)

        # Add request to chat history
        chat_message = ChatMessage(
            sender="USER",
            content=request.text,
            metadata={"source": "api"}
        )
        await memory.add_chat_message(request.user_id, chat_message)

        # Get agent registry
        agent_registry = get_agent_registry()

        # Analyze request and build workflow
        workflow = await reasoning.analyze_request_and_build_workflow(
            request.text,
            agent_registry,
            [msg.dict() for msg in chat_history]
        )

        # Check for missing parameters
        if workflow.get("missing_parameters"):
            # Store workflow in memory
            await memory.store_agent_knowledge("workflow", workflow["workflow_id"], workflow)

            # Return workflow with missing parameters
            return {
                "status": "PARAMETERS_REQUIRED",
                "workflow_id": workflow["workflow_id"],
                "missing_parameters": workflow["missing_parameters"]
            }

        # Execute workflow in background
        background_tasks.add_task(execute_workflow_task, workflow, request.user_id)

        return {
            "status": "PROCESSING",
            "workflow_id": workflow["workflow_id"],
            "message": "Request is being processed"
        }

    except SocialMediaAgentException as e:
        return {"status": "error", "message": e.message, "details": e.details}

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def execute_workflow_task(workflow: Dict[str, Any], user_id: str):
    """Background task to execute a workflow."""
    try:
        # Execute workflow
        result = await action.execute_workflow(workflow)

        # Store result
        await memory.store_agent_knowledge("workflow_result", workflow["workflow_id"], result)

        # Add result to chat history
        output_message = f"Workflow completed with status: {result['status']}"
        if result["status"] == "COMPLETED":
            output_message += "\n\nResults summary:\n"
            for step_id, output in result["output"].items():
                output_message += f"- {workflow['steps'][int(step_id)]['description']}: Success\n"

        chat_message = ChatMessage(
            sender="AGENT",
            content=output_message,
            metadata={"workflow_id": workflow["workflow_id"]}
        )
        await memory.add_chat_message(user_id, chat_message)

    except Exception as e:
        # Log error
        print(f"Error executing workflow: {str(e)}")

        # Add error to chat history
        chat_message = ChatMessage(
            sender="AGENT",
            content=f"Error executing workflow: {str(e)}",
            metadata={"workflow_id": workflow["workflow_id"], "error": True}
        )
        await memory.add_chat_message(user_id, chat_message)


@app.get("/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get the status of a workflow."""
    try:
        # Check if workflow is active
        if workflow_id in action.active_workflows:
            return action.active_workflows[workflow_id]

        # Try to get from memory
        result = await memory.retrieve_agent_knowledge("workflow_result", workflow_id)
        if result:
            return {"status": "COMPLETED", "result": result}

        workflow = await memory.retrieve_agent_knowledge("workflow", workflow_id)
        if workflow:
            return {"status": "PENDING", "workflow": workflow}

        return {"status": "NOT_FOUND"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflow/parameters")
async def update_workflow_parameters(update: ParameterUpdateModel, background_tasks: BackgroundTasks):
    """Update parameters for a workflow and execute it."""
    try:
        # Get workflow from memory
        workflow = await memory.retrieve_agent_knowledge("workflow", update.workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Update parameters
        for param_name, param_value in update.parameters.items():
            for step in workflow["steps"]:
                if param_name in step["parameters"]:
                    step["parameters"][param_name] = param_value

        # Clear missing parameters if all are provided
        workflow["missing_parameters"] = [
            p for p in workflow.get("missing_parameters", [])
            if p["name"] not in update.parameters
        ]

        # Store updated workflow
        await memory.store_agent_knowledge("workflow", workflow["workflow_id"], workflow)

        # If no more missing parameters, execute workflow
        if not workflow["missing_parameters"]:
            # Execute workflow in background
            background_tasks.add_task(execute_workflow_task, workflow, update.user_id)

            return {
                "status": "PROCESSING",
                "workflow_id": workflow["workflow_id"],
                "message": "Workflow is being executed with updated parameters"
            }
        else:
            return {
                "status": "PARAMETERS_REQUIRED",
                "workflow_id": workflow["workflow_id"],
                "missing_parameters": workflow["missing_parameters"]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Social Media Agent API is running"}


if __name__ == "__main__":
    import uvicorn
    # run on 127.0.0.1
    uvicorn.run(app, host="0.0.0.0", port=8000)