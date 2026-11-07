"""每日学习任务业务层（PRD 4.2 每日学习流程 / PRD 5.1 每日任务）。

核心规则（任务书阶段 6 + 产品决策 2026-11-07）：
- 首页查询当天任务：已有任务直接返回；没有任务才生成；
- 「滚动追赶」选取规则：取当前生效计划中最早的、还有未完成项目的计划日，
  该日全部未完成且未掌握的知识点生成当日任务。前一天没做完的，新的一天
  重新生成（旧任务保留为历史记录），学习进度不卡住；
- 不得重复安排已掌握知识点（learning_profiles.status == mastered 排除）；
- 不得跳过未满足的前置知识点：计划结构在创建/调整时已由后端校验
  （前置必须在已知集合〔已掌握∪已完成〕或更早的天），生成时只取最早
  未完成计划日的整批项目——更早的计划日全部已完成/已掌握，同天项目按
  课程顺序在同一批中（先做前置再做后置）；
- 同一用户同一天不能重复生成任务：先查后生成 + 数据库唯一约束兜底；
- 任务开始 → 知识点状态 learning；任务完成 → pending_verification
  （PRD 6.1：用户已报告完成，等待掌握验证）。绝不直接标记 mastered；
- 任务完成同时把当前生效计划版本中对应项目标记为已完成（PRD 4.4
  「读取任务完成情况」与阶段 5 已完成携带的数据来源）。
"""

import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.daily_task import DailyTask
from app.models.learning_plan import LearningPlan, LearningPlanVersion
from app.models.user import User
from app.repositories.daily_task_repository import DailyTaskRepository
from app.repositories.learning_profile_repository import LearningProfileRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.daily_task import DailyTaskKpOut, DailyTaskOut, TodayTasksOut
from app.services.profile_service import DEFAULT_USERNAME
from app.services.time_utils import utc_now_naive, utc_today_naive

ALL_DONE_NOTE = "当前计划的全部知识点已完成或已掌握"


