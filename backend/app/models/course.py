"""课程体系模型（阶段 1 扩展）。

层级：课程方向 → 课程 → 章节（CourseModule）→ 课时（Lesson）→ 知识点
→ 教学内容（CourseContent）→ 练习（Exercise）→ 测验题（复用 question_bank）。

设计约定：
- 稳定标识统一使用业务 code（如 python-basics-01-01），种子与接口以 code 引用，
  不依赖数据库自增 ID；``Course.code`` 即需求中的唯一 slug，复用而不新增重复唯一列。
- 章节继续复用原 ``chapters`` 表（需求中的 CourseModule），不新建同义表。
- 课时为阶段 1 新增层：``lessons`` 挂在章节下；知识点通过
  ``lesson_knowledge_points`` 一对一归属课时（``knowledge_point_id`` 唯一），
  同时保留原有 ``knowledge_points.chapter_id`` 以兼容既有查询、计划与测验逻辑，
  两条归属关系由种子与 Service 保证一致。
- 教学内容按课时一份（``course_contents.lesson_id`` 唯一）；练习挂在知识点下；
  测验题继续复用 ``question_bank``（已满足题目/选项/答案/解析/难度字段）。
- 课程版本以 JSON 快照保存（``course_versions``），仅追加、不覆盖历史。
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin

# 课程难度与推荐能力等级取值（与知识点难度、学习档案 L0/L1/L2 保持一致）。
COURSE_DIFFICULTIES: tuple[str, ...] = ("beginner", "intermediate", "advanced")
COURSE_LEVELS: tuple[str, ...] = ("L0", "L1", "L2")
# 课程发布状态：草稿 / 已发布 / 已归档。
COURSE_PUBLISH_STATUSES: tuple[str, ...] = ("draft", "published", "archived")
# 练习类型。
EXERCISE_TYPES: tuple[str, ...] = (
    "coding",
    "choice",
    "fill_blank",
    "short_answer",
    "project",
)
# 教学内容状态（阶段 3）：草稿 → 已检查 → 正式发布。
# 未检查的内容不得标为 published，避免把空壳内容伪装成完整教材。
TEXTBOOK_CONTENT_STATUSES: tuple[str, ...] = ("draft", "reviewed", "published")


class CourseDirection(UUIDPkMixin, TimestampMixin, Base):
    """课程方向（阶段 2）：Python 编程基础 / 工程与数据库 / 后端 / 大模型 / Agent。

    方向是「课程分类」，与能力等级（L0/L1/L2，存于 ``Course.recommended_level``）
    是两个正交维度，不放在同一字段里，避免把等级当分类用。

    一门课程可关联多个方向（如「软件工程与项目部署」同时属后端与 Agent 综合项目），
    主方向以 ``Course.direction`` 冗余保存，便于单值筛选与前端展示；
    关联集合以 ``course_direction_links`` 为准，由 Service 保证两者一致。
    """

    __tablename__ = "course_directions"

    # 稳定业务标识，如 python-fundamentals
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    courses: Mapped[list[Course]] = relationship(
        secondary="course_direction_links",
        order_by="Course.sort_order",
        viewonly=True,
    )


class Course(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """课程。

    ``code`` 即唯一 slug（如 python-basics）；``version`` 为课程内容版本号，
    发布快照保存在 ``course_versions``。
    """

    __tablename__ = "courses"

    # 稳定业务标识，同时作为唯一 slug 使用
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # 课程学习目标（长文本，由课程内容维护）
    learning_objectives: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 课程方向，如 python / data-analysis；空值表示未分类
    direction: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 推荐能力等级：L0 零基础 / L1 有基础 / L2 进阶
    recommended_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 预计学习时长（分钟），由课时/知识点时长汇总或人工设定
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="1.0.0", server_default="1.0.0"
    )
    # 草稿 / 已发布 / 已归档；默认已发布以兼容既有课程
    publish_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="published",
        server_default="published",
        index=True,
    )
    # 同方向下的展示顺序
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Chapter.order_index",
    )
    versions: Mapped[list[CourseVersion]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CourseVersion.created_at",
    )
    # 阶段 2：关联的课程方向（多对多，主方向冗余在 direction 字段）
    directions: Mapped[list[CourseDirection]] = relationship(
        secondary="course_direction_links",
        order_by="CourseDirection.order_index",
        viewonly=True,
    )
    # 阶段 2：课程级先修（有向无环图，多前置课程）
    prerequisites: Mapped[list[Course]] = relationship(
        secondary="course_prerequisites",
        primaryjoin="Course.id == course_prerequisites.c.course_id",
        secondaryjoin="Course.id == course_prerequisites.c.prerequisite_course_id",
        order_by="Course.sort_order",
        viewonly=True,
    )
    # 阶段 2：入学前应掌握的知识点（可跨课程引用，用于补学提示与跳级判断）
    required_knowledge_points: Mapped[list[KnowledgePoint]] = relationship(
        secondary="course_knowledge_point_prerequisites",
        order_by="KnowledgePoint.code",
        viewonly=True,
    )

    @property
    def slug(self) -> str:
        """唯一 slug：复用 code，避免并存两个几乎相同的唯一键。"""
        return self.code


class Chapter(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """章节（需求中的 CourseModule）。"""

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
    # 阶段 1 新增：章节下的课时
    lessons: Mapped[list[Lesson]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="Lesson.order_index",
    )
    # 兼容保留：章节直挂知识点的原关系（既有计划/测验/前端依赖）
    knowledge_points: Mapped[list[KnowledgePoint]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="KnowledgePoint.order_index",
    )


class Lesson(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """课时：章节下的教学单元，承载教学内容与一组知识点。"""

    __tablename__ = "lessons"
    __table_args__ = (
        CheckConstraint(
            "difficulty IS NULL OR difficulty IN "
            "('beginner', 'intermediate', 'advanced')",
            name="difficulty",
        ),
    )

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 稳定业务标识，如 python-basics-01-lesson-01
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 预计学习时间（分钟）
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    chapter: Mapped[Chapter] = relationship(back_populates="lessons")
    content: Mapped[CourseContent | None] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        uselist=False,
    )
    # 只读视图：知识点归属通过 lesson_knowledge_points 维护，写入走关联对象
    knowledge_points: Mapped[list[KnowledgePoint]] = relationship(
        secondary="lesson_knowledge_points",
        order_by="KnowledgePoint.order_index",
        viewonly=True,
    )


class LessonKnowledgePoint(Base):
    """课时与知识点的一对一归属关联。

    ``knowledge_point_id`` 唯一，保证一个知识点只属于一个课时；
    纯关联表（双列联合主键），不使用通用 Mixin。
    """

    __tablename__ = "lesson_knowledge_points"
    __table_args__ = (
        UniqueConstraint("knowledge_point_id", name="lesson_kp_knowledge_point"),
    )

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CourseContent(UUIDPkMixin, TimestampMixin, Base):
    """课时教学内容（一个课时一份）。

    字段与教材的 15 个必备模块一一对应：
    学习目标 / 为什么学 / 核心概念 / 通俗解释 / 语法介绍 / 示例代码 /
    逐行解释 / 示例输出 / 常见错误 / 错误分析 / 入门练习 / 进阶练习 /
    本节测验 / 学习总结 / 下一课建议。

    ``status`` 采用 draft / reviewed / published 三态：只有人工或自动验收
    通过的课时才能离开 draft，查询接口默认不把 draft 内容当作正式教材返回。
    """

    __tablename__ = "course_contents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'reviewed', 'published')",
            name="content_status",
        ),
    )

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # 1 学习目标
    learning_objectives: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 2 为什么要学这个知识点
    why_learn: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 3 核心概念
    concept_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 4 初学者能理解的通俗解释
    plain_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 5 语法 / API 讲解
    syntax_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 6 示例代码
    example_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 7 逐行解释
    code_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 8 示例输出
    example_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 9 常见错误
    common_mistakes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 10 错误分析
    error_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 11 入门练习说明（具体练习挂在知识点下的 exercises）
    beginner_exercises: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 12 进阶练习说明
    advanced_exercises: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 13 本节测验说明（题目来自 question_bank，按知识点关联）
    quiz_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 14 学习总结
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 15 下一课建议
    next_lesson: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 内容状态：草稿 / 已检查 / 正式发布
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True,
    )

    lesson: Mapped[Lesson] = relationship(back_populates="content")


class Exercise(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """知识点练习（与测验题库 question_bank 分离：练习用于日常动手，测验用于组卷评分）。"""

    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "exercise_type IN "
            "('coding', 'choice', 'fill_blank', 'short_answer', 'project')",
            name="exercise_type",
        ),
        CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="difficulty",
        ),
    )

    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 稳定业务标识，如 ex-python-basics-01-01-1
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    exercise_type: Mapped[str] = mapped_column(String(32), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    knowledge_point: Mapped[KnowledgePoint] = relationship(back_populates="exercises")


class CourseVersion(UUIDPkMixin, TimestampMixin, Base):
    """课程版本快照（发布存档用，只追加不覆盖）。"""

    __tablename__ = "course_versions"
    __table_args__ = (
        UniqueConstraint("course_id", "version", name="course_version"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    # 完整课程结构快照：课程元数据 + 章节 + 课时 + 知识点 + 教学内容 + 练习
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    course: Mapped[Course] = relationship(back_populates="versions")


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

    ``chapter_id`` 为阶段 1 之前的直属章节关系，保留以兼容既有查询；
    课时归属通过 ``lesson``（lesson_knowledge_points 关联）表达。
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
    # 只读视图：所属课时（一个知识点只属于一个课时）
    lesson: Mapped[Lesson | None] = relationship(
        secondary="lesson_knowledge_points",
        primaryjoin=(
            "KnowledgePoint.id == lesson_knowledge_points.c.knowledge_point_id"
        ),
        secondaryjoin="Lesson.id == lesson_knowledge_points.c.lesson_id",
        viewonly=True,
        uselist=False,
    )
    exercises: Mapped[list[Exercise]] = relationship(
        cascade="all, delete-orphan",
        order_by="Exercise.order_index",
    )
    prerequisites: Mapped[list[KnowledgePoint]] = relationship(
        secondary="knowledge_point_prerequisites",
        primaryjoin="KnowledgePoint.id == knowledge_point_prerequisites.c.knowledge_point_id",
        secondaryjoin="KnowledgePoint.id == knowledge_point_prerequisites.c.prerequisite_kp_id",
        order_by="KnowledgePoint.order_index",
    )


class CourseDirectionLink(Base):
    """课程与方向的多对多关联（纯关联表，双列联合主键）。"""

    __tablename__ = "course_direction_links"

    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    direction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("course_directions.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )


class CoursePrerequisite(Base):
    """课程级先修依赖（有向边：course → 先修课程）。

    只存单条边，A 依赖 B 与 B 依赖 A 由 Service 的环检测拒绝，
    不依赖数据库约束（SQLite 无法在表级表达无环）。
    """

    __tablename__ = "course_prerequisites"
    __table_args__ = (
        CheckConstraint(
            "course_id <> prerequisite_course_id",
            name="course_prerequisite_not_self",
        ),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )


class CourseKnowledgePointPrerequisite(Base):
    """课程入学所需的先修知识点（可跨课程引用）。

    与 ``knowledge_point_prerequisites``（知识点之间的先后关系）不同：
    本表表达「学这门课之前应已掌握哪些知识点」，用于诊断后的补学提示与跳级判断。
    """

    __tablename__ = "course_knowledge_point_prerequisites"

    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
