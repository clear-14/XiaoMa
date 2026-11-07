"""测验接口：可测验范围、组卷、答题详情与提交评分（阶段 9）。"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.quiz import (
    QuizAttemptOut,
    QuizAttemptSummaryOut,
    QuizCreate,
    QuizEligibilityOut,
    QuizSubmit,
)
from app.services.quiz_service import QuizService

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.get("/eligibility", response_model=QuizEligibilityOut)
def get_quiz_eligibility(db: Session = Depends(get_db)) -> QuizEligibilityOut:
    """可测验范围：只包含已学习知识点、章节与当前学习阶段。

    未学习知识点不会进入正式测验（PRD 6.3）。
    """
    return QuizService(db).get_eligibility()


@router.get("", response_model=list[QuizAttemptSummaryOut])
def list_quizzes(db: Session = Depends(get_db)) -> list[QuizAttemptSummaryOut]:
    """测验历史（不含错题复习记录）。"""
    return QuizService(db).list_attempts()


@router.post("", response_model=QuizAttemptOut, status_code=201)
async def create_quiz(
    payload: QuizCreate, db: Session = Depends(get_db)
) -> QuizAttemptOut:
    """按知识点/章节/学习阶段组卷；可请求 AI 变式题（生成失败自动降级）。

    未提交前不返回正确答案与解析。
    """
    return await QuizService(db).create_quiz(payload)


@router.get("/{attempt_id}", response_model=QuizAttemptOut)
def get_quiz(
    attempt_id: uuid.UUID, db: Session = Depends(get_db)
) -> QuizAttemptOut:
    """查看测验详情；已提交的测验包含答案、解析与评分依据。"""
    return QuizService(db).get_attempt(attempt_id)


@router.post("/{attempt_id}/submit", response_model=QuizAttemptOut)
def submit_quiz(
    attempt_id: uuid.UUID,
    payload: QuizSubmit,
    db: Session = Depends(get_db),
) -> QuizAttemptOut:
    """提交整份测验：后端评分、保存答题记录、记录错题并判定掌握状态。"""
    return QuizService(db).submit_attempt(attempt_id, payload)