class DailyTaskService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_repo = DailyTaskRepository(db)
        self.plan_repo = PlanRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.learning_profile_repo = LearningProfileRepository(db)

    # ------------------------------------------------------------- 今日任务

    def get_today_tasks(self) -> TodayTasksOut:
        """首页今日任务：先查询当天任务，已有直接返回；没有才生成。"""
        user = self._get_or_create_user()
        plan = self.plan_repo.get_latest_plan(user.id)
        if plan is None:
            raise HTTPException(status_code=404, detail="暂无学习计划，请先创建")
        current = self._current_version(plan)
        if current is None:
            raise HTTPException(
                status_code=409, detail="学习计划尚未确认，请先确认计划"
            )

        today = utc_today_naive()
        existing = self.task_repo.get_tasks_by_date(user.id, today)
        if existing:
            return TodayTasksOut(
                task_date=today, generated=False, tasks=self._tasks_out(existing)
            )

        tasks = self._build_today_tasks(user, plan, current, today)
        if not tasks:
            return TodayTasksOut(task_date=today, generated=False, tasks=[], note=ALL_DONE_NOTE)

        self.task_repo.add_tasks(tasks)
        try:
            self.db.commit()
        except IntegrityError:
            # 防重复兜底：并发请求下唯一约束（user/date/知识点）拦截重复生成，
            # 回滚后返回已存在的当天任务
            self.db.rollback()
            existing = self.task_repo.get_tasks_by_date(user.id, today)
            return TodayTasksOut(
                task_date=today, generated=False, tasks=self._tasks_out(existing)
            )
        tasks = self.task_repo.get_tasks_by_date(user.id, today)
        return TodayTasksOut(task_date=today, generated=True, tasks=self._tasks_out(tasks))

    def _build_today_tasks(
        self,
        user: User,
        plan: LearningPlan,
        version: LearningPlanVersion,
        today,
    ) -> list[DailyTask]:
        """滚动追赶选取：最早未完成计划日中全部未完成且未掌握的知识点。"""
        items = sorted(
            version.items,
            key=lambda item: (item.day_index, item.knowledge_point.code),
        )
        mastered = self.learning_profile_repo.get_mastered_kp_codes(user.id)
        candidates = [
            item
            for item in items
            if item.status == "pending" and item.knowledge_point.code not in mastered
        ]
        if not candidates:
            return []
        earliest_day = candidates[0].day_index
        day_items = [item for item in candidates if item.day_index == earliest_day]
        return [
            DailyTask(
                user_id=user.id,
                plan_id=plan.id,
                knowledge_point_id=item.knowledge_point_id,
                task_date=today,
                day_index=item.day_index,
                status="pending",
            )
            for item in day_items
        ]

    # ------------------------------------------------------------- 任务详情

    def get_task_detail(self, task_id: uuid.UUID) -> DailyTaskOut:
        user = self._get_or_create_user()
        return self._task_out(self._get_task_or_404(task_id, user))

    # ------------------------------------------------------------- 开始学习

    def start_task(self, task_id: uuid.UUID) -> DailyTaskOut:
        """标记开始学习：pending → learning，记录开始时间；学习档案同步 learning。"""
        user = self._get_or_create_user()
        task = self._get_task_or_404(task_id, user)
        if task.status == "completed":
            raise HTTPException(status_code=409, detail="任务已完成，无法开始学习")
        now = utc_now_naive()
        if task.status == "pending":
            task.status = "learning"
            # 幂等：重复标记开始不覆盖首次开始时间
            if task.started_at is None:
                task.started_at = now
        self._profile_on_start(user.id, task.knowledge_point_id, now)
        self.db.commit()
        return self._task_out(task)

    def _profile_on_start(self, user_id: uuid.UUID, kp_id: uuid.UUID, now: datetime) -> None:
        """开始学习 → 知识点状态 learning（PRD 6.1）；已进入后续状态的不降级。"""
        profile = self.learning_profile_repo.get_profile(user_id, kp_id)
        if profile is None:
            self.learning_profile_repo.create_profile(
                user_id, kp_id, status="learning", started_at=now
            )
        elif profile.status == "not_started":
            profile.status = "learning"
            if profile.started_at is None:
                profile.started_at = now

    # ------------------------------------------------------------- 完成任务

    def complete_task(self, task_id: uuid.UUID) -> DailyTaskOut:
        """标记已完成：记录完成时间；同步计划项目完成与知识点待验证状态。

        任务完成只代表任务完成，不代表知识点掌握（PRD：未经测验验证
        不得标记为 mastered）。
        """
        user = self._get_or_create_user()
        task = self._get_task_or_404(task_id, user)
        if task.status == "completed":
            raise HTTPException(status_code=409, detail="任务已完成")
        now = utc_now_naive()
        task.status = "completed"
        task.completed_at = now

        # 同步当前生效计划版本的对应项目（阶段 5 已完成携带的数据来源）。
        # 计划调整后旧任务完成时，标记新生效版本中的对应项目（如仍在计划中）。
        plan = self.plan_repo.get_plan(task.plan_id, user.id)
        current = self._current_version(plan) if plan is not None else None
        if current is not None:
            item = next(
                (
                    item
                    for item in current.items
                    if item.knowledge_point_id == task.knowledge_point_id
                    and item.status == "pending"
                ),
                None,
            )
            if item is not None:
                item.status = "completed"
                item.completed_at = now

        self._profile_on_complete(user.id, task.knowledge_point_id)
        self.db.commit()
        return self._task_out(task)

    def _profile_on_complete(self, user_id: uuid.UUID, kp_id: uuid.UUID) -> None:
        """任务完成 → 知识点状态 pending_verification（等待测验验证）。

        已 mastered / review_due 的知识点不降级；pending_verification 保持。
        """
        profile = self.learning_profile_repo.get_profile(user_id, kp_id)
        if profile is None:
            self.learning_profile_repo.create_profile(
                user_id, kp_id, status="pending_verification"
            )
        elif profile.status in ("not_started", "learning"):
            profile.status = "pending_verification"

    # ------------------------------------------------------------- 内部工具

    def _get_or_create_user(self) -> User:
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user

    def _get_task_or_404(self, task_id: uuid.UUID, user: User) -> DailyTask:
        task = self.task_repo.get_task(task_id, user.id)
        if task is None:
            raise HTTPException(status_code=404, detail="每日任务不存在")
        return task

    @staticmethod
    def _current_version(plan: LearningPlan) -> LearningPlanVersion | None:
        if plan.current_version_number is None:
            return None
        return next(
            (v for v in plan.versions if v.version_number == plan.current_version_number),
            None,
        )

    @staticmethod
    def _task_out(task: DailyTask) -> DailyTaskOut:
        kp = task.knowledge_point
        return DailyTaskOut(
            id=task.id,
            plan_id=task.plan_id,
            task_date=task.task_date,
            day_index=task.day_index,
            status=task.status,
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
        )

    @classmethod
    def _tasks_out(cls, tasks: list[DailyTask]) -> list[DailyTaskOut]:
        # 输出顺序与计划顺序一致：day_index → 知识点稳定 code 字典序
        return [
            cls._task_out(task)
            for task in sorted(tasks, key=lambda t: (t.day_index, t.knowledge_point.code))
        ]
