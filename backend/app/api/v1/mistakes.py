"""错题本接口（PRD 6.5 / 阶段 9）。"""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.quiz import MistakeOut
from app.services.review_service import ReviewService

router = APIRouter(prefix="/mistakes", tags=["mistakes"])


@router.get("", response_model=list[MistakeOut])
def list_mistakes(
    review_status: Literal["pending", "resolved"] | None = Query(
        default=None, description="按复习状态过滤"
    ),
    db: Session = Depends(get_db),
) -> list[MistakeOut]:
    """错题本：含题目解析、知识点、尝试次数、最近结果与复习状态。"""
    return ReviewService(db).list_mistakes(review_status)
