"""课程体系接口（阶段 1：课程筛选、章节/课时、课程版本与发布状态）。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.course import (
    ChapterOut,
    CourseDetail,
    CourseDifficulty,
    CourseLevel,
    CourseStatusUpdate,
    CourseSummary,
    CourseVersionCreate,
    CourseVersionDetail,
    CourseVersionSummary,
    LessonSummary,
)
from app.services.course_service import CourseService

router = APIRouter(tags=["courses"])


@router.get("/courses", response_model=list[CourseSummary])
def list_courses(
    direction: str | None = Query(default=None, description="按课程方向筛选"),
    difficulty: CourseDifficulty | None = Query(
        default=None, description="按课程难度筛选：beginner/intermediate/advanced"
    ),
    recommended_level: CourseLevel | None = Query(
        default=None, description="按推荐能力等级筛选：L0/L1/L2"
    ),
    publish_status: str = Query(
        default="published",
        description="发布状态筛选：draft 草稿 / published 已发布 / archived 已归档 / all 全部",
    ),
    db: Session = Depends(get_db),
) -> list[CourseSummary]:
    """获取课程列表（默认只返回已发布课程，可按方向/难度/等级/状态筛选）。"""
    return CourseService(db).list_courses(
        direction=direction,
        difficulty=difficulty,
        recommended_level=recommended_level,
        publish_status=publish_status,
    )


@router.get("/courses/{course_code}", response_model=CourseDetail)
def get_course(course_code: str, db: Session = Depends(get_db)) -> CourseDetail:
    """获取课程详情（课程元数据 + 全部章节、课时与知识点）。"""
    return CourseService(db).get_course_detail(course_code)


@router.get("/courses/{course_code}/chapters", response_model=list[ChapterOut])
def list_chapters(course_code: str, db: Session = Depends(get_db)) -> list[ChapterOut]:
    """获取课程章节列表（含知识点概要与课时列表）。"""
    return CourseService(db).list_chapters(course_code)


@router.get(
    "/courses/{course_code}/chapters/{chapter_code}/lessons",
    response_model=list[LessonSummary],
)
def list_lessons(
    course_code: str, chapter_code: str, db: Session = Depends(get_db)
) -> list[LessonSummary]:
    """查询指定章节下的课时列表。"""
    return CourseService(db).list_lessons(course_code, chapter_code)


@router.get(
    "/courses/{course_code}/versions", response_model=list[CourseVersionSummary]
)
def list_course_versions(
    course_code: str, db: Session = Depends(get_db)
) -> list[CourseVersionSummary]:
    """查询课程已保存的版本列表（按保存时间倒序）。"""
    return CourseService(db).list_versions(course_code)


@router.get(
    "/courses/{course_code}/versions/{version}", response_model=CourseVersionDetail
)
def get_course_version(
    course_code: str, version: str, db: Session = Depends(get_db)
) -> CourseVersionDetail:
    """查询某个课程版本的完整结构快照。"""
    return CourseService(db).get_version(course_code, version)


@router.post(
    "/courses/{course_code}/versions",
    response_model=CourseVersionDetail,
    status_code=201,
)
def save_course_version(
    course_code: str,
    payload: CourseVersionCreate,
    db: Session = Depends(get_db),
) -> CourseVersionDetail:
    """保存当前课程结构快照为指定版本（同版本号不覆盖）。"""
    return CourseService(db).save_version(
        course_code, version=payload.version, note=payload.note
    )


@router.patch("/courses/{course_code}/status", response_model=CourseSummary)
def update_course_status(
    course_code: str,
    payload: CourseStatusUpdate,
    db: Session = Depends(get_db),
) -> CourseSummary:
    """切换课程发布状态（草稿 / 已发布 / 已归档）。"""
    return CourseService(db).update_publish_status(
        course_code, payload.publish_status
    )
