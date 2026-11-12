"""阶段 4E：打通「软件工程与项目部署」课程的教材。

写入流程复用通用写入器 ``textbook_writer.write_textbook``；
章节与课时结构由课程目录（``course_catalog_seed``）提供，本文件只负责按课程调用。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.seed.deploy import CHAPTERS, COURSE_CODE, META
from app.seed.textbook_writer import write_textbook

# 内容已通过结构自检，统一种为 reviewed，等待人工终审后再逐节置为 published
CONTENT_STATUS = "reviewed"


def seed_software_deploy(db: Session) -> dict:
    """写入「软件工程与项目部署」教材。"""
    return write_textbook(
        db,
        course_code=COURSE_CODE,
        meta=META,
        chapters=CHAPTERS,
        content_status=CONTENT_STATUS,
    )


def seed_phase4e(db: Session) -> dict:
    """写入阶段 4E 的教材，返回统计信息。"""
    stats = seed_software_deploy(db)
    return {
        COURSE_CODE: stats,
        "lessons_total": stats["lessons_total"],
        "contents_total": stats["contents_total"],
    }
