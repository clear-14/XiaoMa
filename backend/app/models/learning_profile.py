"""知识点学习档案模型：用户对单个知识点的掌握状态（PRD 6.1 知识点状态）。

与 user_profiles（学习目标/基础/时长/偏好，PRD 5.1 用户初始化）区分：
本表记录每个用户对每个知识点的学习状态，为测验、复习与学习档案展示提供数据基础。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPkMixin

# PRD 6.1 知识点状态机取值。用户点击任务完成不得直接置为 mastered，
# 必须经系统规定的掌握验证（由测验阶段实现）。
LEARNING_STATUSES: tuple[str, ...] = (
    "not_started",
    "learning",
    "pending_verification",
    "mastered",
    "review_due",
)


class LearningProfile(UUIDPkMixin, TimestampMixin, Base):
    """单个用户对单个知识点的学习状态记录。

    每个用户对每个知识点至多一条记录（user_id + knowledge_point_id 唯一）。
    本表为进度记录，不做软删除：知识点删除时状态记录级联删除。
    """

    __tablename__ = "learning_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "knowledge_point_id", name="user_kp"),
        CheckConstraint(
            "status IN ('not_started', 'learning', 'pending_verification', 'mastered', 'review_due')",
            name="status",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    # 首次开始学习时间；通过掌握验证的时间；最近一次复习时间
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    knowledge_point = relationship("KnowledgePoint")
