"""Resource Subgraph：检索课程库中已登记的学习资源。

输入：用户消息、学习上下文、Resource 意图（search_resources）。
输出：reply、tool_results、result_status。

只返回数据库中的真实资源，不联网搜索、不生成或猜测外部链接；
没有匹配时明确说明，并回退到当前会话知识点的资源。
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.contracts import IntentResult, LearningContext, ToolResult
from app.agent.subgraphs.common import require_ok, unavailable_message
from app.agent.tools import AgentToolbox
from app.schemas.course import KnowledgePointResourcesOut

_RESOURCE_TYPE_LABELS = {
    "documentation": "文档",
    "exercise": "练习",
    "video": "视频",
    "article": "文章",
    "book": "书籍",
}

_NOISE_PHRASES = (
    "请帮我",
    "帮我",
    "给我",
    "请",
    "推荐一些",
    "推荐",
    "有没有",
    "有哪些",
    "有哪些相关",
    "相关",
    "关于",
    "一些",
    "学习资源",
    "学习资料",
    "学习材料",
    "资源",
    "资料",
    "教程",
    "参考书",
    "参考链接",
    "参考",
    "一下",
    "什么",
    "哪些",
    "我",
)


class ResourceState(TypedDict, total=False):
    user_message: str
    context: LearningContext
    intent: IntentResult
    tool_results: dict[str, ToolResult]
    query: str
    reply: str
    result_status: str


def build_resource_subgraph(toolbox: AgentToolbox):
    async def call_tools(state: ResourceState) -> dict[str, Any]:
        query = _extract_query(state["user_message"])
        context = state["context"]
        if not query and context.knowledge_point is not None:
            query = context.knowledge_point.name

        results: dict[str, ToolResult] = {
            "resources": toolbox.search_resources(query)
        }
        if (
            context.knowledge_point is not None
            and query != context.knowledge_point.name
            and results["resources"].ok
            and not results["resources"].data
        ):
            results["fallback"] = toolbox.search_resources(
                context.knowledge_point.name
            )
        return {"tool_results": results, "query": query}

    async def compose(state: ResourceState) -> dict[str, str]:
        results = state["tool_results"]
        reply, status = _compose(
            results["resources"],
            results.get("fallback"),
            query=state.get("query", ""),
            context=state["context"],
        )
        return {"reply": reply, "result_status": status}

    graph = StateGraph(ResourceState)
    graph.add_node("call_tools", call_tools)
    graph.add_node("compose", compose)
    graph.add_edge(START, "call_tools")
    graph.add_edge("call_tools", "compose")
    graph.add_edge("compose", END)
    return graph.compile()


def _compose(
    result: ToolResult,
    fallback: ToolResult | None,
    *,
    query: str,
    context: LearningContext,
) -> tuple[str, str]:
    require_ok(result, "检索学习资源")
    if result.status == "unavailable":
        return unavailable_message(result, "检索学习资源"), "unavailable"

    matched: list[KnowledgePointResourcesOut] = result.data
    used_query = query
    note: str | None = None

    if not matched and fallback is not None:
        require_ok(fallback, "检索当前知识点的学习资源")
        if fallback.ok and fallback.data:
            matched = fallback.data
            used_query = context.knowledge_point.name if context.knowledge_point else ""
            note = f"没有找到与「{query}」直接匹配的资源，以下是当前知识点的资源。"

    if not matched:
        topic = f"「{query}」" if query else "该主题"
        return (
            f"本地课程库中没有登记与{topic}匹配的学习资源。\n\n"
            "系统只提供课程内已登记的资源，不会联网搜索或编造外部链接。"
            "你可以换个关键词（例如具体知识点名称），或到「学习」页查看课程内容。",
            "ok",
        )

    lines: list[str] = []
    if note:
        lines.append(note)
        lines.append("")
    elif query:
        lines.append(f"与「{used_query}」相关的已登记学习资源：")
    else:
        lines.append("课程库中已登记的学习资源（未指定主题，以下为部分结果）：")
    lines.append("")

    for index, group in enumerate(matched, start=1):
        lines.append(f"{index}. {group.knowledge_point_name}（{group.chapter_title}）")
        for resource in group.resources:
            label = _RESOURCE_TYPE_LABELS.get(resource.type, resource.type)
            if resource.url:
                lines.append(f"   - {label}：{resource.title}（{resource.url}）")
            else:
                lines.append(f"   - {label}：{resource.title}")
        lines.append("")

    lines.append(
        "以上资源来自本地课程库；到「学习」页打开对应知识点可以查看完整学习目标与掌握标准。"
    )
    return "\n".join(lines).rstrip(), "ok"


def _extract_query(message: str) -> str:
    query = message
    for phrase in _NOISE_PHRASES:
        query = query.replace(phrase, " ")
    query = re.sub(r"[，。！？、；：,.!?;:\s]+", " ", query)
    query = query.strip(" 的了吗呢吧啊")
    if len(query) > 60:
        query = query[:60]
    return query
