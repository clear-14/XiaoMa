"""LangGraph Agent 开发：第 18—19 章。

第 18 章把「找工具、执行、包消息、处理异常」这四件事交给预置的 `ToolNode`；
第 19 章把「思考—行动—观察」拼成完整的 ReAct 循环，并说清三种工作流形态与预制 Agent 的版本定位。

版本口径（实测）：langgraph 1.2.20、langchain-core 1.7.6。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 18 章
    {
        "code": "langgraph-agent-18",
        "order_index": 18,
        "title": "工具节点",
        "description": "把「执行工具」做成一个可复用的节点，并决定出错时怎么办。",
        "lessons": [
            {
                "code": "langgraph-agent-18-lesson-01",
                "title": "ToolNode 与错误处理",
                "objectives": """1. 能用 `ToolNode` 替代手写的回填循环；
2. 能说出 `ToolNode` 的输入输出：读最后一条 `tool_calls`，返回 `ToolMessage` 列表；
3. 能区分「调用错误」与「业务异常」在默认配置下的不同命运；
4. 能用 `handle_tool_errors` 的四种取值兜住业务异常；
5. 能用 `tools_condition` 做「继续调工具 / 结束」的分支。""",
                "why_learn": """手写回填循环时，你要自己找工具、执行、包消息、处理异常。这四件事每个项目都一样。
`ToolNode` 把它们打包成一个节点，你只需要决定：工具报错时，是炸掉还是让模型自己想办法。""",
                "concepts": """**`ToolNode`**：预置节点。读 `state["messages"]` 最后一条 `AIMessage` 的 `tool_calls`，逐个执行，返回 `{"messages": [ToolMessage, ...]}`。
**并行**：一条消息里多个 `tool_calls` 会被一起执行，按原顺序回填。
**`status`**：成功的 `ToolMessage.status` 是 `"success"`，被兜住的错误是 `"error"`。
**默认只兜调用错误**：工具不存在、参数缺失这类「调用错误」会变成 `ToolMessage`；工具内部抛的业务异常会直接向上抛。
**`handle_tool_errors`**：`True`（默认）/ 字符串（固定话术）/ 异常元组（只兜指定类型）/ 可调用（自己生成话术）。
**`tools_condition`**：现成路由函数，有 `tool_calls` 返回 `"tools"`，否则返回 `"__end__"`。""",
                "plain": """手写回填循环时，工具报错你要自己想：「这次失败该不该让模型知道？」
`ToolNode` 替你做了默认决定：只有「你调错了」才告诉模型，「工具自己坏了」直接抛出。

这个默认值很容易被误解。很多人以为把工具包进 `ToolNode` 就万事大吉，
结果线上一个除零错误把整张图炸停——因为业务异常默认不兜。

要兜住它，就得显式表态：传一个固定话术、传一组异常类型，或者传一个函数自己拼错误信息。
三种写法各有适用场景，本节把它们的实际输出都跑一遍，你会看到 `status` 与 `content` 的差别。

最后别忘了配一条从工具回到模型的回边——否则工具白跑，结果没人消费。""",
                "syntax": """**装配方式**

```python
from langgraph.prebuilt import ToolNode, tools_condition

builder.add_node("tools", ToolNode(tools))
builder.add_conditional_edges("agent", tools_condition)   # "tools" 或 "__end__"
builder.add_edge("tools", "agent")                       # 观察完回到思考
```

**`handle_tool_errors` 的四种取值**

```python
ToolNode(tools)                                        # 默认：只兜调用错误
ToolNode(tools, handle_tool_errors="工具暂时不可用")     # 固定话术
ToolNode(tools, handle_tool_errors=(ZeroDivisionError,))  # 只兜指定类型
ToolNode(tools, handle_tool_errors=lambda e: f"失败：{type(e).__name__}")
```

- `ToolNode` 是节点，不能脱离图直接 `invoke`：它会要运行时上下文，报 `Missing required config key`。
- 兜住的错误 `status` 是 `"error"`，模型能看到内容，但能看出这是错误。
- 返回顺序与 `tool_calls` 顺序一致，按 `id` 对齐。""",
                "example_code": '''from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


@tool
def search_course(keyword: str) -> str:
    """按关键词检索课程资料。"""
    table = {"state": "第 6 章 State", "tool": "第 18 章 工具节点"}
    for k, v in table.items():
        if k in keyword.lower():
            return v
    return "没有匹配"


@tool
def read_lesson(chapter: str) -> str:
    """读取章节正文摘要。"""
    return f"{chapter} 的摘要"


@tool
def divide(a: int, b: int) -> float:
    """做除法。"""
    return a / b


def run(tool_node: ToolNode, calls: list[AIMessage]):
    """把工具节点接进一张最小图里跑一遍，返回工具消息。"""
    model = FakeMessagesListChatModel(responses=[*calls, AIMessage(content="结束")])

    def agent(state: MessagesState) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    out = builder.compile().invoke({"messages": [HumanMessage("问题")]})
    return [m for m in out["messages"] if type(m).__name__ == "ToolMessage"]


node = ToolNode([search_course, read_lesson, divide])

print("=== 1. 一次工具调用 ===")
msgs = run(node, [AIMessage(content="", tool_calls=[
    {"name": "search_course", "args": {"keyword": "state"}, "id": "c1"},
])])
for m in msgs:
    print(f"  {m.name:<14s} id={m.tool_call_id} status={m.status} content={m.content!r}")

print()
print("=== 2. 并行两次调用 ===")
msgs = run(node, [AIMessage(content="", tool_calls=[
    {"name": "search_course", "args": {"keyword": "tool"}, "id": "c1"},
    {"name": "read_lesson", "args": {"chapter": "第 18 章"}, "id": "c2"},
])])
print("  返回条数:", len(msgs))
for m in msgs:
    print(f"    id={m.tool_call_id} {m.content}")

print()
print("=== 3. 工具抛异常（默认配置）===")
try:
    run(node, [AIMessage(content="", tool_calls=[
        {"name": "divide", "args": {"a": 1, "b": 0}, "id": "c3"},
    ])])
except ZeroDivisionError as exc:
    print("  直接抛出:", type(exc).__name__, exc)

print()
print("=== 4. 换成字符串兜底 ===")
soft = ToolNode([divide], handle_tool_errors="计算工具暂时不可用，请换个问题")
msgs = run(soft, [AIMessage(content="", tool_calls=[
    {"name": "divide", "args": {"a": 1, "b": 0}, "id": "c4"},
])])
print("  status:", msgs[0].status, "| content:", msgs[0].content)

print()
print("=== 5. 只兜指定异常 ===")
msgs = run(ToolNode([divide], handle_tool_errors=(ZeroDivisionError,)), [AIMessage(content="", tool_calls=[
    {"name": "divide", "args": {"a": 1, "b": 0}, "id": "c5"},
])])
print("  content:", msgs[0].content)

print()
print("=== 6. 工具名不存在 ===")
msgs = run(node, [AIMessage(content="", tool_calls=[{"name": "nope", "args": {}, "id": "c6"}])])
print("  content:", msgs[0].content)

print()
print("=== 7. 参数缺失 ===")
msgs = run(node, [AIMessage(content="", tool_calls=[{"name": "divide", "args": {"a": 1}, "id": "c7"}])])
print("  content:", msgs[0].content.replace("\\n", " "))''',
                "code_lines": """1. `run` 把「工具节点 + 假模型」接成最小图：模型出一条带 `tool_calls` 的消息，随后交给工具节点。
