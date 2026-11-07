"""错题复习任务接口：列表与提交复习答案（PRD 6.5 / 阶段 9）。"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.quiz import ReviewResultOut, ReviewSubmit, ReviewTaskOut
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/tasks", response_model=list[ReviewTaskOut])
def list_review_tasks(db: Session = Depends(get_db)) -> list[ReviewTaskOut]:
    """待复习任务（按到期时间升序；未到期任务也可以提前复习）。"""
    return ReviewService(db).list_tasks()


@router.post("/tasks/{task_id}/submit", response_model=ReviewResultOut)
def submit_review(
    task_id: uuid.UUID,
    payload: ReviewSubmit,
    db: Session = Depends(get_db),
) -> ReviewResultOut:
    """提交一道错题复习：评分、推进或重置 1/3/7/14 天复习间隔。"""
    return ReviewService(db).submit_review(task_id, payload.answer)
