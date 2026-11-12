"""阶段 3：Python 零基础入门教材种子（幂等）。

内容数据在 ``app/seed/textbook/``（按章节拆文件），写入流程在通用写入器
``app/seed/textbook_writer.py``。本文件只提供本课程的元数据与调用入口。

- 复用既有 31 个知识点与 93 道题（按 id 关联），只改挂载章节，保留原 code，
  因此学习计划、每日任务、错题、测验历史与课程先修关系全部保留；
- 章节 / 课时 / 知识点 / 内容 / 练习 / 题目均按稳定 code upsert，可重复执行。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.seed.textbook import TEXTBOOK
from app.seed.textbook_writer import CONTENT_MODULES, iter_lessons, write_textbook

COURSE_NAME = "Python 零基础入门"
COURSE_DESCRIPTION = (
    "小码首门正式课程，面向零基础学习者：从环境搭建、变量与数据类型开始，"
    "覆盖字符串、列表、元组、集合、字典、条件与循环、函数与作用域、模块与包、"
    "文件读写、JSON、异常处理与调试，最后用一个命令行任务管理工具完成综合实战。"
    "每节课包含学习目标、通俗解释、完整示例代码与逐行讲解、常见错误分析、"
    "入门与进阶练习，以及 6 道配套测验题。"
)
COURSE_OBJECTIVES = """完成本课程后，你将能够：
1. 独立搭建 Python 环境并运行、调试自己的程序；
2. 熟练使用变量、字符串、列表、元组、集合、字典组织数据；
3. 用条件判断与循环表达业务规则，用函数拆分与复用代码；
4. 读写文本文件与 JSON，处理程序运行中的常见异常；
5. 独立完成一个可持久化的命令行任务管理工具。"""

# 教材版本：课程内容结构发生重大升级时递增
COURSE_VERSION = "1.1.0"
# 教学内容状态：本阶段内容已自检，标记 reviewed，等待人工终审后再置 published
CONTENT_STATUS = "reviewed"

META = {
    "name": COURSE_NAME,
    "description": COURSE_DESCRIPTION,
    "objectives": COURSE_OBJECTIVES,
    "direction": "python-fundamentals",
    "difficulty": "beginner",
    "level": "L0",
    "version": COURSE_VERSION,
    "publish_status": "published",
    "sort_order": 1,
}


def seed_textbook(db: Session) -> dict:
    """写入/更新本课程教材，返回统计信息。"""
    stats = write_textbook(
        db,
        course_code="python-basics",
        meta=META,
        chapters=TEXTBOOK,
        content_status=CONTENT_STATUS,
    )
    stats["lessons_total"] = len(
        {lesson["code"] for _ch, lesson in iter_lessons(TEXTBOOK)}
    )
    return stats


__all__ = [
    "CONTENT_MODULES",
    "COURSE_VERSION",
    "CONTENT_STATUS",
    "META",
    "seed_textbook",
]