2. `FakeMessagesListChatModel` 按列表顺序返回消息，最后一条固定是「结束」，让循环能停下。
3. 第 1 段：`ToolMessage` 上有 `name`（哪个工具）、`tool_call_id`（订单号）、`status`（成功与否）。
4. 第 2 段：一条消息里两个 `tool_calls`，返回两条 `ToolMessage`，顺序与调用顺序一致。
5. 第 3 段是最容易被忽略的一条：除零异常**直接抛到顶层**，默认策略并不兜业务异常。
6. 第 4 段：`handle_tool_errors` 传字符串，`status` 变成 `"error"`，`content` 就是那句话。
7. 第 5 段：传异常元组，兜住后的话术是框架模板 `Error: ... Please fix your mistakes.`。
8. 第 6、7 段：工具名不存在、参数缺失属于「调用错误」，默认就会变成 `ToolMessage` 回给模型。""",
                "output": """# 程序输出
=== 1. 一次工具调用 ===
  search_course  id=c1 status=success content='第 6 章 State'

=== 2. 并行两次调用 ===
  返回条数: 2
    id=c1 第 18 章 工具节点
    id=c2 第 18 章 的摘要

=== 3. 工具抛异常（默认配置）===
  直接抛出: ZeroDivisionError division by zero

=== 4. 换成字符串兜底 ===
  status: error | content: 计算工具暂时不可用，请换个问题

=== 5. 只兜指定异常 ===
  content: Error: ZeroDivisionError('division by zero')
 Please fix your mistakes.

=== 6. 工具名不存在 ===
  content: Error: nope is not a valid tool, try one of [search_course, read_lesson, divide].

=== 7. 参数缺失 ===
  content: Error invoking tool 'divide' with kwargs {'a': 1} with error:  b: Field required  Please fix the error and try again.""",
                "mistakes": """- 以为 `ToolNode` 会兜住所有异常：业务异常直接炸穿整张图（第 3 段）。
- 脱离图直接 `ToolNode([...]).invoke({...})`，报 `Missing required config key`——它是节点，需要运行时。
- 用默认策略却指望得到自定义话术：兜住的错误是 `Error: ... Please fix your mistakes.` 模板。
- 忘记 `add_edge("tools", "agent")` 回边：工具结果没人消费，图在工具节点后就结束了。
- 条件边写成 `lambda s: "tools"`，没有出口，跑成无限循环直到 `GraphRecursionError`。
- 工具里 `print` 一堆调试日志，把 `ToolMessage` 的内容和日志混在一起，线上没法查。""",
                "error_analysis": """`ValueError: Missing required config key ... for 'tools'`
—— 把 `ToolNode` 当普通函数直接调用了。它必须在图里跑。

`ZeroDivisionError` / 任何业务异常冒到顶层
—— 默认只兜「调用错误」。用 `handle_tool_errors` 显式兜住需要的异常类型。

`Error: nope is not a valid tool, try one of [...]`
—— 模型编了一个不存在的工具名。检查工具的 `description` 是否让人误解，或工具列表是否没传全。

`Error invoking tool 'divide' with kwargs {'a': 1} ... Field required`
—— 模型漏传必填参数。把参数说明写清楚（第 17 章），或给参数默认值。""",
                "beginner_practice": """1. 给 `search_course` 加一个会抛 `ValueError` 的分支（比如关键词为空），用三种 `handle_tool_errors` 写法各跑一次，对比 `status` 与 `content`。
2. 把第 2 段的两个调用改成同一个工具调两次，观察 `id` 不同的两条结果。""",
                "advanced_practice": """设计一套线上可用的错误策略：调用错误交给模型自纠；业务异常记日志后返回「稍后重试」；超时直接让图重试。
写出 `handle_tool_errors` 的实现，并说明哪些异常绝不该变成 `ToolMessage`。""",
                "quiz_note": "本节 6 道题：2 道基础理解（`ToolNode` 的输入输出、默认兜什么）+ 2 道代码阅读（除零为什么冒到顶层、`status` 何时为 error）+ 2 道应用练习（选哪种 `handle_tool_errors`、补回边与上限）。",
                "summary": """`ToolNode` = 找工具 + 执行 + 包消息 + 兜调用错误。
