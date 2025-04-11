# -*- coding: utf-8 -*-
"""
@file: agentfy/core/action/module.py
@desc: Simplified Action Module that executes workflows by finding and calling agent functions,
@auth(s): Callmeiks
"""
import importlib
import inspect
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from common.exceptions.exceptions import WorkflowExecutionError, StepExecutionError
from common.models.workflows import (
    WorkflowDefinition, WorkflowStep, ParameterValidationResult, StepResult,
    ExecutionResult, StepMetrics, ExecutionMetrics, ExecutionError
)
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)


class ActionModule:
    """
    Simplified Action Module that executes workflows by finding and calling agent functions,
    with proper parameter handling and step-to-step data flow.
    """

    def __init__(self):
        """Initialize the action module."""
        self.active_workflows = {}

        # load agen_registry json from agents.agent_registry route
        # self.agent_registry = self.load_agent_registry()

    async def execute_workflow(self, workflow: WorkflowDefinition,
                               param_validation: ParameterValidationResult) -> ExecutionResult:
        """
        Execute a workflow of agent functions with proper parameter flow.

        Args:
            workflow: The workflow definition with steps
            param_validation: Validation result for workflow parameters

        Returns:
            ExecutionResult: Execution results

        Raises:
            WorkflowExecutionError: If workflow execution fails
        """
        try:
            workflow_id = workflow.workflow_id
            logger.info(f"Preparing to execute workflow: {workflow_id}")

            # Check if all parameters are valid before starting
            if not param_validation.is_valid:
                logger.warning(f"Cannot execute workflow {workflow_id}: Missing required parameters")
                return ExecutionResult(
                    workflow_id=workflow_id,
                    status="FAILED",
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    step_results={},
                    outputs={},
                    errors=[ExecutionError(
                        error_code="MISSING_PARAMETERS",
                        message="Cannot execute workflow due to missing parameters",
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                        details={"missing_parameters": [p.dict() for p in param_validation.missing_required_parameters]}
                    )],
                    metrics=ExecutionMetrics(
                        total_duration=0,
                        step_durations={},
                        resource_utilization={},
                        api_calls=0,
                        data_processed=0
                    )
                )

            # Initialize execution context
            start_time = datetime.utcnow()
            context = {
                "workflow_id": workflow_id,
                "start_time": start_time,
                "variables": {},
                "step_results": {},
                "previous_step_output": None  # To track output from previous step
            }

            # Track step durations and results
            step_results = {}
            step_durations = {}
            total_api_calls = 0
            total_data_processed = 0
            errors = []

            # Register workflow as active
            self.active_workflows[workflow_id] = {
                "status": "RUNNING",
                "workflow": workflow,
                "context": context,
                "start_time": start_time
            }

            logger.info(f"Executing workflow: {workflow_id}")

            # Execute each step in sequence
            for step_index, step in enumerate(workflow.steps):
                step_id = step.step_id
                logger.info(f"Executing step {step_index + 1}/{len(workflow.steps)}: {step_id}")

                try:
                    # Prepare parameters for this step
                    step_parameters = self._prepare_step_parameters(
                        step,
                        context,
                        step_index
                    )

                    # Execute the step
                    step_start_time = datetime.utcnow()
                    step_result = await self._execute_step(step, step_parameters)
                    step_end_time = datetime.utcnow()

                    # Calculate duration
                    duration_ms = int((step_end_time - step_start_time).total_seconds() * 1000)
                    step_durations[step_id] = duration_ms

                    # Create full step result
                    full_step_result = StepResult(
                        step_id=step_id,
                        status="COMPLETED",
                        start_time=step_start_time,
                        end_time=step_end_time,
                        output=step_result,
                        metrics=StepMetrics(
                            duration_ms=duration_ms,
                            cpu_usage=0.1,  # Placeholder
                            memory_usage=0.1,  # Placeholder
                            api_calls=1,  # Placeholder
                            data_processed=len(str(step_result)) if step_result else 0
                        )
                    )

                    # Update context and tracking
                    context["step_results"][step_id] = full_step_result
                    context["previous_step_output"] = step_result
                    step_results[step_id] = full_step_result

                    # Update totals
                    total_api_calls += full_step_result.metrics.api_calls
                    total_data_processed += full_step_result.metrics.data_processed

                    logger.info(f"Step {step_id} completed successfully")

                except Exception as e:
                    logger.error(f"Error executing step {step_id}: {str(e)}")

                    # Create error
                    error = ExecutionError(
                        error_code="STEP_EXECUTION_ERROR",
                        message=f"Error executing step {step_id}: {str(e)}",
                        step_id=step_id,
                        timestamp=datetime.utcnow(),
                        recoverable=False,
                        details={"exception": str(e)}
                    )
                    errors.append(error)

                    # Create failed step result
                    failed_step_result = StepResult(
                        step_id=step_id,
                        status="FAILED",
                        start_time=step_start_time if 'step_start_time' in locals() else datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        error=error,
                        metrics=StepMetrics(
                            duration_ms=0,
                            cpu_usage=0,
                            memory_usage=0,
                            api_calls=0,
                            data_processed=0
                        )
                    )

                    # Update tracking
                    context["step_results"][step_id] = failed_step_result
                    step_results[step_id] = failed_step_result

                    # Stop workflow execution on error
                    break

            # Calculate total duration
            end_time = datetime.utcnow()
            total_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Determine workflow status
            workflow_status = "COMPLETED" if not errors else "FAILED"

            # Collect outputs
            outputs = {}
            for step_id, result in step_results.items():
                if result.status == "COMPLETED" and result.output:
                    outputs[step_id] = result.output

            # Create execution result
            execution_result = ExecutionResult(
                workflow_id=workflow_id,
                status=workflow_status,
                start_time=start_time,
                end_time=end_time,
                step_results=step_results,
                outputs=outputs,
                errors=errors,
                metrics=ExecutionMetrics(
                    total_duration=total_duration_ms,
                    step_durations=step_durations,
                    resource_utilization={},  # Placeholder
                    api_calls=total_api_calls,
                    data_processed=total_data_processed
                )
            )

            # Update workflow status
            self.active_workflows[workflow_id]["status"] = workflow_status
            self.active_workflows[workflow_id]["result"] = execution_result

            logger.info(f"Workflow {workflow_id} completed with status: {workflow_status}")
            return execution_result

        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            raise WorkflowExecutionError(f"Failed to execute workflow: {str(e)}")

    def _prepare_step_parameters(self, step: WorkflowStep, context: Dict[str, Any],
                                 step_index: int) -> Dict[str, Any]:
        """
        Prepare parameters for a step, considering workflow inputs and previous step outputs.

        Args:
            step: The step to prepare parameters for
            context: Execution context
            step_index: Index of the step in the workflow

        Returns:
            Dict[str, Any]: Prepared parameters for the step
        """
        # Start with the parameters defined in the step
        parameters = dict(step.parameters) if step.parameters else {}

        # For the first step, include input parameters from the workflow
        if step_index == 0:
            # Add any workflow input parameters that match this step's parameter names
            for param_name, param_value in context["parameters"].items():
                if param_name in parameters:
                    parameters[param_name] = param_value

        # For subsequent steps, include output from previous step
        else:
            previous_output = context["previous_step_output"]
            if previous_output:
                # If previous output is a dict, check for matching parameter names
                if isinstance(previous_output, dict):
                    for param_name, param_value in previous_output.items():
                        if param_name in parameters:
                            parameters[param_name] = param_value
                # If previous output is not a dict but step has a primary input parameter,
                # use the entire output as the value for that parameter
                elif len(parameters) == 1:
                    # Assume the single parameter is the primary input
                    primary_param = next(iter(parameters))
                    parameters[primary_param] = previous_output

        return parameters

    async def _execute_step(self, step: WorkflowStep, parameters: Dict[str, Any]) -> Any:
        """
        Execute a single workflow step.

        Args:
            step: The step to execute
            parameters: Parameters for the step

        Returns:
            Any: Step execution result

        Raises:
            StepExecutionError: If step execution fails
        """
        try:
            agent_id = step.agent_id
            function_id = step.function_id

            logger.info(f"Executing function: {agent_id}.{function_id}")

            # Find and load the agent module
            try:
                # Dynamic import based on agent ID
                # Format: platform_category (e.g., tiktok_crawler, twitter_analysis)
                platform, category = agent_id.split("_")
                module_path = f"...agents.{platform}.{category}"
                agent_module = importlib.import_module(module_path, package=__name__)

                # Find the function
                if not hasattr(agent_module, function_id):
                    raise StepExecutionError(f"Function {function_id} not found in {module_path}")

                function = getattr(agent_module, function_id)

                # Check if function is async
                if inspect.iscoroutinefunction(function):
                    result = await function(**parameters)
                else:
                    result = function(**parameters)

                return result

            except ImportError as e:
                # If module not found, try a simpler approach with mock functions
                logger.warning(f"Module import failed: {str(e)}, stopping execution")
                raise StepExecutionError(f"Failed to execute step: {str(e)}")

        except Exception as e:
            logger.error(f"Error executing step: {str(e)}")
            raise StepExecutionError(f"Failed to execute step: {str(e)}")

