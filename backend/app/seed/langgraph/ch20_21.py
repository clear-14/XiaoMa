"""LangGraph Agent 开发：第 20—21 章。

第 20 章解决「进程还在，会话能不能接上」：`thread_id` 决定读哪条线，检查点决定能回到哪一步；
第 21 章解决「换一条会话还认不认得这个人」：跨线程的长期数据放 Store，不放状态里。

版本口径（实测）：langgraph 1.2.20、langgraph-checkpoint 4.3.1、langchain-core 1.7.6。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 20 章
    {
        "code": "langgraph-agent-20",
        "order_index": 20,
        "title": "Checkpointer",
        "description": "把每一步的状态存下来，让会话能接上、让流程能回到过去。",
        "lessons": [
            {
                "code": "langgraph-agent-20-lesson-01",
                "title": "线程与检查点",
                "objectives": """1. 能配置 `thread_id`，说清它决定「这通调用读到哪条会话」；
2. 能说出一个检查点里存了什么：`values`、`next`、`metadata`、`config`、`parent_config`；
3. 能解释 `InMemorySaver` 的生命周期，以及生产环境为什么要换后端；
4. 能说明没有 checkpointer 时哪些操作会失败、哪些照常运行。""",
                "why_learn": """没有检查点，每次 `invoke` 都是一次性脚本：进程一重启，对话清零，出错了也没法回到上一步。
检查点是后面「人工介入」「时间旅行」「流式进度」的前置条件——它不装，后面全都做不了。""",
                "concepts": """**Checkpointer**：图每跑完一步，就把当前状态存一份快照。
**`thread_id`**：会话标识。同一个 `thread_id` 的多次调用接在同一份历史上；不同 `thread_id` 互不可见。
**`StateSnapshot`**：`get_state` 的返回值，含 `values`（状态本身）、`next`（下一步执行谁）、`metadata`（来源与步数）、`config`（带检查点 ID 的配置）、`parent_config`（上一个检查点）。
**`next` 为空元组**：说明这条线已经跑完，没有待执行节点。
**`InMemorySaver`**：存在进程内存里，进程退出即丢。生产要换持久化后端（本机未装 `langgraph-checkpoint-sqlite`）。
**没有 checkpointer**：`invoke` 照常跑，但 `get_state` 直接 `ValueError: No checkpointer set`。""",
                "plain": """检查点像游戏存档：每过一关自动存一次，下次从最近那一关继续，而不是从第一关重打。

`thread_id` 是存档位的编号。同一编号读同一份进度，不同编号各玩各的——
这也是为什么同一个 Agent 服务多个人时，必须给每个人分配不同的 `thread_id`。

有个细节新手常踩：`thread_id` 必须写在 `config` 的 `configurable` 里面。
写成顶层键不会报错，只是每次调用都被当成新会话——症状是「明明传了 id，怎么还是不记得」。

另一个细节：`InMemorySaver` 只活在当前进程。重启一次全部清空，多进程部署时各进程还互相看不见。
它适合开发和测试；上线要换成数据库或 Redis 之类的持久化实现。""",
                "syntax": """**装配与读取**

```python
from langgraph.checkpoint.memory import InMemorySaver

graph = builder.compile(checkpointer=InMemorySaver())

cfg = {"configurable": {"thread_id": "t1"}}      # 注意层级
graph.invoke({"messages": [HumanMessage("你好")]}, cfg)

snap = graph.get_state(cfg)
snap.values          # 当前状态
snap.next            # 下一个要执行的节点，() 表示跑完了
snap.metadata        # {"source": "loop", "step": 1, "parents": {}}
snap.config          # 带 checkpoint_id，可用于回放
snap.parent_config   # 上一个检查点的配置
```

- 同一个 `InMemorySaver` 实例才共享存档；重新 `compile` 新建一个，等于换了存档目录。
- 输入里带的字段会覆盖已有值；想让它累积，就别在输入里重复写那些键。
- `checkpoint_id` 是回放与分支的抓手，第 20-2 节会用到。""",
                "example_code": '''from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
    turns: int


def reply(state: State) -> dict:
    n = state.get("turns", 0) + 1
    return {"messages": [AIMessage(content=f"第 {n} 轮回复")], "turns": n}


builder = StateGraph(State)
builder.add_node("reply", reply)
builder.add_edge(START, "reply")
builder.add_edge("reply", END)

saver = InMemorySaver()
graph = builder.compile(checkpointer=saver)

cfg = {"configurable": {"thread_id": "t1"}}
out1 = graph.invoke({"messages": [HumanMessage("你好")]}, cfg)
print("第 1 轮 turns:", out1["turns"], "消息数:", len(out1["messages"]))

snap = graph.get_state(cfg)
print("snapshot 类型:", type(snap).__name__)
print("values:", {k: (len(v) if isinstance(v, list) else v) for k, v in snap.values.items()})
print("next:", snap.next)
print("metadata:", snap.metadata)
print("parent_config:", snap.parent_config)
print("config:", snap.config)

out2 = graph.invoke({"messages": [HumanMessage("再来")]}, cfg)
print("第 2 轮 turns:", out2["turns"], "消息数:", len(out2["messages"]))

cfg2 = {"configurable": {"thread_id": "t2"}}
out3 = graph.invoke({"messages": [HumanMessage("另一条线")]}, cfg2)
print("t2 turns:", out3["turns"], "消息数:", len(out3["messages"]))

print()
print("=== 不带 checkpointer ===")
plain = builder.compile()
print("invoke 结果 turns:", plain.invoke({"messages": [HumanMessage("x")]})["turns"])
try:
    print("get_state:", plain.get_state(cfg))
except Exception as exc:
    print(type(exc).__name__, ":", str(exc)[:80])

print()
print("=== 没有该线程时 get_state ===")
snap_none = graph.get_state({"configurable": {"thread_id": "nope"}})
print("values:", snap_none.values, "| next:", snap_none.next)''',
                "code_lines": """1. `reply` 从状态里读 `turns` 再 +1，所以它能感知「这是第几轮」——前提是有检查点。
