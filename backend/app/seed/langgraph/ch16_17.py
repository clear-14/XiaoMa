"""LangGraph Agent 开发：第 16—17 章。

第 16 章把模型接进图里：先看清它在节点里的位置，再写一个能真正对话的最小模型；
第 17 章让模型能「点菜」：把函数包装成工具、读懂返回的 `tool_calls`、按订单号回填结果。

版本口径（实测）：langgraph 1.2.20、langchain-core 1.7.6。
本章所有示例都用 `httpx.MockTransport` 跑离线假服务，不联网、不花额度。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 16 章
    {
        "code": "langgraph-agent-16",
        "order_index": 16,
        "title": "接入大模型",
        "description": "模型不是框架的一部分，它只是节点里的一次调用。",
        "lessons": [
            {
                "code": "langgraph-agent-16-lesson-01",
                "title": "ChatModel 抽象",
                "objectives": """1. 能说清 LangGraph 对模型没有任何要求，模型只是节点里的一次函数调用；
2. 能写出一个最小的 `BaseChatModel` 子类（`_llm_type` + `_generate`）；
3. 能解释 `_generate` 为什么必须返回 `ChatResult` 而不是 `AIMessage`；
4. 能说明把「组装消息」与「调模型」拆成两个节点的好处。""",
                "why_learn": """从这一章开始，图里第一次出现「不确定、要花钱、会失败」的外部调用。
把「框架负责的」和「模型负责的」分清楚，后面接工具、加重试、插人工审批才有着力点。""",
                "concepts": """**ChatModel**：统一接口。`invoke(messages)` 收一串消息，返回一条 `AIMessage`。
**三种消息**：`SystemMessage` 定规则；`HumanMessage` 是用户输入；`AIMessage` 是模型输出。
**子类只写两处**：`_llm_type`（一个字符串标签，只用于日志追踪）与 `_generate`（真正干活的方法）。
**返回格式固定**：`ChatResult(generations=[ChatGeneration(message=AIMessage(...))])`。
**框架不碰模型**：`StateGraph` 只调度节点，节点里调模型、查库、读文件没有区别。
**拆两个节点**：`prepare` 组装消息（纯函数，好测）；`call_model` 做外部调用（好替换、好打桩）。""",
                "plain": """LangGraph 根本不认识模型。它只关心两件事：状态里有什么、下一步去哪。
模型是某个节点函数里的一次普通调用，和你读一个文件、查一次数据库没有本质区别。

能理解这一点，就不会再问「LangGraph 支持哪些模型」——它一个都不支持，也一个都不限制。
真正决定调谁、怎么调的，是你写在节点里的那几行代码。

示例里用的模型只会把最后一句话原样回显，它不联网、不花钱、每次输出都一样。
先用这种「假模型」把结构跑通，等结构对了再把真的换进去——这是排错时最省时间的顺序。""",
                "syntax": """**最小模型类的骨架**

```python
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class MyModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "my-model"          # 只用于日志与追踪，不影响行为

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # messages 是消息对象列表，不是字符串
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content="..."))]
        )
```

- `invoke`、`batch`、`stream` 都由基类提供，你不需要写。
- `_generate` 的签名要带 `**kwargs`，否则基类传参时会报 `TypeError`。
- `generations` 是列表：一次调用理论上可以返回多个候选，我们只用第一个。""",
                "example_code": '''from typing import TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, START, StateGraph


class EchoModel(BaseChatModel):
    """最小模型：把最后一条消息回显，用来观察模型在节点里怎么被调用。"""

    prefix: str = "（模型回复）"

    @property
    def _llm_type(self) -> str:
        return "echo"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        print("  模型收到：", [(type(m).__name__, m.content) for m in messages])
        text = messages[-1].content
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=f"{self.prefix}{text}"))]
        )


class AskState(TypedDict):
    question: str
    messages: list
    answer: str


model = EchoModel()


def prepare(state: AskState) -> dict:
    """把用户问题包成「系统提示 + 用户消息」。"""
    return {
        "messages": [
            SystemMessage("你是课程助教，回答不超过 30 字。"),
            HumanMessage(state["question"]),
        ]
    }


def call_model(state: AskState) -> dict:
    """节点里唯一的动作：调一次模型。"""
    ai = model.invoke(state["messages"])
    return {"messages": [ai], "answer": ai.content}


builder = StateGraph(AskState)
builder.add_node("prepare", prepare)
builder.add_node("call_model", call_model)
builder.add_edge(START, "prepare")
builder.add_edge("prepare", "call_model")
builder.add_edge("call_model", END)
graph = builder.compile()

result = graph.invoke({"question": "State 是什么", "messages": [], "answer": ""})
print("answer  :", result["answer"])
print("消息条数:", len(result["messages"]))
print()
print("直接调用模型：", model.invoke([HumanMessage("你好")]).content)
print("批处理：", [m.content for m in model.batch([[HumanMessage("A")], [HumanMessage("B")]])])''',
                "code_lines": """1. `EchoModel` 只实现两处：`_llm_type` 返回标签，`_generate` 返回固定格式的结果。
2. `_generate` 里打印收到的消息类型，是为了让你看到「模型拿到的是对象列表，不是一段字符串」。
3. `prefix` 是 pydantic 字段，构造时可以覆盖：`EchoModel(prefix="…")`。
4. `prepare` 是纯函数：输入一个问题，输出两条消息，没有副作用，所以能单独测试。
5. `prepare` 返回 `{"messages": [...]}`，直接写进状态。注意 `AskState.messages` 是普通 `list`，不是 `Annotated[list, add_messages]`，所以后写的会整体覆盖。
6. `call_model` 读 `state["messages"]`（此时是 `prepare` 写的那两条），调一次 `invoke`，再写回 `messages` 与 `answer`。
7. 结果是 1 条而不是 3 条：`call_model` 写的 `[AIMessage]` 把前两条覆盖了。想累积就得给字段配 `add_messages`（第 15 章）。
8. 最后两行证明：模型不经过图也能直接调，图只是替你把「什么时候调」安排好了。""",
                "output": """# 程序输出
  模型收到： [('SystemMessage', '你是课程助教，回答不超过 30 字。'), ('HumanMessage', 'State 是什么')]
answer  : （模型回复）State 是什么
消息条数: 1

  模型收到： [('HumanMessage', '你好')]
直接调用模型： （模型回复）你好
  模型收到： [('HumanMessage', 'A')]
  模型收到： [('HumanMessage', 'B')]
批处理： ['（模型回复）A', '（模型回复）B']""",
                "mistakes": """- 在 `_generate` 里直接 `return AIMessage(...)`，基类取不到 `generations`，报 `AttributeError`。
- `_generate` 的签名漏了 `**kwargs`，基类传入额外参数时报 `TypeError: unexpected keyword argument`。
- 把 `SystemMessage` 放在消息列表最后，模型把规则当成用户刚说的话。
- `call_model` 里写 `state["messages"].append(ai)` 再返回 `{}`：就地修改，下一轮读不到，还会污染历史快照。
- 每次调用都新建一个 HTTP 客户端，连接不复用，几十次请求就把句柄耗尽。
- 把 API Key 直接写进 `SystemMessage` 或代码常量——它会跟着日志和仓库一起泄露。""",
                "error_analysis": """`AttributeError: 'AIMessage' object has no attribute 'generations'`
—— `_generate` 返回类型错了。必须返回 `ChatResult(generations=[ChatGeneration(message=...)])`。

`TypeError: _generate() got an unexpected keyword argument 'stop'`
—— 签名没写全。照抄 `(self, messages, stop=None, run_manager=None, **kwargs)`。

模型「收到空列表」
—— 上游节点没把 `messages` 写进状态，或键名拼错被静默丢弃（第 12 章讲过未声明键会被丢掉）。

