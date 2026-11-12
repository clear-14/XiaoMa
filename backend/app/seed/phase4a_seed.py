"""阶段 4A：打通「Python 进阶与工程实践」「数据库与 Python 数据库开发」两门课的教材。

写入流程复用通用写入器 ``textbook_writer.write_textbook``；
章节与课时结构由课程目录（``course_catalog_seed``）提供，本文件只负责按课程调用，
并把两门课的统计汇总成一份结果。

幂等：所有记录按稳定 code upsert，重复执行只更新不新增。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.seed.advanced import CHAPTERS as ADVANCED_CHAPTERS
from app.seed.advanced import COURSE_CODE as ADVANCED_CODE
from app.seed.advanced import META as ADVANCED_META
from app.seed.database import CHAPTERS as DATABASE_CHAPTERS
from app.seed.database import COURSE_CODE as DATABASE_CODE
from app.seed.database import META as DATABASE_META
from app.seed.textbook_writer import write_textbook

# 两门课的内容均已自检，统一种为 reviewed，等待人工终审后再置 published
CONTENT_STATUS = "reviewed"


def seed_python_advanced(db: Session) -> dict:
    """写入「Python 进阶与工程实践」教材。"""
    return write_textbook(
        db,
        course_code=ADVANCED_CODE,
        meta=ADVANCED_META,
        chapters=ADVANCED_CHAPTERS,
        content_status=CONTENT_STATUS,
    )


def seed_python_database(db: Session) -> dict:
    """写入「数据库与 Python 数据库开发」教材。"""
    return write_textbook(
        db,
        course_code=DATABASE_CODE,
        meta=DATABASE_META,
        chapters=DATABASE_CHAPTERS,
        content_status=CONTENT_STATUS,
    )


def seed_phase4a(db: Session) -> dict:
    """依次写入两门课的教材，返回各自的统计信息。

    顺序上先进阶后数据库：后者在课程目录里以进阶为前置，先写前者更像真实的学习顺序。
    """
    advanced = seed_python_advanced(db)
    database = seed_python_database(db)
    return {
        "python-advanced": advanced,
        "python-database": database,
        "lessons_total": advanced["lessons_total"] + database["lessons_total"],
        "contents_total": advanced["contents_total"] + database["contents_total"],
    }
