"""LangGraph Agent 开发：第 26—27 章。

第 26 章把图包成 HTTP 接口：一次性返回的同步接口，和逐段推送的 SSE 接口；
第 27 章用离线测试锁住图的行为：不调真模型，也能断言消息序列、线程隔离与中断恢复。

版本口径（实测）：langgraph 1.2.20、fastapi 0.162.0、httpx 0.28.1、langchain-core 1.7.6。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 26 章
    {
        "code": "langgraph-agent-26",
        "order_index": 26,
        "title": "FastAPI 集成 LangGraph",
        "description": "把图包成接口，一次性返回和流式返回都要有。",
        "lessons": [
            {
                "code": "langgraph-agent-26-lesson-01",
                "title": "同步接口",
                "objectives": """1. 能把图包装成 FastAPI 接口，用请求体决定线程；
2. 能用 pydantic 做输入校验，并把图内部异常映射成合适的 HTTP 状态码；
3. 能说明「线程 ID 必须由服务端生成」的原因；
4. 能用 `TestClient` 在不起服务的情况下验证接口。""",
                "why_learn": """图跑通了不等于能用。前端要的是「一个 URL、一个 JSON」，还要处理超时、校验失败、内部错误。
这一节把图变成别人能调用的服务。""",
                "concepts": """**接口层职责**：校验输入、拼线程 ID、调用图、映射异常、裁剪输出。
**线程 ID**：`f"{user_id}:{conversation_id}"`，由服务端拼，不让客户端直接传。
**输入校验**：pydantic 的 `Field(min_length=..., max_length=...)`，失败自动 422。
**异常映射**：图内部异常 → 502（上游失败），请求不合法 → 422，找不到 → 404。
**`TestClient`**：直接用 app 构造客户端，不发真实网络请求，适合单测。
**返回值裁剪**：只回前端要的字段，不要把整个状态倒出去。""",
                "plain": """写接口最容易犯的错，是把「图怎么跑」直接搬进接口层：参数不校验、异常不分类、状态整份返回。

几件必须做的事其实很固定。

第一，线程 ID 服务端拼。客户端只传 `user_id`，会话标识由服务端组合。让客户端直接传 `thread_id`，
等于允许他读别人的会话——这是权限漏洞，不是技术细节。

第二，输入先校验再进图。长度、非空这些用 pydantic 声明，校验失败返回 422，比在图里抛错好查得多。

第三，异常要分类。图里调用外部服务失败，那是 502；用户参数不对，那是 422。全都 500 等于放弃排查。

第四，输出只给需要的字段。状态里有 `intent`、`docs` 这些内部结构，前端不需要，也不该看到。""",
                "syntax": """**最小接口**

```python
app = FastAPI()

class ChatIn(BaseModel):
    user_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=500)

@app.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn) -> ChatOut:
    cfg = {"configurable": {"thread_id": f"{payload.user_id}:default"}}
    try:
        out = graph.invoke({"messages": [HumanMessage(payload.question)]}, cfg)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="图执行失败") from exc
    return ChatOut(answer=out["messages"][-1].content, thread_id=..., messages=len(out["messages"]))
```

- 用 `response_model` 声明输出结构，FastAPI 会帮你裁剪与校验。
- 不要把内部异常原文透给用户，日志里留全量，响应里给摘要。
- 图是同步的，接口可以直接用 `def`；要并发靠 FastAPI 的线程池。""",
                "example_code": '''from typing import Annotated, TypedDict

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class EchoModel(BaseChatModel):
    """最小模型：每次返回一条全新的 AIMessage（新 id，不会被去重）。"""

    @property
    def _llm_type(self) -> str:
        return "echo"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=f"收到：{messages[-1].content}"))]
        )


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


model = EchoModel()


def agent(state: ChatState) -> dict:
    return {"messages": [model.invoke(state["messages"])]}


builder = StateGraph(ChatState)
builder.add_node("agent", agent)
builder.add_edge(START, "agent")
builder.add_edge("agent", END)
graph = builder.compile(checkpointer=InMemorySaver())

app = FastAPI()


class ChatIn(BaseModel):
    user_id: str = Field(min_length=1, description="用户标识，决定线程")
    question: str = Field(min_length=1, max_length=500, description="用户问题")


class ChatOut(BaseModel):
    answer: str
    thread_id: str
    messages: int


@app.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn) -> ChatOut:
    thread_id = f"{payload.user_id}:default"
    cfg = {"configurable": {"thread_id": thread_id}}
    try:
        out = graph.invoke({"messages": [HumanMessage(payload.question)]}, cfg)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"图执行失败：{exc}") from exc
    return ChatOut(
        answer=out["messages"][-1].content,
        thread_id=thread_id,
        messages=len(out["messages"]),
    )


client = TestClient(app)

print("=== 正常请求 ===")
r = client.post("/chat", json={"user_id": "u1", "question": "State 是什么"})
print("状态码:", r.status_code)
print("响应:", r.json())

print()
print("=== 第二次请求（同一线程）===")
r = client.post("/chat", json={"user_id": "u1", "question": "再说一遍"})
print("响应:", r.json())

print()
print("=== 换个用户（换线程）===")
r = client.post("/chat", json={"user_id": "u2", "question": "Node 是什么"})
print("响应:", r.json())

print()
print("=== 参数校验失败 ===")
r = client.post("/chat", json={"user_id": "", "question": "x"})
print("状态码:", r.status_code)
print("错误:", r.json()["detail"][0]["msg"])''',
                "code_lines": """1. `EchoModel` 每次返回**新的** `AIMessage`。这点很关键：若复用同一个消息对象，`add_messages` 会按 id 去重，历史会错乱。
