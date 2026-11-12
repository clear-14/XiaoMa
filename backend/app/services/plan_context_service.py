"""学习计划生成的八类输入快照（阶段 6「二、学习计划生成」）。

需求要求生成计划时考虑：学习目标、每日学习时间、当前能力等级、已掌握
知识点、未掌握知识点、课程前置关系、课程预计时间、用户测验表现，并让
入学诊断结果影响计划。本服务把八类输入一次性收集成可审计的 JSON 快照，
写入 ``learning_plan_versions.plan_context``：

- 排期仍由确定性算法 ``build_schedule`` 依据**掌握证据**决定（不靠模型）；
- 有 placement（诊断/跳级）证据的知识点进入 ``mastered``，因此会被跳过；
- 仅自述完成的不跳过，仍安排基础教学；
- 未掌握的先修知识点进入 ``remedial_kp_codes``，只提示补学、不自动跳过；
- 需要复习的知识点进入 ``review_kp_codes``，不重复安排基础教学。
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field

from sqlalchemy.orm import Session

from app.models.course import KnowledgePoint
from app.repositories.mastery_repository import MasteryRepository
from app.repositories.quiz_repository import QuizRepository
from app.services.course_catalog_service import CourseCatalogService
from app.services.course_publication_service import PublishedCourseSnapshot
from app.services.mastery_service import MasteryService

# 课程预计时长与实际知识点时长合计偏差超过该比例时给出提示
ESTIMATED_MINUTES_GAP_RATIO = 0.1
RECENT_QUIZ_LIMIT = 5


@dataclass
class PlanContext:
    """一次计划生成的八类输入与由此得出的提示。"""

    learning_goal: str
    daily_study_minutes: int
    current_level: str | None
    mastered_kp_codes: list[str] = field(default_factory=list)
    unmastered_kp_codes: list[str] = field(default_factory=list)
    prerequisite_kp_codes: list[str] = field(default_factory=list)
    remedial_kp_codes: list[str] = field(default_factory=list)
    review_kp_codes: list[str] = field(default_factory=list)
    course_estimated_minutes: int | None = None
    scheduled_minutes: int = 0
    estimated_minutes_note: str | None = None
    recent_quiz_scores: list[float] = field(default_factory=list)
    quiz_average_score: float | None = None
    quiz_attempt_count: int = 0
    placement_evidence_count: int = 0
    diagnosis_note: str = ""
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


class PlanContextService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.mastery_repo = MasteryRepository(db)
        self.quiz_repo = QuizRepository(db)

    def collect(
        self,
        *,
        user_id: uuid.UUID,
        snapshot: PublishedCourseSnapshot,
        kps: list[KnowledgePoint],
        learning_goal: str,
        daily_study_minutes: int,
        current_level: str | None,
        mastered: set[str],
    ) -> PlanContext:
        course = snapshot.course
        course_codes = {kp.code for kp in kps}
        unmastered = [kp.code for kp in kps if kp.code not in mastered]

        prerequisites = sorted(
            {
                prereq.code
                for kp in kps
                for prereq in kp.prerequisites
                if prereq.deleted_at is None
            }
        )
        # 课程前置关系（含先修课程与入学知识点）：只提示补学，绝不自动跳过
        path = CourseCatalogService(self.db).get_learning_path(
            course.code, mastered_knowledge_point_codes=sorted(mastered)
        )
        remedial = [item.code for item in path.missing_knowledge_points]
        missing_courses = [item.code for item in path.missing_courses]

        mastery_service = MasteryService(self.db)
        review_codes = [
            item.knowledge_point.knowledge_point_code
            for item in mastery_service.review_suggestions()
            if item.knowledge_point.knowledge_point_code in course_codes
        ]

        submitted = [
            attempt
            for attempt in self.quiz_repo.list_attempts(user_id, limit=30)
            if attempt.status == "submitted" and attempt.score is not None
        ]
        recent_scores = [float(a.score) for a in submitted[:RECENT_QUIZ_LIMIT]]
        average = (
            round(sum(recent_scores) / len(recent_scores), 1)
            if recent_scores
            else None
        )
        placement_count = self.mastery_repo.count_evidence_by_source(
            user_id, "placement"
        )

        scheduled_minutes = sum(kp.estimated_minutes for kp in kps)
        gap_note = None
        if course.estimated_minutes:
            gap = abs(course.estimated_minutes - scheduled_minutes)
            if gap > course.estimated_minutes * ESTIMATED_MINUTES_GAP_RATIO:
                gap_note = (
                    f"课程登记预计时长 {course.estimated_minutes} 分钟，"
                    f"知识点时长合计 {scheduled_minutes} 分钟，"
                    f"相差 {gap} 分钟；排期按知识点实际时长计算"
                )

        diagnosis_note = (
            f"入学诊断/跳级验证证据 {placement_count} 条；"
            f"有证据的 {len(mastered & course_codes)} 个知识点不安排基础教学，"
            f"仅自述完成的不跳过"
        )
        notes = list(snapshot.notes)
        if missing_courses:
            notes.append(
                "建议先完成前置课程：" + "、".join(missing_courses)
            )
        if remedial:
            notes.append(
                f"有 {len(remedial)} 个未掌握的先修/入学知识点，建议补学"
            )
        if review_codes:
            notes.append(f"有 {len(review_codes)} 个知识点需要复习，已列入复习建议")
        if gap_note:
            notes.append(gap_note)
        if average is not None and average < 60:
            notes.append(
                f"最近 {len(recent_scores)} 次测验平均 {average} 分偏低，"
                "建议先复习再做新知识点的测验"
            )
        if placement_count:
            notes.append("诊断/跳级测验证据已按掌握证据参与跳过判定")
        notes.extend(path.notes[:2])

        return PlanContext(
            learning_goal=learning_goal,
            daily_study_minutes=daily_study_minutes,
            current_level=current_level,
            mastered_kp_codes=sorted(mastered & course_codes),
            unmastered_kp_codes=unmastered,
            prerequisite_kp_codes=prerequisites,
            remedial_kp_codes=remedial,
            review_kp_codes=review_codes,
            course_estimated_minutes=course.estimated_minutes,
            scheduled_minutes=scheduled_minutes,
            estimated_minutes_note=gap_note,
            recent_quiz_scores=recent_scores,
            quiz_average_score=average,
            quiz_attempt_count=len(submitted),
            placement_evidence_count=placement_count,
            diagnosis_note=diagnosis_note,
            notes=notes,
        )
