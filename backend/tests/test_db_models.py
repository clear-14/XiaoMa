"""基础表写入/读取测试。"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.mixins import utc_now
from app.models.model_config import ModelConfig
from app.models.system import SystemSetting
from app.models.user import User, UserProfile


def test_user_and_profile_write_read(db_session) -> None:
    """用户与档案应能写入并读取，UUID 主键与时间戳应自动生成。"""
    user = User(username="xiaoma")
    db_session.add(user)
    db_session.flush()
    assert isinstance(user.id, uuid.UUID)
    assert isinstance(user.created_at, datetime)

    db_session.add(
        UserProfile(
            user_id=user.id,
            learning_goal="学会 Python 基础",
            current_level="L0",
            daily_study_minutes=30,
            learning_preferences={"style": "循序渐进"},
        )
    )
    db_session.commit()

    loaded = db_session.get(User, user.id)
    assert loaded is not None
    assert loaded.username == "xiaoma"
    assert loaded.profile is not None
    assert loaded.profile.learning_goal == "学会 Python 基础"
    assert loaded.profile.daily_study_minutes == 30


def test_updated_at_changes_on_update(db_session) -> None:
    """更新记录后 updated_at 应刷新。"""
    user = User(username="updater")
    db_session.add(user)
    db_session.commit()
    first_updated = user.updated_at

    user.username = "updater-2"
    db_session.commit()
    db_session.refresh(user)
    assert user.updated_at >= first_updated


def test_system_setting_write_read(db_session) -> None:
    """系统设置键值应能写入读取。"""
    db_session.add(SystemSetting(key="onboarding_done", value="true"))
    db_session.commit()
    row = db_session.query(SystemSetting).filter_by(key="onboarding_done").one()
    assert row.value == "true"


def test_model_config_write_read(db_session) -> None:
    """模型配置应能写入读取。"""
    db_session.add(
        ModelConfig(
            name="DeepSeek 默认",
            provider="deepseek",
            model_name="deepseek-chat",
            is_default=True,
        )
    )
    db_session.commit()
    rows = db_session.query(ModelConfig).all()
    assert len(rows) == 1
    assert rows[0].is_default is True


def test_soft_delete_sets_deleted_at(db_session) -> None:
    """软删除应只写入 deleted_at 标记，记录仍在库中。"""
    user = User(username="to-delete")
    db_session.add(user)
    db_session.commit()

    user.deleted_at = utc_now()
    db_session.commit()
    loaded = db_session.get(User, user.id)
    assert loaded is not None
    assert loaded.deleted_at is not None


def test_unique_username_constraint(db_session) -> None:
    """重复 username 应触发唯一约束。"""
    db_session.add(User(username="dup"))
    db_session.commit()
    db_session.add(User(username="dup"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_cascade_delete(db_session) -> None:
    """删除用户时其档案应级联删除。"""
    user = User(username="cascade")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserProfile(user_id=user.id, learning_goal="x"))
    db_session.commit()

    profile_id = user.profile.id
    db_session.delete(user)
    db_session.commit()
    assert db_session.get(UserProfile, profile_id) is None
