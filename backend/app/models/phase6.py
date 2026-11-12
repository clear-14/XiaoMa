"""阶段 6：学习闭环新增表（计划调整提案 / 复习请求）。

设计约束：
- ``plan_adjustment_proposals`` 是「待用户确认的方案」。提案阶段**不写任何
  学习计划版本**，只有确认接口才生成并生效新版本，因此 Agent 不可能
  「未经确认保存学习计划修改」。
- ``review_requests`` 是用户或 Agent 提出的复习申请，按「用户 + 知识点 +
  日期」唯一，重复请求幂等返回既有记录；它本身不是复习任务，真正的复习
  任务仍由错题本 / 掌握度服务按真实证据生成（不伪造任务）。
- 两张表都只追加状态变化，不覆盖历史；提案确认/拒绝后保留原文供审计。
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
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPkMixin
from app.models.course import KnowledgePoint
from app.models.learning_plan import LearningPlan
from app.models.user import User

# 提案状态：待确认 / 已确认并生效 / 已拒绝（不生效）
PROPOSAL_STATUSES: tuple[str, ...] = ("proposed", "confirmed", "rejected")
# 复习申请状态：待安排 / 已关联复习任务 / 已完成
REVIEW_REQUEST_STATUSES: tuple[str, ...] = ("pending", "scheduled", "completed")

# 动态计划调整的六类触发条件（顺序固定，测试与文档共用）
ADJUSTMENT_TRIGGERS: tuple[str, ...] = (
    "consecutive_quiz_failures",   # 连续测验不通过
    "mastered_downstream_points",  # 已掌握多个后续知识点
    "weak_foundation",             # 某项基础能力明显不足
    "learning_goal_changed",       # 用户改变学习目标
    "daily_minutes_increased",     # 用户需要增加每日学习时间
    "review_requested",            # 用户请求复习以前的内容
)

TRIGGER_LABELS: dict[str, str] = {
    "consecutive_quiz_failures": "连续测验不通过",
    "mastered_downstream_points": "已掌握多个后续知识点",
    "weak_foundation": "某项基础能力明显不足",
    "learning_goal_changed": "用户改变学习目标",
    "daily_minutes_increased": "用户需要增加每日学习时间",
    "review_requested": "用户请求复习以前的内容",
}


class PlanAdjustmentProposal(UUIDPkMixin, TimestampMixin, Base):
    """动态计划调整提案（确认前不产生任何计划版本）。"""

    __tablename__ = "plan_adjustment_proposals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'confirmed', 'rejected')",
            name="ck_plan_adjustment_proposals_status",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="proposed", index=True
    )
    # 触发条件 code 列表（见 ADJUSTMENT_TRIGGERS）
    triggers: Mapped[list] = mapped_column(JSON, nullable=False)
    # 可读的调整理由（展示给用户，确认前必须看到）
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # 建议变更参数：learning_goal / daily_study_minutes / expected_duration_days
    changes: Mapped[dict] = mapped_column(JSON, nullable=False)
    # 方案预览：当前值 → 建议值 + 预计影响 + 补学/复习清单
    preview: Mapped[dict] = mapped_column(JSON, nullable=False)
    # 提案来源：agent / user / api
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 确认后实际生效的版本号（未确认时为 None）
    resulting_version_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    user: Mapped[User] = relationship()
    plan: Mapped[LearningPlan] = relationship()


class ReviewRequest(UUIDPkMixin, TimestampMixin, Base):
    """复习申请记录（幂等：同一用户同一知识点同一天至多一条）。"""

    __tablename__ = "review_requests"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "knowledge_point_id", "request_date",
            name="uq_review_requests_user_kp_date",
        ),
        CheckConstraint(
            "status IN ('pending', 'scheduled', 'completed')",
            name="ck_review_requests_status",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    # 关联的触发条件（可选，供动态调整检测使用）
    trigger: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship()
    knowledge_point: Mapped[KnowledgePoint] = relationship()
