"""阶段 4D：打通「LangGraph Agent 开发」课程的教材。

写入流程复用通用写入器 ``textbook_writer.write_textbook``；
章节与课时结构由课程目录（``course_catalog_seed``）提供，本文件只负责按课程调用。

与阶段 4A—4C 的区别只有一点：本课程先修链更长（``python-advanced`` + ``llm-api``），
正文里出现的大模型调用一律假定读者已学完 ``llm-api``，因此不重复讲 Key 管理、
HTTP 调用与消息结构，只在需要时引用对应章节。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.seed.langgraph import CHAPTERS, COURSE_CODE, META
from app.seed.textbook_writer import write_textbook

# 内容已通过结构自检（含示例代码实跑输出比对），统一种为 reviewed，
# 等待人工终审后再逐节置为 published
CONTENT_STATUS = "reviewed"


def seed_langgraph_agent(db: Session) -> dict:
    """写入「LangGraph Agent 开发」教材。"""
    return write_textbook(
        db,
        course_code=COURSE_CODE,
        meta=META,
        chapters=CHAPTERS,
        content_status=CONTENT_STATUS,
    )


def seed_phase4d(db: Session) -> dict:
    """写入阶段 4D 的教材，返回统计信息。"""
    stats = seed_langgraph_agent(db)
    return {
        "langgraph-agent": stats,
        "lessons_total": stats["lessons_total"],
        "contents_total": stats["contents_total"],
    }
