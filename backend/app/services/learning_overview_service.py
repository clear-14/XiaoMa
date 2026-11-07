"""学习进度概览业务层（阶段 10）。

只做只读聚合，不新增业务规则：
- 学习档案来自 ProfileService；
- 计划进度来自 PlanService（当前生效版本）；
- 已学习/掌握状态与测验成绩来自 QuizService；
- 错题与到期复习任务来自 ReviewService。

Agent 通过该 Service 读取进度，不直接访问数据库。
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas.learning_overview import ChapterProgressOut, LearningOverviewOut
from app.services.plan_service import PlanService
from app.services.profile_service import ProfileService
from app.services.quiz_service import QuizService
from app.services.review_service import ReviewService
from app.services.time_utils import utc_today_naive


class LearningOverviewService:
    def __init__(self, db: Session) -> None:
        self.profile_service = ProfileService(db)
        self.plan_service = PlanService(db)
        self.quiz_service = QuizService(db)
        self.review_service = ReviewService(db)

    def get_overview(self) -> LearningOverviewOut:
        profile = self.profile_service.get_profile()
        plan, plan_available = self._load_plan()
        eligibility = self.quiz_service.get_eligibility()
        attempts = self.quiz_service.list_attempts()
        mistakes = self.review_service.list_mistakes()
        review_tasks = self.review_service.list_tasks()

        learned = eligibility.learned_knowledge_points
        mastered_count = sum(1 for item in learned if item.status == "mastered")
        learning_count = sum(1 for item in learned if item.status == "learning")
        pending_count = sum(
            1 for item in learned if item.status == "pending_verification"
        )
        review_due_count = sum(1 for item in learned if item.status == "review_due")

        chapter_groups: dict[str, ChapterProgressOut] = {}
        for item in learned:
            group = chapter_groups.get(item.chapter_code)
            if group is None:
                group = ChapterProgressOut(
                    chapter_code=item.chapter_code,
                    chapter_title=item.chapter_title,
                    learned_count=0,
                    mastered_count=0,
                )
                chapter_groups[item.chapter_code] = group
            group.learned_count += 1
            if item.status == "mastered":
                group.mastered_count += 1

        submitted = [
            attempt
            for attempt in attempts
            if attempt.status == "submitted" and attempt.score is not None
        ]
        average_score = (
            round(sum(attempt.score for attempt in submitted) / len(submitted), 1)
            if submitted
            else None
        )
        latest_score = submitted[0].score if submitted else None

        plan_version = plan.current_version if plan is not None else None
        plan_total = len(plan_version.items) if plan_version else 0
        plan_completed = (
            sum(1 for item in plan_version.items if item.status == "completed")
            if plan_version
            else 0
        )
        next_item = (
            next(
                (item for item in plan_version.items if item.status == "pending"),
                None,
            )
            if plan_version
            else None
        )
        progress_percent = (
            round(plan_completed / plan_total * 100, 1) if plan_total else 0.0
        )

        pending_mistakes = sum(
            1 for mistake in mistakes if mistake.review_status == "pending"
        )
        notes: list[str] = []
        if plan is None:
            notes.append("暂无学习计划，请先创建并确认学习计划")
        elif plan_version is None:
            notes.append("学习计划尚未确认，确认后才能按计划统计进度")
        elif plan_total and plan_completed >= plan_total:
            notes.append("当前计划的全部知识点项目已完成")
        if not learned:
            notes.append("还没有已学习的知识点")

        return LearningOverviewOut(
            today=utc_today_naive(),
            learning_goal=profile.learning_goal,
            current_level=profile.current_level,
            daily_study_minutes=profile.daily_study_minutes,
            plan_available=plan_available,
            plan_confirmed=plan_version is not None,
            plan_course_name=plan.course_name if plan is not None else None,
            plan_current_version_number=(
                plan.current_version_number if plan is not None else None
            ),
            plan_pending_version_number=(
                plan.pending_version_number if plan is not None else None
            ),
            plan_total_items=plan_total,
            plan_completed_items=plan_completed,
            plan_progress_percent=progress_percent,
            plan_current_day=next_item.day_index if next_item else None,
            plan_warning=plan_version.warning if plan_version else None,
            learned_count=len(learned),
            mastered_count=mastered_count,
            learning_count=learning_count,
            pending_verification_count=pending_count,
            review_due_count=review_due_count,
            quiz_attempt_count=len(attempts),
            quiz_submitted_count=len(submitted),
            quiz_average_score=average_score,
            latest_quiz_score=latest_score,
            mistake_total_count=len(mistakes),
            mistake_pending_count=pending_mistakes,
            mistake_resolved_count=len(mistakes) - pending_mistakes,
            mistake_due_count=sum(1 for task in review_tasks if task.is_due),
            chapters=list(chapter_groups.values()),
            notes=notes,
        )

    def _load_plan(self):
        try:
            return self.plan_service.get_current_plan(), True
        except HTTPException as exc:
            if exc.status_code == 404:
                return None, False
            raise
