"""Agent 工具层（阶段 10）：把已有业务 Service 包装成可审计的工具调用。

规则：
- 工具只调用 Service，不直接访问数据库；
- 业务上可预期的拒绝（暂无计划、未学习、未确认等）返回 unavailable，
  由子图给出明确说明；服务异常返回 failed，子图必须报错而不是伪造成功；
- 日志只记录工具名、状态与耗时，不记录提示词、用户消息或密钥。
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agent.contracts import LearningContext, ToolResult
from app.schemas.plan import PlanAdjust
from app.schemas.quiz import QuizCreate
from app.services.course_service import CourseService
from app.services.daily_task_service import DailyTaskService
from app.services.learning_overview_service import LearningOverviewService
from app.services.plan_service import PlanService
from app.services.quiz_service import QuizService
from app.services.review_service import ReviewService

logger = logging.getLogger("xiaoma.agent")


class AgentToolbox:
    def __init__(self, db: Session, context: LearningContext) -> None:
        self.db = db
        self.context = context

    # ------------------------------------------------------------- 计划/任务

    def get_today_tasks(self) -> ToolResult:
        def call() -> ToolResult:
            return _ok(DailyTaskService(self.db).get_today_tasks())

        return self._run("get_today_tasks", call)

    def get_current_plan(self) -> ToolResult:
        def call() -> ToolResult:
            return _ok(PlanService(self.db).get_current_plan())

        return self._run("get_learning_plan", call)

    def get_progress(self) -> ToolResult:
        def call() -> ToolResult:
            return _ok(LearningOverviewService(self.db).get_overview())

        return self._run("get_progress", call)

    def adjust_plan(self, plan_id: uuid.UUID, changes: dict[str, Any]) -> ToolResult:
        def call() -> ToolResult:
            try:
                payload = PlanAdjust(**changes)
            except ValidationError:
                return _unavailable(
                    "调整参数不合法：每日学习时间需在 1-1440 分钟，"
                    "期望周期需在 1-3650 天，学习目标不能为空"
                )
            return _ok(PlanService(self.db).adjust_plan(plan_id, payload))

        return self._run("update_learning_plan", call)

    # ------------------------------------------------------------- 课程/资源

    def get_knowledge_point(self, code: str) -> ToolResult:
        def call() -> ToolResult:
            return _ok(CourseService(self.db).get_knowledge_point(code))

        return self._run("get_knowledge_point", call)

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

    # ------------------------------------------------------------- 测验/错题

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
        def call() -> ToolResult:
            return _ok(QuizService(self.db).list_attempts())

        return self._run("get_quiz_attempts", call)

    def get_mistakes(self) -> ToolResult:
        def call() -> ToolResult:
            return _ok(ReviewService(self.db).list_mistakes())

        return self._run("get_mistakes", call)

    def get_review_tasks(self) -> ToolResult:
        def call() -> ToolResult:
            return _ok(ReviewService(self.db).list_tasks())

        return self._run("get_review_tasks", call)

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
