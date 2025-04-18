# -*- coding: utf-8 -*-
"""
@file: agentfy/core/perception/module.py
@desc: Perception Module for handling input validation, security checks, and output formatting.
       This module is responsible for:
       - Validating and sanitizing user input
       - Performing security checks
       - Clarifying ambiguous user requests
       - Formatting output for presentation
@auth: Callmeiks
@date: 2024-04-15
"""
from typing import Any, Dict, List, Optional, Union
import json
import pandas as pd
from pydantic import ValidationError

from common.ais.chatgpt import ChatGPT
from common.security.validators import SecurityValidator
from common.security.sanitizers import InputSanitizer, FileValidator
from common.utils.logging import setup_logger
from common.exceptions.exceptions import (
    InputValidationError, OutputFormattingError
)
from common.models.messages import (
    UserInput, ValidationResult, FormattedOutput,
)

# Set up logger
logger = setup_logger(__name__)


class PerceptionModule:
    """
    Perception Module for handling input validation, security checks, and output formatting.
    
    This module serves as the first point of contact for user input, ensuring that:
    1. Input is valid and properly formatted
    2. Security checks are performed
    3. Ambiguous requests are clarified
    4. Output is formatted appropriately for presentation
    """

    def __init__(self):
        """
        Initialize the perception module with validators and sanitizers.
        
        Initializes:
        - SecurityValidator: For checking input for security issues
        - InputSanitizer: For cleaning and normalizing input
        - FileValidator: For validating file uploads
        - ChatGPT: For clarifying ambiguous requests and formatting output
        """
        self.security_validator = SecurityValidator()
        self.input_sanitizer = InputSanitizer()
        self.file_validator = FileValidator()
        self.chatgpt = ChatGPT()

    async def clarify_user_request(self, user_request: str) -> Dict[str, Any]:
        """
        Use GPT to clarify and rephrase a user request into a clear, goal-oriented instruction.

        Args:
            user_request (str): The original user request in natural language.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - is_valid (bool): Whether the request is actionable
                - rephrased_request (str): The clarified request (if valid)
                - reason (str): Explanation if request is invalid

        Example:
            >>> await clarify_user_request("post something about AI")
            {
                "is_valid": True,
                "rephrased_request": "Create a social media post about artificial intelligence",
                "reason": None
            }
        """
        logger.info("Clarifying user request....")
        system_prompt = (
            "You are an intelligent assistant that helps rephrase ambiguous user instructions into clear, goal-oriented tasks for social media agents "
            "Determine if the request is relevant, clean typo. Output a JSON with:\n"
            "- is_valid (bool): if the request is actionable\n"
            "- rephrased_request (str): only if valid\n"
            "- reason (str): why it's invalid, if applicable"
        )

        user_prompt = f"Original request: {user_request}\n\nRespond with JSON:"

        response = await self.chatgpt.chat(system_prompt, user_prompt)
        response = json.loads(response['response']["choices"][0]["message"]["content"].strip())
        return response

    async def validate_input(self, input_data: Union[Dict[str, Any], UserInput]) -> ValidationResult:
        """
        Validate and sanitize user input.

        This method performs several validation steps:
        1. Converts input to UserInput model if needed
        2. Performs security checks on text input
        3. Validates file uploads if present
        4. Sanitizes the input
        5. Clarifies ambiguous text input

        Args:
            input_data (Union[Dict[str, Any], UserInput]): The user input data to validate

        Returns:
            ValidationResult: The validation result containing:
                - is_valid (bool): Whether the input is valid
                - errors (List[Dict]): Any validation errors
                - sanitized_input (Dict): The cleaned input if valid

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
                        "details": [issue.dict() for issue in security_check.detected_issues],
                        "message": "Your request contains potentially harmful content that cannot be processed."
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
                            "details": file_validation["reason"],
                            "message": f"File '{file_info.filename}' is not allowed. {file_validation['reason']}"
                        })

            # If there are errors, return validation result with errors
            if errors:
                return ValidationResult(is_valid=False, errors=errors)

            # Sanitize input
            sanitized_input = self.input_sanitizer.sanitize_input(input_data)

            # refine user text input
            if sanitized_input['text']:
                new_request = await self.clarify_user_request(sanitized_input['text'])
                if new_request.get("is_valid"):
                    sanitized_input['text'] = new_request.get("rephrased_request")
                else:
                    errors.append({
                        "type": "clarification",
                        "details": new_request['reason'],
                        "message": f"Request clarification failed: {new_request['reason']}"
                    })
                    return ValidationResult(is_valid=False, errors=errors)

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

    async def get_gpt_response(self, result: Any, user_input_text: str, output_format: str = "json") -> str:
        """
        Generate the opening response for the user using GPT.

        Args:
            result (Any): The result data to include in the response
            user_input_text (str): The original user input text
            output_format (str): The desired output format ("json" or "text")

        Returns:
            str: The generated response text

        Raises:
            OutputFormattingError: If the output format is not supported
        """
        logger.info("Generating GPT response", {"format": output_format})

        if output_format == "json":
            system_prompt = (
                "You are a helpful social media assistant. Create a brief 2-3 sentence conversational opening "
                "based on the user query and sample result data. Highlight key insights without over-explaining. "
                "Add a few emojis to enhance friendliness and professionalism."
            )
            user_prompt = (
                f"User query: {user_input_text}\n\n"
                f"Sample data: {result[:5]}\n\n"
            )
        elif output_format == "text":
            system_prompt = (
                "You are a helpful social media assistant. Create a concise, conversational response "
                "based on the user query and final result. Keep it under 150 words. Return output in Markdown format. "
                "Feel free to include a few emojis to enhance tone."
            )
            user_prompt = (
                f"User query: {user_input_text}\n\n"
                f"Result: {result}\n\n"
            )
        else:
            raise OutputFormattingError(f"Unsupported output format: {output_format}")

        response = await self.chatgpt.chat(system_prompt, user_prompt)
        return response['response']["choices"][0]["message"]["content"].strip()

    async def format_output(self, result: Any, user_input_text: str, output_format: str = "json") -> FormattedOutput:
        """
        Format the output for presentation to the user.

        This method handles different output formats:
        - JSON: Converts data to a markdown table with an opening message
        - Text: Generates a conversational response

        Args:
            result (Any): The result data to format
            user_input_text (str): The original user input text
            output_format (str): The desired output format ("json" or "text")

        Returns:
            FormattedOutput: The formatted output containing:
                - type (str): The type of output
                - content (Any): The formatted content
                - format (str): The output format

        Raises:
            OutputFormattingError: If formatting fails or format is not supported
        """
        logger.info("Formatting output", {"format": output_format})
        try:
            if output_format == "json":
                opener = await self.get_gpt_response(result, user_input_text, output_format)
                try:
                    df = pd.json_normalize(result)
                    table = df.to_markdown(index=False)
                    content = f"{opener}\n\n{table}"
                except Exception as e:
                    logger.error("Error formatting JSON to Markdown", {"error": str(e)})
                    raise OutputFormattingError("Failed to format JSON data to Markdown", {"details": str(e)})
            elif output_format == "text":
                content = await self.get_gpt_response(result, user_input_text, output_format)
            else:
                raise OutputFormattingError(f"Unsupported output format: {output_format}")

            return FormattedOutput(type="data", content=content, format="json")

        except Exception as e:
            logger.error("Output formatting error", {"error": str(e), "format": output_format})
            raise OutputFormattingError(f"Failed to format output as {output_format}", {"details": str(e)})