业务异常默认不兜，要用 `handle_tool_errors` 显式表态。
`tools_condition` 负责分支，回边负责「观察完继续想」。""",
                "next_lesson": "零件齐了：模型、工具、工具节点、条件边。下一章把它们拼成一个会自己循环的 Agent。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-18-01",
                        "name": "工具节点与错误处理",
                        "goal": "能用 `ToolNode` 装配工具执行，并按场景选择错误策略。",
                        "minutes": 40,
                        "criteria": "能说出默认策略兜什么、不兜什么，并写出四种 `handle_tool_errors` 用法。",
                        "requires": ["langgraph-agent-17-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-18-01-1",
                        "kp": 0,
                        "title": "选对兜底方式",
                        "description": "业务要求：工具超时可以重试，参数错误要让模型改，其它异常记日志后回一句「服务繁忙」。写出 `handle_tool_errors`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''import logging

logger = logging.getLogger(__name__)


def handle(e: Exception) -> str:
    if isinstance(e, TimeoutError):
        raise e                       # 交给图的重试策略，不要变成消息
    if isinstance(e, ValueError):
        return f"参数有问题：{e}，请调整后重试"
    logger.exception("工具执行失败")
    return "服务繁忙，请稍后再试"


node = ToolNode(tools, handle_tool_errors=handle)''',
                        "explanation": "关键在 `raise e`：超时要能被重试策略接住，变成 `ToolMessage` 就等于把「可重试」改成了「已失败」。",
                    },
                    {
                        "code": "lg-ex-18-01-2",
                        "kp": 0,
                        "title": "为什么默认不兜业务异常",
                        "description": "框架默认只兜调用错误，业务异常直接抛。这个默认值合理吗？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """合理，因为两类错误的处理方式根本不同。

调用错误（工具名不存在、参数缺失）是「模型可以自己改」的问题：把原因回给它，它下一轮就会换个工具或补上参数，
这是 Agent 自我修正的主要来源。

业务异常（除零、数据库连不上、第三方接口 500）是「模型改不了」的问题。把它变成一句错误消息，
模型很可能拿这句话当事实继续编，甚至反复重试同一个必然失败的动作——错误被吞掉，排查线索也一起没了。

所以默认策略是：能自纠的交给模型，不能自纠的炸出来给人看。

要用的话也很简单：明确写 `handle_tool_errors`，并在里面区分「可重试」「可自纠」「只能报障」三类。""",
                        "explanation": "错误处理的默认值体现设计者的判断：默认让机器自愈，还是默认让人看见。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-18-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`ToolNode` 执行完后返回什么？",
                        "options": [
                            ("A", "一个字符串结果"),
                            ("B", "形如 `{\"messages\": [ToolMessage, ...]}` 的状态增量"),
                            ("C", "一条 `AIMessage`"),
                            ("D", "一个布尔值表示成功与否"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它是节点，所以按节点的约定返回状态增量；工具结果装在 `ToolMessage` 里，一条调用一条消息。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-18-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "默认配置下，工具内部抛出的 `ZeroDivisionError` 会被包成 `ToolMessage` 返回给模型。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "默认只兜「调用错误」（工具不存在、参数缺失）。业务异常直接向上抛，示例第 3 段就是证据。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-18-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第 3 段为什么是 `try/except ZeroDivisionError` 才接住异常？",
                        "options": [
                            ("A", "因为 `ToolNode` 默认会把业务异常重新抛出"),
                            ("B", "因为 `divide` 工具写错了"),
                            ("C", "因为 `ToolNode` 只能处理一个工具"),
                            ("D", "因为状态里没有 `messages`"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "默认策略只把一个特定异常类型转成消息，其余原样抛出。所以外层不用 `try` 就会看到整张图崩。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-18-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第 6 段（工具名不存在）没有配 `handle_tool_errors`，为什么也没抛异常？",
                        "options": [
                            ("A", "因为 `nope` 被当成合法工具名"),
                            ("B", "因为「工具不存在」属于调用错误，默认就会兜成 `ToolMessage`"),
                            ("C", "因为 `ToolNode` 忽略了未知工具"),
                            ("D", "因为假模型拦住了异常"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "框架把它归为「模型可以自己修」的错误，所以回一条带可用工具清单的消息，让模型重选。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-18-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "`handle_tool_errors` 的四种取值（默认 / 字符串 / 异常元组 / 可调用）分别适合什么场景？",
                        "options": [],
                        "answer": """默认（`True`）：只让模型自纠调用错误，业务异常暴露给人。适合开发期与内部工具。

字符串：所有被兜住的异常都回同一句话。适合对用户话术有统一要求的场景，比如「服务繁忙，请稍后再试」。
缺点是丢掉了具体原因，日志必须另外记。

异常元组：只把指定的几类异常转成消息，其余照旧抛出。适合「已知某几类是可自纠的」的场景，
比字符串精细，比可调用简单。

可调用：自己根据异常类型决定话术，甚至决定「转消息还是继续抛」。适合线上。
注意在可调用里对「该重试」的异常要 `raise`，否则重试策略永远接不到。""",
                        "explanation": "选型的核心问题只有一个：这个异常，模型能自己修吗？能，就转成消息；不能，就抛出来。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-18-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补完装配代码：让 agent 节点在有工具调用时去 `tools`，否则结束；并给循环加上 6 步上限。",
                        "options": [],
                        "answer": {
                            "value": "builder.add_node(\"tools\", ToolNode(tools))\nbuilder.add_edge(START, \"agent\")\nbuilder.add_conditional_edges(\"agent\", tools_condition)\nbuilder.add_edge(\"tools\", \"agent\")\ngraph = builder.compile()\n\nresult = graph.invoke(\n    {\"messages\": [HumanMessage(\"问题\")]},\n    config={\"recursion_limit\": 6},\n)"
                        },
                        "explanation": "三件事缺一不可：条件边给出两个出口、工具节点回到 agent、上限防止模型陷在工具里出不来。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 19 章
    {
        "code": "langgraph-agent-19",
        "order_index": 19,
        "title": "Agent 工作流",
        "description": "把模型、工具、条件边拼成一个会「想—做—看」的循环。",
        "lessons": [
            {
                "code": "langgraph-agent-19-lesson-01",
                "title": "手写 ReAct 图",
                "objectives": """1. 能用「两个节点 + 一条回边 + 一条条件边」画出 ReAct；
2. 能解释 `tools_condition` 凭什么决定「继续」还是「结束」；
3. 能读懂消息序列为什么是 `Human -> AI -> Tool -> AI`；
4. 能用假模型离线调试整条循环，不消耗额度。""",
                "why_learn": """前面几章的零件到这里第一次合体。ReAct 是 Agent 最基础的形态，也是所有「会自动调工具的助手」的共同骨架。