同一个问题两次回答不同
—— 真模型有随机性。示例用固定回复的假模型，就是为了让输出可复现、可断言。""",
                "beginner_practice": """1. 把 `EchoModel` 改成回复「收到 N 条消息：…」，让 N 随 `prepare` 的变化而变化。
2. 在 `prepare` 里再加一条 `SystemMessage`，观察打印出来的消息顺序与条数。""",
                "advanced_practice": """给 `AskState` 加一个 `history` 字段，让第二次提问时能把上一轮的问答一起送给模型。
写完后回答两个问题：历史该在哪一步裁剪长度？裁剪逻辑放在 `prepare` 还是单独一个节点？""",
                "quiz_note": "本节 6 道题：2 道基础理解（框架对模型的要求、`_generate` 的返回类型）+ 2 道代码阅读（`messages` 条数为什么是 1、打印顺序说明什么）+ 2 道应用练习（为什么要拆两个节点、手写一个最小模型）。",
                "summary": """模型不是框架的一部分，它只是节点里的一次调用。
子类写 `_llm_type` 与 `_generate`，返回 `ChatResult`。
组装消息与调用模型分成两个节点：前者好测，后者好替换。""",
                "next_lesson": "下一节把「假模型」换成真的：用 httpx 直连兼容接口，自己实现 `_generate`。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-16-01",
                        "name": "模型在节点中的角色",
                        "goal": "能写出最小 `BaseChatModel` 子类，并在节点里正确调用。",
                        "minutes": 40,
                        "criteria": "能说明 `_generate` 必须返回 `ChatResult`，并解释为什么要拆成两个节点。",
                        "requires": ["langgraph-agent-15-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-16-01-1",
                        "kp": 0,
                        "title": "让假模型回报条数",
                        "description": "改写 `EchoModel._generate`，让回复内容变成「收到 N 条消息」，N 是本次收到的消息条数。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''class CountModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "count"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        text = f"收到 {len(messages)} 条消息"
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=text))]
        )''',
                        "explanation": "关键是把 `len(messages)` 放进返回内容。它能立刻暴露「上游到底传了几条消息」这个最常见的问题。",
                    },
                    {
                        "code": "lg-ex-16-01-2",
                        "kp": 0,
                        "title": "为什么拆成两个节点",
                        "description": "把「组装消息」与「调用模型」写在同一个节点里也能跑。为什么示例要拆开？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """三个理由。

① 可测试性：`prepare` 是纯函数，测试它不用管网络；`call_model` 依赖外部服务，测试时需要打桩。
两者混在一起，一个纯逻辑的 bug 也要先搭好假服务才能测。

② 可观测性：消息组装错了，是 Prompt 问题；调用失败了，是网络或配额问题。拆开后，
在图上看得出停在哪一步，日志也能分层打。

③ 可替换性：想换模型、加超时、加重试，只动 `call_model`；想调 Prompt，只动 `prepare`。
不拆的话，每次改动都要重新理解整段函数。

代价是多一个节点、多一次状态合并。这点开销远小于「混在一起后每次改动都要通读全函数」。""",
                        "explanation": "这条分工在后面的重试与人工审批里会反复用到：能单独替换的步骤，才配得上单独的策略。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-16-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "LangGraph 对「你用什么模型」有什么要求？",
                        "options": [
                            ("A", "必须继承某个 LangGraph 专用的模型类"),
                            ("B", "没有要求，模型在节点函数里被调用即可"),
                            ("C", "必须支持流式输出"),
                            ("D", "必须支持工具调用"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "框架只调度节点与状态。模型用哪个库、什么协议，完全由节点里的代码决定。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-16-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`_generate` 可以直接返回一条 `AIMessage`。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "必须返回 `ChatResult`，`AIMessage` 包在 `ChatGeneration` 里再放进 `generations` 列表。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-16-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "初始 `messages` 是空列表，跑完后 `消息条数` 为什么是 1 而不是 3？",
                        "options": [
                            ("A", "因为 `prepare` 的两条被 `call_model` 写入的列表整体覆盖了"),
                            ("B", "因为 `END` 会清空历史消息"),
                            ("C", "因为 `ADD` 会合并重复消息"),
                            ("D", "因为 `invoke` 只接收最后一条消息"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`AskState.messages` 声明成普通 `list`，没有 `add_messages` reducer，所以每次写入都是覆盖：`prepare` 写 2 条，`call_model` 写 1 条，最终 1 条。要累积必须给字段配 `add_messages`（第 15 章）。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-16-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "打印里的「模型收到」出现了 `SystemMessage` 与 `HumanMessage` 两条，说明什么？",
                        "options": [
                            ("A", "模型自己生成了系统消息"),
                            ("B", "`prepare` 的返回值被合并进状态，`call_model` 从状态里读到了这两条"),
                            ("C", "`invoke` 会自动补一条系统消息"),
                            ("D", "`StateGraph` 会复制上游节点的输出"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "节点之间不直接传参，全部通过状态。`prepare` 写 `messages`，`call_model` 读 `messages`，这就是它们唯一的耦合方式。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-16-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么把「组装消息」和「调用模型」拆成两个节点，而不是写在一个节点里？",
                        "options": [],
                        "answer": """拆分换来三件事：可测试、可观测、可替换。

可测试：组装消息是纯函数，改一个 Prompt 不用起服务就能测；混在一起时，任何改动都要先搭假服务。

可观测：消息错了是 Prompt 问题，请求失败是网络或配额问题。拆开后图上看得出停在哪一步，日志能分层。

可替换：换模型、加超时、加重试只动 `call_model`；调 Prompt 只动 `prepare`。

代价是多一个节点、多一次状态合并。相比「每次改动都要通读整段函数」，这点代价很划算。""",
                        "explanation": "判断要不要拆的标准：这一步是不是需要独立的策略（重试、超时、审批）。需要，就拆。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-16-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个最小模型类 `FixedModel`：不管收到什么消息，都回复「我不知道」。",
                        "options": [],
                        "answer": {
                            "value": "from langchain_core.language_models.chat_models import BaseChatModel\nfrom langchain_core.messages import AIMessage\nfrom langchain_core.outputs import ChatGeneration, ChatResult\n\n\nclass FixedModel(BaseChatModel):\n    @property\n    def _llm_type(self) -> str:\n        return \"fixed\"\n\n    def _generate(self, messages, stop=None, run_manager=None, **kwargs):\n        return ChatResult(\n            generations=[ChatGeneration(message=AIMessage(content=\"我不知道\"))]\n        )"
                        },
                        "explanation": "两处必须写：`_llm_type` 与 `_generate`；返回值格式固定。`messages` 参数用不到也得留着，因为基类按位置传。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-16-lesson-02",
                "title": "接 OpenAI 兼容接口",
                "objectives": """1. 能把消息对象翻译成接口要的 `role / content` 结构；
2. 能实现 `_generate`，从 `choices[0].message` 取出回复；
3. 能用 `httpx.MockTransport` 在离线状态测通整条链路；
4. 能说明为什么把 `client` 注入模型类，而不是在方法里新建。""",
                "why_learn": """上一节的模型只会回显。真实的模型要通过 HTTP 调用：有请求体、有状态码、有超时、有配额。
这一节把这条链路亲手写一遍，之后不论换哪家服务，你都知道该改哪一行。""",
                "concepts": """**翻译层**：消息对象（`SystemMessage` 等）要变成 `{"role": ..., "content": ...}` 才能发出去。
**`_generate` 的职责**：发请求 → 检查状态码 → 取出 `choices[0].message` → 包成 `AIMessage`。
**`raise_for_status()`**：4xx/5xx 直接抛异常，别让错误响应被当成正常回复解析。
**`MockTransport`**：给 `httpx.Client` 换一个假的传输层，请求不出网，还能打印请求体。
**注入 client**：模型类只依赖一个 `client` 字段，测试塞假服务，上线塞真服务，代码不动。""",
                "plain": """模型类其实是个翻译官：把程序里的消息对象翻成接口能懂的 JSON，再把接口返回的 JSON 翻回消息对象。
