"""Alembic 迁移测试：upgrade head 应能建出全部基础表。"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "users",
    "user_profiles",
    "system_settings",
    "model_configs",
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


def test_alembic_upgrade_creates_tables(tmp_path, monkeypatch) -> None:
    """对全新数据库执行 upgrade head 后，基础表与聊天相关表应存在。"""
    db_path = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    command.upgrade(_make_config(), "head")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
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
