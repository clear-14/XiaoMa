"""模型配置业务层（PRD 5.1 模型设置：配置、测试连接、切换默认模型）。

安全规则（PRD 11.2）：
- API Key 使用 Fernet 加密后落库，接口只返回脱敏值；
- 任何错误信息与日志都不包含完整密钥；
- 已保存密钥无法解密时返回明确提示，要求重新填写。

产品决策（2026-11-07）：
- 删除默认模型后系统保持「无默认模型」状态并明确提示，不自动替用户选择。
"""

import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.crypto import (
    SecretDecryptionError,
    decrypt_secret,
    encrypt_secret,
    mask_secret,
)
from app.models.model_config import ModelConfig
from app.repositories.model_config_repository import ModelConfigRepository
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigOut,
    ModelConfigUpdate,
    TestConnectionOut,
)
from app.services.llm_client import LlmError, LlmRequest, create_llm_client
from app.services.llm_providers import resolve_base_url
from app.services.time_utils import utc_now_naive

CONNECTION_TEST_PROMPT = "请只回复：OK"
NO_DEFAULT_MODEL_MESSAGE = "尚未配置默认模型，请先在系统设置中添加模型配置并设为默认"


class ModelConfigService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ModelConfigRepository(db)

    # ------------------------------------------------------------ 查询

    def list_configs(self) -> list[ModelConfigOut]:
        return [self._to_out(config) for config in self.repo.list_configs()]

    def get_config(self, config_id: uuid.UUID) -> ModelConfigOut:
        return self._to_out(self._get_or_404(config_id))

    # ------------------------------------------------------------ 新增

    def create_config(self, payload: ModelConfigCreate) -> ModelConfigOut:
        if self.repo.list_configs() and payload.is_default:
            self.repo.clear_defaults()
        config = ModelConfig(
            name=payload.name,
            provider=payload.provider,
            model_name=payload.model_name,
            base_url=payload.base_url,
            api_key_encrypted=encrypt_secret(payload.api_key),
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            timeout=payload.timeout,
            is_default=payload.is_default,
        )
        self.repo.add(config)
        self.db.commit()
        return self._to_out(config)

    # ------------------------------------------------------------ 编辑

    def update_config(self, config_id: uuid.UUID, payload: ModelConfigUpdate) -> ModelConfigOut:
        config = self._get_or_404(config_id)
        data = payload.model_dump(exclude_unset=True)
        api_key = data.pop("api_key", None)
        if api_key is not None:
            config.api_key_encrypted = encrypt_secret(api_key)
        provider_changed = "provider" in data and data["provider"] != config.provider
        for key, value in data.items():
            setattr(config, key, value)
        # 切换服务商且未显式提供 base_url 时，清空旧端点以使用新服务商预设
        if provider_changed and "base_url" not in data:
            config.base_url = None

        # 更新后的组合校验：自定义兼容接口必须有 base_url
        if config.provider == "custom" and not config.base_url:
            self.db.rollback()
            raise HTTPException(status_code=422, detail="自定义兼容接口必须提供 base_url")
        try:
            resolve_base_url(config.provider, config.base_url)
        except ValueError as exc:
            self.db.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        self.db.commit()
        return self._to_out(config)

    # ------------------------------------------------------------ 删除

    def delete_config(self, config_id: uuid.UUID) -> None:
        """软删除配置；若删除的是默认模型，系统保持无默认状态（产品决策）。"""
        config = self._get_or_404(config_id)
        config.is_default = False
        config.deleted_at = utc_now_naive()
        self.db.commit()

    # ------------------------------------------------------------ 默认模型

    def set_default(self, config_id: uuid.UUID) -> ModelConfigOut:
        config = self._get_or_404(config_id)
        self.repo.clear_defaults()
        config.is_default = True
        self.db.commit()
        return self._to_out(config)

    # ------------------------------------------------------------ 连接测试

    async def test_connection(self, config_id: uuid.UUID) -> TestConnectionOut:
        """发送一次最小请求验证可用性。测试本身成功返回，ok=false 说明原因。"""
        config = self._get_or_404(config_id)
        llm_request = self._llm_request(config)
        client = create_llm_client(llm_request)
        try:
            reply, latency_ms, _usage = await client.complete(
                [{"role": "user", "content": CONNECTION_TEST_PROMPT}]
            )
        except LlmError as exc:
            return TestConnectionOut(
                ok=False, model=config.model_name, error=exc.message
            )
        return TestConnectionOut(
            ok=True,
            model=config.model_name,
            latency_ms=latency_ms,
            reply=reply[:200],
        )

    # ------------------------------------------------------------ 流式对话

    def prepare_chat_stream(
        self, config_id: uuid.UUID | None, messages: list[dict[str, str]]
    ) -> tuple[LlmRequest, list[dict[str, str]]]:
        """解析使用的模型配置并解密密钥；配置问题在此阶段以 HTTP 错误明确返回。"""
        if config_id is not None:
            config = self._get_or_404(config_id)
        else:
            config = self.repo.get_default()
            if config is None:
                raise HTTPException(status_code=409, detail=NO_DEFAULT_MODEL_MESSAGE)
        return self._llm_request(config), messages

    def get_default_llm_request(self) -> tuple[LlmRequest, str]:
        """读取默认模型并解密密钥，返回 (请求参数, 模型名)。

        AI 教学对话使用系统默认模型；未配置时在开始流式响应前明确提示（409）。
        """
        config = self.repo.get_default()
        if config is None:
            raise HTTPException(status_code=409, detail=NO_DEFAULT_MODEL_MESSAGE)
        return self._llm_request(config), config.model_name

    def stream_chat(self, llm_request: LlmRequest, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """返回流式增量文本迭代器（provider 错误由迭代过程抛出 LlmError）。"""
        return create_llm_client(llm_request).stream(messages)

    # ------------------------------------------------------------ 内部工具

    def _get_or_404(self, config_id: uuid.UUID) -> ModelConfig:
        config = self.repo.get_config(config_id)
        if config is None:
            raise HTTPException(status_code=404, detail="模型配置不存在")
        return config

    @staticmethod
    def _llm_request(config: ModelConfig) -> LlmRequest:
        if not config.api_key_encrypted:
            raise HTTPException(status_code=409, detail="该模型配置缺少 API Key，请重新填写")
        try:
            api_key = decrypt_secret(config.api_key_encrypted)
        except SecretDecryptionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        try:
            resolve_base_url(config.provider, config.base_url)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return LlmRequest(
            provider=config.provider,
            model_name=config.model_name,
            base_url=config.base_url,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )

    @staticmethod
    def _to_out(config: ModelConfig) -> ModelConfigOut:
        masked = None
        if config.api_key_encrypted:
            try:
                masked = mask_secret(decrypt_secret(config.api_key_encrypted))
            except SecretDecryptionError:
                masked = "****（无法解密，请重新填写）"
        return ModelConfigOut(
            id=config.id,
            name=config.name,
            provider=config.provider,
            model_name=config.model_name,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            is_default=config.is_default,
            has_api_key=bool(config.api_key_encrypted),
            api_key_masked=masked,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