翻译官不该自己造车——HTTP 连接要由外面递进来，这就是「注入 client」的意思。

为什么要用假服务？因为你要验证的是「翻译对不对」，不是「对方服务器活着没」。
假服务能把请求体原样打出来给你看，真服务做不到这一点。

等翻译确认无误，把 `transport` 那一行删掉、换成真的 base_url 和 Key，代码一个字都不用改。
这就是第 4C 阶段反复强调的：先让结构可测，再谈接真服务。""",
                "syntax": """**三块拼起来**

```python
def to_payload(messages):            # 1. 消息对象 -> 请求体
    ...

class CompatChatModel(BaseChatModel):  # 2. 实现 _generate
    model: str
    client: Any = None

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        resp = self.client.post("/chat/completions", json={"model": self.model,
                                                            "messages": to_payload(messages)})
        resp.raise_for_status()
        message = resp.json()["choices"][0]["message"]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=message.get("content") or ""))])

client = httpx.Client(base_url=..., transport=httpx.MockTransport(fake_server))  # 3. 假传输层
```

- `resp.json()["choices"][0]["message"]["content"]` 可能是 `None`，用 `or ""` 兜住。
- 真实服务要带 `headers={"Authorization": ...}`，Key 从环境变量读。
- `timeout=30.0` 必须显式设，默认值在长回复时会截断。""",
                "example_code": '''import json
import os
from typing import Any, TypedDict

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, START, StateGraph


def to_payload(messages: list[BaseMessage]) -> list[dict]:
    """把消息对象翻译成接口要的 role / content 结构。"""
    rows: list[dict] = []
    for m in messages:
        if isinstance(m, SystemMessage):
            rows.append({"role": "system", "content": m.content})
        elif isinstance(m, HumanMessage):
            rows.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            rows.append({"role": "assistant", "content": m.content or ""})
    return rows


class CompatChatModel(BaseChatModel):
    """直连 OpenAI 兼容接口的最小 ChatModel。"""

    model: str
    client: Any = None          # httpx.Client，注入进来便于替换成假服务

    @property
    def _llm_type(self) -> str:
        return "openai-compatible"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        payload = {"model": self.model, "messages": to_payload(messages)}
        resp = self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        message = resp.json()["choices"][0]["message"]
        ai = AIMessage(content=message.get("content") or "")
        return ChatResult(generations=[ChatGeneration(message=ai)])


def fake_server(request: httpx.Request) -> httpx.Response:
    """假服务：打印收到的请求体，返回一句固定回复。"""
    body = json.loads(request.content)
    print("  -> 请求体:", json.dumps(body, ensure_ascii=False))
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": "状态是节点之间传递的字典。"}}]},
    )


client = httpx.Client(
    base_url="https://api.example.com/v1",
    transport=httpx.MockTransport(fake_server),        # 换真实服务时删掉这一行
)
llm = CompatChatModel(model="chat-small", client=client)

print("=== 1. 直接调用模型 ===")
ai = llm.invoke([SystemMessage("你是助教"), HumanMessage("State 是什么")])
print("  content:", ai.content)
print("  类型   :", type(ai).__name__)

print()
print("=== 2. 放进图里 ===")


class AskState(TypedDict):
    question: str
    messages: list
    answer: str


def ask(state: AskState) -> dict:
    msgs = [SystemMessage("你是课程助教"), HumanMessage(state["question"])]
    reply = llm.invoke(msgs)
    return {"messages": msgs + [reply], "answer": reply.content}


builder = StateGraph(AskState)
builder.add_node("ask", ask)
builder.add_edge(START, "ask")
builder.add_edge("ask", END)
graph = builder.compile()

result = graph.invoke({"question": "State 是什么", "messages": [], "answer": ""})
print("  answer   :", result["answer"])
print("  消息条数 :", len(result["messages"]))

print()
print("=== 3. 换成真实服务只需要改 client ===")
real = httpx.Client(
    base_url=os.environ.get("LLM_BASE_URL", "https://api.example.com/v1"),
    headers={"Authorization": f"Bearer {os.environ.get('LLM_API_KEY', 'sk-local')}"},
    timeout=30.0,
)
print("  base_url:", real.base_url)
print("  timeout :", real.timeout)
real.close()''',
                "code_lines": """1. `to_payload` 只处理三种消息。新增消息类型（比如工具结果）时要同步扩展它，否则会被静默丢掉。
2. `CompatChatModel` 只有两个字段：`model` 名字与 `client`。后者是注入点，也是测试的接缝。
3. `_generate` 里先组 `payload` 再 `post`，把「组装」和「发送」写在两行，排错时能分别打断点。
4. `raise_for_status()` 是关键：没有它，404 的错误响应会被当成正常 JSON 去解析，报错信息会离真相很远。
5. `choices[0]["message"]["content"]` 用 `.get("content") or ""` 兜住 `None`——工具调用时 `content` 常常是空字符串。
6. `fake_server` 打印请求体：你因此能亲眼看到模型收到的是 `messages` 数组，而不是一段拼好的字符串。
7. 第二段把模型放进图里，说明「接入模型」和「写节点」是两件独立的事。
8. 第三段只换了 `client` 的构造参数，模型类与节点函数一行没改。""",
                "output": """# 程序输出
=== 1. 直接调用模型 ===
  -> 请求体: {"model": "chat-small", "messages": [{"role": "system", "content": "你是助教"}, {"role": "user", "content": "State 是什么"}]}
  content: 状态是节点之间传递的字典。
  类型   : AIMessage

=== 2. 放进图里 ===
  -> 请求体: {"model": "chat-small", "messages": [{"role": "system", "content": "你是课程助教"}, {"role": "user", "content": "State 是什么"}]}
  answer   : 状态是节点之间传递的字典。
  消息条数 : 3

=== 3. 换成真实服务只需要改 client ===
  base_url: https://api.example.com/v1/
  timeout : Timeout(timeout=30.0)""",
                "mistakes": """- 忘记 `raise_for_status()`：限流返回 429，代码却拿错误体去取 `choices`，报 `KeyError: 'choices'`。
- 把 `content` 当字符串直接拼接，遇到 `None` 就 `TypeError`。
- 用 `base_url` 拼出 `//chat/completions` 双斜杠，部分网关会 404。
- 把 `timeout` 留默认：长回答被截断，看起来像「模型答到一半停了」。
- 在 `_generate` 里 `print` 调试信息后忘记删，服务端日志被刷满（示例里是为了观察才打）。
- 每次请求新建 `httpx.Client`，连接不复用；正确做法是把 client 注入一次、用完关闭。""",
                "error_analysis": """`httpx.HTTPStatusError: Client error '401 Unauthorized'`
—— Key 没传或格式不对。检查 `Authorization: Bearer <key>` 与 Key 是否带多余空格。

`KeyError: 'choices'`
—— 响应不是预期结构。多半是状态码非 200 却没检查，先加 `raise_for_status()` 再打印 `resp.text`。

`httpx.ConnectTimeout`
—— 网络或超时设置问题。把 `timeout` 调到 30 秒以上再试，仍失败就检查出口网络。

`ValidationError: client Field required`
—— 构造模型时漏了 `client`。它是必填字段，不能靠方法里临时 new。""",
                "beginner_practice": """1. 让假服务返回 `content: null`，观察 `or ""` 兜底后 `ai.content` 是什么。
2. 在 `to_payload` 里加一条 `print(rows)`，确认多轮对话时 assistant 消息也被翻译了。""",
                "advanced_practice": """给 `_generate` 加上「响应里带 `usage` 时，把 token 数记到 `AIMessage.response_metadata`」。
写完后说明：为什么把用量放在消息上，而不是放在模型的实例属性里？""",
                "quiz_note": "本节 6 道题：2 道基础理解（`to_payload` 的职责、`raise_for_status` 的作用）+ 2 道代码阅读（为什么用 `MockTransport`、漏掉 `client` 会怎样）+ 2 道应用练习（补全多轮翻译、解释为什么不直接 `httpx.post`）。",
                "summary": """模型类 = 翻译（消息 ↔ JSON）+ 一次 HTTP 调用。
