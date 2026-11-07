"""学习档案接口 Schema（PRD 5.1：学习目标、当前基础、每日可学习时间、学习偏好）。"""

from typing import Literal

from pydantic import BaseModel, Field


class ProfileOut(BaseModel):
    """学习档案响应。"""

    username: str
    learning_goal: str | None = None
    current_level: str | None = None
    daily_study_minutes: int | None = None
    learning_preferences: dict | None = None


class ProfileUpdate(BaseModel):
    """更新学习档案请求。

    PUT 语义：仅提交的字段会被更新，未提交字段保持不变。
    current_level 取值：L0 零基础 / L1 碎片化 / L2 转行（PRD 2）。
    """

    learning_goal: str | None = Field(default=None, max_length=500)
    current_level: Literal["L0", "L1", "L2"] | None = None
    daily_study_minutes: int | None = Field(default=None, ge=1, le=1440)
    learning_preferences: dict | None = None