2. `compile(checkpointer=saver)` 是唯一开关：不传就没有存档。
3. 第一次调用的 `messages` 只有一条用户消息，节点追加回复后变两条。
4. `get_state` 返回 `StateSnapshot`：`values` 是状态，`next` 是待执行节点，`metadata` 里有 `step` 与 `source`。
5. `next: ()` 说明这条线跑完了；如果停在中间，这里会写着下一个节点的名字。
6. `parent_config` 指向上一个检查点，`config` 指向当前检查点——两者都带 `checkpoint_id`。
7. 第二次调用只传 `messages`，没传 `turns`，于是 `turns` 从存档里读出来是 1，加完变 2，消息累积到 4 条。
8. `t2` 是另一条线程，`turns` 重新从 0 开始——线程之间完全隔离。
9. 不带 checkpointer 时 `invoke` 正常返回 1，但 `get_state` 立刻 `ValueError: No checkpointer set`。
10. 查一个不存在的线程不会报错，返回 `values: {}`、`next: ()`——所以「空」不等于「报错」，判断要小心。""",
                "output": """# 程序输出
第 1 轮 turns: 1 消息数: 2
snapshot 类型: StateSnapshot
values: {'messages': 2, 'turns': 1}
next: ()
metadata: {'source': 'loop', 'step': 1, 'parents': {}}
parent_config: {'configurable': {'thread_id': 't1', 'checkpoint_ns': '', 'checkpoint_id': '1f1db665-438c-6da1-8000-9a47a76085e3'}}
config: {'configurable': {'thread_id': 't1', 'checkpoint_ns': '', 'checkpoint_id': '1f1db665-4390-6913-8001-feb9d9c96523'}}
第 2 轮 turns: 2 消息数: 4
t2 turns: 1 消息数: 2

=== 不带 checkpointer ===
invoke 结果 turns: 1
ValueError : No checkpointer set

=== 没有该线程时 get_state ===
values: {} | next: ()""",
                "mistakes": """- 把 `thread_id` 写成 `{"thread_id": "t1"}`（少了 `configurable` 一层）：不报错，但每次都是新会话。
- 每次请求都生成新的 `thread_id`（比如用 uuid）：等于没有记忆，用户会觉得「它怎么又忘了」。
- 以为 `InMemorySaver` 能跨进程：重启即丢，多副本部署各存各的。
- 重新 `compile` 时又 `new` 了一个 saver：旧存档看不见了。
- 把 `parent_config` 当成「上一轮对话」：它是分支来源，不是时间顺序上的上一轮。
- 输入里每次都带 `turns: 0`：覆盖了存档里的值，看起来像「没有记忆」。
- 轮询 `get_state` 等结果：应该用流式（第 24 章）或回调，而不是死循环查询。""",
                "error_analysis": """`ValueError: No checkpointer set`
—— 编译时没传 `checkpointer`。想用 `get_state` / `get_state_history` / 中断恢复，都必须先装上。

状态「没有接上」
—— 先确认 `thread_id` 在 `configurable` 里，再确认两次调用用的是同一个 saver 实例。

重启后 history 空了
—— `InMemorySaver` 只活在进程内。换持久化后端才能跨重启。

`next` 一直不为空
—— 流程卡在某个节点（比如等中断）。这是「挂起」而不是「跑完」，第 22 章会讲怎么恢复。""",
                "beginner_practice": """1. 把第二次调用的输入改成 `{"messages": [...], "turns": 0}`，观察 `turns` 从几开始。
2. 打印 `snap.created_at`（示例没打，自己加一行），比较两次调用的时间。""",
                "advanced_practice": """设计一个「一个用户多条会话」的存储方案：会话列表怎么存、`thread_id` 怎么生成、怎么列出某个用户的所有会话。
说明哪些数据放状态、哪些必须放 Store（下一章）。""",
                "quiz_note": "本节 6 道题：2 道基础理解（`thread_id` 的作用、`next` 为空表示什么）+ 2 道代码阅读（为什么第二轮 `turns` 是 2、不带 checkpointer 时报什么）+ 2 道应用练习（修 `thread_id` 层级、设计多会话方案）。",
                "summary": """`thread_id` 决定读哪条线，检查点决定能回到哪一步。
`InMemorySaver` 只活进程内，生产要换持久化后端。
没有 checkpointer 时图和 `get_state` 的行为完全不同，别把两者混为一谈。""",
                "next_lesson": "存档有了，下一节学怎么读历史、改一个状态、从那里重新跑。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-20-01",
                        "name": "线程与检查点",
                        "goal": "能配置线程、读取状态快照，并解释各字段含义。",
                        "minutes": 40,
                        "criteria": "能说出 `StateSnapshot` 五个字段的用途，并解释线程隔离。",
                        "requires": ["langgraph-agent-19-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-20-01-1",
                        "kp": 0,
                        "title": "修好线程配置",
                        "description": "下面这段代码「传了 thread_id 却没有记忆」，找出问题并修正。\n\n```python\ncfg = {\"thread_id\": \"user-1\"}\ngraph.invoke({\"messages\": [HumanMessage(\"你好\")]}, cfg)\n```",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''cfg = {"configurable": {"thread_id": "user-1"}}
graph.invoke({"messages": [HumanMessage("你好")]}, cfg)''',
                        "explanation": "`thread_id` 必须嵌在 `configurable` 下。写在顶层不会报错，但线程不生效——这类「静默失效」最难查。",
                    },
                    {
                        "code": "lg-ex-20-01-2",
                        "kp": 0,
                        "title": "内存版能不能上线",
                        "description": "`InMemorySaver` 用在生产会出什么问题？给出替代方向。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """三个问题。

