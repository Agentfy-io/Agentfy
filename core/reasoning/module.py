# -*- coding: utf-8 -*-
"""
@file: agentfy/core/reasoning/module.py
@desc: Reasoning module for analyzing user input and generating corresponding workflows.
@auth: Callmeiks
"""
import json
from typing import Any, Dict, List, Optional, Tuple
import uuid
from datetime import datetime

from common.utils.logging import get_logger
from common.ais.chatgpt import ChatGPT
from config import settings
from common.exceptions.exceptions import AnalysisError, ChatGPTAPIError
from common.models.workflows import WorkflowDefinition, MissingParameter,  ParameterConflict, WorkflowStep, Parameter, ParameterValidationResult

logger = get_logger(__name__)


class ReasoningModule:
    """
    Simplified Reasoning Module that uses ChatGPT to analyze user requests
    and determine the appropriate workflow of sub-agents.
    """

    def __init__(self):
        """Initialize the reasoning module with configuration."""
        self.config = settings
        self.chatgpt = ChatGPT()

    async def analyze_request_and_build_workflow(self,
                                                 user_request: str,
                                                 agent_registry: Dict[str, Any],
                                                 chat_history: List[Dict[str, Any]] = None,
                                                 existing_workflow: Dict[str, Any] = None) -> Tuple[WorkflowDefinition, ParameterValidationResult]:
        """
        Analyze user request and build workflow using ChatGPT.
        Handles both new requests and parameter updates for existing workflows.

        Args:
            user_request: The user's request text
            agent_registry: Registry of available agents and functions
            chat_history: Optional chat history for context
            existing_workflow: Optional existing workflow to update

        Returns:
            Tuple[WorkflowDefinition, List[MissingParameter]]:
                - Workflow definition with steps
                - List of missing parameters (empty if none)

        Raises:
            AnalysisError: If analysis fails
        """
        try:
            if existing_workflow:
                logger.info("Analyzing parameter update for existing workflow")
                # This is a parameter update for an existing workflow
                workflow_data = await self._update_workflow_parameters(
                    user_request,
                    existing_workflow,
                    agent_registry
                )
            else:
                logger.info("Analyzing new user request")
                # This is a new request
                workflow_data = await self._create_new_workflow(
                    user_request,
                    agent_registry,
                    chat_history
                )

            # Convert to proper model objects
            workflow = self._convert_to_workflow_definition(workflow_data)
            missing_parameters = self._extract_missing_parameters(workflow_data)
            parameter_conflicts = self._extract_parameter_conflicts(workflow_data)

            # Create parameter validation result
            parameter_validation_result = ParameterValidationResult(
                is_valid=False if missing_parameters or parameter_conflicts else True,
                missing_required_parameters=missing_parameters,
                parameter_conflicts=parameter_conflicts
            )

            return workflow, parameter_validation_result

        except Exception as e:
            logger.error(f"Error analyzing request: {str(e)}")
            raise AnalysisError(f"Failed to analyze request: {str(e)}")

    async def _create_new_workflow(self,
                                   user_request: str,
                                   agent_registry: Dict[str, Any],
                                   chat_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new workflow based on user request.

        Args:
            user_request: The user's request text
            agent_registry: Registry of available agents and functions
            chat_history: Optional chat history for context

        Returns:
            Dict[str, Any]: New workflow definition
        """
        # Prepare the prompt for ChatGPT
        system_message = self._create_system_message(agent_registry)
        user_message = self._create_user_message(user_request, chat_history)

        # Call ChatGPT API
        workflow = await self.chatgpt.chat(system_message, user_message)

        logger.info("Successfully generated new workflow from ChatGPT")
        return workflow

    async def _update_workflow_parameters(self,
                                          user_input: str,
                                          existing_workflow: Dict[str, Any],
                                          agent_registry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing workflow with parameters from user input.

        Args:
            user_input: The user's input containing parameters
            existing_workflow: The existing workflow to update
            agent_registry: Registry of available agents and functions

        Returns:
            Dict[str, Any]: Updated workflow definition
        """
        # Prepare the prompt for ChatGPT
        system_message = self._create_parameter_update_system_message(agent_registry)
        user_message = self._create_parameter_update_user_message(user_input, existing_workflow)

        # Call ChatGPT API
        updated_workflow = await self.chatgpt.chat(system_message, user_message)

        logger.info("Successfully updated workflow parameters")
        return updated_workflow

    def _create_system_message(self, agent_registry: Dict[str, Any]) -> str:
        """Create the system message with agent registry for ChatGPT."""
        return f"""
        You are an AI assistant that analyzes user requests and creates workflows using available agents.

        You have access to the following agents and their functions:
        {json.dumps(agent_registry, indent=2)}

        Your task is to:
        1. Understand the user's request
        2. Identify the appropriate agents and functions needed to fulfill the request
        3. Create a workflow with the necessary steps in the correct order
        4. Identify any missing parameters needed only for the first step of the workflow
        5. If there are any parameter conflicts, include them in the parameter_conflicts array

        Return ONLY a JSON object with the following structure:
        {{
            "workflow_id": "unique-id",
            "name": "Workflow name",
            "description": "Workflow description",
            "steps": [
                {{
                    "step_id": "step1",
                    "agent_id": "agent-id",
                    "function_id": "function-id",
                    "description": "Step description",
                    "parameters": {{
                        "param1": "value1",
                        "param2": "value2"
                    }}
                }}
            ],
            "missing_parameters": [
                {{
                    "name": "parameter-name",
                    "description": "Parameter description",
                    "type": "string/number/boolean",
                    "required": true/false,
                    "function_id": "function-id",  // Indicate which function needs this parameter
                    "step_id": "step1"  // Indicate which step needs this parameter
                }}
            ]
            "parameter_conflicts": [
                {{
                    "parameter1": "param1",
                    "function_id": "function-id",
                    "step_id": "step1",
                    "reason": "Conflict reason",
                    "resolution": "Resolution suggestion"  // Optional
                }},
                {{
                    "parameter2": "param2",
                    "function_id": "function-id",
                    "step_id": "step1",
                    "reason": "Conflict reason",
                    "resolution": "Resolution suggestion"  // Optional
                }}
            ]
        }}

        The workflow should be as efficient as possible, using only the necessary steps to complete the user's request.
        If there are parameters missing that would be needed from the user, include them in the missing_parameters array.
        If there are any parameter conflicts, include them in the parameter_conflicts array with a reason and resolution suggestion.
        """

    def _create_parameter_update_system_message(self, agent_registry: Dict[str, Any]) -> str:
        """Create the system message for parameter updates."""
        return f"""
        You are an AI assistant that updates workflow parameters based on user input and existing workflows.

        Your task is to:
        1. Analyze the user's input to match the missing parameters for the first step (step 1) of the workflow
        2. check if the missing parameters provided by user are valid (e.g., type, required)
        3. If the parameters are valid, Update the existing workflow by applying these parameter values to step 1
        4. If any parameters are still missing or invalid, include them in the missing_parameters array

        Return ONLY a JSON object with the following structure:
        {{
            "workflow_id": "existing-workflow-id",  // Preserve the original workflow ID
            "name": "Workflow name",  // Preserve the original name
            "description": "Workflow description",  // Preserve the original description
            "steps": [
                {{
                    "step_id": "step1",
                    "agent_id": "agent-id",
                    "function_id": "function-id",
                    "description": "Step description",
                    "parameters": {{
                        "param1": "updated-value1",  // Update with new values from user input
                        "param2": "value2"
                    }}
                }}
            ],
            "missing_parameters": [
                {{
                    "name": "parameter-name",
                    "description": "Parameter description",
                    "type": "string/number/boolean",
                    "required": true/false,
                    "function_id": "function-id", 
                    "step_id": "step1"  
                }},
                {{
                    "name": "another-parameter-name",
                    "description": "Another parameter description",
                    "type": "string/number/boolean",
                    "required": true/false,
                    "function_id": "function-id", 
                    "step_id": "step1"  
                }}
            ]
            "parameter_conflicts": [
                {{
                    "parameter1": "param1",
                    "function_id": "function-id",
                    "step_id": "step1",
                    "reason": "Conflict reason",
                    "resolution": "Resolution suggestion"  // Optional
                }},
                {{
                    "parameter2": "param2",
                    "function_id": "function-id",
                    "step_id": "step1",
                    "reason": "Conflict reason",
                    "resolution": "Resolution suggestion"  // Optional
                }}
            ]
        }}

        FOCUS ONLY ON STEP 1 of the workflow. If all required parameters for step 1 have been provided, 
        the missing_parameters array should be empty. If a parameter value provided by the user is still invalid, 
        put in the parameter_conflicts array with a reason and resolution suggestion.
        """

    def _create_user_message(self, user_request: str, chat_history: List[Dict[str, Any]] = None) -> str:
        """Create the user message with request and chat history for ChatGPT."""
        message = f"User Request: {user_request}\n\n"

        if chat_history:
            message += "Chat History:\n"
            for entry in chat_history[-5:]:  # Include only the last 5 messages for context
                sender = "User" if entry.get("sender") == "USER" else "Assistant"
                message += f"{sender}: {entry.get('content')}\n"

        return message

    def _create_parameter_update_user_message(self, user_input: str, existing_workflow: Dict[str, Any]) -> str:
        """Create the user message for parameter updates."""
        return f"""
        User Input: {user_input}

        Existing Workflow:
        {json.dumps(existing_workflow, indent=2)}

        Please update the workflow by checking if the user input provides any missing parameters for the first step (step 1) of the workflow.
        Focus ONLY on step 1 parameters.
        If any parameters for step 1 are still missing, keep them in the missing_parameters array.
        If any provided parameters are invalid, explain why in the missing_parameters description.
        """

    def _convert_to_workflow_definition(self, workflow_data: Dict[str, Any]) -> WorkflowDefinition:
        """Convert raw workflow data to WorkflowDefinition object."""
        # Create WorkflowStep objects
        steps = []
        for step_data in workflow_data.get("steps", []):
            step = WorkflowStep(
                step_id=step_data.get("step_id", str(uuid.uuid4())),
                agent_id=step_data.get("agent_id", ""),
                function_id=step_data.get("function_id", ""),
                description=step_data.get("description", ""),
                parameters=step_data.get("parameters", {})
            )
            steps.append(step)

        # Create WorkflowDefinition
        workflow = WorkflowDefinition(
            workflow_id=workflow_data.get("workflow_id", str(uuid.uuid4())),
            name=workflow_data.get("name", "Untitled Workflow"),
            description=workflow_data.get("description", ""),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            steps=steps,
            output_format="json"
        )

        return workflow

    def _extract_missing_parameters(self, workflow_data: Dict[str, Any]) -> List[MissingParameter]:
        """Extract missing parameters from workflow data."""
        missing_params = []

        for param_data in workflow_data.get("missing_parameters", []):
            missing_param = MissingParameter(
                name=param_data.get("name", ""),
                type=param_data.get("type", "string"),
                description=param_data.get("description", ""),
                required=param_data.get("required", True),
                function_id=param_data.get("function_id", ""),
                step_id=param_data.get("step_id", "step1")
            )
            missing_params.append(missing_param)

        return missing_params

    def _extract_parameter_conflicts(self, workflow_data):
        """Extract parameter conflicts from workflow data."""
        conflicts = []

        for conflict_data in workflow_data.get("parameter_conflicts", []):
            conflict = ParameterConflict(
                parameter=conflict_data.get("parameter1", ""),
                function_id=conflict_data.get("function_id", ""),
                step_id=conflict_data.get("step_id", "step1"),
                reason=conflict_data.get("reason", ""),
                resolution=conflict_data.get("resolution", None)
            )
            conflicts.append(conflict)

        return conflicts