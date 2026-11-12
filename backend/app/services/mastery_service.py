"""知识点掌握度业务层（阶段 5）。

职责边界：
- 只由本服务写 ``knowledge_mastery`` / ``mastery_evidence``；
- 每次写入后把状态投影回 ``learning_profiles``（``MASTERY_TO_LEGACY``），
  计划排期、每日任务、测验范围这些既有链路不需要认识新状态；
- 判定规则全部委托 ``mastery_rules``（纯函数），本层只负责「取数据、落库、组装输出」。

三条硬规则（对应需求三、五）：
1. 用户自述只能到 ``self_reported_completed``，代码里没有「自述 → MASTERED」的分支；
2. 只有 ``mastered`` 允许跳过；自述、基础理解、应用练习都不够；
3. 每次状态变化都写一条证据，历史测验与练习记录不覆盖。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Chapter, KnowledgePoint
from app.models.learning_profile import LearningProfile
from app.models.mastery import (
    EVIDENCE_SOURCE_LABELS,
    LEGACY_TO_MASTERY,
    MASTERY_STATUS_LABELS,
    MASTERY_TO_LEGACY,
    ExerciseAttempt,
    KnowledgeMastery,
    MasteryEvidence,
)
from app.models.quiz import QuizAttempt
from app.models.user import User
from app.repositories.course_repository import CourseRepository
from app.repositories.learning_profile_repository import LearningProfileRepository
from app.repositories.mastery_repository import MasteryRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.mastery import (
    ExerciseAttemptOut,
    ExerciseAttemptRecordOut,
    MasteryCountsOut,
    MasteryCourseOut,
    MasteryDetailOut,
    MasteryEvidenceOut,
    MasteryKnowledgePointOut,
    MasteryOverviewOut,
    ReviewSuggestionOut,
    SelfReportItemOut,
    SelfReportOut,
    SkipCheckItemOut,
    SkipCheckOut,
)
from app.services.mastery_rules import (
    PLACEMENT_MIN_QUESTIONS,
    ExerciseGrade,
    derive_quiz_level,
    grade_exercise_answer,
    is_skip_allowed,
    on_exercise,
    on_quiz,
    on_self_report,
    on_start,
)
from app.services.profile_service import DEFAULT_USERNAME
from app.services.quiz_grading import MASTERY_MIN_QUESTIONS, MASTERY_MIN_SCORE
from app.services.time_utils import utc_now_naive

SELF_REPORT_NOTE = (
    "自述完成只记录为「用户自述完成」，不会标记为「真正掌握」；"
    "要跳过该知识点，仍需通过知识点测验或诊断测验取得掌握证据。"
)

# 需要复习的建议动作（按状态给出，前端不需要自己判断）
REVIEW_ACTIONS: list[str] = [
    "重看本节教材的「常见错误」与「错误分析」",
    "完成该知识点的应用练习（覆盖率 ≥ 60% 才算通过）",
    "做一次知识点测验，3 题全对且 ≥ 90 分才算掌握",
]


class MasteryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MasteryRepository(db)
        self.course_repo = CourseRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.learning_repo = LearningProfileRepository(db)

    # ------------------------------------------------------------ 对外查询

    def get_overview(self) -> MasteryOverviewOut:
        user = self._get_or_create_user()
        self.bootstrap_from_legacy(user.id)
        records = self.repo.list_for_user(user.id)
        counts = self._counts(records)
        total_known = self._course_kp_total()

        courses: dict[str, MasteryCourseOut] = {}
        for record in records:
            course = record.knowledge_point.chapter.course
            group = courses.get(course.code)
            if group is None:
                group = MasteryCourseOut(
                    course_code=course.code,
                    course_name=course.name,
                    counts=MasteryCountsOut(),
                    mastered_percent=0.0,
                )
                courses[course.code] = group
            self._bump(group.counts, record.status)
        for group in courses.values():
            course_total = self._course_kp_total(group.course_code)
            group.mastered_percent = (
                round(group.counts.mastered / course_total * 100, 1)
                if course_total
                else 0.0
            )

        needs_review = [
            self._kp_out(record, now=utc_now_naive())
            for record in records
            if record.status == "needs_review"
        ]
        return MasteryOverviewOut(
            counts=counts,
            mastered_percent=(
                round(counts.mastered / total_known * 100, 1) if total_known else 0.0
            ),
            verified_mastered_count=counts.mastered,
            self_reported_only_count=counts.self_reported_completed,
            courses=sorted(courses.values(), key=lambda item: item.course_code),
            needs_review=needs_review,
        )

    def get_detail(self, kp_code: str) -> MasteryDetailOut:
        user = self._get_or_create_user()
        kp = self._require_kp(kp_code)
        mastery = self._ensure(user, kp)
        self.db.commit()
        now = utc_now_naive()
        return MasteryDetailOut(
            knowledge_point=self._kp_out(mastery, now=now),
            evidence=[self._evidence_out(item) for item in self.repo.list_evidence(user.id, kp.id)],
            exercise_attempts=[
                self._exercise_record_out(item)
                for item in self.repo.list_exercise_attempts(user.id, kp.id)
            ],
        )

    def list_knowledge_points(self, course_code: str | None = None) -> list[MasteryKnowledgePointOut]:
        """按课程（或全部）列出每个知识点的掌握状态，未学习的也返回。"""
        user = self._get_or_create_user()
        self.bootstrap_from_legacy(user.id)
        kps = self._course_kps(course_code) if course_code else self._all_kps()
        now = utc_now_naive()
        out: list[MasteryKnowledgePointOut] = []
        for kp in kps:
            mastery = self._ensure(user, kp)
            out.append(self._kp_out(mastery, now=now))
        self.db.commit()
        return out

    def review_suggestions(self) -> list[ReviewSuggestionOut]:
        """薄弱知识点复习建议：需要复习，或正确率低于 60 的知识点。"""
        user = self._get_or_create_user()
        records = self.repo.list_for_user(user.id)
        now = utc_now_naive()
        suggestions: list[ReviewSuggestionOut] = []
        for record in records:
            reasons: list[str] = []
            if record.status == "needs_review":
                reasons.append("最近一次验证未通过，已标记为需要复习")
            if record.accuracy is not None and record.accuracy < 60:
                reasons.append(f"最近一次验证正确率 {record.accuracy:g}% 偏低")
            if not reasons:
                continue
            kp = record.knowledge_point
            exercises = self.course_repo.list_exercises_by_knowledge_point(kp.id)
            questions = self.course_repo.list_questions_by_knowledge_point(kp.id)
            suggestions.append(
                ReviewSuggestionOut(
                    knowledge_point=self._kp_out(record, now=now),
                    reasons=reasons,
                    actions=list(REVIEW_ACTIONS),
                    exercise_codes=[item.code for item in exercises],
                    question_count=len(questions),
                )
            )
        return suggestions

    # ------------------------------------------------------------ 自述完成

    def report_self_completed(self, kp_codes: list[str], note: str | None = None) -> SelfReportOut:
        user = self._get_or_create_user()
        now = utc_now_naive()
        items: list[SelfReportItemOut] = []
        for code in self._dedupe(kp_codes):
            kp = self._require_kp(code)
            mastery = self._ensure(user, kp)
            before = mastery.status
            target = on_self_report(before)
            mastery.self_reported_at = now
            self._write(
                user,
                kp,
                mastery,
                target,
                source="self_report",
                now=now,
                note=note or "用户自述已完成本节学习",
            )
            items.append(
                SelfReportItemOut(
                    knowledge_point_code=kp.code,
                    knowledge_point_name=kp.name,
                    status_before=before,  # type: ignore[arg-type]
                    status_after=mastery.status,  # type: ignore[arg-type]
                    changed=before != mastery.status,
                    note=(
                        "已记录为自述完成"
                        if before != mastery.status
                        else f"当前状态为{MASTERY_STATUS_LABELS[mastery.status]}，自述不改变已有结论"
                    ),
                )
            )
        self.db.commit()
        return SelfReportOut(items=items, note=SELF_REPORT_NOTE)

    def start_learning(self, kp_code: str) -> MasteryKnowledgePointOut:
        """开始学习：只推进到 LEARNING，不产生掌握证据。

        「开始学」不是任何意义上的掌握证明，因此这里不写 mastery_evidence，
        但仍投影回 learning_profiles，保证旧链路（每日任务、测验范围）一致。
        """
        user = self._get_or_create_user()
        kp = self._require_kp(kp_code)
        mastery = self._ensure(user, kp)
        now = utc_now_naive()
        target = on_start(mastery.status)
        if target != mastery.status:
            mastery.status = target
            self._sync_legacy(user.id, kp.id, mastery, now)
        self.db.commit()
        return self._kp_out(mastery, now=now)

    def grant_mastery(
        self,
        kp_code: str,
        *,
        source: str = "placement",
        accuracy: float | None = 100.0,
        quiz_difficulty: str | None = None,
        note: str | None = None,
    ) -> MasteryKnowledgePointOut:
        """写入一条「已掌握」证据（内部入口，不对接口暴露）。

        正常路径只有测验提交（``record_quiz_attempt``）；
        本方法供数据修复、迁移与自动化测试使用。它要求显式给出来源，
        不会出现在任何「用户自述」链路里。
        """
        if source not in ("quiz", "placement"):
            raise ValueError("掌握证据来源必须是 quiz 或 placement")
        user = self._get_or_create_user()
        kp = self._require_kp(kp_code)
        mastery = self._ensure(user, kp)
        now = utc_now_naive()
        self._write(
            user,
            kp,
            mastery,
            "mastered",
            source=source,
            now=now,
            accuracy=accuracy,
            quiz_difficulty=quiz_difficulty,
            note=note or "写入掌握证据（内部入口）",
        )
        self.db.commit()
        return self._kp_out(mastery, now=now)

    # ------------------------------------------------------------ 应用练习

    def submit_exercise(self, exercise_code: str, answer: str) -> ExerciseAttemptOut:
        user = self._get_or_create_user()
        exercise = self.repo.get_exercise_by_code(exercise_code)
        if exercise is None:
            raise HTTPException(status_code=404, detail="练习不存在")
        try:
            grade: ExerciseGrade = grade_exercise_answer(
                exercise.reference_answer, answer
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        now = utc_now_naive()
        kp = exercise.knowledge_point
        attempt = ExerciseAttempt(
            user_id=user.id,
            exercise_id=exercise.id,
            knowledge_point_id=kp.id,
            answer=answer,
            result=grade.result,
            coverage=grade.coverage,
            grading_basis=grade.basis,
            graded_at=now,
        )
        self.repo.add_exercise_attempt(attempt)
        self.db.flush()

        mastery = self._ensure(user, kp)
        before = mastery.status
        mastery.exercise_attempt_id = attempt.id
        target = on_exercise(before, passed=grade.result == "passed")
        note = (
            f"练习《{exercise.title}》通过，参考答案覆盖率 {grade.coverage:.0%}"
            if grade.result == "passed"
            else f"练习《{exercise.title}》未通过，覆盖率 {grade.coverage:.0%}"
            f"（阈值 {grade.basis['threshold']:.0%}）"
        )
        self._write(
            user,
            kp,
            mastery,
            target,
            source="exercise",
            now=now,
            accuracy=round(grade.coverage * 100, 1),
            quiz_difficulty=exercise.difficulty,
            exercise_attempt=attempt,
            note=note,
        )
        self.db.commit()

        message = {
            "passed": "练习通过，掌握状态已更新为「应用练习通过」",
            "failed": "练习未通过，已标记为需要复习",
        }[grade.result]
        if grade.result == "failed" and target == "mastered":
            message = "练习未通过，但该知识点已有掌握证据，状态保持「真正掌握」，建议复习"
        return ExerciseAttemptOut(
            attempt=self._exercise_record_out(attempt),
            status_before=before,  # type: ignore[arg-type]
            status_after=mastery.status,  # type: ignore[arg-type]
            knowledge_point=self._kp_out(mastery, now=now),
            message=message,
        )

    # ------------------------------------------------------------ 测验联动

    def record_quiz_attempt(self, attempt: QuizAttempt) -> list[dict]:
        """测验提交后更新掌握度，返回可持久化的判定快照。

        - 知识点测验：单点判定，规则同 PRD 6.4（≥3 题、全对、≥90 分）；
        - 诊断（跳级）测验：按知识点分组，抽样验证（≥2 题全对即掌握）；
        - 章节/阶段/复习测验：只记成绩，不改掌握度。
        """
        if attempt.scope_type == "knowledge_point":
            answers = self._answers(attempt)
            if not answers:
                return []
            kp = answers[0][2]
            return [self._apply_quiz(attempt, kp, answers)]

        if attempt.purpose == "placement":
            grouped: dict[uuid.UUID, list[tuple[str | None, bool, KnowledgePoint]]] = {}
            for category, correct, kp in self._answers(attempt):
                grouped.setdefault(kp.id, []).append((category, correct, kp))
            updates = [
                self._apply_quiz(attempt, items[0][2], items, placement=True)
                for items in grouped.values()
            ]
            updates.sort(key=lambda item: item["knowledge_point_code"])
            return updates

        return []

    @staticmethod
    def _answers(
        attempt: QuizAttempt,
    ) -> list[tuple[str | None, bool, KnowledgePoint]]:
        return [
            (
                answer.question.category,
                bool(answer.is_correct),
                answer.question.knowledge_point,
            )
            for answer in sorted(attempt.answers, key=lambda item: item.question_order)
        ]

    def _apply_quiz(
        self,
        attempt: QuizAttempt,
        kp: KnowledgePoint,
        answers: list[tuple[str | None, bool, KnowledgePoint]],
        *,
        placement: bool = False,
    ) -> dict:
        user_id = attempt.user_id
        mastery = self._ensure_by_id(user_id, kp)
        before = mastery.status

        score = (
            self._score_of(attempt, kp) if placement else (attempt.score or 0.0)
        )
        level = derive_quiz_level(
            [(category, correct) for category, correct, _ in answers],
            score=score,
            min_questions=(
                PLACEMENT_MIN_QUESTIONS if placement else MASTERY_MIN_QUESTIONS
            ),
        )
        difficulty = self._highest_difficulty(attempt, kp)
        now = utc_now_naive()
        reasons = self._quiz_reasons(level, answers, score, placement)
        mastery.quiz_attempt_id = attempt.id
        self._write(
            user_id,
            kp,
            mastery,
            on_quiz(before, level=level),
            source="placement" if placement else "quiz",
            now=now,
            accuracy=round(
                sum(1 for _, correct, _ in answers if correct) / len(answers) * 100, 1
            ),
            quiz_difficulty=difficulty,
            quiz_attempt=attempt,
            note="；".join(reasons),
        )
        return {
            "knowledge_point_code": kp.code,
            "knowledge_point_name": kp.name,
            "achieved": level == "mastered",
            "reasons": reasons,
            "status": mastery.status,
            "status_label": MASTERY_STATUS_LABELS[mastery.status],
        }

    @staticmethod
    def _score_of(attempt: QuizAttempt, kp: KnowledgePoint) -> float:
        answers = [
            answer
            for answer in attempt.answers
            if answer.question.knowledge_point_id == kp.id
        ]
        total = sum(answer.max_score for answer in answers) or 1
        gained = sum(answer.score or 0 for answer in answers)
        return round(gained / total * 100, 1)

    @staticmethod
    def _highest_difficulty(attempt: QuizAttempt, kp: KnowledgePoint) -> str | None:
        order = {"beginner": 0, "intermediate": 1, "advanced": 2}
        levels = [
            answer.question.difficulty
            for answer in attempt.answers
            if answer.question.knowledge_point_id == kp.id
        ]
        if not levels:
            return None
        return max(levels, key=lambda item: order.get(item, 0))

    @staticmethod
    def _quiz_reasons(
        level: str,
        answers: list[tuple[str | None, bool, KnowledgePoint]],
        score: float,
        placement: bool,
    ) -> list[str]:
        wrong = sum(1 for _, correct, _ in answers if not correct)
        if level == "mastered":
            prefix = "诊断测验抽样验证" if placement else "满足掌握条件"
            return [
                f"{prefix}：{len(answers)} 道题全部通过，百分制 {score:g} 分"
            ]
        if level == "applied":
            return [
                "应用练习类题目全部通过，但未满足掌握验证"
                f"（需 ≥{MASTERY_MIN_QUESTIONS} 题、全部通过、≥{MASTERY_MIN_SCORE:g} 分）"
            ]
        if level == "understood":
            return [
                "基础理解与代码阅读类题目全部通过，应用练习尚未完成"
            ]
        return [
            f"有 {wrong} 道题未通过（主观题需关键词覆盖率达到 80%），建议先复习再验证"
        ]

    # ------------------------------------------------------------ 跳级检查

    def skip_check(self, course_code: str) -> SkipCheckOut:
        """跳级检查：只有 MASTERED 可跳过，自述与部分掌握需先验证。"""
        user = self._get_or_create_user()
        self.bootstrap_from_legacy(user.id)
        course = self.course_repo.get_course_by_code(course_code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        kps = self._course_kps(course_code)
        skippable: list[SkipCheckItemOut] = []
        needs_verification: list[SkipCheckItemOut] = []
        blocked: list[SkipCheckItemOut] = []
        claimed = 0
        for kp in kps:
            mastery = self._ensure(user, kp)
            status = mastery.status
            if status == "self_reported_completed":
                claimed += 1
            if is_skip_allowed(status):
                skippable.append(
                    self._skip_item(kp, status, "已有掌握证据（测验或诊断测验通过）")
                )
                continue
            if status in ("self_reported_completed", "understood", "applied", "needs_review"):
                needs_verification.append(
                    self._skip_item(
                        kp,
                        status,
                        f"当前为{MASTERY_STATUS_LABELS[status]}，需通过诊断测验或知识点测验验证后才能跳过",
                    )
                )
                continue
            unmet = [
                item
                for item in kp.prerequisites
                if (self._ensure(user, item).status not in ("understood", "applied", "mastered"))
            ]
            reason = "尚未学习"
            if unmet:
                reason = (
                    "先修未达标："
                    + "、".join(item.name for item in unmet[:3])
                    + ("等" if len(unmet) > 3 else "")
                )
            blocked.append(self._skip_item(kp, status, reason))

        notes: list[str] = []
        if claimed and claimed == len(kps):
            notes.append(
                "自述覆盖了本课程全部知识点，系统仍要求先通过诊断测验验证："
                "不允许仅凭自述跳过所有前置要求"
            )
        elif claimed:
            notes.append(f"有 {claimed} 个知识点为用户自述完成，需验证后才能跳过")
        if blocked and any(item.reason.startswith("先修未达标") for item in blocked):
            notes.append("存在先修未达标的知识点，请先补学先修内容")
        self.db.commit()
        return SkipCheckOut(
            course_code=course.code,
            course_name=course.name,
            skippable=skippable,
            needs_verification=needs_verification,
            blocked=blocked,
            notes=notes,
        )

    def mastered_kp_codes(self) -> set[str]:
        """当前用户有掌握证据的知识点 code（排期跳过的唯一依据）。"""
        user = self._get_or_create_user()
        self.bootstrap_from_legacy(user.id)
        return self.repo.mastered_kp_codes(user.id)

    def self_reported_kp_codes(self) -> set[str]:
        user = self._get_or_create_user()
        self.bootstrap_from_legacy(user.id)
        return {
            record.knowledge_point.code
            for record in self.repo.list_for_user(user.id)
            if record.status == "self_reported_completed"
        }

    # ------------------------------------------------------------ 历史数据补建

    def bootstrap_from_legacy(self, user_id: uuid.UUID) -> None:
        """把只有 learning_profiles 的历史状态补建成掌握记录。

        老用户（阶段 9—10 产生的数据）没有 knowledge_mastery，
        不补建会出现「进度说已掌握、掌握度说未开始」的矛盾。
        """
        existing = {
            record.knowledge_point_id for record in self.repo.list_for_user(user_id)
        }
        stmt = select(LearningProfile).where(LearningProfile.user_id == user_id)
        created = False
        for profile in self.db.scalars(stmt).all():
            if profile.knowledge_point_id in existing:
                continue
            mastery = KnowledgeMastery(
                user_id=user_id,
                knowledge_point_id=profile.knowledge_point_id,
                status=LEGACY_TO_MASTERY.get(profile.status, "not_started"),
                verified_at=profile.mastered_at,
                self_reported_at=(
                    profile.started_at
                    if profile.status == "pending_verification"
                    else None
                ),
            )
            self.repo.add(mastery)
            created = True
        if created:
            self.db.flush()

    # ------------------------------------------------------------ 内部工具

    def _ensure(self, user: User, kp: KnowledgePoint) -> KnowledgeMastery:
        return self._ensure_by_id(user.id, kp)

    def _ensure_by_id(
        self, user_id: uuid.UUID, kp: KnowledgePoint
    ) -> KnowledgeMastery:
        mastery = self.repo.get(user_id, kp.id)
        if mastery is not None:
            return mastery
        profile = self.learning_repo.get_profile(user_id, kp.id)
        status = LEGACY_TO_MASTERY.get(profile.status, "not_started") if profile else "not_started"
        mastery = KnowledgeMastery(
            user_id=user_id,
            knowledge_point_id=kp.id,
            status=status,
            verified_at=profile.mastered_at if profile else None,
        )
        self.repo.add(mastery)
        self.db.flush()
        return mastery

    def _write(
        self,
        user_or_id: User | uuid.UUID,
        kp: KnowledgePoint,
        mastery: KnowledgeMastery,
        target: str,
        *,
        source: str,
        now: datetime,
        note: str | None = None,
        accuracy: float | None = None,
        quiz_difficulty: str | None = None,
        exercise_attempt: ExerciseAttempt | None = None,
        quiz_attempt: QuizAttempt | None = None,
    ) -> None:
        """统一写入口：改当前态 + 写一条证据 + 投影回旧状态。

        三个动作必须一起发生，任何一处跳过都会造成「有状态没证据」或
        「掌握度与进度不一致」。
        """
        user_id = user_or_id.id if isinstance(user_or_id, User) else user_or_id
        before = mastery.status
        mastery.status = target
        mastery.evidence_count = (mastery.evidence_count or 0) + 1
        if accuracy is not None:
            mastery.accuracy = accuracy
        if quiz_difficulty is not None:
            mastery.quiz_difficulty = quiz_difficulty
        if exercise_attempt is not None:
            mastery.exercise_attempt_id = exercise_attempt.id
        if quiz_attempt is not None:
            mastery.quiz_attempt_id = quiz_attempt.id

        if target in ("understood", "applied", "mastered"):
            mastery.verified_at = now
            mastery.review_due_at = None
        elif target == "needs_review":
            mastery.review_due_at = now
        elif target == "self_reported_completed":
            mastery.self_reported_at = now

        self.repo.add_evidence(
            MasteryEvidence(
                user_id=user_id,
                knowledge_point_id=kp.id,
                mastery=mastery,
                source=source,
                status_before=before,
                status_after=target,
                exercise_attempt=exercise_attempt,
                quiz_attempt=quiz_attempt,
                accuracy=accuracy,
                quiz_difficulty=quiz_difficulty,
                note=note,
                verified_at=now,
            )
        )
        self._sync_legacy(user_id, kp.id, mastery, now)

    def _sync_legacy(
        self,
        user_id: uuid.UUID,
        kp_id: uuid.UUID,
        mastery: KnowledgeMastery,
        now: datetime,
    ) -> None:
        """把新状态投影回 learning_profiles（旧链路继续可用）。"""
        legacy = MASTERY_TO_LEGACY[mastery.status]
        profile = self.learning_repo.get_profile(user_id, kp_id)
        if profile is None:
            profile = self.learning_repo.create_profile(
                user_id,
                kp_id,
                status=legacy,
                started_at=None if legacy == "not_started" else now,
            )
        else:
            profile.status = legacy
            if profile.started_at is None and legacy != "not_started":
                profile.started_at = now
        if legacy == "mastered":
            profile.mastered_at = mastery.verified_at or now
        elif legacy == "pending_verification" and profile.mastered_at is not None:
            # 从 mastered 降级（正式验证未通过）时清掉掌握时间，
            # 否则「已掌握时间」会与「需要复习」同时存在，矛盾。
            profile.mastered_at = None

    def _require_kp(self, code: str) -> KnowledgePoint:
        kp = self.course_repo.get_knowledge_point_by_code(code)
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")
        return kp

    def _course_kps(self, course_code: str) -> list[KnowledgePoint]:
        kps = self.course_repo.get_course_knowledge_points(course_code)
        if kps is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        return kps

    def _all_kps(self) -> list[KnowledgePoint]:
        stmt = (
            select(KnowledgePoint)
            .join(Chapter, Chapter.id == KnowledgePoint.chapter_id)
            .where(KnowledgePoint.deleted_at.is_(None))
            .order_by(Chapter.order_index, KnowledgePoint.order_index)
        )
        return list(self.db.scalars(stmt).all())

    def _course_kp_total(self, course_code: str | None = None) -> int:
        if course_code is None:
            return len(self._all_kps())
        kps = self.course_repo.get_course_knowledge_points(course_code)
        return len(kps or [])

    def _counts(self, records: list[KnowledgeMastery]) -> MasteryCountsOut:
        counts = MasteryCountsOut()
        for record in records:
            self._bump(counts, record.status)
        return counts

    @staticmethod
    def _bump(counts, status: str) -> None:
        setattr(counts, status, getattr(counts, status) + 1)
        counts.total += 1

    @staticmethod
    def _dedupe(codes: list[str]) -> list[str]:
        seen: list[str] = []
        for code in codes:
            if code not in seen:
                seen.append(code)
        return seen

    def _get_or_create_user(self) -> User:
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user

    # ------------------------------------------------------------ 组装输出

    @staticmethod
    def _next_action(status: str) -> str:
        return {
            "not_started": "开始学习本节教材，先建立概念",
            "learning": "学完后做基础理解检查（知识点测验）",
            "self_reported_completed": "做一次知识点测验验证：自述不等于掌握",
            "understood": "完成应用练习，把理解变成动手能力",
            "applied": "做一次完整知识点测验（≥3 题全对且 ≥90 分）确认掌握",
            "mastered": "已掌握，按 1/3/7/14 天间隔复习即可",
            "needs_review": "先复习错题与应用练习，再重新验证",
        }[status]

    def _kp_out(self, mastery: KnowledgeMastery, *, now: datetime) -> MasteryKnowledgePointOut:
        kp = mastery.knowledge_point
        chapter = kp.chapter
        course = chapter.course
        return MasteryKnowledgePointOut(
            knowledge_point_code=kp.code,
            knowledge_point_name=kp.name,
            chapter_code=chapter.code,
            chapter_title=chapter.title,
            course_code=course.code,
            course_name=course.name,
            difficulty=kp.difficulty,
            status=mastery.status,  # type: ignore[arg-type]
            status_label=MASTERY_STATUS_LABELS[mastery.status],
            accuracy=mastery.accuracy,
            quiz_difficulty=mastery.quiz_difficulty,
            evidence_count=mastery.evidence_count,
            verified_at=mastery.verified_at,
            self_reported_at=mastery.self_reported_at,
            review_due_at=mastery.review_due_at,
            next_action=self._next_action(mastery.status),
        )

    @staticmethod
    def _evidence_out(item: MasteryEvidence) -> MasteryEvidenceOut:
        return MasteryEvidenceOut(
            id=item.id,
            source=item.source,  # type: ignore[arg-type]
            source_label=EVIDENCE_SOURCE_LABELS[item.source],
            status_before=item.status_before,  # type: ignore[arg-type]
            status_after=item.status_after,  # type: ignore[arg-type]
            status_before_label=MASTERY_STATUS_LABELS[item.status_before],
            status_after_label=MASTERY_STATUS_LABELS[item.status_after],
            accuracy=item.accuracy,
            quiz_difficulty=item.quiz_difficulty,
            quiz_attempt_id=item.quiz_attempt_id,
            exercise_attempt_id=item.exercise_attempt_id,
            note=item.note,
            verified_at=item.verified_at,
        )

    @staticmethod
    def _exercise_record_out(item: ExerciseAttempt) -> ExerciseAttemptRecordOut:
        return ExerciseAttemptRecordOut(
            id=item.id,
            exercise_code=item.exercise.code,
            exercise_title=item.exercise.title,
            exercise_type=item.exercise.exercise_type,
            difficulty=item.exercise.difficulty,
            answer=item.answer,
            result=item.result,  # type: ignore[arg-type]
            coverage=item.coverage,
            grading_basis=item.grading_basis,
            graded_at=item.graded_at,
        )

    @staticmethod
    def _skip_item(
        kp: KnowledgePoint, status: str, reason: str
    ) -> SkipCheckItemOut:
        return SkipCheckItemOut(
            knowledge_point_code=kp.code,
            knowledge_point_name=kp.name,
            status=status,  # type: ignore[arg-type]
            status_label=MASTERY_STATUS_LABELS[status],
            reason=reason,
        )
