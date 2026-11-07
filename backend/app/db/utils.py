"""数据库工具函数。"""

from pathlib import Path


def ensure_sqlite_dir(database_url: str) -> None:
    """确保 SQLite 数据库文件所在目录存在（内存库跳过）。

    SQLite 不会自动创建不存在的父目录，写入文件库前必须保证目录就绪。
    """
    if not database_url.startswith("sqlite:///"):
        return
    path = database_url[len("sqlite:///") :]
    if path in (":memory:", "") or path.startswith("file:"):
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
