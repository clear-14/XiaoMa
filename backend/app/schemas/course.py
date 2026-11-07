"""课程体系接口 Schema。"""

from uuid import UUID

from pydantic import BaseModel


class LearningResource(BaseModel):
    """知识点学习资源条目。"""

    type: str  # documentation / exercise
    title: str
    url: str | None = None


class KnowledgePointSummary(BaseModel):
    """知识点概要（课程详情与前置关系中的展示形态）。"""

    id: UUID
    code: str
    name: str
    difficulty: str
    estimated_minutes: int
    order_index: int


class ChapterOut(BaseModel):
    """章节（含知识点概要，按 order_index 排序）。"""

    id: UUID
    code: str
    title: str
    description: str | None
    order_index: int
    knowledge_points: list[KnowledgePointSummary]


class CourseSummary(BaseModel):
    """课程概要。"""

    id: UUID
    code: str
    name: str
    description: str | None
    chapter_count: int


class CourseDetail(CourseSummary):
    """课程详情：课程信息 + 全部章节与知识点。"""

    chapters: list[ChapterOut]


class ChapterBrief(BaseModel):
    """知识点详情中引用的所属章节信息。"""

    code: str
    title: str


class KnowledgePointDetail(BaseModel):
    """知识点详情（学习目标/难度/预计时长/掌握标准/学习资源/前置知识点）。"""

    id: UUID
    code: str
    name: str
    learning_goal: str
    difficulty: str
    estimated_minutes: int
    mastery_criteria: str
    resources: list[LearningResource] | None
    order_index: int
    chapter: ChapterBrief
    prerequisites: list[KnowledgePointSummary]


class KnowledgePointResourcesOut(BaseModel):
    """知识点及其登记的学习资源（Agent 资源检索结果）。"""

    knowledge_point_code: str
    knowledge_point_name: str
    chapter_title: str
    resources: list[LearningResource]
