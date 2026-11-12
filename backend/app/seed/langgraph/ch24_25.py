"""LangGraph Agent 开发：第 24—27 章。

第 24 章把执行过程一段段推出去（`stream_mode` 与自定义事件）；
第 25 章处理「失败了怎么办」（`RetryPolicy` 与异常分类）；
第 26 章把图包成 FastAPI 接口（同步 + SSE）；
第 27 章用离线测试锁住图的行为。

版本口径（实测）：langgraph 1.2.20、langchain-core 1.7.6、fastapi 0.162.0、httpx 0.28.1。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 24 章
    {
        "code": "langgraph-agent-24",
        "order_index": 24,
        "title": "Streaming",
        "description": "不同流式模式给你不同的东西，选错就白忙一场。",
        "lessons": [
            {
                "code": "langgraph-agent-24-lesson-01",
                "title": "stream_mode 各模式",
                "objectives": """1. 能说出 `values / updates / messages / custom` 四种模式各自产出什么；
2. 能按「前端要什么」选择模式，而不是一律用 `values`；
3. 能用列表形式同时订阅多种模式，并读懂返回的 `(mode, chunk)` 元组；
4. 能说明 `custom` 模式必须配合节点里的 writer 才有效。""",
                "why_learn": """`invoke` 要等全部跑完才返回，用户盯着转圈十几秒。流式能让界面立刻动起来，
但选错模式会把整份状态反复推给前端——带宽浪费、前端还要自己 diff。""",
                "concepts": """**`values`**：每一步之后的**完整状态**。最直观，也最啰嗦。
**`updates`**：这一步**哪个节点写了什么**。最适合「按节点展示进度」。
**`messages`**：模型输出的**消息增量**与元数据（`langgraph_node`）。适合打字机效果。
**`custom`**：节点里用 `get_stream_writer()` 主动发的事件。适合「检索中 20%」这类业务进度。
**多模式**：`stream_mode=["updates", "custom"]`，每个 chunk 是 `(mode, payload)`。
**`debug`**：任务级事件（`task` / `task_result`），排查用，不要给用户看。""",
                "plain": """四种模式不是「四个档位」，而是「四种视角」。

`values` 是每一步拍一张全身照，`updates` 是只拍这一步动的部分，`messages` 是拍模型嘴里蹦出来的字，
`custom` 是你自己在代码里喊的那一嗓子「正在检索」。

所以选型的问法不是「哪个更高级」，而是「界面上要显示什么」。
要显示进度条，用 `updates` 加 `custom`；要做打字机，用 `messages`；要给调试面板，用 `debug`。

`custom` 有个前提：节点里必须有 `get_stream_writer()` 并真的调用它。没写的话这个模式什么都不产出，
不报错，你会以为「流式坏了」。

另外注意多模式返回的是二元组。单模式直接给 payload，多模式给 `(mode, payload)`——
这个不一致是新手最常见的 `ValueError: too many values to unpack` 来源。""",
                "syntax": """**四种模式的调用形态**

```python
for chunk in graph.stream(inp, stream_mode="values"):     # 完整状态
    ...
for chunk in graph.stream(inp, stream_mode="updates"):    # {节点名: 增量}
    ...
for msg, meta in graph.stream(inp, stream_mode="messages"):   # (消息, 元数据)
    ...
for payload in graph.stream(inp, stream_mode="custom"):   # writer 发的内容
    ...

for mode, chunk in graph.stream(inp, stream_mode=["updates", "custom"]):
    ...
```

- 单模式给 payload；多模式给 `(mode, payload)`。
- `messages` 模式永远给二元组，即使只订阅它一个。
- `custom` 需要节点里 `get_stream_writer()`；没有 writer 就没有事件。
- `debug` 给的是任务事件，含内部结构，别直接透给前端。""",
                "example_code": '''from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
    step: str


def first(state: State) -> dict:
    return {"messages": [AIMessage(content="第一步完成")], "step": "first"}


def second(state: State) -> dict:
    writer = get_stream_writer()
    writer({"progress": 50, "note": "正在处理第二步"})
    return {"messages": [AIMessage(content="第二步完成")], "step": "second"}


builder = StateGraph(State)
builder.add_node("first", first)
builder.add_node("second", second)
builder.add_edge(START, "first")
builder.add_edge("first", "second")
builder.add_edge("second", END)
graph = builder.compile()

inp = {"messages": [HumanMessage("开始")], "step": ""}

print("=== values ===")
for chunk in graph.stream(inp, stream_mode="values"):
    print(" ", {k: (len(v) if isinstance(v, list) else v) for k, v in chunk.items()})

print("=== updates ===")
for chunk in graph.stream(inp, stream_mode="updates"):
    print(" ", {k: list(v.keys()) for k, v in chunk.items()})

print("=== custom ===")
for chunk in graph.stream(inp, stream_mode="custom"):
    print(" ", chunk)

print("=== messages ===")
for chunk in graph.stream(inp, stream_mode="messages"):
    msg, meta = chunk
    print("  ", type(msg).__name__, repr(str(msg.content))[:30], "| 来自节点:", meta.get("langgraph_node"))

print("=== 多模式 ===")
for mode, chunk in graph.stream(inp, stream_mode=["updates", "custom"]):
    print(" ", mode, str(chunk)[:60])

print("=== debug ===")
for chunk in graph.stream(inp, stream_mode="debug"):
    print(" ", chunk["type"], chunk.get("step"))''',
                "code_lines": """1. 两个节点：`first` 什么都不发，`second` 用 writer 发一条自定义事件——正好对比 `custom` 有没有内容。
