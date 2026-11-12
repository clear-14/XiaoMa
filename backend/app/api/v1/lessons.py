"""课时接口（阶段 1 新增）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.course import LessonDetail
from app.services.course_service import CourseService

router = APIRouter(tags=["lessons"])


@router.get("/lessons/{lesson_code}", response_model=LessonDetail)
def get_lesson(lesson_code: str, db: Session = Depends(get_db)) -> LessonDetail:
    """获取课时详情：所属课程/章节、教学内容与知识点。"""
    return CourseService(db).get_lesson(lesson_code)
