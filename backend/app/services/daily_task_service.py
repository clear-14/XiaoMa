"""每日学习任务业务层（PRD 4.2 / 5.1，阶段 6「三、今日任务」）。

核心规则（任务书阶段 6 + 产品决策 2026-11-07）：
- 首页先查询当天任务：已有任务直接返回；没有任务才生成；
- 生成逻辑幂等：先查后生成 + 数据库唯一约束兜底，同一天不重复创建相同任务；
- 「滚动追赶」取当前生效计划中最早的、还有未完成项目的计划日，该日全部
  未完成且未掌握的知识点生成当日任务；
- 每条任务固化 course_id / module_id(chapter_id) / lesson_id /
  knowledge_point_id 四个真实标识，由 CoursePublicationService 校验，
  草稿课程或没有归属课时的知识点不会进入任务；
- 任务完成状态与学习证据关联：完成只写「用户自述完成」证据，绝不直接
  标记 mastered；输出同时给出当前 7 态掌握状态与证据条数。
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.daily_task import (
    SOURCE_PLAN,
    SOURCE_SELF_SELECTED,
    DailyTask,
)
from app.models.learning_plan import LearningPlan, LearningPlanVersion
from app.models.user import User
from app.repositories.daily_task_repository import DailyTaskRepository
from app.repositories.learning_profile_repository import LearningProfileRepository
from app.repositories.mastery_repository import MasteryRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.daily_task import DailyTaskOut, TodayTasksOut, TodayTasksSummaryOut
from app.services.course_publication_service import CoursePublicationService
from app.services.daily_task_presenter import build_task_out
from app.services.mastery_service import MasteryService
from app.services.profile_service import DEFAULT_USERNAME
from app.services.time_utils import utc_now_naive, utc_today_naive

ALL_DONE_NOTE = "当前计划的全部知识点已完成或已掌握"
NO_TASKS_YET_NOTE = "当天还没有生成学习任务；首页会在确认无任务后执行一次幂等生成"
NO_PLAN_NOTE = "暂无生效的学习计划；以下是你自己加入的学习任务"
# 跨天承接的窗口：只把最近 7 天内仍处于「学习中」的任务带进今日列表，
# 超出部分折叠为摘要，避免列表无限膨胀。
CARRY_OVER_WINDOW_DAYS = 7


@dataclass(frozen=True)
class _TodayBase:
    """一次今日任务请求的公共校验结果。"""

    user: User
    plan: LearningPlan
    version: LearningPlanVersion
    today: date


class DailyTaskService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_repo = DailyTaskRepository(db)
        self.plan_repo = PlanRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.learning_profile_repo = LearningProfileRepository(db)
        self.mastery_repo = MasteryRepository(db)
        self.publication = CoursePublicationService(db)

    # ------------------------------------------------------------- 今日任务

    def read_today_tasks(self) -> TodayTasksOut:
        """首页第一步：只查询，不生成。"""
        return self.get_today_tasks(generate=False)

    def get_today_tasks(self, *, generate: bool = True) -> TodayTasksOut:
        """首页今日任务：先查当天任务，已有直接返回；没有才按参数决定是否生成。

        ``generate=True`` 保持既有闭环行为（一次请求内完成查 + 幂等生成）；
        首页显式两步走时用 ``generate=False`` 先查，再调用
        ``generate_today_tasks()``。

        阶段 7：「是否需要生成」只看**计划任务**（``source='plan'``），
        用户自选的学习任务不占用计划名额，不会把当天的计划任务挤掉。
        """
        user = self._get_or_create_user()
        today = utc_today_naive()
        plan = self.plan_repo.get_latest_plan(user.id)
        version = self._current_version(plan) if plan is not None else None

        if plan is None or version is None:
            # 无生效计划：仍展示用户自选的内容，但不伪造计划任务；
            # 完全没有自选内容时保持既有「无计划 / 计划未确认」的 404 / 409。
            self_tasks = self.task_repo.get_tasks_by_date(
                user.id, today, source=SOURCE_SELF_SELECTED
            )
            if not self_tasks:
                if plan is None:
                    raise HTTPException(status_code=404, detail="暂无学习计划，请先创建")
                raise HTTPException(
                    status_code=409, detail="学习计划尚未确认，请先确认计划"
                )
            return self._out(today, generated=False, tasks=self_tasks, note=NO_PLAN_NOTE)

        today_tasks = self.task_repo.get_tasks_by_date(user.id, today)
        if self.task_repo.get_plan_tasks_by_date(user.id, today):
            return self._out(today, generated=False, tasks=today_tasks)
        if not generate:
            return self._out(
                today, generated=False, tasks=today_tasks, note=NO_TASKS_YET_NOTE
            )
        return self.generate_today_tasks(
            prepared=_TodayBase(user=user, plan=plan, version=version, today=today)
        )

    def generate_today_tasks(
        self, *, prepared: _TodayBase | None = None
    ) -> TodayTasksOut:
        """首页第二步：仅在当天还没有计划任务时生成；重复调用返回既有任务。

        幂等由三层保证：先查后生成、当天已有知识点剔除、数据库 ``user_date_kp``
        唯一约束；并发的 IntegrityError 回滚后重读已存在任务。
        """
        base = prepared or self._prepare()
        if self.task_repo.get_plan_tasks_by_date(base.user.id, base.today):
            return self._out(
                base.today,
                generated=False,
                tasks=self.task_repo.get_tasks_by_date(base.user.id, base.today),
            )

        tasks = self._build_today_tasks(
            base.user, base.plan, base.version, base.today
        )
        if not tasks:
            return self._out(
                base.today,
                generated=False,
                tasks=self.task_repo.get_tasks_by_date(base.user.id, base.today),
                note=ALL_DONE_NOTE,
            )

        self.task_repo.add_tasks(tasks)
        try:
            self.db.commit()
        except IntegrityError:
            # 并发请求下唯一约束拦截重复生成：回滚后返回已存在的当天任务
            self.db.rollback()
            return self._out(
                base.today,
                generated=False,
                tasks=self.task_repo.get_tasks_by_date(base.user.id, base.today),
            )
        return self._out(
            base.today,
            generated=True,
            tasks=self.task_repo.get_tasks_by_date(base.user.id, base.today),
        )

    def _build_today_tasks(
        self,
        user: User,
        plan: LearningPlan,
        version: LearningPlanVersion,
        today,
    ) -> list[DailyTask]:
        """滚动追赶选取：最早未完成计划日中全部未完成且未掌握的知识点。

        阶段 7：当天已存在任务的知识点（含用户自选）从候选中剔除，
        确保自选与计划自动生成并存、且不会撞 ``user_date_kp`` 唯一约束。
        """
        items = sorted(
            version.items,
            key=lambda item: (item.day_index, item.knowledge_point.code),
        )
        mastered = self.learning_profile_repo.get_mastered_kp_codes(user.id)
        existing_kp_ids = {
            task.knowledge_point_id
            for task in self.task_repo.get_tasks_by_date(user.id, today)
        }
        # 跨天承接的「学习中」任务同样剔除：计划项还是 pending，但这条任务
        # 已在进行中，再下发一次同知识点任务等于让用户从头再来。
        existing_kp_ids |= {
            task.knowledge_point_id
            for task in self.task_repo.get_learning_tasks_since(
                user.id,
                today - timedelta(days=CARRY_OVER_WINDOW_DAYS),
                until=today,
            )
        }
        candidates = [
            item
            for item in items
            if item.status == "pending"
            and item.knowledge_point.code not in mastered
            and item.knowledge_point_id not in existing_kp_ids
        ]
        if not candidates:
            return []
        earliest_day = candidates[0].day_index
        day_items = [item for item in candidates if item.day_index == earliest_day]
        result: list[DailyTask] = []
        for item in day_items:
            # 阶段 6：四个真实课程标识在生成时固化并校验，
            # 草稿课程 / 不存在的课时会在这里被拒绝，不会写入任务。
            refs = self.publication.resolve_task_refs(item.knowledge_point)
            result.append(
                DailyTask(
                    user_id=user.id,
                    plan_id=plan.id,
                    knowledge_point_id=item.knowledge_point_id,
                    course_id=refs.course_id,
                    chapter_id=refs.module_id,
                    lesson_id=refs.lesson_id,
                    task_date=today,
                    day_index=item.day_index,
                    source=SOURCE_PLAN,
                    status="pending",
                )
            )
        return result

    # ------------------------------------------------------------- 任务详情

    def get_task_detail(self, task_id: uuid.UUID) -> DailyTaskOut:
        user = self._get_or_create_user()
        task = self._get_task_or_404(task_id, user)
        return self._task_out(task, self._mastery_map(user.id, [task]))

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
        # 阶段 5：知识点状态统一由掌握度服务推进（LEARNING 不产生掌握证据）
        MasteryService(self.db).start_learning(task.knowledge_point.code)
        self.db.commit()
        return self._task_out(task, self._mastery_map(user.id, [task]))

    # ------------------------------------------------------------- 完成任务

    def complete_task(self, task_id: uuid.UUID) -> DailyTaskOut:
        """标记已完成：记录完成时间；同步计划项目完成与「用户自述」证据。

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
        # 阶段 7：计划外自选任务 plan_id 为空，不触碰任何计划版本。
        plan = (
            self.plan_repo.get_plan(task.plan_id, user.id)
            if task.plan_id is not None
            else None
        )
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

        # 阶段 5/6：任务完成只是「用户自述完成」，绝不写 mastered
        MasteryService(self.db).report_self_completed(
            [task.knowledge_point.code], note="每日任务标记完成（用户自述）"
        )
        self.db.commit()
        return self._task_out(task, self._mastery_map(user.id, [task]))

    # ------------------------------------------------------------- 内部工具

    def _prepare(self) -> _TodayBase:
        user = self._get_or_create_user()
        plan = self.plan_repo.get_latest_plan(user.id)
        if plan is None:
            raise HTTPException(status_code=404, detail="暂无学习计划，请先创建")
        version = self._current_version(plan)
        if version is None:
            raise HTTPException(
                status_code=409, detail="学习计划尚未确认，请先确认计划"
            )
        return _TodayBase(
            user=user, plan=plan, version=version, today=utc_today_naive()
        )

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

    def _mastery_map(
        self, user_id: uuid.UUID, tasks: list[DailyTask]
    ) -> dict[uuid.UUID, tuple[str, int]]:
        return self.mastery_repo.summary_map(
            user_id, [task.knowledge_point_id for task in tasks]
        )

    def _out(
        self,
        task_date: date,
        *,
        generated: bool,
        tasks: list[DailyTask],
        note: str | None = None,
    ) -> TodayTasksOut:
        """装配今日任务输出：平铺 + 按来源分组 + 跨天承接 + 汇总计数。"""
        user = self._get_or_create_user()
        carried = self.task_repo.get_learning_tasks_since(
            user.id,
            task_date - timedelta(days=CARRY_OVER_WINDOW_DAYS),
            until=task_date,
        )
        mastery_map = self._mastery_map(user.id, [*tasks, *carried])
        plan_tasks = [t for t in tasks if t.source == SOURCE_PLAN]
        self_tasks = [t for t in tasks if t.source == SOURCE_SELF_SELECTED]
        carried_out = [
            build_task_out(
                task,
                mastery_map,
                carried_over=True,
                carried_over_days=max((task_date - task.task_date).days, 1),
            )
            for task in carried
        ]
        return TodayTasksOut(
            task_date=task_date,
            generated=generated,
            tasks=self._tasks_out(tasks, mastery_map),
            plan_tasks=self._tasks_out(plan_tasks, mastery_map),
            self_selected_tasks=self._tasks_out(self_tasks, mastery_map),
            carried_over_tasks=carried_out,
            summary=self._summary(plan_tasks, self_tasks, tasks, carried),
            note=note,
        )

    @staticmethod
    def _summary(
        plan_tasks: list[DailyTask],
        self_tasks: list[DailyTask],
        tasks: list[DailyTask],
        carried: list[DailyTask],
    ) -> TodayTasksSummaryOut:
        """今日任务计数。

        只数「学习完成度」这一轴，不把已完成任务当成已掌握——掌握只由证据决定。
        跨天承接的任务不计入 ``plan_total`` / ``self_selected_total``（避免重复计数），
        但计入 ``in_progress`` 与 ``remaining_minutes``。
        """
        unfinished = [t for t in tasks if t.status != "completed"] + carried
        return TodayTasksSummaryOut(
            plan_total=len(plan_tasks),
            plan_completed=sum(1 for t in plan_tasks if t.status == "completed"),
            self_selected_total=len(self_tasks),
            self_selected_completed=sum(
                1 for t in self_tasks if t.status == "completed"
            ),
            in_progress=sum(1 for t in [*tasks, *carried] if t.status == "learning"),
            carried_over=len(carried),
            remaining_minutes=sum(
                t.knowledge_point.estimated_minutes for t in unfinished
            ),
        )

    def _task_out(
        self, task: DailyTask, mastery_map: dict[uuid.UUID, tuple[str, int]]
    ) -> DailyTaskOut:
        """装配单个任务输出（阶段 7 抽到 presenter，与自主选题共用）。"""
        return build_task_out(task, mastery_map)

    def _tasks_out(
        self,
        tasks: list[DailyTask],
        mastery_map: dict[uuid.UUID, tuple[str, int]],
    ) -> list[DailyTaskOut]:
        # 输出顺序与计划顺序一致：day_index → 知识点稳定 code 字典序
        return [
            self._task_out(task, mastery_map)
            for task in sorted(
                tasks, key=lambda t: (t.day_index, t.knowledge_point.code)
            )
        ]
