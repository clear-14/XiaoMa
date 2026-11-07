"""课程体系接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.course import ChapterOut, CourseDetail, CourseSummary
from app.services.course_service import CourseService

router = APIRouter(tags=["courses"])


@router.get("/courses", response_model=list[CourseSummary])
def list_courses(db: Session = Depends(get_db)) -> list[CourseSummary]:
    """获取课程列表。"""
    return CourseService(db).list_courses()


@router.get("/courses/{course_code}", response_model=CourseDetail)
def get_course(course_code: str, db: Session = Depends(get_db)) -> CourseDetail:
    """获取课程详情（课程信息 + 全部章节与知识点）。"""
    return CourseService(db).get_course_detail(course_code)


@router.get("/courses/{course_code}/chapters", response_model=list[ChapterOut])
def list_chapters(course_code: str, db: Session = Depends(get_db)) -> list[ChapterOut]:
    """获取课程章节列表（含知识点概要）。"""
    return CourseService(db).list_chapters(course_code)
