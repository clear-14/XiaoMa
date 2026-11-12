"""V1.4 批次 5：从真实业务结果构造 v1 卡片（Agent 侧纯函数层）。

数据来源只有 ``AgentToolbox`` 经 Service 层返回的业务对象，不从聊天文本推断
掌握状态、成绩或题目答案（PRD §5.4 / §5.6 / §6 原则 1）。

约束：
- 每张卡片生成后都用 ``validate_card_payload()`` 自检；必备字段缺失或类型不符
  时返回 ``None``，宁可不发卡片，也不下发会被前端降级成 ``error_card`` 的半成品；
- 未提交的测验不下发 ``correct_answer`` / ``explanation`` / ``score`` /
  ``is_correct``，答案与评分只由后端在结果卡片给出（PRD §5.4）；
- 错题卡片不下发未作答复习题的正确答案与解析，避免聊天记录剧透；
- 本模块不执行任何写操作。计划确认、测验提交等重要修改仍只走 REST 接口，
  Agent 工具清单中的 ``FORBIDDEN_TOOL_NAMES`` 保持不变。
"""

from __future__ import annotations

from typing import Any

from app.agent.contracts import IntentResult, LearningContext, ToolResult
from app.schemas.cards import CARD_VERSION, validate_card_payload
from app.schemas.daily_task import TodayTasksOut
from app.schemas.learning_overview import LearningOverviewOut
from app.schemas.phase6 import PlanAdjustmentProposalOut
from app.schemas.plan import CurrentPlanOut
from app.schemas.quiz import MistakeOut, QuizAttemptOut