自己拼一遍，你才知道预制组件替你做了什么、什么时候该绕开它。""",
                "concepts": """**ReAct**：Reason + Act。想一步、做一步、看结果、再想，直到能回答。
**两个节点**：`agent`（调模型）与 `tools`（执行工具）。
**一条回边**：`tools -> agent`，把观察结果送回思考。
**一条条件边**：`agent -> tools` 或 `agent -> END`，由有没有 `tool_calls` 决定。
**消息累积**：`MessagesState` 用 `add_messages`，所以每轮都在原有历史上追加，模型能看到自己做过什么。
**假模型**：按剧本返回消息，让循环可复现、可断言。""",
                "plain": """ReAct 循环用一句话说清：模型说「我要查 X」，你去查，把结果给它，它再决定「够了我来回答」还是「再查 Y」。

图上有两个节点。`agent` 负责想：它看历史消息，可能给出工具调用。`tools` 负责做：它执行调用，把结果塞回消息。
从 `tools` 回到 `agent` 的那条边就是「观察后再想」；从 `agent` 直接到 `END` 的那条边就是「不想再查了」。

这个循环必须有刹车的条件，否则模型一直想查，图就一直转。`tools_condition` 就是那个刹车：
模型这一轮没有给工具调用，它就把你送到 `END`。

示例里用的是「按剧本说话」的假模型，好处是循环的每一步你都能提前知道，输出也每次都一样。
真模型接进来之后，图的结构一个字都不用改。""",
                "syntax": """**骨架**

```python
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

builder = StateGraph(MessagesState)
builder.add_node("agent", agent)         # 调模型
builder.add_node("tools", ToolNode(tools))  # 执行工具
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)  # "tools" 或 "__end__"
builder.add_edge("tools", "agent")       # 观察完回到思考
graph = builder.compile()
```

- `tools_condition` 的返回值就两个：有 `tool_calls` 给 `"tools"`，否则给 `"__end__"`。
- `MessagesState` 自带 `Annotated[list, add_messages]`，不用自己声明。
- 循环次数上限由 `recursion_limit` 控制（第 14 章），生产环境一定要设。""",
                "example_code": '''from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


@tool
def search_course(keyword: str) -> str:
    """按关键词检索课程资料，返回匹配的章节标题。"""
    table = {"state": "第 6 章 State：状态结构", "tool": "第 18 章 工具节点"}
    for key, title in table.items():
        if key in keyword.lower():
            return title
    return "没有匹配的章节"


@tool
def read_lesson(chapter: str) -> str:
    """读取指定章节的正文摘要。"""
    return f"{chapter} 的正文摘要：状态是节点之间传递的唯一数据。"


tools = [search_course, read_lesson]

# 用「按剧本回复的假模型」代替真模型，方便离线观察循环
script = [
    AIMessage(content="", tool_calls=[{"name": "search_course", "args": {"keyword": "state"}, "id": "c1"}]),
    AIMessage(content="", tool_calls=[{"name": "read_lesson", "args": {"chapter": "第 6 章"}, "id": "c2"}]),
    AIMessage(content="State 在第 6 章，它决定节点之间传什么数据。"),
]
model = FakeMessagesListChatModel(responses=script)


def agent(state: MessagesState) -> dict:
    """思考：把当前对话交给模型，模型可能要求调工具。"""
    return {"messages": [model.invoke(state["messages"])]}


builder = StateGraph(MessagesState)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)   # 有 tool_calls -> tools，否则 -> END
builder.add_edge("tools", "agent")                        # 观察完回到思考
graph = builder.compile()

result = graph.invoke({"messages": [HumanMessage("State 是什么，顺便把第 6 章摘要给我")]})

print("=== 消息序列 ===")
for i, m in enumerate(result["messages"], 1):
    calls = [c["name"] for c in getattr(m, "tool_calls", []) or []]
    print(f"{i}. {type(m).__name__:14s} tool_calls={calls} content={str(m.content)[:34]!r}")

print()
print("=== 最后一句 ===")
print(result["messages"][-1].content)''',
                "code_lines": """1. 两个工具分别负责「找章节」和「读正文」，模型需要两个都调一次才能回答问题。
2. 剧本三条：先查章节、再读正文、最后作答——这正好演示了两轮循环。
3. `agent` 节点只有一行核心逻辑：`model.invoke(state["messages"])`，把整段历史交给模型。
4. `MessagesState` 用 `add_messages` 累积，所以模型每轮都能看到之前的工具结果。
5. `add_conditional_edges("agent", tools_condition)` 给 `agent` 两个出口：继续调工具，或直接结束。
6. `add_edge("tools", "agent")` 是回边，没有它循环只有半圈，工具结果没人用。
7. 输出里 1、3、5 是「输入与观察」，2、4、6 是「思考与回答」——交替出现就是 ReAct 的形状。
8. 第 6 条消息没有 `tool_calls`，条件边把流程送去 `__end__`，循环自然停下。""",
                "output": """# 程序输出
=== 消息序列 ===
1. HumanMessage   tool_calls=[] content='State 是什么，顺便把第 6 章摘要给我'
2. AIMessage      tool_calls=['search_course'] content=''
3. ToolMessage    tool_calls=[] content='第 6 章 State：状态结构'
4. AIMessage      tool_calls=['read_lesson'] content=''
5. ToolMessage    tool_calls=[] content='第 6 章 的正文摘要：状态是节点之间传递的唯一数据。'
6. AIMessage      tool_calls=[] content='State 在第 6 章，它决定节点之间传什么数据。'

=== 最后一句 ===
State 在第 6 章，它决定节点之间传什么数据。""",
                "mistakes": """- 忘了 `add_edge("tools", "agent")`：图在工具节点后就结束，最终答案是工具结果而不是回答。
