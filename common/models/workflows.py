# -*- coding: utf-8 -*-
"""
@file: agentfy/common/models/workflows.py
@desc: workflow models, including workflow definition, execution result, and step metrics (for reasoning, action modules).
@auth: Callmeiks
"""
from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class Parameter(BaseModel):
    name: str
    value: Any
    type: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "function_id": self.function_id,
            "step_id": self.step_id,
            "suggestions": self.suggestions
        }

class MissingParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool
    function_id: str
    step_id: str
    suggestions: Optional[List[Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter,
            "function_id": self.function_id,
            "step_id": self.step_id,
            "reason": self.reason,
            "resolution": self.resolution
        }

class ParameterConflict(BaseModel):
    parameter: str
    function_id: str
    step_id: str
    reason: str
    resolution: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "agent_id": self.agent_id,
            "function_id": self.function_id,
            "description": self.description,
            "parameters": self.parameters,
            "conditional_execution": self.conditional_execution,
            "retry_policy": self.retry_policy,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
            "timeout": self.timeout
        }


class Entity(BaseModel):
    type: str
    value: str
    relevance: float
    metadata: Dict[str, Any] = None

class WorkflowStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    function_id: str
    description: str
    parameters: Dict[str, Any] = None
    conditional_execution: Optional[Dict[str, Any]] = None
    retry_policy: Optional[Dict[str, Any]] = None
    on_success: Optional[List[str]] = None
    on_failure: Optional[List[str]] = None
    timeout: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "agent_id": self.agent_id,
            "function_id": self.function_id,
            "description": self.description,
            "parameters": self.parameters,
            "conditional_execution": self.conditional_execution,
            "retry_policy": self.retry_policy,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
            "timeout": self.timeout
        }

class WorkflowDefinition(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    steps: List[WorkflowStep]
    output_format: str = "json"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "steps": [step.to_dict() for step in self.steps] if self.steps else None,
            "output_format": self.output_format
        }


class ParameterValidationResult(BaseModel):
    is_valid: bool # True if all parameters are valid
    missing_required_parameters: List[MissingParameter] = None
    recommended_parameters: List[Parameter] = None
    parameter_conflicts: List[ParameterConflict] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "missing_required_parameters": [
                param.to_dict() for param in self.missing_required_parameters
            ] if self.missing_required_parameters else None,
            "recommended_parameters": [
                param.to_dict() for param in self.recommended_parameters
            ] if self.recommended_parameters else None,
            "parameter_conflicts": [
                conflict.to_dict() for conflict in self.parameter_conflicts
            ] if self.parameter_conflicts else None
        }

class StepMetrics(BaseModel):
    duration_ms: int
    cpu_usage: float
    memory_usage: float
    api_calls: int
    data_processed: int

class ExecutionError(BaseModel):
    error_code: str
    message: str
    step_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    recoverable: bool = False
    details: Dict[str, Any] = None

class StepResult(BaseModel):
    step_id: str
    status: Literal["COMPLETED", "FAILED", "SKIPPED"]
    start_time: datetime
    end_time: datetime
    output: Optional[Any] = None
    error: Optional[ExecutionError] = None
    metrics: StepMetrics

class ExecutionMetrics(BaseModel):
    total_duration: int
    step_durations: Dict[str, int]
    resource_utilization: Dict[str, float]
    api_calls: int
    data_processed: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duration": self.total_duration,
            "step_durations": self.step_durations,
            "resource_utilization": self.resource_utilization,
            "api_calls": self.api_calls,
            "data_processed": self.data_processed
        }

class ExecutionResult(BaseModel):
    workflow_id: str
    status: Literal["COMPLETED", "FAILED", "PAUSED", "CANCELLED"]
    start_time: datetime
    end_time: Optional[datetime] = None
    step_results: Dict[str, StepResult] = None
    outputs: Dict[str, Any] = None
    errors: List[ExecutionError] = None
    metrics: ExecutionMetrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "step_results": {
                step_id: step_result.dict()
                for step_id, step_result in self.step_results.items()
            } if self.step_results else None,
            "outputs": self.outputs,
            "errors": [error.dict() for error in self.errors] if self.errors else None,
            "metrics": self.metrics.dict() if self.metrics else None
        }