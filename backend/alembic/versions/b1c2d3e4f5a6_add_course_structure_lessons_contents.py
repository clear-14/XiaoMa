"""add course structure: metadata, lessons, contents, exercises, versions

Revision ID: b1c2d3e4f5a6
Revises: 5a9439936da5
Create Date: 2026-11-08 14:20:00.000000

阶段 1：课程数据结构升级。

升级策略（严格遵守「不重建数据库、不删除已有用户数据、不清空学习历史」）：
- ``courses`` 只做 ADD COLUMN（SQLite 原生支持），不重建表，不影响 ``chapters`` 外键；
- 新增 5 张表：lessons、course_contents、exercises、course_versions、
  lesson_knowledge_points（知识点与课时一对一归属，knowledge_point_id 唯一）；
- 不改动 ``knowledge_points`` 的既有结构（保留 chapter_id），避免重建被 7 张表引用的表；
- 为每个既有章节幂等补一条默认课时（code = 章节 code + '-lesson-01'），
  并把该章节下既有知识点全部关联到默认课时，保证升级后课时层不空、旧数据不丢。

降级会删除新增表与新增列，并恢复课程元数据为升级前状态（列删除即回滚）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = '5a9439936da5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COURSE_NEW_COLUMNS: tuple[str, ...] = (
    "learning_objectives",
    "direction",
    "difficulty",
    "recommended_level",
    "estimated_minutes",
    "version",
    "publish_status",
    "sort_order",
)


def upgrade() -> None:
    # ---- 1. 课程元数据列（ADD COLUMN，不重建 courses 表）----
    op.add_column("courses", sa.Column("learning_objectives", sa.Text(), nullable=True))
    op.add_column("courses", sa.Column("direction", sa.String(length=64), nullable=True))
    op.add_column("courses", sa.Column("difficulty", sa.String(length=16), nullable=True))
    op.add_column(
        "courses", sa.Column("recommended_level", sa.String(length=16), nullable=True)
    )
    op.add_column("courses", sa.Column("estimated_minutes", sa.Integer(), nullable=True))
    op.add_column(
        "courses",
        sa.Column(
            "version",
            sa.String(length=32),
            nullable=False,
            server_default="1.0.0",
        ),
    )
    op.add_column(
        "courses",
        sa.Column(
            "publish_status",
            sa.String(length=16),
            nullable=False,
            server_default="published",
        ),
    )
    op.add_column(
        "courses",
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index(op.f("ix_courses_direction"), "courses", ["direction"], unique=False)
    op.create_index(
        op.f("ix_courses_publish_status"), "courses", ["publish_status"], unique=False
    )

    # ---- 2. 课时 ----
    op.create_table(
        "lessons",
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("difficulty", sa.String(length=16), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "difficulty IS NULL OR difficulty IN "
            "('beginner', 'intermediate', 'advanced')",
            name=op.f("ck_lessons_difficulty"),
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            name=op.f("fk_lessons_chapter_id_chapters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lessons")),
        sa.UniqueConstraint("code", name=op.f("uq_lessons_code")),
    )
    op.create_index(op.f("ix_lessons_chapter_id"), "lessons", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_lessons_deleted_at"), "lessons", ["deleted_at"], unique=False)

    # ---- 3. 课时教学内容（一个课时一份）----
    op.create_table(
        "course_contents",
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("learning_objectives", sa.Text(), nullable=True),
        sa.Column("concept_explanation", sa.Text(), nullable=True),
        sa.Column("syntax_explanation", sa.Text(), nullable=True),
        sa.Column("example_code", sa.Text(), nullable=True),
        sa.Column("code_explanation", sa.Text(), nullable=True),
        sa.Column("common_mistakes", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_course_contents_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_contents")),
    )
    op.create_index(
        op.f("ix_course_contents_lesson_id"),
        "course_contents",
        ["lesson_id"],
        unique=True,
    )

    # ---- 4. 知识点练习 ----
    op.create_table(
        "exercises",
        sa.Column("knowledge_point_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("exercise_type", sa.String(length=32), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("reference_answer", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "exercise_type IN "
            "('coding', 'choice', 'fill_blank', 'short_answer', 'project')",
            name=op.f("ck_exercises_exercise_type"),
        ),
        sa.CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name=op.f("ck_exercises_difficulty"),
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_point_id"],
            ["knowledge_points.id"],
            name=op.f("fk_exercises_knowledge_point_id_knowledge_points"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercises")),
        sa.UniqueConstraint("code", name=op.f("uq_exercises_code")),
    )
    op.create_index(
        op.f("ix_exercises_knowledge_point_id"),
        "exercises",
        ["knowledge_point_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exercises_deleted_at"), "exercises", ["deleted_at"], unique=False
    )

    # ---- 5. 知识点 ⇄ 课时 一对一归属 ----
    op.create_table(
        "lesson_knowledge_points",
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_point_id", sa.Uuid(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_lesson_knowledge_points_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_point_id"],
            ["knowledge_points.id"],
            name=op.f("fk_lesson_knowledge_points_knowledge_point_id_knowledge_points"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "lesson_id",
            "knowledge_point_id",
            name=op.f("pk_lesson_knowledge_points"),
        ),
        sa.UniqueConstraint(
            "knowledge_point_id", name="lesson_kp_knowledge_point"
        ),
    )
    op.create_index(
        op.f("ix_lesson_knowledge_points_knowledge_point_id"),
        "lesson_knowledge_points",
        ["knowledge_point_id"],
        unique=False,
    )

    # ---- 6. 课程版本快照 ----
    op.create_table(
        "course_versions",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_course_versions_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_versions")),
        sa.UniqueConstraint("course_id", "version", name="course_version"),
    )
    op.create_index(
        op.f("ix_course_versions_course_id"),
        "course_versions",
        ["course_id"],
        unique=False,
    )

    # ---- 7. 既有数据回填（只 UPDATE / INSERT，不删除任何行）----
    # 7.1 课程元数据：方向/难度/推荐等级按课程 code 前缀识别，未识别课程保持 NULL；
    #     预计时长按既有知识点时长汇总（不改动知识点本身）。
    op.execute(
        sa.text(
            """
            UPDATE courses
            SET direction = COALESCE(direction, 'python'),
                difficulty = COALESCE(difficulty, 'beginner'),
                recommended_level = COALESCE(recommended_level, 'L0')
            WHERE direction IS NULL AND code LIKE 'python%'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE courses
            SET estimated_minutes = COALESCE(
                estimated_minutes,
                (
                    SELECT COALESCE(SUM(kp.estimated_minutes), 0)
                    FROM knowledge_points kp
                    JOIN chapters ch ON kp.chapter_id = ch.id
                    WHERE ch.course_id = courses.id AND kp.deleted_at IS NULL
                )
            )
            """
        )
    )

    # 7.2 每个既有章节补一条默认课时（幂等：按 code 判重，可重复执行）
    op.execute(
        sa.text(
            """
            INSERT INTO lessons (
                id, chapter_id, code, title, description, difficulty,
                estimated_minutes, order_index, created_at, updated_at
            )
            SELECT
                lower(hex(randomblob(16))),
                ch.id,
                ch.code || '-lesson-01',
                ch.title,
                ch.description,
                NULL,
                NULL,
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM chapters ch
            WHERE ch.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM lessons l
                  WHERE l.chapter_id = ch.id
                    AND l.code = ch.code || '-lesson-01'
              )
            """
        )
    )

    # 7.3 把既有知识点归属到所属章节的默认课时（一个知识点只挂一次）
    op.execute(
        sa.text(
            """
            INSERT INTO lesson_knowledge_points (lesson_id, knowledge_point_id, order_index)
            SELECT l.id, kp.id, kp.order_index
            FROM knowledge_points kp
            JOIN chapters ch ON kp.chapter_id = ch.id
            JOIN lessons l
              ON l.chapter_id = ch.id
             AND l.code = ch.code || '-lesson-01'
            WHERE kp.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM lesson_knowledge_points x
                  WHERE x.knowledge_point_id = kp.id
              )
            """
        )
    )


def downgrade() -> None:
    # ---- 1. 删除归属与版本、练习、教学内容、课时（先删子表）----
    op.drop_index(
        op.f("ix_lesson_knowledge_points_knowledge_point_id"),
        table_name="lesson_knowledge_points",
    )
    op.drop_table("lesson_knowledge_points")

    op.drop_index(op.f("ix_course_versions_course_id"), table_name="course_versions")
    op.drop_table("course_versions")

    op.drop_index(op.f("ix_exercises_deleted_at"), table_name="exercises")
    op.drop_index(op.f("ix_exercises_knowledge_point_id"), table_name="exercises")
    op.drop_table("exercises")

    op.drop_index(
        op.f("ix_course_contents_lesson_id"), table_name="course_contents"
    )
    op.drop_table("course_contents")

    op.drop_index(op.f("ix_lessons_deleted_at"), table_name="lessons")
    op.drop_index(op.f("ix_lessons_chapter_id"), table_name="lessons")
    op.drop_table("lessons")

    # ---- 2. 回滚课程元数据列（SQLite 3.35+ 支持 DROP COLUMN）----
    op.drop_index(op.f("ix_courses_publish_status"), table_name="courses")
    op.drop_index(op.f("ix_courses_direction"), table_name="courses")
    op.drop_column("courses", "sort_order")
    op.drop_column("courses", "publish_status")
    op.drop_column("courses", "version")
    op.drop_column("courses", "estimated_minutes")
    op.drop_column("courses", "recommended_level")
    op.drop_column("courses", "difficulty")
    op.drop_column("courses", "direction")
    op.drop_column("courses", "learning_objectives")
