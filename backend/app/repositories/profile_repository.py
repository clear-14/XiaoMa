"""学习档案数据访问层。"""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user import User, UserProfile


class ProfileRepository:
    """用户与其学习档案（user_profiles）的数据库读写。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_with_profile(self, username: str) -> User | None:
        """按用户名查用户（含档案，单用户产品当前仅默认账号）。"""
        stmt = (
            select(User)
            .where(User.username == username, User.deleted_at.is_(None))
            .options(joinedload(User.profile))
        )
        return self.db.scalars(stmt).first()

    def create_user_with_profile(self, username: str) -> User:
        """创建用户并附带空白学习档案。"""
        user = User(username=username, profile=UserProfile())
        self.db.add(user)
        self.db.flush()
        return user

    def update_profile(self, profile: UserProfile, data: dict) -> None:
        """按字段字典更新学习档案（调用方保证字段名合法）。"""
        for key, value in data.items():
            setattr(profile, key, value)
        self.db.flush()
