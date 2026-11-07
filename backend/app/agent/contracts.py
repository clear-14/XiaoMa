"""Agent 结构化状态与工具结果（阶段 10）。

- 主 Agent 与子图之间只通过这里定义的结构传递状态；
- 工具结果显式区分 ok / unavailable / failed：
  - unavailable：业务上暂时不可用（如暂无学习计划），可以给出明确引导；
  - failed：工具/服务异常，调用方必须报错，不能伪造成功。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentIntentName = Literal["planning", "teaching", "quiz", "review", "resource"]
ToolStatus = Literal["ok", "unavailable", "failed"]


class AgentRunError(Exception):
    """Agent 无法完成本轮回复时抛出（message 可直接展示给用户）。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class IntentResult(BaseModel):
    """意图识别结果；intent 对应五个子图之一。"""

    intent: AgentIntentName
    sub_intent: str
    confidence: float = Field(ge=0, le=1)
    matched_keywords: list[str] = Field(default_factory=list)
    reason: str


class ToolResult(BaseModel):
    """一次工具调用结果。data 为 Service 返回的真实业务对象。"""

    ok: bool
    status: ToolStatus
    data: Any = None
    message: str | None = None


class ProfileSnapshot(BaseModel):
    learning_goal: str | None = None
    current_level: str | None = None
    daily_study_minutes: int | None = None


class KnowledgePointSnapshot(BaseModel):
    code: str
    name: str
    chapter_code: str
    chapter_title: str
    learning_status: str


class DailyTaskSnapshot(BaseModel):
    id: str
    status: str
    day_index: int
    task_date: date


class PlanSnapshot(BaseModel):
    plan_id: str
    course_code: str
    course_name: str
    status: str
    confirmed: bool
    current_version_number: int | None = None
    pending_version_number: int | None = None
    daily_study_minutes: int | None = None
    expected_duration_days: int | None = None
    computed_duration_days: int | None = None
    total_items: int = 0
    completed_items: int = 0
    next_pending_day_index: int | None = None
    next_pending_knowledge_point_code: str | None = None
    warning: str | None = None


class LearningContext(BaseModel):
    """本轮对话开始前读取的学习上下文（全部来自 Service 层）。"""

    today: date
    profile: ProfileSnapshot | None = None
    knowledge_point: KnowledgePointSnapshot | None = None
    daily_task: DailyTaskSnapshot | None = None
    plan: PlanSnapshot | None = None
    notes: list[str] = Field(default_factory=list)
