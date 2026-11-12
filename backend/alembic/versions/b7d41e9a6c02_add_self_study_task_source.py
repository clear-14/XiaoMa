"""阶段 7：每日任务来源与自选任务（plan_id 可空）

Revision ID: b7d41e9a6c02
Revises: 9c1f4a7b2d3e

增量内容（``docs/课程扩展阶段7_自主选题与学习完成度.md``）：
- ``daily_tasks`` 新增 ``source``：``plan`` 计划自动排期 / ``self_selected``
  用户自主加入今日学习；存量任务一律回填 ``plan``；
- ``plan_id`` 由 NOT NULL 改为可空：计划外课程的自选任务不挂计划；
  ``source='plan'`` 时仍必填，由 Service 层保证；
- 新增组合索引 ``(user_id, task_date, source)``，支撑今日任务按来源分组查询。

SQLite 不支持 ``ALTER TABLE ... ALTER COLUMN`` 与 ``ADD CONSTRAINT``，
因此用 ``batch_alter_table(..., recreate="always")`` 做一次 copy-and-move
表重建：既有唯一约束 ``user_date_kp``、``status`` CHECK、三列课程引用外键、
主键与时间戳的 server_default 均由反射保留；新 CHECK 与索引在 batch 内声明。

downgrade 说明：``plan_id`` 要恢复非空，计划外自选任务（``plan_id IS NULL``）
无法满足约束。这些任务是阶段 7 新增的业务数据，降级时按「不伪装成计划任务」
原则直接删除并在此写明，不做编造回填。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d41e9a6c02"
down_revision: Union[str, None] = "9c1f4a7b2d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SOURCE_CHECK_SQL = "source IN ('plan', 'self_selected')"


def upgrade() -> None:
    with op.batch_alter_table("daily_tasks", recreate="always") as batch:
        batch.alter_column("plan_id", existing_type=sa.Uuid(), nullable=True)
        # server_default 保证表重建时存量行回填为 plan；
        # 模型侧声明同样的默认，避免 alembic check 报服务端默认值漂移。
        batch.add_column(
            sa.Column(
                "source",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'plan'"),
            )
        )
        batch.create_check_constraint(op.f("ck_daily_tasks_source"), SOURCE_CHECK_SQL)
        batch.create_index(
            "ix_daily_tasks_date_source", ["user_id", "task_date", "source"]
        )


def downgrade() -> None:
    # 计划外自选任务没有 plan_id，无法满足恢复后的非空约束；
    # 直接删除，不伪造归属计划。
    op.execute(sa.text("DELETE FROM daily_tasks WHERE plan_id IS NULL"))
    with op.batch_alter_table("daily_tasks", recreate="always") as batch:
        batch.drop_index("ix_daily_tasks_date_source")
        batch.drop_constraint(op.f("ck_daily_tasks_source"), type_="check")
        batch.drop_column("source")
        batch.alter_column("plan_id", existing_type=sa.Uuid(), nullable=False)