2. 图只做一件事：把消息交给模型、写回状态。接口层的复杂度不在图里。
3. `build` 到 `graph` 用了 `InMemorySaver`：接口层靠 `thread_id` 找历史。
4. `ChatIn` 用 `Field` 声明长度约束，校验失败由 FastAPI 自动返回 422，不用自己写。
5. `thread_id` 由服务端用 `user_id` 拼出来，客户端无法指定「读哪条线程」。
6. `try/except` 把图内部异常包成 502，并保留 `from exc` 便于日志追溯。
7. `response_model=ChatOut` 让返回结构固定，`messages` 这类调试信息也在契约里。
8. 两次同一用户请求：消息数 2 → 4，说明检查点确实接上了历史；换 `u2` 又从 2 开始。
9. 空 `user_id` 得到 422 与 pydantic 的英文提示——生产环境通常要换成中文文案。""",
                "output": """# 程序输出
=== 正常请求 ===
状态码: 200
响应: {'answer': '收到：State 是什么', 'thread_id': 'u1:default', 'messages': 2}

=== 第二次请求（同一线程）===
响应: {'answer': '收到：再说一遍', 'thread_id': 'u1:default', 'messages': 4}

=== 换个用户（换线程）===
响应: {'answer': '收到：Node 是什么', 'thread_id': 'u2:default', 'messages': 2}

=== 参数校验失败 ===
状态码: 422
错误: String should have at least 1 character""",
                "mistakes": """- 让客户端直接传 `thread_id`：可以读别人的会话，属于越权漏洞。
- 复用同一个 `AIMessage` 对象：`add_messages` 按 id 去重，历史里只剩一条，`[-1]` 拿到的是用户消息。
- 图内部异常直接 500：分不清是用户参数问题还是上游故障。
- 把整个状态作为响应：内部字段泄露，且响应体随时间无端变大。
- 在接口层做业务判断（比如自己判断 intent）：图和接口的职责混在一起，两边都难测。
- 每次请求都 `compile` 一次图：检查点实例被重建，历史全丢。""",
                "error_analysis": """`ValueError: No checkpointer set`
—— 接口里 `graph` 是没带检查点的那个。检查 `compile` 的位置，别在请求函数里重新编译。

响应里 `answer` 是用户的提问
—— `messages[-1]` 不是回答。多半是消息对象复用导致去重，或节点没写回 AI 消息。

`422 Unprocessable Entity`
—— 请求体字段缺失或类型不对。看 `detail` 里的字段名。

`502` 出现但日志里没有细节
—— `HTTPException` 的 `detail` 是给用户看的，异常栈要单独记日志。""",
                "beginner_practice": """1. 给 `ChatIn` 加一个 `conversation_id: str = "default"`，让 `thread_id` 支持多会话。
2. 把 `except` 分支改成记日志 + 返回固定文案，确认响应里不再出现异常原文。""",
                "advanced_practice": """设计接口层的错误码约定：参数错、未授权、图内部失败、上游超时分别用什么状态码与错误体。
说明前端如何据此决定「重试」还是「提示用户改输入」。""",
                "quiz_note": "本节 6 道题：2 道基础理解（线程 ID 该谁生成、422 从哪来）+ 2 道代码阅读（为什么消息数是 4、为什么必须每次返回新消息对象）+ 2 道应用练习（补多会话、设计错误码）。",
                "summary": """接口层只做四件事：校验、拼线程、调用、映射。
`thread_id` 由服务端生成，客户端只给 `user_id`。
返回结构用 `response_model` 固定，内部字段不外泄。""",
                "next_lesson": "同步接口要等全部跑完。下一节用 SSE 把进度一段段推出去。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-26-01",
                        "name": "同步接口",
                        "goal": "能把图包成带校验与错误映射的 FastAPI 接口。",
                        "minutes": 45,
                        "criteria": "能说明线程 ID 的生成位置，并用 `TestClient` 验证。",
                        "requires": ["langgraph-agent-25-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-26-01-1",
                        "kp": 0,
                        "title": "支持多会话",
                        "description": "现有接口只能一个用户一条会话。加 `conversation_id`，并保证不同会话互不干扰。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class ChatIn(BaseModel):
    user_id: str = Field(min_length=1)
    conversation_id: str = Field(default="default", max_length=64)
    question: str = Field(min_length=1, max_length=500)


@app.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn) -> ChatOut:
    thread_id = f"{payload.user_id}:{payload.conversation_id}"
    cfg = {"configurable": {"thread_id": thread_id}}
    ...
    return ChatOut(answer=..., thread_id=thread_id, messages=...)''',
                        "explanation": "`conversation_id` 只允许有限长度、不允许包含分隔符（可再加校验），否则能构造出别人的线程 ID。",
                    },
                    {
                        "code": "lg-ex-26-01-2",
                        "kp": 0,
                        "title": "错误码怎么分",
                        "description": "给出四类错误的状态码与响应体，并说明前端该不该重试。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """① 参数不合法 → 422。响应体带字段名与原因。前端不重试，提示用户改输入。

② 未登录或越权 → 401 / 403。前端跳登录或提示无权限，不重试。

③ 图内部失败（模型超时、上游 5xx）→ 502，响应体给「临时故障，请稍后重试」。
前端可以重试，但要有次数上限与退避。

④ 请求过于频繁 → 429，带 `Retry-After`。前端按提示等待。

