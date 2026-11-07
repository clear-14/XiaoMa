"""测验、评分、错题与复习模型（PRD 6.2-6.5 / 阶段 9）。

设计要点：
- 题目来自人工整理的内置题库或经过自动验证的 AI 变式题；正式组卷只读取
  ``status=approved`` 且 ``validation_status`` 为内置题库/已验证 AI 题的行，
  验证失败的 AI 题不会进入正式测验；
- 一次测验 = quiz_attempts + 若干 quiz_answers（创建时先占位，提交时评分）；
- 答错题目写入 mistakes（用户+题目唯一），并按 1/3/7/14 天间隔生成
  review_tasks；复习提交同样生成一条 scope_type=review 的答题记录，保留历史；
- 知识点掌握状态只由后端测验规则更新，绝不根据任务完成或简单对话直接标记。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPkMixin, utc_now

# 题型：单选 / 多选 / 判断 / 填空 / 简答 / 代码分析 / 代码编写。
# 代码题仅做文本评分，不执行用户代码（V1.0 约束）。
QUESTION_TYPES: tuple[str, ...] = (
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
    "short_answer",
    "code_analysis",
    "code_writing",
)
OBJECTIVE_QUESTION_TYPES: tuple[str, ...] = (
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
)
SUBJECTIVE_QUESTION_TYPES: tuple[str, ...] = (
    "short_answer",
    "code_analysis",
    "code_writing",
)
QUESTION_SOURCES: tuple[str, ...] = ("builtin", "ai")
QUESTION_STATUSES: tuple[str, ...] = ("approved", "rejected")
QUESTION_VALIDATION_STATUSES: tuple[str, ...] = (
    "builtin",  # 人工整理的内置题库
    "ai_validated",  # 通过结构校验与独立复核调用的 AI 变式题
    "ai_rejected",  # 仅用于审计；正式组卷不会读取
)

# 测验范围：知识点 / 章节 / 当前学习阶段 / 错题复习。
QUIZ_SCOPE_TYPES: tuple[str, ...] = (
    "knowledge_point",
    "chapter",
    "stage",
    "review",
)
QUIZ_ATTEMPT_STATUSES: tuple[str, ...] = ("in_progress", "submitted")

# 错题复习状态与间隔（PRD 6.5 建议间隔 1、3、7、14 天）。
REVIEW_STATUSES: tuple[str, ...] = ("pending", "resolved")
REVIEW_TASK_STATUSES: tuple[str, ...] = ("pending", "completed", "skipped")
REVIEW_INTERVALS: tuple[int, ...] = (1, 3, 7, 14)


class Question(UUIDPkMixin, TimestampMixin, Base):
    """题库题目。

    options 结构：[{"key": "A", "text": "..."}]（单选/多选）；其他题型为 null。
    correct_answer 结构：
    - single_choice: {"value": "A"}
    - multiple_choice: {"values": ["A", "C"]}
    - true_false: {"value": true}
    - fill_blank: {"values": ["可接受答案1", "可接受答案2"]}
    - 主观题: {"reference": "参考答案", "keywords": ["评分关键词", ...]}
    """

    __tablename__ = "question_bank"
    __table_args__ = (
        CheckConstraint(
            "question_type IN ('single_choice', 'multiple_choice', 'true_false', "
            "'fill_blank', 'short_answer', 'code_analysis', 'code_writing')",
            name="question_type",
        ),
        CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="difficulty",
        ),
        CheckConstraint("source IN ('builtin', 'ai')", name="source"),
        CheckConstraint("status IN ('approved', 'rejected')", name="status"),
        CheckConstraint(
            "validation_status IN ('builtin', 'ai_validated', 'ai_rejected')",
            name="validation_status",
        ),
        Index(
            "ix_question_bank_kp_status",
            "knowledge_point_id",
            "status",
            "validation_status",
        ),
    )

    # 稳定题目标识；内置题如 q-python-basics-01-01-1，AI 题以 ai- 开头
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[dict] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)

    source: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="approved")
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    # AI 题验证结论/失败原因；内置题为空
    validation_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # AI 变式题基于哪道内置题生成；内置题为空
    generated_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("question_bank.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    knowledge_point = relationship("KnowledgePoint")


class QuizAttempt(UUIDPkMixin, TimestampMixin, Base):
    """一次测验（创建时生成题目占位，提交后计分）。"""

    __tablename__ = "quiz_attempts"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('knowledge_point', 'chapter', 'stage', 'review')",
            name="scope_type",
        ),
        CheckConstraint(
            "status IN ('in_progress', 'submitted')", name="status"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # 知识点/章节稳定 code；学习阶段与复习为空。使用快照字符串，历史记录不受
    # 课程内容后续调整影响。
    scope_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="in_progress"
    )
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 百分制得分，保留一位小数；未提交时为空
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_requested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # 提交后记录的掌握状态更新结果快照（含未满足条件的原因）
    mastery_updates: Mapped[list | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    answers: Mapped[list[QuizAnswer]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="QuizAnswer.question_order",
    )


class QuizAnswer(UUIDPkMixin, TimestampMixin, Base):
    """测验中的一道题及用户答案、评分依据。

    创建测验时写入 question_id/顺序/满分占位；提交时写入用户答案与评分。
    主观题的 grading_basis 必须保留关键词命中情况与参考答案（评分依据）。
    """

    __tablename__ = "quiz_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="attempt_question"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 题目为历史数据来源，禁止物理删除题目导致答题记录丢失
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_bank.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    user_answer: Mapped[object | None] = mapped_column(JSON, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    grading_basis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    attempt: Mapped[QuizAttempt] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship()


class Mistake(UUIDPkMixin, TimestampMixin, Base):
    """错题记录：同一用户同一题目只有一条，重复答错更新最近结果与复习进度。"""

    __tablename__ = "mistakes"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="user_question"),
        CheckConstraint(
            "review_status IN ('pending', 'resolved')", name="review_status"
        ),
        CheckConstraint(
            "review_stage >= 0 AND review_stage <= 4", name="review_stage"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_bank.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_answer: Mapped[object | None] = mapped_column(JSON, nullable=True)
    last_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="SET NULL"), nullable=True
    )
    last_wrong_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    # 连续复习通过次数：0 待 1 天复习；1 待 3 天；2 待 7 天；3 待 14 天；4 已掌握/完成
    review_stage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    question: Mapped[Question] = relationship()
    knowledge_point = relationship("KnowledgePoint")
    last_attempt: Mapped[QuizAttempt | None] = relationship(
        foreign_keys=[last_attempt_id]
    )


class ReviewTask(UUIDPkMixin, TimestampMixin, Base):
    """错题复习任务（每次按间隔生成一条，保留完整历史）。"""

    __tablename__ = "review_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed', 'skipped')", name="status"
        ),
        CheckConstraint(
            "interval_days IN (1, 3, 7, 14)", name="interval_days"
        ),
        CheckConstraint(
            "last_result IS NULL OR last_result IN ('correct', 'wrong')",
            name="last_result",
        ),
        Index(
            "ix_review_tasks_user_status_due",
            "user_id",
            "status",
            "due_at",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mistake_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mistakes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_bank.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="SET NULL"), nullable=True
    )

    mistake: Mapped[Mistake] = relationship()
    question: Mapped[Question] = relationship()
    knowledge_point = relationship("KnowledgePoint")
    last_attempt: Mapped[QuizAttempt | None] = relationship(
        foreign_keys=[last_attempt_id]
    )