def _card(card_type: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """统一出口：只有字段表校验通过的完整卡片才会被下发。"""
    if validate_card_payload(card_type, payload) is not None:
        return None
    return {
        "card_version": CARD_VERSION,
        "type": card_type,
        "payload": payload,
    }


def _one(card: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [card] if card is not None else []


# ---------------------------------------------------------------- 各类卡片

def build_task_card(data: object) -> dict[str, Any] | None:
    """今日任务卡片：取第一条待学任务，全部字段来自 ``TodayTasksOut``。"""
    if not isinstance(data, TodayTasksOut) or not data.tasks:
        return None
    task = next(
        (item for item in data.tasks if item.status in ("pending", "learning")),
        data.tasks[0],
    )
    kp = task.knowledge_point
    return _card(
        "task_card",
        {
            "title": kp.name,
            "knowledge_point_code": kp.code,
            "knowledge_point_name": kp.name,
            "learning_goal": kp.learning_goal,
            "estimated_minutes": kp.estimated_minutes,
            "task_id": str(task.id),
            "day_index": task.day_index,
            "chapter_title": kp.chapter_title,
            "status": task.status,
            "mastery_status": task.mastery_status,
        },
    )


def build_plan_card(data: object) -> dict[str, Any] | None:
    """学习计划卡片：生效版本优先，其次待确认草案。"""
    if not isinstance(data, CurrentPlanOut):
        return None
    version = data.current_version or data.pending_version
    if version is None:
        return None
    return _card(
        "plan_card",
        {
            "plan_id": str(data.id),
            "course_name": data.course_name,
            "version_number": version.version_number,
            "items": [
                {
                    "day_index": item.day_index,
                    "knowledge_point_name": item.knowledge_point_name,
                    "estimated_minutes": item.estimated_minutes,
                    "status": item.status,
                }
                for item in version.items
            ],
            "learning_goal": version.learning_goal,
            "daily_study_minutes": version.daily_study_minutes,
            "expected_duration_days": version.expected_duration_days,
            "status": version.status,
        },
    )


def build_progress_card(data: object) -> dict[str, Any] | None:
    """学习进度卡片：所有数字直接取 ``LearningOverviewOut`` 原值，不自行推算。"""
    if not isinstance(data, LearningOverviewOut):
        return None
    # 课程名只作展示标签；无生效计划时用中性文案，不推断任何业务状态。
    course_name = data.plan_course_name or "当前课程"
    return _card(
        "progress_card",
        {
            "course_name": course_name,
            "mastered_count": data.mastered_count,
            "learning_count": data.learning_count,
            "pending_verification_count": data.pending_verification_count,
            "review_due_count": data.review_due_count,
            "plan_progress_percent": data.plan_progress_percent,
            "chapter_title": (
                data.chapters[0].chapter_title if data.chapters else None
            ),
        },
    )


def build_plan_change_card(data: object) -> dict[str, Any] | None:
    """计划调整建议卡片：只展示待确认提案，确认动作仍走 REST。"""
    if not isinstance(data, PlanAdjustmentProposalOut):
        return None
    preview = data.preview if isinstance(data.preview, dict) else {}
    impacts = preview.get("impacts", [])
    return _card(
        "plan_change_card",
        {
            "proposal_id": str(data.id),
            "changes": data.changes,
            "reason": data.reason,
            "impacts": impacts if isinstance(impacts, list) else [],
            "preview": preview,
            "requires_confirmation": data.requires_confirmation,
            "status": data.status,
        },
    )


def build_quiz_card(data: object) -> dict[str, Any] | None:
    """测验题目卡片：只下发未提交测验的题干、题型与选项。"""
    if not isinstance(data, QuizAttemptOut) or data.status == "submitted":
        return None
    questions = []
    for question in data.questions:
        options = [
            {"key": option.key, "text": option.text}
            for option in (question.options or [])
        ]
        questions.append(
            {
                "id": str(question.id),
                "stem": question.stem,
                "question_type": question.question_type,
                "options": options,
            }
        )
    return _card(
        "quiz_card",
        {
            "attempt_id": str(data.id),
            "questions": questions,
            "scope_name": data.scope_name,
            "total_points": data.total_points,
        },
    )


def build_quiz_result_card(data: object) -> dict[str, Any] | None:
    """测验结果卡片：只在后端已评分后生成，答案与解析来自评分结果。"""
    if (
        not isinstance(data, QuizAttemptOut)
        or data.status != "submitted"
        or data.score is None
    ):
        return None
    questions = [
        {
            "id": str(question.id),
            "stem": question.stem,
            "user_answer": question.user_answer,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation,
            "score": question.score,
            "is_correct": question.is_correct,
        }
        for question in data.questions
    ]
    return _card(
        "quiz_result_card",
        {
            "attempt_id": str(data.id),
            "score": data.score,
            "total_points": data.total_points,
            "questions": questions,
            "mastery_updates": [
                {
                    "knowledge_point_name": item.knowledge_point_name,
                    "achieved": item.achieved,
                    "status_label": item.status_label,
                }
                for item in data.mastery_updates
            ],
            "mastered_count": sum(
                1 for item in data.mastery_updates if item.achieved
            ),
        },
    )


def build_mistake_card(data: object) -> dict[str, Any] | None:
    """错题复习卡片：取第一条待复习错题，携带真实复习任务标识。"""
    if not isinstance(data, list) or not data:
        return None
    mistake = next(
        (
            item
            for item in data
            if isinstance(item, MistakeOut) and item.review_status == "pending"
        ),
        None,
    )
    if mistake is None:
        return None
    return _card(
        "mistake_card",
        {
            "mistake_id": str(mistake.id),
            "question_stem": mistake.question.stem,
            "knowledge_point_name": mistake.knowledge_point.name,
            "last_answer": mistake.last_answer,
            "review_task_id": (
                str(mistake.pending_review_task_id)
                if mistake.pending_review_task_id is not None
                else None
            ),
            "review_status": mistake.review_status,
            "attempt_count": mistake.attempt_count,
            "next_review_at": (
                mistake.next_review_at.isoformat()
                if mistake.next_review_at is not None
                else None
            ),
        },
    )


def build_lesson_card(
    context: LearningContext | None, reply: str
) -> dict[str, Any] | None:
    """知识点讲解卡片：讲解正文来自本轮模型输出，知识点标识来自学习上下文。"""
    if context is None or context.knowledge_point is None:
        return None
    explanation = (reply or "").strip()
    if not explanation:
        return None
    kp = context.knowledge_point
    return _card(
        "lesson_card",
        {
            "knowledge_point_code": kp.code,
            "knowledge_point_name": kp.name,
            "explanation": explanation,
            "chapter_title": kp.chapter_title,
        },
    )


# ---------------------------------------------------------------- 状态分发

def _data(
    results: dict[str, ToolResult], key: str
) -> object | None:
    """只取成功工具结果；失败 / 暂不可用一律不产卡。"""
    result = results.get(key)
    if not isinstance(result, ToolResult):
        return None
    if not result.ok or result.status != "ok":
        return None
    return result.data


def _planning_cards(
    sub_intent: str, results: dict[str, ToolResult]
) -> list[dict[str, Any]]:
    if sub_intent == "today_tasks":
        return _one(build_task_card(_data(results, "today_tasks")))
    if sub_intent == "plan_overview":
        return _one(build_plan_card(_data(results, "plan")))
    if sub_intent == "progress":
        return _one(build_progress_card(_data(results, "progress")))
    if sub_intent == "adjust_plan":
        return _one(build_plan_change_card(_data(results, "adjust")))
    return []


def _quiz_cards(
    sub_intent: str, results: dict[str, ToolResult]
) -> list[dict[str, Any]]:
    if sub_intent == "generate_quiz":
        attempt = _data(results, "quiz")
        return _one(build_quiz_card(attempt)) or _one(
            build_quiz_result_card(attempt)
        )
    if sub_intent == "quiz_result":
        # 批次 8：聊天可查看最近一次已提交测验的结果，9 类卡片由此全部可达。
        return _one(build_quiz_result_card(_data(results, "quiz_result")))
    # 测验历史是列表统计，不构成一次可交互的业务对象，不编造卡片。
    return []


def _review_cards(results: dict[str, ToolResult]) -> list[dict[str, Any]]:
    return _one(build_mistake_card(_data(results, "mistakes")))


def cards_for_state(
    *,
    intent: IntentResult,
    tool_results: dict[str, ToolResult] | None,
    context: LearningContext | None,
    reply: str,
    reply_scope: str = "",
) -> list[dict[str, Any]]:
    """按意图把本轮真实工具结果转成 0..n 张完整卡片。

    这是 Agent 产出卡片的唯一入口；由主图的 ``finalize`` 节点调用，
    避免嵌套子图的 custom 事件无法冒泡到父图流。

    ``reply_scope`` 为 ``"out_of_scope"`` 时表示模型本轮只是在说明「这个问题
    不在当前知识点范围内」，属于范围说明而不是讲解正文，因此不下发讲解卡片。
    """
    results = tool_results or {}
    if intent.intent == "planning":
        return _planning_cards(intent.sub_intent, results)
    if intent.intent == "quiz":
        return _quiz_cards(intent.sub_intent, results)
    if intent.intent == "review":
        return _review_cards(results)
    if intent.intent == "teaching":
        if reply_scope == "out_of_scope":
            return []
        return _one(build_lesson_card(context, reply))
    return []
