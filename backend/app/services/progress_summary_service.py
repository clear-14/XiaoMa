"""学习进度汇总服务（阶段 7 F3）。

只做**读聚合**，不写任何表、不产生掌握证据。两个轴的口径写死在这里，
前端与 Agent 都只能拿到同一份口径，避免各页面自己算一套「假进度」。

口径（纯函数 ``build_course_progress`` 可直接单测）：

- ``kp_started``：掌握状态不是 ``not_started``（有学习记录）；
- ``kp_learned``：``self_reported_completed`` / ``understood`` / ``applied`` /
  ``mastered`` / ``needs_review``——用户自述学完也算「学过」；
- ``kp_mastered``：只有 ``mastered``，即「有验证证据」；自述永远不进这一列；
- ``minutes_learned``：只累加 ``kp_learned`` 的知识点预计时长（保守口径，
  「学习中」不计入，避免学了一半就显示 90%）；
- ``learning_percent`` = 已学分钟 / 总分钟；``mastery_percent`` = 掌握数 / 总数。
"""

from __future__ import annotations

import uuid
from collections import OrderedDict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import KnowledgePoint
from app.models.user import User
from app.repositories.course_repository import CourseRepository
from app.repositories.mastery_repository import MasteryRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.progress import ChapterProgressOut, CourseProgressOut
from app.services.profile_service import DEFAULT_USERNAME

# 视为「已学完」的掌握状态：自述完成即可算学过，但不算掌握。
LEARNED_STATUSES: frozenset[str] = frozenset(
    {
        "self_reported_completed",
        "understood",
        "applied",
        "mastered",
        "needs_review",
    }
)
MASTERED_STATUS = "mastered"


def _percent(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total * 100, 1)


def build_course_progress(
    course,
    knowledge_points: list[KnowledgePoint],
    status_map: dict[uuid.UUID, str],
    *,
    notes: list[str] | None = None,
) -> CourseProgressOut:
    """按章节聚合进度（纯函数，不访问数据库）。"""
    # 按章节分组，保持传入顺序（仓储已按章节顺序、知识点顺序排好）
    grouped: OrderedDict[uuid.UUID, list[KnowledgePoint]] = OrderedDict()
    for kp in knowledge_points:
        grouped.setdefault(kp.chapter_id, []).append(kp)

    chapters: list[ChapterProgressOut] = []
    for _chapter_id, kps in grouped.items():
        chapter = kps[0].chapter
        started = learned = mastered = 0
        minutes_total = minutes_learned = 0
        for kp in kps:
            status = status_map.get(kp.id, "not_started")
            minutes_total += kp.estimated_minutes
            if status != "not_started":
                started += 1
            if status in LEARNED_STATUSES:
                learned += 1
                minutes_learned += kp.estimated_minutes
            if status == MASTERED_STATUS:
                mastered += 1
        chapters.append(
            ChapterProgressOut(
                chapter_code=chapter.code,
                chapter_title=chapter.title,
                order_index=chapter.order_index,
                kp_total=len(kps),
                kp_started=started,
                kp_learned=learned,
                kp_mastered=mastered,
                minutes_total=minutes_total,
                minutes_learned=minutes_learned,
                learning_percent=_percent(minutes_learned, minutes_total),
                mastery_percent=_percent(mastered, len(kps)),
            )
        )

    total = len(knowledge_points)
    return CourseProgressOut(
        course_code=course.code,
        course_name=course.name,
        course_publish_status=course.publish_status,
        kp_total=total,
        kp_started=sum(c.kp_started for c in chapters),
        kp_learned=sum(c.kp_learned for c in chapters),
        kp_mastered=sum(c.kp_mastered for c in chapters),
        minutes_total=sum(c.minutes_total for c in chapters),
        minutes_learned=sum(c.minutes_learned for c in chapters),
        learning_percent=_percent(
            sum(c.minutes_learned for c in chapters),
            sum(c.minutes_total for c in chapters),
        ),
        mastery_percent=_percent(sum(c.kp_mastered for c in chapters), total),
        chapters=chapters,
        notes=list(notes or []),
    )


class ProgressSummaryService:
    """课程 / 章节进度总览。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.course_repo = CourseRepository(db)
        self.mastery_repo = MasteryRepository(db)
        self.profile_repo = ProfileRepository(db)

    def get_summary(self, course_code: str) -> CourseProgressOut:
        user = self._get_or_create_user()
        course = self.course_repo.get_course_by_code(course_code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        kps = self.course_repo.get_course_knowledge_points_with_lessons(course_code)
        if not kps:
            raise HTTPException(status_code=422, detail="该课程没有可统计的知识点")

        status_map = self.mastery_repo.status_map(user.id, [kp.id for kp in kps])
        notes: list[str] = []
        if course.publish_status != "published":
            notes.append(
                f"课程当前为 {course.publish_status}，尚未正式发布，进度仅供目录预览"
            )
        if not status_map:
            notes.append("该课程还没有学习记录：先学一个知识点或做一次诊断测验")

        return build_course_progress(course, kps, status_map, notes=notes)

    def _get_or_create_user(self) -> User:
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user


__all__ = [
    "LEARNED_STATUSES",
    "ProgressSummaryService",
    "build_course_progress",
]
