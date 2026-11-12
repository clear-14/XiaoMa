"""SQLite 数据库备份与恢复（PRD 5.1 / 11.3 / 12.1）。

技术设计（2026-11-07）：

- 备份使用 Python 标准库 sqlite3 的在线备份 API，生成一致的 SQLite 快照，
  不依赖文件系统直接复制（可正确处理事务与 WAL）。
- 恢复前先校验备份文件：SQLite integrity_check 通过，且包含本产品必需的
  核心表；校验通过后才替换数据库。替换前自动为当前数据库创建
  ``pre-restore-*.db`` 备份，满足“恢复前备份当前数据”。
- 恢复操作会替换数据库文件，必须在后端服务停止时执行（CLI 文档明确说明）。
  备份文件本身不会被删除，失败回滚时当前数据库文件保持不变。
- 备份目录默认位于 SQLite 文件同目录的 backups/，Docker 部署中位于数据卷，
  因此容器重启后备份仍然存在。
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, get_settings

# 恢复时必须存在的核心表（覆盖课程、档案、计划、任务、测验、会话与迁移版本）。
REQUIRED_TABLES = frozenset(
    {
        "alembic_version",
        "users",
        "user_profiles",
        "courses",
        "chapters",
        "knowledge_points",
        "learning_profiles",
        "learning_plans",
        "learning_plan_versions",
        "learning_plan_items",
        "daily_tasks",
        "question_bank",
        "quiz_attempts",
        "quiz_answers",
        "mistakes",
        "review_tasks",
        "conversations",
        "messages",
        "learning_sessions",
    }
)


class BackupError(RuntimeError):
    """备份/恢复的业务错误（文件不存在、校验失败、路径非法等）。"""


@dataclass(frozen=True)
class BackupInfo:
    """备份文件元数据。"""

    name: str
    path: Path
    size_bytes: int
    created_at: datetime


@dataclass(frozen=True)
class RestoreResult:
    """恢复结果：恢复的备份与恢复前自动生成的当前数据备份。"""

    restored: BackupInfo
    pre_restore_backup: BackupInfo


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _backup_info(path: Path) -> BackupInfo:
    stat = path.stat()
    return BackupInfo(
        name=path.name,
        path=path,
        size_bytes=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_mtime).astimezone(),
    )


def _validate_sqlite_backup(path: Path) -> None:
    """校验 SQLite 文件完整性、必要表与可读性。"""
    if not path.is_file():
        raise BackupError(f"备份文件不存在：{path.name}")
    try:
        # 只读打开，避免校验过程修改备份文件。
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise BackupError(f"无法打开备份文件：{exc}") from exc
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            raise BackupError("备份文件未通过 SQLite 完整性检查")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            raise BackupError(
                "备份文件缺少小码必需的数据表，可能不是有效的数据库备份："
                + ", ".join(missing)
            )
        version = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        if version is None:
            raise BackupError("备份文件缺少数据库迁移版本信息")
    except sqlite3.DatabaseError as exc:
        raise BackupError(f"备份文件不是有效的 SQLite 数据库：{exc}") from exc
    finally:
        connection.close()


class BackupService:
    """SQLite 备份与恢复服务（不直接操作业务表，不依赖 ORM Session）。"""

    def __init__(
        self,
        db_path: Path | None = None,
        backup_dir: Path | None = None,
    ) -> None:
        settings = get_settings()
        if db_path is None:
            db_path = _sqlite_path_from_url(settings.database_url)
        self.db_path = db_path
        if backup_dir is None:
            configured = settings.xiaoma_backup_dir
            if configured is not None:
                backup_dir = (
                    configured if configured.is_absolute() else BACKEND_DIR / configured
                )
            else:
                backup_dir = db_path.parent / "backups"
        self.backup_dir = backup_dir

    @classmethod
    def from_session(cls, db: Session) -> "BackupService":
        """按 API 实际使用的数据库连接创建服务（便于测试与依赖覆盖）。"""
        url = db.get_bind().url
        if url.get_backend_name() != "sqlite" or not url.database:
            raise BackupError("当前部署不是文件型 SQLite，无法使用内置备份功能")
        db_path = Path(url.database)
        if not db_path.is_absolute():
            db_path = (Path.cwd() / db_path).resolve()
        return cls(db_path=db_path)

    def list_backups(self) -> list[BackupInfo]:
        """按修改时间倒序列出备份。备份目录不存在时返回空列表。"""
        if not self.backup_dir.is_dir():
            return []
        backups = [
            _backup_info(path)
            for path in self.backup_dir.iterdir()
            if path.is_file() and path.suffix == ".db" and not path.name.startswith(".")
        ]
        return sorted(backups, key=lambda item: item.created_at, reverse=True)

    def create_backup(self, name: str | None = None) -> BackupInfo:
        """为当前数据库创建一致性备份，返回备份元数据。"""
        if not self.db_path.is_file():
            raise BackupError(f"数据库文件不存在：{self.db_path}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        filename = name or f"xiaoma-{_timestamp()}.db"
        self._validate_name(filename)
        target = self.backup_dir / filename
        if target.exists():
            raise BackupError(f"备份文件已存在：{filename}")

        temp = target.with_name(f".{target.name}.tmp")
        try:
            source = sqlite3.connect(self.db_path)
            try:
                destination = sqlite3.connect(temp)
                try:
                    source.backup(destination)
                finally:
                    destination.close()
            finally:
                source.close()
            _validate_sqlite_backup(temp)
            os.replace(temp, target)
        except sqlite3.Error as exc:
            raise BackupError(f"创建备份失败：{exc}") from exc
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)
        return _backup_info(target)

    def restore_backup(self, name: str) -> RestoreResult:
        """按备份名称恢复；恢复前自动备份当前数据库。"""
        source = self.resolve_backup(name)
        return self.restore_path(source)

    def restore_path(self, source: Path) -> RestoreResult:
        """按备份文件路径恢复；恢复前自动备份当前数据库。

        注意：调用方必须先停止后端服务，避免替换时仍有数据库连接持有旧文件。
        """
        source = source.expanduser()
        if not source.is_absolute():
            source = self.backup_dir / source
        source = source.resolve()
        if not source.is_file():
            raise BackupError(f"备份文件不存在：{source}")
        if source == self.db_path:
            raise BackupError("不能把当前数据库文件当作备份来恢复")
        _validate_sqlite_backup(source)

        pre_restore = self.create_backup(f"pre-restore-{_timestamp()}.db")
        temp = self.db_path.with_name(f".{self.db_path.name}.restore.tmp")
        try:
            shutil.copy2(source, temp)
            _validate_sqlite_backup(temp)
            try:
                os.replace(temp, self.db_path)
            except OSError as exc:
                raise BackupError(
                    "替换数据库文件失败，请先停止后端服务后重试："
                    f"{exc}"
                ) from exc
            self._remove_sqlite_sidecars()
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)
        return RestoreResult(
            restored=_backup_info(source),
            pre_restore_backup=pre_restore,
        )

    def resolve_backup(self, name: str) -> Path:
        """把备份名称安全解析为备份目录内的文件路径。"""
        self._validate_name(name)
        path = (self.backup_dir / name).resolve()
        if path.parent != self.backup_dir.resolve():
            raise BackupError("备份文件路径不合法")
        if not path.is_file():
            raise BackupError(f"备份文件不存在：{name}")
        return path

    @staticmethod
    def _validate_name(name: str) -> None:
        """只允许备份目录内的 .db 文件名，防止路径穿越。"""
        if not name or Path(name).name != name or "/" in name or "\\" in name:
            raise BackupError("备份文件名不合法")
        if not name.endswith(".db"):
            raise BackupError("备份文件名必须以 .db 结尾")

    def _remove_sqlite_sidecars(self) -> None:
        """恢复后清理旧库的 WAL/SHM 附属文件，避免 SQLite 读取陈旧内容。"""
        for suffix in ("-wal", "-shm"):
            sidecar = self.db_path.with_name(self.db_path.name + suffix)
            sidecar.unlink(missing_ok=True)


def _sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise BackupError("当前部署不是文件型 SQLite，无法使用内置备份功能")
    raw = database_url[len(prefix) :]
    if raw in ("", ":memory:") or raw.startswith("file:"):
        raise BackupError("当前数据库不是可备份的文件型 SQLite")
    path = Path(raw)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return path
