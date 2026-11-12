"""正式课程与真实课时校验（阶段 6）。

需求「二、学习计划生成」要求：只允许选择正式发布的课程内容，不能把草稿
课程或不存在的课时加入正式学习计划；需求「三、今日任务」要求任务引用
course_id / module_id / lesson_id / knowledge_point_id 四个真实标识。

口径（写死在 Service，测试可直接断言）：
1. 课程必须 ``publish_status == "published"`` 且未软删除；draft / archived
   一律拒绝（409），这是「草稿课程」的硬门槛；
2. 每个知识点必须归属一个真实存在、未软删除的课时，且课时与知识点属于
   同一章节、章节属于目标课程；否则拒绝（422），这是「不存在的课时」硬门槛；
3. 课时若已录入教学内容，内容状态不能是 ``draft``；``reviewed`` /
   ``published`` 视为正式教材；
4. 课时尚未录入内容时不伪造内容：允许排期但在 ``notes`` 中明确标注
   「内容待补充」，不把它当作已发布教材（兼容阶段 3 之前的旧种子数据）。

所有数据经 CourseRepository 读取，Service 不写 SQL、不碰 Session 查询构造。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course, KnowledgePoint, Lesson
from app.repositories.course_repository import CourseRepository

# 允许进入正式计划的课程发布状态
PUBLISHED_STATUS = "published"
# 视为正式教学内容的课时内容状态（draft 明确排除）
FORMAL_CONTENT_STATUSES: tuple[str, ...] = ("reviewed", "published")


@dataclass(frozen=True)
class TaskCourseRefs:
    """一条每日任务必须固化的真实课程层级引用。

    ``module_id`` 对应需求中的 CourseModule，本项目复用既有 ``chapters`` 表。
    """

    course_id: uuid.UUID
    module_id: uuid.UUID
    lesson_id: uuid.UUID
    knowledge_point_id: uuid.UUID
    course_code: str
    module_code: str
    lesson_code: str
    knowledge_point_code: str
    lesson_title: str


@dataclass
class PublishedCourseSnapshot:
    """一次发布校验的结果，供计划生成与诊断展示复用。"""

    course: Course
    knowledge_points: list[KnowledgePoint]
    lesson_by_kp_id: dict[uuid.UUID, Lesson]
    notes: list[str] = field(default_factory=list)
    scheduled_minutes: int = 0
    formal_content_count: int = 0
    missing_content_count: int = 0

    @property
    def course_estimated_minutes(self) -> int | None:
        return self.course.estimated_minutes

    def lesson_for(self, kp: KnowledgePoint) -> Lesson:
        return self.lesson_by_kp_id[kp.id]


class CoursePublicationService:
    """课程是否可进入正式学习计划 / 每日任务的唯一判定入口。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.course_repo = CourseRepository(db)

    def require_published(self, course_code: str) -> PublishedCourseSnapshot:
        course = self.course_repo.get_course_by_code(course_code)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        if course.publish_status != PUBLISHED_STATUS:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"课程「{course.name}」尚未正式发布（{course.publish_status}），"
                    "不能加入正式学习计划"
                ),
            )

        kps = self.course_repo.get_course_knowledge_points_with_lessons(course_code)
        if kps is None or not kps:
            raise HTTPException(
                status_code=422, detail="该课程没有可安排的知识点，不能生成正式学习计划"
            )

        lesson_by_kp: dict[uuid.UUID, Lesson] = {}
        formal = 0
        missing = 0
        for kp in kps:
            lesson = kp.lesson
            self._validate_lesson(course, kp, lesson)
            lesson_by_kp[kp.id] = lesson
            content = lesson.content
            if content is None:
                missing += 1
            elif content.status in FORMAL_CONTENT_STATUSES:
                formal += 1
            else:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"课时「{lesson.title}」（{lesson.code}）的教学内容仍为草稿，"
                        "不能加入正式学习计划"
                    ),
                )

        notes: list[str] = []
        if missing:
            notes.append(
                f"有 {missing} 个课时尚未录入正式教材内容，已保留排期但标记为内容待补充；"
                "系统不会伪造教材内容"
            )
        if course.estimated_minutes is None:
            notes.append("课程未登记预计学习时长，排期按知识点实际时长计算")

        return PublishedCourseSnapshot(
            course=course,
            knowledge_points=kps,
            lesson_by_kp_id=lesson_by_kp,
            notes=notes,
            scheduled_minutes=sum(kp.estimated_minutes for kp in kps),
            formal_content_count=formal,
            missing_content_count=missing,
        )

    def resolve_task_refs(self, kp: KnowledgePoint) -> TaskCourseRefs:
        """为一条任务解析并校验四个真实标识；任何一层缺失都拒绝生成。"""
        lesson = kp.lesson
        self._validate_lesson(kp.chapter.course, kp, lesson)
        course = kp.chapter.course
        if course.publish_status != PUBLISHED_STATUS:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"课程「{course.name}」尚未正式发布，"
                    "不能为草稿课程生成正式学习任务"
                ),
            )
        return TaskCourseRefs(
            course_id=course.id,
            module_id=kp.chapter_id,
            lesson_id=lesson.id,
            knowledge_point_id=kp.id,
            course_code=course.code,
            module_code=kp.chapter.code,
            lesson_code=lesson.code,
            knowledge_point_code=kp.code,
            lesson_title=lesson.title,
        )

    @staticmethod
    def _validate_lesson(
        course: Course, kp: KnowledgePoint, lesson: Lesson | None
    ) -> None:
        if lesson is None or lesson.deleted_at is not None:
            raise HTTPException(
                status_code=422,
                detail=f"知识点「{kp.name}」（{kp.code}）没有归属的正式课时，不能加入正式学习计划",
            )
        if kp.chapter is None or kp.chapter.deleted_at is not None:
            raise HTTPException(
                status_code=422,
                detail=f"知识点「{kp.name}」（{kp.code}）没有归属的正式章节",
            )
        if lesson.chapter_id != kp.chapter_id or kp.chapter.course_id != course.id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"知识点「{kp.name}」的课时归属与章节/课程不一致，"
                    "不能加入正式学习计划"
                ),
            )
