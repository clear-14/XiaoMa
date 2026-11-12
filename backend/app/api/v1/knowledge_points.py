"""知识点接口（阶段 1：补充所属课时、练习与测验题查询）。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.course import ExerciseOut, KnowledgePointDetail, QuestionOut
from app.services.course_service import CourseService

router = APIRouter(tags=["knowledge-points"])


@router.get("/knowledge-points/{kp_code}", response_model=KnowledgePointDetail)
def get_knowledge_point(kp_code: str, db: Session = Depends(get_db)) -> KnowledgePointDetail:
    """获取知识点详情（学习目标/难度/时长/掌握标准/资源/前置知识点/所属课时）。"""
    return CourseService(db).get_knowledge_point(kp_code)


@router.get(
    "/knowledge-points/{kp_code}/exercises", response_model=list[ExerciseOut]
)
def list_knowledge_point_exercises(
    kp_code: str, db: Session = Depends(get_db)
) -> list[ExerciseOut]:
    """查询知识点练习（含参考答案与解析）。"""
    return CourseService(db).list_exercises(kp_code)


@router.get("/knowledge-points/{kp_code}/questions", response_model=list[QuestionOut])
def list_knowledge_point_questions(
    kp_code: str,
    include_answer: bool = Query(
        default=False,
        description="是否返回正确答案与解析（默认不返回，避免影响正式测验）",
    ),
    db: Session = Depends(get_db),
) -> list[QuestionOut]:
    """查询知识点测验题。"""
    return CourseService(db).list_questions(kp_code, include_answer=include_answer)
