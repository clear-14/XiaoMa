"""pytest 共享夹具。"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


@pytest.fixture(autouse=True)
def _test_secret_key(monkeypatch):
    """测试统一使用固定的加密密钥，避免在开发目录生成 .secret_key 文件。"""
    from app.core import config, crypto

    monkeypatch.setenv("XIAOMA_SECRET_KEY", "xiaoma-test-secret-key")
    config.get_settings.cache_clear()
    crypto.reset_crypto_cache()
    yield
    config.get_settings.cache_clear()
    crypto.reset_crypto_cache()


def _enable_sqlite_foreign_keys(engine) -> None:
    """SQLite 默认不启用外键约束；测试引擎连接时显式开启（与 app/db/session.py 一致）。"""

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture
def db_engine(tmp_path):
    """基于临时文件的 SQLite 引擎，表结构已建好。"""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    _enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    """测试用数据库会话。"""
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def api_env(tmp_path):
    """API 测试环境：临时数据库 + TestClient。

    返回 (client, session_factory)，两者共享同一临时数据库；
    通过 dependency_overrides 替换 get_db，不触碰真实开发数据库。
    """
    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app

    engine = create_engine(
        f"sqlite:///{tmp_path / 'api_test.db'}",
        connect_args={"check_same_thread": False},
    )
    _enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
