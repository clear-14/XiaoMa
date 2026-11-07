"""数据持久性测试：模拟服务重启后数据不丢失。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User


def test_data_survives_engine_restart(tmp_path) -> None:
    """关闭并重新打开数据库后，数据应仍然存在。"""
    db_path = tmp_path / "persist.db"
    url = f"sqlite:///{db_path.as_posix()}"

    # 第一次"启动"：建表并写入数据
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as s:
        s.add(User(username="persistent"))
        s.commit()
    engine.dispose()  # 释放引擎与连接，模拟服务重启

    # 第二次"启动"：重新连接，数据应可读
    engine2 = create_engine(url, connect_args={"check_same_thread": False})
    session_factory2 = sessionmaker(bind=engine2)
    with session_factory2() as s:
        usernames = [u.username for u in s.query(User).all()]
        assert usernames == ["persistent"]
    engine2.dispose()
