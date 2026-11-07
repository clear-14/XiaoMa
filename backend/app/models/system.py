"""系统设置模型。"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class SystemSetting(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """系统级键值设置（单用户产品的全局配置，不含 user_id）。"""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[str | None] = mapped_column(String(2000), nullable=True)
