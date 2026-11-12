"""课程体系接口 Schema（阶段 1：课程 → 章节 → 课时 → 知识点 → 内容/练习/测验）。"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# 输入校验用的字面量（输出字段用 str，避免历史脏值导致响应校验失败）
CourseDifficulty = Literal["beginner", "intermediate", "advanced"]
CourseLevel = Literal["L0", "L1", "L2"]
CoursePublishStatus = Literal["draft", "published", "archived"]
ExerciseType = Literal["coding", "choice", "fill_blank", "short_answer", "project"]


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


class LessonSummary(BaseModel):
    """课时概要（章节详情内的课时列表）。"""

    id: UUID
    code: str
    title: str
    description: str | None
    difficulty: str | None
    estimated_minutes: int | None
    order_index: int
    knowledge_point_count: int
    has_content: bool


class ChapterBrief(BaseModel):
    """知识点/课时详情中引用的所属章节信息。"""

    code: str
    title: str


class CourseBrief(BaseModel):
    """课时详情中引用的所属课程信息。"""

    code: str
    name: str


class DirectionBrief(BaseModel):
    """课程方向的最简引用（阶段 2：课程详情内展示所属方向）。"""

    code: str
    name: str


class CourseContentOut(BaseModel):
    """课时教学内容。"""

    learning_objectives: str | None
    concept_explanation: str | None
    syntax_explanation: str | None
    example_code: str | None
    code_explanation: str | None
    common_mistakes: str | None
    summary: str | None


class ChapterOut(BaseModel):
    """章节（含知识点概要与课时列表，均按 order_index 排序）。"""

    id: UUID
    code: str
    title: str
    description: str | None
    order_index: int
    knowledge_points: list[KnowledgePointSummary]
    lessons: list[LessonSummary]


class CourseSummary(BaseModel):
    """课程概要（含阶段 1 元数据）。"""

    id: UUID
    code: str
    # 唯一 slug：与 code 同值（复用既有唯一业务标识，不另存重复列）
    slug: str
    name: str
    description: str | None
    direction: str | None
    difficulty: str | None
    recommended_level: str | None
    estimated_minutes: int | None
    version: str
    publish_status: str
    sort_order: int
    chapter_count: int
    lesson_count: int
    knowledge_point_count: int


class CourseDetail(CourseSummary):
    """课程详情：课程信息 + 全部章节、课时与知识点。"""

    learning_objectives: str | None
    chapters: list[ChapterOut]
    # 阶段 2：关联方向、直接先修课程与入学需掌握的知识点
    directions: list[DirectionBrief] = Field(default_factory=list)
    prerequisites: list[CourseBrief] = Field(default_factory=list)
    required_knowledge_points: list[KnowledgePointSummary] = Field(
        default_factory=list
    )


class KnowledgePointDetail(BaseModel):
    """知识点详情（学习目标/难度/时长/掌握标准/资源/前置知识点/所属课时）。"""

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
    lesson: LessonSummary | None
    prerequisites: list[KnowledgePointSummary]
    exercise_count: int
    question_count: int


class KnowledgePointResourcesOut(BaseModel):
    """知识点及其登记的学习资源（Agent 资源检索结果）。"""

    knowledge_point_code: str
    knowledge_point_name: str
    chapter_title: str
    resources: list[LearningResource]


class LessonDetail(BaseModel):
    """课时详情：所属课程/章节、教学内容与知识点。"""

    id: UUID
    code: str
    title: str
    description: str | None
    difficulty: str | None
    estimated_minutes: int | None
    order_index: int
    module: ChapterBrief
    course: CourseBrief
    content: CourseContentOut | None
    knowledge_points: list[KnowledgePointSummary]


class ExerciseOut(BaseModel):
    """练习详情（含参考答案与解析，用于日常练习与自测）。"""

    id: UUID
    code: str
    title: str
    description: str | None
    exercise_type: str
    difficulty: str
    reference_answer: str | None
    explanation: str | None
    order_index: int


class QuestionOut(BaseModel):
    """测验题输出。

    默认不返回正确答案与解析（避免影响正式测验公平性）；
    仅在显式请求 include_answer=true 时填充。
    """

    id: UUID
    code: str
    stem: str
    question_type: str
    options: list | None
    difficulty: str
    correct_answer: dict | None = None
    explanation: str | None = None


class CourseVersionSummary(BaseModel):
    """课程版本概要。"""

    id: UUID
    version: str
    note: str | None
    created_at: datetime


class CourseVersionDetail(CourseVersionSummary):
    """课程版本详情（含完整结构快照）。"""

    snapshot: dict


class CourseVersionCreate(BaseModel):
    """保存课程版本请求：版本号为空时使用课程当前 version。"""

    version: str | None = Field(default=None, max_length=32)
    note: str | None = Field(default=None, max_length=500)


class CourseStatusUpdate(BaseModel):
    """课程发布状态切换请求。"""

    publish_status: CoursePublishStatus
