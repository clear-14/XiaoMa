"""每日任务数据访问层。"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import KnowledgePoint
from app.models.daily_task import DailyTask


class DailyTaskRepository:
    """每日任务的数据库读写。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _task_options():
        """任务输出所需关系预取：知识点（含章节与前置知识点）。"""
        return selectinload(DailyTask.knowledge_point).options(
            selectinload(KnowledgePoint.chapter),
            selectinload(KnowledgePoint.prerequisites),
        )

    def get_tasks_by_date(self, user_id: uuid.UUID, task_date: date) -> list[DailyTask]:
        """用户某天的全部任务（按 day_index 与创建时间排序）。"""
        stmt = (
            select(DailyTask)
            .where(DailyTask.user_id == user_id, DailyTask.task_date == task_date)
            .order_by(DailyTask.day_index.asc(), DailyTask.created_at.asc())
            .options(self._task_options())
        )
        return list(self.db.scalars(stmt).all())

    def get_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> DailyTask | None:
        """按 ID 与用户查任务。"""
        stmt = (
            select(DailyTask)
            .where(DailyTask.id == task_id, DailyTask.user_id == user_id)
            .options(self._task_options())
        )
        return self.db.scalars(stmt).first()

    def add_tasks(self, tasks: list[DailyTask]) -> None:
        self.db.add_all(tasks)

    def flush(self) -> None:
        self.db.flush()
