"""阶段 6 接口 Schema：动态计划调整提案、复习申请与调整信号。

关键口径：``PlanAdjustmentProposalOut.requires_confirmation`` 恒为 True，
提案对象里没有任何「已保存 / 已生效」字段；只有确认接口才返回生效后的计划。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.plan import CurrentPlanOut
from app.schemas.quiz import ReviewTaskOut

ProposalStatus = Literal["proposed", "confirmed", "rejected"]
ReviewRequestStatus = Literal["pending", "scheduled", "completed"]


class PlanSignalOut(BaseModel):
    """一条调整信号：后端实测达标，或调用方声明的线索（后者在 detail 中明确标注未实测）。"""

    code: str
    label: str
    detail: str


class PlanSignalsOut(BaseModel):
    """当前学习状态下的调整信号盘点。"""

    signals: list[PlanSignalOut]
    proposal_needed: bool
    summary: str


class ProposalCreate(BaseModel):
    """请求生成一份调整方案（只生成提案，不改动计划）。"""

    learning_goal: str | None = Field(default=None, min_length=1, max_length=500)
    daily_study_minutes: int | None = Field(default=None, ge=1, le=1440)
    expected_duration_days: int | None = Field(default=None, ge=1, le=3650)
    reason: str | None = Field(default=None, max_length=1000)
    source: Literal["user", "agent", "api"] = "user"
    # 由调用方（Agent / 前端）显式声明的触发条件；后端还会自行检测真实信号
    declared_triggers: list[str] = Field(default_factory=list, max_length=6)


class PlanAdjustmentProposalOut(BaseModel):
    """待确认方案：确认前不产生任何计划版本。"""

    id: UUID
    plan_id: UUID
    status: ProposalStatus
    triggers: list[str]
    trigger_labels: list[str]
    reason: str
    changes: dict
    preview: dict
    source: str
    created_at: datetime
    confirmed_at: datetime | None
    rejected_at: datetime | None
    resulting_version_number: int | None
    # 恒为 True：接口层/前端/ Agent 都必须先看方案再确认
    requires_confirmation: bool = True
    note: str


class ProposalConfirmOut(BaseModel):
    """确认结果：提案状态 + 生效后的计划版本。"""

    proposal: PlanAdjustmentProposalOut
    plan: CurrentPlanOut
    message: str


class ReviewRequestIn(BaseModel):
    """申请复习某个知识点（幂等：同一天同一知识点不重复创建）。"""

    knowledge_point_code: str = Field(min_length=1, max_length=64)
    reason: str | None = Field(default=None, max_length=500)
    source: Literal["user", "agent", "api"] = "user"
    trigger: str | None = Field(default=None, max_length=64)


class ReviewRequestOut(BaseModel):
    """复习申请结果：真实申请记录 + 真实待复习任务，不伪造任务。"""

    id: UUID
    knowledge_point_code: str
    knowledge_point_name: str
    request_date: date
    reason: str
    status: ReviewRequestStatus
    source: str
    created_at: datetime
    created: bool
    # 该知识点已有的真实错题复习任务
    review_tasks: list[ReviewTaskOut]
    mastery_status: str
    mastery_status_label: str
    suggestions: list[str]
    note: str
