# -*- coding: utf-8 -*-
"""
@file: agentfy/core/perception/formatter.py
@desc: formatting output before sending data to the frontend/users
@auth(s): Callmeiks
"""
from typing import Any, Dict, List, Optional, Union
import json
from datetime import datetime
from common.utils.logging import get_logger
from common.exceptions.exceptions import OutputFormattingError

logger = get_logger(__name__)


class OutputFormatter:
    """Formatter for different output formats."""

    def format_json(self, data: Any) -> str:
        """Format data as JSON string."""
        try:
            # Convert Pydantic models to dict if necessary
            if hasattr(data, "dict"):
                data = data.dict()

            return json.dumps(data, indent=2, default=str)
        except Exception as e:
            logger.error_with_data(
                "Error formatting JSON output",
                {"error": str(e)}
            )
            raise OutputFormattingError(f"Failed to format as JSON: {str(e)}")

    def format_text(self, data: Any) -> str:
        """Format data as plain text."""
        try:
            if isinstance(data, (dict, list)):
                return json.dumps(data, indent=2, default=str)
            return str(data)
        except Exception as e:
            logger.error_with_data(
                "Error formatting text output",
                {"error": str(e)}
            )
            raise OutputFormattingError(f"Failed to format as text: {str(e)}")

    def format_html(self, data: Any) -> str:
        """Format data as HTML."""
        try:
            html = ["<div class='result'>"]

            if isinstance(data, dict):
                html.append("<table>")
                for key, value in data.items():
                    html.append("<tr>")
                    html.append(f"<td><strong>{key}</strong></td>")

                    if isinstance(value, dict):
                        nested_html = self.format_nested_dict_as_html(value)
                        html.append(f"<td>{nested_html}</td>")
                    elif isinstance(value, list):
                        nested_html = self.format_list_as_html(value)
                        html.append(f"<td>{nested_html}</td>")
                    else:
                        html.append(f"<td>{value}</td>")

                    html.append("</tr>")
                html.append("</table>")
            elif isinstance(data, list):
                html.append(self.format_list_as_html(data))
            else:
                html.append(f"<p>{data}</p>")

            html.append("</div>")
            return "".join(html)
        except Exception as e:
            logger.error_with_data(
                "Error formatting HTML output",
                {"error": str(e)}
            )
            raise OutputFormattingError(f"Failed to format as HTML: {str(e)}")

    def format_nested_dict_as_html(self, data: Dict[str, Any]) -> str:
        """Format a nested dictionary as HTML."""
        html = ["<table class='nested'>"]
        for key, value in data.items():
            html.append("<tr>")
            html.append(f"<td><strong>{key}</strong></td>")

            if isinstance(value, dict):
                nested_html = self.format_nested_dict_as_html(value)
                html.append(f"<td>{nested_html}</td>")
            elif isinstance(value, list):
                nested_html = self.format_list_as_html(value)
                html.append(f"<td>{nested_html}</td>")
            else:
                html.append(f"<td>{value}</td>")

            html.append("</tr>")
        html.append("</table>")
        return "".join(html)

    def format_list_as_html(self, data: List[Any]) -> str:
        """Format a list as HTML."""
        html = ["<ul>"]
        for item in data:
            if isinstance(item, dict):
                nested_html = self.format_nested_dict_as_html(item)
                html.append(f"<li>{nested_html}</li>")
            elif isinstance(item, list):
                nested_html = self.format_list_as_html(item)
                html.append(f"<li>{nested_html}</li>")
            else:
                html.append(f"<li>{item}</li>")
        html.append("</ul>")
        return "".join(html)

    def format_error(self, error: Exception) -> Dict[str, Any]:
        """Format an error message."""
        error_data = {
            "error": True,
            "message": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add details if available
        if hasattr(error, "details"):
            error_data["details"] = error.details

        return error_data

    def format_workflow_result(self, result: Dict[str, Any], format_type: str = "json") -> str:
        """Format a workflow result in the specified format."""
        if format_type == "json":
            return self.format_json(result)
        elif format_type == "text":
            return self.format_text(result)
        elif format_type == "html":
            return self.format_html(result)
        else:
            raise OutputFormattingError(f"Unsupported format type: {format_type}")