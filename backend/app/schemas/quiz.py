"""测验、错题与复习接口 Schema（PRD 6.2-6.5 / 阶段 9）。

安全与产品约定：
- 未提交的测验只返回题干与选项，不返回正确答案与解析；
- 提交后返回正确答案、解析与评分依据（主观题必须保留依据）；
- 错题本可查看题目解析；复习任务在提交后显示答案与依据。
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

QuizScopeType = Literal["knowledge_point", "chapter", "stage"]


class QuizCreate(BaseModel):
    """开始一次测验。"""

    scope_type: QuizScopeType
    knowledge_point_code: str | None = Field(default=None, max_length=64)
    chapter_code: str | None = Field(default=None, max_length=64)
    # AI 变式题数量（0 表示只用内置题库）；生成失败时降级为内置题库并返回说明
    ai_variant_count: int = Field(default=0, ge=0, le=5)

    @model_validator(mode="after")
    def _check_scope_ref(self) -> "QuizCreate":
        if self.scope_type == "knowledge_point":
            if not self.knowledge_point_code:
                raise ValueError("知识点测验必须提供 knowledge_point_code")
            if self.chapter_code:
                raise ValueError("知识点测验不能同时提供 chapter_code")
        elif self.scope_type == "chapter":
            if not self.chapter_code:
                raise ValueError("章节测验必须提供 chapter_code")
            if self.knowledge_point_code:
                raise ValueError("章节测验不能同时提供 knowledge_point_code")
        elif self.knowledge_point_code or self.chapter_code:
            raise ValueError("阶段测验不需要指定知识点或章节")
        return self


class QuizAnswerIn(BaseModel):
    """一道题的用户答案；具体结构由题型决定，由后端评分器校验。"""

    question_id: UUID
    answer: Any = None


class QuizSubmit(BaseModel):
    """提交整份测验答案。"""

    answers: list[QuizAnswerIn] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def _check_duplicates(self) -> "QuizSubmit":
        ids = [answer.question_id for answer in self.answers]
        if len(ids) != len(set(ids)):
            raise ValueError("同一道题不能提交多个答案")
        return self


class ReviewSubmit(BaseModel):
    """提交一道错题复习的答案。"""

    answer: Any = None


class QuestionOptionOut(BaseModel):
    key: str
    text: str


class QuizKnowledgePointOut(BaseModel):
    code: str
    name: str
    chapter_code: str
    chapter_title: str


class QuizQuestionOut(BaseModel):
    """测验题目。

    未提交时 correct_answer/explanation/score/grading_basis 为 null；
    提交后返回评分结果。source=ai 的题目均已通过后端验证。
    """

    id: UUID
    order: int
    question_type: str
    stem: str
    options: list[QuestionOptionOut] | None = None
    points: int
    source: str  # builtin | ai
    knowledge_point: QuizKnowledgePointOut
    user_answer: Any = None
    correct_answer: Any = None
    explanation: str | None = None
    score: float | None = None
    max_score: int
    is_correct: bool | None = None
    grading_basis: Any = None


class MasteryUpdateOut(BaseModel):
    """一次测验对知识点掌握状态的判定结果（不满足条件时给出原因）。

    阶段 5 起同时返回 7 态掌握度（``status``/``status_label``）：
    achieved 仍表示「是否达到 MASTERED」，便于既有调用方不变。
    """

    knowledge_point_code: str
    knowledge_point_name: str
    achieved: bool
    reasons: list[str]
    status: str | None = None
    status_label: str | None = None


class QuizAttemptOut(BaseModel):
    """测验详情 / 提交结果。"""

    id: UUID
    scope_type: str
    scope_ref: str | None
    scope_name: str
    status: str  # in_progress | submitted
    # 阶段 5：practice=常规练习测验，placement=诊断（跳级）测验。
    # 历史列表据此区分两类测验，避免「诊断验证」被当成普通练习记录。
    purpose: str = "practice"
    question_count: int
    total_points: int
    score: float | None
    ai_requested: int
    ai_accepted: int
    ai_note: str | None
    mastery_updates: list[MasteryUpdateOut] = Field(default_factory=list)
    started_at: datetime
    submitted_at: datetime | None
    questions: list[QuizQuestionOut]


class QuizAttemptSummaryOut(BaseModel):
    """测验历史列表项。"""

    id: UUID
    scope_type: str
    scope_name: str
    status: str
    # 阶段 5：与 QuizAttemptOut 同源，保留测验用途供历史列表筛选
    purpose: str = "practice"
    question_count: int
    score: float | None
    ai_accepted: int
    started_at: datetime
    submitted_at: datetime | None


class EligibilityKnowledgePointOut(BaseModel):
    code: str
    name: str
    chapter_code: str
    chapter_title: str
    status: str
    question_count: int
    quiz_available: bool


class EligibilityChapterOut(BaseModel):
    code: str
    title: str
    learned_knowledge_point_count: int
    question_count: int
    quiz_available: bool


class EligibilityStageOut(BaseModel):
    available: bool
    course_code: str | None = None
    course_name: str | None = None
    learned_knowledge_point_count: int = 0
    question_count: int = 0
    note: str | None = None


class QuizEligibilityOut(BaseModel):
    """可测验范围：只包含已学习知识点（不得对未学习内容正式测验）。"""

    learned_knowledge_points: list[EligibilityKnowledgePointOut]
    chapters: list[EligibilityChapterOut]
    stage: EligibilityStageOut


class MistakeOut(BaseModel):
    """错题本条目（含题目解析、错因与下次复习时间）。"""

    id: UUID
    question: QuizQuestionOut
    knowledge_point: QuizKnowledgePointOut
    attempt_count: int
    last_answer: Any = None
    last_wrong_at: datetime
    review_status: str
    review_stage: int
    next_review_at: datetime | None
    resolved_at: datetime | None
    pending_review_task_id: UUID | None = None


class ReviewTaskOut(BaseModel):
    """错题复习任务（题目在提交前不返回答案与解析）。"""

    id: UUID
    mistake_id: UUID
    due_at: datetime
    interval_days: int
    status: str
    is_due: bool
    last_result: str | None
    question: QuizQuestionOut
    knowledge_point: QuizKnowledgePointOut


class ReviewResultOut(BaseModel):
    """复习提交结果：本题评分 + 错题状态 + 下一次复习任务。"""

    review_task: ReviewTaskOut
    question: QuizQuestionOut
    mistake: MistakeOut
    next_review_task: ReviewTaskOut | None = None
    message: str