- 条件边写成固定返回 `"tools"`：模型不再调工具时仍被送去工具节点，跑到 `GraphRecursionError`。
- 用普通 `list` 而不是 `MessagesState` 存消息，每轮覆盖，模型永远只看得到最后一条。
- 不给 `recursion_limit`：一个死循环的工具调用能跑很久，账单一并变长。
- 在 `agent` 节点里自己拼消息（只传最后一条 `HumanMessage`），模型看不到工具结果，会重复调同一个工具。
- 用真模型做单元测试：结果不稳定、还花钱。测试用假模型，联调用真模型。""",
                "error_analysis": """`GraphRecursionError: Recursion limit of 25 reached`
—— 循环没有出口。检查 `tools_condition` 是否真的生效，以及模型是否一直给 `tool_calls`。

最终回答是工具结果，不是自然语言
—— 少了回边，流程在 `tools` 后直接结束。

模型重复调用同一个工具
—— 工具结果没进历史，或 `agent` 节点没把完整 `messages` 传给模型。

`TypeError: Object of type ToolMessage is not JSON serializable`
—— 某处把消息对象当普通 dict 处理了，检查是否手动做序列化。""",
                "beginner_practice": """1. 把剧本改成只调一个工具，观察消息序列变成几条。
2. 删掉 `add_edge("tools", "agent")`，再跑一次，看最终答案变成了什么。""",
                "advanced_practice": """给这张图加一个「工具调用次数上限」：超过 3 次就强制结束并返回「信息不足」。
说明你会用状态字段、条件边还是 `recursion_limit` 来实现，以及各自的取舍。""",
                "quiz_note": "本节 6 道题：2 道基础理解（ReAct 的回边作用、`tools_condition` 的两个返回值）+ 2 道代码阅读（消息序列为什么交替、删掉回边会怎样）+ 2 道应用练习（加循环上限、为什么用假模型）。",
                "summary": """ReAct = agent 想 + tools 做 + 回边观察 + 条件边刹车。
`MessagesState` 负责累积历史，模型因此能看到自己做过什么。
循环必须有出口：条件边给出口，`recursion_limit` 保底。""",
                "next_lesson": "这张图和你听过的「预制 Agent」是什么关系？下一节对比三种工作流形态，并说清预制组件的版本变化。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-19-01",
                        "name": "手写 ReAct 循环",
                        "goal": "能独立装配带工具循环的 Agent 图，并控制其退出。",
                        "minutes": 45,
                        "criteria": "能解释每条边的作用，并在缺边时定位症状。",
                        "requires": ["langgraph-agent-18-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-19-01-1",
                        "kp": 0,
                        "title": "给循环装刹车",
                        "description": "在状态里加一个 `tool_calls_used: int`，让工具调用累计超过 3 次时直接结束，并返回「信息不足」。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    tool_calls_used: int


def agent(state: AgentState) -> dict:
    return {"messages": [model.invoke(state["messages"])]}


def route(state: AgentState) -> str:
    last = state["messages"][-1]
    if not getattr(last, "tool_calls", None):
        return "end"
    if state.get("tool_calls_used", 0) >= 3:
        return "give_up"
    return "tools"


def count_tools(state: AgentState) -> dict:
    used = state.get("tool_calls_used", 0)
    last = state["messages"][-1]
    return {"tool_calls_used": used + len(getattr(last, "tool_calls", []) or [])}


def give_up(state: AgentState) -> dict:
    return {"messages": [AIMessage(content="信息不足，先到这里。")]}


builder = StateGraph(AgentState)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(tools))
builder.add_node("count", count_tools)
builder.add_node("give_up", give_up)
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route, {"tools": "tools", "give_up": "give_up", "end": END})
builder.add_edge("tools", "count")
builder.add_edge("count", "agent")
builder.add_edge("give_up", END)
graph = builder.compile()''',
                        "explanation": "用状态字段做上限比只靠 `recursion_limit` 更好：能主动给用户一句解释，而不是抛异常。代价是多一个计数节点。",
                    },
                    {
                        "code": "lg-ex-19-01-2",
                        "kp": 0,
                        "title": "为什么测试要用假模型",
                        "description": "写 ReAct 的单元测试时，用真模型和用假模型有什么本质区别？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """本质区别是「测的是图，还是测的模型」。

用真模型：同一个输入两次可能给出不同的工具调用，断言只能写得很松（比如「消息变多了」）。
你无法判断失败是图接错了，还是模型今天心情不同。而且还花钱、要网络、慢。

用假模型：剧本固定，就能精确断言「第 2 条必须是带 search_course 的 AIMessage」「第 3 条必须是
tool_call_id 为 c1 的 ToolMessage」。图接错立刻红。

正确分工是两层：单元测试用假模型锁住图的结构；联调与评测用真模型看效果。
把两件事混在一层，就会得到「偶尔失败、重跑就好」的测试，那种测试很快会被忽略。""",
                        "explanation": "可复现是测试的前提。模型的不确定性应该被隔离在评测层，而不是泄漏进单元测试。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-19-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "ReAct 循环里，哪条边让模型能看到工具的执行结果？",
                        "options": [
                            ("A", "`START -> agent`"),
                            ("B", "`agent -> tools`"),
                            ("C", "`tools -> agent` 这条回边"),
                            ("D", "`agent -> END`"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "回边把工具产出的 `ToolMessage` 送进历史，模型下一轮才看得到。删掉它，循环只有半圈。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-19-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "模型这一轮没有返回 `tool_calls` 时，`tools_condition` 返回 `\"__end__\"`。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "这正是循环的刹车：没有工具调用就说明模型认为可以作答了，流程直接结束。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-19-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "输出里第 2 条和第 4 条的 `tool_calls` 分别是什么？为什么？",
                        "options": [
                            ("A", "都是 `search_course`，因为剧本只写了一个"),
                            ("B", "第 2 条是 `search_course`，第 4 条是 `read_lesson`，因为剧本按顺序返回"),
                            ("C", "第 2 条为空，第 4 条是 `read_lesson`"),
                            ("D", "两条都为空，工具是 `ToolNode` 自动选的"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "假模型严格按 `responses` 列表顺序返回，所以每条消息的内容由剧本决定，与图无关——这正是它适合调试的原因。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-19-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "如果删掉 `builder.add_edge(\"tools\", \"agent\")`，这次运行的最终结果会变成什么？",
                        "options": [
                            ("A", "报错，图无法编译"),
                            ("B", "在第一次工具执行后结束，`messages` 的最后一条是 `ToolMessage`"),
                            ("C", "仍然正常，`tools` 会自动回到 `agent`"),
                            ("D", "循环执行两次后结束"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`tools` 没有出边就走到终点，拿到的是工具结果而不是自然语言回答。这个症状很典型：答案「像日志」。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-19-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给这次调用加上 8 步上限，并说明超限时会发生什么。",
                        "options": [],
                        "answer": {
                            "value": "result = graph.invoke(\n    {\"messages\": [HumanMessage(\"State 是什么\")]},\n    config={\"recursion_limit\": 8},\n)"
                        },
                        "explanation": "超限抛 `GraphRecursionError`。示例这次只走 6 步，8 够用；若设成 4 就会在执行中被截断——上限要按「一次问答最多几轮工具」估算。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-19-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么调试这张图时要用「按剧本回复」的假模型，而不是直接接真模型？",
                        "options": [],
                        "answer": """因为调试的目标不同。