原则：状态码表达「谁的问题」。4xx 是调用方的问题，不该重试；5xx 是服务方的问题，可以退避重试。

另外：错误体用固定结构（`{"code": "...", "message": "..."}`），别只给一段自由文本，
否则前端只能靠匹配字符串做判断。""",
                        "explanation": "错误码是接口契约的一部分，前端据此决定「重试、改输入、还是找客服」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-26-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`thread_id` 应该由谁生成？",
                        "options": [
                            ("A", "客户端自由传入"),
                            ("B", "服务端用 `user_id`（加会话标识）拼出来"),
                            ("C", "随机生成，不用保存"),
                            ("D", "用请求时间戳"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "让客户端直接传线程标识，等于允许读别人的会话。会话归属必须由服务端决定。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-26-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`user_id` 传空字符串时，接口会进入图执行并最终返回 200。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`Field(min_length=1)` 让 FastAPI 在进入函数之前就返回 422，图根本不会执行。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-26-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "同一用户第二次请求返回 `messages: 4`，说明什么？",
                        "options": [
                            ("A", "检查点按线程累积了历史"),
                            ("B", "模型一次生成两条消息"),
                            ("C", "接口把请求发了两次"),
                            ("D", "`add_messages` 会复制消息"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "两轮各产生「用户消息 + 回答」，共 4 条。线程隔离让 `u2` 从 2 开始。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-26-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例里 `EchoModel._generate` 每次都新建 `AIMessage`，为什么这很重要？",
                        "options": [
                            ("A", "新建对象更快"),
                            ("B", "复用同一个消息对象会让 id 相同，`add_messages` 按 id 去重，历史会错乱"),
                            ("C", "只有新建的对象才能被序列化"),
                            ("D", "因为 `ChatResult` 要求唯一对象"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "去重是 `add_messages` 的正常行为，用于更新同一条消息。复用对象时它把「追加」变成了「替换」，`[-1]` 可能拿到用户消息。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-26-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么接口层不该做业务判断（比如自己判断用户问的是概念还是章节）？",
                        "options": [],
                        "answer": """三个理由。

① 双份真相：判断逻辑写两遍，改一处忘另一处，行为就不一致了。图里分类错了，接口层又判一遍，
最后没人说得清以谁为准。

② 不可测试：接口层的判断藏在 HTTP 处理函数里，只能通过发请求来测；放进图里，可以单独断言节点行为。

③ 无法复用：换个入口（CLI、定时任务、别的服务）就要再写一遍。

正确分工：接口层负责「协议」——校验、鉴权、错误码、序列化；图负责「业务」——分类、检索、生成、审批。

判断标准：把这段逻辑删掉，接口还能不能正常工作？如果只是少了业务能力，那它就该在图里。""",
                        "explanation": "分层的目的不是整齐，而是让每层都能被单独替换与验证。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-26-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个 `/chat` 接口：校验 `user_id` 与 `question`，拼线程，调用图，返回回答与消息数。",
                        "options": [],
                        "answer": {
                            "value": "@app.post(\"/chat\", response_model=ChatOut)\ndef chat(payload: ChatIn) -> ChatOut:\n    thread_id = f\"{payload.user_id}:default\"\n    cfg = {\"configurable\": {\"thread_id\": thread_id}}\n    try:\n        out = graph.invoke({\"messages\": [HumanMessage(payload.question)]}, cfg)\n    except Exception as exc:\n        raise HTTPException(status_code=502, detail=\"图执行失败\") from exc\n    return ChatOut(\n        answer=out[\"messages\"][-1].content,\n        thread_id=thread_id,\n        messages=len(out[\"messages\"]),\n    )"
                        },
                        "explanation": "四个动作：拼线程、调用、包异常、裁输出。注意 `from exc` 保留因果链，日志里才看得到根因。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-26-lesson-02",
                "title": "SSE 流式接口",
                "objectives": """1. 能用 `StreamingResponse` 把图的流式输出转成 SSE；
2. 能说清 `media_type` 与响应头的设置要求；
3. 能用 `TestClient` 逐行读取并断言 SSE 内容；
4. 能处理流式过程中的异常与结束信号。""",
                "why_learn": """一个要跑十几秒的 Agent，用户看不到进展就会以为卡死。SSE 是浏览器原生支持的推送方式，
改动小、部署简单，是最划算的方案。""",
                "concepts": """**`StreamingResponse(gen(), media_type="text/event-stream")`**：把生成器的产出逐块写回。
**生成器即接口**：`yield` 什么就发什么，帧格式要自己拼。
**`astream` / `stream`**：同步接口用 `graph.stream`，异步接口用 `graph.astream`。
**`updates` 可能为 `None`**：节点返回空时 payload 是 `None`，取值前要判断。
**`TestClient.stream(...)`**：配合 `iter_lines()` 在测试里逐行断言。
**结束信号**：一定要发，客户端才知道「跑完了」。""",
                "plain": """SSE 接口的写法看着简单：一个生成器、一个 `StreamingResponse`，剩下的全是帧格式。

真正容易出问题的是三处。

第一处，`updates` 的 payload 可能是 `None`。节点返回空字典或 `None` 时，`chunk` 里对应值是 `None`，
你直接 `update["messages"]` 就会 `TypeError`。加一个 `isinstance` 判断就解决了。

第二处，异常。流一旦开始，状态码已经发出去了。后面出错只能 `yield` 一个 `error` 事件，
然后在 `finally` 里补 `done`，否则客户端会一直等。

第三处，代理缓冲。`text/event-stream` 要求中间层不缓冲，很多网关默认会攒一批再发，
表现是「进度条过了十秒才一起跳」。需要时得配置 `X-Accel-Buffering: no` 之类的响应头。

