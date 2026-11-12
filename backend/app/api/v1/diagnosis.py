"""学习诊断接口（阶段 5）。

``/diagnosis`` 输出 6 个维度的能力画像与个性化学习路线；
``/diagnosis/placement`` 生成诊断（跳级）测验，是唯一允许对未学知识点出题的入口。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.diagnosis import (
    DiagnosisDimensionOut,
    DiagnosisIn,
    DiagnosisOut,
    PlacementIn,
    PlacementPlanOut,
)
from app.schemas.quiz import QuizAttemptOut
from app.services.diagnosis_service import DiagnosisService
from app.services.quiz_service import QuizService

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])


@router.get("/dimensions", response_model=list[DiagnosisDimensionOut])
def list_dimensions(
    db: Session = Depends(get_db),
) -> list[DiagnosisDimensionOut]:
    """6 个诊断维度及其锚点知识点的当前状态。"""
    return DiagnosisService(db).list_dimensions()


@router.post("", response_model=DiagnosisOut)
def run_diagnosis(
    payload: DiagnosisIn, db: Session = Depends(get_db)
) -> DiagnosisOut:
    """执行诊断：维度画像 + 个性化学习路线。

    请求里的自述只记为「待验证」，不会让知识点变成已掌握。
    """
    return DiagnosisService(db).diagnose(payload)


@router.post("/placement/plan", response_model=PlacementPlanOut)
def plan_placement(
    payload: PlacementIn, db: Session = Depends(get_db)
) -> PlacementPlanOut:
    """诊断测验预检：能验证哪些知识点、各能出几道题。"""
    return DiagnosisService(db).placement_plan(payload)


@router.post("/placement", response_model=QuizAttemptOut, status_code=201)
def create_placement(
    payload: PlacementIn, db: Session = Depends(get_db)
) -> QuizAttemptOut:
    """生成诊断（跳级）测验：允许未学知识点，通过后写入掌握证据。"""
    service = DiagnosisService(db)
    attempt = service.create_placement_quiz(payload)
    return QuizService(db).present_attempt(attempt)
