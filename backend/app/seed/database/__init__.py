"""「数据库与 Python 数据库开发」课程教材数据（阶段 4A）。

章节结构以课程目录（``course_catalog_seed``）为准：本包只提供教学内容、
知识点、练习与测验题。
"""

from app.seed.database.ch01_03 import CHAPTERS as _CH01_03
from app.seed.database.ch04_06 import CHAPTERS as _CH04_06
from app.seed.database.ch07_09 import CHAPTERS as _CH07_09

CHAPTERS: list[dict] = [*_CH01_03, *_CH04_06, *_CH07_09]

COURSE_CODE = "python-database"

META: dict = {
    "name": "数据库与 Python 数据库开发",
    "description": (
        "从关系模型与 SQL 写起，经 SQLite 实战、索引与事务，进入 SQLAlchemy 2.x 的 "
        "Engine、Core 表达式与声明式 ORM 模型，最后用 Session 管理事务边界、完成 CRUD "
        "并用 Alembic 维护可回滚的迁移链。示例以 SQLAlchemy 2.0 与 SQLite 为准，"
        "每节课都给出可直接运行的代码与逐行解释。"
    ),
    "objectives": """完成本课程后，你将能够：
1. 写出常用的建表、查询、连接与聚合 SQL，并解释 NULL、约束与索引的作用；
2. 用 sqlite3 完成建库、查询、事务与备份；
3. 用 SQLAlchemy 2.x 定义模型与关系，正确管理 Engine、连接与 Session；
4. 识别并解决 N+1 查询、连接放大与并发写入问题；
5. 用 Alembic 维护版本链，编写可 upgrade/downgrade 循环的迁移。""",
    "direction": "python-engineering",
    "difficulty": "intermediate",
    "level": "L1",
    "version": "1.0.0",
    "publish_status": "published",
    "sort_order": 3,
}


def total_lessons() -> int:
    return sum(len(chapter["lessons"]) for chapter in CHAPTERS)


def total_questions() -> int:
    return sum(
        len(lesson["questions"])
        for chapter in CHAPTERS
        for lesson in chapter["lessons"]
    )


def total_exercises() -> int:
    return sum(
        len(lesson["practice"])
        for chapter in CHAPTERS
        for lesson in chapter["lessons"]
    )