`client` 注入让「假服务」与「真服务」共用同一份代码。
`raise_for_status()` 与 `or ""` 是两个成本极低、收益极高的防御。""",
                "next_lesson": "模型能对话了，但还不会用工具。下一章把函数包装成工具，让它能「点菜」。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-16-02",
                        "name": "实现兼容接口的 ChatModel",
                        "goal": "能用 httpx 写出可离线测试的最小 ChatModel。",
                        "minutes": 45,
                        "criteria": "能解释 `_generate` 的每一步，并说明为什么要注入 `client`。",
                        "requires": ["langgraph-agent-16-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-16-02-1",
                        "kp": 0,
                        "title": "支持多轮的翻译函数",
                        "description": "现有 `to_payload` 已支持 system / user / assistant。补上「连续两轮问答」的输入，确认请求体里角色顺序正确。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''messages = [
    SystemMessage("你是课程助教"),
    HumanMessage("State 是什么"),
    AIMessage("State 是节点之间传递的数据。"),
    HumanMessage("那 Node 呢"),
]

print(json.dumps(to_payload(messages), ensure_ascii=False, indent=2))
# 期望角色顺序：system, user, assistant, user''',
                        "explanation": "多轮的关键是 assistant 的历史回复必须原样带回，否则模型看不到自己上一轮说过什么，会出现自相矛盾的回答。",
                    },
                    {
                        "code": "lg-ex-16-02-2",
                        "kp": 0,
                        "title": "为什么不直接 httpx.post",
                        "description": "既然 `_generate` 里就是一次 post，为什么还要继承 `BaseChatModel`？直接写个 `ask()` 函数不行吗？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """直接写函数能用，但会丢掉三样东西。

① 统一的消息协议：继承 `BaseChatModel` 后，任何人拿到你的对象都能按 `invoke(messages) -> AIMessage` 使用，
不用问「你这个 ask 收字符串还是列表、返回 dict 还是对象」。

② 基类白送的能力：`batch`、`stream`、回调、重试钩子都基于这套接口。自己写函数要一项项重造。

③ 可组合：后面的工具调用、预制 Agent、流式输出，都要求传进去的是「模型对象」而不是「某个函数」。
用一个自定义函数，等于把自己挡在这些能力之外。

结论：如果只是一次性脚本，直接 post 没问题；只要这东西要进图、要被别人用，就值得包成模型类。""",
                        "explanation": "接口一致性的价值，在第一次「别人要复用你的代码」时就体现出来。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-16-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`to_payload` 的唯一职责是什么？",
                        "options": [
                            ("A", "发 HTTP 请求"),
                            ("B", "把消息对象翻译成接口要的 role / content 结构"),
                            ("C", "解析响应里的 token 用量"),
                            ("D", "重试失败的请求"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它只做翻译，不发请求、不解析响应。职责单一才好测。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-16-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`resp.raise_for_status()` 在响应状态码为 4xx 或 5xx 时会抛出异常。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "这正是它的作用：让错误响应在解析之前就暴露，而不是等到 `KeyError: 'choices'` 才发现。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-16-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例为什么用 `httpx.MockTransport` 而不是直接请求真实接口？",
                        "options": [
                            ("A", "因为真实接口太慢"),
                            ("B", "因为要离线验证「翻译是否正确」，并让输出可复现"),
                            ("C", "因为 MockTransport 支持流式，真实接口不支持"),
                            ("D", "因为真实接口不能返回 JSON"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "要验证的是代码逻辑，不是对方服务器。假传输层还能把请求体打出来，真接口做不到。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-16-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "如果在 `CompatChatModel` 上删掉 `client` 字段，直接 `CompatChatModel(model=\"x\")` 会怎样？",
                        "options": [
                            ("A", "正常运行，内部会自动创建 client"),
                            ("B", "构造时就报字段缺失的校验错误"),
                            ("C", "运行到 `_generate` 时抛 `AttributeError`"),
                            ("D", "自动改用系统默认代理"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`client: Any = None` 只是给了默认值；若字段完全不存在，pydantic 会在构造时报校验错误。这也是「注入」的意义：依赖必须显式提供。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-16-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给 `to_payload` 增加对 `AIMessage` 的处理：翻译成 `assistant` 角色，`content` 为空时用空字符串。",
                        "options": [],
                        "answer": {
                            "value": "def to_payload(messages: list[BaseMessage]) -> list[dict]:\n    rows: list[dict] = []\n    for m in messages:\n        if isinstance(m, SystemMessage):\n            rows.append({\"role\": \"system\", \"content\": m.content})\n        elif isinstance(m, HumanMessage):\n            rows.append({\"role\": \"user\", \"content\": m.content})\n        elif isinstance(m, AIMessage):\n            rows.append({\"role\": \"assistant\", \"content\": m.content or \"\"})\n        else:\n            raise TypeError(f\"未支持的消息类型：{type(m).__name__}\")\n    return rows"
                        },
                        "explanation": "末尾的 `else: raise TypeError` 很重要：新增消息类型时宁可报错，也不要静默丢掉——静默丢消息会让模型「失忆」，且极难排查。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-16-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "既然 `_generate` 里就是一次 HTTP 请求，为什么还要继承 `BaseChatModel`，而不是写个普通函数？",
                        "options": [],
                        "answer": """三样东西是继承才有的。

① 统一协议：别人拿到对象就知道 `invoke(messages) -> AIMessage`，不用问参数是字符串还是列表。

② 基类能力：`batch`、`stream`、回调、重试钩子都基于这套接口，自己写函数要一项项重造。

③ 可组合：工具调用、预制 Agent、流式输出都要求传「模型对象」。用普通函数等于把自己挡在这些能力之外。

一句话：一次性脚本可以直接 post；要进图、要给别人用，就值得包成模型类。""",
                        "explanation": "判断标准不是「能不能跑」，而是「要不要被别人复用」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 17 章
    {
        "code": "langgraph-agent-17",
        "order_index": 17,
        "title": "Tool Calling",
        "description": "让模型输出「我要调哪个函数、传什么参数」，再由你的代码去执行。",
        "lessons": [
            {
                "code": "langgraph-agent-17-lesson-01",
                "title": "工具定义与 schema",
                "objectives": """1. 能用 `@tool` 把普通函数变成工具，并说出 `name / description / args` 从哪来；
2. 能用 `args_schema` 给参数写说明与默认值；
3. 能读懂 `convert_to_openai_tool` 生成的工具描述；
4. 能说明「描述写得含糊」会怎样直接导致模型选错工具。""",
                "why_learn": """模型不认识你的函数，它只看得见一份「说明书」。这份说明书由函数名、docstring 和类型注解自动生成。
写不好它，模型就会调错工具、传错参数——而你会以为是模型笨。""",
                "concepts": """**工具三要素**：`name`（函数名）、`description`（docstring）、`parameters`（由类型注解生成的 JSON Schema）。
**`@tool` 做了什么**：把函数包成 `StructuredTool`，同时生成 `args_schema`。
**默认值与必填**：有默认值的参数不进 `required`；没默认值的就是必填。
**`args_schema`**：需要更细的字段说明时，传一个 pydantic 模型进去。
**`convert_to_openai_tool`**：把工具对象转成接口认识的 `{"type": "function", "function": {...}}`。
**描述即契约**：模型只按描述挑工具，描述里没写「什么时候用」，它就只能猜。""",
                "plain": """工具描述是写给模型看的说明书，不是写给人看的注释。
人看代码能猜出用途，模型只能读那段 `description`——你写得含糊，它就挑错工具，而且错得理直气壮。

所以工具名要像动词短语（`search_course`、`read_lesson`），描述要说清「做什么」加「什么时候该用」，
参数说明要写清取值范围。这三件事做到位，工具调用的准确率会明显不一样。

