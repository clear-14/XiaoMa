"""课程体系模型：课程、章节、知识点与前置关系（PRD 5.1 结构化课程体系）。

稳定标识约定：课程/章节/知识点均使用业务 code（如 python-basics-01-01）作为
跨环境、跨执行的稳定标识，种子数据与接口均以 code 引用，不依赖数据库自增 ID。
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class Course(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """课程。"""

    __tablename__ = "courses"

    # 稳定业务标识，如 python-basics
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Chapter.order_index",
    )


class Chapter(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """章节。"""

    __tablename__ = "chapters"

    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 稳定业务标识，如 python-basics-01
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    course: Mapped[Course] = relationship(back_populates="chapters")
    knowledge_points: Mapped[list[KnowledgePoint]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="KnowledgePoint.order_index",
    )


class KnowledgePointPrerequisite(Base):
    """知识点前置关系关联表（知识点多对多自关联）。

    不使用通用 Mixin：纯关联表，双列联合主键；prerequisite_kp_id 建索引
    支持反向查询（哪些知识点以某知识点为前置）。
    """

    __tablename__ = "knowledge_point_prerequisites"

    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_kp_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )


class KnowledgePoint(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """知识点。

    难度取值约定：beginner 入门 / intermediate 进阶 / advanced 高级。
    resources 为 JSON 数组：[{"type": "documentation|exercise", "title": str, "url": str|null}]
    """

    __tablename__ = "knowledge_points"

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 稳定业务标识，如 python-basics-01-01
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    learning_goal: Mapped[str] = mapped_column(String(1000), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    mastery_criteria: Mapped[str] = mapped_column(String(1000), nullable=False)
    resources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    chapter: Mapped[Chapter] = relationship(back_populates="knowledge_points")
    prerequisites: Mapped[list[KnowledgePoint]] = relationship(
        secondary="knowledge_point_prerequisites",
        primaryjoin="KnowledgePoint.id == knowledge_point_prerequisites.c.knowledge_point_id",
        secondaryjoin="KnowledgePoint.id == knowledge_point_prerequisites.c.prerequisite_kp_id",
        order_by="KnowledgePoint.order_index",
    )
