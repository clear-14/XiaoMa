"""V1.4：消息卡片字段 + 流式/停止状态

Revision ID: 9c1f4a7b2d3e
Revises: 7e6ec48dafbe

增量内容：
- ``messages`` 新增 message_type / structured_data / card_version 三列，
  用于结构化卡片消息的持久化与刷新恢复（PRD V1.4 §11）；
- ``status`` 的 CHECK 由 ('completed','error') 扩为
  ('completed','error','streaming','stopped')，支持「生成中」与「用户停止」；
- 存量消息回填 message_type='text'，其余两列保持 NULL，status 不变。

SQLite 不支持原地修改 CHECK 约束，也不支持 ``ALTER TABLE ADD CONSTRAINT``；
这里用 ``batch_alter_table(..., recreate="always")`` 做一次 copy-and-move
表重建，role 的 CHECK、指向 conversations 的外键（ON DELETE CASCADE）、
主键、索引与 created_at/updated_at 的 server_default 均由反射保留。
外键语义依赖运行时的 ``PRAGMA foreign_keys=ON``（由 db/session.py 与
测试夹具开启），downgrade 同样走 batch 重建。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c1f4a7b2d3e"
down_revision: Union[str, None] = "7e6ec48dafbe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_STATUS_SQL = "status IN ('completed', 'error', 'streaming', 'stopped')"
OLD_STATUS_SQL = "status IN ('completed', 'error')"


def upgrade() -> None:
    with op.batch_alter_table("messages", recreate="always") as batch:
        # server_default 保证表重建时存量行自动回填；模型侧声明同样的默认，
        # 避免 alembic check 检测到服务端默认值漂移。
        batch.add_column(
            sa.Column(
                "message_type",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'text'"),
            )
        )
        batch.add_column(
            sa.Column("structured_data", sa.JSON(), nullable=True)
        )
        batch.add_column(
            sa.Column("card_version", sa.String(length=16), nullable=True)
        )
        batch.drop_constraint(op.f("ck_messages_status"), type_="check")
        batch.create_check_constraint(op.f("ck_messages_status"), NEW_STATUS_SQL)


def downgrade() -> None:
    # 旧 CHECK 不认识新状态，先归一化为 error（保留内容、不伪装成功），
    # 否则表重建会因约束冲突失败。
    op.execute(
        sa.text(
            "UPDATE messages SET status = 'error' "
            "WHERE status IN ('streaming', 'stopped')"
        )
    )
    with op.batch_alter_table("messages", recreate="always") as batch:
        batch.drop_constraint(op.f("ck_messages_status"), type_="check")
        batch.create_check_constraint(op.f("ck_messages_status"), OLD_STATUS_SQL)
        batch.drop_column("card_version")
        batch.drop_column("structured_data")
        batch.drop_column("message_type")
