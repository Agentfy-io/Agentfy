# -*- coding: utf-8 -*-
"""
Integration tests for common/ais/minimax.py

These tests verify the integration with the MiniMax API using the
MINIMAX_API_KEY environment variable.  They are skipped automatically
when the key is not present.
"""
import os
import pytest


pytestmark = pytest.mark.skipif(
    not os.getenv("MINIMAX_API_KEY"),
    reason="MINIMAX_API_KEY not set — skipping integration tests",
)


@pytest.fixture
def minimax():
    from common.ais.minimax import MiniMax
    return MiniMax()


class TestMiniMaxIntegration:
    @pytest.mark.asyncio
    async def test_chat_returns_non_empty_response(self, minimax):
        result = await minimax.chat(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello in one word.",
            model="MiniMax-M2.7",
            max_tokens=20,
        )
        choices = result["response"].get("choices", [])
        assert len(choices) > 0
        content = choices[0]["message"]["content"]
        assert isinstance(content, str) and len(content) > 0

    @pytest.mark.asyncio
    async def test_chat_highspeed_model(self, minimax):
        result = await minimax.chat(
            system_prompt="You are a helpful assistant.",
            user_prompt="Reply with the single word 'OK'.",
            model="MiniMax-M2.7-highspeed",
            max_tokens=10,
        )
        assert result["model"] == "MiniMax-M2.7-highspeed"

    @pytest.mark.asyncio
    async def test_chat_cost_is_positive(self, minimax):
        result = await minimax.chat(
            system_prompt="Answer briefly.",
            user_prompt="What is 2+2?",
            model="MiniMax-M2.7",
            max_tokens=20,
        )
        assert result["cost"]["total_cost"] > 0