另外一个容易被忽略的点：参数不写类型注解，生成的 schema 里那个字段就是空的 `{}`——
模型不知道它该填字符串还是数字，只能瞎猜。这不是模型的问题，是说明书缺页。""",
                "syntax": """**三种写法**

```python
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool

@tool
def search_course(keyword: str, limit: int = 3) -> str:
    \"\"\"按关键词检索课程资料，返回章节标题。\"\"\"       # 第一行就是 description
    ...

@tool("read_lesson")                                  # 自定义工具名
def read(chapter: str) -> str:
    \"\"\"读取章节正文。\"\"\"
    ...

@tool("read_lesson", args_schema=ReadInput)           # 自定义参数说明
def read_lesson(chapter: str, full: bool = False) -> str:
    \"\"\"读取章节正文。\"\"\"
    ...

print(convert_to_openai_tool(search_course))
```

- 没有 docstring 会直接 `ValueError`：工具必须有描述。
- 参数缺类型注解不会报错，但 schema 是空的——比报错更危险。
- `args_schema` 与函数签名要一致，不一致时以 `args_schema` 为准，调用时容易对不上。""",
                "example_code": '''import json

from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, Field


@tool
def search_course(keyword: str, limit: int = 3) -> str:
    """按关键词检索课程资料，返回章节标题。"""
    return f"匹配「{keyword}」的前 {limit} 条：第 6 章 State：状态结构"


print("=== 1. 函数被包装成了什么 ===")
print("name        :", search_course.name)
print("description :", search_course.description)
print("args        :", search_course.args)
print("必填字段    :", search_course.args_schema.model_json_schema()["required"])

print()
print("=== 2. 送给模型的工具描述 ===")
print(json.dumps(convert_to_openai_tool(search_course)["function"], ensure_ascii=False, indent=2))

print()
print("=== 3. 自己写参数说明 ===")


class ReadInput(BaseModel):
    """读取某章正文的入参。"""

    chapter: str = Field(description="章节编号，例如 6")
    full: bool = Field(default=False, description="是否返回全文")


@tool("read_lesson", args_schema=ReadInput)
def read_lesson(chapter: str, full: bool = False) -> str:
    """读取章节正文。"""
    return f"第 {chapter} 章" + ("全文" if full else "摘要")


print(json.dumps(convert_to_openai_tool(read_lesson)["function"], ensure_ascii=False, indent=2))

print()
print("=== 4. 两个常见错误 ===")
try:

    @tool
    def no_doc(question: str) -> str:
        return "x"

except ValueError as exc:
    print("没有 docstring ->", exc)


@tool
def no_type(question: str, n) -> str:
    """第二个参数没写类型。"""
    return "x"


schema = convert_to_openai_tool(no_type)["function"]["parameters"]
print("参数没类型 ->", json.dumps(schema, ensure_ascii=False))

print()
print("=== 5. 调用工具 ===")
print("传 dict    :", search_course.invoke({"keyword": "state"}))
print("传字符串   :", search_course.invoke("state"))
print("传两个参数 :", search_course.invoke({"keyword": "state", "limit": 1}))''',
                "code_lines": """1. `@tool` 把函数包成 `StructuredTool`，原函数变成 `.func`，调用要走 `.invoke()`。
2. `.description` 直接取自 docstring 第一段；写多行会整段带进描述，模型会读到多余的话。
3. `.args` 是参数 schema 的简表：类型、默认值一目了然；`limit` 有默认值，所以不在 `required` 里。
4. `convert_to_openai_tool(...)["function"]` 才是真正发给接口的部分：`name / description / parameters`。
5. 第 3 段用 `args_schema` 给每个字段补 `description`，文件里因此多了「章节编号，例如 6」这种说明。
6. 第 4 段第一个错误：没有 docstring 直接在装饰时就 `ValueError`，不给运行机会。
7. 第二个错误更隐蔽：`n` 没有类型注解，schema 里只有 `{}`，但它仍是必填项——模型只能猜该填什么。
8. 第 5 段证明工具可以像函数一样调用，传 dict 或按位置传单个参数都行。""",
                "output": """# 程序输出
=== 1. 函数被包装成了什么 ===
name        : search_course
description : 按关键词检索课程资料，返回章节标题。
args        : {'keyword': {'title': 'Keyword', 'type': 'string'}, 'limit': {'default': 3, 'title': 'Limit', 'type': 'integer'}}
必填字段    : ['keyword']

=== 2. 送给模型的工具描述 ===
{
  "name": "search_course",
  "description": "按关键词检索课程资料，返回章节标题。",
  "parameters": {
    "properties": {
      "keyword": {
        "type": "string"
      },
      "limit": {
        "default": 3,
        "type": "integer"
      }
    },
    "required": [
      "keyword"
    ],
    "type": "object"
  }
}

=== 3. 自己写参数说明 ===
{
  "name": "read_lesson",
  "description": "读取章节正文。",
  "parameters": {
    "properties": {
      "chapter": {
        "description": "章节编号，例如 6",
        "type": "string"
      },
      "full": {
        "default": false,
        "description": "是否返回全文",
        "type": "boolean"
      }
    },
    "required": [
      "chapter"
    ],
    "type": "object"
  }
}

=== 4. 两个常见错误 ===
没有 docstring -> Function must have a docstring if description not provided.
参数没类型 -> {"properties": {"question": {"type": "string"}, "n": {}}, "required": ["question", "n"], "type": "object"}

=== 5. 调用工具 ===
传 dict    : 匹配「state」的前 3 条：第 6 章 State：状态结构
传字符串   : 匹配「state」的前 3 条：第 6 章 State：状态结构
传两个参数 : 匹配「state」的前 1 条：第 6 章 State：状态结构""",
                "mistakes": """- 工具名用 `do_it`、`helper` 这种动词——模型分不清它和别的工具的区别。
- docstring 写成「TODO」或直接照抄函数名，模型只能靠猜。
- 参数不写类型注解，schema 里是空的 `{}`，模型传进来一个字符串当数字用。
- `args_schema` 里定义的字段和函数签名不一致，校验通过但调用时 `TypeError`。
- 一个工具干三件事（查资料 + 总结 + 存库），模型永远不知道该在什么时候调它。
- 把内部实现的细节写进描述（比如「走 Redis 缓存」），对模型选工具毫无帮助，只是噪音。""",
                "error_analysis": """`ValueError: Function must have a docstring if description not provided.`
—— 工具没有 docstring。补一句描述，或在 `@tool(description=...)` 里显式给。

`pydantic.ValidationError: 1 validation error for search_course`
—— 调用时缺必填参数，或参数类型不对。先打印工具 schema 核对。

模型总是传错参数类型
—— 参数缺类型注解，schema 里是 `{}`。补上 `str` / `int` / `bool`。

模型选了错误的工具
—— 两个工具的描述有重叠。把「什么时候用 A、什么时候用 B」写进各自的描述里。""",
                "beginner_practice": """1. 给 `search_course` 加一个 `chapter: str = ""` 参数（限定在某章内检索），观察 `required` 的变化。
2. 把 `no_type` 的 `n` 改成 `n: int`，对比两次打印出的 schema。""",
                "advanced_practice": """设计一组「课程查询」工具（检索、读正文、查练习），要求三者的描述互不重叠。
写出三份描述，并说明你会用什么办法验证「模型不会选错」。""",
                "quiz_note": "本节 6 道题：2 道基础理解（模型靠什么选工具、无 docstring 的后果）+ 2 道代码阅读（`limit` 为什么不是必填、空 schema 的隐患）+ 2 道应用练习（加参数并写说明、描述该怎么写）。",
                "summary": """`@tool` 把函数变成「模型看得见的说明书」：名字、描述、参数 schema。
