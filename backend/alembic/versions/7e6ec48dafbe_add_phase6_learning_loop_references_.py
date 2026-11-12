"""阶段 6：学习闭环课程引用 + 计划调整提案 + 复习申请

Revision ID: 7e6ec48dafbe
Revises: d8cfe871faa5

只做增量：
- ``daily_tasks`` 新增 course_id / chapter_id(module) / lesson_id 三列，
  让今日任务固化真实课程层级引用；升级时按知识点归属回填历史任务；
- 新增 ``plan_adjustment_proposals``：动态计划调整的待确认方案，提案阶段
  不产生任何计划版本，确认后才由 Service 生效；
- 新增 ``review_requests``：幂等的复习申请记录，不伪造复习任务。

SQLite 不支持 ``ALTER TABLE ADD CONSTRAINT``，三列及其外键通过
``batch_alter_table`` 的 copy-and-move 重建一次创建；downgrade 同样用
batch 重建去掉三列及其外键。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e6ec48dafbe"
down_revision: Union[str, None] = "d8cfe871faa5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plan_adjustment_proposals",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("triggers", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("preview", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resulting_version_number", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'confirmed', 'rejected')",
            name=op.f("ck_plan_adjustment_proposals_ck_plan_adjustment_proposals_status"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["learning_plans.id"],
            name=op.f("fk_plan_adjustment_proposals_plan_id_learning_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_plan_adjustment_proposals_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_adjustment_proposals")),
    )
    op.create_index(
        op.f("ix_plan_adjustment_proposals_plan_id"),
        "plan_adjustment_proposals", ["plan_id"], unique=False,
    )
    op.create_index(
        op.f("ix_plan_adjustment_proposals_status"),
        "plan_adjustment_proposals", ["status"], unique=False,
    )
    op.create_index(
        op.f("ix_plan_adjustment_proposals_user_id"),
        "plan_adjustment_proposals", ["user_id"], unique=False,
    )

    op.create_table(
        "review_requests",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_point_id", sa.Uuid(), nullable=False),
        sa.Column("request_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("trigger", sa.String(length=64), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'scheduled', 'completed')",
            name=op.f("ck_review_requests_ck_review_requests_status"),
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_point_id"], ["knowledge_points.id"],
            name=op.f("fk_review_requests_knowledge_point_id_knowledge_points"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_review_requests_user_id_users"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_requests")),
        sa.UniqueConstraint(
            "user_id", "knowledge_point_id", "request_date",
            name="uq_review_requests_user_kp_date",
        ),
    )
    op.create_index(
        op.f("ix_review_requests_knowledge_point_id"),
        "review_requests", ["knowledge_point_id"], unique=False,
    )
    op.create_index(
        op.f("ix_review_requests_request_date"),
        "review_requests", ["request_date"], unique=False,
    )
    op.create_index(
        op.f("ix_review_requests_status"),
        "review_requests", ["status"], unique=False,
    )
    op.create_index(
        op.f("ix_review_requests_user_id"),
        "review_requests", ["user_id"], unique=False,
    )

    # 计划版本记录生成时的八类输入快照（纯 JSON，无外键，可直接 ADD COLUMN）
    op.add_column(
        "learning_plan_versions",
        sa.Column("plan_context", sa.JSON(), nullable=True),
    )

    # SQLite 不支持 ALTER TABLE ADD CONSTRAINT，外键与新增列一起走 batch
    # copy-and-move 重建；recreate="auto" 会在检测到 create_foreign_key 时
    # 自动选择重建，既有唯一约束 / CHECK / 索引由反射保留。
    with op.batch_alter_table("daily_tasks") as batch:
        batch.add_column(sa.Column("course_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("chapter_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("lesson_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            op.f("fk_daily_tasks_course_id_courses"),
            "courses", ["course_id"], ["id"], ondelete="CASCADE",
        )
        batch.create_foreign_key(
            op.f("fk_daily_tasks_chapter_id_chapters"),
            "chapters", ["chapter_id"], ["id"], ondelete="CASCADE",
        )
        batch.create_foreign_key(
            op.f("fk_daily_tasks_lesson_id_lessons"),
            "lessons", ["lesson_id"], ["id"], ondelete="CASCADE",
        )
    op.create_index(
        op.f("ix_daily_tasks_chapter_id"), "daily_tasks", ["chapter_id"], unique=False
    )
    op.create_index(
        op.f("ix_daily_tasks_course_id"), "daily_tasks", ["course_id"], unique=False
    )
    op.create_index(
        op.f("ix_daily_tasks_lesson_id"), "daily_tasks", ["lesson_id"], unique=False
    )

    _backfill_daily_task_refs()


def _backfill_daily_task_refs() -> None:
    """按知识点归属回填历史任务的课程/章节/课时引用（可重入）。

    课时归属取 ``lesson_knowledge_points``；老数据若确实没有归属课时则保持
    NULL，不猜测、不伪造。新任务一律由 DailyTaskService 填齐四个标识。
    """
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT dt.id, ch.course_id, kp.chapter_id, lkp.lesson_id "
            "FROM daily_tasks dt "
            "JOIN knowledge_points kp ON kp.id = dt.knowledge_point_id "
            "JOIN chapters ch ON ch.id = kp.chapter_id "
            "LEFT JOIN lesson_knowledge_points lkp "
            "  ON lkp.knowledge_point_id = kp.id"
        )
    ).all()
    for task_id, course_id, chapter_id, lesson_id in rows:
        bind.execute(
            sa.text(
                "UPDATE daily_tasks SET course_id = :course_id, "
                "chapter_id = :chapter_id, lesson_id = :lesson_id "
                "WHERE id = :task_id"
            ),
            {
                "course_id": course_id,
                "chapter_id": chapter_id,
                "lesson_id": lesson_id,
                "task_id": task_id,
            },
        )


def downgrade() -> None:
    with op.batch_alter_table("learning_plan_versions") as batch:
        batch.drop_column("plan_context")
    op.drop_index(op.f("ix_daily_tasks_lesson_id"), table_name="daily_tasks")
    op.drop_index(op.f("ix_daily_tasks_course_id"), table_name="daily_tasks")
    op.drop_index(op.f("ix_daily_tasks_chapter_id"), table_name="daily_tasks")
    # batch 重建会同时移除三列上的内联外键，SQLite 不支持单独 DROP CONSTRAINT
    with op.batch_alter_table("daily_tasks") as batch:
        batch.drop_column("lesson_id")
        batch.drop_column("chapter_id")
        batch.drop_column("course_id")

    op.drop_index(op.f("ix_review_requests_user_id"), table_name="review_requests")
    op.drop_index(op.f("ix_review_requests_status"), table_name="review_requests")
    op.drop_index(
        op.f("ix_review_requests_request_date"), table_name="review_requests"
    )
    op.drop_index(
        op.f("ix_review_requests_knowledge_point_id"), table_name="review_requests"
    )
    op.drop_table("review_requests")
    op.drop_index(
        op.f("ix_plan_adjustment_proposals_user_id"),
        table_name="plan_adjustment_proposals",
    )
    op.drop_index(
        op.f("ix_plan_adjustment_proposals_status"),
        table_name="plan_adjustment_proposals",
    )
    op.drop_index(
        op.f("ix_plan_adjustment_proposals_plan_id"),
        table_name="plan_adjustment_proposals",
    )
    op.drop_table("plan_adjustment_proposals")
