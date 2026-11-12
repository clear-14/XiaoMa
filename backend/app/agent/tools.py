"""Agent 工具层（阶段 6 扩展）：把已有业务 Service 包装成可审计的工具调用。

规则（需求「四、AI 教学集成」「五、Agent 工具」）：
- 工具只调用 Service，不直接访问 Repository / 不执行 SQL；
- 只读工具：get_course / get_lesson / get_knowledge_point /
  get_user_learning_progress / get_today_tasks；
- 写工具：submit_exercise / submit_quiz_result / request_review_task /
  propose_learning_plan_adjustment，**全部经 Service 层**；
- 不提供任何「创建课程 / 修改课程依赖 / 跳过先修 / 直接写掌握状态 /
  确认计划」的工具；计划调整只生成提案（proposed），确认由用户完成；
- 业务上可预期的拒绝返回 unavailable，服务异常返回 failed，子图必须
  明确报错而不是伪造成功；
- 日志只记录工具名、状态与耗时，不记录提示词、用户消息或密钥。
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agent.contracts import LearningContext, ToolResult
from app.schemas.phase6 import ProposalCreate, ReviewRequestIn
from app.schemas.quiz import QuizAnswerIn, QuizCreate, QuizSubmit
from app.services.course_service import CourseService
from app.services.daily_task_service import DailyTaskService
from app.services.learning_overview_service import LearningOverviewService
from app.services.mastery_service import MasteryService
from app.services.plan_adjustment_service import PlanAdjustmentService
from app.services.plan_service import PlanService
from app.services.quiz_service import QuizService
from app.services.review_request_service import ReviewRequestService
from app.services.review_service import ReviewService

logger = logging.getLogger("xiaoma.agent")


@dataclass(frozen=True)
class ToolSpec:
    """工具清单条目：供文档、审计与测试使用。"""

    name: str
    method: str
    service: str
    write: bool
    description: str


# 需求「五、Agent 工具」的 9 个工具；write=True 表示会写业务数据，
# 测试会逐个断言这些工具只调用 Service、不触碰数据库。
AGENT_TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec("get_course", "get_course", "CourseService.get_course_detail", False, "读取已发布课程的结构与前置关系"),
    ToolSpec("get_lesson", "get_lesson", "CourseService.get_lesson", False, "读取课时教学内容和所属章节"),
    ToolSpec("get_knowledge_point", "get_knowledge_point", "CourseService.get_knowledge_point", False, "读取知识点目标、前置、练习与所属课时"),
    ToolSpec("get_user_learning_progress", "get_user_learning_progress", "LearningOverviewService + MasteryService", False, "读取学习进度、7 态掌握度与复习建议"),
    ToolSpec("get_today_tasks", "get_today_tasks", "DailyTaskService.get_today_tasks", False, "读取当日任务（含真实课程引用）"),
    ToolSpec("submit_exercise", "submit_exercise", "MasteryService.submit_exercise", True, "提交练习答案，由 Service 写练习记录与掌握证据"),
    ToolSpec("submit_quiz_result", "submit_quiz_result", "QuizService.submit_attempt", True, "提交测验答案，由 Service 评分并写掌握证据/错题复习任务"),
    ToolSpec("request_review_task", "request_review_task", "ReviewRequestService.request", True, "申请复习，由 Service 幂等写入申请记录"),
    ToolSpec("propose_learning_plan_adjustment", "propose_learning_plan_adjustment", "PlanAdjustmentService.propose", True, "只生成待确认调整提案，不写任何计划版本"),
)

# 阶段 10 既有工具与后续批次新增的只读工具（保留原闭环，均为只读或经 Service 的既有能力）
LEGACY_TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec("get_current_plan", "get_current_plan", "PlanService.get_current_plan", False, "读取当前计划与待确认草案"),
    ToolSpec("get_progress", "get_progress", "LearningOverviewService.get_overview", False, "读取旧版学习进度概览（兼容）"),
    ToolSpec("search_learning_resources", "search_resources", "CourseService.search_learning_resources", False, "检索课程库已登记资源"),
    ToolSpec("generate_quiz", "generate_quiz", "QuizService.create_quiz", True, "按范围组卷（题库只读，写测验记录）"),
    ToolSpec("get_quiz_attempts", "get_quiz_attempts", "QuizService.list_attempts", False, "读取测验历史"),
    ToolSpec("get_latest_quiz_result", "get_latest_quiz_result", "QuizService.get_attempt", False, "读取最近一次已提交测验的完整结果（只读，不提交）"),
    ToolSpec("get_mistakes", "get_mistakes", "ReviewService.list_mistakes", False, "读取错题本"),
    ToolSpec("get_review_tasks", "get_review_tasks", "ReviewService.list_tasks", False, "读取待复习任务"),
)

# Agent 明确禁止的能力：工具清单里不存在、也不允许新增这些入口。
FORBIDDEN_TOOL_NAMES: tuple[str, ...] = (
    "create_course",
    "create_lesson",
    "create_knowledge_point",
    "update_publish_status",
    "add_prerequisite",
    "remove_prerequisite",
    "skip_prerequisite",
    "grant_mastery",
    "set_mastery_status",
    "confirm_plan",
    "confirm_proposal",
    "adjust_plan",
)


def tool_specs() -> list[dict[str, Any]]:
    """返回可序列化的完整工具清单（文档与测试共用）。"""
    return [
        {
            "name": spec.name,
            "method": spec.method,
            "service": spec.service,
            "write": spec.write,
            "description": spec.description,
        }
        for spec in (*AGENT_TOOL_SPECS, *LEGACY_TOOL_SPECS)
    ]


class AgentToolbox:
    def __init__(self, db: Session, context: LearningContext) -> None:
        self.db = db
        self.context = context

    # ------------------------------------------------------- 只读：课程内容

    def get_course(self, course_code: str) -> ToolResult:
        """读取课程库中的真实课程（不存在/草稿课程由 Service 明确拒绝）。"""
        return self._run(
            "get_course",
            lambda: _ok(CourseService(self.db).get_course_detail(course_code)),
        )

    def get_lesson(self, lesson_code: str) -> ToolResult:
        """读取真实课时的教学内容，Agent 讲解前必须先经此工具取内容。"""
        return self._run(
            "get_lesson",
            lambda: _ok(CourseService(self.db).get_lesson(lesson_code)),
        )

    def get_knowledge_point(self, code: str) -> ToolResult:
        return self._run(
            "get_knowledge_point",
            lambda: _ok(CourseService(self.db).get_knowledge_point(code)),
        )

    def get_user_learning_progress(self) -> ToolResult:
        """学习进度 + 7 态掌握度 + 复习建议（全部来自 Service）。"""
        def call() -> ToolResult:
            return _ok(
                {
                    "overview": LearningOverviewService(self.db).get_overview(),
                    "mastery": MasteryService(self.db).get_overview(),
                    "review_suggestions": MasteryService(self.db).review_suggestions(),
                }
            )

        return self._run("get_user_learning_progress", call)

    # ------------------------------------------------------------- 只读：任务

    def get_today_tasks(self) -> ToolResult:
        return self._run(
            "get_today_tasks",
            lambda: _ok(DailyTaskService(self.db).get_today_tasks()),
        )

    def get_current_plan(self) -> ToolResult:
        return self._run(
            "get_learning_plan",
            lambda: _ok(PlanService(self.db).get_current_plan()),
        )

    def get_progress(self) -> ToolResult:
        return self._run(
            "get_progress",
            lambda: _ok(LearningOverviewService(self.db).get_overview()),
        )

    # ------------------------------------------------------------- 写：证据

    def submit_exercise(self, exercise_code: str, answer: str) -> ToolResult:
        """提交练习：写操作全部委托 MasteryService（含证据流水与状态机）。"""
        def call() -> ToolResult:
            if not answer or not answer.strip():
                return _unavailable("练习答案不能为空")
            return _ok(
                MasteryService(self.db).submit_exercise(exercise_code, answer)
            )

        return self._run("submit_exercise", call)

    def submit_quiz_result(
        self, attempt_id: uuid.UUID | str, answers: list[dict[str, Any]]
    ) -> ToolResult:
        """提交测验答案：写操作全部委托 QuizService（评分 + 掌握证据 + 错题复习）。"""
        def call() -> ToolResult:
            try:
                payload = QuizSubmit(
                    answers=[QuizAnswerIn(**item) for item in answers]
                )
                target = (
                    uuid.UUID(str(attempt_id))
                    if not isinstance(attempt_id, uuid.UUID)
                    else attempt_id
                )
            except (ValidationError, ValueError, TypeError) as exc:
                return _unavailable(f"测验提交参数不合法：{exc}")
            return _ok(QuizService(self.db).submit_attempt(target, payload))

        return self._run("submit_quiz_result", call)

    def request_review_task(
        self, knowledge_point_code: str, reason: str | None = None
    ) -> ToolResult:
        """申请复习：写操作委托 ReviewRequestService（幂等）。"""
        def call() -> ToolResult:
            payload = ReviewRequestIn(
                knowledge_point_code=knowledge_point_code,
                reason=reason,
                source="agent",
                trigger="review_requested",
            )
            return _ok(ReviewRequestService(self.db).request(payload))

        return self._run("request_review_task", call)

    def propose_learning_plan_adjustment(
        self,
        changes: dict[str, Any] | None = None,
        *,
        reason: str | None = None,
        declared_triggers: list[str] | None = None,
        plan_id: uuid.UUID | str | None = None,
    ) -> ToolResult:
        """只生成待确认提案；绝不调用 confirm / adjust_plan 写计划版本。"""
        def call() -> ToolResult:
            try:
                allowed = {
                    "learning_goal",
                    "daily_study_minutes",
                    "expected_duration_days",
                }
                clean = {
                    key: value
                    for key, value in (changes or {}).items()
                    if key in allowed
                }
                payload = ProposalCreate(
                    **clean,
                    reason=reason,
                    source="agent",
                    declared_triggers=declared_triggers or [],
                )
                target = (
                    uuid.UUID(str(plan_id))
                    if plan_id is not None and not isinstance(plan_id, uuid.UUID)
                    else plan_id
                )
            except (ValidationError, ValueError, TypeError) as exc:
                return _unavailable(f"调整提案参数不合法：{exc}")
            return _ok(PlanAdjustmentService(self.db).propose(payload, target))

        return self._run("propose_learning_plan_adjustment", call)

    # ------------------------------------------------------- 既有工具（保留）

    def search_resources(self, query: str) -> ToolResult:
        def call() -> ToolResult:
            course_code = (
                self.context.plan.course_code if self.context.plan else None
            )
            return _ok(
                CourseService(self.db).search_learning_resources(
                    query, course_code=course_code
                )
            )

        return self._run("search_learning_resources", call)

    async def generate_quiz(
        self,
        *,
        scope_type: str,
        knowledge_point_code: str | None = None,
        chapter_code: str | None = None,
    ) -> ToolResult:
        """生成测验（使用内置已验证题库；AI 变式题仍在测验中心按需请求）。"""
        async def call() -> ToolResult:
            payload = QuizCreate(
                scope_type=scope_type,
                knowledge_point_code=knowledge_point_code,
                chapter_code=chapter_code,
                ai_variant_count=0,
            )
            return _ok(await QuizService(self.db).create_quiz(payload))

        return await self._run_async("generate_quiz", call)

    def get_quiz_attempts(self) -> ToolResult:
        return self._run(
            "get_quiz_attempts",
            lambda: _ok(QuizService(self.db).list_attempts()),
        )

    def get_latest_quiz_result(self) -> ToolResult:
        """读取最近一次**已提交**测验的完整结果（批次 8，纯只读）。

        提交动作仍然只走 REST（``FORBIDDEN_TOOL_NAMES`` 不变），本工具只把
        已经由 Service 评分过的结果读出来，供聊天里展示结果卡片。
        """

        def call() -> ToolResult:
            service = QuizService(self.db)
            # list_attempts 已按 started_at 倒序，取第一条已提交的即为最近一次。
            submitted = [
                item
                for item in service.list_attempts()
                if item.status == "submitted"
            ]
            if not submitted:
                return _unavailable("还没有已提交的测验，暂时没有成绩可以查看")
            return _ok(service.get_attempt(submitted[0].id))

        return self._run("get_latest_quiz_result", call)

    def get_mistakes(self) -> ToolResult:
        return self._run(
            "get_mistakes", lambda: _ok(ReviewService(self.db).list_mistakes())
        )

    def get_review_tasks(self) -> ToolResult:
        return self._run(
            "get_review_tasks", lambda: _ok(ReviewService(self.db).list_tasks())
        )

    # ------------------------------------------------------------- 内部工具

    def _run(self, name: str, call) -> ToolResult:
        started = time.perf_counter()
        try:
            result = call()
        except HTTPException as exc:
            result = _from_http_error(exc)
        except Exception:
            logger.exception("Agent 工具执行异常: tool=%s", name)
            result = _failed("服务暂时不可用，请稍后重试")
        self._log(name, result, started)
        return result

    async def _run_async(self, name: str, call) -> ToolResult:
        started = time.perf_counter()
        try:
            result = await call()
        except HTTPException as exc:
            result = _from_http_error(exc)
        except Exception:
            logger.exception("Agent 工具执行异常: tool=%s", name)
            result = _failed("服务暂时不可用，请稍后重试")
        self._log(name, result, started)
        return result

    @staticmethod
    def _log(name: str, result: ToolResult, started: float) -> None:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "agent tool name=%s status=%s duration_ms=%d",
            name,
            result.status,
            duration_ms,
        )


def _ok(data: Any) -> ToolResult:
    return ToolResult(ok=True, status="ok", data=data)


def _unavailable(message: str) -> ToolResult:
    return ToolResult(ok=False, status="unavailable", message=message)


def _failed(message: str) -> ToolResult:
    return ToolResult(ok=False, status="failed", message=message)


def _from_http_error(exc: HTTPException) -> ToolResult:
    detail = exc.detail
    message = detail if isinstance(detail, str) else "请求未通过后端校验"
    if exc.status_code >= 500:
        return _failed("服务暂时不可用，请稍后重试")
    return _unavailable(message)
