"""学习计划模型：计划、计划版本与计划项目（PRD 5.1 学习计划 + PRD 9 版本记录规则）。

设计要点：
- 计划调整采用版本记录，不覆盖历史版本（PRD 9）：每次调整生成新版本，
  确认后旧版本转为 superseded 保留，已完成任务随新版本携带、历史版本原样保留；
- 计划存在「草稿→确认」流程（PRD 4.1）：创建/调整先生成草稿版本，
  用户确认后才生效（plan.current_version_number 指向生效版本）。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin
from app.models.course import Course, KnowledgePoint
from app.models.user import User

# 计划状态：draft 未确认过（尚无生效版本）/ active 已有生效版本
PLAN_STATUSES: tuple[str, ...] = ("draft", "active")
# 版本状态：draft 待确认 / active 当前生效 / superseded 已被新版本取代
PLAN_VERSION_STATUSES: tuple[str, ...] = ("draft", "active", "superseded")
# 计划项目状态：pending 待完成 / completed 已完成（完成入口由每日任务阶段实现）
PLAN_ITEM_STATUSES: tuple[str, ...] = ("pending", "completed")


class LearningPlan(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """学习计划。单用户产品下同一用户当前至多一份未删除计划。"""

    __tablename__ = "learning_plans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    # 计划开始日（首次确认时设定，后续调整保持不变；day_index 相对此日计算）
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 当前生效版本号；未确认过任何版本时为 None
    current_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 待确认草稿版本号；无待确认版本时为 None
    pending_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    versions: Mapped[list[LearningPlanVersion]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="LearningPlanVersion.version_number",
    )
    course: Mapped[Course] = relationship()
    user: Mapped[User] = relationship()


class LearningPlanVersion(UUIDPkMixin, TimestampMixin, Base):
    """计划版本。每个版本记录当时的计划参数快照与全部计划项目。

    版本为历史记录，不做软删除：计划软删除时版本随级联规则由应用层处理。
    """

    __tablename__ = "learning_plan_versions"
    __table_args__ = (
        UniqueConstraint("plan_id", "version_number", name="plan_version"),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    # 计划参数快照
    learning_goal: Mapped[str] = mapped_column(String(500), nullable=False)
    daily_study_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # 排期实际总天数（由后端排期算法计算，见 plan_scheduler）
    computed_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # 初始诊断快照：当前编程基础（L0/L1/L2）
    current_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 阶段 5 起：有掌握证据、实际不排期的知识点稳定 code 列表。
    # 证据来自知识点测验或诊断测验（status=mastered），自述不算。
    # 历史版本里该列可能装着「诊断自述」的 code，读取时以掌握度表为准重新计算。
    mastered_kp_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 用户自述完成但未验证的知识点（阶段 5）：保留当时的说法，但不用于跳过。
    self_reported_kp_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 阶段 6：生成/调整计划时实际使用的八类输入快照（学习目标、每日时间、
    # 能力等级、已掌握/未掌握、课程前置、课程预计时间、测验表现、诊断证据）。
    # 只作审计与展示，不参与排期算法；排期仍以确定性的掌握证据为准。
    plan_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    plan: Mapped[LearningPlan] = relationship(back_populates="versions")
    items: Mapped[list[LearningPlanItem]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class LearningPlanItem(UUIDPkMixin, TimestampMixin, Base):
    """计划项目：某知识点安排在计划的第几天。

    调整计划时：已完成项目携带到新版本（保留原 day_index 与完成时间），
    未完成项目重新排期；旧版本项目原样保留（PRD：调整后历史版本仍然保留，
    已完成任务不因调整丢失）。
    """

    __tablename__ = "learning_plan_items"
    __table_args__ = (
        UniqueConstraint("version_id", "knowledge_point_id", name="version_kp"),
    )

    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_plan_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    version: Mapped[LearningPlanVersion] = relationship(back_populates="items")
    knowledge_point: Mapped[KnowledgePoint] = relationship()
