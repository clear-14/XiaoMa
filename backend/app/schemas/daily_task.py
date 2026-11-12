"""每日任务接口 Schema。"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


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


class DailyTaskCourseRefsOut(BaseModel):
    """任务引用的真实课程层级标识（阶段 6）。

    ``module_id`` 对应需求中的 CourseModule，本项目复用既有 ``chapters`` 表；
    四个 UUID 均指向数据库中真实存在且未软删除的记录，由生成时固化，
    计划或课程结构变化后历史任务仍可追溯当时的引用。
    """

    course_id: UUID
    module_id: UUID
    lesson_id: UUID
    knowledge_point_id: UUID
    course_code: str
    module_code: str
    lesson_code: str
    knowledge_point_code: str
    lesson_title: str


class DailyTaskOut(BaseModel):
    """每日任务（含知识点信息、真实课程引用与掌握证据概况）。

    阶段 7 起区分两个轴，前端必须分开展示，不得合成单一进度条：
    - ``status`` / ``progress_label``：学习完成度（用户动作驱动，三档）；
    - ``mastery_status`` / ``mastery_evidence_count``：掌握度（证据驱动）。
    """

    id: UUID
    # 计划外自选任务不挂计划，故可为空
    plan_id: UUID | None
    task_date: date
    day_index: int
    # 任务来源：plan 计划自动排期 / self_selected 用户自主加入今日学习
    source: str = "plan"
    status: str  # pending | learning | completed
    progress_label: str = ""  # 未开始 / 学习中 / 已学完（未验证）
    # 跨天承接：当天未开始时为 False；「学习中」的逾期任务次日进当日列表时为 True
    carried_over: bool = False
    carried_over_days: int = 0
    started_at: datetime | None
    completed_at: datetime | None
    knowledge_point: DailyTaskKpOut
    # 新生成的任务四 ID 齐全；升级前的历史任务若确实没有归属课时则为 null
    course_refs: DailyTaskCourseRefsOut | None = None
    # 任务完成状态与学习证据的关联说明：任务完成只是自述，掌握需测验证据
    mastery_status: str
    mastery_evidence_count: int
    completion_note: str | None = None


class TodayTasksSummaryOut(BaseModel):
    """今日任务汇总（阶段 7）：只做计数，不做「学完 = 掌握」的错误合并。"""

    plan_total: int = 0
    plan_completed: int = 0
    self_selected_total: int = 0
    self_selected_completed: int = 0
    # 今天处于「学习中」的任务数（含跨天承接的）
    in_progress: int = 0
    # 跨天承接的「学习中」任务数
    carried_over: int = 0
    # 今天仍未完成任务的预计剩余分钟
    remaining_minutes: int = 0


class TodayTasksOut(BaseModel):
    """首页今日任务：查询已有则直接返回；无任务则按计划与进度生成。

    阶段 7 起按来源分组返回，``tasks`` 保留为「当天全部任务」的兼容字段
    （不含跨天承接），旧前端不受影响；新前端按 ``plan_tasks`` 判断是否需要
    调用生成接口，避免自选任务把计划任务「挤掉」。
    """

    task_date: date
    generated: bool  # 本次请求是否触发了任务生成
    tasks: list[DailyTaskOut]
    plan_tasks: list[DailyTaskOut] = Field(default_factory=list)
    self_selected_tasks: list[DailyTaskOut] = Field(default_factory=list)
    # 昨天及更早仍处于「学习中」的任务（7 天窗口内），跨天承接
    carried_over_tasks: list[DailyTaskOut] = Field(default_factory=list)
    summary: TodayTasksSummaryOut = Field(default_factory=TodayTasksSummaryOut)
    note: str | None = None  # 无任务可生成时的说明（如计划已全部完成）
