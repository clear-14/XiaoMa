"""小码后端命令行工具。

用法：
    python -m app.cli init-db         # 初始化数据库：执行 Alembic 迁移到最新版本
    python -m app.cli seed-courses    # 写入课程种子数据（幂等，可重复执行）
    python -m app.cli seed-questions  # 写入内置题库种子（幂等，依赖课程数据）
    python -m app.cli seed-phase4a     # 写入 Python 进阶 / 数据库两门课教材（幂等）
    python -m app.cli seed-phase4b     # 写入 FastAPI 后端开发教材（幂等）
    python -m app.cli seed-phase4c     # 写入大模型 API 应用开发教材（幂等）
    python -m app.cli seed-phase4d     # 写入 LangGraph Agent 开发教材（幂等）
    python -m app.cli backup-db       # 备份当前 SQLite 数据库
    python -m app.cli list-backups    # 列出备份文件
    python -m app.cli restore-db NAME --yes  # 恢复备份（请先停止后端服务）
"""

import argparse
import sys
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
    """写入课程内容与课程目录种子（幂等：重复执行不会产生重复课程/章节/课时）。

    顺序：先写「Python 零基础入门」的章节/课时/知识点，再写方向、七门课程目录
    与先修依赖 —— 后者需要引用前者的课程与知识点。
    """
    # 延迟导入：避免 CLI 导入时即创建数据库引擎
    from app.db.session import SessionLocal
    from app.seed.course_catalog_seed import seed_course_catalog
    from app.seed.course_seed import seed_courses as run_content_seed

    db = SessionLocal()
    try:
        content = run_content_seed(db)
        catalog = seed_course_catalog(db)
        print(
            "课程内容种子完成：课程 %(courses)s，章节 %(chapters)s，课时 %(lessons)s，"
            "知识点 %(knowledge_points)s，前置关系 %(prerequisites)s" % content
        )
        if content.get("skipped") == "textbook":
            print("提示：该课程已进入教材模式，已跳过旧版目录重写（教材由 seed-textbook 维护）")
        print(
            "课程目录种子完成：方向 %(directions)s，课程 %(courses)s，"
            "处理章节 %(chapters)s，处理课时 %(lessons)s，"
            "新增课程先修 %(prerequisites)s，新增入学知识点 %(required_knowledge_points)s"
            % catalog
        )
    finally:
        db.close()


def seed_catalog() -> None:
    """仅写入课程目录（方向、七门课程、章节课时、先修依赖）。"""
    from app.db.session import SessionLocal
    from app.seed.course_catalog_seed import seed_course_catalog

    db = SessionLocal()
    try:
        stats = seed_course_catalog(db)
        print(
            "课程目录种子完成：方向 %(directions)s，课程 %(courses)s，"
            "处理章节 %(chapters)s，处理课时 %(lessons)s，"
            "新增课程先修 %(prerequisites)s，新增入学知识点 %(required_knowledge_points)s"
            % stats
        )
    finally:
        db.close()


def seed_textbook() -> None:
    """写入「Python 零基础入门」完整教材（20 章 / 29 课时，幂等）。"""
    from app.db.session import SessionLocal
    from app.seed.textbook_seed import seed_textbook as run_seed

    db = SessionLocal()
    try:
        stats = run_seed(db)
        print(
            "教材种子完成：新增章节 %(chapters_created)s，更新章节 %(chapters_updated)s，"
            "新增课时 %(lessons_created)s，清理旧课时 %(lessons_removed)s，"
            "复用知识点 %(knowledge_points_reused)s，新增知识点 %(knowledge_points_created)s，"
            "新增内容 %(contents_created)s，更新内容 %(contents_updated)s，"
            "新增练习 %(exercises_created)s，更新练习 %(exercises_updated)s，"
            "新增题目 %(questions_created)s，更新题目 %(questions_updated)s，"
            "清理前置倒挂 %(prerequisite_edges_removed)s"
            % stats
        )
        print("课时总数：%(lessons_total)s，教学内容总数：%(contents_total)s" % stats)
    finally:
        db.close()


def seed_phase4a() -> None:
    """写入阶段 4A 两门课的完整教材（Python 进阶、数据库，幂等）。

    章节与课时结构由课程目录提供，因此这里先跑一次目录种子，再写正文。
    """
    from app.db.session import SessionLocal
    from app.seed.course_catalog_seed import seed_course_catalog
    from app.seed.phase4a_seed import seed_phase4a as run_seed

    db = SessionLocal()
    try:
        catalog = seed_course_catalog(db)
        stats = run_seed(db)
        print(
            "课程目录对齐：处理章节 %(chapters)s，处理课时 %(lessons)s" % catalog
        )
        for code in ("python-advanced", "python-database"):
            item = stats[code]
            print(
                f"{code}：课时 {item['lessons_total']}，内容 {item['contents_total']}，"
                f"新增内容 {item['contents_created']}，更新内容 {item['contents_updated']}，"
                f"新增练习 {item['exercises_created']}，新增题目 {item['questions_created']}"
            )
        print(
            "阶段 4A 合计：课时 %(lessons_total)s，教学内容 %(contents_total)s"
            % stats
        )
    finally:
        db.close()


