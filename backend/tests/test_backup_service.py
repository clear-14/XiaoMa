"""SQLite 备份/恢复服务测试（PRD 5.1 / 11.3 / 12.1）。"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

import app.models  # noqa: F401 - 注册全部 ORM 模型
from app.db.base import Base
from app.services.backup_service import BackupError, BackupService


def _make_database(path: Path) -> None:
    """创建包含完整表结构、alembic_version 与 marker 数据的测试数据库。"""
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('test-head')")
        )
        connection.execute(text("CREATE TABLE marker (value TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO marker (value) VALUES ('v1')"))
    engine.dispose()


def _read_marker(path: Path) -> str:
    connection = sqlite3.connect(path)
    try:
        return connection.execute("SELECT value FROM marker").fetchone()[0]
    finally:
        connection.close()


def _write_marker(path: Path, value: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("UPDATE marker SET value = ?", (value,))
        connection.commit()
    finally:
        connection.close()


def test_create_backup_and_list(tmp_path) -> None:
    """备份文件应存在、完整，并能出现在备份列表中。"""
    db_path = tmp_path / "xiaoma.db"
    backup_dir = tmp_path / "backups"
    _make_database(db_path)
    service = BackupService(db_path=db_path, backup_dir=backup_dir)

    info = service.create_backup("manual.db")
    assert info.name == "manual.db"
    assert info.path.is_file()
    assert info.size_bytes > 0
    assert _read_marker(info.path) == "v1"
    assert [item.name for item in service.list_backups()] == ["manual.db"]


def test_restore_reverts_data_and_creates_pre_restore_backup(tmp_path) -> None:
    """恢复应回到备份时数据，并自动保留恢复前的当前数据。"""
    db_path = tmp_path / "xiaoma.db"
    backup_dir = tmp_path / "backups"
    _make_database(db_path)
    service = BackupService(db_path=db_path, backup_dir=backup_dir)
    service.create_backup("before.db")

    _write_marker(db_path, "v2")
    result = service.restore_backup("before.db")

    assert _read_marker(db_path) == "v1"
    assert result.pre_restore_backup.path.is_file()
    assert result.pre_restore_backup.name.startswith("pre-restore-")
    assert _read_marker(result.pre_restore_backup.path) == "v2"


def test_invalid_backup_does_not_replace_database(tmp_path) -> None:
    """损坏的备份必须在替换前被拒绝，当前数据库保持不变。"""
    db_path = tmp_path / "xiaoma.db"
    backup_dir = tmp_path / "backups"
    _make_database(db_path)
    service = BackupService(db_path=db_path, backup_dir=backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    invalid = backup_dir / "broken.db"
    invalid.write_text("这不是 SQLite 数据库", encoding="utf-8")

    with pytest.raises(BackupError):
        service.restore_path(invalid)
    assert _read_marker(db_path) == "v1"


def test_backup_missing_required_tables_is_rejected(tmp_path) -> None:
    """缺少小码核心表的 SQLite 文件不能用于恢复。"""
    db_path = tmp_path / "xiaoma.db"
    backup_dir = tmp_path / "backups"
    _make_database(db_path)
    service = BackupService(db_path=db_path, backup_dir=backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    incomplete = backup_dir / "incomplete.db"
    connection = sqlite3.connect(incomplete)
    connection.execute("CREATE TABLE alembic_version (version_num TEXT)")
    connection.execute("INSERT INTO alembic_version VALUES ('x')")
    connection.commit()
    connection.close()

    with pytest.raises(BackupError, match="缺少"):
        service.restore_path(incomplete)


def test_backup_name_path_traversal_rejected(tmp_path) -> None:
    """备份名称不得穿越备份目录。"""
    service = BackupService(
        db_path=tmp_path / "xiaoma.db",
        backup_dir=tmp_path / "backups",
    )
    for name in ("../evil.db", "a/../../evil.db", "evil.txt", ""):
        with pytest.raises(BackupError):
            service.resolve_backup(name)


def test_backup_api_create_list_download_delete(api_env) -> None:
    """备份 API：创建、列表、下载、删除全流程。"""
    client, factory = api_env
    db = factory()
    try:
        db.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        db.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('test-head')")
        )
        db.commit()
    finally:
        db.close()

    created = client.post("/api/v1/data/backups")
    assert created.status_code == 201, created.text
    name = created.json()["name"]
    assert name.endswith(".db")

    listed = client.get("/api/v1/data/backups")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == [name]

    downloaded = client.get(f"/api/v1/data/backups/{name}")
    assert downloaded.status_code == 200
    assert downloaded.content[:16] == b"SQLite format 3\x00"

    deleted = client.delete(f"/api/v1/data/backups/{name}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/data/backups/{name}").status_code == 404
