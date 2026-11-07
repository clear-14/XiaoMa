"""Teaching Subgraph：AI 教学子图（PRD 7.1 Agent 组织方式 / 阶段 8）。

使用 LangGraph 的单节点子图承载教学对话流程：
1. 节点内调用统一 LLM Provider 的流式接口；
2. 通过 get_stream_writer() 把增量文本作为 custom 流输出给 SSE 端点；
3. 模型错误由 LlmError 向上抛出，由业务层保存为 status=error 的失败消息，
   绝不伪造成功回复（PRD 7.3）。

当前 V1.0 的教学子图只做「讲解/答疑」，不执行用户代码，也不直接修改数据库；
学习档案、知识点与任务上下文由 Service 层读取后以提示词传入。
"""

from collections.abc import AsyncIterator, Callable
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.services.llm_client import LlmRequest, create_llm_client

DeltaEmitter = Callable[[dict[str, str]], None]


class TeachingState(TypedDict):
    """教学子图状态：传给模型的历史消息与最终回复。"""

    messages: list[dict[str, str]]
    reply: str


async def _teach_node(
    state: TeachingState,
    *,
    llm_request: LlmRequest,
    system_prompt: str,
    emit: DeltaEmitter | None = None,
) -> dict[str, str]:
    """调用模型流式生成回复，并把每个增量写入 LangGraph custom 流。

    emit 用于主 Agent 显式转发增量（嵌套子图的 custom 事件不会自动冒泡到
    父图），未提供时沿用 get_stream_writer()。
    """
    client = create_llm_client(llm_request)
    writer = emit or get_stream_writer()
    parts: list[str] = []
    payload = [
        {"role": "system", "content": system_prompt},
        *state["messages"],
    ]
    async for delta in client.stream(payload):
        parts.append(delta)
        writer({"delta": delta})
    return {"reply": "".join(parts)}


def build_teaching_graph(
    llm_request: LlmRequest,
    system_prompt: str,
    *,
    emit: DeltaEmitter | None = None,
):
    """构建单节点 Teaching 子图（每次请求绑定模型参数与系统提示词）。"""

    async def teach(state: TeachingState) -> dict[str, str]:
        return await _teach_node(
            state,
            llm_request=llm_request,
            system_prompt=system_prompt,
            emit=emit,
        )

    graph = StateGraph(TeachingState)
    graph.add_node("teach", teach)
    graph.add_edge(START, "teach")
    graph.add_edge("teach", END)
    return graph.compile()


async def stream_teaching_reply(
    llm_request: LlmRequest,
    system_prompt: str,
    messages: list[dict[str, str]],
) -> AsyncIterator[str]:
    """运行教学子图，逐个产出模型增量文本。

    模型超时/不可用/空回复等错误由 LlmError 抛出；调用方必须明确处理，
    不得把失败伪装成正常回复。
    """
    graph = build_teaching_graph(llm_request, system_prompt)
    async for chunk in graph.astream(
        {"messages": messages, "reply": ""}, stream_mode="custom"
    ):
        if isinstance(chunk, dict) and chunk.get("delta"):
            yield str(chunk["delta"])
