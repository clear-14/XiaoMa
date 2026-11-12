"""每日任务数据访问层。

阶段 7 起任务有 ``source``（plan / self_selected）：今日任务要按来源分组，
「是否需要自动生成」只看计划任务，因此查询方法同时支持按来源过滤。
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Chapter, KnowledgePoint, Lesson
from app.models.daily_task import DailyTask


class DailyTaskRepository:
    """每日任务的数据库读写。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _task_options():
        """任务输出所需关系预取：知识点（含章节/课程、归属课时、前置知识点）
        与阶段 6 固化的课程/章节/课时引用。"""
        return (
            selectinload(DailyTask.knowledge_point).options(
                selectinload(KnowledgePoint.chapter).selectinload(Chapter.course),
                selectinload(KnowledgePoint.lesson).selectinload(Lesson.content),
                selectinload(KnowledgePoint.prerequisites),
            ),
            selectinload(DailyTask.course),
            selectinload(DailyTask.chapter),
            selectinload(DailyTask.lesson),
        )

    def get_tasks_by_date(
        self,
        user_id: uuid.UUID,
        task_date: date,
        *,
        source: str | None = None,
    ) -> list[DailyTask]:
        """用户某天的任务（按 day_index 与创建时间排序）。

        ``source`` 为 None 时返回全部来源（保持既有调用行为）；
        传 ``plan`` / ``self_selected`` 时只返回对应来源。
        """
        stmt = select(DailyTask).where(
            DailyTask.user_id == user_id, DailyTask.task_date == task_date
        )
        if source is not None:
            stmt = stmt.where(DailyTask.source == source)
        stmt = stmt.order_by(
            DailyTask.day_index.asc(), DailyTask.created_at.asc()
        ).options(*self._task_options())
        return list(self.db.scalars(stmt).all())

    def get_plan_tasks_by_date(
        self, user_id: uuid.UUID, task_date: date
    ) -> list[DailyTask]:
        """用户某天的计划任务（source='plan'）。

        「是否需要自动生成今日任务」只看这个集合：用户自选任务不占用计划名额。
        """
        return self.get_tasks_by_date(user_id, task_date, source="plan")

    def get_task_by_date_kp(
        self, user_id: uuid.UUID, task_date: date, knowledge_point_id: uuid.UUID
    ) -> DailyTask | None:
        """按 用户 + 日期 + 知识点 查任务（唯一约束 user_date_kp 对应的查询）。"""
        stmt = (
            select(DailyTask)
            .where(
                DailyTask.user_id == user_id,
                DailyTask.task_date == task_date,
                DailyTask.knowledge_point_id == knowledge_point_id,
            )
            .options(*self._task_options())
        )
        return self.db.scalars(stmt).first()

    def get_learning_tasks_since(
        self, user_id: uuid.UUID, since: date, until: date | None = None
    ) -> list[DailyTask]:
        """跨天承接：``since``（含）之后、``until``（不含）之前仍处于「学习中」的任务。

        只取 ``learning``：未开始的逾期任务由滚动追赶重新下发，不重复展示；
        已完成任务留在历史记录里，不进当日列表。
        """
        stmt = select(DailyTask).where(
            DailyTask.user_id == user_id,
            DailyTask.status == "learning",
            DailyTask.task_date >= since,
        )
        if until is not None:
            stmt = stmt.where(DailyTask.task_date < until)
        stmt = stmt.order_by(
            DailyTask.task_date.asc(), DailyTask.day_index.asc()
        ).options(*self._task_options())
        return list(self.db.scalars(stmt).all())

    def get_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> DailyTask | None:
        """按 ID 与用户查任务。"""
        stmt = (
            select(DailyTask)
            .where(DailyTask.id == task_id, DailyTask.user_id == user_id)
            .options(*self._task_options())
        )
        return self.db.scalars(stmt).first()

    def add_tasks(self, tasks: list[DailyTask]) -> None:
        self.db.add_all(tasks)

    def delete_task(self, task: DailyTask) -> None:
        self.db.delete(task)

    def flush(self) -> None:
        self.db.flush()