描述决定模型选不选它，参数说明决定模型填得对不对。
没有 docstring 会报错，没有类型注解不会报错但更危险。""",
                "next_lesson": "工具定义好了，下一节看模型怎么「点菜」：`tool_calls` 的结构与结果回填。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-17-01",
                        "name": "工具定义与工具描述",
                        "goal": "能定义描述清晰、参数完整的工具，并读懂生成的 schema。",
                        "minutes": 40,
                        "criteria": "能解释 `description` 与 `parameters` 如何影响模型的工具选择。",
                        "requires": ["langgraph-agent-16-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-17-01-1",
                        "kp": 0,
                        "title": "给检索工具加范围参数",
                        "description": "给 `search_course` 增加 `chapter: str = \"\"` 参数，表示「只在这一章内检索」，并让 `convert_to_openai_tool` 里出现它的说明。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    keyword: str = Field(description="检索词，例如 state")
    chapter: str = Field(default="", description="限定章节编号；留空表示全书检索")
    limit: int = Field(default=3, description="最多返回几条")


@tool("search_course", args_schema=SearchInput)
def search_course(keyword: str, chapter: str = "", limit: int = 3) -> str:
    """按关键词检索课程资料，返回章节标题。"""
    scope = f"第 {chapter} 章" if chapter else "全书"
    return f"在{scope}内检索「{keyword}」，取前 {limit} 条"''',
                        "explanation": "用 `args_schema` 才能给每个字段写说明。只靠类型注解，模型知道是字符串，但不知道「留空表示全书」这种约定。",
                    },
                    {
                        "code": "lg-ex-17-01-2",
                        "kp": 0,
                        "title": "描述该怎么写",
                        "description": "「检索课程」和「查课程资料」两个描述，模型选错的概率一样吗？写出你认为合格的版本。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """一个合格的描述要回答三个问题：做什么、什么时候用、不要用它做什么。

示例：

「按关键词检索课程章节标题，返回命中的章节名。适用于用户问『某概念在哪一章』『有没有讲过 X』。
若用户要正文内容，请改用 read_lesson；若用户问课程安排或价格，本工具不适用。」

「检索课程」这种写法只回答了第一个问题：模型知道它能搜，但不知道和 read_lesson 的边界在哪，
遇到「讲讲第 6 章」时两个工具都像，于是随机挑一个。

可验证的办法：准备 20 条真实问句，看模型选对的比例；描述改动后再跑一遍对比。
描述不是文案工作，它是有指标的功能。""",
                        "explanation": "把「不适用」也写进描述，是最容易被忽略、也最能降低误选率的一句。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-17-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "模型决定「调不调工具、调哪个」时，主要依据是什么？",
                        "options": [
                            ("A", "函数的 Python 实现"),
                            ("B", "工具名、描述与参数 schema"),
                            ("C", "函数的返回类型"),
                            ("D", "模块的文件名"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "模型看不到实现，只能读到发过去的那份说明书。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-17-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "用 `@tool` 装饰一个没有 docstring 的函数，会在装饰时就抛出 `ValueError`。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "报错信息是 `Function must have a docstring if description not provided.`，连运行机会都不给。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-17-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "生成的 schema 里，为什么 `limit` 不在 `required` 中？",
                        "options": [
                            ("A", "因为它的类型是 int"),
                            ("B", "因为它有默认值 3"),
                            ("C", "因为它在参数列表最后"),
                            ("D", "因为它的名字太短"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "有默认值的参数视为可选；没有默认值的一律必填。想让某参数可选，就给它一个默认值。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-17-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`no_type` 的 schema 里 `\"n\": {}`，这会造成什么后果？",
                        "options": [
                            ("A", "装饰时就报错"),
                            ("B", "模型不知道这个参数该填什么类型，只能猜"),
                            ("C", "该参数会被自动忽略"),
                            ("D", "该参数变成可选"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "空 schema 表示「没有任何约束与说明」，但字段仍是必填的。模型只能靠参数名猜，猜错就得到校验错误。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-17-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给 `read_lesson` 增加 `max_chars: int = 2000` 参数，并用 `args_schema` 写清它的含义。",
                        "options": [],
                        "answer": {
                            "value": "class ReadInput(BaseModel):\n    chapter: str = Field(description=\"章节编号，例如 6\")\n    full: bool = Field(default=False, description=\"是否返回全文\")\n    max_chars: int = Field(default=2000, description=\"返回正文的最大字符数，超过则截断\")\n\n\n@tool(\"read_lesson\", args_schema=ReadInput)\ndef read_lesson(chapter: str, full: bool = False, max_chars: int = 2000) -> str:\n    \"\"\"读取章节正文。\"\"\"\n    text = f\"第 {chapter} 章正文\"\n    return text if full else text[:max_chars]"
                        },
                        "explanation": "加了默认值就自动变成可选；`description` 里写清单位（字符数）与行为（超过则截断），模型才会传合理值。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-17-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说「描述里要写清什么时候不要用这个工具」？",
                        "options": [],
                        "answer": """因为模型是在多个工具之间做选择，不是在判断「单个工具能不能用」。

只写「做什么」时，几个功能相近的工具在模型眼里没有边界，只能随机挑。
写上「不适用」的情形，等于给了它排除条件。

例如：「检索章节标题。要正文请用 read_lesson；课程价格与排课问题本工具不适用。」
这句话让模型在「讲讲第 6 章」这类请求上不再犹豫。

代价是描述变长，会占一点上下文。相比选错工具后多跑一轮的消耗，这个代价很划算。""",
                        "explanation": "多工具共存的场景里，描述的重点是「划边界」，而不只是「介绍自己」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-17-lesson-02",
                "title": "tool_calls 与结果回填",
                "objectives": """1. 能说出 `tool_calls` 里 `name / args / id` 三个字段各自的作用；
2. 能用 `tool_call_id` 把结果配回对应的调用；
3. 能给模型实现 `bind_tools`，让请求真正带上工具描述；
4. 能说明 `arguments` 在传输时是 JSON 字符串、`args` 是解析后的字典。""",
                "why_learn": """工具调用不是模型去执行函数，而是模型给你一张「点菜单」。菜单要你去做菜，还要按订单号把菜端回去。
搞不清订单号，两轮工具调用就会串味。""",
                "concepts": """**`tool_calls`**：`AIMessage` 上的列表，每项含 `name`（调哪个）、`args`（传什么）、`id`（订单号）。
**两种形态**：传输时 `arguments` 是 JSON 字符串；解析后 `args` 是字典。手写消息时用字典。
**`ToolMessage`**：工具结果的消息类型，必须带 `tool_call_id`，否则构造时报 `KeyError`。
**并行调用**：一次可以返回多个 `tool_calls`，每个都要各自回填一条 `ToolMessage`。
**`bind_tools`**：基类没有默认实现，子类必须自己把工具转成 schema 塞进请求。
**闭环**：模型出菜单 → 你执行 → 回填 → 再问模型，它才知道结果。""",
                "plain": """工具调用分两半：模型负责「决定调什么」，你的代码负责「真的去调」。
模型返回的 `tool_calls` 就是一张点菜单，上面写着菜名、口味和订单号。

订单号（`id`）是最容易被忽略的一项。它存在的唯一理由是：一次可以点好几道菜，
端回去的时候必须让模型知道「这盘菜对应哪张单」，否则它会把 A 的结果当成 B 的。

另外要注意 `args` 的类型：接口传过来的是 JSON 字符串，SDK 帮你解析成了字典。
你自己手工造消息时用字典就行，但要把消息发回接口，又得把字典转回字符串——
这一来一回，是最常见的报错来源。

最后一步别忘了：回填之后要再问一次模型。它不会自动看到工具结果，你得把结果作为新消息交给它。""",
                "syntax": """**回填的固定套路**