2. `values` 模式第一个 chunk 是初始输入（`messages` 1 条、`step` 为空），之后每步一条。
3. `values` 里 `messages` 从 1 到 2 到 3：因为 `add_messages` 在累积，`values` 给的是累积后的全量。
4. `updates` 只给这一步写了什么：键是节点名，值是那个节点返回的增量，没有全量状态。
5. `custom` 只有一个 chunk，就是 `second` 里 writer 发的那条；`first` 没写 writer，所以没贡献。
6. `messages` 模式每项是 `(消息, 元数据)`，元数据里的 `langgraph_node` 告诉你这条是哪个节点产的。
7. 多模式每项是 `(mode, payload)`，顺序按实际发生时间交错：先 updates(first)，再 custom，再 updates(second)。
8. `debug` 给的是 `task` / `task_result` 这类任务事件，粒度和前面几种完全不同。""",
                "output": """# 程序输出
=== values ===
  {'messages': 1, 'step': ''}
  {'messages': 2, 'step': 'first'}
  {'messages': 3, 'step': 'second'}
=== updates ===
  {'first': ['messages', 'step']}
  {'second': ['messages', 'step']}
=== custom ===
  {'progress': 50, 'note': '正在处理第二步'}
=== messages ===
   AIMessage '第一步完成' | 来自节点: first
   AIMessage '第二步完成' | 来自节点: second
