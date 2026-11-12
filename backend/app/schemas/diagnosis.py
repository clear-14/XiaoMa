"""学习诊断接口 Schema（阶段 5）。

诊断维度固定为 6 个（需求「四、学习诊断升级」）：
Python 基础 / Python 工程能力 / 数据库能力 / Web 后端能力 /
大模型 API 能力 / LangGraph Agent 能力。
每个维度都映射到具体知识点，不用「感觉差不多」这种描述代替证据。
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.mastery import MasteryStatus

DimensionLevel = Literal["mastered", "partial", "not_started", "no_data"]

RouteAction = Literal["study", "review", "verify", "skip", "remedial"]

# 维度等级中文说明，接口与文档共用。
DIMENSION_LEVEL_LABELS: dict[str, str] = {
    "mastered": "已掌握",
    "partial": "部分掌握",
    "not_started": "未开始",
    "no_data": "暂无数据",
}

ROUTE_ACTION_LABELS: dict[str, str] = {
    "study": "学习",
    "review": "复习",
    "verify": "验证（诊断测验）",
    "skip": "跳过（已有掌握证据）",
    "remedial": "补学先修",
}


class DiagnosisKnowledgePointOut(BaseModel):
    """诊断结果里的一个知识点。"""

    knowledge_point_code: str
    knowledge_point_name: str
    chapter_title: str
    difficulty: str
    status: MasteryStatus
    status_label: str
    # 状态来源：evidence=有验证证据，claim=仅自述，none=无记录
    source: Literal["evidence", "claim", "none"]
    accuracy: float | None
    verified_at: str | None


class DiagnosisDimensionOut(BaseModel):
    """一个诊断维度（含映射到的知识点与等级）。"""

    code: str
    name: str
    description: str
    course_code: str
    course_name: str | None
    available: bool
    level: DimensionLevel
    level_label: str
    mastered_count: int
    understood_count: int
    applied_count: int
    needs_review_count: int
    not_started_count: int
    total: int
    coverage_percent: float
    knowledge_points: list[DiagnosisKnowledgePointOut]
    note: str | None


class RouteStepOut(BaseModel):
    """个性化学习路线的一步。"""

    order_index: int
    knowledge_point_code: str
    knowledge_point_name: str
    course_code: str
    course_name: str
    action: RouteAction
    action_label: str
    reason: str
    estimated_minutes: int


class DiagnosisIn(BaseModel):
    """发起诊断：目标 + 可选的自述（自述只作为待验证线索，不作为掌握证据）。"""

    learning_goal: str | None = Field(default=None, max_length=500)
    target_course_code: str | None = Field(default=None, max_length=64)
    self_reported_kp_codes: list[str] = Field(default_factory=list, max_length=200)
    # 只诊断指定维度；为空表示 6 个维度全诊断
    dimension_codes: list[str] = Field(default_factory=list, max_length=6)


class DiagnosisOut(BaseModel):
    """诊断报告 + 个性化学习路线。"""

    generated_at: date
    learning_goal: str | None
    target_course_code: str | None
    target_course_name: str | None
    dimensions: list[DiagnosisDimensionOut]
    route: list[RouteStepOut]
    # 可跳过 / 需验证 / 补学的汇总，前端直接渲染
    skippable_kp_codes: list[str]
    needs_verification_kp_codes: list[str]
    remedial_kp_codes: list[str]
    summary: str
    notes: list[str]


class PlacementIn(BaseModel):
    """生成诊断（跳级）测验。

    允许对未开始的知识点出题——这正是诊断的用途；
    但通过后进入的是「抽样验证」证据，规则见 services/mastery_rules.py。
    """

    course_code: str | None = Field(default=None, max_length=64)
    knowledge_point_codes: list[str] = Field(default_factory=list, max_length=20)
    # 每个知识点的题量（1—3）；达到 2 题且全对才可能判定掌握
    questions_per_point: int = Field(default=2, ge=1, le=3)


class PlacementPlanOut(BaseModel):
    """诊断测验的可出题范围（不生成测验，仅告知能验证哪些知识点）。"""

    course_code: str | None
    course_name: str | None
    knowledge_points: list[DiagnosisKnowledgePointOut]
    question_counts: dict[str, int]
    notes: list[str]
