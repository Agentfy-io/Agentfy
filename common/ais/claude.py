import json
import traceback
from typing import Dict, Any, List, Optional

from anthropic import AsyncAnthropic, APIError, APITimeoutError, RateLimitError as AnthropicRateLimitError
from config import settings
from common.utils.logging import setup_logger
from common.exceptions.exceptions import ClaudeAPIError

logger = setup_logger(__name__)


class Claude:
    """Anthropic API客户端封装类，支持异步调用Claude模型"""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        初始化Claude客户端

        Args:
            anthropic_api_key: Anthropic API密钥，如果未提供则从环境变量中读取
        """
        # 设置Anthropic API Key
        self.anthropic_key = anthropic_api_key or settings.anthropic_api_key

        if not self.anthropic_key:
            logger.warning("未提供Anthropic API密钥，Claude功能将不可用")
            self.anthropic_client = None
        else:
            # 初始化Anthropic客户端
            self.anthropic_client = AsyncAnthropic(api_key=self.anthropic_key)

        # Claude模型名称映射
        self.model_map = {
            "claude-3-opus": "claude-3-opus-20240229",
            "claude-3-sonnet": "claude-3-sonnet-20240229",
            "claude-3-haiku": "claude-3-haiku-20240307",
            "claude-3.5-sonnet": "claude-3-5-sonnet-20240620"
        }

    async def calculate_claude_cost(self, model: str, input_tokens: int, output_tokens: int)->Dict[str, Any]:
        """
        异步计算Claude API使用成本

        参数:
        model (str): 模型名称（如'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'等）
        input_tokens (int): 输入token数量
        output_tokens (int): 输出token数量

        返回:
        dict: 包含input_cost, output_cost和total_cost的字典
        """
        # Claude模型价格配置（每百万token的美元价格）
        pricing = {
            "claude-3-opus": {
                "input": 15.00 / 1000000,  # $15.00 per 1M tokens
                "output": 75.00 / 1000000  # $75.00 per 1M tokens
            },
            "claude-3-sonnet": {
                "input": 3.00 / 1000000,  # $3.00 per 1M tokens
                "output": 15.00 / 1000000  # $15.00 per 1M tokens
            },
            "claude-3-haiku": {
                "input": 0.25 / 1000000,  # $0.25 per 1M tokens
                "output": 1.25 / 1000000  # $1.25 per 1M tokens
            },
            "claude-2": {
                "input": 8.00 / 1000000,  # $8.00 per 1M tokens
                "output": 24.00 / 1000000  # $24.00 per 1M tokens
            },
            "claude-instant": {
                "input": 1.63 / 1000000,  # $1.63 per 1M tokens
                "output": 5.51 / 1000000  # $5.51 per 1M tokens
            },
            "claude-3-5-sonnet": {
                "input": 3.00 / 1000000,  # $3.00 per 1M tokens (预估价格)
                "output": 15.00 / 1000000  # $15.00 per 1M tokens (预估价格)
            },
            "claude-3-7-sonnet": {
                "input": 5.00 / 1000000,  # $5.00 per 1M tokens (预估价格)
                "output": 25.00 / 1000000  # $25.00 per 1M tokens (预估价格)
            }
        }

        # 标准化模型名称
        model_key = model.lower()
        if "claude-3-opus" in model_key:
            model_key = "claude-3-opus"
        elif "claude-3-7" in model_key or "claude-3.7" in model_key:
            model_key = "claude-3-7-sonnet"
        elif "claude-3-5" in model_key or "claude-3.5" in model_key:
            model_key = "claude-3-5-sonnet"
        elif "claude-3-sonnet" in model_key:
            model_key = "claude-3-sonnet"
        elif "claude-3-haiku" in model_key:
            model_key = "claude-3-haiku"
        elif "claude-2" in model_key:
            model_key = "claude-2"
        elif "claude-instant" in model_key:
            model_key = "claude-instant"

        if model_key not in pricing:
            raise ValueError(f"未知模型: {model}")

        # 计算成本
        input_cost = input_tokens * pricing[model_key]["input"]
        output_cost = output_tokens * pricing[model_key]["output"]
        total_cost = input_cost + output_cost

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }

    async def chat(self,
                   system_prompt: str,
                   user_prompt: str,
                   model: str = "claude-3-5-sonnet-20241022",
                   temperature: float = 0.7,
                   max_tokens: int = 3000,
                   timeout: int = 60
                   ) -> Dict[str, Any]:
        """
        调用Anthropic的Claude聊天接口（异步）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model: 模型名称，默认为"claude-3-7-sonnet"
            temperature: 温度参数，默认使用配置中的DEFAULT_TEMPERATURE
            max_tokens: 最大生成长度，默认使用配置中的DEFAULT_MAX_TOKENS
            timeout: 超时时间，默认为60秒

        Returns:
            返回生成的结果（dict）

        Raises:
            ExternalAPIError: 当调用Anthropic API出错时
            RateLimitError: 当遇到速率限制错误时
        """
        # 检查客户端是否初始化
        if not self.anthropic_client:
            raise ClaudeAPIError(
                "Anthropic client not initialized, chat functionality unavailable",
                {"details": "Please provide a valid Claude key"},
            )

        # 确保使用完整的模型名称
        full_model_name = self.model_map.get(model.lower(), model)

        try:
            # 调用Anthropic的聊天接口
            message = await self.anthropic_client.messages.create(
                model=full_model_name,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )

            cost = await self.calculate_claude_cost(model=full_model_name, input_tokens=message.usage.input_tokens, output_tokens=message.usage.output_tokens)

            # 将Anthropic响应转换为标准格式
            content = message.content[0].text if message.content else ""
            standardized_response = {
                "id": message.id,
                "model": message.model,
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "index": 0,
                        "finish_reason": message.stop_reason
                    }
                ],
                "usage": {
                    "prompt_tokens": message.usage.input_tokens,
                    "completion_tokens": message.usage.output_tokens,
                    "total_tokens": message.usage.input_tokens + message.usage.output_tokens
                },
                "cost": cost
            }

            # 记录基本响应信息
            logger.info(
                f"Claude响应: 模型={full_model_name}, "
                f"输出tokens={message.usage.output_tokens}, "
                f"输入tokens={message.usage.input_tokens}"
                f"输入成本={cost['input_cost']:.6f}, 输出成本={cost['output_cost']:.6f}, 总成本={cost['total_cost']:.6f}"
            )

            return standardized_response

        except AnthropicRateLimitError as e:
            # 处理速率限制错误
            logger.error(f"Anthropic速率限制错误: {str(e)}")
            raise ClaudeAPIError(
                "Error calling Claude API",
                {"details": str(e)},
            )

        except Exception as e:
            # 记录其他未预期错误
            logger.error(f"调用Claude时发生未预期错误: {str(e)}")
            traceback.print_exc()
            raise ClaudeAPIError(
                "Error calling Claude API",
                {"details": str(e)},
            )
