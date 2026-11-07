"""学习档案业务层（PRD 5.1：学习目标、当前基础、每日可学习时间、学习偏好）。"""

from sqlalchemy.orm import Session

from app.models.user import User, UserProfile
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileOut, ProfileUpdate

# 单用户产品（PRD）：本地默认账号。正式「首次启动初始化档案」流程由后续阶段实现，
# 当前阶段读取档案时懒创建该账号，保证接口可直接保存与读取。
DEFAULT_USERNAME = "local"


class ProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ProfileRepository(db)

    def get_profile(self) -> ProfileOut:
        user = self._get_or_create_user()
        return self._to_out(user)

    def update_profile(self, payload: ProfileUpdate) -> ProfileOut:
        user = self._get_or_create_user()
        if user.profile is None:
            user.profile = UserProfile()
            self.db.flush()
        # exclude_unset：PUT 部分更新语义，未提交字段保持不变
        self.repo.update_profile(user.profile, payload.model_dump(exclude_unset=True))
        self.db.commit()
        return self._to_out(user)

    def _get_or_create_user(self) -> User:
        user = self.repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user

    @staticmethod
    def _to_out(user: User) -> ProfileOut:
        profile = user.profile
        return ProfileOut(
            username=user.username,
            learning_goal=profile.learning_goal,
            current_level=profile.current_level,
            daily_study_minutes=profile.daily_study_minutes,
            learning_preferences=profile.learning_preferences,
        )
