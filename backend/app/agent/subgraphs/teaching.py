"""Teaching Subgraph：讲解与答疑（复用阶段 8 的教学子图）。

输入：对话历史 messages、学习上下文与教学意图。
输出：reply（完整回复）、streamed=True、result_status。

模型增量通过主 Agent 节点的 get_stream_writer() 实时转发；模型异常由
LlmError 向上抛出，由 API 保存为失败消息，绝不伪造成功回复。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.agent.contracts import AgentRunError, IntentResult, LearningContext
from app.services.llm_client import LlmRequest
from app.services.teaching_graph import build_teaching_graph

DeltaEmitter = Callable[[dict[str, str]], None]


class TeachingAgentState(TypedDict, total=False):
    user_message: str
    messages: list[dict[str, str]]
    context: LearningContext
    intent: IntentResult
    reply: str
    streamed: bool
    result_status: str


def build_teaching_subgraph(
    llm_request: LlmRequest | None,
    system_prompt: str,
    *,
    emit: DeltaEmitter | None = None,
):
    if llm_request is None:
        raise AgentRunError(
            "模型未配置或当前不可用，暂时无法讲解。"
            "请到「系统设置」页配置可用的模型后重试；学习计划、测验等数据查询不受影响。"
        )

    async def teach(state: TeachingAgentState) -> dict[str, object]:
        # emit 由主 Agent 的教学节点传入父图 writer：嵌套编译子图的 custom
        # 事件不会自动冒泡，必须显式转发。
        writer = emit or get_stream_writer()
        graph = build_teaching_graph(
            llm_request, system_prompt, emit=writer
        )
        result = await graph.ainvoke(
            {"messages": state.get("messages", []), "reply": ""}
        )
        reply = str(result.get("reply", ""))
        if not reply.strip():
            raise AgentRunError("模型没有返回有效内容，请稍后重试。")
        return {"reply": reply, "streamed": True, "result_status": "ok"}

    graph = StateGraph(TeachingAgentState)
    graph.add_node("teach", teach)
    graph.add_edge(START, "teach")
    graph.add_edge("teach", END)
    return graph.compile()
