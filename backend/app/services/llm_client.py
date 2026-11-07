"""统一 LLM Provider 客户端（OpenAI 兼容协议：DeepSeek / 通义千问 / OpenAI / 自定义）。

职责：
- 非流式调用（连接测试）与流式调用（SSE 增量输出）；
- 超时、网络错误、服务端错误统一转换为带明确中文提示的 LlmError；
- 安全：不在日志与错误信息中出现 API Key（错误信息中的密钥统一替换为 ***）。

PRD 7.3：模型超时、不可用、空回复必须可识别，失败时返回明确提示，不得无限等待。
"""

import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from app.services.llm_providers import resolve_base_url

logger = logging.getLogger("xiaoma.llm")

EMPTY_REPLY_MESSAGE = "模型返回了空回复"


class LlmError(Exception):
    """统一的模型调用错误（message 可直接展示给用户）。"""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class LlmRequest:
    """一次模型调用所需参数（从模型配置解密后组装，不含数据库会话）。"""

    provider: str
    model_name: str
    base_url: str | None
    api_key: str
    temperature: float
    max_tokens: int
    timeout: int


class LlmClient:
    """OpenAI 兼容协议的统一客户端。"""

    def __init__(self, request: LlmRequest, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.request = request
        self.base_url = resolve_base_url(request.provider, request.base_url)
        self._transport = transport

    @property
    def _chat_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.request.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, messages: list[dict[str, str]], *, stream: bool, max_tokens: int | None = None) -> dict:
        return {
            "model": self.request.model_name,
            "messages": messages,
            "temperature": self.request.temperature,
            "max_tokens": max_tokens or self.request.max_tokens,
            "stream": stream,
        }

    def _sanitize(self, text: str) -> str:
        """错误信息脱敏：任何位置出现的 API Key 替换为 ***（日志安全要求）。"""
        key = self.request.api_key
        if key:
            text = text.replace(key, "***")
        return text[:300]

    def _provider_message(self, body: str) -> str:
        """从服务商错误响应中提取可读信息（JSON error.message / message / detail）。"""
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return self._sanitize(body.strip())
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict) and error.get("message"):
                return self._sanitize(str(error["message"]))
            for field in ("message", "detail"):
                if data.get(field):
                    return self._sanitize(str(data[field]))
        return self._sanitize(body.strip())

    def _error_from_status(self, status: int, body: str) -> LlmError:
        detail = self._provider_message(body)
        if status in (401, 403):
            message = f"模型服务拒绝访问（HTTP {status}）：API Key 无效或无权限"
        elif status == 404:
            message = "模型或接口地址不存在（HTTP 404），请检查 base_url 与 model_name"
        elif status == 429:
            message = "模型服务请求过于频繁或额度不足（HTTP 429），请稍后重试"
        elif status == 400:
            message = f"模型请求被拒绝（HTTP 400）：{detail}"
        elif status >= 500:
            message = f"模型服务异常（HTTP {status}），请稍后重试"
        else:
            message = f"模型请求失败（HTTP {status}）：{detail}"
        return LlmError(message, status_code=502)

    @staticmethod
    def _network_error(exc: Exception) -> LlmError:
        if isinstance(exc, httpx.TimeoutException):
            return LlmError("模型请求超时，请稍后重试或在模型配置中调大 timeout", status_code=504)
        if isinstance(exc, httpx.HTTPError):
            return LlmError("无法连接模型服务，请检查网络或 base_url 配置", status_code=502)
        return LlmError("模型调用失败，请稍后重试", status_code=502)

    # ------------------------------------------------------------ 非流式

    async def complete(self, messages: list[dict[str, str]]) -> tuple[str, int, dict | None]:
        """非流式调用，返回 (回复文本, 耗时毫秒, usage)。用于连接测试。"""
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.request.timeout),
                transport=self._transport,
            ) as client:
                response = await client.post(
                    self._chat_url,
                    headers=self._headers,
                    json=self._payload(messages, stream=False, max_tokens=min(16, self.request.max_tokens)),
                )
        except httpx.HTTPError as exc:
            raise self._network_error(exc) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code != 200:
            raise self._error_from_status(response.status_code, response.text)
        try:
            data = response.json()
            content = data["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LlmError("模型返回了无法解析的响应") from exc
        if not str(content).strip():
            raise LlmError(EMPTY_REPLY_MESSAGE)
        return str(content).strip(), latency_ms, data.get("usage")

    # ------------------------------------------------------------ 流式

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """流式调用：逐段产出增量文本；空回复/超时/服务错误抛出 LlmError。"""
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.request.timeout),
                transport=self._transport,
            ) as client:
                async with client.stream(
                    "POST",
                    self._chat_url,
                    headers=self._headers,
                    json=self._payload(messages, stream=True),
                ) as response:
                    if response.status_code != 200:
                        body = (await response.aread()).decode("utf-8", "replace")
                        raise self._error_from_status(response.status_code, body)
                    saw_content = False
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or line.startswith(":"):
                            continue
                        if not line.startswith("data:"):
                            continue
                        payload = line[len("data:"):].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                        except json.JSONDecodeError as exc:
                            raise LlmError("模型流式响应解析失败") from exc
                        if isinstance(chunk, dict) and chunk.get("error"):
                            error = chunk["error"]
                            message = error.get("message") if isinstance(error, dict) else str(error)
                            raise LlmError(self._sanitize(f"模型返回错误：{message}"))
                        for choice in (chunk.get("choices") or []) if isinstance(chunk, dict) else []:
                            delta = choice.get("delta") or {}
                            content = delta.get("content")
                            if content:
                                saw_content = True
                                yield content
                    if not saw_content:
                        raise LlmError(EMPTY_REPLY_MESSAGE)
        except httpx.HTTPError as exc:
            raise self._network_error(exc) from exc


def create_llm_client(request: LlmRequest) -> LlmClient:
    """客户端工厂（测试可替换以实现本地模拟服务）。"""
    return LlmClient(request)
