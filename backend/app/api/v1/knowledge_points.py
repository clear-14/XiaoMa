"""知识点接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.course import KnowledgePointDetail
from app.services.course_service import CourseService

router = APIRouter(tags=["knowledge-points"])


@router.get("/knowledge-points/{kp_code}", response_model=KnowledgePointDetail)
def get_knowledge_point(kp_code: str, db: Session = Depends(get_db)) -> KnowledgePointDetail:
    """获取知识点详情（学习目标/难度/预计时长/掌握标准/资源/前置知识点）。"""
    return CourseService(db).get_knowledge_point(kp_code)
