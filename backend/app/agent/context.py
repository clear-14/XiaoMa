"""读取本轮对话的学习上下文（阶段 10）。

全部数据通过现有 Service 层读取；Agent 不导入 Repository、不执行 SQL。
读取失败时记录日志并给出 notes，不把缺失数据伪装成真实值。
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agent.contracts import (
    DailyTaskSnapshot,
    KnowledgePointSnapshot,
    LearningContext,
    PlanSnapshot,
    ProfileSnapshot,
)
from app.schemas.plan import CurrentPlanOut, PlanVersionOut
from app.services.conversation_service import ChatContext
from app.services.plan_service import PlanService
from app.services.profile_service import ProfileService
from app.services.time_utils import utc_today_naive

logger = logging.getLogger("xiaoma.agent")


class AgentContextService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def load(self, chat_context: ChatContext) -> LearningContext:
        notes: list[str] = []
        profile = self._load_profile(notes)
        plan = self._load_plan(notes)

        conversation = chat_context.conversation
        knowledge_point = None
        if conversation.knowledge_point is not None:
            kp = conversation.knowledge_point
            knowledge_point = KnowledgePointSnapshot(
                code=kp.code,
                name=kp.name,
                chapter_code=kp.chapter.code,
                chapter_title=kp.chapter.title,
                learning_status=chat_context.learning_status,
            )

        daily_task = None
        if conversation.daily_task is not None:
            task = conversation.daily_task
            daily_task = DailyTaskSnapshot(
                id=str(task.id),
                status=task.status,
                day_index=task.day_index,
                task_date=task.task_date,
            )

        return LearningContext(
            today=utc_today_naive(),
            profile=profile,
            knowledge_point=knowledge_point,
            daily_task=daily_task,
            plan=plan,
            notes=notes,
        )

    def _load_profile(self, notes: list[str]) -> ProfileSnapshot | None:
        try:
            profile = ProfileService(self.db).get_profile()
        except Exception:
            logger.exception("读取学习档案失败")
            notes.append("无法读取学习档案")
            return None
        return ProfileSnapshot(
            learning_goal=profile.learning_goal,
            current_level=profile.current_level,
            daily_study_minutes=profile.daily_study_minutes,
        )

    def _load_plan(self, notes: list[str]) -> PlanSnapshot | None:
        try:
            plan = PlanService(self.db).get_current_plan()
        except HTTPException as exc:
            if exc.status_code == 404:
                notes.append("暂无学习计划")
                return None
            logger.warning("读取学习计划失败: %s", exc.detail)
            notes.append("无法读取学习计划")
            return None
        except Exception:
            logger.exception("读取学习计划失败")
            notes.append("无法读取学习计划")
            return None
        return _plan_snapshot(plan)


def _plan_snapshot(plan: CurrentPlanOut) -> PlanSnapshot:
    version: PlanVersionOut | None = plan.current_version or plan.pending_version
    items = version.items if version is not None else []
    completed = sum(1 for item in items if item.status == "completed")
    next_item = next((item for item in items if item.status == "pending"), None)

    return PlanSnapshot(
        plan_id=str(plan.id),
        course_code=plan.course_code,
        course_name=plan.course_name,
        status=plan.status,
        confirmed=plan.current_version is not None,
        current_version_number=plan.current_version_number,
        pending_version_number=plan.pending_version_number,
        daily_study_minutes=version.daily_study_minutes if version else None,
        expected_duration_days=version.expected_duration_days if version else None,
        computed_duration_days=version.computed_duration_days if version else None,
        total_items=len(items),
        completed_items=completed,
        next_pending_day_index=next_item.day_index if next_item else None,
        next_pending_knowledge_point_code=(
            next_item.knowledge_point_code if next_item else None
        ),
        warning=version.warning if version else None,
    )