这三处都不是「框架问题」，是流式接口本身的工程细节。""",
                "syntax": """**接口骨架**

```python
@app.post("/chat/stream")
def chat_stream(payload: ChatIn) -> StreamingResponse:
    def events():
        yield "event: open\\ndata: {}\\n\\n"
        for mode, chunk in graph.stream(inp, cfg, stream_mode=["updates", "custom"]):
            ...
            yield f"event: {name}\\ndata: {json.dumps(data, ensure_ascii=False)}\\n\\n"
        yield "event: done\\ndata: [DONE]\\n\\n"

    return StreamingResponse(events(), media_type="text/event-stream")
```

- `media_type` 必须是 `text/event-stream`，否则浏览器不按 SSE 处理。
- 异步接口用 `async def` + `graph.astream`，同步生成器放进异步路由会被线程池接管，注意别混用。
- 测试用 `client.stream(...)` + `resp.iter_lines()`，别用 `iter_text()`（当前 httpx 版本行为不一致）。""",
                "example_code": '''import json
from typing import Annotated, TypedDict

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


model = FakeMessagesListChatModel(responses=[AIMessage(content="先查资料，再回答。")])


def agent(state: ChatState) -> dict:
    writer = get_stream_writer()
    writer({"stage": "思考中"})
    reply = model.invoke(state["messages"])
    writer({"stage": "已生成回答"})
    return {"messages": [reply]}


builder = StateGraph(ChatState)
builder.add_node("agent", agent)
builder.add_edge(START, "agent")
builder.add_edge("agent", END)
graph = builder.compile(checkpointer=InMemorySaver())

app = FastAPI()


class ChatIn(BaseModel):
    user_id: str
    question: str


@app.post("/chat/stream")
def chat_stream(payload: ChatIn) -> StreamingResponse:
    cfg = {"configurable": {"thread_id": f"{payload.user_id}:default"}}

    def events():
        yield "event: open\\ndata: {}\\n\\n"
        for mode, chunk in graph.stream(
            {"messages": [HumanMessage(payload.question)]},
            cfg,
            stream_mode=["updates", "custom"],
        ):
            if mode == "custom":
                yield f"event: progress\\ndata: {json.dumps(chunk, ensure_ascii=False)}\\n\\n"
            else:
                for node, update in chunk.items():
                    text = update["messages"][-1].content
                    payload_out = {"node": node, "text": text}
                    yield f"event: message\\ndata: {json.dumps(payload_out, ensure_ascii=False)}\\n\\n"
        yield "event: done\\ndata: [DONE]\\n\\n"

    return StreamingResponse(events(), media_type="text/event-stream")


client = TestClient(app)
print("=== 原始 SSE 文本 ===")
with client.stream("POST", "/chat/stream", json={"user_id": "u1", "question": "讲讲 State"}) as resp:
    print("状态码:", resp.status_code, "| 类型:", resp.headers["content-type"])
    for line in resp.iter_lines():
        print(repr(line))''',
                "code_lines": """1. 图里只有一个 `agent` 节点，但它在模型调用前后各发一条进度事件——这就是 `custom` 的用法。
2. `chat_stream` 里的 `events()` 是生成器：`yield` 一个字符串，就写一段响应体。
3. 第一帧是 `open`，让前端确认连接建立；最后是 `done`，让前端知道结束。
4. `graph.stream(..., stream_mode=["updates", "custom"])` 同时拿两种事件，按 `mode` 分开拼帧。
5. `json.dumps(..., ensure_ascii=False)` 保留中文可读性；`\\n\\n` 是帧分隔，不能省。
6. `media_type="text/event-stream"` 决定浏览器按 SSE 解析；打印出来的 `content-type` 还带了 `charset=utf-8`。
7. `TestClient.stream(...)` 用 `iter_lines()` 逐行读，`repr` 让空行显形——空行就是帧边界。
8. 可以看到 `progress` 与 `message` 交错出现：事件按真实发生顺序推送，不受订阅列表顺序影响。""",
                "output": """# 程序输出
=== 原始 SSE 文本 ===
状态码: 200 | 类型: text/event-stream; charset=utf-8
'event: open'
'data: {}'
''
'event: progress'
'data: {"stage": "思考中"}'
''
'event: progress'
'data: {"stage": "已生成回答"}'
''
'event: message'
'data: {"node": "agent", "text": "先查资料，再回答。"}'
''
'event: done'
'data: [DONE]'
''""",
                "mistakes": """- `media_type` 写成 `application/json`：浏览器不按 SSE 处理，`EventSource` 收不到。
- 帧结尾只写一个 `\\n`：两条事件粘连，前端解析乱码。
- 直接 `update["messages"]`：`updates` 的 payload 可能是 `None`（节点返回空时），报 `TypeError`。
- 流开始后抛异常：状态码已经发出，客户端只能看到断连。要在生成器里捕获并 `yield` 错误帧。
- 忘记发 `done`：前端只能靠超时判断结束。
- 在 `async def` 里调同步的 `graph.stream`：阻塞事件循环；要么用 `def`，要么用 `astream`。
- 网关缓冲：进度一次性到达。需要时加 `X-Accel-Buffering: no`。""",
                "error_analysis": """`TypeError: argument of type 'NoneType' is not a container or iterable`
—— `updates` 里某个节点的 payload 是 `None`。加 `isinstance(update, dict)` 判断。

客户端收到 200 但没有任何事件
—— 要么生成器没产出（配置错了模式），要么被代理缓冲。先看服务端日志有没有执行。

`EventSource` 立刻断开
—— `content-type` 不对，或中间层不支持长连接。

`RuntimeError: no active stream writer`
—— writer 在节点外调用。`get_stream_writer()` 只在节点执行期间有效。""",
                "beginner_practice": """1. 在 `events()` 里加一个 `try/except`，让异常时 `yield` 一个 `error` 帧。
2. 把 `media_type` 改成 `text/plain`，观察 `content-type` 与客户端行为。""",
                "advanced_practice": """把接口改成异步：`async def` + `graph.astream`，并说明为什么不能在异步函数里直接 `for chunk in graph.stream(...)`。
写完后对比两种实现的内存占用与吞吐。""",
                "quiz_note": "本节 6 道题：2 道基础理解（`media_type` 的作用、为什么要发 `done`）+ 2 道代码阅读（为什么用 `iter_lines`、`updates` 为 `None` 时怎么办）+ 2 道应用练习（补错误帧、改成异步）。",
                "summary": """`StreamingResponse(events(), media_type="text/event-stream")`，生成器 yield 什么就发什么。
帧 = `event:` + `data:` + 空行；`updates` 的 payload 可能为 `None`。
流开始后只能靠事件表达错误，不能改状态码。""",
                "next_lesson": "接口能用了，下一章补上最后一块：怎么在没有真模型的情况下测住这些行为。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-26-02",
                        "name": "SSE 流式接口",
                        "goal": "能把图的流式输出转成 SSE 并处理异常。",
                        "minutes": 45,
                        "criteria": "能写对帧格式、`media_type` 与结束信号，并用测试逐行断言。",
                        "requires": ["langgraph-agent-26-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-26-02-1",
                        "kp": 0,
                        "title": "补错误帧",
                        "description": "现有生成器出错会直接断连。改成发一个 `error` 帧再发 `done`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def events():
    try:
        yield "event: open\\ndata: {}\\n\\n"
        for mode, chunk in graph.stream(inp, cfg, stream_mode=["updates", "custom"]):
            ...
            yield frame
    except Exception as exc:
        payload = {"message": "生成失败，请稍后重试"}
        yield f"event: error\\ndata: {json.dumps(payload, ensure_ascii=False)}\\n\\n"
    finally:
        yield "event: done\\ndata: {}\\n\\n"''',
                        "explanation": "`finally` 保证无论成功失败都发 `done`；`error` 的内容要脱敏，异常细节进日志。",
                    },
                    {
                        "code": "lg-ex-26-02-2",
                        "kp": 0,
                        "title": "同步还是异步",
                        "description": "为什么不能在 `async def` 里直接 `for chunk in graph.stream(...)`？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """因为 `graph.stream` 是同步阻塞调用：它内部会等模型与工具，期间一直占着线程。

在 `async def` 里这么写，整个事件循环被堵住，其他请求全部排队。
症状是「一个人在用流式，别人连不上」——并发压测时特别明显。

三种正确做法：

① 路由用 `def`（同步）：FastAPI 会把整个处理函数丢进线程池，不阻塞事件循环。示例就是这个写法。

② 用 `async def` + `graph.astream`：真正异步，最推荐用于高并发。

③ 用 `async def` + `run_in_threadpool` 包住同步生成器：可行但多一层，不如直接 `astream`。

如果图里有同步的工具或阻塞的 HTTP 调用，`astream` 也只是把阻塞点挪了位置，
仍然要考虑用异步客户端（`httpx.AsyncClient`）。""",
                        "explanation": "流式接口的并发问题，几乎都来自「同步调用跑在事件循环里」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-26-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`StreamingResponse` 的 `media_type` 应该设成什么？",
                        "options": [
                            ("A", "`application/json`"),
                            ("B", "`text/event-stream`"),
                            ("C", "`text/plain`"),
                            ("D", "`multipart/form-data`"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "只有这个类型浏览器才按 SSE 解析并触发 `EventSource` 事件。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-26-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "流式响应开始后如果发生异常，应该把 HTTP 状态码改成 500。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "响应头已经发出，状态码改不了。只能用 `error` 事件表达失败，再补 `done`。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-26-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "测试里为什么用 `resp.iter_lines()` 而不是 `iter_text()`？",
                        "options": [
                            ("A", "`iter_lines` 更快"),
                            ("B", "SSE 以行与空行分隔，逐行读才能看到帧边界；且当前 httpx 版本的 `iter_text` 在流式响应上行为不一致"),
                            ("C", "`iter_text` 不支持中文"),
                            ("D", "`iter_lines` 会自动解析 JSON"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`iter_text` 在当前 httpx 版本上会直接抛错（示例实测）。逐行读还能用 `repr` 看清空行。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-26-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`updates` 模式下 `update` 为 `None` 时，代码会发生什么？",
                        "options": [
                            ("A", "静默跳过"),
                            ("B", "`TypeError: argument of type 'NoneType' is not a container`"),
                            ("C", "返回空字符串"),
                            ("D", "框架自动补一个空字典"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "节点返回空时 payload 就是 `None`。取值前要 `isinstance(update, dict)` 判断。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-26-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么流式接口一定要发结束事件？",
                        "options": [],
                        "answer": """因为客户端无法区分「还在跑」和「已经断了」。

没有结束事件时，前端只能设一个超时。超时设短了，长任务被误判为失败；
设长了，真失败时用户要干等几十秒。两种体验都很差。

结束事件还承担两件事：

① 释放资源：前端可以关掉连接、停掉加载动画、把「生成中」改成「已完成」。

② 传递最终状态：成功还是失败、消息 id、用量统计，都可以挂在最后一个事件上。

实践中建议同时发 `error` 与 `done`：`error` 说明原因，`done` 表示这次流到此为止。
用 `finally` 保证 `done` 一定发出，哪怕前面抛了异常。""",
                        "explanation": "流式协议里，「结束」是一个必须被显式表达的状态。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-26-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个 SSE 生成器：先发 `open`，再按 `updates` 发 `message`，最后发 `done`。",
                        "options": [],
                        "answer": {
                            "value": "def events():\n    yield \"event: open\\ndata: {}\\n\\n\"\n    for mode, chunk in graph.stream(inp, cfg, stream_mode=[\"updates\", \"custom\"]):\n        if mode == \"custom\":\n            yield f\"event: progress\\ndata: {json.dumps(chunk, ensure_ascii=False)}\\n\\n\"\n        else:\n            for node, update in chunk.items():\n                if isinstance(update, dict) and \"answer\" in update:\n                    data = {\"node\": node, \"text\": update[\"answer\"]}\n                    yield f\"event: message\\ndata: {json.dumps(data, ensure_ascii=False)}\\n\\n\"\n    yield \"event: done\\ndata: {}\\n\\n\""
                        },
                        "explanation": "注意 `isinstance` 判断与结尾 `\\n\\n`。少了判断会崩，少了空行会粘帧。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 27 章
    {
        "code": "langgraph-agent-27",
        "order_index": 27,
        "title": "LangGraph 测试",
        "description": "不打真实模型，也能测出图的行为。",
        "lessons": [
            {
                "code": "langgraph-agent-27-lesson-01",
                "title": "离线测试与断言",
                "objectives": """1. 能用假模型把图的行为固定下来，做到可复现；
2. 会写四类断言：消息序列、工具回填、线程隔离、中断恢复；
3. 能说明「测图」与「测模型效果」是两件事，方法不同；
4. 能列出至少三个「看起来能过、实际没测到」的假测试。""",
                "why_learn": """图接错一条边，可能线上跑一周才发现。离线测试是唯一能在提交前发现结构错误的手段，
而且它比联调快两个数量级——不用网络、不花钱、结果稳定。""",
                "concepts": """**假模型**：`FakeMessagesListChatModel` 按剧本返回，或用自定义 `BaseChatModel` 返回固定内容。
**断言对象**：消息类型序列、`tool_call_id` 配对、线程隔离、`__interrupt__` 与 `next`。
**可复现**：同一份剧本每次结果相同，失败就是真 bug。
**分层**：结构用假模型测；效果（回答质量）用评测集测，两者不要混。
**独立存储**：每个测试用独立 `thread_id`，避免相互污染。
**别断言全文**：断言「包含关键信息」「类型正确」，比断言整段中文更稳。""",
                "plain": """测试图的核心思路是：把不确定的东西换成确定的，然后断言结构。

模型是不确定的，就换成一个按剧本说话的假模型；网络是不确定的，就不发网络请求；
时间是不确定的，就用独立的线程 ID，让每个用例互不干扰。

断言什么？不是「回答写得对不对」，而是「流程走对了没」：
消息类型是不是 `Human → AI → Tool → AI`、`tool_call_id` 有没有对上、
挂起时 `next` 指向谁、恢复后有没有跑完。

这些断言有个共同点：它们和模型说什么无关。所以假模型足够，也不会频繁失效。

最后一件事：别写「看起来能过」的测试。比如只断言 `status_code == 200`，
或者只断言 `len(messages) > 0`——这种测试在真正的 bug 面前一样是绿的。""",
                "syntax": """**四类断言**

```python
# 1. 消息序列
assert [type(m).__name__ for m in out["messages"]] == ["HumanMessage", "AIMessage"]

# 2. 工具回填
tools = [m for m in out["messages"] if isinstance(m, ToolMessage)]
assert tools[0].tool_call_id == "c1"

# 3. 线程隔离
out_b = graph.invoke(..., {"configurable": {"thread_id": "b"}})
assert len(out_b["messages"]) == 2

# 4. 中断恢复
assert "__interrupt__" in out
assert graph.get_state(cfg).next == ("review",)
```

- 用 `pytest` 运行时，测试函数名以 `test_` 开头、用 `assert` 即可。
- 每个用例用不同 `thread_id`，或每个用例新建一个 `InMemorySaver`。
- 断言里带一句中文说明（`assert cond, "说明"`），失败时能直接看懂。""",
                "example_code": '''from typing import Annotated, TypedDict

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt


@tool
def search_course(keyword: str) -> str:
    """按关键词检索课程资料。"""
    return "第 6 章 State：状态结构"


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


def build_agent(responses):
    model = FakeMessagesListChatModel(responses=responses)

    def agent(state: ChatState) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    builder = StateGraph(ChatState)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode([search_course]))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=InMemorySaver())


class Review(TypedDict):
    action: str
    decision: str


def review_node(state: Review) -> dict:
    return {"decision": interrupt({"action": state["action"]})}


rb = StateGraph(Review)
rb.add_node("review", review_node)
rb.add_edge(START, "review")
rb.add_edge("review", END)
review_graph = rb.compile(checkpointer=InMemorySaver())


def test_agent_replies_without_tools():
    graph = build_agent([AIMessage(content="State 是节点之间传递的数据。")])
    out = graph.invoke({"messages": [HumanMessage("State 是什么")]}, {"configurable": {"thread_id": "t1"}})
    assert len(out["messages"]) == 2
    assert out["messages"][-1].content.startswith("State")


def test_tool_result_is_linked_by_id():
    graph = build_agent([
        AIMessage(content="", tool_calls=[{"name": "search_course", "args": {"keyword": "state"}, "id": "c1"}]),
        AIMessage(content="在第 6 章。"),
    ])
    out = graph.invoke({"messages": [HumanMessage("State 在哪")]}, {"configurable": {"thread_id": "t2"}})
    tool_msgs = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].tool_call_id == "c1"
    assert tool_msgs[0].name == "search_course"


def test_threads_are_isolated():
    graph = build_agent([AIMessage(content="第一次回答"), AIMessage(content="第二次回答")])
    graph.invoke({"messages": [HumanMessage("问题一")]}, {"configurable": {"thread_id": "a"}})
    out_b = graph.invoke({"messages": [HumanMessage("问题二")]}, {"configurable": {"thread_id": "b"}})
    assert len(out_b["messages"]) == 2, "新线程不该带别人的历史"


def test_review_pauses_and_resumes():
    cfg = {"configurable": {"thread_id": "r1"}}
    out = review_graph.invoke({"action": "退款 199 元", "decision": ""}, cfg)
    assert "__interrupt__" in out
    assert review_graph.get_state(cfg).next == ("review",), "挂起时 next 指向未完成的节点"
    out2 = review_graph.invoke(Command(resume="同意"), cfg)
    assert out2["decision"] == "同意"
    assert review_graph.get_state(cfg).next == (), "恢复后应该跑完"


def run_all():
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
                passed += 1
            except AssertionError as exc:
                print(f"FAIL {name}: {exc}")
                failed += 1
    print(f"\\n{passed} passed, {failed} failed")


run_all()''',
                "code_lines": """1. `build_agent` 接收「剧本」，每次调用都新建模型与图——用例之间不共享状态。
2. 第一个用例断言「两条消息，且最后一条是回答」，这是最小结构断言。
3. 第二个用例让模型先给一个 `tool_calls`，再给最终回答；`ToolNode` 负责执行并回填。
4. 断言 `tool_call_id == "c1"` 是核心：它验证「结果配回了正确的调用」，而不是「有工具消息」。
5. 第三个用例故意让两个线程说不同的话，断言新线程只有 2 条消息。
6. 第四个用例先断言 `__interrupt__` 存在、`next` 指向 `review`，再断言恢复后 `next` 为空。
7. `run_all` 用 `globals()` 收集 `test_` 开头的函数逐个执行——等价于 pytest 的收集过程，便于离线演示。
8. 真实项目把这四个函数放进 `test_agent.py`，用 `pytest` 运行，无需改一行断言。""",
                "output": """# 程序输出
PASS test_agent_replies_without_tools
PASS test_review_pauses_and_resumes
PASS test_threads_are_isolated
PASS test_tool_result_is_linked_by_id

4 passed, 0 failed""",
                "mistakes": """- 用真模型写单测：结果不稳定、要网络、花钱，失败时说不清是图错还是模型变了。
- 只断言 `len(messages) > 0`：等于什么都没测，图接错也能过。
- 断言整段中文回答：模型换个措辞就红，维护成本极高。
- 所有用例共用一个 `thread_id`：前一个用例的历史污染后一个（这正好是「线程隔离」反例）。
- 只测 happy path：不测「工具报错」「中断恢复」「拒绝路径」，线上第一天才发现。
- 在测试里 sleep 等异步任务：要么用同步接口，要么用 `await`，别靠睡。
- 把 `assert` 写成 `if ...: print(...)`：不会让测试失败，等于没断言。""",
                "error_analysis": """测试全绿但线上报错
—— 断言的粒度太粗，或只覆盖了 happy path。补「工具失败」「拒绝」「超时」用例。

`AssertionError` 但看不出哪里错
—— 断言没带说明。写成 `assert cond, "期望 X，实际 Y"`。

用例之间互相影响
—— 共享了 `thread_id` 或共享了 saver 实例。每个用例独立。

`IndexError: list index out of range`
—— 消息条数比预期少，通常是剧本条数不够（模型还没给最终回答就用完了）。

`GraphRecursionError`
—— 剧本一直给 `tool_calls`，循环停不下来。检查最后一条是不是纯文本回答。""",
                "beginner_practice": """1. 给 `test_agent_replies_without_tools` 加一条断言：第一条消息是 `HumanMessage`。
2. 故意把剧本里的最终回答改成 `tool_calls`，观察哪个用例变红、报什么错。""",
                "advanced_practice": """设计一套「图级回归测试」：用 10 条固定问题跑同一张图，把消息类型序列快照下来，
下次改动图时自动对比。说明快照该存哪些字段、遇到合法变更时如何更新。""",
                "quiz_note": "本节 6 道题：2 道基础理解（为什么要用假模型、断言该断什么）+ 2 道代码阅读（`tool_call_id` 断言的意义、共用 `thread_id` 的后果）+ 2 道应用练习（补断言、设计回归测试）。",
                "summary": """测图 = 固定输入 + 断言结构，与模型说什么无关。
