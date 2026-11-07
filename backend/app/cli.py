"""小码后端命令行工具。

用法：
    python -m app.cli init-db         # 初始化数据库：执行 Alembic 迁移到最新版本
    python -m app.cli seed-courses    # 写入课程种子数据（幂等，可重复执行）
    python -m app.cli seed-questions  # 写入内置题库种子（幂等，依赖课程数据）
"""

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

# 按包路径定位后端目录，保证任意工作目录下均可执行
BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def _alembic_config() -> Config:
    """构造 Alembic 配置，路径全部显式指定，不依赖执行时工作目录。"""
    if not ALEMBIC_INI.is_file():
        raise FileNotFoundError(f"未找到 Alembic 配置：{ALEMBIC_INI}")
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("prepend_sys_path", str(BACKEND_DIR))
    return cfg


def init_db() -> None:
    """执行数据库迁移（等价于 alembic upgrade head）。"""
    command.upgrade(_alembic_config(), "head")
    print("数据库迁移完成（alembic upgrade head）")


def seed_courses() -> None:
    """写入课程种子数据（幂等：重复执行不会产生重复课程）。"""
    # 延迟导入：避免 CLI 导入时即创建数据库引擎
    from app.db.session import SessionLocal
    from app.seed.course_seed import seed_courses as run_seed

    db = SessionLocal()
    try:
        stats = run_seed(db)
        print(
            "课程种子数据完成：课程 %(courses)s，章节 %(chapters)s，"
            "知识点 %(knowledge_points)s，前置关系 %(prerequisites)s" % stats
        )
    finally:
        db.close()


def seed_questions() -> None:
    """写入内置题库（幂等；需先执行 seed-courses）。"""
    from app.db.session import SessionLocal
    from app.seed.question_seed import seed_questions as run_seed

    db = SessionLocal()
    try:
        stats = run_seed(db)
        print(
            "内置题库种子完成：新增 %(created)s，更新 %(updated)s，"
            "共 %(total)s 题" % stats
        )
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="小码后端命令行工具")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="初始化数据库：执行 Alembic 迁移到最新版本")
    sub.add_parser("seed-courses", help="写入课程种子数据（幂等，可重复执行）")
    sub.add_parser("seed-questions", help="写入内置题库种子（幂等，需先有课程数据）")
    args = parser.parse_args(argv)

    if args.command == "init-db":
        init_db()
        return 0
    if args.command == "seed-courses":
        seed_courses()
        return 0
    if args.command == "seed-questions":
        seed_questions()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
