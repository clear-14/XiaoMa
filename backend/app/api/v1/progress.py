"""学习进度接口（阶段 7）：课程 / 章节两轴进度总览。

两个轴分开返回，不提供任何「合成总进度」字段——避免用户把
「学完」误读成「掌握」（PRD 6.1）。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.progress import CourseProgressOut
from app.services.progress_summary_service import ProgressSummaryService

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/summary", response_model=CourseProgressOut)
def get_progress_summary(
    course_code: str = Query(
        ..., min_length=1, max_length=64, description="课程稳定 code，如 python-basics"
    ),
    db: Session = Depends(get_db),
) -> CourseProgressOut:
    """课程进度汇总：``learning_percent``（学习完成度）与
    ``mastery_percent``（已验证掌握度）分开返回，含章节明细。
    """
    return ProgressSummaryService(db).get_summary(course_code)