调图的时候，你要验证的是「边接对没、消息顺序对不对、出口在不在」。这些与模型无关。
真模型每次给的 `tool_calls` 都可能不同，失败时你分不清是图错了还是模型变了。

假模型把不确定性抽走：剧本固定，就能断言第几条消息一定是什么类型、`tool_call_id` 是多少。
图接错立刻暴露，而且不花钱、不联网、秒级重复。

接真模型是下一步的事，那时关注点变成「回答质量」，用的是另一套方法（评测集、对比跑分）。""",
                        "explanation": "分层的意义：结构用确定性的手段验证，效果用统计性的手段评估。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-19-lesson-02",
                "title": "工作流形态与版本定位",
                "objectives": """1. 能区分固定链、路由图、ReAct 循环三种形态，并按「有没有分支」选择；
2. 能说清 `create_react_agent` 在 langgraph 1.2.20 的弃用状态与官方给出的替代；
3. 能读懂预制 Agent 导出的图结构，确认它与手写版同构；
4. 能说明为什么学习顺序是「先手写、后预制」。""",
                "why_learn": """同一个需求可以用三种图表达，选错了要么写死流程不够灵活，要么为一个固定步骤引入不必要的循环。
另外一个现实问题：网上大量教程用的 `create_react_agent` 在新版本里已被弃用，照抄会踩坑。""",
                "concepts": """**固定链**：节点顺序写死，没有分支。适合流程确定的场景（翻译、摘要、固定字段抽取）。
**路由图**：在链上插入条件边，按数据选一条支路。适合「分类后走不同处理」的场景。
**ReAct 循环**：有回边，模型自己决定调几次工具。适合「步骤数量不确定」的探索式任务。
**预制 Agent**：`create_react_agent` 就是把 19-1 那张图装配好；在 1.2.20 已标记弃用，指向 `langchain.agents.create_agent`。
**版本事实**：弃用告警类别是 `LangGraphDeprecatedSinceV10`，提示「将在 V2.0 移除」；本机没装 `langchain` 包，因此该替代入口暂不可用。
**为什么先手写**：知道每条边的作用，才能在预制组件不适用时自己改。""",
                "plain": """三种形态的分界线不是「高级不高级」，而是「下一步由谁决定」。

下一步由代码写死，就是固定链；由数据里的某个字段决定，就是路由图；由模型每一轮临时决定，就是 ReAct。

选型的判断很简单：如果你的流程里「第几步做什么」是产品经理能画出来的，别用 ReAct——它更贵、更慢、更难测。
反过来，如果用户的问题可能需要查三次也可能一次都不用查，固定链就写不出来。

关于预制 Agent，有个必须说清的现实：`create_react_agent` 在当前版本已经带弃用告警，
官方让迁到 `langchain.agents.create_agent`。网上大量教程还停在旧写法，
你照抄会看到告警，甚至在没装 `langchain` 的环境里直接 `ImportError`。

所以这一节的重点不是「记住哪个函数名」，而是「看懂预制组件装的是哪张图」——
这样它改名、换包、加参数，你都能自己接上。""",
                "syntax": """**三种形态的骨架差异**

```python
# 1) 固定链：只有 add_edge
builder.add_edge(START, "a"); builder.add_edge("a", "b"); builder.add_edge("b", END)

# 2) 路由图：链 + 条件边
builder.add_conditional_edges("classify", route, {"x": "x_node", "y": "y_node"})

# 3) ReAct：链 + 条件边 + 回边
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")
```

**预制 Agent 的现状（langgraph 1.2.20）**

```python
from langgraph.prebuilt import create_react_agent   # 会发弃用告警
# LangGraphDeprecatedSinceV10: create_react_agent has been moved to `langchain.agents`.
# 请改用：from langchain.agents import create_agent
```

