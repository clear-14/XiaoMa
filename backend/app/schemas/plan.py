"""学习计划接口 Schema。

「初始诊断信息」为创建计划的输入：当前编程基础、学习目标、每天可学习时间、
期望学习周期（天）、已掌握的知识点（稳定 code 列表）。
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PlanCreate(BaseModel):
    """创建学习计划请求（含初始诊断信息）。"""

    course_code: str
    learning_goal: str = Field(min_length=1, max_length=500)
    # 当前编程基础：L0 零基础 / L1 碎片化 / L2 转行（PRD 2）
    current_level: Literal["L0", "L1", "L2"] | None = None
    daily_study_minutes: int = Field(ge=1, le=1440)
    # 期望学习周期，单位：天
    expected_duration_days: int = Field(ge=1, le=3650)
    # 诊断中用户自述已掌握的知识点（稳定 code），排期时不再安排
    mastered_kp_codes: list[str] = Field(default_factory=list)


class PlanAdjust(BaseModel):
    """调整学习计划请求（PUT 语义：仅提交的字段被调整，其余沿用当前版本参数）。"""

    learning_goal: str | None = Field(default=None, min_length=1, max_length=500)
    daily_study_minutes: int | None = Field(default=None, ge=1, le=1440)
    expected_duration_days: int | None = Field(default=None, ge=1, le=3650)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "PlanAdjust":
        if all(
            v is None
            for v in (self.learning_goal, self.daily_study_minutes, self.expected_duration_days)
        ):
            raise ValueError("至少提交一个需要调整的字段")
        return self


class PlanItemOut(BaseModel):
    """计划项目（某知识点安排在计划的第几天）。"""

    id: UUID
    knowledge_point_code: str
    knowledge_point_name: str
    estimated_minutes: int
    day_index: int
    status: Literal["pending", "completed"]
    completed_at: datetime | None


class PlanVersionOut(BaseModel):
    """计划版本详情（含全部计划项目）。"""

    version_number: int
    status: str
    learning_goal: str
    daily_study_minutes: int
    expected_duration_days: int
    computed_duration_days: int
    # 排期超出期望周期时的提示（由后端计算，用户据此决定是否调整参数）
    warning: str | None
    current_level: str | None
    mastered_kp_codes: list[str] | None
    created_at: datetime
    items: list[PlanItemOut]


class PlanVersionSummary(BaseModel):
    """计划版本概要（历史版本列表条目）。"""

    version_number: int
    status: str
    learning_goal: str
    daily_study_minutes: int
    expected_duration_days: int
    computed_duration_days: int
    item_count: int
    completed_count: int
    created_at: datetime


class PlanOut(BaseModel):
    """计划详情：计划信息 + 全部历史版本概要。"""

    id: UUID
    course_code: str
    course_name: str
    status: str
    start_date: date | None
    current_version_number: int | None
    pending_version_number: int | None
    versions: list[PlanVersionSummary]
    created_at: datetime


class CurrentPlanOut(PlanOut):
    """当前计划视图：计划信息 + 生效版本与待确认草稿版本（含项目）。"""

    current_version: PlanVersionOut | None
    pending_version: PlanVersionOut | None
