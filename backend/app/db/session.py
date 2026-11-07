"""数据库引擎与 Session 统一管理。"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.utils import ensure_sqlite_dir

settings = get_settings()
ensure_sqlite_dir(settings.database_url)

# 统一引擎：check_same_thread=False 允许 FastAPI 多线程请求共享连接；
# pool_pre_ping 在连接失效时自动重建，避免服务重启后陈旧连接报错。
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    """SQLite 默认不启用外键约束；连接时显式开启，使迁移中声明的
    ON DELETE CASCADE 等外键行为真正生效（应用统一在此维护数据完整性）。"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：每个请求一个数据库会话，请求结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
