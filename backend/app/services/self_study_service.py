"""自主选题服务（阶段 7）。

职责边界（``docs/课程扩展阶段7_自主选题与学习完成度.md`` F1）：

- 用户从**已发布课程**的知识点里自选，加入今日学习；粒度固定为知识点；
- 准入完全复用 ``CoursePublicationService.resolve_task_refs()``：草稿课程、
  无归属课时、归属不一致一律拒绝，不自建第二套校验；
- 已 ``mastered`` 的知识点拒绝重复排学习任务，引导去做复习/练习
  （PRD 6.1：掌握只由证据推进，学习任务不再是它的入口）；
- 未掌握的先修**只提示不阻塞**，与阶段 5/6 口径一致；
- 幂等：同一用户同一天同一知识点至多一条任务，由数据库唯一约束
  ``user_date_kp`` 兜底，撞约束时回滚并返回既有任务；
- 计划归属：知识点在当前生效计划版本内 → 记 ``plan_id`` 与计划日，
  完成时由 ``DailyTaskService`` 同步 ``plan_item.completed``（自选即顶替）；
  不在计划内（跨课程自学）→ ``plan_id=None``，不动计划。

本服务不写 SQL，全部经 Repository / Service；不产生计划版本，不改掌握度。
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.daily_task import SOURCE_SELF_SELECTED, DailyTask
from app.models.learning_plan import LearningPlan
from app.models.mastery import MASTERY_STATUS_LABELS
from app.models.user import User
from app.repositories.course_repository import CourseRepository
from app.repositories.daily_task_repository import DailyTaskRepository
from app.repositories.mastery_repository import MasteryRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.study import (
    PrerequisiteWarningOut,
    SelfStudyOut,
    StudyCandidateChapterOut,
    StudyCandidateKpOut,
    StudyCandidatesOut,
)
from app.services.course_publication_service import CoursePublicationService
from app.services.daily_task_presenter import build_task_out
from app.services.mastery_service import MasteryService
from app.services.profile_service import DEFAULT_USERNAME
from app.services.progress_summary_service import build_course_progress
from app.services.time_utils import utc_today_naive

ALREADY_IN_TODAY = "该知识点已在今天的学习任务中，直接开始学习即可"
ALREADY_MASTERED = (
    "该知识点已通过验证（mastered），不需要再排学习任务；"
    "建议到能力诊断页做复习或练习巩固"
)
OUTSIDE_PLAN_NOTE = "该知识点不在当前学习计划内，完成不会改变计划安排"


class SelfStudyService:
    """用户自主选择学习知识点。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_repo = DailyTaskRepository(db)
        self.plan_repo = PlanRepository(db)
        self.course_repo = CourseRepository(db)
        self.mastery_repo = MasteryRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.publication = CoursePublicationService(db)

    # ------------------------------------------------------------ 加入今日学习

    def create_task(self, knowledge_point_code: str) -> SelfStudyOut:
        user = self._get_or_create_user()
        kp = self.course_repo.get_knowledge_point_by_code(knowledge_point_code)
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")

        # 发布校验：草稿课程 / 无正式课时 / 归属不一致在这里被拒绝（复用阶段 6 判定）
        refs = self.publication.resolve_task_refs(kp)

        today = utc_today_naive()
        warnings = self._prerequisite_warnings(user, kp, mastered=set())

        # 幂等：当天已有该知识点的任务（计划或自选）直接返回，不再新建
        existing = self.task_repo.get_task_by_date_kp(user.id, today, kp.id)
        if existing is not None:
            return SelfStudyOut(
                task=build_task_out(existing, self._mastery_map(user, [existing])),
                created=False,
                prerequisite_warnings=warnings,
                note=ALREADY_IN_TODAY,
            )

        mastered_codes = MasteryService(self.db).mastered_kp_codes()
        if kp.code in mastered_codes:
            raise HTTPException(status_code=409, detail=ALREADY_MASTERED)
        # 掌握集合已算出，先修提示按真实掌握状态重建一次（不重复查库）
        warnings = self._prerequisite_warnings(user, kp, mastered=mastered_codes)

        plan, day_index = self._plan_context(user, kp)
        task = DailyTask(
            user_id=user.id,
            plan_id=plan.id if plan is not None else None,
            knowledge_point_id=kp.id,
            course_id=refs.course_id,
            chapter_id=refs.module_id,
            lesson_id=refs.lesson_id,
            task_date=today,
            day_index=day_index,
            source=SOURCE_SELF_SELECTED,
            status="pending",
        )
        self.task_repo.add_tasks([task])
        try:
            self.db.commit()
        except IntegrityError:
            # 并发自选同一知识点：唯一约束拦截，回滚后返回已存在任务
            self.db.rollback()
            existing = self.task_repo.get_task_by_date_kp(user.id, today, kp.id)
            if existing is None:
                raise
            return SelfStudyOut(
                task=build_task_out(existing, self._mastery_map(user, [existing])),
                created=False,
                prerequisite_warnings=warnings,
                note=ALREADY_IN_TODAY,
            )

        stored = self.task_repo.get_task(task.id, user.id)
        if stored is None:  # 理论不可达，防御性处理而非返回半成品
            raise HTTPException(status_code=500, detail="自选任务写入后无法读取")
        return SelfStudyOut(
            task=build_task_out(stored, self._mastery_map(user, [stored])),
            created=True,
            prerequisite_warnings=warnings,
            note=None if plan is not None else OUTSIDE_PLAN_NOTE,
        )

    # ------------------------------------------------------------ 撤回自选任务

    def delete_task(self, task_id: uuid.UUID) -> None:
        """撤回自选任务：只允许撤回「自选且未完成」的任务。

        计划任务归学习计划管理；已完成任务属历史记录，不可篡改。
        """
        user = self._get_or_create_user()
        task = self.task_repo.get_task(task_id, user.id)
        if task is None:
            raise HTTPException(status_code=404, detail="每日任务不存在")
        if task.source != SOURCE_SELF_SELECTED:
            raise HTTPException(
                status_code=409, detail="计划内任务由学习计划管理，不能单独撤回"
            )
        if task.status == "completed":
            raise HTTPException(status_code=409, detail="已完成的任务不能撤回")
        self.task_repo.delete_task(task)
        self.db.commit()

    # ------------------------------------------------------------ 可自选知识点

    def list_candidates(self, course_code: str) -> StudyCandidatesOut:
        """课程学习页数据源：两轴进度 + 章节目录 + 每个知识点的可开始性。

        已掌握的知识点 ``can_start=False``（引导去复习/练习）；课程未发布时
        整门不可开始；缺少归属课时的知识点单独标出原因，不假装可学。
        """
        user = self._get_or_create_user()
        course = self.course_repo.get_course_by_code(course_code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        kps = self.course_repo.get_course_knowledge_points_with_lessons(course_code)
        if not kps:
            raise HTTPException(status_code=422, detail="该课程没有可学习的知识点")

        status_map = self.mastery_repo.status_map(user.id, [kp.id for kp in kps])
        mastered_codes = MasteryService(self.db).mastered_kp_codes()
        today_tasks = {
            task.knowledge_point_id: task
            for task in self.task_repo.get_tasks_by_date(user.id, utc_today_naive())
        }

        notes: list[str] = []
        if course.publish_status != "published":
            notes.append(
                f"课程当前为 {course.publish_status}，尚未正式发布，不能加入学习任务"
            )
        if not status_map:
            notes.append("该课程还没有学习记录：可以先自选一个知识点，或做一次诊断测验")

        progress = build_course_progress(course, kps, status_map)
        kps_by_chapter: dict[str, list] = {}
        for kp in kps:
            kps_by_chapter.setdefault(kp.chapter.code, []).append(kp)

        chapters = [
            StudyCandidateChapterOut(
                code=chapter.chapter_code,
                title=chapter.chapter_title,
                order_index=chapter.order_index,
                kp_total=chapter.kp_total,
                kp_learned=chapter.kp_learned,
                kp_mastered=chapter.kp_mastered,
                learning_percent=chapter.learning_percent,
                mastery_percent=chapter.mastery_percent,
                knowledge_points=[
                    self._candidate_out(
                        kp, status_map, mastered_codes, today_tasks, course
                    )
                    for kp in kps_by_chapter.get(chapter.chapter_code, [])
                ],
            )
            for chapter in progress.chapters
        ]

        return StudyCandidatesOut(
            course_code=course.code,
            course_name=course.name,
            course_publish_status=course.publish_status,
            progress=progress,
            chapters=chapters,
            notes=notes,
        )

    @staticmethod
    def _candidate_out(
        kp,
        status_map: dict[uuid.UUID, str],
        mastered_codes: set[str],
        today_tasks: dict[uuid.UUID, DailyTask],
        course,
    ) -> StudyCandidateKpOut:
        status = status_map.get(kp.id, "not_started")
        task = today_tasks.get(kp.id)
        can_start = True
        block_reason: str | None = None
        if course.publish_status != "published":
            can_start = False
            block_reason = "课程尚未正式发布，不能加入学习任务"
        elif status == "mastered":
            can_start = False
            block_reason = "已通过验证，建议做复习或练习巩固"
        elif kp.lesson is None or kp.lesson.deleted_at is not None:
            can_start = False
            block_reason = "该知识点还没有归属的正式课时"
        return StudyCandidateKpOut(
            code=kp.code,
            name=kp.name,
            difficulty=kp.difficulty,
            estimated_minutes=kp.estimated_minutes,
            chapter_code=kp.chapter.code,
            mastery_status=status,
            mastery_status_label=MASTERY_STATUS_LABELS.get(status, status),
            today_task_status=task.status if task is not None else None,
            today_task_source=task.source if task is not None else None,
            can_start=can_start,
            block_reason=block_reason,
            prerequisite_codes=sorted(p.code for p in kp.prerequisites),
            unmastered_prerequisite_codes=sorted(
                p.code for p in kp.prerequisites if p.code not in mastered_codes
            ),
        )

    # ------------------------------------------------------------ 内部工具

    def _plan_context(
        self, user: User, kp
    ) -> tuple[LearningPlan | None, int]:
        """知识点是否在当前生效计划版本内：在则返回计划与该计划日，否则 (None, 0)。"""
        plan = self.plan_repo.get_latest_plan(user.id)
        if plan is None or plan.current_version_number is None:
            return None, 0
        version = next(
            (
                v
                for v in plan.versions
                if v.version_number == plan.current_version_number
            ),
            None,
        )
        if version is None:
            return None, 0
        item = next(
            (i for i in version.items if i.knowledge_point_id == kp.id), None
        )
        if item is None:
            return None, 0
        return plan, item.day_index

    def _prerequisite_warnings(
        self, user: User, kp, *, mastered: set[str]
    ) -> list[PrerequisiteWarningOut]:
        """未掌握的前置知识点（只提示，不阻塞）。"""
        if not kp.prerequisites:
            return []
        status_map = self.mastery_repo.status_map(
            user.id, [p.id for p in kp.prerequisites]
        )
        warnings: list[PrerequisiteWarningOut] = []
        for prereq in sorted(kp.prerequisites, key=lambda p: p.code):
            if prereq.code in mastered:
                continue
            status = status_map.get(prereq.id, "not_started")
            warnings.append(
                PrerequisiteWarningOut(
                    knowledge_point_code=prereq.code,
                    knowledge_point_name=prereq.name,
                    status=status,
                    status_label=MASTERY_STATUS_LABELS.get(status, status),
                )
            )
        return warnings

    def _mastery_map(
        self, user: User, tasks: list[DailyTask]
    ) -> dict[uuid.UUID, tuple[str, int]]:
        return self.mastery_repo.summary_map(
            user.id, [task.knowledge_point_id for task in tasks]
        )

    def _get_or_create_user(self) -> User:
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user
