"""Teaching Subgraph：讲解与答疑（阶段 6：先经 Service 读取课程库内容）。

流程：load_course_material（AgentToolbox → CourseService） → teach（LLM）。

约束：
- Agent 讲解前必须先通过 Service 取得知识点与课时内容，作为事实依据注入
  系统提示词；取不到内容时明确标注，绝不编造教材原文；
- 模型增量通过主 Agent 节点的 get_stream_writer() 实时转发；
- 工具 failed 必须抛 AgentRunError，不能把失败包装成成功回答；
- 模型异常由 LlmError 向上抛出，由 API 保存为失败消息；
- V1.4 批次 8：模型的「超范围说明」以结构化标记 ``[[out_of_scope]]`` 开头时，
  标记会被剥离并转成 ``reply_scope``，由 finalize 决定不下发讲解卡片。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.agent.contracts import (
    AgentRunError,
    IntentResult,
    LearningContext,
)
from app.agent.scope_marker import ScopeMarkerFilter
from app.agent.tools import AgentToolbox
from app.services.llm_client import LlmRequest
from app.services.teaching_graph import build_teaching_graph
from app.services.teaching_prompt import build_course_material_section

DeltaEmitter = Callable[[dict[str, str]], None]


class TeachingAgentState(TypedDict, total=False):
    user_message: str
    messages: list[dict[str, str]]
    context: LearningContext
    intent: IntentResult
    course_material: str | None
    tool_results: dict[str, Any]
    reply: str
    streamed: bool
    result_status: str
    reply_scope: str


def build_teaching_subgraph(
    llm_request: LlmRequest | None,
    system_prompt: str,
    *,
    emit: DeltaEmitter | None = None,
    toolbox: AgentToolbox | None = None,
):
    if llm_request is None:
        raise AgentRunError(
            "模型未配置或当前不可用，暂时无法讲解。"
            "请到「系统设置」页配置可用的模型后重试；学习计划、测验等数据查询不受影响。"
        )

    async def load_course_material(
        state: TeachingAgentState,
    ) -> dict[str, Any]:
        """先经 Service 取真实课程内容；没有关联知识点时不注入内容。"""
        context: LearningContext | None = state.get("context")
        if toolbox is None or context is None or context.knowledge_point is None:
            return {"course_material": None, "tool_results": {}}

        kp_result = toolbox.get_knowledge_point(context.knowledge_point.code)
        if kp_result.status == "failed":
            raise AgentRunError(kp_result.message or "读取知识点失败")
        if not kp_result.ok:
            # unavailable 说明课程库里没有该知识点，不能带着编造内容继续讲
            raise AgentRunError(
                kp_result.message or "课程库中找不到当前知识点，无法讲解"
            )
        kp_detail = kp_result.data
        results: dict[str, Any] = {"knowledge_point": kp_result}

        lesson_detail = None
        kp_lesson = getattr(kp_detail, "lesson", None)
        if kp_lesson is not None:
            lesson_result = toolbox.get_lesson(kp_lesson.code)
            if lesson_result.status == "failed":
                raise AgentRunError(lesson_result.message or "读取课时内容失败")
            if not lesson_result.ok:
                raise AgentRunError(
                    lesson_result.message or "课程库中找不到当前课时内容，无法讲解"
                )
            lesson_detail = lesson_result.data
            results["lesson"] = lesson_result

        material = build_course_material_section(kp_detail, lesson_detail)
        return {"course_material": material, "tool_results": results}

    async def teach(state: TeachingAgentState) -> dict[str, object]:
        # emit 由主 Agent 的教学节点传入父图 writer：嵌套编译子图的 custom
        # 事件不会自动冒泡，必须显式转发。
        writer = emit or get_stream_writer()
        material = state.get("course_material")
        prompt = (
            f"{system_prompt}\n\n{material}" if material else system_prompt
        )
        # 批次 8：范围标记既要在流式转发时剥离，也要成为可判定的结构化信号。
        scope_filter = ScopeMarkerFilter(writer)
        graph = build_teaching_graph(
            llm_request, prompt, emit=scope_filter.feed_event
        )
        result = await graph.ainvoke(
            {"messages": state.get("messages", []), "reply": ""}
        )
        scope_filter.flush()
        raw_reply = str(result.get("reply", ""))
        # 判定为超范围时以剥离后的正文为准：即使模型只输出了标记也不让它泄露出去。
        reply = scope_filter.text if scope_filter.out_of_scope else raw_reply
        if not reply.strip():
            raise AgentRunError("模型没有返回有效内容，请稍后重试。")
        return {
            "reply": reply,
            "streamed": True,
            "result_status": "ok",
            "reply_scope": "out_of_scope" if scope_filter.out_of_scope else "in_scope",
        }

    graph = StateGraph(TeachingAgentState)
    graph.add_node("load_course_material", load_course_material)
    graph.add_node("teach", teach)
    graph.add_edge(START, "load_course_material")
    graph.add_edge("load_course_material", "teach")
    graph.add_edge("teach", END)
    return graph.compile()