=== 多模式 ===
  updates {'first': {'messages': [AIMessage(content='第一步完成', additiona
  custom {'progress': 50, 'note': '正在处理第二步'}
  updates {'second': {'messages': [AIMessage(content='第二步完成', addition
=== debug ===
  task 1
  task_result 1
  task 2
  task_result 2""",
                "mistakes": """- 多模式仍按「单模式」解包：`for chunk in graph.stream(..., stream_mode=[...])` 直接当下标用，报 `too many values to unpack`。
- 用 `values` 做打字机效果：每次拿到的是全量状态，前端得自己算哪部分是新的。
- 用 `custom` 却没在节点里调 writer：什么都不产出，也不报错。
- 把 `debug` 直接透给前端：里面是内部任务结构，既有噪音也泄露实现细节。
- 以为 `stream` 会返回最终结果：它是逐块产出，要汇总得自己拼。
- 在同步接口里 `stream` 完再一次性返回：等于没流式，还多占了内存。""",
                "error_analysis": """`ValueError: too many values to unpack (expected 2)`
—— 多模式返回的是 `(mode, chunk)`，但你按单模式写了 `for chunk in ...`。

流式没有输出
—— 检查是否真的调用了 `graph.stream`（而不是 `invoke`），以及 `custom` 模式下节点里有没有 writer。

`messages` 模式拿到的不是字符串
—— 它给的是消息对象（或消息块），要 `.content`。

进度条跳得乱七八糟
—— 混用了 `values` 与 `updates`。统一用 `updates`，并只在关键节点发 `custom`。""",
                "beginner_practice": """1. 把 `second` 里的 writer 注释掉，再跑 `custom` 模式，观察输出变成什么。
2. 把多模式的列表改成 `["values", "messages"]`，看 `chunk` 结构有什么不同。""",
                "advanced_practice": """设计一个前端进度协议：哪些事件必须发（开始、节点完成、进度百分比、错误、结束）、
每个事件带哪些字段、如何保证顺序可恢复。用 `updates + custom` 实现它。""",
                "quiz_note": "本节 6 道题：2 道基础理解（四种模式的差别、多模式的返回结构）+ 2 道代码阅读（为什么 `custom` 只有一条、`messages` 元数据里有什么）+ 2 道应用练习（选模式、设计进度协议）。",
                "summary": """`values` 全量、`updates` 增量、`messages` 消息块、`custom` 自定义事件。
多模式返回 `(mode, payload)`，单模式直接给 payload。
`custom` 的前提是节点里真的调了 writer。""",
                "next_lesson": "知道数据长什么样，下一节把它拼成 SSE 帧、让前端能直接消费。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-24-01",
                        "name": "stream_mode 各模式",
                        "goal": "能按界面需求选择流式模式，并正确解析返回结构。",
                        "minutes": 40,
                        "criteria": "能说出四种模式的差别，并解释 `custom` 为什么可能没有输出。",
                        "requires": ["langgraph-agent-23-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-24-01-1",
                        "kp": 0,
                        "title": "按界面选模式",
                        "description": "三个界面元素：① 顶部进度文字（检索中 / 生成中）；② 回答的打字机效果；③ 调试面板看每一步耗时。分别用哪种模式？",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": """① 进度文字：`custom` + `updates`。`custom` 发「检索中 20%」这类业务事件，
`updates` 提供「哪个节点刚跑完」这个事实。两者拼起来就是一条时间线。

② 打字机：`messages`。它给的是模型输出的增量块与元数据，前端按块追加即可，
不需要自己去 diff 全量状态。

③ 调试面板：`debug`。它给 `task` / `task_result` 事件，含内部结构，只给开发者看。

一次请求可以同时订阅多个模式，服务端按事件类型分别封装后推给前端——
前端不需要知道 LangGraph 的存在，只需要知道「收到 progress 就更新文字，收到 delta 就追加字符」。""",
                        "explanation": "选模式的依据是「界面上要显示什么」，不是「哪个模式信息多」。",
                    },
                    {
                        "code": "lg-ex-24-01-2",
                        "kp": 0,
                        "title": "custom 为什么空了",
                        "description": "某同学用 `stream_mode=\"custom\"` 什么都没收到，也没报错。列出三个可能原因。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''# 原因一：节点里根本没调 writer
from langgraph.config import get_stream_writer

def node(state):
    get_stream_writer()({"stage": "x"})   # 有这一行才有事件
    return {}

# 原因二：在节点之外调用了 get_stream_writer()
# 它只能在节点执行期间调用，模块级调用拿不到当前运行上下文

# 原因三：发事件的那个节点根本没被执行到
# 比如它在一条没走到的条件分支上''',
                        "explanation": "`custom` 是「主动发」的模式，没有发送方就没有内容。它不报错，所以只能靠排查代码确认。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-24-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "哪种模式给你的是「这一步哪个节点写了什么」？",
                        "options": [
                            ("A", "`values`"),
                            ("B", "`updates`"),
                            ("C", "`messages`"),
                            ("D", "`debug`"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`updates` 的 payload 形如 `{节点名: 增量}`；`values` 给的是累积后的完整状态。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-24-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "订阅多种模式时，每个 chunk 是一个 `(mode, payload)` 元组。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "单模式直接给 payload，多模式给二元组。这个不一致是解包报错的主要原因。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-24-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`custom` 模式只输出了一条，为什么不是两条？",
                        "options": [
                            ("A", "因为 `first` 节点没调用 writer"),
                            ("B", "因为 `custom` 只保留最后一条"),
                            ("C", "因为两个节点合并成一步"),
                            ("D", "因为 writer 不能在同一张图里用两次"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "只有 `second` 里调了 `get_stream_writer()`。`custom` 是主动发送，不发就没有。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-24-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`values` 模式里 `messages` 从 1 涨到 3，说明什么？",
                        "options": [
                            ("A", "每次 chunk 是累积后的全量状态，不是增量"),
                            ("B", "`add_messages` 每步加两条"),
                            ("C", "图被跑了三次"),
                            ("D", "状态被复制了两份"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`values` 给的是「此刻的状态全貌」。做打字机效果时用它，前端就得自己比对哪部分是新的——这正是 `messages` 存在的意义。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-24-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么不该把 `debug` 模式的输出直接透给前端？",
                        "options": [],
                        "answer": """两个理由。

① 语义不对：`debug` 是任务级事件（`task`、`task_result`），描述的是「调度器做了什么」，
不是「用户关心什么」。前端拿到还要自己翻译成业务语言。

② 成本与风险：payload 里有内部结构（节点名、状态片段、可能的异常栈），
体积大，且会把实现细节暴露给客户端。将来图一改，前端的解析就可能崩。

正确分层是：服务端订阅 `debug` 只用于日志与排查；给前端的是经过封装的事件
（progress / message / error / done），字段自己定义，与图的内部结构解耦。

一句话：给用户看「进展」，给开发者看「细节」，两者别混在一条通道里。""",
                        "explanation": "接口是契约。把内部结构直接当契约，等于把重构自由交出去。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-24-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一段代码：同时订阅 `updates` 与 `custom`，把节点名与进度分别打印出来。",
                        "options": [],
                        "answer": {
                            "value": "for mode, chunk in graph.stream(inp, stream_mode=[\"updates\", \"custom\"]):\n    if mode == \"updates\":\n        for node, update in chunk.items():\n            print(\"节点完成:\", node)\n    else:\n        print(\"进度:\", chunk.get(\"percent\"), chunk.get(\"stage\"))"
                        },
                        "explanation": "多模式必须先看 `mode` 再解析 payload——同一个循环里两种结构，不分支就会崩。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-24-lesson-02",
                "title": "自定义事件与前端透传",
                "objectives": """1. 能在节点里用 `get_stream_writer()` 发出业务进度事件；
2. 能把事件拼成合法的 SSE 帧（`event:` + `data:` + 空行）；
3. 能写一个客户端解析器，按空行切帧、按前缀取字段；
4. 能说明为什么事件字段要自己定义，而不是直接透出图的内部结构。""",
                "why_learn": """光有 `updates` 只能告诉前端「某节点跑完了」，说不出「正在检索第 2 条资料」。
自定义事件补上这块，SSE 负责把它送到浏览器。这两件事合起来，用户才看得到「它在干活」。""",
                "concepts": """**`get_stream_writer()`**：返回一个函数，调用它就把 payload 推给 `custom` 流。
**调用位置**：只能在节点执行期间调用；模块级调用拿不到当前上下文。
**SSE 帧格式**：`event: 名称` 一行、`data: 内容` 一行、再加一个空行。空行是分隔符，不能省。
**`data` 必须是字符串**：字典要先 `json.dumps`。
**多行 data**：可以写多行 `data:`，客户端按行拼接；实践中建议压成一行 JSON，少踩坑。
**字段命名**：自己定义 `progress / message / done / error`，别把节点名当接口。""",
                "plain": """SSE 的格式简单到容易被轻视：一行 `event:`、一行 `data:`、一个空行。

空行是帧之间的分隔符。少了它，客户端会把两条事件读成一条，症状是「数据粘在一起」或者
「只收到第一条」。加上它，浏览器那边 `EventSource` 才能一条条触发。

`data` 必须是字符串。传字典进去不会自动序列化，你会看到 `[object Object]` 或者干脆断流。

字段设计上，建议把「节点名」留在服务端。前端不需要知道你的图里有 `retrieve` 还是 `search`，
它只需要知道「progress 用于更新进度、message 用于追加文字、done 表示结束」。
这样以后你把图重构成子图，前端一行都不用改。

最后一个细节：结束事件一定要发。否则前端不知道是「还在跑」还是「已经挂了」，
只能靠超时——那体验比不流式还差。""",
                "syntax": """**帧格式与服务端**

```python
def to_sse(event: str, data: dict) -> str:
    return f"event: {event}\\ndata: {json.dumps(data, ensure_ascii=False)}\\n\\n"

def node(state):
    get_stream_writer()({"stage": "检索中", "percent": 20})
    ...
```

**客户端解析**

```python
for block in buffer.split("\\n\\n"):
    if not block.strip():
        continue
    event = data = ""
    for line in block.splitlines():
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: "):
            data = line[6:]
```

- `\\n\\n` 是帧分隔，缺一个 `\\n` 就会粘连。
- `data` 必须是字符串；中文用 `ensure_ascii=False` 可读性更好。
- 结束事件（`done`）与错误事件（`error`）要显式发，别指望客户端猜。""",
                "example_code": '''import json
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]


def retrieve(state: State) -> dict:
    writer = get_stream_writer()
    writer({"stage": "检索中", "percent": 20})
    writer({"stage": "检索完成", "percent": 60, "hit": 3})
    return {"messages": [AIMessage(content="找到 3 条资料")]}


def answer(state: State) -> dict:
    get_stream_writer()({"stage": "生成回答", "percent": 90})
    return {"messages": [AIMessage(content="State 在第 6 章。")]}


builder = StateGraph(State)
builder.add_node("retrieve", retrieve)
builder.add_node("answer", answer)
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "answer")
builder.add_edge("answer", END)
graph = builder.compile()


def to_sse(event: str, data: dict) -> str:
    """把一条事件拼成 SSE 帧：event 行 + data 行 + 空行。"""
    return f"event: {event}\\ndata: {json.dumps(data, ensure_ascii=False)}\\n\\n"


print("=== 服务端拼出来的帧 ===")
frames = []
for mode, chunk in graph.stream(
    {"messages": [HumanMessage("State 在哪一章")]},
    stream_mode=["custom", "updates"],
):
    if mode == "custom":
        frames.append(to_sse("progress", chunk))
    else:
        for node, update in chunk.items():
            frames.append(to_sse("message", {"node": node, "text": update["messages"][-1].content}))

for frame in frames:
    print(repr(frame))

print()
print("=== 客户端怎么解 ===")
buffer = "".join(frames)
for block in buffer.split("\\n\\n"):
    if not block.strip():
        continue
    event, data = "", ""
    for line in block.splitlines():
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: "):
            data = line[6:]
    print(f"[{event}] {data}")''',
                "code_lines": """1. `retrieve` 连发两条自定义事件：一条表示开始、一条表示完成并带上命中数量。
2. `answer` 在生成前发一条 90% 的进度——进度值由业务决定，框架不关心。
3. `to_sse` 只有一行，但三个细节都不能少：`event:` 前缀、`data:` 前缀、结尾两个换行。
4. 订阅顺序写的是 `["custom", "updates"]`，实际输出顺序按事件发生时间交错，不受列表顺序影响。
5. `repr(frame)` 让换行显示成 `\\n`，你能清楚看到帧与帧之间是两个换行。
6. 客户端按 `\\n\\n` 切块，跳过空块，再逐行读前缀——这就是一个最小 SSE 解析器。
7. 解析结果里 `progress` 与 `message` 交替出现，说明它们真的按发生顺序排好了。
8. 注意 `data` 里是压缩成一行的 JSON，没有内嵌换行——否则切帧会切错。""",
                "output": """# 程序输出
=== 服务端拼出来的帧 ===
'event: progress\\ndata: {"stage": "检索中", "percent": 20}\\n\\n'
'event: progress\\ndata: {"stage": "检索完成", "percent": 60, "hit": 3}\\n\\n'
'event: message\\ndata: {"node": "retrieve", "text": "找到 3 条资料"}\\n\\n'
'event: progress\\ndata: {"stage": "生成回答", "percent": 90}\\n\\n'
'event: message\\ndata: {"node": "answer", "text": "State 在第 6 章。"}\\n\\n'

=== 客户端怎么解 ===
[progress] {"stage": "检索中", "percent": 20}
[progress] {"stage": "检索完成", "percent": 60, "hit": 3}
[message] {"node": "retrieve", "text": "找到 3 条资料"}
[progress] {"stage": "生成回答", "percent": 90}
[message] {"node": "answer", "text": "State 在第 6 章。"}""",
                "mistakes": """- 帧结尾只写一个 `\\n`：两条事件粘成一条，客户端解析出乱码。
- `data` 直接塞字典：不是字符串，序列化失败或输出 `[object Object]`。
- JSON 里有真实换行（没压缩）：切帧时被当成帧分隔符，事件被劈成两半。
- 事件名直接用节点名：图一重构前端就崩，且暴露内部结构。
- 不发结束事件：前端只能靠超时判断结束。
- 在模块级调 `get_stream_writer()`：拿不到运行上下文，报错或什么都不发。
- 出错时直接抛出：流已经开始了，必须发一个 `error` 事件再结束，否则前端只能看到断连。""",
                "error_analysis": """客户端只收到第一条事件
—— 帧分隔不对。检查结尾是不是 `\\n\\n`。

`json.decoder.JSONDecodeError`
—— `data` 被截断了，通常是 JSON 里带真实换行。

前端 EventSource 不触发
—— 响应头不是 `text/event-stream`，或者代理做了缓冲。

`RuntimeError: no active stream writer`
—— 在节点之外调用 writer。它只在节点执行期间有效。

流式接口返回 500，日志里是图内部异常
—— 流已经开始就不能改状态码了，应在生成器里捕获异常并 yield 一个 `error` 帧。""",
                "beginner_practice": """1. 把 `to_sse` 结尾的 `\\n\\n` 改成 `\\n`，再看客户端解析的结果。
2. 加一个 `done` 事件（`data: {"ok": true}`），并在客户端打印它。""",
                "advanced_practice": """设计断线重连方案：客户端拿到 `Last-Event-ID` 后，服务端怎么知道从哪继续？
结合检查点（第 20 章）说明可行的做法，以及哪些事件无法重放。""",
                "quiz_note": "本节 6 道题：2 道基础理解（SSE 帧的分隔符、`data` 的类型要求）+ 2 道代码阅读（为什么用 `repr` 打印、事件顺序由什么决定）+ 2 道应用练习（补 done/error 事件、断线重连）。",
                "summary": """节点里 `get_stream_writer()` 发事件，服务端拼成 `event + data + 空行` 的帧。
`data` 必须是字符串，JSON 要压成一行。
事件字段自己定义，别把节点名当接口。""",
                "next_lesson": "流式解决了「看得见」，下一章解决「失败了怎么办」——重试与异常分类。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-24-02",
                        "name": "自定义事件与前端透传",
                        "goal": "能发出业务事件并拼成前端可消费的 SSE 帧。",
                        "minutes": 45,
                        "criteria": "能写对帧格式与解析器，并说明字段设计为什么要与图结构解耦。",
                        "requires": ["langgraph-agent-24-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-24-02-1",
                        "kp": 0,
                        "title": "补两个事件",
                        "description": "现有实现只有 progress 与 message。补上 error 与 done，并说明它们必须满足什么条件。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def events():
    try:
        for mode, chunk in graph.stream(inp, stream_mode=["custom", "updates"]):
            ...
            yield frame
    except Exception as exc:
        yield to_sse("error", {"message": str(exc)[:200]})
    finally:
        yield to_sse("done", {"ok": True})''',
                        "explanation": "关键在 `try/except/finally`：流一旦开始，状态码已经发出去了，只能靠事件告诉前端「出错了」或「结束了」。",
                    },
                    {
                        "code": "lg-ex-24-02-2",
                        "kp": 0,
                        "title": "事件字段怎么定",
                        "description": "为什么建议事件里不要直接暴露节点名？如果一定要带，怎么带比较好？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """直接暴露节点名有两个问题。

① 耦合：前端会开始写 `if (node === "retrieve")`。你把 `retrieve` 拆成子图或改名，前端立刻坏。
这是典型的「内部实现泄漏成外部契约」。

② 语义缺失：节点名是给开发者看的，不是给用户看的。用户看到「retrieve 完成」毫无意义。

更好的做法是定义业务事件：`progress{stage: "检索中", percent: 20}`、
`message{text: ...}`、`done{ok: true}`。前端只认这几种，不关心背后是哪个节点。

如果确实需要定位（比如调试模式），可以带一个 `trace` 字段，
但它应该被标记为「可选、非稳定」，前端不得依赖它做逻辑。

一句话：契约由你定义，节点名只是实现细节。""",
                        "explanation": "接口稳定性的关键，是别把「今天恰好这样实现」写进对外协议。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-24-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "SSE 帧之间靠什么分隔？",
                        "options": [
                            ("A", "一个空行（两个换行）"),
                            ("B", "分号"),
                            ("C", "长度前缀"),
                            ("D", "`---` 三个短横线"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`event:` 行 + `data:` 行 + 空行。少一个换行就会粘连，这是最常见的 SSE bug。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-24-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`data:` 后面可以直接放一个 Python 字典，框架会自动序列化。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "SSE 是文本协议，`data` 必须是字符串。字典要自己 `json.dumps`，否则序列化失败或输出无意义内容。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-24-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例里为什么用 `print(repr(frame))` 而不是 `print(frame)`？",
                        "options": [
                            ("A", "因为 `repr` 更快"),
                            ("B", "因为 `repr` 会把换行显示成 `\\n`，能看清帧的分隔结构"),
                            ("C", "因为 `print` 不支持字符串"),
                            ("D", "因为 `repr` 会自动转 JSON"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "直接打印会真的换行，五条帧糊成一片；`repr` 让不可见字符显形，调试 SSE 时非常有用。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-24-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "输出顺序是「progress, progress, message, progress, message」，与订阅列表 `[\"custom\", \"updates\"]` 的顺序不一致。为什么？",
                        "options": [
                            ("A", "列表顺序只影响解析方式，不影响发射顺序"),
                            ("B", "因为 `custom` 优先级更高"),
                            ("C", "因为 `updates` 被延迟到最后统一发"),
                            ("D", "因为字典无序"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "多模式是按事件真实发生时间交错产出的，列表只是「订阅哪些」。想控制顺序要靠业务侧的设计，不能靠列表顺序。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-24-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "流式接口里出错该怎么处理？为什么不能直接抛异常？",
                        "options": [],
                        "answer": """不能直接抛，因为响应头和部分内容已经发出去了，状态码改不了。

正确做法是在生成器里包 `try/except`：捕获后 `yield` 一个 `error` 事件，再 `yield` 一个 `done`，
让客户端知道「这次结束了，而且是失败结束」。

典型帧：

`event: error` + `data: {"message": "检索服务超时"}`

几个要点：

① 错误信息要脱敏，不要把内部栈直接给前端。

② 一定要发 `done`（或用 `finally` 保证发），否则前端以为还在跑。

③ 服务端日志里记完整异常，前端只拿摘要——两边信息量不同。

④ 如果错误发生在第一个事件之前，可以直接返回 5xx；一旦开始流式，就只能用事件表达。""",
                        "explanation": "流式接口的错误处理是「协议内的事」，不是「HTTP 层的事」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-24-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个 `to_sse` 函数，把事件名与字典拼成合法帧（中文不转义）。",
                        "options": [],
                        "answer": {
                            "value": "def to_sse(event: str, data: dict) -> str:\n    return f\"event: {event}\\ndata: {json.dumps(data, ensure_ascii=False)}\\n\\n\""
                        },
                        "explanation": "三个细节：`event:` 前缀、`data:` 前缀、结尾 `\\n\\n`。`ensure_ascii=False` 让中文直接可读，也省带宽。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 25 章
    {
        "code": "langgraph-agent-25",
        "order_index": 25,
        "title": "错误处理与重试",
        "description": "哪些异常会重试、哪些不会，必须显式声明。",
        "lessons": [
            {
                "code": "langgraph-agent-25-lesson-01",
                "title": "RetryPolicy 与异常分类",
                "objectives": """1. 能说清「不传 `retry_policy`」和「传 `RetryPolicy()`」的区别；
2. 能说出默认策略重试哪些异常、不重试哪些；
3. 能用 `retry_on` 显式指定要重试的异常类型；
4. 能按「可重试 / 可自纠 / 只能报障」给异常分类。""",
                "why_learn": """网络抖一下重试就好，业务参数错了重试一万次也没用，还可能重复扣款。
重试策略写错，轻则浪费额度，重则造成资损——这是必须显式表态的地方。""",
                "concepts": """**默认不重试**：`add_node` 的 `retry_policy` 默认是 `None`，一个异常就结束。
**`RetryPolicy()`**：默认 `max_attempts=3`、指数退避、带抖动，`retry_on=default_retry_on`。
**`default_retry_on` 认哪些**：`ConnectionError`、`httpx.ConnectError`、HTTP 5xx 等「连接类」异常；不认 `RuntimeError`、`ValueError`、`OSError`，也不认 HTTP 429。
**`retry_on`**：传异常类型或元组，可覆盖默认判断；传入后默认规则不再生效。
**子类算命中**：`retry_on=RuntimeError` 也会重试它的子类。
**用尽后**：把最后一次异常原样抛出，不是包装成新异常。""",
                "plain": """重试的前提是「这个错误再试一次可能就好了」。判断不了这一点，就不该重试。

框架的判断是保守的：只有连接类异常（连不上、5xx）才值得再试；
`RuntimeError`、`ValueError` 这类一看就是代码或参数问题，重试只是重复犯错。

要注意两个容易误解的地方。

第一，`retry_policy` 默认是 `None`——不传就完全不重试。这一点和很多人的直觉相反：
以为「框架总会重试几次」。示例第 1 段就是证据：一个 `ConnectionError`，调用 1 次就抛了。

第二，`RetryPolicy()` 的默认规则不认 HTTP 429（限流）。限流恰恰是最该退避重试的场景，
所以线上通常要自己写 `retry_on`，把 429 和业务上的临时性异常加进去。

最后一条纪律：**重试的节点必须幂等**。发消息、扣款这类操作，重试前要先确认「上次到底做成了没有」。""",
                "syntax": """**三种写法**

```python
from langgraph.types import RetryPolicy

builder.add_node("a", a)                                        # 不重试
builder.add_node("b", b, retry_policy=RetryPolicy())            # 默认策略
builder.add_node("c", c, retry_policy=RetryPolicy(
    max_attempts=4, retry_on=(ConnectionError, TimeoutError),
))

# 多个策略按顺序匹配（1.x 支持传序列）
builder.add_node("d", d, retry_policy=[RetryPolicy(retry_on=ValueError), RetryPolicy()])
```

- `max_attempts` 含首次尝试：`3` 表示最多执行 3 次。
- `initial_interval` / `backoff_factor` / `max_interval` / `jitter` 控制退避节奏。
- 节点还能设 `timeout=`，超时抛出的异常同样走重试判断。
- 重试发生在节点级别，不是整张图级别——不要指望「重跑整个流程」。""",
                "example_code": '''from typing import TypedDict

import httpx
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, default_retry_on


class S(TypedDict):
    log: str


calls = {"n": 0}


class Boom(RuntimeError):
    """自定义业务异常，继承自 RuntimeError。"""


def build(node_fn, **kwargs):
    builder = StateGraph(S)
    builder.add_node("work", node_fn, **kwargs)
    builder.add_edge(START, "work")
    builder.add_edge("work", END)
    return builder.compile()


def run(label, fn, **kwargs):
    calls["n"] = 0
    graph = build(fn, **kwargs)
    try:
        out = graph.invoke({"log": ""})
        print(f"{label}: 成功 | {out['log']} | 调用 {calls['n']} 次")
    except Exception as exc:
        print(f"{label}: 抛出 {type(exc).__name__} | 调用 {calls['n']} 次")


def flaky_conn(state: S) -> dict:
    calls["n"] += 1
    if calls["n"] < 3:
        raise ConnectionError("连接抖了一下")
    return {"log": f"第 {calls['n']} 次成功"}


def always_runtime(state: S) -> dict:
    calls["n"] += 1
    raise RuntimeError("业务失败")


def always_boom(state: S) -> dict:
    calls["n"] += 1
    raise Boom("数据源挂了")


def flaky_boom(state: S) -> dict:
    calls["n"] += 1
    if calls["n"] < 3:
        raise Boom("前两次不行")
    return {"log": f"第 {calls['n']} 次成功"}


print("=== 1. 不传 retry_policy ===")
run("ConnectionError", flaky_conn)

print()
print("=== 2. RetryPolicy() 默认策略 + ConnectionError ===")
run("ConnectionError", flaky_conn, retry_policy=RetryPolicy())

print()
print("=== 3. RetryPolicy() 默认策略 + RuntimeError ===")
run("RuntimeError", always_runtime, retry_policy=RetryPolicy())

print()
print("=== 4. retry_on=RuntimeError（实际抛的是子类 Boom）===")
run("Boom", always_boom, retry_policy=RetryPolicy(max_attempts=3, retry_on=RuntimeError))

print()
print("=== 5. retry_on=Boom，第三次成功 ===")
run("Boom", flaky_boom, retry_policy=RetryPolicy(max_attempts=4, retry_on=Boom))

print()
print("=== 6. 默认策略认定哪些异常该重试 ===")
cases = [
    ("ConnectionError", ConnectionError("x")),
    ("RuntimeError", RuntimeError("x")),
    ("ValueError", ValueError("x")),
    ("OSError", OSError("x")),
    ("httpx.ConnectError", httpx.ConnectError("x")),
    ("HTTP 500", httpx.HTTPStatusError("500", request=httpx.Request("GET", "http://x"), response=httpx.Response(500))),
    ("HTTP 429", httpx.HTTPStatusError("429", request=httpx.Request("GET", "http://x"), response=httpx.Response(429))),
]
for name, exc in cases:
    print(f"  {name:20s} -> {default_retry_on(exc)}")''',
                "code_lines": """1. `calls` 记录节点被执行了几次——判断「有没有重试」靠计数，不靠猜。
2. `build` 把节点、边、编译封装起来，每次用不同的 `retry_policy` 重跑同一段逻辑。
3. 第 1 段：不传 `retry_policy`，`ConnectionError` 只执行 1 次就抛出——默认不重试。
4. 第 2 段：`RetryPolicy()` 的默认规则认得 `ConnectionError`，三次后成功。
5. 第 3 段：同一个默认策略不认 `RuntimeError`，仍然只执行 1 次。
6. 第 4 段：`retry_on=RuntimeError` 命中，执行 3 次；用尽后抛出的是最后一次的 `Boom`，不是 `RuntimeError`。
7. 第 5 段：`retry_on=Boom` 且第三次成功，说明重试确实是「重新执行节点」。
8. 第 6 段是本节的重点：默认规则认连接类与 5xx，不认 `RuntimeError`/`ValueError`/`OSError`，也**不认 429**。""",
                "output": """# 程序输出
=== 1. 不传 retry_policy ===
ConnectionError: 抛出 ConnectionError | 调用 1 次

=== 2. RetryPolicy() 默认策略 + ConnectionError ===
ConnectionError: 成功 | 第 3 次成功 | 调用 3 次

=== 3. RetryPolicy() 默认策略 + RuntimeError ===
RuntimeError: 抛出 RuntimeError | 调用 1 次

=== 4. retry_on=RuntimeError（实际抛的是子类 Boom）===
Boom: 抛出 Boom | 调用 3 次

=== 5. retry_on=Boom，第三次成功 ===
Boom: 成功 | 第 3 次成功 | 调用 3 次

=== 6. 默认策略认定哪些异常该重试 ===
  ConnectionError      -> True
  RuntimeError         -> False
  ValueError           -> False
  OSError              -> False
  httpx.ConnectError   -> True
  HTTP 500             -> True
  HTTP 429             -> False""",
                "mistakes": """- 以为不配置也会重试：默认 `retry_policy=None`，一个异常就结束。
- 用 `RetryPolicy()` 就以为万事大吉：它不认业务异常，也不认 429。
- `retry_on` 里塞了 `Exception`：等于所有异常都重试，包括参数错误，白烧额度。
- 重试非幂等节点：发消息、扣款被执行多次，造成重复副作用。
- `max_attempts` 设成 10 以上：出问题时用户等几十秒，还不如快速失败。
- 重试与工具层的 `handle_tool_errors` 打架：一个吞掉异常，一个永远等不到异常。""",
                "error_analysis": """只执行 1 次就失败
—— 没传 `retry_policy`，或异常类型不在 `retry_on` 里。

重试了但每次都失败
—— 异常不是「临时性」的。先看日志确认原因，别加 `max_attempts` 硬顶。

`RetryError` 之类的包装异常
—— 本版本是把最后一次异常原样抛出；若你看到包装异常，说明中间还有一层重试库。

重试后出现重复数据
—— 节点不幂等。加去重键，或改成「先查后做」。

等待时间太长
—— 指数退避叠加了大 `initial_interval`。调小 `max_interval` 或减少 `max_attempts`。""",
                "beginner_practice": """1. 把第 2 段的 `max_attempts` 改成 2，观察 `flaky_conn` 的结果（需要三次才成功）。
2. 给第 3 段加 `retry_on=RuntimeError`，确认它开始重试。""",
                "advanced_practice": """设计一套异常分类规范：把项目里可能出现的异常分成「可重试」「可自纠」「必须报障」三类，
分别给出处理方式（重试 / 变成 ToolMessage / 直接抛出），并说明为什么超时属于第一类。""",
                "quiz_note": "本节 6 道题：2 道基础理解（不配置时会不会重试、默认策略认哪些异常）+ 2 道代码阅读（第 4 段为什么抛的是 `Boom`、计数为什么是 3）+ 2 道应用练习（写 `retry_on`、异常分类）。",
                "summary": """默认不重试；`RetryPolicy()` 才启用，且只认连接类与 5xx。
业务异常要显式 `retry_on`，否则一次就结束。
重试的节点必须幂等，`max_attempts` 别贪大。""",
                "next_lesson": "图能流式、能重试了。下一章把它包装成 HTTP 接口，让前端真的能用上。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-25-01",
                        "name": "重试策略与异常分类",
                        "goal": "能按异常类型配置重试，并避免非幂等重试。",
                        "minutes": 40,
                        "criteria": "能说出默认策略的边界，并写出带 `retry_on` 的配置。",
                        "requires": ["langgraph-agent-24-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-25-01-1",
                        "kp": 0,
                        "title": "把 429 加进重试",
                        "description": "默认策略不重试 HTTP 429。写出一个把 429 与连接错误都纳入重试的策略。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''import httpx
from langgraph.types import RetryPolicy


def retry_on_ratelimit(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, (ConnectionError, TimeoutError))


policy = RetryPolicy(max_attempts=4, retry_on=retry_on_ratelimit)
builder.add_node("call_model", call_model, retry_policy=policy)''',
                        "explanation": "`retry_on` 可以传函数，判断逻辑自己写。注意 429 要配合退避（`initial_interval` 别太小），否则重试只会更快地撞上限流。",
                    },
                    {
                        "code": "lg-ex-25-01-2",
                        "kp": 0,
                        "title": "重试与幂等",
                        "description": "一个节点负责「给用户发一条通知」。加上重试后可能出现什么问题？怎么解决？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """问题：重试会导致重复发送。用户收到两条一样的通知，轻则不专业，重则被投诉。

三种解法，按可靠性排序：

① 幂等键：每次发送带一个业务唯一键（订单号 + 事件类型）。发送方或接收方按该键去重，
重复请求直接返回成功。这是最可靠的做法。

② 先记录后发送：发送前在库里写一条「已发送」标记（带唯一约束），发送失败再回滚。
关键是唯一约束在数据库层，不是内存里的标志位。

③ 把副作用移出重试范围：节点只负责「准备内容」，真正的发送交给一个不带重试的下游步骤，
或在重试成功后再触发。

不能用的做法：在节点里用内存变量记「发过了」。进程重启、多副本部署时这个标志根本不存在。

原则：**能被重试的节点，必须能被重复执行而结果不变**。做不到，就别给它配重试。""",
                        "explanation": "重试是「可能执行多次」的显式声明；节点是否支持多次执行，是设计时要回答的问题。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-25-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`add_node` 不传 `retry_policy` 时，节点抛异常会怎样？",
                        "options": [
                            ("A", "按默认策略重试 3 次"),
                            ("B", "不重试，异常直接向上抛"),
                            ("C", "静默失败，返回空状态"),
                            ("D", "跳过该节点继续执行"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "默认是 `None`，也就是不重试。示例第 1 段：`ConnectionError` 只调用 1 次就抛出。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-25-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`RetryPolicy()` 的默认规则会重试 HTTP 429（限流）。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "示例第 6 段实测为 `False`。限流要自己写进 `retry_on`，并配上足够长的退避。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-25-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第 4 段配置 `retry_on=RuntimeError`，最终抛出的异常类型是什么？为什么？",
                        "options": [
                            ("A", "`RuntimeError`，因为配置里写的是它"),
                            ("B", "`Boom`，因为抛出的是最后一次的原始异常"),
                            ("C", "`RetryError`，重试耗尽后统一包装"),
                            ("D", "`ConnectionError`"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`retry_on` 只决定「要不要重试」，不改变异常本身。用尽后把最后一次异常原样抛出，`Boom` 是 `RuntimeError` 的子类所以命中了规则。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-25-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第 5 段 `max_attempts=4`，实际调用 3 次就成功了。说明什么？",
                        "options": [
                            ("A", "`max_attempts` 是上限，成功即停止"),
                            ("B", "`max_attempts` 少算了 1"),
                            ("C", "框架忽略了配置"),
                            ("D", "第三次之后还有一次重试"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`max_attempts` 是「最多尝试几次」，不是「必须试几次」。第三次成功就不会有第四次。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-25-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么 `RuntimeError`、`ValueError` 默认不重试，而 `ConnectionError` 默认重试？",
                        "options": [],
                        "answer": """因为前者「再试也不会变」，后者「再试可能就通了」。

`ConnectionError`、`httpx.ConnectError`、HTTP 5xx 属于**临时性故障**：
网络抖动、对端重启、上游瞬时过载，几秒后重试往往就成功，重试的期望收益很高。

`ValueError`、`RuntimeError`、`OSError` 属于**确定性故障**：参数错了、代码有 bug、路径不存在。
同样的输入再跑一万次结果一样，重试只会浪费额度、拖长用户等待，还掩盖了真正的问题。

这个划分体现了一个工程判断：**默认行为应该朝「不制造新问题」倾斜**。
误重试一个确定性错误，可能造成重复副作用；而少重试一次临时故障，用户再点一下就好了。

HTTP 429 不在默认名单里则是个保守之处：限流需要更长的退避和配额感知，交给业务自己决定更合适。""",
                        "explanation": "默认值的背后是「错误分类学」：临时故障重试，确定性故障暴露。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-25-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给一个调用外部接口的节点配置重试：最多 4 次，重试连接错误与超时。",
                        "options": [],
                        "answer": {
                            "value": "from langgraph.types import RetryPolicy\n\npolicy = RetryPolicy(\n    max_attempts=4,\n    initial_interval=0.5,\n    backoff_factor=2.0,\n    max_interval=8.0,\n    retry_on=(ConnectionError, TimeoutError),\n)\n\nbuilder.add_node(\"call_api\", call_api, retry_policy=policy, timeout=15)"
                        },
                        "explanation": "`timeout` 放在节点上比放请求里更可靠：它约束的是整个节点执行时间，超时抛出后同样进入重试判断。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
