"""阶段 3：教学内容补齐 15 个模块字段与内容状态

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-11-08

只对 course_contents 做 ADD COLUMN 与建索引：
- 不重建表，不触碰 lessons / knowledge_points / question_bank 等既有数据；
- 新增列全部可空，存量行升级后仍有效；
- status 默认 draft，存量内容不会被误判为已发布。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# 需要新增的教材模块列（全部 Text、可空）
CONTENT_NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("why_learn", sa.Text()),
    ("plain_explanation", sa.Text()),
    ("example_output", sa.Text()),
    ("error_analysis", sa.Text()),
    ("beginner_exercises", sa.Text()),
    ("advanced_exercises", sa.Text()),
    ("quiz_note", sa.Text()),
    ("next_lesson", sa.Text()),
)


def upgrade() -> None:
    existing = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("course_contents")
    }
    for name, type_ in CONTENT_NEW_COLUMNS:
        if name not in existing:
            op.add_column("course_contents", sa.Column(name, type_, nullable=True))

    if "status" not in existing:
        op.add_column(
            "course_contents",
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default="draft",
            ),
        )
        op.create_index(
            "ix_course_contents_status", "course_contents", ["status"]
        )

    # SQLite 无法直接加 CHECK 约束，改用触发器保证取值合法（与模型定义一致）
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_course_contents_status_insert
        BEFORE INSERT ON course_contents
        FOR EACH ROW
        WHEN NEW.status NOT IN ('draft', 'reviewed', 'published')
        BEGIN
            SELECT RAISE(ABORT, 'content_status');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_course_contents_status_update
        BEFORE UPDATE OF status ON course_contents
        FOR EACH ROW
        WHEN NEW.status NOT IN ('draft', 'reviewed', 'published')
        BEGIN
            SELECT RAISE(ABORT, 'content_status');
        END
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_course_contents_status_update")
    op.execute("DROP TRIGGER IF EXISTS trg_course_contents_status_insert")

    existing = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("course_contents")
    }
    if "status" in existing:
        op.drop_index("ix_course_contents_status", table_name="course_contents")
        with op.batch_alter_table("course_contents") as batch:
            batch.drop_column("status")
    for name, _type in CONTENT_NEW_COLUMNS:
        if name in existing:
            with op.batch_alter_table("course_contents") as batch:
                batch.drop_column(name)
