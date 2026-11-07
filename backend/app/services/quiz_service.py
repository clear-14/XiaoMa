"""测验业务层（PRD 6.2-6.4 / 阶段 9）。

范围与题量（技术决策，记录于任务书）：
- 知识点测验：目标 5 题，只能针对「已学习」知识点；
- 章节测验：目标 10 题，只取该章节内已学习知识点；
- 阶段测验：目标 30 题，取当前生效学习计划所属课程内已学习知识点；
- 题量受题库实际数量限制，正式组卷只读取内置题库与通过验证的 AI 变式题；
- AI 变式题生成失败时降级为内置题库，并在 ai_note 中明确说明。

掌握判定（PRD 6.1 / 6.4）：
- 只有知识点测验可以更新掌握状态，章节/阶段测验只记录成绩；
- 必须同时满足：有效题量 ≥ 3、全部题目通过、百分制得分 ≥ 90；
- 主观题「通过」的判定依据（参考答案、命中/缺失关键词、覆盖率）随答题记录
  持久化；90 分只是参考线之一，不单独构成掌握依据；
- 任务完成或普通对话永远不会写入 mastered。
"""

from __future__ import annotations

import random
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import KnowledgePoint
from app.models.learning_profile import LearningProfile
from app.models.quiz import (
    QuizAnswer,
    QuizAttempt,
    Question,
)
from app.models.user import User
from app.repositories.course_repository import CourseRepository
from app.repositories.learning_profile_repository import (
    LEARNED_STATUSES,
    LearningProfileRepository,
)
from app.repositories.plan_repository import PlanRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.quiz_repository import QuizRepository
from app.schemas.quiz import (
    EligibilityChapterOut,
    EligibilityKnowledgePointOut,
    EligibilityStageOut,
    MasteryUpdateOut,
    QuizAttemptOut,
    QuizAttemptSummaryOut,
    QuizCreate,
    QuizEligibilityOut,
    QuizSubmit,
)
from app.services.ai_question_service import MAX_AI_VARIANTS, AiQuestionService
from app.services.profile_service import DEFAULT_USERNAME
from app.services.quiz_grading import (
    MASTERY_MIN_QUESTIONS,
    MASTERY_MIN_SCORE,
    grade_answer,
)
from app.services.quiz_presenters import knowledge_point_out, question_out
from app.services.review_service import ReviewService
from app.services.time_utils import utc_now_naive

QUESTION_TARGETS: dict[str, int] = {
    "knowledge_point": 5,
    "chapter": 10,
    "stage": 30,
}

SCOPE_LABELS: dict[str, str] = {
    "knowledge_point": "知识点测验",
    "chapter": "章节测验",
    "stage": "阶段综合测验",
}


