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

class MissingParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool
    function_id: str
    step_id: str
    suggestions: Optional[List[Any]] = None

class ParameterConflict(BaseModel):
    parameter: str
    function_id: str
    step_id: str
    reason: str
    resolution: Optional[str] = None

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

class WorkflowDefinition(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    steps: List[WorkflowStep]
    output_format: str = "json"

class ParameterValidationResult(BaseModel):
    is_valid: bool # True if all parameters are valid
    missing_required_parameters: List[MissingParameter] = None
    recommended_parameters: List[Parameter] = None
    parameter_conflicts: List[ParameterConflict] = None

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

class ExecutionResult(BaseModel):
    workflow_id: str
    status: Literal["COMPLETED", "FAILED", "PAUSED", "CANCELLED"]
    start_time: datetime
    end_time: Optional[datetime] = None
    step_results: Dict[str, StepResult] = None
    outputs: Dict[str, Any] = None
    errors: List[ExecutionError] = None
    metrics: ExecutionMetrics