"""Alembic 迁移测试：upgrade head 应能建出全部基础表与阶段 6 结构。"""

from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "users",
    "user_profiles",
    "system_settings",
    "model_configs",
    "courses",
    "chapters",
    "lessons",
    "course_contents",
    "exercises",
    "course_versions",
    "lesson_knowledge_points",
    "course_directions",
    "course_direction_links",
    "course_prerequisites",
    "course_knowledge_point_prerequisites",
    "knowledge_points",
    "knowledge_point_prerequisites",
    "learning_profiles",
    "knowledge_mastery",
    "mastery_evidence",
    "exercise_attempts",
    "learning_plans",
    "learning_plan_versions",
    "learning_plan_items",
    "daily_tasks",
    "plan_adjustment_proposals",
    "review_requests",
    "question_bank",
    "quiz_attempts",
    "quiz_answers",
    "mistakes",
    "review_tasks",
    "conversations",
    "messages",
    "learning_sessions",
    "alembic_version",
}


def _make_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    # 显式指定迁移脚本目录，避免受执行时 CWD 影响
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def _engine_for(db_path: Path):
    return create_engine(f"sqlite:///{db_path.as_posix()}")


def test_alembic_upgrade_creates_tables(tmp_path, monkeypatch) -> None:
    """对全新数据库执行 upgrade head 后，基础表与聊天相关表应存在。"""
    db_path = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    command.upgrade(_make_config(), "head")

    engine = _engine_for(db_path)
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= tables
    engine.dispose()


def test_alembic_upgrade_is_idempotent(tmp_path, monkeypatch) -> None:
    """重复执行 upgrade head 不应报错。"""
    db_path = tmp_path / "migration_twice.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    cfg = _make_config()
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")  # 第二次应无操作


def test_alembic_downgrade_and_reupgrade(tmp_path, monkeypatch) -> None:
    """全部迁移应支持降级到 base，并能重新升级到 head（迁移可逆性验证）。"""
    db_path = tmp_path / "migration_cycle.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    cfg = _make_config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    engine = _engine_for(db_path)
    try:
        remaining = set(inspect(engine).get_table_names())
        assert remaining <= {"alembic_version"}
    finally:
        engine.dispose()

    command.upgrade(cfg, "head")
    engine = _engine_for(db_path)
    try:
        tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES <= tables
    finally:
        engine.dispose()


def test_alembic_upgrade_creates_phase6_schema(tmp_path, monkeypatch) -> None:
    """阶段 6 独立验收：两张新表、八因素快照列、任务三列与幂等唯一约束必须落地。"""
    db_path = tmp_path / "phase6_schema.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    command.upgrade(_make_config(), "head")

    engine = _engine_for(db_path)
    try:
        inspector = inspect(engine)
        assert {"plan_adjustment_proposals", "review_requests"} <= set(
            inspector.get_table_names()
        )
        plan_columns = {
            column["name"]
            for column in inspector.get_columns("learning_plan_versions")
        }
        assert "plan_context" in plan_columns
        task_columns = {
            column["name"] for column in inspector.get_columns("daily_tasks")
        }
        assert {"course_id", "chapter_id", "lesson_id"} <= task_columns
        unique_names = {
            item["name"]
            for item in inspector.get_unique_constraints("review_requests")
        }
        assert "uq_review_requests_user_kp_date" in unique_names
    finally:
        engine.dispose()


def test_alembic_backfills_historical_daily_task_refs(tmp_path, monkeypatch) -> None:
    """阶段 6 独立验收：历史任务三列按知识点真实归属回填；无课时保持 NULL。

    先在阶段 6 之前的版本 ``d8cfe871faa5`` 造两条真实历史任务（其中一条
    的知识点没有归属课时），再升级到 head，验证迁移的回填函数既不漏填、
    也不猜测课时。
    """
    db_path = tmp_path / "phase6_backfill.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cfg = _make_config()
    command.upgrade(cfg, "d8cfe871faa5")

    ids = {
        key: uuid4().hex
        for key in (
            "user",
            "course",
            "chapter",
            "lesson",
            "kp",
            "kp_without_lesson",
            "plan",
            "task",
            "task_without_lesson",
        )
    }
    engine = _engine_for(db_path)
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (id, username) VALUES (:i, 'accept')"),
            {"i": ids["user"]},
        )
        conn.execute(
            text(
                "INSERT INTO courses (id, code, name) "
                "VALUES (:i, 'accept-course', '验收课程')"
            ),
            {"i": ids["course"]},
        )
        conn.execute(
            text(
                "INSERT INTO chapters (id, course_id, code, title, order_index) "
                "VALUES (:i, :c, 'accept-ch', '验收章节', 1)"
            ),
            {"i": ids["chapter"], "c": ids["course"]},
        )
        conn.execute(
            text(
                "INSERT INTO lessons (id, chapter_id, code, title) "
                "VALUES (:i, :c, 'accept-lesson', '验收课时')"
            ),
            {"i": ids["lesson"], "c": ids["chapter"]},
        )
        kp_sql = (
            "INSERT INTO knowledge_points "
            "(id, chapter_id, code, name, learning_goal, difficulty, "
            " estimated_minutes, mastery_criteria, order_index) "
            "VALUES (:i, :c, :code, :name, '目标', 'beginner', 30, '标准', 1)"
        )
        conn.execute(
            text(kp_sql),
            {
                "i": ids["kp"],
                "c": ids["chapter"],
                "code": "accept-kp-1",
                "name": "验收知识点一",
            },
        )
        conn.execute(
            text(kp_sql),
            {
                "i": ids["kp_without_lesson"],
                "c": ids["chapter"],
                "code": "accept-kp-2",
                "name": "验收知识点二",
            },
        )
        conn.execute(
            text(
                "INSERT INTO lesson_knowledge_points (lesson_id, knowledge_point_id) "
                "VALUES (:l, :k)"
            ),
            {"l": ids["lesson"], "k": ids["kp"]},
        )
        conn.execute(
            text(
                "INSERT INTO learning_plans (id, user_id, course_id, status) "
                "VALUES (:i, :u, :c, 'active')"
            ),
            {"i": ids["plan"], "u": ids["user"], "c": ids["course"]},
        )
        task_sql = (
            "INSERT INTO daily_tasks "
            "(id, user_id, plan_id, knowledge_point_id, task_date, day_index, status) "
            "VALUES (:i, :u, :p, :k, '2026-01-01', 1, 'pending')"
        )
        conn.execute(
            text(task_sql),
            {
                "i": ids["task"],
                "u": ids["user"],
                "p": ids["plan"],
                "k": ids["kp"],
            },
        )
        conn.execute(
            text(task_sql),
            {
                "i": ids["task_without_lesson"],
                "u": ids["user"],
                "p": ids["plan"],
                "k": ids["kp_without_lesson"],
            },
        )
    engine.dispose()

    command.upgrade(cfg, "head")

    engine = _engine_for(db_path)
    try:
        with engine.connect() as conn:
            rows = {
                row[0]: tuple(row[1:])
                for row in conn.execute(
                    text(
                        "SELECT id, course_id, chapter_id, lesson_id FROM daily_tasks"
                    )
                )
            }
        assert rows[ids["task"]] == (
            ids["course"],
            ids["chapter"],
            ids["lesson"],
        )
        assert rows[ids["task_without_lesson"]] == (
            ids["course"],
            ids["chapter"],
            None,
        )
    finally:
        engine.dispose()
