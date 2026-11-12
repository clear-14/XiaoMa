"""自主选题接口 Schema（阶段 7）。

对应 ``docs/课程扩展阶段7_自主选题与学习完成度.md`` 第五节。
"""

from pydantic import BaseModel, Field

from app.schemas.daily_task import DailyTaskOut
from app.schemas.progress import CourseProgressOut


class SelfStudyIn(BaseModel):
    """加入今日学习：只接受知识点稳定 code，粒度固定为知识点。"""

    knowledge_point_code: str = Field(min_length=1, max_length=64)


class PrerequisiteWarningOut(BaseModel):
    """未掌握的前置知识点提示。

    **只提示、不阻塞**：阶段 5/6 已固化「未掌握先修只提示补学、不自动跳过」，
    这里沿用同一口径，用户仍可继续学习该知识点。
    """

    knowledge_point_code: str
    knowledge_point_name: str
    status: str
    status_label: str


class SelfStudyOut(BaseModel):
    """自选任务创建结果（幂等：当天已存在则 created=false 返回既有任务）。"""

    task: DailyTaskOut
    created: bool
    prerequisite_warnings: list[PrerequisiteWarningOut] = Field(default_factory=list)
    note: str | None = None


class StudyCandidateKpOut(BaseModel):
    """可自选知识点：两轴状态 + 是否可开始 + 先修提示。"""

    code: str
    name: str
    difficulty: str
    estimated_minutes: int
    chapter_code: str
    mastery_status: str
    mastery_status_label: str
    # 今天已在该知识点的任务里：pending / learning / completed
    today_task_status: str | None = None
    today_task_source: str | None = None
    can_start: bool
    block_reason: str | None = None
    prerequisite_codes: list[str] = Field(default_factory=list)
    unmastered_prerequisite_codes: list[str] = Field(default_factory=list)


class StudyCandidateChapterOut(BaseModel):
    """章节分组（含两轴进度，前端据此渲染章节标题右侧百分比）。"""

    code: str
    title: str
    order_index: int
    kp_total: int
    kp_learned: int
    kp_mastered: int
    learning_percent: float
    mastery_percent: float
    knowledge_points: list[StudyCandidateKpOut] = Field(default_factory=list)


class StudyCandidatesOut(BaseModel):
    """课程学习页的完整数据源：进度 + 可自选知识点目录。"""

    course_code: str
    course_name: str
    course_publish_status: str
    progress: CourseProgressOut
    chapters: list[StudyCandidateChapterOut] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