def seed_phase4b() -> None:
    """写入阶段 4B 的 FastAPI 后端开发教材（16 章 / 31 课时，幂等）。

    章节与课时结构由课程目录提供，因此这里先跑一次目录种子，再写正文。
    """
    from app.db.session import SessionLocal
    from app.seed.course_catalog_seed import seed_course_catalog
    from app.seed.phase4b_seed import seed_phase4b as run_seed

    db = SessionLocal()
    try:
        catalog = seed_course_catalog(db)
        stats = run_seed(db)
        print("课程目录对齐：处理章节 %(chapters)s，处理课时 %(lessons)s" % catalog)
        item = stats["fastapi-backend"]
        print(
            f"fastapi-backend：课时 {item['lessons_total']}，内容 {item['contents_total']}，"
            f"新增内容 {item['contents_created']}，更新内容 {item['contents_updated']}，"
            f"新增练习 {item['exercises_created']}，新增题目 {item['questions_created']}"
        )
        print(
            "阶段 4B 合计：课时 %(lessons_total)s，教学内容 %(contents_total)s" % stats
        )
    finally:
        db.close()


def seed_phase4c() -> None:
    """写入阶段 4C 的大模型 API 应用开发教材（16 章 / 32 课时，幂等）。

    章节与课时结构由课程目录提供，因此这里先跑一次目录种子，再写正文。
    """
    from app.db.session import SessionLocal
    from app.seed.course_catalog_seed import seed_course_catalog
    from app.seed.phase4c_seed import seed_phase4c as run_seed

    db = SessionLocal()
    try:
        catalog = seed_course_catalog(db)
        stats = run_seed(db)
        print("课程目录对齐：处理章节 %(chapters)s，处理课时 %(lessons)s" % catalog)
        item = stats["llm-api"]
        print(
            f"llm-api：课时 {item['lessons_total']}，内容 {item['contents_total']}，"
            f"新增内容 {item['contents_created']}，更新内容 {item['contents_updated']}，"
            f"新增练习 {item['exercises_created']}，新增题目 {item['questions_created']}"
        )
        print(
            "阶段 4C 合计：课时 %(lessons_total)s，教学内容 %(contents_total)s" % stats
        )
    finally:
        db.close()


def seed_phase4d() -> None:
    """写入阶段 4D 的 LangGraph Agent 开发教材（28 章 / 47 课时，幂等）。

    章节与课时结构由课程目录提供，因此这里先跑一次目录种子，再写正文。
    """
    from app.db.session import SessionLocal
    from app.seed.course_catalog_seed import seed_course_catalog
    from app.seed.phase4d_seed import seed_phase4d as run_seed

    db = SessionLocal()
    try:
        catalog = seed_course_catalog(db)
        stats = run_seed(db)
        print("课程目录对齐：处理章节 %(chapters)s，处理课时 %(lessons)s" % catalog)
        item = stats["langgraph-agent"]
        print(
            f"langgraph-agent：课时 {item['lessons_total']}，内容 {item['contents_total']}，"
            f"新增内容 {item['contents_created']}，更新内容 {item['contents_updated']}，"
            f"新增练习 {item['exercises_created']}，新增题目 {item['questions_created']}"
        )
        print(
            "阶段 4D 合计：课时 %(lessons_total)s，教学内容 %(contents_total)s" % stats
        )
    finally:
        db.close()


