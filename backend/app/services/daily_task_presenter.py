"""每日任务输出装配（阶段 7 抽出，供计划任务与自主选题共用）。

抽出的理由：自选任务与计划任务返回的是同一种 ``DailyTaskOut``，
两处各写一份必然漂移（阶段 6 的 ``completion_note`` 文案就吃过这个亏）。
本模块只做「实体 → Schema」的纯装配，不含任何业务规则与数据库访问。
"""

from __future__ import annotations

import uuid

from app.models.daily_task import DAILY_TASK_STATUS_LABELS, DailyTask
from app.models.mastery import MASTERY_STATUS_LABELS
from app.schemas.daily_task import (
    DailyTaskCourseRefsOut,
    DailyTaskKpOut,
    DailyTaskOut,
)


def build_course_refs(task: DailyTask) -> DailyTaskCourseRefsOut | None:
    """优先用任务表固化的引用；历史任务缺列时从知识点归属派生。"""
    kp = task.knowledge_point
    chapter = task.chapter or kp.chapter
    course = chapter.course if chapter is not None else None
    lesson = task.lesson or kp.lesson
    if lesson is None or chapter is None or course is None:
        return None
    return DailyTaskCourseRefsOut(
        course_id=task.course_id or course.id,
        module_id=task.chapter_id or chapter.id,
        lesson_id=task.lesson_id or lesson.id,
        knowledge_point_id=kp.id,
        course_code=course.code,
        module_code=chapter.code,
        lesson_code=lesson.code,
        knowledge_point_code=kp.code,
        lesson_title=lesson.title,
    )


def build_task_out(
    task: DailyTask,
    mastery_map: dict[uuid.UUID, tuple[str, int]],
    *,
    carried_over: bool = False,
    carried_over_days: int = 0,
) -> DailyTaskOut:
    """装配单个任务输出。

    ``mastery_map`` 为 ``{kp_id: (掌握状态, 证据条数)}``，由调用方批量查询后传入，
    避免逐条任务查库（N+1）。
    """
    kp = task.knowledge_point
    mastery_status, evidence_count = mastery_map.get(kp.id, ("not_started", 0))
    mastery_label = MASTERY_STATUS_LABELS.get(mastery_status, mastery_status)
    return DailyTaskOut(
        id=task.id,
        plan_id=task.plan_id,
        task_date=task.task_date,
        day_index=task.day_index,
        source=task.source,
        status=task.status,
        progress_label=DAILY_TASK_STATUS_LABELS.get(task.status, task.status),
        carried_over=carried_over,
        carried_over_days=carried_over_days,
        started_at=task.started_at,
        completed_at=task.completed_at,
        knowledge_point=DailyTaskKpOut(
            code=kp.code,
            name=kp.name,
            learning_goal=kp.learning_goal,
            difficulty=kp.difficulty,
            estimated_minutes=kp.estimated_minutes,
            mastery_criteria=kp.mastery_criteria,
            chapter_code=kp.chapter.code,
            chapter_title=kp.chapter.title,
            resources=kp.resources,
            prerequisite_codes=sorted(p.code for p in kp.prerequisites),
        ),
        course_refs=build_course_refs(task),
        mastery_status=mastery_status,
        mastery_evidence_count=evidence_count,
        completion_note=(
            "任务完成只写「用户自述完成」证据，不代表掌握；"
            f"当前掌握状态：{mastery_label}，掌握证据 {evidence_count} 条"
            "（由测验 / 练习 / 诊断验证写入）"
        ),
    )