class QuizService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.profile_repo = ProfileRepository(db)
        self.course_repo = CourseRepository(db)
        self.plan_repo = PlanRepository(db)
        self.learning_profile_repo = LearningProfileRepository(db)
        self.question_repo = QuestionRepository(db)
        self.quiz_repo = QuizRepository(db)

    # ------------------------------------------------------------- 可测验范围

    def get_eligibility(self) -> QuizEligibilityOut:
        """只返回已学习知识点及其可测题量，未学习内容不会出现在正式测验范围。"""
        user = self._get_or_create_user()
        learned = self.learning_profile_repo.list_learned(user.id)
        counts = self.question_repo.count_selectable_by_knowledge_point()

        kp_out: list[EligibilityKnowledgePointOut] = []
        chapter_groups: dict[uuid.UUID, dict] = {}
        for profile in learned:
            kp = profile.knowledge_point
            count = counts.get(kp.id, 0)
            kp_out.append(
                EligibilityKnowledgePointOut(
                    code=kp.code,
                    name=kp.name,
                    chapter_code=kp.chapter.code,
                    chapter_title=kp.chapter.title,
                    status=profile.status,
                    question_count=count,
                    quiz_available=count > 0,
                )
            )
            group = chapter_groups.setdefault(
                kp.chapter_id,
                {
                    "chapter": kp.chapter,
                    "learned_count": 0,
                    "question_count": 0,
                },
            )
            group["learned_count"] += 1
            group["question_count"] += count

        chapters_out = [
            EligibilityChapterOut(
                code=group["chapter"].code,
                title=group["chapter"].title,
                learned_knowledge_point_count=group["learned_count"],
                question_count=group["question_count"],
                quiz_available=group["question_count"] > 0,
            )
            for group in chapter_groups.values()
        ]

        return QuizEligibilityOut(
            learned_knowledge_points=kp_out,
            chapters=chapters_out,
            stage=self._stage_eligibility(user, learned, counts),
        )

    def _stage_eligibility(
        self,
        user: User,
        learned: list[LearningProfile],
        counts: dict[uuid.UUID, int],
    ) -> EligibilityStageOut:
        plan = self.plan_repo.get_latest_plan(user.id)
        if plan is None:
            return EligibilityStageOut(
                available=False, note="暂无学习计划，请先创建并确认学习计划"
            )
        if plan.current_version_number is None:
            return EligibilityStageOut(
                available=False,
                course_code=plan.course.code,
                course_name=plan.course.name,
                note="学习计划尚未确认，确认后才可以进行阶段测验",
            )
        profiles = self._learned_in_course(learned, plan.course_id)
        question_count = sum(counts.get(item.knowledge_point_id, 0) for item in profiles)
        note: str | None = None
        if not profiles:
            note = "当前学习阶段还没有已学习的知识点"
        elif question_count == 0:
            note = "当前学习阶段暂无可用题目"
        return EligibilityStageOut(
            available=bool(profiles) and question_count > 0,
            course_code=plan.course.code,
            course_name=plan.course.name,
            learned_knowledge_point_count=len(profiles),
            question_count=question_count,
            note=note,
        )

    # ------------------------------------------------------------- 创建测验

    async def create_quiz(self, payload: QuizCreate) -> QuizAttemptOut:
        """按范围组卷；题目只来自已学习知识点。"""
        user = self._get_or_create_user()
        if payload.scope_type == "knowledge_point":
            knowledge_points, scope_ref, scope_name = self._knowledge_point_scope(
                user, payload.knowledge_point_code or ""
            )
        elif payload.scope_type == "chapter":
            knowledge_points, scope_ref, scope_name = self._chapter_scope(
                user, payload.chapter_code or ""
            )
        else:
            knowledge_points, scope_ref, scope_name = self._stage_scope(user)

        kp_ids = [kp.id for kp in knowledge_points]
        questions = self.question_repo.list_selectable_by_knowledge_points(kp_ids)

        ai_requested = min(payload.ai_variant_count, MAX_AI_VARIANTS)
        ai_accepted = 0
        ai_note: str | None = None
        if ai_requested > 0 and questions:
            accepted, ai_note = await AiQuestionService(self.db).generate_variants(
                questions, ai_requested
            )
            ai_accepted = len(accepted)
            if accepted:
                # generate_variants 内部已 flush，重新读取可包含新题
                questions = self.question_repo.list_selectable_by_knowledge_points(
                    kp_ids
                )

        if not questions:
            raise HTTPException(
                status_code=409,
                detail="该范围内暂无正式可用题目，请先完成相关知识点学习",
            )

        selected = self._select_questions(
            questions, knowledge_points, QUESTION_TARGETS[payload.scope_type]
        )
        now = utc_now_naive()
        attempt = QuizAttempt(
            user_id=user.id,
            scope_type=payload.scope_type,
            scope_ref=scope_ref,
            scope_name=scope_name,
            status="in_progress",
            question_count=len(selected),
            total_points=len(selected) * 10,
            ai_requested=ai_requested,
            ai_accepted=ai_accepted,
            ai_note=ai_note,
            started_at=now,
        )
        for index, question in enumerate(selected, start=1):
            QuizAnswer(
                attempt=attempt,
                question=question,
                question_order=index,
                max_score=10,
            )
        self.quiz_repo.add_attempt(attempt)
        self.db.commit()
        return self._attempt_out(attempt)

    def _knowledge_point_scope(
        self, user: User, code: str
    ) -> tuple[list[KnowledgePoint], str, str]:
        kp = self.course_repo.get_knowledge_point_by_code(code)
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")
        profile = self.learning_profile_repo.get_profile(user.id, kp.id)
        if profile is None or profile.status not in LEARNED_STATUSES:
            raise HTTPException(
                status_code=400, detail="该知识点尚未学习，不能进行正式测验"
            )
        return [kp], kp.code, kp.name

    def _chapter_scope(
        self, user: User, code: str
    ) -> tuple[list[KnowledgePoint], str, str]:
        chapter = self.course_repo.get_chapter_by_code(code)
        if chapter is None:
            raise HTTPException(status_code=404, detail="章节不存在")
        learned = self.learning_profile_repo.list_learned(user.id)
        kps = [
            profile.knowledge_point
            for profile in learned
            if profile.knowledge_point.chapter_id == chapter.id
        ]
        if not kps:
            raise HTTPException(
                status_code=400,
                detail="该章节还没有已学习的知识点，不能进行正式测验",
            )
        return kps, chapter.code, chapter.title

    def _stage_scope(
        self, user: User
    ) -> tuple[list[KnowledgePoint], None, str]:
        plan = self.plan_repo.get_latest_plan(user.id)
        if plan is None:
            raise HTTPException(status_code=404, detail="暂无学习计划，请先创建学习计划")
        if plan.current_version_number is None:
            raise HTTPException(
                status_code=409, detail="学习计划尚未确认，请先确认计划"
            )
        learned = self.learning_profile_repo.list_learned(user.id)
        profiles = self._learned_in_course(learned, plan.course_id)
        if not profiles:
            raise HTTPException(
                status_code=400,
                detail="当前学习阶段还没有已学习的知识点，不能进行正式测验",
            )
        return (
            [profile.knowledge_point for profile in profiles],
            None,
            f"{plan.course.name} · {SCOPE_LABELS['stage']}",
        )

    @staticmethod
    def _learned_in_course(
        learned: list[LearningProfile], course_id: uuid.UUID
    ) -> list[LearningProfile]:
        return [
            profile
            for profile in learned
            if profile.knowledge_point.chapter.course_id == course_id
        ]

    @staticmethod
    def _select_questions(
        questions: list[Question],
        knowledge_points: list[KnowledgePoint],
        limit: int,
    ) -> list[Question]:
        """按知识点轮转选题，保证覆盖面；同知识点内顺序随机。"""
        ordered_ids = [kp.id for kp in knowledge_points]
        groups: dict[uuid.UUID, list[Question]] = {kp_id: [] for kp_id in ordered_ids}
        for question in questions:
            groups.setdefault(question.knowledge_point_id, []).append(question)
        for group in groups.values():
            random.shuffle(group)

        selected: list[Question] = []
        round_index = 0
        while len(selected) < limit:
            progressed = False
            for kp_id in ordered_ids:
                group = groups.get(kp_id, [])
                if round_index < len(group):
                    selected.append(group[round_index])
                    progressed = True
                    if len(selected) >= limit:
                        break
            if not progressed:
                break
            round_index += 1
        random.shuffle(selected)
        return selected

    # ------------------------------------------------------------- 查询

    def list_attempts(self) -> list[QuizAttemptSummaryOut]:
        user = self._get_or_create_user()
        attempts = self.quiz_repo.list_attempts(user.id)
        return [
            QuizAttemptSummaryOut(
                id=attempt.id,
                scope_type=attempt.scope_type,
                scope_name=attempt.scope_name,
                status=attempt.status,
                question_count=attempt.question_count,
                score=attempt.score,
                ai_accepted=attempt.ai_accepted,
                started_at=attempt.started_at,
                submitted_at=attempt.submitted_at,
            )
            for attempt in attempts
        ]

    def get_attempt(self, attempt_id: uuid.UUID) -> QuizAttemptOut:
        user = self._get_or_create_user()
        attempt = self._get_attempt_or_404(attempt_id, user)
        return self._attempt_out(attempt)

    # ------------------------------------------------------------- 提交评分

    def submit_attempt(
        self, attempt_id: uuid.UUID, payload: QuizSubmit
    ) -> QuizAttemptOut:
        user = self._get_or_create_user()
        attempt = self._get_attempt_or_404(attempt_id, user)
        if attempt.status == "submitted":
            raise HTTPException(status_code=409, detail="该测验已提交，不能重复提交")

        submitted = {
            item.question_id: item.answer for item in payload.answers
        }
        expected = {answer.question_id for answer in attempt.answers}
        if set(submitted) != expected:
            raise HTTPException(
                status_code=400,
                detail="请完成本次测验的全部题目后再提交",
            )

        now = utc_now_naive()
        wrong_answers: list[QuizAnswer] = []
        for answer in attempt.answers:
            result = grade_answer(
                answer.question, submitted[answer.question_id]
            )
            answer.user_answer = submitted[answer.question_id]
            answer.score = result.score
            answer.is_correct = result.is_correct
            answer.grading_basis = result.basis
            answer.graded_at = now
            if not result.is_correct:
                wrong_answers.append(answer)

        total = sum(answer.max_score for answer in attempt.answers)
        gained = sum(answer.score or 0 for answer in attempt.answers)
        attempt.score = round(gained / total * 100, 1) if total else 0.0
        attempt.status = "submitted"
        attempt.submitted_at = now
        attempt.mastery_updates = (
            [self._mastery_update(attempt)]
            if attempt.scope_type == "knowledge_point"
            else []
        )
        if attempt.scope_type == "knowledge_point":
            update = attempt.mastery_updates[0]
            if update["achieved"]:
                target = attempt.answers[0].question.knowledge_point
                self.learning_profile_repo.set_mastered(user.id, target.id, now)

        if wrong_answers:
            ReviewService(self.db).record_wrong_answers(
                user, attempt, wrong_answers, now=now
            )

        self.db.commit()
        return self._attempt_out(attempt)

    def _mastery_update(self, attempt: QuizAttempt) -> dict:
        """知识点测验的掌握判定；返回可持久化的判定快照与原因。"""
        target = attempt.answers[0].question.knowledge_point
        question_count = attempt.question_count
        score = attempt.score or 0.0
        wrong_count = sum(1 for answer in attempt.answers if not answer.is_correct)

        reasons: list[str] = []
        if question_count < MASTERY_MIN_QUESTIONS:
            reasons.append(
                f"有效题量 {question_count} 道少于 {MASTERY_MIN_QUESTIONS} 道，"
                "无法完成掌握验证"
            )
        if wrong_count:
            reasons.append(
                f"仍有 {wrong_count} 道题未通过（主观题需关键词覆盖率达到 80%）"
            )
        if score < MASTERY_MIN_SCORE:
            reasons.append(
                f"百分制得分 {score} 低于 {MASTERY_MIN_SCORE:g} 分参考线"
            )

        achieved = not reasons
        if achieved:
            reasons.append(
                "满足掌握条件：不少于 3 道题、全部题目通过、"
                f"百分制得分不低于 {MASTERY_MIN_SCORE:g}"
            )
        return MasteryUpdateOut(
            knowledge_point_code=target.code,
            knowledge_point_name=target.name,
            achieved=achieved,
            reasons=reasons,
        ).model_dump()

    # ------------------------------------------------------------- 内部工具

    def _get_or_create_user(self) -> User:
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user

    def _get_attempt_or_404(
        self, attempt_id: uuid.UUID, user: User
    ) -> QuizAttempt:
        attempt = self.quiz_repo.get_attempt(attempt_id, user.id)
        if attempt is None:
            raise HTTPException(status_code=404, detail="测验记录不存在")
        return attempt

    @staticmethod
    def _attempt_out(attempt: QuizAttempt) -> QuizAttemptOut:
        submitted = attempt.status == "submitted"
        answers = sorted(attempt.answers, key=lambda item: item.question_order)
        return QuizAttemptOut(
            id=attempt.id,
            scope_type=attempt.scope_type,
            scope_ref=attempt.scope_ref,
            scope_name=attempt.scope_name,
            status=attempt.status,
            question_count=attempt.question_count,
            total_points=attempt.total_points,
            score=attempt.score,
            ai_requested=attempt.ai_requested,
            ai_accepted=attempt.ai_accepted,
            ai_note=attempt.ai_note,
            mastery_updates=[
                MasteryUpdateOut(**item) for item in (attempt.mastery_updates or [])
            ],
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            questions=[
                question_out(
                    answer.question,
                    order=answer.question_order,
                    answer=answer,
                    include_result=submitted,
                )
                for answer in answers
            ],
        )
