"""模型汇总导入：确保全部模型注册到 Base.metadata（Alembic autogenerate 依赖此导入）。"""

from app.models.conversation import Conversation, LearningSession, Message
from app.models.course import Chapter, Course, KnowledgePoint, KnowledgePointPrerequisite
from app.models.daily_task import DailyTask
from app.models.learning_plan import LearningPlan, LearningPlanItem, LearningPlanVersion
from app.models.learning_profile import LearningProfile
from app.models.model_config import ModelConfig
from app.models.quiz import (
    Mistake,
    Question,
    QuizAnswer,
    QuizAttempt,
    ReviewTask,
)
from app.models.system import SystemSetting
from app.models.user import User, UserProfile

__all__ = [
    "Chapter",
    "Conversation",
    "Course",
    "DailyTask",
    "KnowledgePoint",
    "KnowledgePointPrerequisite",
    "LearningPlan",
    "LearningPlanItem",
    "LearningPlanVersion",
    "LearningProfile",
    "LearningSession",
    "Message",
    "Mistake",
    "ModelConfig",
    "Question",
    "QuizAnswer",
    "QuizAttempt",
    "ReviewTask",
    "SystemSetting",
    "User",
    "UserProfile",
]
