"""自主选题接口（阶段 7）：课程学习页的可自选知识点目录。

自选任务本身的创建/撤回在 ``/daily-tasks`` 下（任务语义一致，前端共用一套模型）。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.study import StudyCandidatesOut
from app.services.self_study_service import SelfStudyService

router = APIRouter(prefix="/study", tags=["study"])


@router.get("/candidates", response_model=StudyCandidatesOut)
def list_candidates(
    course_code: str = Query(
        ..., min_length=1, max_length=64, description="课程稳定 code，如 python-basics"
    ),
    db: Session = Depends(get_db),
) -> StudyCandidatesOut:
    """可自选知识点目录。

    返回章节两轴进度、每个知识点的掌握状态、是否可开始、被阻止的原因，
    以及未掌握的先修知识点（只提示、不阻止）。
    """
    return SelfStudyService(db).list_candidates(course_code)
