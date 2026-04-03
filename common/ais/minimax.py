# -*- coding: utf-8 -*-
"""
@file: agentfy/common/ais/minimax.py
@desc: MiniMax API client wrapper for chat via OpenAI-compatible interface
@auth: Callmeiks
"""
import traceback
from typing import Dict, Any, Optional
from decimal import Decimal

from openai import AsyncOpenAI, OpenAIError
from config import settings
from common.exceptions.exceptions import MiniMaxAPIError
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)

MINIMAX_BASE_URL = "https://api.minimax.io/v1"


class MiniMax:
    """MiniMax API client wrapper using the OpenAI-compatible interface."""

    # Model pricing configuration (price per token in USD)
    PRICING = {
        "MiniMax-M2.7": {
            "input": Decimal("0.80") / 1000000,
            "output": Decimal("4.00") / 1000000,
        },
        "MiniMax-M2.7-highspeed": {
            "input": Decimal("0.20") / 1000000,
            "output": Decimal("1.00") / 1000000,
        },
        "MiniMax-M2.5": {
            "input": Decimal("0.80") / 1000000,
            "output": Decimal("4.00") / 1000000,
        },
        "MiniMax-M2.5-highspeed": {
            "input": Decimal("0.20") / 1000000,
            "output": Decimal("1.00") / 1000000,
        },
    }

    # Supported model names
    SUPPORTED_MODELS = list(PRICING.keys())

    def __init__(self, minimax_api_key: Optional[str] = None):
        """
        Initialize MiniMax client.

        Args:
            minimax_api_key: MiniMax API key; reads MINIMAX_API_KEY env var if not provided.
        """
        self.minimax_key = minimax_api_key or settings.minimax_api_key

        if not self.minimax_key:
            logger.warning("No MiniMax API key provided, MiniMax functionality will be unavailable")
            self.minimax_client = None
        else:
            self.minimax_client = AsyncOpenAI(
                api_key=self.minimax_key,
                base_url=MINIMAX_BASE_URL,
                timeout=60,
            )

    def _clamp_temperature(self, temperature: float) -> float:
        """
        Clamp temperature to the valid MiniMax range (0.0, 1.0].

        MiniMax requires temperature > 0 and <= 1.
        """
        if temperature <= 0.0:
            temperature = 0.01
        elif temperature > 1.0:
            temperature = 1.0
        return temperature

    def _normalize_model(self, model: str) -> str:
        """Return the canonical model name, defaulting to MiniMax-M2.7."""
        if model in self.PRICING:
            return model
        logger.warning(f"Unknown MiniMax model '{model}', falling back to MiniMax-M2.7")
        return "MiniMax-M2.7"

    async def calculate_chat_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> Dict[str, Any]:
        """
        Calculate MiniMax API usage cost.

        Args:
            model: Model name.
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.

        Returns:
            dict with input_cost, output_cost, total_cost.
        """
        model_key = self._normalize_model(model)
        input_cost = prompt_tokens * self.PRICING[model_key]["input"]
        output_cost = completion_tokens * self.PRICING[model_key]["output"]
        total_cost = input_cost + output_cost

        return {
            "input_cost": float(input_cost),
            "output_cost": float(output_cost),
            "total_cost": float(total_cost),
        }

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "MiniMax-M2.7",
        temperature: float = 0.7,
        max_tokens: int = 10000,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """
        Call MiniMax chat API via the OpenAI-compatible interface (async).

        Args:
            system_prompt: System prompt.
            user_prompt: User prompt.
            model: Model name (default: MiniMax-M2.7, 204K context).
            temperature: Sampling temperature; clamped to (0.0, 1.0].
            max_tokens: Maximum output tokens.
            timeout: Request timeout in seconds.

        Returns:
            dict with model, temperature, max_tokens, response, cost.

        Raises:
            MiniMaxAPIError: When the API call fails.
        """
        if not self.minimax_client:
            raise MiniMaxAPIError(
                "MiniMax client not initialized, chat functionality unavailable",
                {"details": "Please provide a valid MINIMAX_API_KEY"},
            )

        model = self._normalize_model(model)
        temperature = self._clamp_temperature(temperature)

        try:
            chat_completion = await self.minimax_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

            cost = await self.calculate_chat_cost(
                model,
                chat_completion.usage.prompt_tokens,
                chat_completion.usage.completion_tokens,
            )

            result = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response": chat_completion.model_dump(),
                "cost": cost,
            }

            logger.info(
                f"MiniMax response: model={model}, "
                f"completion={chat_completion.usage.completion_tokens}/{chat_completion.usage.total_tokens} "
                f"input_cost=${cost['input_cost']:.6f}, output_cost=${cost['output_cost']:.6f}, "
                f"total_cost=${cost['total_cost']:.6f}"
            )

            return result

        except OpenAIError as e:
            logger.error(
                f"MiniMax API error: {str(e)}",
                {"model": model, "temperature": temperature, "max_tokens": max_tokens},
            )
            raise MiniMaxAPIError(
                "Error calling MiniMax API",
                {"details": str(e)},
            )
        except Exception as e:
            logger.error(f"Unexpected error calling MiniMax: {str(e)}")
            traceback.print_exc()
            raise MiniMaxAPIError(
                "Unexpected error calling MiniMax",
                {"details": str(e)},
            )
