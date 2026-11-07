"""LLM 模型配置模型。"""

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class ModelConfig(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """LLM 模型配置。

    统一 Provider，兼容 DeepSeek、通义千问、OpenAI 兼容接口及自定义兼容端点（PRD 5.1）。
    """

    __tablename__ = "model_configs"

    name: Mapped[str] = mapped_column(String(64), nullable=False)  # 配置显示名，如"DeepSeek 默认"
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # deepseek / qwen / openai / custom
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)  # 模型标识，如 deepseek-chat
    base_url: Mapped[str | None] = mapped_column(String(256), nullable=True)  # 自定义兼容端点
    # 加密后的 API Key（Fernet 密文，见 app/core/crypto.py）；接口只输出脱敏值
    api_key_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    temperature: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.7, server_default="0.7"
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2048, server_default="2048"
    )
    # 单次请求超时（秒）
    timeout: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60, server_default="60"
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