① 不持久：进程退出、容器重启、发版，全部会话丢失。

② 不共享：多副本部署时每个进程一份内存，用户在 A 副本说了话，下一次请求落到 B 副本就「失忆」。
负载均衡在这种场景下会放大问题。

③ 不可控：内存没有容量上限，长会话累积会把进程撑爆，也没有清理策略。

替代方向：换成基于数据库或 Redis 的检查点实现（LangGraph 提供对应包，需要单独安装）；
自建方案要保证「按 thread_id 顺序写入、支持按 checkpoint_id 读取」。

开发与测试继续用 `InMemorySaver` 没问题——它快、无依赖、进程内足够真实。""",
                        "explanation": "存储选型的判断标准：需不需要跨进程、跨重启、跨副本。三者有一个成立，就不能用内存版。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-20-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`thread_id` 决定什么？",
                        "options": [
                            ("A", "图的节点数量"),
                            ("B", "这次调用接在哪条会话的历史后面"),
                            ("C", "模型的温度参数"),
                            ("D", "检查点写磁盘的路径"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它就是一个会话标识：同 id 接同一份历史，不同 id 互不可见。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-20-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`get_state(cfg).next` 返回空元组，表示这条线还有节点没跑完。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "空元组表示「没有待执行节点」，也就是跑完了。有值时才说明停在了哪里。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-20-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第二次调用只传了 `messages`，为什么 `turns` 变成 2 而不是 1？",
                        "options": [
                            ("A", "因为 `turns` 有默认值 1"),
                            ("B", "因为检查点里存着上一轮的 `turns=1`，节点读到后 +1"),
                            ("C", "因为 `messages` 长度影响 `turns`"),
                            ("D", "因为 `add_messages` 会自增计数"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "输入没带 `turns`，状态从存档恢复为 1；节点计算 1+1=2。若输入里写 `turns: 0`，就会覆盖成 0。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-20-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "不带 checkpointer 的那次 `invoke` 正常返回，紧接的 `get_state` 却报 `ValueError: No checkpointer set`。这说明什么？",
                        "options": [
                            ("A", "图和状态查询是两个独立能力：图能跑，不代表能查历史"),
                            ("B", "`invoke` 内部会自动补一个 checkpointer"),
                            ("C", "`get_state` 需要额外传入 saver"),
                            ("D", "`compile` 之后不能再查询"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "检查点是可选能力。没有它，图照样执行，只是不存快照、也查不到历史。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-20-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "一个 Agent 服务同时服务多个用户，`thread_id` 该怎么设计？",
                        "options": [],
                        "answer": """核心原则：`thread_id` 必须能唯一标识「一个用户的一条会话」，且由服务端可控。

常见做法是 `f"{user_id}:{conversation_id}"`。用冒号或斜杠分隔，既能保证唯一，又能按前缀扫描出某个用户的全部会话
（Store 的 `search` 支持按命名空间前缀查，第 21 章）。

几个要点：

① 不要让客户端随便传 `thread_id` 就直接用——要校验它属于当前登录用户，否则能读到别人的会话。

② 不要用 uuid 当唯一会话 id 却不落库，否则用户下次打开就找不回来了。

③ 会话与用户分开存：会话列表（标题、更新时间）适合放 Store 或你自己的业务表，详细的对话历史交给检查点。

④ 明确生命周期：多久算过期、要不要归档。检查点只负责「存得住」，不负责「该不该留」。""",
                        "explanation": "会话标识既影响隔离性，也影响越权风险，不能只当技术细节。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-20-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一段代码：配置线程、跑一次图、打印快照的 `values` 与 `next`。",
                        "options": [],
                        "answer": {
                            "value": "from langgraph.checkpoint.memory import InMemorySaver\n\ngraph = builder.compile(checkpointer=InMemorySaver())\ncfg = {\"configurable\": {\"thread_id\": \"t1\"}}\n\ngraph.invoke({\"messages\": [HumanMessage(\"你好\")]}, cfg)\nsnap = graph.get_state(cfg)\nprint(\"values:\", snap.values)\nprint(\"next:\", snap.next)"
                        },
                        "explanation": "三件套：`compile(checkpointer=...)`、`configurable.thread_id`、`get_state`。缺一个都读不到快照。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-20-lesson-02",
                "title": "时间旅行与人工修正",
                "objectives": """1. 能用 `get_state_history` 按时间倒序读出全部检查点；
2. 能读懂检查点上的 `next` 与 `metadata.step`，定位「哪一步该改」；
3. 能用 `update_state` 在指定检查点上改状态，并从那里继续跑；
4. 能解释修正为什么产生新分支，而不是抹掉旧历史。""",
                "why_learn": """线上最常见的两个需求：一是「它刚才那步为什么这么走」，二是「把那个字段改掉，从那里重跑」。
检查点不只能恢复，还能回看与改写——这才让它从「缓存」变成「可运维的能力」。""",
                "concepts": """**`get_state_history(cfg)`**：返回该线程的全部检查点，从新到旧。