```python
# 1. 模型给出 tool_calls
ai = AIMessage(content="", tool_calls=[
    {"name": "search_course", "args": {"keyword": "state"}, "id": "call_1"},
])

# 2. 按名字找工具，按 args 执行，按 id 回填
registry = {"search_course": search_course}
for call in ai.tool_calls:
    result = registry[call["name"]].invoke(call["args"])
    msg = ToolMessage(content=str(result), tool_call_id=call["id"], name=call["name"])
```

**让模型真的返回 tool_calls**

```python
def bind_tools(self, tools, **kwargs):
    schemas = [convert_to_openai_tool(t)["function"] for t in tools]
    return self.bind(tools=schemas, **kwargs)     # bind 会把 tools 透传给 _generate
```

- `ToolMessage` 的 `tool_call_id` 必填，缺了直接 `KeyError`。
- `bind_tools` 返回的不是模型本身，而是一个「带参数的绑定对象」。
- 基类的 `bind_tools` 会抛 `NotImplementedError`，且消息是空字符串——很难从报错里看出原因。""",
                "example_code": '''import json
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool


@tool
def search_course(keyword: str) -> str:
    """按关键词检索课程资料。"""
    return "第 6 章 State：状态结构"


@tool
def read_lesson(chapter: str) -> str:
    """读取章节正文摘要。"""
    return f"{chapter} 的摘要"


# ---------- 第一部分：模型返回的 tool_calls 长什么样 -------------------------
ai = AIMessage(
    content="",
    tool_calls=[
        {"name": "search_course", "args": {"keyword": "state"}, "id": "call_1"},
        {"name": "read_lesson", "args": {"chapter": "第 6 章"}, "id": "call_2"},
    ],
)

print("=== 1. 模型返回的消息 ===")
print("  content        :", repr(ai.content))
print("  tool_calls 条数:", len(ai.tool_calls))
print("  第一条         :", ai.tool_calls[0]["name"], ai.tool_calls[0]["args"])
print("  args 类型      :", type(ai.tool_calls[0]["args"]).__name__)

print()
print("=== 2. 发回接口时要变回字符串 ===")
for call in ai.tool_calls:
    print(f"  {call['name']:<14s} arguments={json.dumps(call['args'], ensure_ascii=False)}")

print()
print("=== 3. 自己执行并回填 ===")
registry = {"search_course": search_course, "read_lesson": read_lesson}
filled = []
for call in ai.tool_calls:
    result = registry[call["name"]].invoke(call["args"])
    msg = ToolMessage(content=str(result), tool_call_id=call["id"], name=call["name"])
    filled.append(msg)
    print(f"  ToolMessage(id={msg.tool_call_id}) -> {msg.content}")

print()
print("=== 4. 漏掉 tool_call_id ===")
try:
    ToolMessage(content="结果")
except KeyError as exc:
    print("  KeyError:", exc)


# ---------- 第二部分：让模型能把工具调用返回给我们 ---------------------------
def to_payload(messages: list[BaseMessage]) -> list[dict]:
    rows: list[dict] = []
    for m in messages:
        if isinstance(m, SystemMessage):
            rows.append({"role": "system", "content": m.content})
        elif isinstance(m, HumanMessage):
            rows.append({"role": "user", "content": m.content})
        elif isinstance(m, ToolMessage):
            rows.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
        elif isinstance(m, AIMessage):
            row: dict = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                row["tool_calls"] = [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {
                            "name": c["name"],
                            "arguments": json.dumps(c["args"], ensure_ascii=False),
                        },
                    }
                    for c in m.tool_calls
                ]
            rows.append(row)
    return rows


class CompatChatModel(BaseChatModel):
    model: str
    client: Any = None

    @property
    def _llm_type(self) -> str:
        return "openai-compatible"

    def bind_tools(self, tools, **kwargs):
        schemas = [convert_to_openai_tool(t)["function"] for t in tools]
        return self.bind(tools=schemas, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        payload: dict = {"model": self.model, "messages": to_payload(messages)}
        if schemas := kwargs.get("tools"):
            payload["tools"] = [{"type": "function", "function": s} for s in schemas]
        resp = self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        message = resp.json()["choices"][0]["message"]
        calls = [
            {
                "name": c["function"]["name"],
                "args": json.loads(c["function"]["arguments"]),
                "id": c["id"],
            }
            for c in message.get("tool_calls") or []
        ]
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=message.get("content") or "", tool_calls=calls))]
        )


def server(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    print("  -> 请求 roles:", [m["role"] for m in body["messages"]])
    print("  -> 带上的工具:", [t["function"]["name"] for t in body.get("tools", [])])
    return httpx.Response(200, json={"choices": [{"message": {
        "role": "assistant",
        "content": "",
        "tool_calls": [{
            "id": "call_1",
            "type": "function",
            "function": {"name": "search_course", "arguments": json.dumps({"keyword": "state"})},
        }],
    }}]})


client = httpx.Client(base_url="https://api.example.com/v1", transport=httpx.MockTransport(server))
llm = CompatChatModel(model="chat-small", client=client)

print()
print("=== 5. 绑定工具后调用 ===")
bound = llm.bind_tools([search_course, read_lesson])
print("  返回类型:", type(bound).__name__)
reply = bound.invoke([HumanMessage("State 在哪一章")])
print("  tool_calls:", reply.tool_calls)

print()
print("=== 6. 不实现 bind_tools 的模型 ===")


class BareModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "bare"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="ok"))])


try:
    BareModel().bind_tools([search_course])
except NotImplementedError as exc:
    print("  NotImplementedError:", repr(str(exc)))''',
                "code_lines": """1. 手写的 `AIMessage` 里 `content` 是空字符串：模型决定调工具时，通常不附带文字。
2. `tool_calls` 每项三个键：`name` 决定调谁，`args` 决定传什么，`id` 是回填时要用的订单号。
3. `args` 打印出来是 `dict`——SDK 已经把 JSON 字符串解析好了，你直接用。
4. 第 2 段反向演示：要把历史消息发回接口，`args` 必须重新 `json.dumps` 成字符串。
5. 第 3 段用注册表按名字找工具：`registry[call["name"]]`，找不到就 `KeyError`，这比静默跳过好。
6. `ToolMessage(content=..., tool_call_id=call["id"])` 是回填的标准写法，`name` 可选但建议带上，日志里好认。
7. 第 4 段说明 `tool_call_id` 是必填的：漏了直接 `KeyError`，连对象都构造不出来。
8. 第 5 段：`bind_tools` 自己实现后，请求体里就带上了 `tools`，假服务按剧本返回一个 `tool_calls`。
9. 第 6 段：基类的 `bind_tools` 抛 `NotImplementedError` 且消息为空——这正是「自己实现」的理由。""",
                "output": """# 程序输出
=== 1. 模型返回的消息 ===
  content        : ''
  tool_calls 条数: 2
  第一条         : search_course {'keyword': 'state'}
  args 类型      : dict

=== 2. 发回接口时要变回字符串 ===
  search_course  arguments={"keyword": "state"}
  read_lesson    arguments={"chapter": "第 6 章"}

=== 3. 自己执行并回填 ===
  ToolMessage(id=call_1) -> 第 6 章 State：状态结构
  ToolMessage(id=call_2) -> 第 6 章 的摘要

=== 4. 漏掉 tool_call_id ===
  KeyError: 'tool_call_id'

=== 5. 绑定工具后调用 ===
  返回类型: _ChatModelBinding
  -> 请求 roles: ['user']
  -> 带上的工具: ['search_course', 'read_lesson']
  tool_calls: [{'name': 'search_course', 'args': {'keyword': 'state'}, 'id': 'call_1', 'type': 'tool_call'}]

=== 6. 不实现 bind_tools 的模型 ===
  NotImplementedError: ''""",
                "mistakes": """- 回填时用工具名配对而不是 `id`：两个同名调用一多，结果就串了。
