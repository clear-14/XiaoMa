"""主 Agent 图（阶段 10）。

流程：
用户输入 → 意图识别 → 读取学习上下文 → 路由子图 → 调用工具
        → 整理回答（finalize）→ 保存聊天记录（由 AgentRun/API 完成）→ 返回结果

约束：
- 图与子图只调用 AgentToolbox → Service，不导入 Repository、不执行 SQL；
- 五个子图输入/输出均为结构化 AgentState 的子集；
- 工具 failed 必须抛 AgentRunError，不能把失败包装成成功回答；
- finalize 对未流式输出的子图发送一次完整 delta，保证前端总能收到内容。
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agent.context import AgentContextService
from app.agent.contracts import AgentRunError, IntentResult, LearningContext, ToolResult
from app.agent.intent import recognize_intent
from app.agent.subgraphs.planning import build_planning_subgraph
from app.agent.subgraphs.quiz import build_quiz_subgraph
from app.agent.subgraphs.resource import build_resource_subgraph
from app.agent.subgraphs.review import build_review_subgraph
from app.agent.subgraphs.teaching import build_teaching_subgraph
from app.agent.tools import AgentToolbox
from app.services.conversation_service import ChatContext

logger = logging.getLogger("xiaoma.agent")


class AgentState(TypedDict, total=False):
    """主 Agent 与子图共享的结构化状态（子图只读写自己需要的字段）。"""

    user_message: str
    messages: list[dict[str, str]]
    chat_context: ChatContext
    context: LearningContext
    intent: IntentResult
    subgraph: str
    tool_results: dict[str, ToolResult]
    reply: str
    streamed: bool
    result_status: str


def build_agent_graph(*, db: Session):
    """构建主 Agent 图；Teaching 子图在节点内按本轮模型配置构建。"""

    async def recognize_node(state: AgentState) -> dict[str, Any]:
        intent = state.get("intent") or recognize_intent(state["user_message"])
        return {"intent": intent, "subgraph": intent.intent}

    async def load_context_node(state: AgentState) -> dict[str, Any]:
        try:
            context = AgentContextService(db).load(state["chat_context"])
        except Exception:
            # 不记录对话内容；上下文读取失败必须明确报错，不能带病继续。
            logger.exception("Agent 读取学习上下文失败")
            raise AgentRunError("读取学习上下文失败，请稍后重试。") from None
        return {"context": context}

    async def route_node(state: AgentState) -> dict[str, str]:
        return {"subgraph": state["intent"].intent}

    def make_subgraph_node(name: str, builder):
        async def node(state: AgentState) -> dict[str, Any]:
            toolbox = AgentToolbox(db, state["context"])
            subgraph = builder(toolbox)
            result = await subgraph.ainvoke(
                {
                    "user_message": state["user_message"],
                    "messages": state.get("messages", []),
                    "context": state["context"],
                    "intent": state["intent"],
                }
            )
            return {
                "tool_results": result.get("tool_results", {}),
                "reply": result.get("reply", ""),
                "streamed": bool(result.get("streamed", False)),
                "result_status": result.get("result_status", "ok"),
            }

        node.__name__ = f"{name}_subgraph"
        return node

    async def teaching_node(state: AgentState) -> dict[str, Any]:
        chat_context = state["chat_context"]
        if chat_context.llm_request is None:
            raise AgentRunError(
                "模型未配置或当前不可用，暂时无法讲解。"
                "请到「系统设置」页配置可用的模型后重试。"
            )
        # 必须在此处取父图 writer，再显式传给嵌套子图转发增量。
        writer = get_stream_writer()
        teaching_subgraph = build_teaching_subgraph(
            chat_context.llm_request,
            chat_context.system_prompt,
            emit=writer,
        )
        result = await teaching_subgraph.ainvoke(
            {
                "user_message": state["user_message"],
                "messages": state.get("messages", []),
                "context": state["context"],
                "intent": state["intent"],
            }
        )
        return {
            "tool_results": {},
            "reply": result.get("reply", ""),
            "streamed": bool(result.get("streamed", False)),
            "result_status": result.get("result_status", "ok"),
        }

    async def finalize_node(state: AgentState) -> dict[str, Any]:
        reply = (state.get("reply") or "").strip()
        if not reply:
            raise AgentRunError("没有生成有效回复，请稍后重试。")
        if not state.get("streamed"):
            get_stream_writer()({"delta": state["reply"]})
        return {}

    graph = StateGraph(AgentState)
    graph.add_node("recognize_intent", recognize_node)
    graph.add_node("load_context", load_context_node)
    graph.add_node("route", route_node)
    graph.add_node("planning", make_subgraph_node("planning", build_planning_subgraph))
    graph.add_node("quiz", make_subgraph_node("quiz", build_quiz_subgraph))
    graph.add_node("review", make_subgraph_node("review", build_review_subgraph))
    graph.add_node("resource", make_subgraph_node("resource", build_resource_subgraph))
    graph.add_node("teaching", teaching_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "recognize_intent")
    graph.add_edge("recognize_intent", "load_context")
    graph.add_edge("load_context", "route")
    graph.add_conditional_edges(
        "route",
        lambda state: state["intent"].intent,
        {
            "planning": "planning",
            "teaching": "teaching",
            "quiz": "quiz",
            "review": "review",
            "resource": "resource",
        },
    )
    for name in ("planning", "teaching", "quiz", "review", "resource"):
        graph.add_edge(name, "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
