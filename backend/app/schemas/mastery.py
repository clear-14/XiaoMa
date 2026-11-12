"""掌握度接口 Schema（阶段 5）。

字段直接对应需求「三、掌握证据」：用户标识（单用户模型由后端固定）、
知识点 ID、练习记录、测验记录、正确率、测验难度、掌握状态、验证时间。
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MasteryStatus = Literal[
    "not_started",
    "learning",
    "self_reported_completed",
    "understood",
    "applied",
    "mastered",
    "needs_review",
]

EvidenceSource = Literal["self_report", "exercise", "quiz", "placement"]


class MasteryEvidenceOut(BaseModel):
    """一条掌握证据。"""

    id: UUID
    source: EvidenceSource
    source_label: str
    status_before: MasteryStatus
    status_after: MasteryStatus
    status_before_label: str
    status_after_label: str
    accuracy: float | None
    quiz_difficulty: str | None
    quiz_attempt_id: UUID | None
    exercise_attempt_id: UUID | None
    note: str | None
    verified_at: datetime


class MasteryKnowledgePointOut(BaseModel):
    """单个知识点的掌握情况。"""

    knowledge_point_code: str
    knowledge_point_name: str
    chapter_code: str
    chapter_title: str
    course_code: str
    course_name: str
    difficulty: str
    status: MasteryStatus
    status_label: str
    accuracy: float | None
    quiz_difficulty: str | None
    evidence_count: int
    verified_at: datetime | None
    self_reported_at: datetime | None
    review_due_at: datetime | None
    # 下一步该做什么（由后端给出，避免前端各写一套判断）
    next_action: str


class MasteryDetailOut(BaseModel):
    """知识点掌握详情：当前态 + 证据流水 + 练习记录。"""

    knowledge_point: MasteryKnowledgePointOut
    evidence: list[MasteryEvidenceOut]
    exercise_attempts: list[ExerciseAttemptRecordOut]


class MasteryCountsOut(BaseModel):
    """状态计数（用于总览与维度画像）。"""

    not_started: int = 0
    learning: int = 0
    self_reported_completed: int = 0
    understood: int = 0
    applied: int = 0
    mastered: int = 0
    needs_review: int = 0
    total: int = 0


class MasteryCourseOut(BaseModel):
    """按课程聚合的掌握度。"""

    course_code: str
    course_name: str
    counts: MasteryCountsOut
    # 已掌握占该课程已登记知识点的比例（0—100）
    mastered_percent: float


class MasteryOverviewOut(BaseModel):
    """掌握度总览：全局计数 + 按课程分布 + 需要复习清单。"""

    counts: MasteryCountsOut
    mastered_percent: float
    # 「真正掌握」与「仅自述」分开报，避免把自述当能力
    verified_mastered_count: int
    self_reported_only_count: int
    courses: list[MasteryCourseOut]
    needs_review: list[MasteryKnowledgePointOut]


class SelfReportIn(BaseModel):
    """用户自述完成（一次可报多个知识点）。"""

    knowledge_point_codes: list[str] = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class SelfReportItemOut(BaseModel):
    knowledge_point_code: str
    knowledge_point_name: str
    status_before: MasteryStatus
    status_after: MasteryStatus
    changed: bool
    note: str


class SelfReportOut(BaseModel):
    items: list[SelfReportItemOut]
    # 固定提示：自述不等于掌握，跳过仍需验证
    note: str


class ExerciseAttemptIn(BaseModel):
    answer: str = Field(min_length=1, max_length=20000)


class ExerciseAttemptRecordOut(BaseModel):
    """一次练习提交记录。"""

    id: UUID
    exercise_code: str
    exercise_title: str
    exercise_type: str
    difficulty: str
    answer: str
    result: Literal["passed", "failed"]
    coverage: float | None
    grading_basis: dict | None
    graded_at: datetime


class ExerciseAttemptOut(BaseModel):
    """练习提交结果：判定 + 掌握变化。"""

    attempt: ExerciseAttemptRecordOut
    status_before: MasteryStatus
    status_after: MasteryStatus
    knowledge_point: MasteryKnowledgePointOut
    message: str


class ReviewSuggestionOut(BaseModel):
    """薄弱知识点的复习建议。"""

    knowledge_point: MasteryKnowledgePointOut
    reasons: list[str]
    actions: list[str]
    exercise_codes: list[str]
    question_count: int


class SkipCheckItemOut(BaseModel):
    knowledge_point_code: str
    knowledge_point_name: str
    status: MasteryStatus
    status_label: str
    reason: str


class SkipCheckOut(BaseModel):
    """跳级检查：可跳过 / 需验证 / 被先修阻塞。"""

    course_code: str
    course_name: str
    skippable: list[SkipCheckItemOut]
    needs_verification: list[SkipCheckItemOut]
    blocked: list[SkipCheckItemOut]
    notes: list[str]


# 前向引用：MasteryDetailOut 在 ExerciseAttemptRecordOut 之前定义，
# 需要在模块末尾显式重建，避免首次校验时报 ForwardRef 未解析。
MasteryDetailOut.model_rebuild()
