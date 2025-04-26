# -*- coding: utf-8 -*-
"""
@file: agentfy/common/exceptions/exceptions.py
@desc: customized exceptions
@auth: Callmeiks
"""
from typing import Any, Dict, Optional

class SocialMediaAgentException(Exception):
    """Base exception class for all social media agent exceptions."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

# Perception Module Exceptions
class PerceptionException(SocialMediaAgentException):
    """Base exception for perception module."""
    pass

class InputValidationError(PerceptionException):
    """Raised when input validation fails."""
    pass

class SecurityCheckFailedError(PerceptionException):
    """Raised when security check fails."""
    pass

class FileValidationError(PerceptionException):
    """Raised when file validation fails."""
    pass

class OutputFormattingError(PerceptionException):
    """Raised when output formatting fails."""
    pass

# Memory Module Exceptions
class MemoryException(SocialMediaAgentException):
    """Base exception for memory module."""
    pass

class DatabaseConnectionError(MemoryException):
    """Raised when database connection fails."""
    pass

class RecordNotFoundError(MemoryException):
    """Raised when a record is not found in the database."""
    pass

class StorageError(MemoryException):
    """Raised when data storage operations fail."""
    pass

# Reasoning Module Exceptions
class ReasoningException(SocialMediaAgentException):
    """Base exception for reasoning module."""
    pass

class AnalysisError(ReasoningException):
    """Raised when request analysis fails."""
    pass

class WorkflowBuildError(ReasoningException):
    """Raised when workflow building fails."""
    pass

class ChatGPTAPIError(ReasoningException):
    """Raised when ChatGPT API call fails."""
    pass

class ClaudeAPIError(ReasoningException):
    """Raised when Claude API call fails."""
    pass

# Action Module Exceptions
class ActionException(SocialMediaAgentException):
    """Base exception for action module."""
    pass

class WorkflowExecutionError(ActionException):
    """Raised when workflow execution fails."""
    pass

class StepExecutionError(ActionException):
    """Raised when step execution fails."""
    pass

class ResourceAllocationError(ActionException):
    """Raised when resource allocation fails."""
    pass

class TimeoutError(ActionException):
    """Raised when execution times out."""
    pass

# Monitoring Module Exceptions
class MonitoringException(SocialMediaAgentException):
    """Base exception for monitoring module."""
    pass

class TrackingError(MonitoringException):
    """Raised when workflow or step tracking fails."""
    pass

class AlertGenerationError(MonitoringException):
    """Raised when alert generation fails."""
    pass

class MetricsCollectionError(MonitoringException):
    """Raised when metrics collection fails."""
    pass

# Communication Module Exceptions
class CommunicationException(SocialMediaAgentException):
    """Base exception for communication module."""
    pass

class MessageDeliveryError(CommunicationException):
    """Raised when message delivery fails."""
    pass

class ProtocolError(CommunicationException):
    """Raised when protocol validation fails."""
    pass

class QueueError(CommunicationException):
    """Raised when message queue operations fail."""
    pass

class ConnectionError(CommunicationException):
    """Raised when agent connection fails."""
    pass

# Learning Module Exceptions
class LearningException(SocialMediaAgentException):
    """Base exception for learning module."""
    pass

class AnalyzerError(LearningException):
    """Raised when performance analysis fails."""
    pass

class OptimizationError(LearningException):
    """Raised when workflow optimization fails."""
    pass

class ModelUpdateError(LearningException):
    """Raised when model update fails."""
    pass
