"""每日学习任务模型（PRD 5.1 每日任务 / PRD 9 防重复机制）。

任务生成规则（任务书阶段 6 + 产品决策 2026-11-07）：
- 「滚动追赶」：取当前生效计划中最早的、还有未完成项目的计划日，该日全部
  未完成且未掌握的知识点生成当日任务；前一天没做完的，新的一天重新生成
  （旧任务保留为历史记录）；
- 防重复机制：接口层先查后生成，数据库层以 user_id + task_date +
  knowledge_point_id 唯一约束兜底（同一用户同一天同一知识点至多一条任务）；
- 任务完成只代表任务完成，不代表知识点掌握（掌握须经测验验证，
  见 learning_profiles 与 PRD 6.1）。

阶段 7 增量（自主选题，`docs/课程扩展阶段7_自主选题与学习完成度.md`）：
- 新增 ``source`` 区分任务来源：``plan`` 由学习计划自动排期下发，
  ``self_selected`` 由用户自己加入今日学习；
- ``plan_id`` 改为可空：计划外课程的自选任务不挂计划（``source='plan'``
  时仍必填，由 Service 层保证，数据库层不做跨列约束以免迁移复杂化）；
- 唯一约束 ``user_date_kp`` 对两种来源同时生效，同一天同一知识点仍只有一条，
  因此自选与自动生成天然不会重复；
- 学习完成度仍复用 ``status`` 三档，不新增状态机；「学习中」可跨天承接。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text as sa_text

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPkMixin
from app.models.course import Chapter, Course, KnowledgePoint, Lesson
from app.models.learning_plan import LearningPlan
from app.models.user import User

# 任务状态机：pending 待开始 / learning 学习中 / completed 已完成
DAILY_TASK_STATUSES: tuple[str, ...] = ("pending", "learning", "completed")

# 学习完成度对外标签（阶段 7）：只有三档，与状态机一一对应。
# 注意「已学完」不等于「已掌握」——掌握只由测验/练习/诊断证据推进。
DAILY_TASK_STATUS_LABELS: dict[str, str] = {
    "pending": "未开始",
    "learning": "学习中",
    "completed": "已学完（未验证）",
}

# 任务来源（阶段 7）：计划自动排期 / 用户自主加入今日学习
DAILY_TASK_SOURCES: tuple[str, ...] = ("plan", "self_selected")
SOURCE_PLAN = "plan"
SOURCE_SELF_SELECTED = "self_selected"


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
        CheckConstraint("source IN ('plan', 'self_selected')", name="source"),
        # 今日任务分组查询（计划任务 / 自选任务）走这条索引
        Index("ix_daily_tasks_date_source", "user_id", "task_date", "source"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 阶段 7：计划外自选任务不挂计划，故允许为空；
    # source='plan' 的任务仍由 Service 层保证必填（数据库层不做跨列约束）。
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=True, index=True
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 阶段 6：任务生成时固化的真实课程层级引用（课程 / 章节即 CourseModule /
    # 课时）。历史任务由迁移按知识点归属回填；三列可空仅为兼容升级前的记录，
    # 新生成的任务必须由 DailyTaskService 全部填齐，不允许引用不存在的课时。
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True, index=True
    )
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # 任务所属日期（应用统一使用 naive UTC 约定）
    task_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # 生成时所属计划日快照（计划调整后历史任务仍可追溯原安排）
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # 阶段 7：任务来源。plan=计划自动排期；self_selected=用户自主加入今日学习。
    # server_default 与迁移保持一致，避免 alembic check 检测到服务端默认值漂移。
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=SOURCE_PLAN,
        server_default=sa_text("'plan'"),
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    # 标记开始学习时间
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 任务完成时间（任务书要求记录）
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped[LearningPlan] = relationship()
    user: Mapped[User] = relationship()
    knowledge_point: Mapped[KnowledgePoint] = relationship()
    course: Mapped[Course | None] = relationship()
    chapter: Mapped[Chapter | None] = relationship()
    lesson: Mapped[Lesson | None] = relationship()
