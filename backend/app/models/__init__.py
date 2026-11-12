"""模型汇总导入：确保全部模型注册到 Base.metadata（Alembic autogenerate 依赖此导入）。"""

from app.models.conversation import Conversation, LearningSession, Message
from app.models.course import (
    Chapter,
    Course,
    CourseContent,
    CourseDirection,
    CourseDirectionLink,
    CourseKnowledgePointPrerequisite,
    CoursePrerequisite,
    CourseVersion,
    Exercise,
    KnowledgePoint,
    KnowledgePointPrerequisite,
    Lesson,
    LessonKnowledgePoint,
)
from app.models.daily_task import DailyTask
from app.models.learning_plan import LearningPlan, LearningPlanItem, LearningPlanVersion
from app.models.learning_profile import LearningProfile
from app.models.mastery import ExerciseAttempt, KnowledgeMastery, MasteryEvidence
from app.models.model_config import ModelConfig
from app.models.phase6 import PlanAdjustmentProposal, ReviewRequest
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
    "CourseContent",
    "CourseDirection",
    "CourseDirectionLink",
    "CourseKnowledgePointPrerequisite",
    "CoursePrerequisite",
    "CourseVersion",
    "DailyTask",
    "Exercise",
    "ExerciseAttempt",
    "KnowledgeMastery",
    "KnowledgePoint",
    "KnowledgePointPrerequisite",
    "LearningPlan",
    "LearningPlanItem",
    "LearningPlanVersion",
    "LearningProfile",
    "LearningSession",
    "Lesson",
    "LessonKnowledgePoint",
    "MasteryEvidence",
    "Message",
    "Mistake",
    "ModelConfig",
    "PlanAdjustmentProposal",
    "Question",
    "QuizAnswer",
    "QuizAttempt",
    "ReviewRequest",
    "ReviewTask",
    "SystemSetting",
    "User",
    "UserProfile",
]
