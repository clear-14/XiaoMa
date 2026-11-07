"""学习进度概览 Schema（阶段 10：Planning 子图的只读进度视图）。

数据全部来自现有业务 Service（学习档案、学习计划、测验与复习记录），
不包含推测值；没有数据的部分明确为 0 或 None。
"""

from datetime import date

from pydantic import BaseModel, Field


class ChapterProgressOut(BaseModel):
    """按章节汇总的已学习/已掌握知识点数量。"""

    chapter_code: str
    chapter_title: str
    learned_count: int
    mastered_count: int


class LearningOverviewOut(BaseModel):
    """当前学习进度概览。"""

    today: date

    learning_goal: str | None = None
    current_level: str | None = None
    daily_study_minutes: int | None = None

    plan_available: bool
    plan_confirmed: bool
    plan_course_name: str | None = None
    plan_current_version_number: int | None = None
    plan_pending_version_number: int | None = None
    plan_total_items: int = 0
    plan_completed_items: int = 0
    plan_progress_percent: float = 0.0
    plan_current_day: int | None = None
    plan_warning: str | None = None

    learned_count: int = 0
    mastered_count: int = 0
    learning_count: int = 0
    pending_verification_count: int = 0
    review_due_count: int = 0

    quiz_attempt_count: int = 0
    quiz_submitted_count: int = 0
    quiz_average_score: float | None = None
    latest_quiz_score: float | None = None

    mistake_total_count: int = 0
    mistake_pending_count: int = 0
    mistake_resolved_count: int = 0
    mistake_due_count: int = 0

    chapters: list[ChapterProgressOut] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