**`snap.next`**：这个检查点「接下来要执行谁」。它比时间顺序更有用——同一时刻可能有多条分支。
**`metadata["step"]`**：执行步数，负数表示还没开始。
**`update_state(config, values)`**：在指定检查点上写入新值，返回新检查点的配置。
**`invoke(None, new_cfg)`**：从新检查点继续执行，不重新输入。
**分支**：修正是「在旧点旁边长出一条新枝」，旧历史仍在，`get_state_history` 会同时看到两条。""",
                "plain": """时间旅行不是「撤销」，而是「从某一关重新开一局」。旧的那局还在，只是在旁边多了一局。

所以你会看到历史里出现重复的 `step`：同一个第 2 步，两个不同结果，一个来自原始执行，一个来自你改过的分支。
理解这一点，才不会误以为「历史被改了」。

实际用起来就三步：找到那个检查点、把要改的字段写进去、从那里继续跑。
找检查点别只看时间顺序，要看 `next`——它告诉你「这一步之后原本要做什么」，
你要改的往往是「某个节点刚跑完、下一个还没开始」的那一格。

一个容易忽略的限制：`update_state` 改的是状态，不会重跑已经执行过的节点。
如果你想让它重新执行，就得回到更早的那个检查点。""",
                "syntax": """**三步走**

```python
history = list(graph.get_state_history(cfg))        # 从新到旧

target = [s for s in history if s.next and "polish" in s.next][0]
new_cfg = graph.update_state(target.config, {"answer": "人工改过的答案"})
result = graph.invoke(None, new_cfg)                # 从那里继续
```

- `update_state` 的第一个参数是**检查点的 config**（不是 `thread_id` 那个 cfg）。
- 返回的新 config 里带新的 `checkpoint_id`，继续跑必须用它。
- `invoke(None, ...)` 的 `None` 表示「不提供新输入，接着已有的状态跑」。
- 改完不会自动重跑上游节点；要重跑就选更早的检查点。""",
                "example_code": '''from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
    answer: str


def draft(state: State) -> dict:
    return {"answer": "第一版答案"}


def polish(state: State) -> dict:
    return {"answer": state["answer"] + "（已润色）"}


builder = StateGraph(State)
builder.add_node("draft", draft)
builder.add_node("polish", polish)
builder.add_edge(START, "draft")
builder.add_edge("draft", "polish")
builder.add_edge("polish", END)
graph = builder.compile(checkpointer=InMemorySaver())

cfg = {"configurable": {"thread_id": "t1"}}
out = graph.invoke({"messages": [HumanMessage("写个答案")]}, cfg)
print("跑完:", out["answer"])

print()
print("=== 历史（从新到旧）===")
for i, snap in enumerate(graph.get_state_history(cfg)):
    print(i, "next=", snap.next, "step=", snap.metadata.get("step"), "answer=", repr(snap.values.get("answer")))

print()
print("=== 人工修正：把 draft 刚跑完的那个检查点改掉 ===")
history = list(graph.get_state_history(cfg))
target = [s for s in history if s.next and "polish" in s.next][0]
print("目标检查点 next:", target.next, "| answer:", repr(target.values["answer"]))

new_cfg = graph.update_state(target.config, {"answer": "人工改过的答案"})
after = graph.get_state(new_cfg)
print("改后 answer:", repr(after.values["answer"]), "| next:", after.next)

resumed = graph.invoke(None, new_cfg)
print("从这里继续跑:", resumed["answer"])

print()
print("=== 历史变成了两条分支 ===")
for i, snap in enumerate(graph.get_state_history(cfg)):
    print(i, "next=", snap.next, "step=", snap.metadata.get("step"), "answer=", repr(snap.values.get("answer")))''',
                "code_lines": """1. 图只有两步：`draft` 产出初稿，`polish` 加工。链路短才好观察历史。
2. `get_state_history` 返回的是**倒序**：第 0 条是最新，最后一条是最早（`step=-1` 是初始输入）。
3. 每条快照的 `next` 写着「接下来要执行谁」：`('polish',)` 表示 draft 刚跑完、polish 还没开始。
4. 选择目标检查点的条件就是「`next` 里有 polish」——这是最可靠的选择方式，比按索引硬编码稳。
5. `update_state(target.config, {...})` 的第一个参数必须是检查点的 `config`，传线程 cfg 会报错。
6. 返回的新 `new_cfg` 带新的 `checkpoint_id`，`next` 仍是 `('polish',)`，说明接着要跑的还是 polish。
7. `invoke(None, new_cfg)` 从这一点继续，polish 用的是你改过的答案，所以结果是「人工改过的答案（已润色）」。
8. 最后的历史有 6 条：`step=2` 出现两次，一个是原始结果，一个是新分支——旧历史没被覆盖。""",
                "output": """# 程序输出
跑完: 第一版答案（已润色）

=== 历史（从新到旧）===
0 next= () step= 2 answer= '第一版答案（已润色）'
1 next= ('polish',) step= 1 answer= '第一版答案'
2 next= ('draft',) step= 0 answer= None
3 next= ('__start__',) step= -1 answer= None

=== 人工修正：把 draft 刚跑完的那个检查点改掉 ===
目标检查点 next: ('polish',) | answer: '第一版答案'
改后 answer: '人工改过的答案' | next: ('polish',)
从这里继续跑: 人工改过的答案（已润色）

