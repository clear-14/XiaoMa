"""每日学习任务模型（PRD 5.1 每日任务 / PRD 9 防重复机制）。

任务生成规则（任务书阶段 6 + 产品决策 2026-11-07）：
- 「滚动追赶」：取当前生效计划中最早的、还有未完成项目的计划日，该日全部
  未完成且未掌握的知识点生成当日任务；前一天没做完的，新的一天重新生成
  （旧任务保留为历史记录）；
- 防重复机制：接口层先查后生成，数据库层以 user_id + task_date +
  knowledge_point_id 唯一约束兜底（同一用户同一天同一知识点至多一条任务）；
- 任务完成只代表任务完成，不代表知识点掌握（掌握须经测验验证，
  见 learning_profiles 与 PRD 6.1）。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPkMixin
from app.models.course import KnowledgePoint
from app.models.learning_plan import LearningPlan
from app.models.user import User

# 任务状态机：pending 待开始 / learning 学习中 / completed 已完成
DAILY_TASK_STATUSES: tuple[str, ...] = ("pending", "learning", "completed")


class DailyTask(UUIDPkMixin, TimestampMixin, Base):
    """某用户某天的学习任务（对应计划中的某个知识点）。

    任务为历史记录，不做软删除：计划/知识点删除时任务随外键级联删除。
    """

    __tablename__ = "daily_tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "task_date", "knowledge_point_id", name="user_date_kp"),
        CheckConstraint(
            "status IN ('pending', 'learning', 'completed')", name="status"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 任务所属日期（应用统一使用 naive UTC 约定）
    task_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # 生成时所属计划日快照（计划调整后历史任务仍可追溯原安排）
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    # 标记开始学习时间
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 任务完成时间（任务书要求记录）
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped[LearningPlan] = relationship()
    user: Mapped[User] = relationship()
    knowledge_point: Mapped[KnowledgePoint] = relationship()
