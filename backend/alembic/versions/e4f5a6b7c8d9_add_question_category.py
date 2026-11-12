"""阶段 3：题库补题目分类（基础理解 / 代码阅读 / 应用练习）

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-11-08

只做一件事：给 question_bank 增加 category 列。
- ADD COLUMN，不重建表，不触碰答题记录、错题、复习任务；
- 存量 93 道内置题按题型映射一次性回填，升级后分类不会留空；
- 列保持可空，避免极早期或外部导入的数据因缺少分类而写不进去。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 题型 → 分类：与 app.models.quiz.CATEGORY_BY_QUESTION_TYPE 保持一致。
# 迁移脚本内联一份，避免历史迁移依赖会继续变化的业务代码。
CATEGORY_BY_TYPE: dict[str, str] = {
    "single_choice": "基础理解",
    "multiple_choice": "基础理解",
    "true_false": "基础理解",
    "fill_blank": "基础理解",
    "code_analysis": "代码阅读",
    "code_writing": "应用练习",
    "short_answer": "应用练习",
}


def upgrade() -> None:
    existing = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("question_bank")
    }
    if "category" not in existing:
        op.add_column(
            "question_bank",
            sa.Column("category", sa.String(length=16), nullable=True),
        )

    # 回填存量题目：按题型给出默认分类
    for question_type, category in CATEGORY_BY_TYPE.items():
        op.execute(
            sa.text(
                "UPDATE question_bank SET category = :category "
                "WHERE category IS NULL AND question_type = :question_type"
            ).bindparams(category=category, question_type=question_type)
        )


def downgrade() -> None:
    existing = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("question_bank")
    }
    if "category" in existing:
        with op.batch_alter_table("question_bank") as batch:
            batch.drop_column("category")
