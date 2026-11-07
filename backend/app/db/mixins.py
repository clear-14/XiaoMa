"""通用模型 Mixin。"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    """当前 UTC 时间，用于 created_at / updated_at。

    SQLite 不保存时区信息（读回为 naive datetime），因此统一约定：
    应用侧全部使用无时区（naive）的 UTC 时间，避免 aware/naive 混用导致比较报错。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UUIDPkMixin:
    """UUID 主键。"""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """创建时间与更新时间（应用侧维护，数据库端默认值兜底）。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """软删除标记：deleted_at 非空即视为已删除。"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )
