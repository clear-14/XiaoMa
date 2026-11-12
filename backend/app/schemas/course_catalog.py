"""课程目录与学习路线接口 Schema（阶段 2）。

方向（课程分类）与能力等级（L0/L1/L2）是两个正交维度：
- 方向见 ``CourseDirection``，表达课程所属的领域；
- 等级见 ``CourseCatalogItem.recommended_level``，表达推荐的学习阶段。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.course import CourseBrief, DirectionBrief


class DirectionOut(BaseModel):
    """课程方向（含该方向下的课程数量）。"""

    id: UUID
    code: str
    name: str
    description: str | None
    order_index: int
    course_count: int


class CourseCatalogItem(BaseModel):
    """课程目录条目：课程元数据 + 章节/课时规模 + 直接先修课程。"""

    code: str
    slug: str
    name: str
    description: str | None
    # 主方向 code（与 directions 中的某一项一致）
    direction: str | None
    # 全部关联方向 code（一门课可属多个方向）
    direction_codes: list[str]
    recommended_level: str | None
    difficulty: str | None
    estimated_minutes: int | None
    version: str
    publish_status: str
    sort_order: int
    chapter_count: int
    lesson_count: int
    knowledge_point_count: int
    # 直接先修课程 code（不含传递依赖）
    prerequisites: list[str]


class DirectionGroup(BaseModel):
    """按方向分组的课程目录。"""

    direction: DirectionOut
    courses: list[CourseCatalogItem]


class CourseCatalogOut(BaseModel):
    """课程目录总览：按方向分组 + 未归入任何方向的课程。"""

    directions: list[DirectionGroup]
    ungrouped: list[CourseCatalogItem]
    total_courses: int
    total_chapters: int
    total_lessons: int


class PrerequisiteEdgeOut(BaseModel):
    """依赖图中的一条有向边：course_code 依赖 prerequisite_code。"""

    course_code: str
    prerequisite_code: str


class KnowledgePointReferenceOut(BaseModel):
    """课程引用的入学知识点。"""

    course_code: str
    knowledge_point_code: str


class DependencyGraphOut(BaseModel):
    """课程依赖图与检查结果。"""

    valid: bool
    course_count: int
    edge_count: int
    edges: list[PrerequisiteEdgeOut]
    # 每条环为一个从起点回到起点的课程 code 序列，如 [a, b, c, a]
    cycles: list[list[str]]
    # 数据库内不可能存在（外键保证），保留字段用于暴露导入/脚本数据问题
    missing_course_references: list[PrerequisiteEdgeOut]
    missing_knowledge_point_references: list[KnowledgePointReferenceOut]
    self_references: list[str]
    # 拓扑顺序：先修课程排在依赖它的课程之前；有环时为空
    topological_order: list[str]


class CourseRelationsOut(BaseModel):
    """某门课的前置课程（或后续可学课程）：直接关系 + 传递闭包。"""

    course_code: str
    direct: list[CourseBrief]
    transitive: list[CourseBrief]


class SkippedCourseOut(BaseModel):
    """判定为可跳过的前置课程及原因。"""

    code: str
    name: str
    reason: str


class MissingKnowledgePointOut(BaseModel):
    """尚未掌握、建议补学的知识点。"""

    code: str
    name: str
    course_code: str


class LearningPathOut(BaseModel):
    """学习路径建议：能否开始、缺哪些课程/知识点、哪些可跳过。"""

    course_code: str
    course_name: str
    ready: bool
    missing_courses: list[CourseBrief]
    skipped_courses: list[SkippedCourseOut]
    missing_knowledge_points: list[MissingKnowledgePointOut]
    notes: list[str]


class KnowledgePointBrief(BaseModel):
    """课程入学知识点的最简引用。"""

    code: str
    name: str


class PrerequisiteCreate(BaseModel):
    """新增课程先修请求。"""

    prerequisite_code: str = Field(min_length=1, max_length=64)


class CourseKnowledgePointPrerequisiteCreate(BaseModel):
    """新增课程入学知识点请求。"""

    knowledge_point_code: str = Field(min_length=1, max_length=64)