=== 历史变成了两条分支 ===
0 next= () step= 3 answer= '人工改过的答案（已润色）'
1 next= ('polish',) step= 2 answer= '人工改过的答案'
2 next= () step= 2 answer= '第一版答案（已润色）'
3 next= ('polish',) step= 1 answer= '第一版答案'
4 next= ('draft',) step= 0 answer= None
5 next= ('__start__',) step= -1 answer= None""",
                "mistakes": """- 把线程的 `cfg` 传给 `update_state`：它要的是某个检查点的 `config`，两者不是一回事。
- `update_state` 后直接用 `cfg` 继续跑：跑的还是旧分支，改动看不到。
- 以为修正会重跑上游节点：它只改状态，已执行的节点不会重来。
- 按列表下标选检查点（比如 `history[1]`）：节点增减后下标就错，应该按 `next` 或 `metadata` 匹配。
- 以为历史被覆盖了：看到重复 `step` 就慌了，其实是新分支。
- 在生产环境随手 `update_state`：对客诉排查很有用，但没有审计记录时会说不清谁改了什么。""",
                "error_analysis": """`ValueError: No checkpointer set`
—— 还是那个老问题：没装检查点就没有历史，也就没有时间旅行。

`KeyError: 'configurable'`
—— 传给 `update_state` 的不是检查点 config。用 `snap.config`，不要自己拼。

改完继续跑，结果没变
—— 用了旧的 `cfg`。要用 `update_state` 的返回值。

`invoke(None, cfg)` 又从头跑了一遍
—— 该 `cfg` 指向的检查点没有待执行节点（`next` 为空）。选有 `next` 的那一条。""",
                "beginner_practice": """1. 打印每条历史的 `snap.created_at`，确认顺序确实是倒序。
2. 把 `target` 换成 `next` 含 `draft` 的那条（更早），再 `update_state` + 继续跑，观察 `draft` 是否被重跑。""",
                "advanced_practice": """设计一个「人工修正」的审计方案：谁在什么时候改了哪个字段、从哪个检查点继续、最终结果是什么。
说明这些信息应该存在哪里，以及怎么和检查点关联。""",
                "quiz_note": "本节 6 道题：2 道基础理解（历史顺序、`update_state` 的第一个参数）+ 2 道代码阅读（为什么选 `next` 含 polish 的那条、重复 step 说明什么）+ 2 道应用练习（修正流程、审计设计）。",
                "summary": """`get_state_history` 给出全部检查点，倒序；`next` 比时间顺序更好用。
`update_state` 在指定检查点上写入新值，返回新 config；用它继续跑。
修正是长新分支，旧历史仍在。""",
                "next_lesson": "检查点管「一条会话的过去」，下一章管「跨会话还记得你」——那是 Store 的活儿。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-20-02",
                        "name": "时间旅行与人工修正",
                        "goal": "能定位检查点、改写状态并从该点继续执行。",
                        "minutes": 45,
                        "criteria": "能解释修行为什么产生分支，并正确使用 `update_state` 的返回值。",
                        "requires": ["langgraph-agent-20-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-20-02-1",
                        "kp": 0,
                        "title": "从更早的检查点重跑",
                        "description": "现在改的是「draft 之后」，所以 draft 没重跑。改成从「draft 之前」修正，让 draft 重新执行。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''history = list(graph.get_state_history(cfg))
target = [s for s in history if s.next and "draft" in s.next][0]   # draft 还没跑
new_cfg = graph.update_state(target.config, {"answer": "外部注入的初稿"})
result = graph.invoke(None, new_cfg)
print(result["answer"])''',
                        "explanation": "`next` 含 `draft` 表示「下一步执行 draft」，此时状态里还没有 draft 的产出。从这里继续，draft 会覆盖你注入的值——想保留就得改 draft 的逻辑。",
                    },
                    {
                        "code": "lg-ex-20-02-2",
                        "kp": 0,
                        "title": "修正该不该留痕",
                        "description": "生产环境允许人工 `update_state`，需要额外记录什么？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """至少要记四样：谁、什么时候、改了哪些字段、改前改后各是什么。

原因有三：

① 可追责：用户投诉「为什么给我退了两次」，要能证明是人工改过，而不是系统重复执行。

② 可复现：出问题时需要从同一个检查点重放。记下 `checkpoint_id` 才能精确回到那一刻。

③ 可评估：统计人工修正的频率与原因，才知道 Prompt 或工具哪里需要改。频繁修正某个字段，说明那一步模型不可靠。

实现上不必塞进状态（会污染业务数据），写到独立的审计表：`thread_id`、`checkpoint_id`、操作人、
字段名、旧值、新值、时间、原因。检查点负责「状态是什么」，审计表负责「为什么变成这样」。""",
                        "explanation": "能改历史是能力，能解释历史是责任。两者要分开设计。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-20-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`get_state_history` 返回的顺序是？",
                        "options": [
                            ("A", "从旧到新"),
                            ("B", "从新到旧"),
                            ("C", "按节点名字母序"),
                            ("D", "随机顺序"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "第 0 条是最新检查点。示例里 `step` 依次是 2、1、0、-1，正是倒序。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-20-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`update_state` 的第一个参数可以直接传 `{\"configurable\": {\"thread_id\": \"t1\"}}`。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它需要一个具体的检查点 config（带 `checkpoint_id`），通常用 `snap.config`。只给 `thread_id` 无法确定改哪一步。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-20-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "为什么用「`next` 里含 polish」来选检查点，而不是 `history[1]`？",
                        "options": [
                            ("A", "因为下标从 0 开始"),
                            ("B", "因为节点增减后下标会变，而 `next` 表达的是语义「draft 已跑完、polish 未跑」"),
                            ("C", "因为 `history` 是生成器，不能取下标"),
                            ("D", "因为 `next` 一定只有一个元素"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "按语义选比按下标选稳。图一改，下标全变，但「polish 还没跑」这个条件仍然成立。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-20-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "修正后历史里出现两条 `step=2`，说明什么？",
                        "options": [
                            ("A", "数据写坏了，需要清理"),
                            ("B", "`update_state` 在旧点旁长出新分支，旧分支仍然保留"),
                            ("C", "`polish` 被执行了两次"),
                            ("D", "检查点去重失败"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "同一步可以有多条路径，这正是「时间旅行」的意义：旧结果留在历史里可对比，新结果在另一条枝上。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-20-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "`update_state` 改完状态后，上游节点会自动重跑吗？为什么？",
                        "options": [],
                        "answer": """不会。`update_state` 只是在选定的检查点上写入了新值，然后从「该检查点的 `next`」继续。

