"""模型配置数据访问层。"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig


class ModelConfigRepository:
    """LLM 模型配置的数据库读写（查询统一过滤软删除）。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_configs(self) -> list[ModelConfig]:
        """全部未删除配置，按创建时间升序。"""
        stmt = (
            select(ModelConfig)
            .where(ModelConfig.deleted_at.is_(None))
            .order_by(ModelConfig.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_config(self, config_id: uuid.UUID) -> ModelConfig | None:
        stmt = select(ModelConfig).where(
            ModelConfig.id == config_id, ModelConfig.deleted_at.is_(None)
        )
        return self.db.scalars(stmt).first()

    def get_default(self) -> ModelConfig | None:
        stmt = select(ModelConfig).where(
            ModelConfig.is_default.is_(True), ModelConfig.deleted_at.is_(None)
        )
        return self.db.scalars(stmt).first()

    def clear_defaults(self) -> None:
        """取消所有配置的默认标记（设置/删除默认模型时使用）。"""
        self.db.execute(update(ModelConfig).values(is_default=False))

    def add(self, config: ModelConfig) -> None:
        self.db.add(config)

    def flush(self) -> None:
        self.db.flush()
