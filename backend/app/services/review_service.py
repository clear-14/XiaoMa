"""错题本与间隔复习业务层（PRD 6.5 / 阶段 9）。

规则：
- 测验答错即写入/更新错题（用户+题目唯一），并生成 1 天后复习任务；
- 重复答错：旧的待复习任务标记 skipped，重新从 1 天间隔开始；
- 复习答对：按 1 → 3 → 7 → 14 天逐级推进，完成 14 天复习后标记已解决；
- 复习答错：间隔重置为 1 天，错题保持待复习；
- 每次复习提交都创建一条 scope_type=review 的测验记录与答题记录，保留完整历史；
- 复习任务允许提前提交（页面会明确标记是否到期），但不能重复提交已完成的任
  务；所有时间统一使用 naive UTC。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.quiz import (
    REVIEW_INTERVALS,
    Mistake,
    QuizAnswer,
    QuizAttempt,
    ReviewTask,
)
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.repositories.quiz_repository import QuizRepository
from app.repositories.review_repository import (
    MistakeRepository,
    ReviewTaskRepository,
)
from app.schemas.quiz import (
    MistakeOut,
    ReviewResultOut,
    ReviewTaskOut,
)
from app.services.profile_service import DEFAULT_USERNAME
from app.services.quiz_grading import grade_answer
from app.services.quiz_presenters import knowledge_point_out, question_out
from app.services.time_utils import utc_now_naive


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.profile_repo = ProfileRepository(db)
        self.mistake_repo = MistakeRepository(db)
        self.task_repo = ReviewTaskRepository(db)
        self.quiz_repo = QuizRepository(db)

    # ------------------------------------------------------------- 错题本

    def list_mistakes(self, review_status: str | None = None) -> list[MistakeOut]:
        if review_status is not None and review_status not in ("pending", "resolved"):
            raise HTTPException(status_code=422, detail="review_status 取值不合法")
        user = self._get_or_create_user()
        mistakes = self.mistake_repo.list_for_user(user.id, review_status)
        pending = self.task_repo.map_pending_for_user(user.id)
        return [
            self._mistake_out(
                mistake,
                pending_task_id=pending[mistake.id].id
                if mistake.id in pending
                else None,
            )
            for mistake in mistakes
        ]

    # ------------------------------------------------------------- 复习任务

    def list_tasks(self) -> list[ReviewTaskOut]:
        """待复习任务（按到期时间升序；提前复习由前端提示是否到期）。"""
        user = self._get_or_create_user()
        now = utc_now_naive()
        tasks = self.task_repo.list_pending(user.id)
        return [self._task_out(task, now=now) for task in tasks]

    def submit_review(
        self, task_id: uuid.UUID, answer: object
    ) -> ReviewResultOut:
        """提交一道错题的复习答案并推进/重置复习间隔。"""
        user = self._get_or_create_user()
        task = self.task_repo.get(task_id, user.id)
        if task is None:
            raise HTTPException(status_code=404, detail="复习任务不存在")
        if task.status != "pending":
            raise HTTPException(status_code=409, detail="该复习任务已完成或已跳过")

        now = utc_now_naive()
        grade = grade_answer(task.question, answer)
        attempt = QuizAttempt(
            user_id=user.id,
            scope_type="review",
            scope_ref=task.question.code,
            scope_name=f"错题复习：{task.knowledge_point.name}",
            status="submitted",
            question_count=1,
            total_points=grade.max_score,
            score=round(grade.score / grade.max_score * 100, 1),
            started_at=now,
            submitted_at=now,
        )
        quiz_answer = QuizAnswer(
            attempt=attempt,
            question=task.question,
            question_order=1,
            max_score=grade.max_score,
            user_answer=answer,
            score=grade.score,
            is_correct=grade.is_correct,
            grading_basis=grade.basis,
            graded_at=now,
        )
        self.quiz_repo.add_attempt(attempt)
        self.quiz_repo.add_answer(quiz_answer)

        task.status = "completed"
        task.completed_at = now
        task.last_result = "correct" if grade.is_correct else "wrong"
        task.last_attempt = attempt

        # 同一错题的其他待复习任务（正常不会存在）标记 skipped，避免重复复习。
        # 查询不触发 flush，当前任务仍会出现在结果中，需按 ID 排除。
        for other in self.task_repo.list_pending_for_mistake(task.mistake_id):
            if other.id != task.id:
                other.status = "skipped"

        mistake = task.mistake
        mistake.last_answer = answer
        mistake.last_attempt = attempt
        next_task: ReviewTask | None = None
        if grade.is_correct:
            mistake.review_stage = min(
                mistake.review_stage + 1, len(REVIEW_INTERVALS)
            )
            if mistake.review_stage >= len(REVIEW_INTERVALS):
                mistake.review_status = "resolved"
                mistake.resolved_at = now
                mistake.next_review_at = None
                message = "连续完成 1/3/7/14 天复习，这道错题已标记为已解决"
            else:
                interval = REVIEW_INTERVALS[mistake.review_stage]
                next_task = self._create_task(
                    user.id, mistake, interval=interval, now=now
                )
                message = (
                    f"本次复习通过，{interval} 天后进行下一次复习"
                )
        else:
            mistake.attempt_count += 1
            mistake.last_wrong_at = now
            mistake.review_stage = 0
            mistake.review_status = "pending"
            mistake.resolved_at = None
            next_task = self._create_task(
                user.id, mistake, interval=REVIEW_INTERVALS[0], now=now
            )
            message = "本次复习仍未完全答对，复习间隔已重置为 1 天"

        self.db.commit()

        return ReviewResultOut(
            review_task=self._task_out(
                task, now=now, include_result=True, answer=quiz_answer
            ),
            question=question_out(
                task.question,
                order=1,
                answer=quiz_answer,
                include_result=True,
            ),
            mistake=self._mistake_out(
                mistake, pending_task_id=next_task.id if next_task else None
            ),
            next_review_task=(
                self._task_out(next_task, now=now) if next_task else None
            ),
            message=message,
        )

    # ------------------------------------------------------------- 测验错题联动

    def record_wrong_answers(
        self,
        user: User,
        attempt: QuizAttempt,
        wrong_answers: list[QuizAnswer],
        now: datetime | None = None,
    ) -> None:
        """测验提交后记录错题并安排 1 天后复习（由 QuizService 调用）。"""
        now = now or utc_now_naive()
        for answer in wrong_answers:
            question = answer.question
            mistake = self.mistake_repo.get(user.id, question.id)
            if mistake is None:
                mistake = Mistake(
                    user_id=user.id,
                    question=question,
                    question_id=question.id,
                    knowledge_point=question.knowledge_point,
                    knowledge_point_id=question.knowledge_point_id,
                    attempt_count=1,
                    last_answer=answer.user_answer,
                    last_attempt=attempt,
                    last_wrong_at=now,
                    review_status="pending",
                    review_stage=0,
                )
                self.mistake_repo.add(mistake)
            else:
                mistake.attempt_count += 1
                mistake.last_answer = answer.user_answer
                mistake.last_attempt = attempt
                mistake.last_wrong_at = now
                mistake.review_status = "pending"
                mistake.review_stage = 0
                mistake.resolved_at = None
                for existing in self.task_repo.list_pending_for_mistake(mistake.id):
                    existing.status = "skipped"
            self._create_task(
                user.id, mistake, interval=REVIEW_INTERVALS[0], now=now
            )
        self.task_repo.flush()

    # ------------------------------------------------------------- 内部工具

    def _create_task(
        self,
        user_id: uuid.UUID,
        mistake: Mistake,
        *,
        interval: int,
        now: datetime,
    ) -> ReviewTask:
        due_at = now + timedelta(days=interval)
        task = ReviewTask(
            user_id=user_id,
            mistake=mistake,
            question=mistake.question,
            question_id=mistake.question_id,
            knowledge_point=mistake.knowledge_point,
            knowledge_point_id=mistake.knowledge_point_id,
            due_at=due_at,
            interval_days=interval,
            status="pending",
        )
        mistake.next_review_at = due_at
        self.task_repo.add(task)
        return task

    def _get_or_create_user(self) -> User:
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user

    def _mistake_out(
        self, mistake: Mistake, pending_task_id: uuid.UUID | None
    ) -> MistakeOut:
        question = mistake.question
        return MistakeOut(
            id=mistake.id,
            question=question_out(
                question,
                include_result=True,
                user_answer=mistake.last_answer,
            ),
            knowledge_point=knowledge_point_out(question.knowledge_point),
            attempt_count=mistake.attempt_count,
            last_answer=mistake.last_answer,
            last_wrong_at=mistake.last_wrong_at,
            review_status=mistake.review_status,
            review_stage=mistake.review_stage,
            next_review_at=mistake.next_review_at,
            resolved_at=mistake.resolved_at,
            pending_review_task_id=pending_task_id,
        )

    @staticmethod
    def _task_out(
        task: ReviewTask,
        *,
        now: datetime,
        include_result: bool = False,
        answer: QuizAnswer | None = None,
    ) -> ReviewTaskOut:
        return ReviewTaskOut(
            id=task.id,
            mistake_id=task.mistake_id,
            due_at=task.due_at,
            interval_days=task.interval_days,
            status=task.status,
            is_due=task.status == "pending" and task.due_at <= now,
            last_result=task.last_result,
            question=question_out(
                task.question,
                order=1,
                answer=answer,
                include_result=include_result,
            ),
            knowledge_point=knowledge_point_out(task.question.knowledge_point),
        )
