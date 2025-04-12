# -*- coding: utf-8 -*-
"""
@file: agentfy/core/perception/module.py
@desc: Perception Module for handling input validation, security checks,
@auth: Callmeiks
"""
from typing import Any, Dict, List, Optional, Union
import json
from pydantic import ValidationError

from common.models.messages import (
    UserInput, ValidationResult, SecurityCheckResult,
    FileValidationResult, PromptMessage, FormattedOutput,
    ParameterInfo
)
from common.security.validators import SecurityValidator
from common.security.sanitizers import InputSanitizer, FileValidator
from common.exceptions.exceptions import (
    InputValidationError, SecurityCheckFailedError,
    FileValidationError, OutputFormattingError
)
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)


class PerceptionModule:
    """
    Perception Module for handling input validation, security checks,
    and output formatting.
    """

    def __init__(self):
        """Initialize the perception module with validators and sanitizers."""
        self.security_validator = SecurityValidator()
        self.input_sanitizer = InputSanitizer()
        self.file_validator = FileValidator()

    async def validate_input(self, input_data: Union[Dict[str, Any], UserInput]) -> ValidationResult:
        """
        Validate and sanitize user input.

        Args:
            input_data: The user input data to validate

        Returns:
            ValidationResult: The validation result with sanitized input if valid

        Raises:
            InputValidationError: If input validation fails
        """
        try:
            # Convert to UserInput if dict
            if isinstance(input_data, dict):
                input_data = UserInput(**input_data)

            logger.info(
                "Validating user input",
                {"user_id": input_data.metadata.user_id}
            )

            errors = []

            # Check for security issues if text is present
            if input_data.text:
                security_check = self.security_validator.check_for_injection(input_data.text)
                if not security_check.is_safe:
                    logger.warning(
                        "Security check failed",
                        {
                            "user_id": input_data.metadata.user_id,
                            "issues": [issue.dict() for issue in security_check.detected_issues]
                        }
                    )
                    errors.append({
                        "type": "security",
                        "details": [issue.dict() for issue in security_check.detected_issues]
                    })

            # Validate files if present
            if input_data.files:
                for file_info in input_data.files:
                    file_validation = self.file_validator.validate_file(
                        file_info.filename, file_info.size
                    )
                    if not file_validation["is_allowed"]:
                        errors.append({
                            "type": "file",
                            "details": file_validation["reason"]
                        })

            # If there are errors, return validation result with errors
            if errors:
                return ValidationResult(is_valid=False, errors=errors)

            # Sanitize input
            sanitized_input = self.input_sanitizer.sanitize_input(input_data)

            return ValidationResult(
                is_valid=True,
                sanitized_input=sanitized_input
            )

        except ValidationError as e:
            logger.error(
                "Input validation error",
                {"error": str(e)}
            )
            raise InputValidationError(
                "Invalid input format",
                {"details": e.errors()}
            )

        except Exception as e:
            logger.error(
                "Unexpected error during input validation",
                {"error": str(e)}
            )
            raise InputValidationError(
                "Failed to validate input",
                {"details": str(e)}
            )

    async def format_output(self, result: Any, output_format: str = "json") -> FormattedOutput:
        """
        Format the output for presentation to the user.

        Args:
            result: The result data to format
            output_format: The desired output format (json, text, html)

        Returns:
            FormattedOutput: The formatted output

        Raises:
            OutputFormattingError: If output formatting fails
        """
        try:
            logger.info(
                "Formatting output",
                {"format": output_format}
            )

            if output_format == "json":
                # If result is already a dict, use it directly
                if isinstance(result, dict):
                    content = result
                # If result is an object with a dict method, use that
                elif hasattr(result, "dict"):
                    content = result.dict()
                # Otherwise, convert to string and then try to parse as JSON
                else:
                    try:
                        content = json.loads(str(result))
                    except json.JSONDecodeError:
                        content = {"result": str(result)}

                return FormattedOutput(
                    type="data",
                    content=content,
                    format="json"
                )

            elif output_format == "text":
                # Convert result to string
                if hasattr(result, "dict"):
                    content = json.dumps(result.dict(), indent=2)
                elif isinstance(result, dict):
                    content = json.dumps(result, indent=2)
                else:
                    content = str(result)

                return FormattedOutput(
                    type="message",
                    content=content,
                    format="text"
                )

            elif output_format == "html":
                # Convert result to HTML
                if hasattr(result, "dict"):
                    result_dict = result.dict()
                elif isinstance(result, dict):
                    result_dict = result
                else:
                    result_dict = {"result": str(result)}

                # Simple HTML table format
                html_content = "<table>"
                for key, value in result_dict.items():
                    html_content += f"<tr><td>{key}</td><td>{value}</td></tr>"
                html_content += "</table>"

                return FormattedOutput(
                    type="html",
                    content=html_content,
                    format="html"
                )

            else:
                raise OutputFormattingError(f"Unsupported output format: {output_format}")

        except Exception as e:
            logger.error(
                "Output formatting error",
                {"error": str(e), "format": output_format}
            )
            raise OutputFormattingError(
                f"Failed to format output as {output_format}",
                {"details": str(e)}
            )

    async def generate_parameter_prompt(self, missing_parameters: List[Dict[str, Any]]) -> PromptMessage:
        """
        Generate a prompt message for missing parameters.

        Args:
            missing_parameters: List of missing parameters with details

        Returns:
            PromptMessage: A formatted prompt message for the user
        """
        try:
            logger.info("Generating parameter prompt")

            # Convert dictionary parameters to ParameterInfo objects
            param_info_list = []
            for param in missing_parameters:
                param_info_list.append(ParameterInfo(
                    name=param["name"],
                    description=param["description"],
                    type=param["type"],
                    required=param.get("required", True),
                    default=param.get("default")
                ))

            # Generate message text
            message = "To complete your request, I need some additional information:\n\n"
            for param in param_info_list:
                message += f"- {param.description}"
                if param.default is not None:
                    message += f" (default: {param.default})"
                message += "\n"

            return PromptMessage(
                type="PARAMETER_REQUEST",
                message=message,
                parameters=param_info_list
            )

        except Exception as e:
            logger.error(
                "Error generating parameter prompt",
                {"error": str(e)}
            )
            # Return a simple message on error
            return PromptMessage(
                type="PARAMETER_REQUEST",
                message="I need some additional information to process your request."
            )

    async def handle_input_error(self, error: InputValidationError) -> FormattedOutput:
        """
        Handle input validation errors and format for user display.

        Args:
            error: The input validation error

        Returns:
            FormattedOutput: Formatted error message
        """
        logger.error(
            "Handling input error",
            {"error_message": error.message, "details": error.details}
        )

        # Create user-friendly error message
        if "security" in str(error.details).lower():
            message = "Your request contains potentially harmful content that cannot be processed."
        elif "file" in str(error.details).lower():
            message = "There was an issue with one or more files you provided. Please check file types and sizes."
        else:
            message = "We couldn't process your request. Please check your input and try again."

        return FormattedOutput(
            type="error",
            content={
                "message": message,
                "details": error.details if hasattr(error, "details") else str(error)
            },
            format="json"
        )