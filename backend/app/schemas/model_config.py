"""模型配置接口 Schema（PRD 5.1 模型设置）。

安全约定：请求中可提交明文 api_key（仅用于写入，立即加密落库）；
任何响应都不返回明文或密文，只返回脱敏值 api_key_masked。
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

ProviderName = Literal["deepseek", "qwen", "openai", "custom"]


def _validate_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().rstrip("/")
    if not value:
        return None
    if not value.startswith(("http://", "https://")):
        raise ValueError("base_url 必须以 http:// 或 https:// 开头")
    return value


class ModelConfigCreate(BaseModel):
    """添加模型配置。"""

    name: str = Field(min_length=1, max_length=64)
    provider: ProviderName
    model_name: str = Field(min_length=1, max_length=128)
    base_url: str | None = Field(default=None, max_length=256)
    api_key: str = Field(min_length=1, max_length=256)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1, le=65536)
    timeout: int = Field(default=60, ge=1, le=600)
    is_default: bool = False

    @field_validator("base_url")
    @classmethod
    def _check_base_url(cls, value: str | None) -> str | None:
        return _validate_base_url(value)

    @model_validator(mode="after")
    def _require_base_url_for_custom(self) -> "ModelConfigCreate":
        if self.provider == "custom" and not self.base_url:
            raise ValueError("自定义兼容接口必须提供 base_url")
        return self


class ModelConfigUpdate(BaseModel):
    """编辑模型配置（部分更新；api_key 不提交表示保持原密钥不变）。"""

    name: str | None = Field(default=None, min_length=1, max_length=64)
    provider: ProviderName | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=128)
    base_url: str | None = Field(default=None, max_length=256)
    api_key: str | None = Field(default=None, min_length=1, max_length=256)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=65536)
    timeout: int | None = Field(default=None, ge=1, le=600)

    @field_validator("base_url")
    @classmethod
    def _check_base_url(cls, value: str | None) -> str | None:
        return _validate_base_url(value)


class ModelConfigOut(BaseModel):
    """模型配置信息（脱敏，不含任何密钥原文/密文）。"""

    id: UUID
    name: str
    provider: str
    model_name: str
    base_url: str | None
    temperature: float
    max_tokens: int
    timeout: int
    is_default: bool
    has_api_key: bool
    api_key_masked: str | None
    created_at: datetime
    updated_at: datetime


class TestConnectionOut(BaseModel):
    """连接测试结果：测试本身总是成功返回，ok=false 时 error 说明原因。"""

    ok: bool
    model: str
    latency_ms: int | None = None
    reply: str | None = None
    error: str | None = None
