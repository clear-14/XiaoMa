"""复习申请服务（阶段 6 Agent 工具 ``request_review_task`` 的写操作落点）。

设计要点：
- 写操作只经本 Service → ``ReviewRequestRepository``，Agent 不碰数据库；
- 按「用户 + 知识点 + 日期」幂等，重复申请返回既有记录（created=False），
  同一天不会重复创建；
- 不伪造复习任务：返回的 ``review_tasks`` 全部来自真实错题本
  （ReviewService.list_tasks），没有错题任务时明确说明「暂无待复习错题任务」；
- 不更新掌握状态：掌握度状态只读，复习结果仍由测验/练习写入证据。
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.mastery import MASTERY_STATUS_LABELS
from app.repositories.course_repository import CourseRepository
from app.repositories.mastery_repository import MasteryRepository
from app.repositories.phase6_repository import ReviewRequestRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.phase6 import ReviewRequestIn, ReviewRequestOut
from app.services.mastery_service import MasteryService
from app.services.profile_service import DEFAULT_USERNAME
from app.services.review_service import ReviewService
from app.services.time_utils import utc_today_naive

NO_REAL_TASK_NOTE = (
    "目前没有该知识点的真实错题复习任务；系统不会凭空生成复习任务。"
    "可以先做一次知识点测验，答错的题会自动进入错题本并安排复习。"
)


class ReviewRequestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.profile_repo = ProfileRepository(db)
        self.course_repo = CourseRepository(db)
        self.mastery_repo = MasteryRepository(db)
        self.request_repo = ReviewRequestRepository(db)

    def request(self, payload: ReviewRequestIn) -> ReviewRequestOut:
        user = self._get_or_create_user()
        kp = self.course_repo.get_knowledge_point_by_code(
            payload.knowledge_point_code
        )
        if kp is None:
            raise HTTPException(status_code=404, detail="知识点不存在")

        today = utc_today_naive()
        existing = self.request_repo.get_by_user_kp_date(
            user.id, kp.id, today
        )
        created = existing is None
        if created:
            from app.models.phase6 import ReviewRequest

            request = self.request_repo.add(
                ReviewRequest(
                    user_id=user.id,
                    knowledge_point_id=kp.id,
                    request_date=today,
                    reason=payload.reason or "用户或 Agent 请求复习该知识点",
                    status="pending",
                    source=payload.source,
                    trigger=payload.trigger,
                )
            )
            self.db.commit()
        else:
            request = existing

        tasks = [
            task
            for task in ReviewService(self.db).list_tasks()
            if task.knowledge_point.code == kp.code
        ]
        mastery = self.mastery_repo.get(user.id, kp.id)
        status = mastery.status if mastery is not None else "not_started"
        suggestions = [
            item
            for suggestion in MasteryService(self.db).review_suggestions()
            if suggestion.knowledge_point.knowledge_point_code == kp.code
            for item in suggestion.actions
        ]
        if not suggestions:
            suggestions = [
                "重看本节教材的「常见错误」与「错误分析」",
                "完成该知识点的应用练习",
                "做一次知识点测验，用证据验证掌握情况",
            ]

        return ReviewRequestOut(
            id=request.id,
            knowledge_point_code=kp.code,
            knowledge_point_name=kp.name,
            request_date=request.request_date,
            reason=request.reason,
            status=request.status,
            source=request.source,
            created_at=request.created_at,
            created=created,
            review_tasks=tasks,
            mastery_status=status,
            mastery_status_label=MASTERY_STATUS_LABELS.get(status, status),
            suggestions=suggestions,
            note=(
                "复习申请已记录，未改动任何掌握状态。"
                + ("" if tasks else NO_REAL_TASK_NOTE)
            ),
        )

    def _get_or_create_user(self):
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user
