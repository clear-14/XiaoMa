"""Planning Subgraph：今日任务、学习进度与学习计划调整建议。

输入：用户消息、学习上下文、Planning 意图（today_tasks / progress /
      plan_overview / adjust_plan）。
输出：reply（给用户的明确回答）、tool_results、result_status。

调整计划始终调用 PlanService：后端生成「待确认草案」，Agent 绝不自动确认，
也不会声称草案已生效；无明确参数时只询问，不擅自修改计划。
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.contracts import IntentResult, LearningContext, ToolResult
from app.agent.subgraphs.common import format_date, require_ok, unavailable_message
from app.agent.tools import AgentToolbox
from app.schemas.learning_overview import LearningOverviewOut
from app.schemas.plan import CurrentPlanOut, PlanVersionOut
from app.schemas.daily_task import TodayTasksOut
from app.services.teaching_prompt import (
    LEVEL_LABELS,
    TASK_STATUS_LABELS,
)


class PlanningState(TypedDict, total=False):
    user_message: str
    context: LearningContext
    intent: IntentResult
    tool_results: dict[str, ToolResult]
    plan_changes: dict[str, Any]
    reply: str
    result_status: str


def build_planning_subgraph(toolbox: AgentToolbox):
    async def call_tools(state: PlanningState) -> dict[str, Any]:
        mode = state["intent"].sub_intent
        results: dict[str, ToolResult] = {}
        plan_changes: dict[str, Any] = {}

        if mode == "today_tasks":
            results["today_tasks"] = toolbox.get_today_tasks()
        elif mode == "progress":
            results["progress"] = toolbox.get_progress()
        elif mode == "adjust_plan":
            results["plan"] = toolbox.get_current_plan()
            plan_changes = _extract_plan_changes(state["user_message"])
            if plan_changes and results["plan"].ok:
                plan: CurrentPlanOut = results["plan"].data
                results["adjust"] = toolbox.adjust_plan(plan.id, plan_changes)
        else:
            results["plan"] = toolbox.get_current_plan()

        return {"tool_results": results, "plan_changes": plan_changes}

    async def compose(state: PlanningState) -> dict[str, str]:
        mode = state["intent"].sub_intent
        results = state["tool_results"]
        if mode == "today_tasks":
            reply, status = _compose_today_tasks(results["today_tasks"])
        elif mode == "progress":
            reply, status = _compose_progress(results["progress"])
        elif mode == "adjust_plan":
            reply, status = _compose_adjust_plan(
                results["plan"],
                results.get("adjust"),
                state.get("plan_changes", {}),
            )
        else:
            reply, status = _compose_plan_overview(results["plan"])
        return {"reply": reply, "result_status": status}

    graph = StateGraph(PlanningState)
    graph.add_node("call_tools", call_tools)
    graph.add_node("compose", compose)
    graph.add_edge(START, "call_tools")
    graph.add_edge("call_tools", "compose")
    graph.add_edge("compose", END)
    return graph.compile()


# ---------------------------------------------------------------- 今日任务

def _compose_today_tasks(result: ToolResult) -> tuple[str, str]:
    require_ok(result, "获取今日学习任务")
    if result.status == "unavailable":
        guidance = "请先到「学习计划」页面创建并确认学习计划，或确认计划是否已生效。"
        return f"{unavailable_message(result, '获取今日学习任务')}\n\n{guidance}", "unavailable"

    data: TodayTasksOut = result.data
    if not data.tasks:
        note = data.note or "今天没有需要完成的学习任务"
        return (
            f"{note}。\n\n你可以到「测验中心」复习已学知识点，"
            "或在「错题本」完成待复习任务。",
            "ok",
        )

    lines = [f"今天（{format_date(data.task_date)}）的学习任务："]
    if data.generated:
        lines.append("（已根据当前学习计划生成今日任务）")
    lines.append("")
    for index, task in enumerate(data.tasks, start=1):
        kp = task.knowledge_point
        status = TASK_STATUS_LABELS.get(task.status, task.status)
        lines.append(
            f"{index}. {kp.name}（第 {task.day_index} 天，预计 "
            f"{kp.estimated_minutes} 分钟）— {status}"
        )

    pending = [
        task
        for task in data.tasks
        if task.status in ("pending", "learning")
    ]
    lines.append("")
    if pending:
        lines.append(
            f"建议先完成「{pending[0].knowledge_point.name}」；"
            "学习后到「测验中心」做一次知识点测验，验证是否真正掌握。"
        )
    else:
        lines.append(
            "今天的任务都已标记完成。可以到「测验中心」做知识点测验，"
            "或到「错题本」完成复习任务。"
        )
    return "\n".join(lines), "ok"


# ---------------------------------------------------------------- 学习进度

def _compose_progress(result: ToolResult) -> tuple[str, str]:
    require_ok(result, "获取学习进度")
    if result.status == "unavailable":
        return unavailable_message(result, "获取学习进度"), "unavailable"

    data: LearningOverviewOut = result.data
    lines = [f"学习进度概览（{format_date(data.today)}）", ""]
    lines.append(f"- 学习目标：{data.learning_goal or '未填写'}")
    lines.append(
        f"- 当前基础：{LEVEL_LABELS.get(data.current_level or '', '未填写')}"
    )
    if data.daily_study_minutes:
        lines.append(f"- 每日学习时间：{data.daily_study_minutes} 分钟")

    if data.plan_available:
        if data.plan_confirmed:
            lines.append(
                f"- 学习计划：{data.plan_course_name or '当前课程'} · "
                f"已完成 {data.plan_completed_items}/{data.plan_total_items} "
                f"个计划项目（{data.plan_progress_percent}%）"
            )
            if data.plan_current_day is not None:
                lines.append(f"- 下一个待完成计划日：第 {data.plan_current_day} 天")
        else:
            lines.append(
                f"- 学习计划：{data.plan_course_name or '当前课程'} 尚未确认"
            )
        if data.plan_pending_version_number is not None:
            lines.append(
                f"- 计划草案：版本 {data.plan_pending_version_number} 待确认"
            )
        if data.plan_warning:
            lines.append(f"- 计划提示：{data.plan_warning}")
    else:
        lines.append("- 学习计划：暂无（请先创建并确认学习计划）")

    lines.append(
        f"- 已学习知识点：{data.learned_count} 个"
        f"（已掌握 {data.mastered_count}、待验证 {data.pending_verification_count}、"
        f"学习中 {data.learning_count}）"
    )

    if data.chapters:
        lines.append("")
        lines.append("分章节：")
        for chapter in data.chapters[:5]:
            lines.append(
                f"- {chapter.chapter_title}：已学习 {chapter.learned_count} 个，"
                f"已掌握 {chapter.mastered_count} 个"
            )
        if len(data.chapters) > 5:
            lines.append(f"- 另有 {len(data.chapters) - 5} 个章节有学习记录")

    lines.append("")
    if data.quiz_submitted_count:
        lines.append(
            f"- 测验：共 {data.quiz_attempt_count} 次记录，"
            f"已提交 {data.quiz_submitted_count} 次；"
            f"平均 {data.quiz_average_score} 分，"
            f"最近一次 {data.latest_quiz_score} 分"
        )
    else:
        lines.append("- 测验：还没有已提交的测验记录")
    if data.mistake_total_count:
        lines.append(
            f"- 错题：{data.mistake_pending_count} 道待复习，"
            f"{data.mistake_resolved_count} 道已解决；"
            f"{data.mistake_due_count} 个复习任务已到期"
        )
    else:
        lines.append("- 错题：暂无错题记录")

    advice: list[str] = []
    if data.mistake_due_count:
        advice.append(f"先完成 {data.mistake_due_count} 个已到期的复习任务。")
    if data.pending_verification_count:
        advice.append(
            f"有 {data.pending_verification_count} 个知识点已完成学习但尚未通过测验验证，"
            "建议到「测验中心」完成知识点测验。"
        )
    if data.learned_count == 0:
        advice.append("还没有开始学习，建议先完成今天的学习任务。")
    elif data.mastered_count == data.learned_count:
        advice.append("已学习知识点均已通过掌握验证，可以继续推进学习计划。")
    elif not advice:
        advice.append("继续按今日任务学习，学完后用测验验证掌握情况。")

    lines.append("")
    lines.append("建议：" + "".join(advice))
    if data.notes:
        lines.append("说明：" + "；".join(data.notes))
    return "\n".join(lines), "ok"


# ---------------------------------------------------------------- 计划查看

def _compose_plan_overview(result: ToolResult) -> tuple[str, str]:
    require_ok(result, "读取学习计划")
    if result.status == "unavailable":
        return (
            f"{unavailable_message(result, '读取学习计划')}\n\n"
            "请到「学习计划」页面填写学习目标、当前基础和每日学习时间，"
            "创建并确认计划后，我才能按计划安排学习。",
            "unavailable",
        )

    plan: CurrentPlanOut = result.data
    lines = [f"当前学习计划：{plan.course_name}"]
    current = plan.current_version
    pending = plan.pending_version

    if current is None and pending is None:
        lines.append("当前计划还没有可用的版本，请到「学习计划」页面查看。")
        return "\n".join(lines), "ok"

    if current is not None:
        lines.extend(_version_lines(current, prefix="当前生效版本"))
        lines.append(f"- 计划进度：已完成 {_completed(current)}/{len(current.items)} 个项目")
    else:
        lines.append("- 当前没有已生效的版本")

    if pending is not None:
        lines.append("")
        lines.extend(_version_lines(pending, prefix="待确认草案"))
        lines.append("- 草案需要到「学习计划」页面确认后才会生效。")

    lines.append("")
    lines.append(
        "如需调整，直接告诉我新的每日学习时间、期望周期或学习目标，"
        "例如「每天学习 30 分钟，期望 20 天完成」。"
    )
    return "\n".join(lines), "ok"


def _version_lines(version: PlanVersionOut, *, prefix: str) -> list[str]:
    lines = [
        f"- {prefix}：版本 {version.version_number}（{version.status}）",
        f"- 学习目标：{version.learning_goal}",
        f"- 每日学习时间：{version.daily_study_minutes} 分钟",
        f"- 期望周期：{version.expected_duration_days} 天；"
        f"预计需要 {version.computed_duration_days} 天",
    ]
    if version.warning:
        lines.append(f"- 计划提示：{version.warning}")
    return lines


# ---------------------------------------------------------------- 计划调整

def _compose_adjust_plan(
    plan_result: ToolResult,
    adjust_result: ToolResult | None,
    changes: dict[str, Any],
) -> tuple[str, str]:
    require_ok(plan_result, "读取学习计划")
    if plan_result.status == "unavailable":
        return (
            f"{unavailable_message(plan_result, '调整学习计划')}\n\n"
            "请先到「学习计划」页面创建并确认计划，再告诉我需要调整的参数。",
            "unavailable",
        )

    plan: CurrentPlanOut = plan_result.data
    current = plan.current_version or plan.pending_version
    if not changes:
        lines = ["可以调整学习计划，但我还没有看到具体的新参数。请告诉我，例如："]
        lines.append("")
        lines.append("- 「每天学习 30 分钟」")
        lines.append("- 「期望 20 天完成」")
        lines.append("- 「学习目标改为 转行做后端开发」")
        lines.append("")
        if current is not None:
            lines.append(
                f"当前计划：每日 {current.daily_study_minutes} 分钟 / "
                f"期望 {current.expected_duration_days} 天 / "
                f"目标「{current.learning_goal}」。"
            )
        lines.append("调整会先生成待确认草案，不会立即生效。")
        return "\n".join(lines), "ok"

    if adjust_result is None:
        return "没有执行计划调整，请稍后重试。", "unavailable"
    require_ok(adjust_result, "调整学习计划")
    if adjust_result.status == "unavailable":
        return (
            f"{unavailable_message(adjust_result, '调整学习计划')}\n\n"
            "当前计划保持不变。请检查参数后重试。",
            "unavailable",
        )

    adjusted: CurrentPlanOut = adjust_result.data
    pending = adjusted.pending_version
    if pending is None:
        return (
            "调整请求已提交，但没有返回待确认草案。请到「学习计划」页面查看当前状态。",
            "unavailable",
        )

    lines = [f"已生成学习计划调整草案（版本 {pending.version_number}），尚未生效："]
    lines.append("")
    lines.append(f"- 每日学习时间：{pending.daily_study_minutes} 分钟")
    lines.append(f"- 期望周期：{pending.expected_duration_days} 天")
    lines.append(f"- 预计需要：{pending.computed_duration_days} 天")
    if pending.warning:
        lines.append(f"- 计划提示：{pending.warning}")
    lines.append("")
    if adjusted.current_version_number is not None:
        lines.append(
            f"当前生效版本仍是版本 {adjusted.current_version_number}。"
        )
    lines.append(
        "请到「学习计划」页面确认草案后才会应用；在确认前，学习安排不会改变。"
    )
    return "\n".join(lines), "ok"


# ---------------------------------------------------------------- 参数提取

def _extract_plan_changes(message: str) -> dict[str, Any]:
    """从用户消息中提取明确给出的调整参数；未给出则不猜测。"""
    changes: dict[str, Any] = {}

    match = re.search(r"(?:每天|每日)[^0-9]{0,12}(\d{1,4})\s*分钟", message)
    if match:
        changes["daily_study_minutes"] = int(match.group(1))

    match = re.search(
        r"(?:期望|希望|目标|周期)[^0-9]{0,8}(\d{1,4})\s*天", message
    )
    if not match:
        match = re.search(r"(?<!今)(?<!明)(\d{1,4})\s*天(?:内|完成|学完)", message)
    if match:
        changes["expected_duration_days"] = int(match.group(1))

    match = re.search(
        r"(?:学习目标|目标)(?:改为|调整为|改成|是|：|:)\s*([^，。；;\n]{2,200})",
        message,
    )
    if match:
        goal = match.group(1).strip(" ，。；;,.!！?？")
        if goal:
            changes["learning_goal"] = goal

    return changes


def _completed(version: PlanVersionOut) -> int:
    return sum(1 for item in version.items if item.status == "completed")