已经执行过的节点，其产出已经写进状态，框架没有理由、也没有依据去重跑它们——
重跑意味着再次调用模型或工具，这可能产生费用与副作用，绝不应该是隐式行为。

想让它重跑，有两个办法：

① 选更早的检查点（`next` 指向那个节点的），从那里继续，节点自然重新执行。

② 显式改图或加一条回边，让流程真的再走一遍那个节点。

这也是一条设计纪律：修正要「可预测」。用户点一次「改这个字段」，结果系统悄悄重跑了五个节点，
这种事没人能接受。""",
                        "explanation": "「隐式重跑」是时间旅行功能最容易造成事故的地方，理解它能避免误用。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-20-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写出「找到 draft 刚跑完的检查点、把 answer 改成「人工稿」、从那里继续跑」的完整代码。",
                        "options": [],
                        "answer": {
                            "value": "history = list(graph.get_state_history(cfg))\ntarget = [s for s in history if s.next and \"polish\" in s.next][0]\n\nnew_cfg = graph.update_state(target.config, {\"answer\": \"人工稿\"})\nresult = graph.invoke(None, new_cfg)\nprint(result[\"answer\"])   # 人工稿（已润色）"
                        },
                        "explanation": "四行：取历史、按 `next` 选点、写入、从该点继续。注意继续跑用的是 `update_state` 的返回值。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 21 章
    {
        "code": "langgraph-agent-21",
        "order_index": 21,
        "title": "Store",
        "description": "跨会话的长期数据放 Store，不塞进状态里。",
        "lessons": [
            {
                "code": "langgraph-agent-21-lesson-01",
                "title": "跨线程长期存储",
                "objectives": """1. 能说清 Checkpointer 与 Store 的分工：一个存「一条会话的过去」，一个存「跨会话的事实」；
2. 能用 `Runtime` 在节点里拿到 `store`，并读写命名空间；
3. 能用 `put / get / search` 完成写入、读取与按前缀查找；
4. 能说明哪些数据不该放进状态。""",
                "why_learn": """用户说「以后都简短点」，这句话不该只对当前这条会话生效。
状态跟着 `thread_id` 走，换条会话就没了；跨会话的事实需要另一个容器——Store。""",
                "concepts": """**Store**：跨线程的键值存储，用「命名空间元组 + 键」定位一条记录。
**与检查点的分工**：检查点存「这条会话每一步的状态」；Store 存「这个用户的偏好、档案、长期记忆」。
**`Runtime`**：节点第二个参数声明 `runtime: Runtime` 就能拿到 `runtime.store`（1.x 的注入方式）。
**`put(ns, key, value)` / `get(ns, key)` / `search(ns)`**：写、读、按命名空间前缀查。
**命名空间**：元组，例如 `("preferences", user_id)`；`search` 传更短的前缀能一次查到多条。
**没传 store**：`runtime.store` 是 `None`，一写就 `AttributeError`。""",
                "plain": """把这两个容器想成「聊天记录」和「客户档案」。

聊天记录属于某一次对话，翻回去能看到当时说了什么；这就是检查点。
客户档案属于这个人，换个渠道、换次对话都还在；这就是 Store。

分错了会很难受：把偏好塞进状态，用户开新会话就得重说一遍；
把整段对话塞进 Store，每次都要手动清理，还会把存储撑爆。

技术上要注意的是取值方式。当前版本里，节点要拿到 store 得声明 `runtime: Runtime` 参数，
然后 `runtime.store`。网上一些老教程写的是 `config["store"]`，在当前版本里取不到——
照着抄会得到一个「键不存在」的错误，而不是一个「用法变了」的提示。""",
                "syntax": """**装配 + 取值**

```python
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
graph = builder.compile(checkpointer=InMemorySaver(), store=store)


def remember(state, runtime: Runtime) -> dict:
    ns = ("preferences", state["user"])
    runtime.store.put(ns, "style", {"tone": "简短"})
    item = runtime.store.get(ns, "style")
    return {}
```

