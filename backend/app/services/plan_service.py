"""学习计划业务层：诊断 → 排期 → 草稿 → 用户确认 → 生效；调整走新版本。

规则要点（PRD 4.1 / 5.1 / 9）：
- 创建与调整均先产生「草稿版本」，用户确认后才生效（不确认不改变当前计划）；
- 调整产生新版本，旧版本转为 superseded 保留，历史不覆盖；
- 调整时已完成项目携带到新版本（保留 day_index 与完成时间），未完成项目重新排期，
  已完成任务不因调整丢失；
- 排期与结构校验全部由后端确定性算法完成（AI 辅助分析接入前的基础实现），
  后端校验课程知识点、前置依赖与计划结构；
- 诊断中「已掌握知识点」仅用于排期范围，不写入学习档案掌握状态
  （PRD：未经测验验证不得标记为已掌握）。
"""

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import KnowledgePoint
from app.models.learning_plan import (
    LearningPlan,
    LearningPlanItem,
    LearningPlanVersion,
)
from app.models.user import User
from app.repositories.course_repository import CourseRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.plan import (
    CurrentPlanOut,
    PlanAdjust,
    PlanCreate,
    PlanItemOut,
    PlanOut,
    PlanVersionOut,
    PlanVersionSummary,
)
from app.services.plan_scheduler import build_schedule, computed_duration_days, validate_schedule
from app.services.profile_service import DEFAULT_USERNAME
from app.services.time_utils import utc_today_naive


def _warning(version: LearningPlanVersion) -> str | None:
    """排期超出期望周期时生成提示（产品决策 2026-11-03：创建并标记警告）。"""
    computed = version.computed_duration_days
    if computed > version.expected_duration_days:
        return (
            f"按每日 {version.daily_study_minutes} 分钟排期需要 {computed} 天，"
            f"超出期望周期 {computed - version.expected_duration_days} 天"
        )
    return None


