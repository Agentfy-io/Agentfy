# -*- coding: utf-8 -*-
"""
@file: agentfy/common/models/agents.py
@desc: agent models that is used for sub-agents registry and communication between sub-agents.
@auth: Callmeiks
"""
from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class AgentFunction(BaseModel):
    """
    Represents a function that a sub agent can perform.
    """
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: str
    dependencies: List[str] = None


class AgentInfo(BaseModel):
    """
    Represents the information of a sub agent, including its ID, platform, category, and functions.
    """
    id: str
    platform: str
    category: Literal["crawler", "analysis", "interactive"]
    name: str
    description: str
    functions: Dict[str, AgentFunction]
    configuration: Dict[str, Any] = None


class AgentMapping(BaseModel):
    """
    Represents the mapping of an agent to its functions and platforms.
    """
    agent_type: str
    platform: str
    category: str
    confidence: float
    required_functions: List[str]


class MessagePayload(BaseModel):
    """
    Represents the payload of a message sent between agents.
    """
    data: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None
    command: Optional[Dict[str, Any]] = None
    status: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class AgentMessage(BaseModel):
    """
    Represents a message sent between sub-agents.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_agent_id: str
    target_agent_id: Union[str, Literal["broadcast"]]
    message_type: Literal["DATA", "COMMAND", "STATUS", "ERROR"]
    payload: MessagePayload
    priority: Literal["LOW", "NORMAL", "HIGH", "CRITICAL"] = "NORMAL"
    expires_at: Optional[datetime] = None
    requires_acknowledgment: bool = False


class MessageDeliveryResult(BaseModel):
    """
    Represents the result of a message delivery attempt.
    """
    message_id: str
    delivered: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    receiver_id: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    acknowledged_at: Optional[datetime] = None