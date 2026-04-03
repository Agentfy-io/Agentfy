# -*- coding: utf-8 -*-
"""
Unit tests for common/ais/minimax.py
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_minimax(api_key="test-key"):
    """Return a MiniMax instance with a dummy key (no real HTTP)."""
    with patch("common.ais.minimax.settings") as mock_settings:
        mock_settings.minimax_api_key = api_key
        from common.ais.minimax import MiniMax
        return MiniMax(minimax_api_key=api_key)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestMiniMaxInit:
    def test_init_with_explicit_key(self):
        from common.ais.minimax import MiniMax
        with patch("common.ais.minimax.settings") as ms:
            ms.minimax_api_key = None
            mm = MiniMax(minimax_api_key="explicit-key")
        assert mm.minimax_key == "explicit-key"
        assert mm.minimax_client is not None

    def test_init_no_key_client_is_none(self):
        from common.ais.minimax import MiniMax
        with patch("common.ais.minimax.settings") as ms:
            ms.minimax_api_key = None
            mm = MiniMax(minimax_api_key=None)
        assert mm.minimax_client is None

    def test_init_reads_from_settings(self):
        from common.ais.minimax import MiniMax
        with patch("common.ais.minimax.settings") as ms:
            ms.minimax_api_key = "settings-key"
            mm = MiniMax()
        assert mm.minimax_key == "settings-key"


# ---------------------------------------------------------------------------
# Temperature clamping
# ---------------------------------------------------------------------------

class TestClampTemperature:
    def setup_method(self):
        self.mm = _make_minimax()

    def test_valid_temperature_unchanged(self):
        assert self.mm._clamp_temperature(0.7) == pytest.approx(0.7)

    def test_temperature_zero_clamped_up(self):
        assert self.mm._clamp_temperature(0.0) == pytest.approx(0.01)

    def test_negative_temperature_clamped_up(self):
        assert self.mm._clamp_temperature(-1.0) == pytest.approx(0.01)

    def test_temperature_above_one_clamped_down(self):
        assert self.mm._clamp_temperature(1.5) == pytest.approx(1.0)

    def test_temperature_exactly_one_unchanged(self):
        assert self.mm._clamp_temperature(1.0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Model normalization
# ---------------------------------------------------------------------------

class TestNormalizeModel:
    def setup_method(self):
        self.mm = _make_minimax()

    def test_known_model_returned_unchanged(self):
        assert self.mm._normalize_model("MiniMax-M2.7") == "MiniMax-M2.7"
        assert self.mm._normalize_model("MiniMax-M2.7-highspeed") == "MiniMax-M2.7-highspeed"
        assert self.mm._normalize_model("MiniMax-M2.5") == "MiniMax-M2.5"
        assert self.mm._normalize_model("MiniMax-M2.5-highspeed") == "MiniMax-M2.5-highspeed"

    def test_unknown_model_falls_back_to_m27(self):
        assert self.mm._normalize_model("unknown-model") == "MiniMax-M2.7"


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------

class TestCalculateChatCost:
    def setup_method(self):
        self.mm = _make_minimax()

    @pytest.mark.asyncio
    async def test_cost_m27(self):
        cost = await self.mm.calculate_chat_cost("MiniMax-M2.7", 1000, 500)
        assert cost["input_cost"] == pytest.approx(1000 * 0.80 / 1_000_000)
        assert cost["output_cost"] == pytest.approx(500 * 4.00 / 1_000_000)
        assert cost["total_cost"] == pytest.approx(cost["input_cost"] + cost["output_cost"])

    @pytest.mark.asyncio
    async def test_cost_m27_highspeed(self):
        cost = await self.mm.calculate_chat_cost("MiniMax-M2.7-highspeed", 2000, 1000)
        assert cost["input_cost"] == pytest.approx(2000 * 0.20 / 1_000_000)
        assert cost["output_cost"] == pytest.approx(1000 * 1.00 / 1_000_000)

    @pytest.mark.asyncio
    async def test_cost_unknown_model_uses_fallback(self):
        # unknown model falls back to M2.7 pricing
        cost = await self.mm.calculate_chat_cost("bad-model", 1000, 1000)
        assert cost["input_cost"] == pytest.approx(1000 * 0.80 / 1_000_000)


# ---------------------------------------------------------------------------
# chat()
# ---------------------------------------------------------------------------

def _make_completion_mock(prompt_tokens=100, completion_tokens=50, model="MiniMax-M2.7"):
    """Build a mock chat completion object."""
    choice = MagicMock()
    choice.message.content = "Hello from MiniMax"
    choice.finish_reason = "stop"
    choice.index = 0

    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = prompt_tokens + completion_tokens

    completion = MagicMock()
    completion.usage = usage
    completion.model = model
    completion.model_dump.return_value = {
        "id": "chat-123",
        "choices": [{"message": {"role": "assistant", "content": "Hello from MiniMax"}}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }
    return completion


class TestChat:
    def setup_method(self):
        self.mm = _make_minimax()

    @pytest.mark.asyncio
    async def test_chat_raises_when_no_client(self):
        from common.ais.minimax import MiniMax
        from common.exceptions.exceptions import MiniMaxAPIError
        with patch("common.ais.minimax.settings") as ms:
            ms.minimax_api_key = None
            mm = MiniMax(minimax_api_key=None)
        with pytest.raises(MiniMaxAPIError, match="not initialized"):
            await mm.chat("sys", "user")

    @pytest.mark.asyncio
    async def test_chat_success_returns_expected_keys(self):
        mock_completion = _make_completion_mock()
        self.mm.minimax_client = MagicMock()
        self.mm.minimax_client.chat = MagicMock()
        self.mm.minimax_client.chat.completions = MagicMock()
        self.mm.minimax_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await self.mm.chat("Be helpful", "What is AI?")
        assert "model" in result
        assert "response" in result
        assert "cost" in result
        assert "temperature" in result

    @pytest.mark.asyncio
    async def test_chat_temperature_is_clamped(self):
        mock_completion = _make_completion_mock()
        self.mm.minimax_client = MagicMock()
        self.mm.minimax_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await self.mm.chat("sys", "user", temperature=0.0)
        # clamped up from 0.0 to 0.01
        assert result["temperature"] == pytest.approx(0.01)

    @pytest.mark.asyncio
    async def test_chat_uses_default_model(self):
        mock_completion = _make_completion_mock()
        self.mm.minimax_client = MagicMock()
        self.mm.minimax_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await self.mm.chat("sys", "user")
        assert result["model"] == "MiniMax-M2.7"

    @pytest.mark.asyncio
    async def test_chat_wraps_openai_error(self):
        from openai import OpenAIError
        from common.exceptions.exceptions import MiniMaxAPIError
        self.mm.minimax_client = MagicMock()
        self.mm.minimax_client.chat.completions.create = AsyncMock(
            side_effect=OpenAIError("rate limit")
        )
        with pytest.raises(MiniMaxAPIError):
            await self.mm.chat("sys", "user")

    @pytest.mark.asyncio
    async def test_chat_wraps_generic_exception(self):
        from common.exceptions.exceptions import MiniMaxAPIError
        self.mm.minimax_client = MagicMock()
        self.mm.minimax_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("network failure")
        )
        with pytest.raises(MiniMaxAPIError):
            await self.mm.chat("sys", "user")

    @pytest.mark.asyncio
    async def test_chat_cost_values_are_floats(self):
        mock_completion = _make_completion_mock(prompt_tokens=200, completion_tokens=100)
        self.mm.minimax_client = MagicMock()
        self.mm.minimax_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await self.mm.chat("sys", "user")
        cost = result["cost"]
        assert isinstance(cost["input_cost"], float)
        assert isinstance(cost["output_cost"], float)
        assert isinstance(cost["total_cost"], float)

    @pytest.mark.asyncio
    async def test_chat_highspeed_model(self):
        mock_completion = _make_completion_mock(model="MiniMax-M2.7-highspeed")
        self.mm.minimax_client = MagicMock()
        self.mm.minimax_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await self.mm.chat("sys", "user", model="MiniMax-M2.7-highspeed")
        assert result["model"] == "MiniMax-M2.7-highspeed"

    @pytest.mark.asyncio
    async def test_chat_m25_model(self):
        mock_completion = _make_completion_mock(model="MiniMax-M2.5")
        self.mm.minimax_client = MagicMock()
        self.mm.minimax_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await self.mm.chat("sys", "user", model="MiniMax-M2.5")
        assert result["model"] == "MiniMax-M2.5"
