"""add conversations messages learning sessions

Revision ID: e8b1c4d7a902
Revises: d0b5a8fe0785
Create Date: 2026-11-07 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8b1c4d7a902'
down_revision: Union[str, None] = 'd0b5a8fe0785'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('conversations',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=True),
    sa.Column('knowledge_point_id', sa.Uuid(), nullable=True),
    sa.Column('daily_task_id', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['daily_task_id'], ['daily_tasks.id'], name=op.f('fk_conversations_daily_task_id_daily_tasks'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['knowledge_point_id'], ['knowledge_points.id'], name=op.f('fk_conversations_knowledge_point_id_knowledge_points'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_conversations_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_conversations'))
    )
    op.create_index(op.f('ix_conversations_daily_task_id'), 'conversations', ['daily_task_id'], unique=False)
    op.create_index(op.f('ix_conversations_deleted_at'), 'conversations', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_conversations_knowledge_point_id'), 'conversations', ['knowledge_point_id'], unique=False)
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)

    op.create_table('messages',
    sa.Column('conversation_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('error_message', sa.String(length=500), nullable=True),
    sa.Column('model_name', sa.String(length=128), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("role IN ('user', 'assistant')", name=op.f('ck_messages_role')),
    sa.CheckConstraint("status IN ('completed', 'error')", name=op.f('ck_messages_status')),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name=op.f('fk_messages_conversation_id_conversations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_messages'))
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)

    op.create_table('learning_sessions',
    sa.Column('conversation_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('knowledge_point_id', sa.Uuid(), nullable=True),
    sa.Column('daily_task_id', sa.Uuid(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('message_count', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name=op.f('fk_learning_sessions_conversation_id_conversations'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['daily_task_id'], ['daily_tasks.id'], name=op.f('fk_learning_sessions_daily_task_id_daily_tasks'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['knowledge_point_id'], ['knowledge_points.id'], name=op.f('fk_learning_sessions_knowledge_point_id_knowledge_points'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_learning_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_learning_sessions')),
    sa.UniqueConstraint('conversation_id', name='conversation_session')
    )
    op.create_index(op.f('ix_learning_sessions_conversation_id'), 'learning_sessions', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_learning_sessions_user_id'), 'learning_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_learning_sessions_user_id'), table_name='learning_sessions')
    op.drop_index(op.f('ix_learning_sessions_conversation_id'), table_name='learning_sessions')
    op.drop_table('learning_sessions')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_knowledge_point_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_deleted_at'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_daily_task_id'), table_name='conversations')
    op.drop_table('conversations')
