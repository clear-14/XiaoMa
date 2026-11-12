"""知识点掌握度模型（阶段 5）。

需求背景：原 ``learning_profiles`` 只有 5 个 PRD 6.1 状态
（not_started / learning / pending_verification / mastered / review_due），
无法区分「用户自述完成」「基础理解通过」「应用练习通过」「真正掌握」
「需要复习」。本模块把这五种情况拆成 7 个状态，并为每次状态变化留下证据流水。

与原有状态的关系（避免冲突，而不是推翻）：
- ``learning_profiles`` 继续作为「学习进度状态」被计划、每日任务、测验范围读取，
  30 多个既有用例与前端依赖它，不改其取值集合与 CHECK 约束；
- ``knowledge_mastery`` 是新的「掌握度状态」，粒度同为「用户 × 知识点」，
  每次写入后由 Service 投影回 ``learning_profiles``（见 ``MASTERY_TO_LEGACY``），
  两边永远同源，不出现「掌握度说已掌握、进度说没学」的矛盾；
- 历史数据（只有 learning_profiles 没有 knowledge_mastery）在首次读取时
  按 ``LEGACY_TO_MASTERY`` 补建，不丢老用户状态。

设计约束：
- 用户自述（self_report）只能进入 SELF_REPORTED_COMPLETED，
  代码路径上不存在「自述 → MASTERED」的分支；
- 每次状态变化必须写一条 ``mastery_evidence``，包含来源、关联的测验记录/
  练习记录、正确率、题目难度与验证时间，历史不覆盖；
- 一张表只表达一件事：``knowledge_mastery`` 是当前态（唯一），
  ``mastery_evidence`` 是流水（多行），``exercise_attempts`` 是练习记录。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPkMixin

# 7 个掌握度状态（需求「二、知识点状态」）。
MASTERY_STATUSES: tuple[str, ...] = (
    "not_started",  # NOT_STARTED：未开始
    "learning",  # LEARNING：学习中
    "self_reported_completed",  # SELF_REPORTED_COMPLETED：用户自述完成
    "understood",  # UNDERSTOOD：通过基础理解检查
    "applied",  # APPLIED：通过应用练习
    "mastered",  # MASTERED：通过掌握验证
    "needs_review",  # NEEDS_REVIEW：需要复习
)

# 状态的中文说明（接口与文档共用一份，避免前端/文档各写一套说法）。
MASTERY_STATUS_LABELS: dict[str, str] = {
    "not_started": "未开始",
    "learning": "学习中",
    "self_reported_completed": "用户自述完成",
    "understood": "基础理解通过",
    "applied": "应用练习通过",
    "mastered": "真正掌握",
    "needs_review": "需要复习",
}

# 掌握等级：只用于「向上推进不降级」的比较。
# needs_review 是分支状态（可能出现在任何等级之后），不参与比较；
# self_reported_completed 与 learning 只差一档，代表「用户说学完了」。
MASTERY_RANK: dict[str, int] = {
    "not_started": 0,
    "learning": 1,
    "self_reported_completed": 2,
    "understood": 3,
    "applied": 4,
    "mastered": 5,
}

# 旧状态 → 新状态：历史数据（只有 learning_profiles）首次读取时补建掌握记录。
# pending_verification 的原意就是「用户已报告完成，等待掌握验证」，映射为自述完成；
# review_due 映射为需要复习。
LEGACY_TO_MASTERY: dict[str, str] = {
    "not_started": "not_started",
    "learning": "learning",
    "pending_verification": "self_reported_completed",
    "mastered": "mastered",
    "review_due": "needs_review",
}

# 新状态 → 旧状态：写回 learning_profiles，保证计划排期、每日任务、
# 测验范围这些既有链路不需要认识新状态。
# UNDERSTOOD / APPLIED 在旧模型里都叫「等待验证」，但都还允许继续测验；
# MASTERED 才投影成旧 mastered（每日任务与排期据此跳过）。
MASTERY_TO_LEGACY: dict[str, str] = {
    "not_started": "not_started",
    "learning": "learning",
    "self_reported_completed": "pending_verification",
    "understood": "pending_verification",
    "applied": "pending_verification",
    "mastered": "mastered",
    "needs_review": "review_due",
}

# 掌握证据来源：自述 / 练习 / 知识点测验 / 诊断（跳级）测验。
MASTERY_EVIDENCE_SOURCES: tuple[str, ...] = (
    "self_report",
    "exercise",
    "quiz",
    "placement",
)

# 证据来源的中文说明（接口直接返回，便于前端展示「凭什么算掌握」）。
EVIDENCE_SOURCE_LABELS: dict[str, str] = {
    "self_report": "用户自述完成",
    "exercise": "应用练习",
    "quiz": "知识点测验",
    "placement": "诊断测验（跳级验证）",
}

# 可以被跳过的状态：只有真正掌握。自述、基础理解、应用练习都不足以跳过。
SKIPPABLE_STATUSES: tuple[str, ...] = ("mastered",)

# 视为「已学过」的状态：供诊断与复习建议判断是否需要安排学习任务。
LEARNED_MASTERY_STATUSES: tuple[str, ...] = (
    "learning",
    "self_reported_completed",
    "understood",
    "applied",
    "mastered",
    "needs_review",
)

# 练习判定结果。
EXERCISE_RESULTS: tuple[str, ...] = ("passed", "failed")


class KnowledgeMastery(UUIDPkMixin, TimestampMixin, Base):
    """用户对单个知识点的当前掌握状态（一知识点一条）。

    需求「三、掌握证据」要求的字段在这里落两份：
    当前态落在本表（正确率、难度、状态、验证时间、最近一次测验/练习记录），
    历史流水落在 ``mastery_evidence``，两者由 Service 同时写入。
    """

    __tablename__ = "knowledge_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "knowledge_point_id", name="user_kp_mastery"),
        CheckConstraint(
            "status IN ('not_started', 'learning', 'self_reported_completed', "
            "'understood', 'applied', 'mastered', 'needs_review')",
            name="mastery_status",
        ),
        Index("ix_knowledge_mastery_user_status", "user_id", "status"),
    )

    # 单用户模型：仍写 user_id，保留多用户扩展空间
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_started"
    )
    # 最近一次验证的正确率（0—100）；自述不产生正确率，保持为空
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 最近一次验证所用题目的难度（beginner / intermediate / advanced）。
    # 难度参与掌握判定说明，不允许只报「通过了」而不报难度。
    quiz_difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 最近一次知识点测验 / 诊断测验
    quiz_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="SET NULL"), nullable=True
    )
    # 最近一次应用练习
    exercise_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exercise_attempts.id", ondelete="SET NULL"), nullable=True
    )
    # 累计有效证据条数（自述也算一条，但单独可查）
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 用户自述完成的时间（需求「用户自述完成不能自动标记为 MASTERED」，
    # 因此自述时间与验证时间分开存，不能互相覆盖）
    self_reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 状态被验证性证据（练习/测验）确认的时间
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 进入 needs_review 的时间；重新验证通过后清空
    review_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    knowledge_point = relationship("KnowledgePoint")
    evidence: Mapped[list[MasteryEvidence]] = relationship(
        back_populates="mastery",
        cascade="all, delete-orphan",
        order_by="MasteryEvidence.created_at",
    )


class MasteryEvidence(UUIDPkMixin, TimestampMixin, Base):
    """掌握证据流水（只追加，不覆盖）。

    一条证据 = 一次「凭什么改状态」的记录：自述一次、交一次练习、考一次测验，
    都各留一条。历史测验与练习记录因此可以长期回溯（需求「学习记录和测验历史保留」）。
    """

    __tablename__ = "mastery_evidence"
    __table_args__ = (
        CheckConstraint(
            "source IN ('self_report', 'exercise', 'quiz', 'placement')",
            name="source",
        ),
        CheckConstraint(
            "status_after IN ('not_started', 'learning', 'self_reported_completed', "
            "'understood', 'applied', 'mastered', 'needs_review')",
            name="status_after",
        ),
        Index(
            "ix_mastery_evidence_user_kp",
            "user_id",
            "knowledge_point_id",
            "created_at",
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
    # 归属的掌握记录（同一用户同一知识点只有一条，便于按知识点取全部证据）
    mastery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_mastery.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    status_before: Mapped[str] = mapped_column(String(32), nullable=False)
    status_after: Mapped[str] = mapped_column(String(32), nullable=False)
    # 关联的练习记录 / 测验记录（两者最多一个非空；自述都为空）
    exercise_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exercise_attempts.id", ondelete="SET NULL"), nullable=True
    )
    quiz_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="SET NULL"), nullable=True
    )
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    quiz_difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 可读结论（为什么升级/为什么降级），与测验的 reasons 同风格
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 验证时间：自述证据记自述时间，练习/测验证据记判定时间
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    mastery: Mapped[KnowledgeMastery] = relationship(back_populates="evidence")
    knowledge_point = relationship("KnowledgePoint")
    exercise_attempt: Mapped[ExerciseAttempt | None] = relationship(
        foreign_keys=[exercise_attempt_id]
    )
    quiz_attempt = relationship("QuizAttempt", foreign_keys=[quiz_attempt_id])


class ExerciseAttempt(UUIDPkMixin, TimestampMixin, Base):
    """知识点练习提交记录（应用练习证据）。

    V1.0 不执行用户代码：判定方式是「参考答案二元组覆盖率」的确定性文本比对，
    评分依据（覆盖率、缺失片段）随记录持久化，供用户自查与审计。
    """

    __tablename__ = "exercise_attempts"
    __table_args__ = (
        CheckConstraint("result IN ('passed', 'failed')", name="result"),
        Index(
            "ix_exercise_attempts_user_kp", "user_id", "knowledge_point_id"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    # 参考答案覆盖率（0—1），判定阈值见 services/mastery_rules.py
    coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 评分依据：参考答案、覆盖率、判定说明
    grading_basis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    graded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    exercise = relationship("Exercise")
    knowledge_point = relationship("KnowledgePoint")
