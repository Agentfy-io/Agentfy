# -*- coding: utf-8 -*-
"""
@file: agentfy/common/ais/chatgpt.py
@desc: OpenAI API client wrapper for chat and image generation
@auth: Callmeiks
"""
import traceback
from typing import Dict, Any, Optional
from decimal import Decimal

from openai import AsyncOpenAI, OpenAIError
from config import settings
from common.exceptions.exceptions import ChatGPTAPIError
from common.utils.logging import setup_logger

# Set up logger
logger = setup_logger(__name__)

class ChatGPT:
    """OpenAI API client wrapper class, supporting asynchronous calls to ChatGPT models"""

    # Model pricing configuration (price per token in USD)
    PRICING = {
        "o1": {
            "input": Decimal("15.00") / 1000000,
            "cached_input": Decimal("7.50") / 1000000,
            "output": Decimal("60.00") / 1000000
        },
        "o3-mini": {
            "input": Decimal("1.10") / 1000000,
            "cached_input": Decimal("0.55") / 1000000,
            "output": Decimal("4.40") / 1000000
        },
        "gpt-4.5": {
            "input": Decimal("75.00") / 1000000,
            "cached_input": Decimal("37.50") / 1000000,
            "output": Decimal("150.00") / 1000000
        },
        "gpt-4o": {
            "input": Decimal("2.50") / 1000000,
            "cached_input": Decimal("1.25") / 1000000,
            "output": Decimal("10.00") / 1000000
        },
        "gpt-4o-mini": {
            "input": Decimal("0.150") / 1000000,
            "cached_input": Decimal("0.075") / 1000000,
            "output": Decimal("0.600") / 1000000
        },
        "gpt-3.5-turbo": {
            "input": Decimal("0.0015") / 1000,
            "cached_input": Decimal("0.0015") / 1000,
            "output": Decimal("0.002") / 1000
        }
    }

    # DALL-E pricing (2024 prices, may need updates)
    IMAGE_PRICING = {
        "dall-e-3": {
            "standard": {
                "1024x1024": Decimal("0.04"),
                "1024x1792": Decimal("0.08"),
                "1792x1024": Decimal("0.08"),
            },
            "hd": {
                "1024x1024": Decimal("0.08"),
                "1024x1792": Decimal("0.12"),
                "1792x1024": Decimal("0.12"),
            }
        },
        "dall-e-2": {
            "standard": {
                "1024x1024": Decimal("0.02"),
                "512x512": Decimal("0.018"),
                "256x256": Decimal("0.016"),
            }
            # DALL-E 2 has no HD option
        }
    }

    # Model name normalization map
    MODEL_ALIASES = {
        "o1": ["o1", "claude-3-opus"],
        "o3-mini": ["o3-mini", "claude-3-haiku"],
        "gpt-4.5": ["gpt-4.5", "gpt-4.5-turbo"],
        "gpt-4o": ["gpt-4o"],
        "gpt-4o-mini": ["gpt-4o-mini"],
        "gpt-3.5-turbo": ["gpt-3.5", "gpt-3.5-turbo"]
    }

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize ChatGPT client

        Args:
            openai_api_key: OpenAI API key, if not provided will read from environment variables
        """
        # Set OpenAI API Key
        self.openai_key = openai_api_key or settings.openai_api_key

        if not self.openai_key:
            logger.warning("No OpenAI API key provided, ChatGPT functionality will be unavailable")
            self.openai_client = None
        else:
            # Initialize OpenAI client
            self.openai_client = AsyncOpenAI(api_key=self.openai_key, timeout=60)

    def _normalize_model_name(self, model: str) -> str:
        """
        Normalize model name to match pricing configuration

        Args:
            model: The model name to normalize

        Returns:
            Normalized model name

        Raises:
            ValueError: If the model is unknown
        """
        model_lower = model.lower()

        # Check all known model aliases
        for canonical_name, aliases in self.MODEL_ALIASES.items():
            if any(alias in model_lower for alias in aliases):
                return canonical_name

        # If no match found
        raise ValueError(f"Unknown model: {model}")

    async def calculate_chat_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> Dict[str, Any]:
        """
        Asynchronously calculate OpenAI API usage cost

        Args:
            model: Model name (e.g. 'gpt-4o', 'o1', 'gpt-4o-mini', etc.)
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            dict: Dictionary containing input_cost, output_cost and total_cost
        """
        # Normalize model name
        model_key = self._normalize_model_name(model)

        # Calculate costs
        input_cost = prompt_tokens * self.PRICING[model_key]["input"]
        output_cost = completion_tokens * self.PRICING[model_key]["output"]
        total_cost = input_cost + output_cost

        return {
            "input_cost": float(input_cost),
            "output_cost": float(output_cost),
            "total_cost": float(total_cost)
        }

    async def calculate_image_cost(self, model: str, size: str, quality: str, n: int) -> Dict[str, float]:
        """
        Calculate image generation cost

        Args:
            model: Model used
            size: Image size
            quality: Image quality
            n: Number of images

        Returns:
            Dictionary containing cost information
        """
        # Default values for fallbacks
        default_model = "dall-e-3"
        default_quality = "standard"
        default_size = "1024x1024"
        default_price = Decimal("0.04")

        # Normalize model
        model = model.lower()
        if model not in self.IMAGE_PRICING:
            logger.warning(f"Unknown model {model}, using {default_model} pricing")
            model = default_model

        # Check if quality is supported
        if quality not in self.IMAGE_PRICING[model]:
            logger.warning(f"Model {model} doesn't support quality {quality}, using {default_quality}")
            quality = default_quality

        # Check if size is supported
        if size not in self.IMAGE_PRICING[model][quality]:
            logger.warning(f"Model {model} with quality {quality} doesn't support size {size}, using {default_size}")
            size = default_size

        try:
            unit_price = self.IMAGE_PRICING[model][quality][size]
        except KeyError:
            logger.warning(
                f"Missing price configuration for {model}/{quality}/{size}, using default price ${default_price}")
            unit_price = default_price

        # Calculate total cost
        total_cost = unit_price * n

        return {
            "unit_price": float(unit_price),
            "quantity": n,
            "total_cost": float(total_cost)
        }

    async def chat(self,
                   system_prompt: str,
                   user_prompt: str,
                   model: str = "gpt-4o-mini",
                   temperature: float = 0.7,
                   max_tokens: int = 10000,
                   timeout: int = 60,
                   ) -> Dict[str, Any]:
        """
        Call OpenAI's chat interface (async)

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model name, defaults to DEFAULT_AI_MODEL from settings
            temperature: Temperature parameter, defaults to DEFAULT_TEMPERATURE from settings
            max_tokens: Maximum token length, defaults to DEFAULT_MAX_TOKENS from settings
            timeout: Timeout in seconds, default 60 seconds

        Returns:
            Generated result (dict)

        Raises:
            ChatGPTAPIError: When OpenAI API call fails
        """
        # Check if client is initialized
        if not self.openai_client:
            raise ChatGPTAPIError(
            "OpenAI client not initialized, chat functionality unavailable",
            {"details": "Please provide a valid OPENAI API key"},
        )

        try:
            # Call OpenAI's chat interface
            chat_completion = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

            # Calculate cost
            cost = await self.calculate_chat_cost(
                model,
                chat_completion.usage.prompt_tokens,
                chat_completion.usage.completion_tokens
            )

            result = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response": chat_completion.model_dump(),
                "cost": cost
            }

            # Log basic response info, without full content (which may be large)
            logger.info(
                f"OpenAI response: model={model}, "
                f"completion={chat_completion.usage.completion_tokens}/{chat_completion.usage.total_tokens} "
                f"input_cost=${cost['input_cost']:.6f}, output_cost=${cost['output_cost']:.6f}, total_cost=${cost['total_cost']:.6f}"
            )

            # Return generated result
            return result
        except OpenAIError as e:
            # Log and wrap OpenAI specific errors
            logger.error(
                f"OpenAI API error: {str(e)}",
                {"model": model, "temperature": temperature, "max_tokens": max_tokens}
            )
            raise ChatGPTAPIError(
                "Error calling OpenAI API",
                {"details": str(e)},
            )
        except Exception as e:
            # Log other unexpected errors
            logger.error(f"Unexpected error calling OpenAI: {str(e)}")
            traceback.print_exc()
            raise ChatGPTAPIError(
                "Unexpected error calling OpenAI",
                {"details": str(e)},
            )

    async def image(self,
                    prompt: str,
                    model: str = "dall-e-3",
                    size: str = "1024x1024",
                    quality: str = "standard",
                    n: int = 1,
                    timeout: int = 60,
                    ) -> Dict[str, Any]:
        """
        Call OpenAI's image generation interface (async)

        Args:
            prompt: Image generation prompt
            model: Model name, defaults to DEFAULT_IMAGE_MODEL from settings
            size: Generated image size, options "1024x1024", "1024x1792", "1792x1024"
            quality: Image quality, options "standard", "hd"
            n: Number of images to generate, default 1
            timeout: Timeout in seconds, default 60 seconds

        Returns:
            Generated result (dict)

        Raises:
            ChatGPTAPIError: When OpenAI API call fails
        """
        # Check if client is initialized
        if not self.openai_client:
            raise ChatGPTAPIError(
            "OpenAI client not initialized, image generation unavailable",
            {"details": "Please provide a valid OPENAI API key"},
        )

        try:
            # Call OpenAI's image generation interface
            image_response = await self.openai_client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
                timeout=timeout,
            )

            # Calculate cost (based on model, size and quality)
            cost = await self.calculate_image_cost(model, size, quality, n)

            result = {
                "model": model,
                "size": size,
                "quality": quality,
                "n": n,
                "response": image_response.model_dump(),
                "urls": [item.url for item in image_response.data],  # Extract all image URLs
                "cost": cost
            }

            # Log basic response info
            logger.info(
                f"OpenAI image generation response: model={model}, "
                f"size={size}, quality={quality}, quantity={n}, "
                f"total_cost=${cost['total_cost']:.6f}"
            )

            # Return generated result
            return result
        except OpenAIError as e:
            # Log and wrap OpenAI specific errors
            logger.error(f"OpenAI image API error: {str(e)}")
            raise ChatGPTAPIError(
                "Error calling OpenAI image generation",
                {"details": str(e)},
            )
        except Exception as e:
            # Log other unexpected errors
            logger.error(f"Unexpected error calling OpenAI image generation: {str(e)}")
            traceback.print_exc()
            raise ChatGPTAPIError(
                "Error calling OpenAI image generation",
                {"details": str(e)},
            )


async def main():
    # Create ChatGPT client
    chatgpt = ChatGPT()

    # Generate an image
    image_result = await chatgpt.image(
        prompt="A cat floating in space with colorful nebulae in the background",
        size="1024x1024",
        quality="standard"
    )

    # Get image URL
    image_url = image_result["urls"][0]
    print(f"Generated image URL: {image_url}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