- 命名空间是元组，不要传字符串。
- `search(("preferences",))` 查整个命名空间；`search(("preferences", "alice"))` 查这个前缀下全部键。
- `get` 返回的对象有 `.value`，不存在时返回 `None`。
- `InMemoryStore` 也是进程内存储，生产要换持久化实现。""",
                "example_code": '''from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore


class State(TypedDict):
    messages: Annotated[list, add_messages]
    user: str
    greeting: str


store = InMemoryStore()


def remember(state: State, runtime: Runtime) -> dict:
    ns = ("preferences", state["user"])
    runtime.store.put(ns, "style", {"tone": "简短", "lang": "zh"})
    print("  写入:", ns, "->", runtime.store.get(ns, "style").value)
    return {}


def greet(state: State, runtime: Runtime) -> dict:
    item = runtime.store.get(("preferences", state["user"]), "style")
    tone = item.value["tone"] if item else "未知"
    print("  读取:", item.value if item else None)
    return {"greeting": f"{state['user']} 的偏好语气：{tone}"}


builder = StateGraph(State)
builder.add_node("remember", remember)
builder.add_node("greet", greet)
builder.add_edge(START, "remember")
builder.add_edge("remember", "greet")
builder.add_edge("greet", END)
graph = builder.compile(checkpointer=InMemorySaver(), store=store)

for user in ("alice", "bob"):
    cfg = {"configurable": {"thread_id": f"thread-{user}"}}
    out = graph.invoke({"messages": [HumanMessage("你好")], "user": user, "greeting": ""}, cfg)
    print(user, "->", out["greeting"])

print()
print("=== 直接操作 store ===")
print("get:", store.get(("preferences", "alice"), "style").value)
print("search 全命名空间:", [i.value for i in store.search(("preferences",))])
print("search 带前缀的键:", [i.key for i in store.search(("preferences", "alice"))])

print()
print("=== 编译时不传 store ===")
plain = builder.compile(checkpointer=InMemorySaver())
try:
    plain.invoke({"messages": [HumanMessage("x")], "user": "carol", "greeting": ""},
                 {"configurable": {"thread_id": "c1"}})
except Exception as exc:
    print(type(exc).__name__, ":", str(exc)[:100])''',
                "code_lines": """1. `remember` 的第二个参数声明成 `runtime: Runtime`，框架就会把运行时对象注入进来。
2. 命名空间 `("preferences", state["user"])` 把「偏好」和「谁」分开，后续能按前缀批量查。
3. `put(ns, key, value)` 三个参数：写到哪、叫什么、写什么。`value` 是普通字典，不用包一层。
4. `get` 返回的对象要取 `.value`；记录不存在时返回 `None`，所以 `greet` 里有 `if item else` 分支。
5. 两个用户跑同一个图，各自的 `thread_id` 不同，但偏好都能读到——说明数据确实不在状态里。
6. `search(("preferences",))` 拿到两条记录；`search(("preferences", "alice"))` 只拿到 alice 的键。
7. 编译时不传 `store`，`runtime.store` 就是 `None`，第一次 `put` 就 `AttributeError`。
8. 注意它和检查点是两套存储：`compile` 时分别传，互不依赖。""",
                "output": """# 程序输出
  写入: ('preferences', 'alice') -> {'tone': '简短', 'lang': 'zh'}
  读取: {'tone': '简短', 'lang': 'zh'}
alice -> alice 的偏好语气：简短
  写入: ('preferences', 'bob') -> {'tone': '简短', 'lang': 'zh'}
  读取: {'tone': '简短', 'lang': 'zh'}
bob -> bob 的偏好语气：简短

=== 直接操作 store ===
get: {'tone': '简短', 'lang': 'zh'}
search 全命名空间: [{'tone': '简短', 'lang': 'zh'}, {'tone': '简短', 'lang': 'zh'}]
search 带前缀的键: ['style']

=== 编译时不传 store ===
AttributeError : 'NoneType' object has no attribute 'put'""",
                "mistakes": """- 把偏好、档案这类跨会话数据写进状态：换会话就丢，用户要重复交代。
- 把整段对话历史灌进 Store：状态里已经有检查点存着，重复存两份，还不好清理。
- 命名空间传字符串（`"preferences/alice"`）：类型不对，查不到也写不进。
- 声明 `runtime: Runtime` 却忘了 `compile(store=...)`：`runtime.store` 是 `None`。
- 老教程里的 `config["store"]`：当前版本取不到，要改用 `Runtime`。
- 用 `InMemoryStore` 上线：重启即丢，多副本各存各的。""",
                "error_analysis": """`AttributeError: 'NoneType' object has no attribute 'put'`
—— `runtime.store` 是 `None`。编译时没传 `store`。

`TypeError: remember() missing 1 required keyword-only argument: 'store'`
—— 把 `store` 写成了普通关键字参数。要声明 `runtime: Runtime` 再取 `runtime.store`。

`KeyError: 'store'`
—— 用了 `config["store"]` 这种旧写法。当前版本从 `Runtime` 取。

`search` 返回空列表
—— 命名空间前缀不匹配。打印 `store.search(())` 看看实际写到了哪个空间下。

写入成功但读不到
—— 两个不同的 store 实例（比如一个在模块级、一个在别处新建）。要用同一个对象。""",
                "beginner_practice": """1. 给 `remember` 加一个 `key` 参数，让同一个用户能存多条偏好（比如 `style` 与 `level`）。
2. 把 `search(("preferences",))` 换成 `search(())`，观察返回值有什么变化。""",
                "advanced_practice": """设计长期记忆的读写策略：什么时候写（每轮都写？只在模型判断「这是稳定偏好」时写？）、怎么防重复、怎么过期。
说明你会把这些元信息放在 Store 的 value 里，还是另建结构。""",
                "quiz_note": "本节 6 道题：2 道基础理解（Store 与检查点的分工、命名空间形态）+ 2 道代码阅读（为什么两个用户都能读到、没传 store 报什么）+ 2 道应用练习（哪些数据该进 Store、长期记忆策略）。",
                "summary": """检查点管一条会话的过去，Store 管跨会话的事实。
