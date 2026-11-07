"""每日任务接口 Schema。"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class DailyTaskKpOut(BaseModel):
    """任务关联的知识点信息（学习目标/难度/时长/掌握标准/资源/章节/前置）。"""

    code: str
    name: str
    learning_goal: str
    difficulty: str
    estimated_minutes: int
    mastery_criteria: str
    chapter_code: str
    chapter_title: str
    resources: list | None
    prerequisite_codes: list[str]


class DailyTaskOut(BaseModel):
    """每日任务（含知识点信息）。"""

    id: UUID
    plan_id: UUID
    task_date: date
    day_index: int
    status: str  # pending | learning | completed
    started_at: datetime | None
    completed_at: datetime | None
    knowledge_point: DailyTaskKpOut


class TodayTasksOut(BaseModel):
    """首页今日任务：查询已有则直接返回；无任务则按计划与进度生成。"""

    task_date: date
    generated: bool  # 本次请求是否触发了任务生成
    tasks: list[DailyTaskOut]
    note: str | None = None  # 无任务可生成时的说明（如计划已全部完成）