- 把 `tool_calls` 里的 `arguments` 当字典用——自己手写时是字典，从网络来的原始结构是字符串。
- 回填后忘了再调一次模型，直接把工具结果当成最终答案返回给用户。
- 一次返回两个 `tool_calls` 却只回填一条，下一轮请求被接口拒掉（缺少对应的 tool 消息）。
- `bind_tools` 里直接返回 `self`，请求体里从不带 `tools`，模型永远不知道有工具可用。
- 把 `ToolMessage` 的 `content` 传成 dict，部分接口要求是字符串，序列化时才报错。""",
                "error_analysis": """`KeyError: 'tool_call_id'`
—— 构造 `ToolMessage` 时漏了订单号。它必须等于对应 `tool_call` 的 `id`。

`NotImplementedError`（消息为空）
—— 调了基类的 `bind_tools`。自定义模型必须自己实现。

`IndexError` / `KeyError: 'choices'`
—— 假服务返回的剧本与代码预期不一致，先打印 `resp.json()` 核对。

模型始终不调用工具
—— 请求体里没有 `tools` 字段。检查 `bind_tools` 是否真的把 schema 透传到了 `_generate`。

工具结果被忽略，模型重复调同一个工具
—— 回填的 `ToolMessage` 没进下一轮的 `messages`，模型看不到结果。""",
                "beginner_practice": """1. 在假服务里返回两个 `tool_calls`，把第 3 段的回填循环跑一遍，确认生成两条 `ToolMessage`。
2. 把 `ToolMessage` 的 `name` 去掉，观察打印结果与报错有无变化。""",
                "advanced_practice": """如果模型调用了注册表里不存在的工具名，现在的代码会 `KeyError`。
设计一个更稳的处理：把「工具不存在」也变成一条 `ToolMessage` 回填给模型，让它自己改主意。
写出这段代码，并说明为什么这比直接抛异常更适合线上。""",
                "quiz_note": "本节 6 道题：2 道基础理解（靠哪个字段配对、`args` 的类型）+ 2 道代码阅读（`content` 为什么为空、不实现 `bind_tools` 的后果）+ 2 道应用练习（写回填循环、并行调用能否只回填一条）。",
                "summary": """模型出菜单（`tool_calls`），你上菜（执行），按订单号（`id`）回填 `ToolMessage`，再问一次模型。
`bind_tools` 是自定义模型的必修课，基类只抛 `NotImplementedError`。
`args` 是字典，`arguments` 是字符串，两个方向都要会转。""",
                "next_lesson": "手写回填循环太啰嗦。下一章用 `ToolNode` 把它交给框架，并处理工具出错的情况。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-17-02",
                        "name": "工具调用与结果回填",
                        "goal": "能实现工具调用的完整闭环，并让自定义模型支持绑定工具。",
                        "minutes": 45,
                        "criteria": "能按 `id` 正确回填，并解释 `bind_tools` 为什么必须自己写。",
                        "requires": ["langgraph-agent-17-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-17-02-1",
                        "kp": 0,
                        "title": "写一个回填循环",
                        "description": "给定一条含两个 `tool_calls` 的 `AIMessage` 与一个注册表，写出完整的执行 + 回填代码，返回消息列表。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def run_tool_calls(ai: AIMessage, registry: dict) -> list[ToolMessage]:
    """执行 ai 上的全部工具调用，返回对应的 ToolMessage 列表。"""
    results: list[ToolMessage] = []
    for call in ai.tool_calls:
        tool_fn = registry.get(call["name"])
        if tool_fn is None:
            content = f"工具 {call['name']} 不存在，可用工具：{list(registry)}"
        else:
            try:
                content = str(tool_fn.invoke(call["args"]))
            except Exception as exc:
                content = f"工具执行失败：{exc}"
        results.append(
            ToolMessage(content=content, tool_call_id=call["id"], name=call["name"])
        )
    return results''',
                        "explanation": "把「工具不存在」与「执行失败」都转成字符串回填，模型就有机会自我修正；直接抛异常会让整张图停在这里。",
                    },
                    {
                        "code": "lg-ex-17-02-2",
                        "kp": 0,
                        "title": "并行调用能不能只回填一条",
                        "description": "模型一次返回两个 `tool_calls`，只回填其中一个会怎样？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """不行。一条 `tool_calls` 对应一条 `ToolMessage`，缺一条就破坏了消息序列的完整性。

具体后果分两层：

① 协议层：主流接口会校验「每个 tool_call 是否都有对应的 tool 消息」，缺失时直接返回 400。
报错信息通常长得像 `An assistant message with 'tool_calls' must be followed by tool messages
responding to each tool_call_id`。

② 逻辑层：即使接口放宽，模型也看不到那个工具的结果，可能重复调用同一个工具，或者基于不完整的信息作答。

正确做法是全部执行、全部回填；某个工具失败也要回填一条内容为错误说明的 `ToolMessage`，
让模型知道「这条路走不通」，而不是让它以为还有结果在路上。""",
                        "explanation": "「失败也要回填」是工具调用里最反直觉、也最实用的一条纪律。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-17-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "把工具结果回填给模型时，靠哪个字段把结果和调用配对？",
                        "options": [
                            ("A", "工具名 `name`"),
                            ("B", "订单号 `tool_call_id`"),
                            ("C", "消息的时间戳"),
                            ("D", "结果内容的哈希"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "同名工具可以在一轮里被调用多次，只有 `id` 能唯一区分。`name` 只是方便人看日志。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-17-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`ai.tool_calls[0][\"args\"]` 是一个 JSON 字符串。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它是解析后的字典。JSON 字符串只存在于传输层（原始响应里的 `arguments`）。示例第 1 段打印的 `args 类型 : dict` 就是证据。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-17-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例里模型决定调用工具时，`content` 为什么是空字符串？",
                        "options": [
                            ("A", "因为假服务写错了"),
                            ("B", "因为模型把「要说的话」换成了「要调的工具」，通常不附带正文"),
                            ("C", "因为 `content` 一定为空"),
                            ("D", "因为 `tool_calls` 会覆盖 `content`"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "模型可以同时给文字和工具调用，但实践中调工具的那一轮通常只给工具调用。展示时要把 `content` 为空当成正常情况处理。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-17-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`BareModel().bind_tools([...])` 抛出的 `NotImplementedError` 有什么特别之处？",
                        "options": [
                            ("A", "它带有完整的修复建议"),
                            ("B", "它的消息是空字符串，几乎给不出线索"),
                            ("C", "它会自动回退到不绑定工具的模式"),
                            ("D", "它只在异步调用时抛出"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "报错信息为空，栈里只看到 `bind_tools` 一行。这正是本节要自己实现它的原因——否则线上只能靠猜。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-17-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补完这段回填代码：给定 `ai` 与 `registry`，执行全部工具调用并返回 `ToolMessage` 列表。",
                        "options": [],
                        "answer": {
                            "value": "msgs = []\nfor call in ai.tool_calls:\n    result = registry[call[\"name\"]].invoke(call[\"args\"])\n    msgs.append(\n        ToolMessage(\n            content=str(result),\n            tool_call_id=call[\"id\"],\n            name=call[\"name\"],\n        )\n    )"
                        },
                        "explanation": "三件事不能少：按 `name` 找工具、按 `args` 执行、按 `id` 回填。`content` 建议 `str()` 一下，避免部分接口要求字符串。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-17-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "模型一次返回两个 `tool_calls`，只回填其中一个会有什么问题？",
                        "options": [],
                        "answer": """两个层面都会出问题。

协议层：主流接口会校验「每个 tool_call 是否有对应的 tool 消息」，缺一条直接返回 400，
报错大意是「带 tool_calls 的 assistant 消息后面必须跟齐对应的 tool 消息」。

逻辑层：即使接口不校验，模型也拿不到那条结果，可能重复调用同一工具，或基于残缺信息作答。

正确做法是全部执行、全部回填。某个工具失败时也要回填一条写明错误的 `ToolMessage`，
让模型知道这条路走不通——沉默比报错更糟。""",
                        "explanation": "「失败也要回填」是工具调用里最容易被忽略的纪律。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
