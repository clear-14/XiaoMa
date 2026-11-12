"""教材接口 Schema（阶段 3）：课时教材全文、课程教材大纲、内容状态与验收报告。"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ContentStatus = Literal["draft", "reviewed", "published"]


class TextbookContentOut(BaseModel):
    """课时教学内容的 15 个必备模块。"""

    status: str
    learning_objectives: str | None
    why_learn: str | None
    concept_explanation: str | None
    plain_explanation: str | None
    syntax_explanation: str | None
    example_code: str | None
    code_explanation: str | None
    example_output: str | None
    common_mistakes: str | None
    error_analysis: str | None
    beginner_exercises: str | None
    advanced_exercises: str | None
    quiz_note: str | None
    summary: str | None
    next_lesson: str | None


class TextbookExerciseOut(BaseModel):
    """教材练习（带参考答案与解析）。"""

    code: str
    title: str
    description: str | None
    exercise_type: str
    difficulty: str
    reference_answer: str | None
    explanation: str | None


class TextbookQuestionOut(BaseModel):
    """教材本节测验题（带答案与解析，用于学习反馈）。"""

    code: str
    knowledge_point_code: str
    question_type: str
    stem: str
    options: list | None
    correct_answer: dict
    explanation: str
    difficulty: str
    category: str | None


class TextbookKnowledgePointOut(BaseModel):
    """课时内的知识点。"""

    code: str
    name: str
    learning_goal: str
    difficulty: str
    estimated_minutes: int
    mastery_criteria: str


class LessonTextbookOut(BaseModel):
    """一个课时的完整教材。"""

    lesson_code: str
    lesson_title: str
    chapter_code: str
    chapter_title: str
    course_code: str
    course_name: str
    difficulty: str | None
    estimated_minutes: int | None
    has_content: bool
    content: TextbookContentOut | None
    knowledge_points: list[TextbookKnowledgePointOut]
    exercises: list[TextbookExerciseOut]
    questions: list[TextbookQuestionOut]


class TextbookLessonBrief(BaseModel):
    """教材大纲中的课时条目。"""

    code: str
    title: str
    order_index: int
    estimated_minutes: int | None
    knowledge_point_count: int
    content_status: str | None
    has_content: bool


class TextbookChapterOut(BaseModel):
    """教材大纲中的章节。"""

    code: str
    title: str
    order_index: int
    lesson_count: int
    lessons: list[TextbookLessonBrief]


class TextbookOutlineOut(BaseModel):
    """课程教材大纲。"""

    course_code: str
    course_name: str
    version: str
    publish_status: str
    chapter_count: int
    lesson_count: int
    content_count: int
    reviewed_count: int
    published_count: int
    draft_count: int
    chapters: list[TextbookChapterOut]


class ContentStatusUpdate(BaseModel):
    """教学内容状态切换请求。"""

    status: ContentStatus


class ContentStatusOut(BaseModel):
    """内容状态切换结果。"""

    lesson_code: str
    lesson_title: str
    status: str
    previous_status: str | None


class AuditCheckOut(BaseModel):
    """单项验收结果。"""

    key: str
    name: str
    passed: bool
    detail: str
    issues: list[str] = Field(default_factory=list)


class LessonAuditOut(BaseModel):
    """单个课时的验收结果（便于定位问题）。"""

    lesson_code: str
    lesson_title: str
    passed: bool
    failed_checks: list[str] = Field(default_factory=list)


class TextbookAuditOut(BaseModel):
    """课程教材验收报告。"""

    course_code: str
    course_name: str
    total_chapters: int
    total_lessons: int
    total_questions: int
    total_exercises: int
    passed: bool
    checked_at: datetime
    checks: list[AuditCheckOut]
    lesson_failures: list[LessonAuditOut] = Field(default_factory=list)