节点用 `runtime: Runtime` 取 `runtime.store`，命名空间用元组。
两套存储分别装配；内存版都只活进程内。""",
                "next_lesson": "有了记忆，下一步让流程「停下来等人」——下一章的中断与恢复。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-21-01",
                        "name": "跨线程长期存储",
                        "goal": "能用 Store 存取跨线程数据，并正确区分状态与长期记忆。",
                        "minutes": 40,
                        "criteria": "能写出命名空间读写代码，并说明为什么某些数据不能放状态。",
                        "requires": ["langgraph-agent-20-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-21-01-1",
                        "kp": 0,
                        "title": "存两条偏好",
                        "description": "同一个用户存 `style` 与 `level` 两条记录，并一次列出他的全部偏好。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''def save(runtime, user: str) -> None:
    ns = ("preferences", user)
    runtime.store.put(ns, "style", {"tone": "简短"})
    runtime.store.put(ns, "level", {"stage": "进阶", "chapter": 21})


def load_all(runtime, user: str) -> dict:
    ns = ("preferences", user)
    return {item.key: item.value for item in runtime.store.search(ns)}''',
                        "explanation": "同一个命名空间下用不同 `key` 区分不同事实；`search(ns)` 一次取回该用户的全部记录，拼成字典就能直接用。",
                    },
                    {
                        "code": "lg-ex-21-01-2",
                        "kp": 0,
                        "title": "哪些数据不该进状态",
                        "description": "给出三条判断标准：什么数据应该放 Store，而不是状态。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """三条标准，满足任意一条就考虑 Store。

① 生命周期比会话长：用户偏好、等级、常用课程。换条会话还要用，放状态就是错配。

② 与具体对话无关：账号信息、权限、订阅状态。它们不随对话改变，塞进状态只会让快照越来越大。

③ 需要被别的会话读到：上次学习进度、历史错题。状态按 `thread_id` 隔离，别的会话看不见。

反过来，这些应该留在状态里：本轮的工具结果、中间草稿、待确认的动作、临时路由标记。
它们的共同点是「这一趟用完就结束」。

还有一个工程角度的判断：状态每个检查点都会整体存一份，越大越慢；Store 是按键读写的，按需取用。
把大块的长期数据放状态，会让每次调用都拖着它跑。""",
                        "explanation": "分层的标准是「生命周期」与「归属」，不是「数据大小」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-21-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "Store 与 Checkpointer 的分工是什么？",
                        "options": [
                            ("A", "都用同一种存储，只是名字不同"),
                            ("B", "检查点存一条会话每步的状态，Store 存跨会话的事实"),
                            ("C", "检查点存用户档案，Store 存对话历史"),
                            ("D", "Store 只在内存里，检查点一定落盘"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "一个是「这条会话的过去」，一个是「这个人的长期事实」。分清了才知道什么数据该放哪。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-21-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "命名空间可以传字符串，例如 `\"preferences/alice\"`。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它是元组，例如 `(\"preferences\", \"alice\")`，这样才能按前缀 `search`。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-21-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "alice 和 bob 的 `thread_id` 不同，为什么都能读到各自的偏好？",
                        "options": [
                            ("A", "因为状态被复制了一份"),
                            ("B", "因为偏好写在 Store 里，按用户命名空间区分，与线程无关"),
                            ("C", "因为 `add_messages` 会自动同步"),
                            ("D", "因为 `InMemorySaver` 按用户分了区"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "这正是 Store 的用途：数据归属是「用户」，不是「某条会话」。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-21-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例最后一段报 `AttributeError: 'NoneType' object has no attribute 'put'`，根因是什么？",
                        "options": [
                            ("A", "`InMemoryStore` 不支持 `put`"),
                            ("B", "编译时没传 `store`，注入的 `runtime.store` 是 `None`"),
                            ("C", "命名空间写错了"),
                            ("D", "节点函数签名写错了"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "注入本身没错，注入进来的是 `None`。这类错误看着像「方法不存在」，实际是「对象不存在」。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-21-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「用户偏好」不该放在状态里？",
                        "options": [],
                        "answer": """三个原因。

① 生命周期不匹配：状态属于一条会话，偏好属于一个人。放状态里，用户开新会话就得再说一遍。

② 快照变大：每个检查点都会整体存一份状态。偏好这类长期数据每步都跟着存，浪费空间也拖慢读写。

③ 无法跨会话共享：状态按 `thread_id` 隔离，别的会话读不到，想复用只能再传一遍。

正确做法是：偏好写 Store，节点需要时按 `(命名空间, 用户)` 读出来，用完不写回状态
（或只在需要展示时写进一个临时字段）。

判断口诀：这趟用完就结束的放状态，下次还要用的放 Store。""",
                        "explanation": "这不是「哪个方便」，而是「数据归属谁」的问题。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-21-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个节点：读取当前用户的偏好，取得 `tone`，若不存在则写入默认值「标准」。",
                        "options": [],
                        "answer": {
                            "value": "def load_pref(state: State, runtime: Runtime) -> dict:\n    ns = (\"preferences\", state[\"user\"])\n    item = runtime.store.get(ns, \"style\")\n    if item is None:\n        runtime.store.put(ns, \"style\", {\"tone\": \"标准\"})\n        tone = \"标准\"\n    else:\n        tone = item.value.get(\"tone\", \"标准\")\n    return {\"greeting\": f\"按「{tone}」语气回答\"}"
                        },
                        "explanation": "先读后写，读不到才写默认值——避免每次调用都覆盖用户改过的偏好。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