- 弃用不等于不能用：当前版本仍可运行，V2.0 才移除。
- 替代入口在 `langchain` 包（不是 `langchain-core`），需要单独安装。
- 预制 Agent 要求模型实现 `bind_tools`，否则一构造就 `NotImplementedError`。""",
                "example_code": '''import warnings

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


@tool
def search_course(keyword: str) -> str:
    """按关键词检索课程资料，返回匹配的章节标题。"""
    return "第 6 章 State：状态结构"


# --- 形态一：固定链，没有分支 -----------------------------------------------
def retrieve(state: MessagesState) -> dict:
    return {"messages": [AIMessage(content="检索结果：第 6 章 State")]}


def answer(state: MessagesState) -> dict:
    return {"messages": [AIMessage(content="State 在第 6 章。")]}


chain = StateGraph(MessagesState)
chain.add_node("retrieve", retrieve)
chain.add_node("answer", answer)
chain.add_edge(START, "retrieve")
chain.add_edge("retrieve", "answer")
chain.add_edge("answer", END)
chain_graph = chain.compile()

print("=== 形态一：固定链 ===")
print("节点:", sorted(chain_graph.get_graph().nodes.keys() - {"__start__", "__end__"}))
print("回答:", chain_graph.invoke({"messages": [HumanMessage("State 在哪")]})["messages"][-1].content)


# --- 形态二：手写 ReAct（就是上一节那张图）----------------------------------
script = [
    AIMessage(content="", tool_calls=[{"name": "search_course", "args": {"keyword": "state"}, "id": "c1"}]),
    AIMessage(content="State 在第 6 章，讲的是状态结构。"),
]


class ScriptedToolModel(BaseChatModel):
    """按剧本回复的假模型，同时假装支持工具绑定。"""

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self                      # 剧本里已写好工具调用，绑定只走形式

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=script.pop(0))])


model = ScriptedToolModel()


def agent(state: MessagesState) -> dict:
    return {"messages": [model.invoke(state["messages"])]}


builder = StateGraph(MessagesState)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode([search_course]))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")
hand_graph = builder.compile()

print()
print("=== 形态二：手写 ReAct ===")
out = hand_graph.invoke({"messages": [HumanMessage("State 在哪")]})
for m in out["messages"]:
    print(f"  {type(m).__name__:14s} {str(m.content)[:26]!r}")

# --- 形态三：预制 Agent ------------------------------------------------------
script2 = [
    AIMessage(content="", tool_calls=[{"name": "search_course", "args": {"keyword": "state"}, "id": "c1"}]),
    AIMessage(content="State 在第 6 章。"),
]


class ScriptedToolModel2(ScriptedToolModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=script2.pop(0))])


print()
print("=== 形态三：预制 Agent ===")
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    from langgraph.prebuilt import create_react_agent

    prebuilt = create_react_agent(model=ScriptedToolModel2(), tools=[search_course])
    for w in caught:
        print("告警:", w.category.__name__)
        print("内容:", str(w.message))

print()
print("=== 预制 Agent 的图结构 ===")
print(prebuilt.get_graph().draw_mermaid())''',
                "code_lines": """1. 形态一只有 `add_edge`：`START -> retrieve -> answer -> END`，没有任何分支。
2. `get_graph().nodes` 里带着 `__start__` 与 `__end__`，所以打印前把它们减掉，只留自己定义的节点。
3. `ScriptedToolModel` 的 `bind_tools` 直接 `return self`：剧本已写好工具调用，绑定只需不报错。
4. 形态二就是上一节的四行装配，输出里能看到 `Human -> AI -> Tool -> AI` 的交替。
5. 形态三用 `warnings.catch_warnings(record=True)` 把告警抓下来打印，否则它只在 stderr 一闪而过。
6. 告警类别是 `LangGraphDeprecatedSinceV10`，内容明确说「已移到 `langchain.agents`，V2.0 移除」。
7. 最后的 Mermaid 结构里，预制 Agent 同样是 `agent` 与 `tools` 两个节点、一条回边、两条条件出边。
8. 也就是说：预制组件省的是装配代码，不是省掉了那张图——图你迟早要读懂。""",
                "output": """# 程序输出
=== 形态一：固定链 ===
节点: ['answer', 'retrieve']
回答: State 在第 6 章。

=== 形态二：手写 ReAct ===
  HumanMessage   'State 在哪'
  AIMessage      ''
  ToolMessage    '第 6 章 State：状态结构'
  AIMessage      'State 在第 6 章，讲的是状态结构。'

=== 形态三：预制 Agent ===
告警: LangGraphDeprecatedSinceV10
内容: create_react_agent has been moved to `langchain.agents`. Please update your import to `from langchain.agents import create_agent`. Deprecated in LangGraph V1.0 to be removed in V2.0.

=== 预制 Agent 的图结构 ===
---
config:
  flowchart:
    curve: linear
