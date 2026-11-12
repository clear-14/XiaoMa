"""知识点掌握度接口（阶段 5）。

路径分组：
- ``/mastery``：总览（7 态计数、按课程聚合、需要复习清单）；
- ``/mastery/knowledge-points``：逐知识点掌握状态与证据；
- ``/mastery/self-report``：用户自述完成（只写自述，不写掌握）；
- ``/mastery/exercises/{code}/attempt``：提交应用练习（文本比对，不执行代码）；
- ``/mastery/review-suggestions``：薄弱知识点的复习建议；
- ``/mastery/skip-check``：跳级检查（只有掌握证据允许跳过）。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.mastery import (
    ExerciseAttemptIn,
    ExerciseAttemptOut,
    MasteryDetailOut,
    MasteryKnowledgePointOut,
    MasteryOverviewOut,
    ReviewSuggestionOut,
    SelfReportIn,
    SelfReportOut,
    SkipCheckOut,
)
from app.services.mastery_service import MasteryService

router = APIRouter(prefix="/mastery", tags=["mastery"])


@router.get("", response_model=MasteryOverviewOut)
def get_mastery_overview(db: Session = Depends(get_db)) -> MasteryOverviewOut:
    """掌握度总览：7 态计数、按课程分布、需要复习清单。"""
    return MasteryService(db).get_overview()


@router.get("/knowledge-points", response_model=list[MasteryKnowledgePointOut])
def list_mastery_knowledge_points(
    course_code: str | None = Query(default=None, description="按课程 code 过滤"),
    db: Session = Depends(get_db),
) -> list[MasteryKnowledgePointOut]:
    """逐知识点的掌握状态（未学习的也会返回，方便前端画出完整进度）。"""
    return MasteryService(db).list_knowledge_points(course_code)


@router.get(
    "/knowledge-points/{kp_code}", response_model=MasteryDetailOut
)
def get_mastery_detail(
    kp_code: str, db: Session = Depends(get_db)
) -> MasteryDetailOut:
    """单个知识点的掌握详情：当前态 + 证据流水（测验/练习/自述）。"""
    return MasteryService(db).get_detail(kp_code)


@router.post("/self-report", response_model=SelfReportOut)
def report_self_completed(
    payload: SelfReportIn, db: Session = Depends(get_db)
) -> SelfReportOut:
    """用户自述完成。

    只会写 ``self_reported_completed``；要跳过该知识点仍需测验验证。
    """
    return MasteryService(db).report_self_completed(
        payload.knowledge_point_codes, payload.note
    )


@router.post(
    "/exercises/{exercise_code}/attempt", response_model=ExerciseAttemptOut
)
def submit_exercise(
    exercise_code: str,
    payload: ExerciseAttemptIn,
    db: Session = Depends(get_db),
) -> ExerciseAttemptOut:
    """提交应用练习：按参考答案二元组覆盖率判定，通过后进入「应用练习通过」。"""
    return MasteryService(db).submit_exercise(exercise_code, payload.answer)


@router.get("/review-suggestions", response_model=list[ReviewSuggestionOut])
def list_review_suggestions(
    db: Session = Depends(get_db),
) -> list[ReviewSuggestionOut]:
    """需要复习的知识点及建议动作（含可练的练习与可测的题量）。"""
    return MasteryService(db).review_suggestions()


@router.get("/skip-check", response_model=SkipCheckOut)
def check_skip(
    course_code: str = Query(description="课程 code"),
    db: Session = Depends(get_db),
) -> SkipCheckOut:
    """跳级检查：可跳过 / 需验证 / 被先修阻塞。

    只有 ``mastered``（测验或诊断测验通过）进入「可跳过」；
    自述与基础理解、应用练习都只能进入「需验证」。
    """
    return MasteryService(db).skip_check(course_code)