四类断言：消息序列、工具回填、线程隔离、中断恢复。
每个用例独立线程；断言带说明；别只测 happy path。""",
                "next_lesson": "零件全部齐了。下一章把它们装成一个能用的东西：个人 AI 学习 Agent。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-27-01",
                        "name": "离线测试与断言",
                        "goal": "能用假模型写出可复现的图级测试。",
                        "minutes": 40,
                        "criteria": "能写出四类断言，并说明为什么不该断言回答全文。",
                        "requires": ["langgraph-agent-26-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-27-01-1",
                        "kp": 0,
                        "title": "补一条结构断言",
                        "description": "给无工具用例补断言：第一条必须是 `HumanMessage`，最后一条必须是 `AIMessage`。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''def test_message_order():
    graph = build_agent([AIMessage(content="好的")])
    out = graph.invoke({"messages": [HumanMessage("你好")]}, {"configurable": {"thread_id": "t9"}})
    kinds = [type(m).__name__ for m in out["messages"]]
    assert kinds == ["HumanMessage", "AIMessage"], f"消息序列应为 Human->AI，实际 {kinds}"''',
                        "explanation": "断言类型序列比断言条数更强：条数对了但顺序错了，一样是 bug。",
                    },
                    {
                        "code": "lg-ex-27-01-2",
                        "kp": 0,
                        "title": "哪些是假测试",
                        "description": "判断下面三条断言哪些没有实际约束力：① `assert r.status_code == 200`；② `assert len(out[\"messages\"]) > 0`；③ `assert out[\"messages\"][-1].content == \"第 6 章 State：状态结构\"`。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """①② 基本没有约束力，③ 过强。

① 只验证「没崩」。图接错、答案为空、字段缺失，都可能还是 200。

② 只要有一条消息就过。用户消息本来就在状态里，这条断言在图什么都没做时也成立。

③ 太强：把整段内容写死，模型（或 Prompt）一改措辞就红。它测的是文案，不是逻辑。

更好的写法：

`assert kinds == ["HumanMessage", "AIMessage"]`
`assert isinstance(out["messages"][-1], AIMessage)`
`assert "第 6 章" in out["messages"][-1].content`

原则：断言**结构与关键信息**，不断言**措辞**。结构错了是 bug，措辞变了不是。""",
                        "explanation": "测试的价值不在于「能跑」，而在于「能红」——在真出问题时红。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-27-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "为什么图级测试要用假模型？",
                        "options": [
                            ("A", "因为假模型更聪明"),
                            ("B", "因为要断言的是图的结构行为，需要结果可复现"),
                            ("C", "因为真模型不支持工具调用"),
                            ("D", "因为假模型能自动修 bug"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "真模型有随机性，失败时无法区分是图接错还是模型变了。假模型把不确定性抽走。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-27-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "好的图级测试应该断言模型输出的完整中文文本。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "措辞会变。断言结构与关键信息（类型、`tool_call_id`、`next`、包含某关键词）才稳定。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-27-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`assert tool_msgs[0].tool_call_id == \"c1\"` 这条断言真正验证了什么？",
                        "options": [
                            ("A", "工具有没有被调用"),
                            ("B", "工具结果有没有配回正确的那次调用"),
                            ("C", "工具返回内容是否正确"),
                            ("D", "工具是否被注册"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "「有工具消息」很弱；「订单号对上了」才说明回填逻辑正确。一次多个调用时这条尤其关键。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-27-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "如果所有用例共用 `thread_id=\"t1\"`，最可能出现什么现象？",
                        "options": [
                            ("A", "测试变慢"),
                            ("B", "后跑的用例读到前面留下的历史，断言条数失败"),
                            ("C", "检查点自动清理"),
                            ("D", "没有影响，线程 ID 只影响日志"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "这正是「线程隔离」用例要防的问题：共享线程时消息会累积，条数断言随执行顺序变化，测试变得不可重复。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-27-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "「测图」和「测模型效果」有什么区别？各用什么方法？",
                        "options": [],
                        "answer": """两者目标不同，方法也不同。

**测图**（结构测试）：验证边接对没、消息序列对不对、状态合并是否符合预期、中断能否恢复。
用假模型 + 固定剧本 + 断言结构。特点是确定、快、免费，适合放进 CI，每次提交都跑。

**测效果**（质量评估）：验证回答准不准、有没有幻觉、工具选得对不对。
用真模型 + 评测集 + 打分（人工标注或 LLM 评审）。特点是带统计性质，有波动，适合定期跑、改动后对比。

混在一起的典型症状：用真模型写单测，结果「偶尔失败」，团队很快学会「重跑一次」，
从此这套测试就失去意义；或者只用假模型评估效果，永远发现不了 Prompt 变差。

正确做法是两层分开：结构层必须全绿才允许合并；效果层看趋势，允许小幅波动。""",
                        "explanation": "确定性验证与统计性评估不能混在一个套件里，否则两边都失效。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-27-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个测试：验证「工具不存在」时，`ToolNode` 会把错误包成 `ToolMessage` 而不是抛异常。",
                        "options": [],
                        "answer": {
                            "value": "def test_unknown_tool_returns_error_message():\n    graph = build_agent([\n        AIMessage(content=\"\", tool_calls=[{\"name\": \"nope\", \"args\": {}, \"id\": \"c9\"}]),\n        AIMessage(content=\"换个说法。\"),\n    ])\n    out = graph.invoke({\"messages\": [HumanMessage(\"x\")]}, {\"configurable\": {\"thread_id\": \"t8\"}})\n    tool_msgs = [m for m in out[\"messages\"] if isinstance(m, ToolMessage)]\n    assert len(tool_msgs) == 1, \"应该有一条工具消息\"\n    assert tool_msgs[0].status == \"error\", \"状态应为 error\"\n    assert \"not a valid tool\" in tool_msgs[0].content"
                        },
                        "explanation": "断言 `status == \"error\"` 比断言内容片段更稳；内容片段只用来确认「是这一类错误」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