---
graph TD;
\t__start__([<p>__start__</p>]):::first
\tagent(agent)
\ttools(tools<hr/><small><em>__tools = search_course</em></small>)
\t__end__([<p>__end__</p>]):::last
\t__start__ --> agent;
\tagent -.-> __end__;
\tagent -.-> tools;
\ttools --> agent;
\tclassDef default fill:#f2f0ff,line-height:1.2
\tclassDef first fill-opacity:0
\tclassDef last fill:#bfb6fc""",
                "mistakes": """- 明明流程固定却用 ReAct：多花 token、多等几秒，还引入不确定性。
- 明明分支很多却用固定链：每加一种情况就要改图结构。
- 照抄旧教程的 `create_react_agent`，在没装 `langchain` 的环境里直接 `ImportError`。
- 把 `create_react_agent` 的告警当错误处理，以为功能坏了——它是提醒迁移，当前仍可用。
- 给预制 Agent 传一个没实现 `bind_tools` 的模型，构造阶段就 `NotImplementedError`。
- 以为「用了预制 Agent 就不用懂图」：参数一多就开始猜，出问题定位不了。""",
                "error_analysis": """`ImportError: Please install langchain (pip install langchain) to use '<provider>:<model>' string syntax`
—— 用字符串指定模型时，预制 Agent 会去 `langchain` 包里找 `init_chat_model`。要么装包，要么直接传模型对象。

`NotImplementedError`（构造 `create_react_agent` 时）
—— 传进去的模型没实现 `bind_tools`。用第 17 章那个兼容模型，或换成支持工具绑定的实现。

`LangGraphDeprecatedSinceV10` 告警
—— 不是错误，是迁移提示。当前版本可继续用，升级到 V2 前要换成 `langchain.agents.create_agent`。

返回的图里多出 `tools` 节点名不一致
—— 预制 Agent 允许自定义节点名，读图前先看实际名字，不要硬编码。""",
                "beginner_practice": """1. 给形态一的固定链加一个条件边，让它变成「路由图」，观察节点数与箭头变化。
2. 把告警捕获那段注释掉，再运行，观察告警默认输出到哪里。""",
                "advanced_practice": """查一下你所在项目锁定的 langgraph 版本，写一份迁移说明：当前用哪个入口、升级到下一大版本要改哪一行、如何在不改业务代码的前提下先做兼容。""",
                "quiz_note": "本节 6 道题：2 道基础理解（三种形态的分界、弃用告警的性质）+ 2 道代码阅读（预制图为什么和手写同构、`bind_tools` 为什么返回 self）+ 2 道应用练习（如何选形态、写出手写装配）。",
                "summary": """形态由「下一步谁决定」区分：写死、按数据、按模型。
`create_react_agent` 在 1.2.20 已弃用，指向 `langchain.agents.create_agent`；它装的就是 19-1 那张图。
先手写、后预制：读懂图，才接得住组件的版本变化。""",
                "next_lesson": "到这里，Agent 已经会思考、会调工具。下一章解决另一个问题：进程重启后，对话还在不在？",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-19-02",
                        "name": "工作流形态与版本定位",
                        "goal": "能按需求选择工作流形态，并正确处理预制 Agent 的版本变化。",
                        "minutes": 35,
                        "criteria": "能说出三种形态的分界，并给出 `create_react_agent` 的替代路径。",
                        "requires": ["langgraph-agent-19-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-19-02-1",
                        "kp": 0,
                        "title": "选形态",
                        "description": "三个需求：① 把用户问题翻译成英文再入库；② 按问题类型分别走「查课表」和「查成绩」；③ 回答课程问题，需要时反复查资料。分别选哪种形态？",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": """① 固定链：步骤固定、无分支，用条件边都是浪费。
② 路由图：分类一次，之后各走各的支路，支路内部仍是固定链。
③ ReAct 循环：查几次资料事先不知道，只能由模型每轮决定。

判断标准只有一条：下一步由谁决定。写死 -> 固定链；数据决定 -> 路由图；模型决定 -> ReAct。

补充：真实项目常常是混合的——外层路由图选择业务线，某条支路内部是一个 ReAct 循环。
三种形态不是互斥选项，而是可以嵌套的零件。""",
                        "explanation": "「混合」是生产环境的常态：先用路由缩小范围，再在范围内让模型自由探索。",
                    },
                    {
                        "code": "lg-ex-19-02-2",
                        "kp": 0,
                        "title": "迁移到新入口",
                        "description": "项目里现在写的是 `from langgraph.prebuilt import create_react_agent`。写出迁移方案。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''# 迁移前（langgraph 1.2.20 会发 LangGraphDeprecatedSinceV10）
from langgraph.prebuilt import create_react_agent

# 迁移后（需要安装 langchain 包）
from langchain.agents import create_agent

agent = create_agent(model=llm, tools=tools)

# 过渡期：把构造入口收在一处，业务代码只依赖这个函数
def build_agent(model, tools):
    try:
        from langchain.agents import create_agent
    except ImportError:
        from langgraph.prebuilt import create_react_agent as create_agent
    return create_agent(model=model, tools=tools)''',
                        "explanation": "关键是「入口收口」：业务代码只调 `build_agent`，换包时改一处。别把 import 散落在十个文件里。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-19-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "区分三种工作流形态的关键问题是什么？",
                        "options": [
                            ("A", "用了几个节点"),
                            ("B", "下一步由谁决定：代码、数据，还是模型"),
                            ("C", "有没有用工具"),
                            ("D", "用不用预制组件"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "节点数量与是否用工具都不是分界线。决定权在谁手里，才决定图的形状。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-19-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "在 langgraph 1.2.20 里，`create_react_agent` 一旦调用就会直接抛出异常，无法使用。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它发出的是 `LangGraphDeprecatedSinceV10` 告警，功能仍可用，V2.0 才移除。告警与异常是两件事。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-19-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "为什么预制 Agent 导出的图结构和手写版几乎一样？",
                        "options": [
                            ("A", "巧合"),
                            ("B", "预制 Agent 就是把 `agent + tools + 条件边 + 回边` 装配起来，图本身没变"),
                            ("C", "因为两者都用了同一个模型"),
                            ("D", "因为 `get_graph` 只显示模板"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "预制组件省的是装配代码。理解这点，参数变化、包迁移都不会让你措手不及。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-19-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例里 `ScriptedToolModel.bind_tools` 直接 `return self`，为什么这样也能跑通？",
                        "options": [
                            ("A", "因为 `bind_tools` 可以随便返回"),
                            ("B", "因为剧本里已经写死了工具调用，绑定只需不报错；预制 Agent 构造时会调用它"),
                            ("C", "因为预制 Agent 不会调用 `bind_tools`"),
                            ("D", "因为 `_generate` 里忽略了入参"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "如果完全不实现，构造时就会 `NotImplementedError`（第 17 章验证过）。返回 self 是「假装绑过」的最小实现。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-19-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "什么情况下应该自己画图，而不是用预制 Agent？",
                        "options": [],
                        "answer": """四种典型情况。

① 流程里有必须人工确认的一步（如退款、发邮件），需要在图中插中断点，预制 Agent 的固定形状放不下。

② 需要在调模型前后插入确定性的处理：权限校验、字段脱敏、结果校验。这些不该交给模型决定。

③ 需要多个 Agent 分工（子图），或者一条支路用固定链、一条用循环。

④ 需要对每一步单独设策略：不同的重试次数、不同的超时、不同的缓存。

反过来说，如果需求就是「给模型一堆工具，让它自己查」，预制 Agent 完全够用，
而且比你手写更不容易漏掉细节。

判断标准：图的结构是否需要按业务定制。需要，就自己画；不需要，就用预制。""",
                        "explanation": "预制组件的价值在于「标准形状开箱即用」，不在于「替代你理解图」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-19-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写出「手写 ReAct」的装配代码（含入口、两个节点、条件边、回边），并说明每条边的作用。",
                        "options": [],
                        "answer": {
                            "value": "builder = StateGraph(MessagesState)\nbuilder.add_node(\"agent\", agent)\nbuilder.add_node(\"tools\", ToolNode(tools))\nbuilder.add_edge(START, \"agent\")                          # 入口：先进思考\nbuilder.add_conditional_edges(\"agent\", tools_condition)   # 有 tool_calls 去 tools，否则结束\nbuilder.add_edge(\"tools\", \"agent\")                        # 回边：观察完继续想\ngraph = builder.compile()"
                        },
                        "explanation": "四条边各司其职：入口、分支、回边。少入口跑不起来，少分支会死循环，少回边则看不到工具结果。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