def seed_phase4e() -> None:
    """写入阶段 4E 的软件工程与项目部署教材（8 章 / 28 课时，幂等）。

    章节与课时结构由课程目录提供，因此这里先跑一次目录种子，再写正文。
    """
    from app.db.session import SessionLocal
    from app.seed.course_catalog_seed import seed_course_catalog
    from app.seed.phase4e_seed import seed_phase4e as run_seed

    db = SessionLocal()
    try:
        catalog = seed_course_catalog(db)
        stats = run_seed(db)
        print("课程目录对齐：处理章节 %(chapters)s，处理课时 %(lessons)s" % catalog)
        item = stats["software-engineering-deploy"]
        print(
            f"software-engineering-deploy：课时 {item['lessons_total']}，"
            f"内容 {item['contents_total']}，"
            f"新增内容 {item['contents_created']}，更新内容 {item['contents_updated']}，"
            f"新增练习 {item['exercises_created']}，新增题目 {item['questions_created']}"
        )
        print(
            "阶段 4E 合计：课时 %(lessons_total)s，教学内容 %(contents_total)s" % stats
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


def backup_db(name: str | None = None) -> int:
    """备份当前数据库；默认写入数据库同目录的 backups/。"""
    from app.services.backup_service import BackupError, BackupService

    try:
        info = BackupService().create_backup(name)
    except BackupError as exc:
        print(f"备份失败：{exc}", file=sys.stderr)
        return 1
    print(f"备份完成：{info.path}")
    print(f"大小：{info.size_bytes} 字节")
    return 0


def list_backups() -> int:
    """列出全部备份文件。"""
    from app.services.backup_service import BackupError, BackupService

    try:
        service = BackupService()
        backups = service.list_backups()
    except BackupError as exc:
        print(f"读取备份失败：{exc}", file=sys.stderr)
        return 1
    if not backups:
        print(f"暂无备份（目录：{service.backup_dir}）")
        return 0
    print(f"备份目录：{service.backup_dir}")
    for item in backups:
        print(f"- {item.name}  {item.size_bytes} 字节  {item.created_at:%Y-%m-%d %H:%M:%S}")
    return 0


def restore_db(backup: str, confirmed: bool) -> int:
    """恢复备份。必须显式 --yes；恢复前自动备份当前数据库。"""
    from app.services.backup_service import BackupError, BackupService

    if not confirmed:
        print(
            "恢复会替换当前数据库文件。请先停止后端服务，然后加 --yes 确认执行。",
            file=sys.stderr,
        )
        return 2
    service = BackupService()
    source = Path(backup)
    if not source.is_file():
        # 允许只写备份名称（在默认备份目录中查找）
        source = service.backup_dir / backup
    try:
        result = service.restore_path(source)
    except BackupError as exc:
        print(f"恢复失败：{exc}", file=sys.stderr)
        return 1
    print(f"恢复完成：{result.restored.name}")
    print(f"恢复前已自动备份当前数据：{result.pre_restore_backup.path}")
    print("请重新启动后端服务。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="小码后端命令行工具")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="初始化数据库：执行 Alembic 迁移到最新版本")
    sub.add_parser("seed-courses", help="写入课程内容与目录种子（幂等，可重复执行）")
    sub.add_parser("seed-catalog", help="仅写入课程目录与先修依赖（幂等）")
    sub.add_parser("seed-textbook", help="写入 Python 零基础入门完整教材（20 章，幂等）")
    sub.add_parser("seed-questions", help="写入内置题库种子（幂等，需先有课程数据）")
    sub.add_parser(
        "seed-phase4a",
        help="写入 Python 进阶与数据库两门课教材（阶段 4A，幂等）",
    )
    sub.add_parser(
        "seed-phase4b",
        help="写入 FastAPI 后端开发教材（阶段 4B，幂等）",
    )
    sub.add_parser(
        "seed-phase4c",
        help="写入大模型 API 应用开发教材（阶段 4C，幂等）",
    )
    sub.add_parser(
        "seed-phase4d",
        help="写入 LangGraph Agent 开发教材（阶段 4D，幂等）",
    )
    sub.add_parser(
        "seed-phase4e",
        help="写入软件工程与项目部署教材（阶段 4E，幂等）",
    )
    backup_parser = sub.add_parser("backup-db", help="备份当前 SQLite 数据库")
    backup_parser.add_argument("--name", help="备份文件名（默认自动生成，需以 .db 结尾）")
    sub.add_parser("list-backups", help="列出备份文件")
    restore_parser = sub.add_parser(
        "restore-db", help="恢复备份（会替换数据库，请先停止后端服务）"
    )
    restore_parser.add_argument("backup", help="备份文件名或完整路径")
    restore_parser.add_argument(
        "--yes", action="store_true", help="确认替换当前数据库（必需）"
    )
    args = parser.parse_args(argv)

    if args.command == "init-db":
        init_db()
        return 0
    if args.command == "seed-courses":
        seed_courses()
        return 0
    if args.command == "seed-catalog":
        seed_catalog()
        return 0

    if args.command == "seed-textbook":
        seed_textbook()
        return 0
    if args.command == "seed-questions":
        seed_questions()
        return 0
    if args.command == "seed-phase4a":
        seed_phase4a()
        return 0
    if args.command == "seed-phase4b":
        seed_phase4b()
        return 0
    if args.command == "seed-phase4c":
        seed_phase4c()
        return 0
    if args.command == "seed-phase4d":
        seed_phase4d()
        return 0
    if args.command == "seed-phase4e":
        seed_phase4e()
        return 0
    if args.command == "backup-db":
        return backup_db(args.name)
    if args.command == "list-backups":
        return list_backups()
    if args.command == "restore-db":
        return restore_db(args.backup, args.yes)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
