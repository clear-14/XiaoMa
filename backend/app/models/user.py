"""用户与学习档案模型。"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class User(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """用户账号。

    当前产品为单用户，但保留独立用户表，方便未来扩展多用户。
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    profile: Mapped[UserProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserProfile(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """用户学习档案：学习目标、当前基础、每日可学习时间与学习偏好（PRD 5.1）。"""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    learning_goal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 基础水平：L0 零基础 / L1 碎片化 / L2 转行（PRD 2）
    current_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    daily_study_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    learning_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")
