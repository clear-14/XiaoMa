"""Quiz Subgraph：生成测验与查看测验记录。

输入：用户消息、学习上下文、Quiz 意图（generate_quiz / quiz_history）。
输出：reply、tool_results、result_status。

所有组卷与范围校验都由 QuizService 完成：
- 未学习的知识点不会进入正式测验；
- 题量、总分以 Service 返回为准，不虚报；
- 聊天中不返回未作答测验的答案与解析。
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.contracts import IntentResult, LearningContext, ToolResult
from app.agent.subgraphs.common import (
    format_date,
    require_ok,
    unavailable_message,
)
from app.agent.tools import AgentToolbox
from app.schemas.quiz import QuizAttemptOut, QuizAttemptSummaryOut

_CHAPTER_WORDS = ("章节", "本章", "这一章", "这章", "当前章")
_STAGE_WORDS = ("阶段", "综合", "全部", "整体", "所有内容")


class QuizState(TypedDict, total=False):
    user_message: str
    context: LearningContext
    intent: IntentResult
    tool_results: dict[str, ToolResult]
    quiz_scope: dict[str, str | None]
    reply: str
    result_status: str


def build_quiz_subgraph(toolbox: AgentToolbox):
    async def call_tools(state: QuizState) -> dict[str, Any]:
        results: dict[str, ToolResult] = {}
        if state["intent"].sub_intent == "quiz_history":
            results["attempts"] = toolbox.get_quiz_attempts()
            return {"tool_results": results}

        scope = _resolve_scope(state["user_message"], state["context"], toolbox, results)
        if scope is None:
            return {"tool_results": results, "quiz_scope": {}}

        result = await toolbox.generate_quiz(
            scope_type=scope["scope_type"] or "stage",
            knowledge_point_code=scope.get("knowledge_point_code"),
            chapter_code=scope.get("chapter_code"),
        )
        results["quiz"] = result
        return {"tool_results": results, "quiz_scope": scope}

    async def compose(state: QuizState) -> dict[str, str]:
        results = state["tool_results"]
        if state["intent"].sub_intent == "quiz_history":
            reply, status = _compose_history(results["attempts"])
        elif "quiz" not in results:
            reply, status = _compose_missing_scope(state["quiz_scope"])
        else:
            reply, status = _compose_quiz(results["quiz"], state["quiz_scope"])
        return {"reply": reply, "result_status": status}

    graph = StateGraph(QuizState)
    graph.add_node("call_tools", call_tools)
    graph.add_node("compose", compose)
    graph.add_edge(START, "call_tools")
    graph.add_edge("call_tools", "compose")
    graph.add_edge("compose", END)
    return graph.compile()


# ---------------------------------------------------------------- 范围解析

def _resolve_scope(
    message: str,
    context: LearningContext,
    toolbox: AgentToolbox,
    results: dict[str, ToolResult],
) -> dict[str, str | None] | None:
    """按用户明确指定的范围组卷；没有依据时不猜测章节。"""
    wants_chapter = any(word in message for word in _CHAPTER_WORDS)
    wants_stage = any(word in message for word in _STAGE_WORDS)

    if wants_stage:
        return {"scope_type": "stage", "knowledge_point_code": None, "chapter_code": None}

    if wants_chapter:
        chapter_code, chapter_title = _chapter_from_context(context, toolbox, results)
        if chapter_code is None:
            return None
        return {
            "scope_type": "chapter",
            "knowledge_point_code": None,
            "chapter_code": chapter_code,
            "label": chapter_title,
        }

    if context.knowledge_point is not None:
        kp = context.knowledge_point
        return {
            "scope_type": "knowledge_point",
            "knowledge_point_code": kp.code,
            "chapter_code": None,
            "label": kp.name,
        }

    if (
        context.plan is not None
        and context.plan.next_pending_knowledge_point_code
    ):
        code = context.plan.next_pending_knowledge_point_code
        kp_result = toolbox.get_knowledge_point(code)
        results["scope_knowledge_point"] = kp_result
        if kp_result.status == "failed":
            require_ok(kp_result, "读取当前知识点")
        if kp_result.ok:
            kp = kp_result.data
            return {
                "scope_type": "knowledge_point",
                "knowledge_point_code": kp.code,
                "chapter_code": None,
                "label": kp.name,
            }

    # 没有会话/计划上下文时，按已学习内容组一份阶段测验；
    # 若未学习任何知识点，QuizService 会返回明确错误，这里不伪造题目。
    return {
        "scope_type": "stage",
        "knowledge_point_code": None,
        "chapter_code": None,
        "label": "全部已学习内容",
    }


def _chapter_from_context(
    context: LearningContext,
    toolbox: AgentToolbox,
    results: dict[str, ToolResult],
) -> tuple[str | None, str | None]:
    if context.knowledge_point is not None:
        kp = context.knowledge_point
        return kp.chapter_code, kp.chapter_title

    if context.plan is not None and context.plan.next_pending_knowledge_point_code:
        kp_result = toolbox.get_knowledge_point(
            context.plan.next_pending_knowledge_point_code
        )
        results["scope_knowledge_point"] = kp_result
        require_ok(kp_result, "读取当前章节")
        if kp_result.ok:
            kp = kp_result.data
            return kp.chapter.code, kp.chapter.title
    return None, None


# ---------------------------------------------------------------- 生成测验

def _compose_quiz(
    result: ToolResult, scope: dict[str, str | None]
) -> tuple[str, str]:
    require_ok(result, "生成测验")
    if result.status == "unavailable":
        target = scope.get("label") or "当前范围"
        return (
            f"{unavailable_message(result, f'为「{target}」生成测验')}\n\n"
            "只有已学习的知识点才会进入正式测验。请先完成相关学习任务，"
            "或到「测验中心」查看当前可测验的知识点。",
            "unavailable",
        )

    attempt: QuizAttemptOut = result.data
    builtin = sum(1 for question in attempt.questions if question.source == "builtin")
    ai = sum(1 for question in attempt.questions if question.source == "ai")

    lines = [f"已为「{attempt.scope_name}」生成一份测验："]
    lines.append("")
    lines.append(f"- 题量：{attempt.question_count} 题")
    lines.append(f"- 总分：{attempt.total_points} 分")
    source_parts = []
    if builtin:
        source_parts.append(f"内置已验证题库 {builtin} 道")
    if ai:
        source_parts.append(f"AI 变式题 {ai} 道")
    lines.append("- 题目来源：" + "、".join(source_parts or ["已验证题库"]))

    if attempt.scope_type == "knowledge_point":
        lines.append(
            "- 掌握条件：至少 3 题、全部答对且百分制得分 ≥ 90，"
            "才会计为已掌握"
        )

    lines.append("")
    lines.append(
        f"请到「测验中心」打开本次测验（编号 {attempt.id}）作答。"
        "提交后系统会自动评分，答错的题会进入错题本并生成复习任务。"
    )
    if attempt.ai_note:
        lines.append(f"说明：{attempt.ai_note}")
    return "\n".join(lines), "ok"


def _compose_missing_scope(scope: dict[str, str | None]) -> tuple[str, str]:
    if scope.get("scope_type") == "chapter":
        return (
            "无法确定要测验的章节：当前会话没有关联知识点，学习计划里也没有"
            "可用的待学知识点。\n\n请从「学习」页的知识点进入对话后再说"
            "「为本章生成测验」，或直接到「测验中心」选择可测验的章节。",
            "unavailable",
        )
    return (
        "暂时无法确定测验范围，请到「测验中心」选择知识点、章节或阶段测验。",
        "unavailable",
    )


# ---------------------------------------------------------------- 测验记录

def _compose_history(result: ToolResult) -> tuple[str, str]:
    require_ok(result, "读取测验记录")
    if result.status == "unavailable":
        return unavailable_message(result, "读取测验记录"), "unavailable"

    attempts: list[QuizAttemptSummaryOut] = result.data
    if not attempts:
        return (
            "还没有测验记录。\n\n你可以说「为当前章节生成测验」，"
            "或到「测验中心」选择范围开始测验。",
            "ok",
        )

    lines = [f"最近的测验记录（共 {len(attempts)} 次）：", ""]
    for attempt in attempts[:10]:
        if attempt.status == "submitted":
            score = f"{attempt.score} 分" if attempt.score is not None else "已提交"
            status = f"已提交 · {score}"
        else:
            status = "未提交"
        lines.append(
            f"- {format_date(attempt.started_at)} · {attempt.scope_name} · "
            f"{attempt.question_count} 题 · {status}"
        )
    if len(attempts) > 10:
        lines.append(f"- 另有 {len(attempts) - 10} 次更早的记录，请到「测验中心」查看")

    pending = [item for item in attempts if item.status == "in_progress"]
    lines.append("")
    if pending:
        lines.append(f"你有 {len(pending)} 次测验尚未提交，建议先完成后再开始新的测验。")
    else:
        lines.append("可以继续说「为当前章节生成测验」，开始一次新的测验。")
    return "\n".join(lines), "ok"
