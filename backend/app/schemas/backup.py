"""数据备份接口 Schema。"""

from datetime import datetime

from pydantic import BaseModel


class BackupOut(BaseModel):
    """备份文件信息。"""

    name: str
    size_bytes: int
    created_at: datetime
