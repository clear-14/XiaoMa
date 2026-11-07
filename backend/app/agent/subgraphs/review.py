"""Review Subgraph：分析错题本与复习任务。

输入：用户消息、学习上下文、Review 意图（analyze_mistakes）。
输出：reply、tool_results、result_status。

只基于错题记录做统计与复习建议；不推测具体错因，也不在聊天中输出
未提交复习题的正确答案与解析，避免剧透。
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.contracts import IntentResult, LearningContext, ToolResult
from app.agent.subgraphs.common import (
    format_date,
    require_ok,
    truncate,
    unavailable_message,
)
from app.agent.tools import AgentToolbox
from app.schemas.quiz import MistakeOut, ReviewTaskOut

_QUESTION_TYPE_LABELS = {
    "single_choice": "单选题",
    "multiple_choice": "多选题",
    "true_false": "判断题",
    "fill_blank": "填空题",
    "short_answer": "简答题",
    "code_analysis": "代码分析题",
    "code_writing": "代码编写题",
}

_REVIEW_STAGE_TOTAL = 4


class ReviewState(TypedDict, total=False):
    user_message: str
    context: LearningContext
    intent: IntentResult
    tool_results: dict[str, ToolResult]
    reply: str
    result_status: str


def build_review_subgraph(toolbox: AgentToolbox):
    async def call_tools(state: ReviewState) -> dict[str, Any]:
        return {
            "tool_results": {
                "mistakes": toolbox.get_mistakes(),
                "review_tasks": toolbox.get_review_tasks(),
            }
        }

    async def compose(state: ReviewState) -> dict[str, str]:
        results = state["tool_results"]
        reply, status = _compose(results["mistakes"], results["review_tasks"])
        return {"reply": reply, "result_status": status}

    graph = StateGraph(ReviewState)
    graph.add_node("call_tools", call_tools)
    graph.add_node("compose", compose)
    graph.add_edge(START, "call_tools")
    graph.add_edge("call_tools", "compose")
    graph.add_edge("compose", END)
    return graph.compile()


def _compose(
    mistakes_result: ToolResult, tasks_result: ToolResult
) -> tuple[str, str]:
    require_ok(mistakes_result, "读取错题本")
    require_ok(tasks_result, "读取复习任务")
    if mistakes_result.status == "unavailable":
        return unavailable_message(mistakes_result, "读取错题本"), "unavailable"
    if tasks_result.status == "unavailable":
        return unavailable_message(tasks_result, "读取复习任务"), "unavailable"

    mistakes: list[MistakeOut] = mistakes_result.data
    tasks: list[ReviewTaskOut] = tasks_result.data
    pending = [item for item in mistakes if item.review_status == "pending"]
    resolved = [item for item in mistakes if item.review_status == "resolved"]
    due_tasks = [task for task in tasks if task.is_due]

    if not mistakes:
        return (
            "错题本目前是空的，没有需要分析的错题。\n\n"
            "继续按学习计划学习，到「测验中心」做测验；答错的题会自动进入错题本，"
            "并按 1/3/7/14 天安排复习。",
            "ok",
        )

    lines = [
        f"错题分析（共 {len(mistakes)} 道：待复习 {len(pending)} 道，"
        f"已解决 {len(resolved)} 道）"
    ]

    if pending:
        lines.append("")
        lines.append("按知识点分布（待复习）：")
        groups: dict[str, list[MistakeOut]] = {}
        for mistake in pending:
            groups.setdefault(mistake.knowledge_point.name, []).append(mistake)
        for name, items in list(groups.items())[:6]:
            repeat = sum(1 for item in items if item.attempt_count > 1)
            latest = max(item.last_wrong_at for item in items)
            stage = min(item.review_stage for item in items)
            detail = f"- 「{name}」：{len(items)} 道"
            if repeat:
                detail += f"，其中 {repeat} 道重复做错"
            detail += (
                f"；最近错误 {format_date(latest)}；"
                f"最早一道处于第 {stage + 1}/{_REVIEW_STAGE_TOTAL} 轮复习"
            )
            lines.append(detail)
        if len(groups) > 6:
            lines.append(f"- 另有 {len(groups) - 6} 个知识点有错题")

        type_counts: dict[str, int] = {}
        for mistake in pending:
            label = _QUESTION_TYPE_LABELS.get(
                mistake.question.question_type, mistake.question.question_type
            )
            type_counts[label] = type_counts.get(label, 0) + 1
        lines.append("")
        lines.append(
            "题型分布："
            + "、".join(f"{label} {count} 道" for label, count in type_counts.items())
        )
    else:
        lines.append("")
        lines.append("目前没有待复习的错题。")

    lines.append("")
    if tasks:
        lines.append(
            f"复习任务：{len(tasks)} 个待完成，其中 {len(due_tasks)} 个已到期。"
        )
        for task in due_tasks[:3]:
            lines.append(
                f"- 「{task.knowledge_point.name}」"
                f"第 {task.interval_days} 天复习 · 到期 {format_date(task.due_at)} · "
                f"题目：{truncate(task.question.stem, 30)}"
            )
        if len(due_tasks) > 3:
            lines.append(f"- 另有 {len(due_tasks) - 3} 个已到期任务")
    elif pending:
        lines.append("复习任务：当前没有待完成的复习任务，错题会在到期时生成。")
    else:
        lines.append("复习任务：没有待完成的复习任务。")

    suggestions: list[str] = []
    if due_tasks:
        suggestions.append(f"先到「错题本」完成 {len(due_tasks)} 个已到期的复习任务。")
    if pending and not due_tasks:
        suggestions.append("按错题本显示的下次复习时间回来复习，不要提前跳过。")
    repeated = [item for item in pending if item.attempt_count > 1]
    if repeated:
        suggestions.append(
            f"有 {len(repeated)} 道题重复做错，建议回到对应知识点重新学习，"
            "再请求「为当前知识点生成测验」。"
        )
    if resolved:
        suggestions.append(f"已有 {len(resolved)} 道错题完成复习，继续保持。")
    if not suggestions:
        suggestions.append("继续保持当前学习节奏。")

    lines.append("")
    lines.append("建议：" + "".join(suggestions))
    lines.append(
        "说明：以上是错题记录统计，不推测具体错因；"
        "到「错题本」查看题目解析后再总结自己的薄弱点。"
    )
    return "\n".join(lines), "ok"
