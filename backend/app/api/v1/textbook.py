"""教材接口（阶段 3）：课时教材、课程教材大纲、内容状态与验收报告。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.textbook import (
    ContentStatusOut,
    ContentStatusUpdate,
    LessonTextbookOut,
    TextbookAuditOut,
    TextbookOutlineOut,
)
from app.services.textbook_service import TextbookService

router = APIRouter(tags=["textbook"])


@router.get(
    "/courses/{course_code}/textbook", response_model=TextbookOutlineOut
)
def get_course_textbook(
    course_code: str,
    status: str | None = Query(
        default=None,
        description="按内容状态筛选：draft / reviewed / published，不传返回全部",
    ),
    db: Session = Depends(get_db),
) -> TextbookOutlineOut:
    """课程教材大纲（章节 → 课时 → 内容状态）。"""
    return TextbookService(db).get_course_textbook(course_code, status=status)


@router.get(
    "/courses/{course_code}/textbook/audit", response_model=TextbookAuditOut
)
def audit_course_textbook(
    course_code: str, db: Session = Depends(get_db)
) -> TextbookAuditOut:
    """课程教材内容验收（10 项确定性检查）。"""
    return TextbookService(db).audit_course(course_code)


@router.get(
    "/lessons/{lesson_code}/textbook", response_model=LessonTextbookOut
)
def get_lesson_textbook(
    lesson_code: str,
    include_draft: bool = Query(
        default=False, description="是否返回尚未通过检查的草稿内容"
    ),
    db: Session = Depends(get_db),
) -> LessonTextbookOut:
    """课时完整教材：15 个内容模块 + 知识点 + 练习 + 本节测验。"""
    return TextbookService(db).get_lesson_textbook(
        lesson_code, include_draft=include_draft
    )


@router.patch(
    "/lessons/{lesson_code}/content-status", response_model=ContentStatusOut
)
def update_content_status(
    lesson_code: str,
    payload: ContentStatusUpdate,
    db: Session = Depends(get_db),
) -> ContentStatusOut:
    """切换教学内容状态（draft → reviewed → published）。"""
    return TextbookService(db).set_content_status(lesson_code, payload.status)
