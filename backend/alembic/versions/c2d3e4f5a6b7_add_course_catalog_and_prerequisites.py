"""add course catalog: directions, direction links, course prerequisites

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-11-08 14:35:00.000000

阶段 2：课程目录与学习路线建设。

升级策略（只增不改，不重建既有表、不动任何业务数据）：
- 新增 ``course_directions``：课程方向字典（5 个方向由种子写入）；
- 新增 ``course_direction_links``：课程与方向的多对多关联（一门课可属多个方向）；
- 新增 ``course_prerequisites``：课程级先修有向边，CHECK 拒绝自引用，
  环检测由 Service 在写入时执行（SQLite 无法用表约束表达无环）；
- 新增 ``course_knowledge_point_prerequisites``：课程入学需掌握的知识点（可跨课程）。

既有 ``courses`` / ``chapters`` / ``lessons`` / ``knowledge_points`` 结构不变，
因此题库、学习计划、测验、错题复习等已上线数据完全不受影响。

降级只删除上述 4 张新表，课程与学习历史数据保留。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TIMESTAMP_COLUMNS = (
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("(CURRENT_TIMESTAMP)"),
        nullable=False,
    ),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("(CURRENT_TIMESTAMP)"),
        nullable=False,
    ),
)


def upgrade() -> None:
    # ---- 1. 课程方向 ----
    op.create_table(
        "course_directions",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_TIMESTAMP_COLUMNS,
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_directions")),
        sa.UniqueConstraint("code", name=op.f("uq_course_directions_code")),
    )

    # ---- 2. 课程 ↔ 方向（多对多）----
    op.create_table(
        "course_direction_links",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("direction_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_course_direction_links_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["direction_id"],
            ["course_directions.id"],
            name=op.f("fk_course_direction_links_direction_id_course_directions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "course_id", "direction_id", name=op.f("pk_course_direction_links")
        ),
    )
    op.create_index(
        op.f("ix_course_direction_links_direction_id"),
        "course_direction_links",
        ["direction_id"],
        unique=False,
    )

    # ---- 3. 课程级先修（有向边）----
    op.create_table(
        "course_prerequisites",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("prerequisite_course_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "course_id <> prerequisite_course_id",
            name=op.f("ck_course_prerequisites_course_prerequisite_not_self"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_course_prerequisites_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_course_id"],
            ["courses.id"],
            name=op.f("fk_course_prerequisites_prerequisite_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "course_id", "prerequisite_course_id", name=op.f("pk_course_prerequisites")
        ),
    )
    op.create_index(
        op.f("ix_course_prerequisites_prerequisite_course_id"),
        "course_prerequisites",
        ["prerequisite_course_id"],
        unique=False,
    )

    # ---- 4. 课程入学所需知识点（跨课程引用）----
    op.create_table(
        "course_knowledge_point_prerequisites",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_point_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_course_knowledge_point_prerequisites_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_point_id"],
            ["knowledge_points.id"],
            name=op.f(
                "fk_course_knowledge_point_prerequisites_knowledge_point_id_knowledge_points"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "course_id",
            "knowledge_point_id",
            name=op.f("pk_course_knowledge_point_prerequisites"),
        ),
    )
    op.create_index(
        op.f("ix_course_knowledge_point_prerequisites_knowledge_point_id"),
        "course_knowledge_point_prerequisites",
        ["knowledge_point_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_course_knowledge_point_prerequisites_knowledge_point_id"),
        table_name="course_knowledge_point_prerequisites",
    )
    op.drop_table("course_knowledge_point_prerequisites")

    op.drop_index(
        op.f("ix_course_prerequisites_prerequisite_course_id"),
        table_name="course_prerequisites",
    )
    op.drop_table("course_prerequisites")

    op.drop_index(
        op.f("ix_course_direction_links_direction_id"),
        table_name="course_direction_links",
    )
    op.drop_table("course_direction_links")

    op.drop_table("course_directions")