class PlanService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.plan_repo = PlanRepository(db)
        self.course_repo = CourseRepository(db)
        self.profile_repo = ProfileRepository(db)

    # ------------------------------------------------------------------ 创建

    def create_plan(self, payload: PlanCreate) -> CurrentPlanOut:
        user = self._get_or_create_user()
        if self.plan_repo.get_latest_plan(user.id) is not None:
            raise HTTPException(
                status_code=409,
                detail="已存在学习计划，如需修改请使用调整接口",
            )
        kps = self._course_kps(payload.course_code)
        mastered = self._validate_mastered_codes(payload.mastered_kp_codes, kps)

        schedule = build_schedule(kps, mastered, payload.daily_study_minutes)
        self._validate_generated_schedule(schedule, kps, mastered)

        course = self.course_repo.get_course_by_code(payload.course_code)
        plan = LearningPlan(
            user_id=user.id,
            course_id=course.id,
            status="draft",
            current_version_number=None,
            pending_version_number=1,
        )
        version = self._build_version(
            plan,
            1,
            learning_goal=payload.learning_goal,
            daily_study_minutes=payload.daily_study_minutes,
            expected_duration_days=payload.expected_duration_days,
            current_level=payload.current_level,
            schedule=schedule,
            mastered=mastered,
        )
        self.db.add_all([plan, version])
        self.db.commit()
        return self._current_plan_out(plan)

    # ------------------------------------------------------------------ 确认

    def confirm_plan(self, plan_id: uuid.UUID) -> CurrentPlanOut:
        user = self._get_or_create_user()
        plan = self._get_plan_or_404(plan_id, user)
        pending = self._pending_version(plan)
        if pending is None:
            raise HTTPException(status_code=409, detail="没有待确认的版本")

        for version in plan.versions:
            if version.status == "active":
                version.status = "superseded"
        pending.status = "active"
        plan.current_version_number = pending.version_number
        plan.pending_version_number = None
        plan.status = "active"
        # 计划开始日：首次确认时设定，后续调整保持不变
        if plan.start_date is None:
            plan.start_date = utc_today_naive()
        self.db.commit()
        return self._current_plan_out(plan)

    # ------------------------------------------------------------------ 调整

    def adjust_plan(self, plan_id: uuid.UUID, payload: PlanAdjust) -> CurrentPlanOut:
        user = self._get_or_create_user()
        plan = self._get_plan_or_404(plan_id, user)

        # 以当前生效版本为基准；从未确认过则以现有草稿为基准
        base = self._current_version(plan) or self._pending_version(plan)
        if base is None:
            raise HTTPException(status_code=409, detail="计划没有可调整的版本")

        learning_goal = payload.learning_goal or base.learning_goal
        daily_minutes = payload.daily_study_minutes or base.daily_study_minutes
        expected_days = payload.expected_duration_days or base.expected_duration_days
        mastered = set(base.mastered_kp_codes or [])

        # 已完成项目携带（保留 day_index / completed_at），剩余知识点重新排期
        completed_items = [item for item in base.items if item.status == "completed"]
        # 排期排除条件按知识点稳定 code 比较（与 mastered_codes 口径一致）
        completed_codes = {item.knowledge_point.code for item in completed_items}
        kps = self._course_kps(plan.course.code)
        schedule = build_schedule(kps, mastered | completed_codes, daily_minutes)
        # 结构校验的「已知集合」= 已掌握 ∪ 已完成：
        # 已完成知识点虽不重新排期，但满足其后置知识点的前置依赖
        self._validate_generated_schedule(schedule, kps, mastered | completed_codes)

        # 版本号：已有待确认草稿则原地重建（同一编号），否则在最大编号上 +1
        if plan.pending_version_number is not None:
            # delete-orphan：从集合移除即删除旧草稿版本及其项目
            plan.versions.remove(self._pending_version(plan))
            self.plan_repo.flush()
            version_number = plan.pending_version_number
        else:
            version_number = max(v.version_number for v in plan.versions) + 1

        version = self._build_version(
            plan,
            version_number,
            learning_goal=learning_goal,
            daily_study_minutes=daily_minutes,
            expected_duration_days=expected_days,
            current_level=base.current_level,
            schedule=schedule,
            mastered=mastered,
        )
        for item in completed_items:
            version.items.append(
                LearningPlanItem(
                    knowledge_point_id=item.knowledge_point_id,
                    day_index=item.day_index,
                    status="completed",
                    completed_at=item.completed_at,
                )
            )
        plan.pending_version_number = version_number
        self.db.add(version)
        self.db.commit()
        return self._current_plan_out(plan)

    # ------------------------------------------------------------------ 查询

    def get_current_plan(self) -> CurrentPlanOut:
        user = self._get_or_create_user()
        plan = self.plan_repo.get_latest_plan(user.id)
        if plan is None:
            raise HTTPException(status_code=404, detail="暂无学习计划，请先创建")
        return self._current_plan_out(plan)

    def get_plan_detail(self, plan_id: uuid.UUID) -> PlanOut:
        user = self._get_or_create_user()
        plan = self._get_plan_or_404(plan_id, user)
        return self._plan_out(plan)

    def get_plan_version(self, plan_id: uuid.UUID, version_number: int) -> PlanVersionOut:
        user = self._get_or_create_user()
        plan = self._get_plan_or_404(plan_id, user)
        version = next(
            (v for v in plan.versions if v.version_number == version_number), None
        )
        if version is None:
            raise HTTPException(status_code=404, detail="计划版本不存在")
        return self._version_out(version)

    # ------------------------------------------------------------- 内部工具

    def _get_or_create_user(self) -> User:
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user

    def _get_plan_or_404(self, plan_id: uuid.UUID, user: User) -> LearningPlan:
        plan = self.plan_repo.get_plan(plan_id, user.id)
        if plan is None:
            raise HTTPException(status_code=404, detail="学习计划不存在")
        return plan

    def _course_kps(self, course_code: str) -> list[KnowledgePoint]:
        kps = self.course_repo.get_course_knowledge_points(course_code)
        if kps is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        return kps

    def _validate_mastered_codes(
        self, mastered_codes: list[str], kps: list[KnowledgePoint]
    ) -> set[str]:
        codes = {kp.code for kp in kps}
        mastered = set(mastered_codes)
        unknown = sorted(mastered - codes)
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"以下知识点不属于该课程：{', '.join(unknown)}",
            )
        return mastered

    def _validate_generated_schedule(
        self,
        schedule: list[tuple[KnowledgePoint, int]],
        kps: list[KnowledgePoint],
        mastered: set[str],
    ) -> None:
        """后端结构校验（任务书硬性要求）：课程归属、重复安排、前置依赖。"""
        order_position = {kp.code: i for i, kp in enumerate(kps)}
        try:
            validate_schedule(
                schedule, {kp.code: kp for kp in kps}, mastered, order_position
            )
        except ValueError as exc:  # 排期算法自产结构理论不会违反，防御性兜底
            raise HTTPException(status_code=500, detail=f"计划结构校验失败：{exc}") from exc

    def _build_version(
        self,
        plan: LearningPlan,
        version_number: int,
        *,
        learning_goal: str,
        daily_study_minutes: int,
        expected_duration_days: int,
        current_level: str | None,
        schedule: list[tuple[KnowledgePoint, int]],
        mastered: set[str],
    ) -> LearningPlanVersion:
        version = LearningPlanVersion(
            plan=plan,
            version_number=version_number,
            status="draft",
            learning_goal=learning_goal,
            daily_study_minutes=daily_study_minutes,
            expected_duration_days=expected_duration_days,
            computed_duration_days=computed_duration_days(schedule),
            current_level=current_level,
            mastered_kp_codes=sorted(mastered) or None,
        )
        version.items = [
            LearningPlanItem(knowledge_point_id=kp.id, day_index=day, status="pending")
            for kp, day in schedule
        ]
        return version

    def _current_version(self, plan: LearningPlan) -> LearningPlanVersion | None:
        if plan.current_version_number is None:
            return None
        return next(
            (v for v in plan.versions if v.version_number == plan.current_version_number),
            None,
        )

    def _pending_version(self, plan: LearningPlan) -> LearningPlanVersion | None:
        if plan.pending_version_number is None:
            return None
        return next(
            (v for v in plan.versions if v.version_number == plan.pending_version_number),
            None,
        )

    # ------------------------------------------------------------- 组装输出

    @staticmethod
    def _version_out(version: LearningPlanVersion) -> PlanVersionOut:
        # 按（day_index, 知识点 code）排序：稳定 code 字典序与课程顺序一致
        items = sorted(
            version.items,
            key=lambda item: (item.day_index, item.knowledge_point.code),
        )
        return PlanVersionOut(
            version_number=version.version_number,
            status=version.status,
            learning_goal=version.learning_goal,
            daily_study_minutes=version.daily_study_minutes,
            expected_duration_days=version.expected_duration_days,
            computed_duration_days=version.computed_duration_days,
            warning=_warning(version),
            current_level=version.current_level,
            mastered_kp_codes=version.mastered_kp_codes,
            created_at=version.created_at,
            items=[
                PlanItemOut(
                    id=item.id,
                    knowledge_point_code=item.knowledge_point.code,
                    knowledge_point_name=item.knowledge_point.name,
                    estimated_minutes=item.knowledge_point.estimated_minutes,
                    day_index=item.day_index,
                    status=item.status,
                    completed_at=item.completed_at,
                )
                for item in items
            ],
        )

    @staticmethod
    def _version_summary(version: LearningPlanVersion) -> PlanVersionSummary:
        return PlanVersionSummary(
            version_number=version.version_number,
            status=version.status,
            learning_goal=version.learning_goal,
            daily_study_minutes=version.daily_study_minutes,
            expected_duration_days=version.expected_duration_days,
            computed_duration_days=version.computed_duration_days,
            item_count=len(version.items),
            completed_count=sum(1 for item in version.items if item.status == "completed"),
            created_at=version.created_at,
        )

    def _plan_out(self, plan: LearningPlan) -> PlanOut:
        return PlanOut(
            id=plan.id,
            course_code=plan.course.code,
            course_name=plan.course.name,
            status=plan.status,
            start_date=plan.start_date,
            current_version_number=plan.current_version_number,
            pending_version_number=plan.pending_version_number,
            versions=[self._version_summary(v) for v in plan.versions],
            created_at=plan.created_at,
        )

    def _current_plan_out(self, plan: LearningPlan) -> CurrentPlanOut:
        current = self._current_version(plan)
        pending = self._pending_version(plan)
        return CurrentPlanOut(
            **self._plan_out(plan).model_dump(),
            current_version=self._version_out(current) if current is not None else None,
            pending_version=self._version_out(pending) if pending is not None else None,
        )
