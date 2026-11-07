"""Alembic 迁移环境：连接串统一从应用配置读取（支持 DATABASE_URL 环境变量覆盖）。"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  # 确保全部模型注册到 Base.metadata
from app.core.config import Settings
from app.db.base import Base
from app.db.utils import ensure_sqlite_dir

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 每次迁移时新建配置实例，确保 DATABASE_URL 环境变量即时生效（测试依赖此行为）
settings = Settings()


def _get_url() -> str:
    return settings.database_url


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 脚本，不连接数据库。"""
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库执行迁移。"""
    url = _get_url()
    ensure_sqlite_dir(url)
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
