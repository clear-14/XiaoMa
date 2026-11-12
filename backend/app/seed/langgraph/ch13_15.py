"""LangGraph Agent 开发：第 13—15 章。

第 13 章讲三种「决定下一步去哪」的方式（条件边、Command、Send），
第 14 章讲循环与上限，第 15 章讲状态合并规则——它是并行与累积的前提。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 13 章
    {
        "code": "langgraph-agent-13",
        "order_index": 13,
        "title": "条件路由",
        "description": "让流程按数据决定走向，而不是写死顺序。",
        "lessons": [
            {
                "code": "langgraph-agent-13-lesson-01",
                "title": "路由函数与条件边",
                "objectives": """1. 能写一个纯函数作为路由函数，返回下一站的名字；
2. 能区分「只传函数」与「传函数 + 映射表」两种写法；
3. 能说明框架为什么不替你兜底未知返回值；
4. 能给每条条件边配一个兜底分支。""",
                "why_learn": """条件路由是 Agent「自己决定下一步」的落地方式。
写不好它，图要么走错分支，要么在遇到没见过的输入时直接崩。""",
                "concepts": """**路由函数**：读状态、返回一个字符串，字符串决定下一站。
**条件边**：挂在某个节点之后，由路由函数的返回值选一条出边。
**两种写法**：只传函数（返回值即节点名）；传函数 + 映射表（返回值是短键）。
**框架不兜底**：返回未映射的值会抛 `KeyError`，不会自动走默认分支。
**兜底分支**：路由函数自己必须处理「没命中任何规则」的情况。""",
                "plain": """路由函数像分拣员：看一眼包裹上的面单（状态），把它丢进「本市 / 外地 / 疑难」三个筐之一。
分拣员必须对每个包裹都有结论——遇到没见过的面单，他不能愣在那儿，
要么丢进「疑难」筐，要么当场报错。系统不会替他决定丢哪个筐。""",
                "syntax": """**两种写法**

```python
# 只传函数：返回值必须等于某个节点名
builder.add_conditional_edges("classify", route_fn)

# 函数 + 映射表：返回值是短键，映射到节点名
builder.add_conditional_edges(
    "classify",
    route_fn,
    {"code": "code_answer", "concept": "concept_answer", "other": "fallback"},
)
```

- 路由函数必须是纯函数：只读状态，不做副作用。
- 返回未在映射表里的键会抛 `KeyError`。
- 映射表建议显式列出全部可能值，包括兜底。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    kind: str
    answer: str


def classify(state: State) -> dict:
    return {}


def code_answer(state: State) -> dict:
    return {"answer": "给你代码"}


def concept_answer(state: State) -> dict:
    return {"answer": "给你概念"}


def fallback(state: State) -> dict:
    return {"answer": "没听懂，请再说一次"}


def short_route(state: State) -> str:
    """路由函数：把各种输入压成三个短键，未知一律走 other。"""
    table = {"code": "code", "concept": "concept"}
    return table.get(state["kind"], "other")


builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("code_answer", code_answer)
builder.add_node("concept_answer", concept_answer)
builder.add_node("fallback", fallback)
builder.add_edge(START, "classify")
builder.add_conditional_edges(
    "classify",
    short_route,
    {"code": "code_answer", "concept": "concept_answer", "other": "fallback"},
)
builder.add_edge("code_answer", END)
builder.add_edge("concept_answer", END)
builder.add_edge("fallback", END)
graph = builder.compile()

for kind in ("code", "concept", "unknown"):
    result = graph.invoke({"kind": kind, "answer": ""})
    print(f"kind={kind:8s} -> answer={result['answer']}")

print()
print("=== 路由函数返回未映射的值 ===")


def raw_route(state: State) -> str:
    return state["kind"]        # 不做兜底


b2 = StateGraph(State)
b2.add_node("classify", classify)
b2.add_node("code_answer", code_answer)
b2.add_edge(START, "classify")
b2.add_conditional_edges("classify", raw_route, {"code": "code_answer"})
b2.add_edge("code_answer", END)
try:
    b2.compile().invoke({"kind": "weird", "answer": ""})
except KeyError as exc:
    print("  KeyError:", exc)''',
                "code_lines": """1. `classify` 什么都不改，只占一个位置——真实项目里它做分类判断。
2. `short_route` 是纯函数：只读 `state["kind"]`，返回一个短键。
3. `table.get(..., "other")` 是关键：未知输入被压成 `other`，这是兜底的唯一来源。
4. `add_conditional_edges` 的第三个参数把短键映射到节点名，路由函数因此不必知道节点叫什么。
5. 三次调用分别命中 `code`、`concept` 和兜底 `other`，输出各不相同。
6. 第二段故意不做兜底，`raw_route` 直接返回原始值。
7. 传入 `weird` 时抛 `KeyError: 'weird'`——框架确实不替你兜底。""",
                "output": """# 程序输出
kind=code     -> answer=给你代码
kind=concept  -> answer=给你概念
kind=unknown  -> answer=没听懂，请再说一次

=== 路由函数返回未映射的值 ===
  KeyError: 'weird'""",
                "mistakes": """- 路由函数返回了中文（「代码」「概念」），而映射表的键是英文，全部落到 KeyError。
- 只写了正常分支，没写兜底，线上遇到新输入直接 500。
- 路由函数里做副作用（写日志、改状态），导致同样的输入两次结果不同。
- 用 `if/elif` 链但最后没有 `else`，函数某些路径返回 `None`。
- 把分类逻辑写进路由函数里，函数变得无法单独测试。""",
                "error_analysis": """`KeyError: 'xxx'`
—— 路由函数返回了映射表里没有的键。加兜底，或补齐映射。

条件边的箭头在图上显示为虚线，但运行时不走
—— 映射表里的节点名拼错，或该节点没注册。

分类结果看起来「总是走兜底」
—— 路由函数的判断条件与实际数据不匹配，打印函数入参核对。""",
                "beginner_practice": """1. 给 `short_route` 加一条「math」分支，并补一个对应节点与映射。
2. 把 `table.get(state["kind"], "other")` 改成 `state["kind"]`，观察三次调用的结果变化。""",
                "advanced_practice": """设计一个「多级路由」：先分大类（课程 / 闲聊 / 其他），课程再分小类。
说明应该用一张映射表还是两层条件边，并给出可测试性上的理由。""",
                "quiz_note": "本节 6 道题：2 道基础理解（路由函数的职责、映射表的作用）+ 2 道代码阅读（读三次结果、读 KeyError）+ 2 道应用练习（补兜底、设计多级路由）。",
                "summary": """路由函数 = 纯函数 + 返回下一站的键。
映射表把「短键」和「节点名」解耦，改节点名不影响路由逻辑。
框架不兜底，兜底必须写在路由函数里。""",
                "next_lesson": "下一节看另外两种走向控制：节点自己跳转（Command）与并行分发（Send）。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-13-01",
                        "name": "路由函数与条件边",
                        "goal": "能写出带兜底的纯函数路由，并正确配置映射表。",
                        "minutes": 40,
                        "criteria": "能说明两种写法差别，并指出未映射返回值会抛 `KeyError`。",
                        "requires": ["langgraph-agent-12-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-13-01-1",
                        "kp": 0,
                        "title": "补一个兜底分支",
                        "description": "现有映射表只有 `code` 与 `concept` 两项，路由函数直接返回原始值。改成永不抛 KeyError 的版本。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def safe_route(state: State) -> str:
    known = {"code", "concept"}
    return state["kind"] if state["kind"] in known else "other"


builder.add_conditional_edges(
    "classify",
    safe_route,
    {"code": "code_answer", "concept": "concept_answer", "other": "fallback"},
)''',
                        "explanation": "先判断「是不是已知值」，再决定返回什么——比在映射表里加默认项更明确，因为兜底节点需要真的存在。",
                    },
                    {
                        "code": "lg-ex-13-01-2",
                        "kp": 0,
                        "title": "路由函数该不该做业务",
                        "description": "把「判断问题类型」的逻辑写在路由函数里，还是写在它前面的节点里？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """写在节点里，路由函数只负责「读结论、返回键」。

理由：① 分类往往需要调用模型或查表，属于有副作用的业务，放进路由函数就破坏了纯函数性质；
② 分类结果写进状态后可以被日志、持久化、人工修正复用，路由函数只读不写；
③ 路由函数保持「一行映射」，单独测试它极简单，而测试一次模型调用要造 mock。

结论：节点产出结论，路由函数消费结论。两者职责不同，不要合在一起。""",
                        "explanation": "这条分工是「可测试性」和「可观测性」的双重收益。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-13-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "路由函数的返回值决定什么？",
                        "options": [
                            ("A", "状态的最终值"),
                            ("B", "下一步去哪个节点"),
                            ("C", "节点执行几次"),
                            ("D", "图的节点数量"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "返回值经过（可选的）映射表后，指向一个后继节点，从而决定走向。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-13-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "路由函数返回未在映射表里的键时，框架会自动走一个默认分支。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "框架直接抛 `KeyError`。兜底必须由路由函数自己实现（例如压成 `other`）。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-13-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "传入 `kind=\"unknown\"` 时，走到哪个节点？",
                        "options": [
                            ("A", "`code_answer`"),
                            ("B", "`concept_answer`"),
                            ("C", "`fallback`"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "`table.get` 对未知键返回 `\"other\"`，映射表把 `other` 指向 `fallback`。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-13-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第二段为什么抛的是 `KeyError` 而不是别的异常？",
                        "options": [
                            ("A", "因为节点没注册"),
                            ("B", "因为路由返回值被当成映射表的键去查，查不到"),
                            ("C", "因为 State 缺字段"),
                            ("D", "因为图没编译"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "框架用返回值去映射表里取节点名，取不到就是字典的 `KeyError`。这也说明报错信息不够友好，兜底只能自己写。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-13-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么建议映射表显式列出所有可能值，而不是只列几个常见值？",
                        "options": [],
                        "answer": """因为映射表本身就是这份路由的「契约文档」。

显式列全有三点好处：① 读代码的人一眼看到「一共有几条出路」，不用去追路由函数的每个分支；
② 新增分支时，忘记改映射表会立刻在测试里暴露（返回一个没映射的键）；
③ 每个键对应哪个节点是可审计的，避免「某个键被悄悄指向了不相干的节点」。

只列常见值的写法，等于把契约藏在 `get` 的默认参数里，时间一长没人说得清到底有几条路。""",
                        "explanation": "映射表是结构，结构应该完整可见，不要用默认值掩盖缺失。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-13-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给路由加一个「需要人工确认」的分支：`kind == \"risky\"` 时走向 `need_approval` 节点。写出路由函数与映射表。",
                        "options": [],
                        "answer": {"value": "def route(state: State) -> str:\n    table = {\"code\": \"code\", \"concept\": \"concept\", \"risky\": \"risky\"}\n    return table.get(state[\"kind\"], \"other\")\n\n\nbuilder.add_conditional_edges(\n    \"classify\",\n    route,\n    {\n        \"code\": \"code_answer\",\n        \"concept\": \"concept_answer\",\n        \"risky\": \"need_approval\",\n        \"other\": \"fallback\",\n    },\n)"},
                        "explanation": "加分支要同时改两处：路由表（认得出这个键）与映射表（知道它去哪）。缺一处就会走兜底或报错。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-13-lesson-02",
                "title": "Command 与 Send",
                "objectives": """1. 能用 `Command(update=..., goto=...)` 让节点自己决定下一站；
2. 能说出 `Command` 相比条件边的优势与代价；
3. 能用 `Send` 把一批任务并行分发到同一个节点；
4. 能解释 `Send` 为什么必须配合 `input_schema` 与 reducer。""",
                "why_learn": """条件边要在「父节点之后」单独声明，走向和节点被拆成两处。
`Command` 把「改什么」和「去哪」写在节点里；`Send` 则解决「一次要做 N 件相同的事」。""",
                "concepts": """**`Command(update, goto)`**：节点返回值同时携带状态增量与下一站。
**结构不可见**：用 `Command` 的走向不会出现在图结构导出里，可读性下降。
**`Send(node, arg)`**：把任务分发出去，`arg` 成为该节点的输入。
**必须配 `input_schema`**：被分发节点要知道自己只吃 `arg` 里的字段。
**必须配 reducer**：多个并行分支写同一个键会冲突。""",
                "plain": """条件边像在走廊尽头贴一张指示牌：走完这个房间，抬头看牌决定往哪走。
`Command` 像房间里的人自己说「我下一步去 302」——更直接，但门口的指示牌上看不到这条路线。
`Send` 像把一叠工单同时发给同一个工位：每张单子写不同的任务，工位按单子干活，最后把结果汇总到一处。""",
                "syntax": """**Command**

```python
from langgraph.types import Command

def node(state) -> Command:
    return Command(update={"kind": "code"}, goto="write_code")
```

**Send**

```python
from langgraph.types import Send

def dispatch(state):
    return [Send("work", {"topic": t}) for t in state["topics"]]

builder.add_node("work", work, input_schema=TaskState)
builder.add_conditional_edges(START, dispatch)
```

- `Send` 只能从条件边的路由函数返回，不能当普通节点的返回值。
- 多个 `Send` 并行执行，写同一个键时必须声明 reducer。""",
                "example_code": '''import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send


# ---------- 一、Command：节点自己决定下一站 ----------
class State(TypedDict):
    question: str
    kind: str
    answer: str


def classify(state: State) -> Command:
    if "代码" in state["question"]:
        return Command(update={"kind": "code"}, goto="write_code")
    return Command(update={"kind": "concept"}, goto="explain")


def write_code(state: State) -> dict:
    return {"answer": "给你一段示例代码"}


def explain(state: State) -> dict:
    return {"answer": "用一句话解释这个概念"}


builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("write_code", write_code)
builder.add_node("explain", explain)
builder.add_edge(START, "classify")
builder.add_edge("write_code", END)
builder.add_edge("explain", END)
graph = builder.compile()

print("=== Command 路由 ===")
for question in ("给我一段代码", "解释一下概念"):
    result = graph.invoke({"question": question, "kind": "", "answer": ""})
    print(f"  {question:10s} -> kind={result['kind']:8s} {result['answer']}")

print("  图结构里能看到 classify 的出边吗：")
for edge in graph.get_graph().edges:
    print(f"    {edge.source:10s} -> {edge.target}")

# ---------- 二、Send：并行分发 ----------
class FanState(TypedDict):
    topics: list[str]
    results: Annotated[list[str], operator.add]


class TaskState(TypedDict):
    topic: str
    results: list[str]


def dispatch(state: FanState):
    return [Send("work", {"topic": topic}) for topic in state["topics"]]


def work(state: TaskState) -> dict:
    return {"results": [f"{state['topic']} 已处理"]}


fan = StateGraph(FanState)
fan.add_node("work", work, input_schema=TaskState)
fan.add_conditional_edges(START, dispatch)
fan.add_edge("work", END)

print()
print("=== Send 并行分发 ===")
print("  ", fan.compile().invoke({"topics": ["State", "Node", "Edge"], "results": []}))''',
                "code_lines": """1. `classify` 的返回类型是 `Command`，不是 dict——它同时携带更新与去向。
2. `Command(update=..., goto=...)` 里 `update` 和普通返回值一样会被合并进状态。
3. `goto` 直接写节点名，不需要再声明条件边。
4. 图结构导出只有 `__start__ -> classify`：`Command` 指定的走向对结构不可见。
5. `dispatch` 返回一个 `Send` 列表，每个元素带一个 `topic`。
6. `add_node("work", work, input_schema=TaskState)` 告诉框架：这个节点只吃 `TaskState` 的字段。
7. `results` 用 `Annotated[..., operator.add]` 声明累加，否则三个并行分支会触发冲突报错。""",
                "output": """# 程序输出
=== Command 路由 ===
  给我一段代码     -> kind=code     给你一段示例代码
  解释一下概念     -> kind=concept  用一句话解释这个概念
  图结构里能看到 classify 的出边吗：
    __start__  -> classify
    classify   -> __end__

=== Send 并行分发 ===
   {'topics': ['State', 'Node', 'Edge'], 'results': ['State 已处理', 'Node 已处理', 'Edge 已处理']}""",
                "mistakes": """- 用 `Command` 之后还在父节点上连条件边，两条路径互相打架。
- `goto` 写了一个不存在的节点名，运行时报错。
- `Send` 当普通节点返回值用，报 `InvalidUpdateError: Expected dict`。
- 用了 `Send` 但没写 `input_schema`，被分发节点读不到分发参数。
- 多个 `Send` 分支写同一个键却没声明 reducer，跑起来就冲突。""",
                "error_analysis": """`InvalidUpdateError: Expected dict, got [Send(...)]`
—— `Send` 只能从条件边的路由函数返回，不能当节点返回值。

被分发节点报 `KeyError`
—— 没声明 `input_schema`，节点收到的是父状态而不是 `Send` 的参数。

`InvalidUpdateError: At key 'xxx': Can receive only one value per step`
—— 并行分支写同一个键。用 `Annotated` 声明 reducer。""",
                "beginner_practice": """1. 把 `classify` 的 `Command` 改成「返回 dict + 条件边」，对比图结构导出的差别。
2. 给 `dispatch` 的 `topics` 加一个重复项，观察结果里是否出现重复。""",
                "advanced_practice": """设计一个「先分发给 3 个检索器、再汇总」的流程，比较「用 Send + reducer」与
「各写各的键 + 汇聚节点」两种方案，说明什么情况下必须用前者。""",
                "quiz_note": "本节 6 道题：2 道基础理解（Command 的作用、Send 的分发语义）+ 2 道代码阅读（读结构导出、读 Send 报错）+ 2 道应用练习（改写路由方式、选择并行方案）。",
                "summary": """`Command` 把「改什么」和「去哪」写在一起，代价是结构不可见。
`Send` 做并行分发，必须配 `input_schema` 与 reducer。
条件边适合「路由逻辑独立可测」，`Command` 适合「走向由节点内部强决定」。""",
                "next_lesson": "下一章讲循环：有了路由能力，怎么写出不会停不下来的环。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-13-02",
                        "name": "Command 跳转与 Send 并行分发",
                        "goal": "能用 Command 让节点自决去向，用 Send 分发并行任务。",
                        "minutes": 40,
                        "criteria": "能说明 Command 的结构可见性代价，以及 Send 需要 input_schema 与 reducer 的原因。",
                        "requires": ["langgraph-agent-13-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-13-02-1",
                        "kp": 0,
                        "title": "改成条件边",
                        "description": "把 `classify` 的 `Command` 写法改成「节点返回 dict + 条件边」，保持行为一致。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def classify(state: State) -> dict:
    return {"kind": "code" if "代码" in state["question"] else "concept"}


def route(state: State) -> str:
    return state["kind"]


builder.add_node("classify", classify)
builder.add_conditional_edges(
    "classify", route, {"code": "write_code", "concept": "explain"}
)''',
                        "explanation": "改完之后图结构里能看到两条出边，代价是多了一个路由函数、走向和节点被拆到两处。",
                    },
                    {
                        "code": "lg-ex-13-02-2",
                        "kp": 0,
                        "title": "什么时候必须用 Send",
                        "description": "「根据用户选中的 N 个章节，各生成一段摘要」应该用 Send 还是普通循环节点？",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": """用 Send。

关键判据是「任务数量在运行时才知道，且彼此独立、可以并行」。Send 能把 N 个任务同时发出去，
用 `input_schema` 让每个分支只看到自己那份参数，再用 reducer 把结果汇总。

普通循环节点也能做，但它是串行的：N 个章节就等 N 次调用时间；而且循环内部要自己维护
「第几个了」的游标，一旦中途失败，重试边界很难划清。

什么时候不用 Send：任务之间有依赖（后一个要用前一个的结果），或者必须严格串行以控制速率。""",
                        "explanation": "「数量运行时才定 + 彼此独立」是并行的两个前提，缺一个就应该串行。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-13-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`Command(update=..., goto=...)` 里 `goto` 的作用是？",
                        "options": [
                            ("A", "更新状态"),
                            ("B", "指定下一站节点"),
                            ("C", "结束流程"),
                            ("D", "记录日志"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`update` 负责改状态，`goto` 负责指定去向，两者可以同时给。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-13-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "用 `Command` 指定走向后，图结构导出里能看到对应的边。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`Command` 的走向是运行期决定的，结构导出里看不到——这是它最主要的代价。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-13-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "结构导出只有 `__start__ -> classify`，说明什么？",
                        "options": [
                            ("A", "图编译失败"),
                            ("B", "`classify` 的出边由 `Command` 在运行期决定，结构里没有声明"),
                            ("C", "`write_code` 没注册"),
                            ("D", "边被自动删除"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "两个后继节点都注册了，但没有任何静态边指向它们；走向藏在 `Command` 里。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-13-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`Send(\"work\", {\"topic\": topic})` 的第二个参数是什么？",
                        "options": [
                            ("A", "给 `work` 节点的输入"),
                            ("B", "状态增量"),
                            ("C", "节点名"),
                            ("D", "日志内容"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "它是该分支节点的输入，配合 `input_schema` 声明才能被正确接收。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-13-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么用了 `Send` 就几乎一定要配 reducer？",
                        "options": [],
                        "answer": """因为 `Send` 的本质是「同一节点并行执行多次」，而这些分支通常都要把结果写回同一个字段（例如 `results`）。

默认合并规则是「同一步只能有一个值」，多个分支同时写就会抛 `InvalidUpdateError`。要让它们能共存，必须声明「多个值怎么合成一个」——也就是 reducer。

如果各分支写不同字段，确实可以不配 reducer，但那样通常说明你不需要 `Send`：各写各的字段用普通并行分支就够了。""",
                        "explanation": "`Send` 与 reducer 是一对：前者制造并发写入，后者解决并发写入。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-13-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "用 `Send` 实现「把一句话分给 2 个改写器并行处理」，要求结果用 `rewrites` 字段累加。写出状态与分发函数。",
                        "options": [],
                        "answer": {"value": "class FanState(TypedDict):\n    text: str\n    rewrites: Annotated[list[str], operator.add]\n\n\nclass TaskState(TypedDict):\n    text: str\n    style: str\n    rewrites: list[str]\n\n\ndef dispatch(state: FanState):\n    return [Send(\"rewrite\", {\"text\": state[\"text\"], \"style\": s}) for s in (\"简洁\", \"正式\")]\n\n\nfan.add_node(\"rewrite\", rewrite, input_schema=TaskState)\nfan.add_conditional_edges(START, dispatch)"},
                        "explanation": "父状态负责汇总（`rewrites` 用 reducer），子输入携带每个分支自己的参数（`style`），两层职责分开。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 14 章
    {
        "code": "langgraph-agent-14",
        "order_index": 14,
        "title": "循环和流程控制",
        "description": "写循环必须写出口，还要知道步数上限。",
        "lessons": [
            {
                "code": "langgraph-agent-14-lesson-01",
                "title": "循环、终止条件与上限",
                "objectives": """1. 能用条件边构造一个带出口的循环；
2. 能解释 `recursion_limit` 计的是什么、默认值是多少含义；
3. 能在循环里安全地累加状态而不重复；
4. 能设计「双重保险」：业务出口 + 步数上限。""",
                "why_learn": """Agent 的核心机制就是循环。不写出口会死循环，只靠上限会让每次运行都跑满，
既慢又烧钱。两种保险缺一不可。""",
                "concepts": """**回边**：从后面的节点连回前面的节点，形成循环。
**业务出口**：状态满足某个条件时跳出循环（例如「已完成」）。
**步数上限**：`recursion_limit`，配置在 `config` 里，超过就抛 `GraphRecursionError`。
**计数放在状态里**：用状态字段记录已跑几轮，退出条件才可判断。
**幂等**：循环里重复执行的节点不能重复写同一份数据。""",
                "plain": """循环像洗衣机：设定「洗到水变清」是业务出口，「最多洗 40 分钟」是保险。
只设业务出口，遇到永远洗不清的情况就转到天亮；只设时间上限，每次都要转满 40 分钟才停。
两个都设，才是既正确又省电的做法。""",
                "syntax": """**循环结构**

```python
def work(state): ...           # 做事，并把进度写进状态
def route(state):              # 判断是否该继续
    return "end" if state["done"] else "again"

builder.add_edge(START, "work")
builder.add_conditional_edges("work", route, {"again": "work", "end": END})
```

**上限**

```python
graph.invoke(state, {"recursion_limit": 20})
```

- 默认上限是 25 步，超过抛 `GraphRecursionError`。
- 上限按「超步」计，一次节点执行算一步。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    count: int
    done: bool


def work(state: State) -> dict:
    nxt = state["count"] + 1
    print(f"  第 {nxt} 次执行 work")
    return {"count": nxt, "done": nxt >= 3}


def route(state: State) -> str:
    return "end" if state["done"] else "again"


builder = StateGraph(State)
builder.add_node("work", work)
builder.add_edge(START, "work")
builder.add_conditional_edges("work", route, {"again": "work", "end": END})
graph = builder.compile()

print("=== 带出口的循环 ===")
print("  结果：", graph.invoke({"count": 0, "done": False}))

print()
print("=== 同样的图，上限调到 2 ===")
try:
    graph.invoke({"count": 0, "done": False}, {"recursion_limit": 2})
except Exception as exc:
    print("  ", type(exc).__name__, ":", str(exc).splitlines()[0][:120])''',
                "code_lines": """1. `work` 每次把 `count` 加一并重算 `done`，进度就在状态里。
2. `route` 只读 `done`，不关心执行了几次——出口条件是业务语义，不是计数。
3. `add_conditional_edges` 把 `again` 指回 `work` 自己，这就是回边。
4. 第一次运行打印 3 行，第 3 次 `done` 为真，走 `end` 到 `END`。
5. 第二次运行把 `recursion_limit` 设为 2，只能跑 2 步。
6. 第 2 步之后仍想继续，触发 `GraphRecursionError`，提示可以调高上限。
7. 两次运行对比说明：业务出口决定「正常要几轮」，上限决定「最多允许几轮」。""",
                "output": """# 程序输出
=== 带出口的循环 ===
  第 1 次执行 work
  第 2 次执行 work
  第 3 次执行 work
  结果： {'count': 3, 'done': True}

=== 同样的图，上限调到 2 ===
  第 1 次执行 work
  第 2 次执行 work
   GraphRecursionError : Recursion limit of 2 reached without hitting a stop condition. You can increase the limit by setting the `recursion_limi""",
                "mistakes": """- 回边连回去但路由函数永远返回 `again`，跑到上限才停。
- 只用上限当出口，每次运行都跑满，延迟和费用都被放大。
- 循环里 `append` 到不判重的列表，结果里同一个值出现好几遍。
- 把计数放在闭包变量里而不是状态里，并行或恢复时直接错乱。
- 上限设得太小，正常流程被误杀，报错信息还看不出是真出错。""",
                "error_analysis": """`GraphRecursionError: Recursion limit of N reached`
—— 要么出口条件没生效，要么上限太小。先确认后者：正常流程需要几步？

结果里出现重复项
—— 循环里每次都在追加同一内容。改成「先判断是否已存在」。

循环次数每次都等于上限
—— 路由函数没读状态，或读了一个永远不变的字段。打印路由函数的入参核对。""",
                "beginner_practice": """1. 把出口条件改成 `nxt >= 5`，观察打印次数与最终 `count`。
2. 把 `recursion_limit` 设为 10，确认正常流程能跑完。""",
                "advanced_practice": """给循环加一个「连续两次结果相同就跳出」的保护（避免模型反复给出同一答案），
说明这个判断该放在节点里还是路由函数里，以及为什么。""",
                "quiz_note": "本节 6 道题：2 道基础理解（业务出口与上限的区别、上限计什么）+ 2 道代码阅读（读循环次数、读报错）+ 2 道应用练习（改出口、加防重）。",
                "summary": """循环 = 回边 + 业务出口；上限是第二道保险，不是替代品。
`recursion_limit` 按步数计，超了抛 `GraphRecursionError`。
进度写进状态，出口条件才有依据。""",
                "next_lesson": "下一章讲 Reducer：并行与累积场景下的状态合并规则。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-14-01",
                        "name": "循环构造、终止条件与步数上限",
                        "goal": "能写出带业务出口与步数上限的循环，并排查不终止问题。",
                        "minutes": 35,
                        "criteria": "能说明业务出口与上限各自的职责，并在循环中安全累加状态。",
                        "requires": ["langgraph-agent-13-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-14-01-1",
                        "kp": 0,
                        "title": "加一个防重复",
                        "description": "循环里每次都想往 `seen` 列表追加 `count`，要求不出现重复值。写出节点改动。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def work(state: State) -> dict:
    nxt = state["count"] + 1
    seen = state.get("seen", [])
    if nxt not in seen:
        seen = [*seen, nxt]
    return {"count": nxt, "done": nxt >= 3, "seen": seen}''',
                        "explanation": "循环里写列表必须先判重，否则重试或回边会把同一项加多次。",
                    },
                    {
                        "code": "lg-ex-14-01-2",
                        "kp": 0,
                        "title": "上限该设多少",
                        "description": "一个「检索→判断是否够用→不够再检索」的循环，`recursion_limit` 该怎么定？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """按「最坏情况的步数 × 安全系数」定，并在业务出口里也设一个轮次上限。

具体：如果最多检索 3 轮，每轮 2 步（检索 + 判断），最坏 6 步，再加上前后处理约 10 步。
那么 `recursion_limit` 设 15—20 比较合适，既不会误杀正常流程，也不会让异常情况跑到很久。

更重要的是同时在状态里加 `rounds` 字段，达到 3 轮就主动降级输出「资料不足」。
这样正常路径由业务出口结束，上限只负责兜住真正的异常——不会出现「每次都跑满上限」的情况。""",
                        "explanation": "上限是兜底，不该成为常规出口；两者职责分开，日志里才能区分「正常结束」与「超限」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-14-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`recursion_limit` 计的是什么？",
                        "options": [
                            ("A", "重试次数"),
                            ("B", "执行的超步数（约等于节点执行次数）"),
                            ("C", "并发数"),
                            ("D", "返回的字符数"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它按执行步数计，超了就抛 `GraphRecursionError`，是防死循环的第二道保险。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-14-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只要设了 `recursion_limit`，就不需要业务出口了。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "上限只保证会停，不保证停得对。没有业务出口，每次都会跑满上限，既慢又贵。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-14-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第一次运行打印了几行「第 N 次执行 work」？",
                        "options": [
                            ("A", "1"),
                            ("B", "2"),
                            ("C", "3"),
                            ("D", "4"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "第 3 次时 `nxt >= 3` 成立，`done` 为真，路由走 `end`，所以正好 3 次。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-14-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "上限设为 2 时，最终返回值是什么？",
                        "options": [
                            ("A", "`{'count': 2, 'done': False}`"),
                            ("B", "抛 `GraphRecursionError`，没有返回值"),
                            ("C", "`{'count': 3, 'done': True}`"),
                            ("D", "`None`"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "达到上限时直接抛异常中断，调用方拿不到状态——这也是为什么要把上限设得合理，别让它成为常规路径。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-14-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么循环里的进度必须写在状态里，而不能用闭包或全局变量？",
                        "options": [],
                        "answer": """三个原因：

① 状态是唯一能在节点之间传递的东西。闭包变量只有定义它的函数能看到，别的节点读不到，路由函数也就无法判断进度。
② 状态会被持久化。一旦开启检查点，恢复时能拿回的是状态，闭包变量在进程重启后就没了。
③ 状态是可观测的。日志、调试、人工修正都依赖「当前进度」这个字段，藏在闭包里等于把它藏起来。

反过来说，凡是「用来决定下一步」的信息，都必须进状态。""",
                        "explanation": "「会不会被多个节点读到、能不能被持久化」是判断一个值该不该进状态的标准。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-14-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给循环加「最多 2 轮」的业务出口：超过 2 轮无论 `done` 如何都走 `give_up`。写出路由函数与边。",
                        "options": [],
                        "answer": {"value": "def route(state: State) -> str:\n    if state[\"count\"] >= 2:\n        return \"give_up\"\n    return \"again\" if not state[\"done\"] else \"end\"\n\n\nbuilder.add_conditional_edges(\n    \"work\", route, {\"again\": \"work\", \"end\": END, \"give_up\": \"give_up\"}\n)\nbuilder.add_edge(\"give_up\", END)"},
                        "explanation": "把「轮次上限」写成显式分支，能区分「正常完成」与「达到上限降级」，日志和用户提示都能分开处理。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ---------------------------------------------------------------- 第 15 章
    {
        "code": "langgraph-agent-15",
        "order_index": 15,
        "title": "Reducer",
        "description": "覆盖会把并行结果吞掉，reducer 负责合并。",
        "lessons": [
            {
                "code": "langgraph-agent-15-lesson-01",
                "title": "为什么需要 reducer",
                "objectives": """1. 能复现「多个值写同一个键」导致的报错；
2. 能解释 reducer 的输入输出签名；
3. 能说明「同一节点循环写一个键」为什么也需要 reducer；
4. 能判断哪些字段需要 reducer、哪些不需要。""",
                "why_learn": """第 12 章看到过并行冲突的报错，这一节给出解法。
不声明 reducer，你的图一旦加并行或加循环，就只能靠「各写各的键」绕，状态会越拆越碎。""",
                "concepts": """**reducer**：一个二元函数 `(旧值, 新值) -> 合并值`，声明在字段的类型标注里。
**默认行为**：没有 reducer 时，同一步只能收到一个值，多于一个就报错。
**`Annotated[类型, 函数]`**：把 reducer 绑在字段上。
**并行场景**：多个分支写同一个键，必须有 reducer 才能合并。
**顺序语义**：`operator.add` 的合并顺序取决于完成顺序，不适合有强序要求的场景。""",
                "plain": """默认合并规则是「这一格只能填一次」。
两个人同时来填，登记员只能拒收——他不是懒，是没法决定留谁的字。
reducer 就是提前告诉登记员「如果有多份，按这个规则合起来」：
排队接在后面（`operator.add`）、或者只保留不重复的（去重函数）。""",
                "syntax": """**声明 reducer**

```python
import operator
from typing import Annotated, TypedDict

class State(TypedDict):
    results: Annotated[list[str], operator.add]
```

- reducer 签名：两个参数（旧值、新值），返回合并后的值。
- 返回值会替换旧值，所以累加语义要自己写全（`left + right`）。
- 没有 reducer 的字段，同一步被写两次就报错。""",
                "example_code": '''import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class BadState(TypedDict):
    topic: str
    results: list[str]


class GoodState(TypedDict):
    topic: str
    results: Annotated[list[str], operator.add]


def branch_a(state: TypedDict) -> dict:
    return {"results": ["A 的检索结果"]}


def branch_b(state: TypedDict) -> dict:
    return {"results": ["B 的检索结果"]}


def build(schema):
    builder = StateGraph(schema)
    builder.add_node("a", branch_a)
    builder.add_node("b", branch_b)
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_edge("a", END)
    builder.add_edge("b", END)
    return builder.compile()


print("=== 没有 reducer ===")
try:
    print("  ", build(BadState).invoke({"topic": "x", "results": []}))
except Exception as exc:
    print("  ", type(exc).__name__, ":", str(exc).splitlines()[0])

print()
print("=== 声明 operator.add 之后 ===")
print("  ", build(GoodState).invoke({"topic": "x", "results": []}))''',
                "code_lines": """1. `BadState.results` 是普通 `list[str]`，没有任何合并规则。
2. `branch_a` 与 `branch_b` 都从 `START` 出发，构成并行。
3. 两者都返回 `results`，同一步产生两个值。
4. 没有 reducer 时，合并阶段无法决定取谁，抛 `InvalidUpdateError`。
5. `GoodState.results` 用 `Annotated[list[str], operator.add]` 声明了「追加」。
6. 同样的并行结构，声明 reducer 后两个结果被拼成一个列表。
7. 注意顺序是 `A` 在前——这只是本例的完成顺序，不保证永远如此。""",
                "output": """# 程序输出
=== 没有 reducer ===
   InvalidUpdateError : At key 'results': Can receive only one value per step. Use an Annotated key to handle multiple values.

=== 声明 operator.add 之后 ===
   {'topic': 'x', 'results': ['A 的检索结果', 'B 的检索结果']}""",
                "mistakes": """- 加了并行分支就报错，于是删掉一个分支，掩盖了真实需求。
- 给所有字段都加 `operator.add`，结果数字字段被不断累加、字符串被拼接。
- 以为 `operator.add` 有确定顺序，跨请求时结果顺序变化导致断言不稳定。
- 在 reducer 里做副作用（发消息、写库），并发时会重复执行。
- 只给并行场景加 reducer，忘了「同一节点在循环里反复写」也需要。""",
                "error_analysis": """`InvalidUpdateError: At key 'xxx': Can receive only one value per step`
—— 同一步多次写同一个键。加 reducer，或改成各写各的键。

结果里数字越来越大
—— 给计数字段加了 `operator.add`，而节点自己是「先读再加」，等于加了两次。

列表顺序在测试里不稳定
—— `operator.add` 的顺序依赖完成时序。需要稳定顺序时，改成「各写各的键 + 汇聚节点排序」。""",
                "beginner_practice": """1. 把 `GoodState` 的 `results` 改成 `Annotated[list[str], operator.add]` 之外的写法（例如返回整列表），观察差别。
2. 给 `BadState` 加一个 `count: int` 字段并在两个分支里都自增，确认它是否也会报错。""",
                "advanced_practice": """设计一个「合并时要排序」的 reducer（按结果里的分数字段排序），
说明为什么这类有强序要求的合并更适合放在汇聚节点而不是 reducer 里。""",
                "quiz_note": "本节 6 道题：2 道基础理解（reducer 的作用、默认规则）+ 2 道代码阅读（读报错、读合并结果）+ 2 道应用练习（判断该不该加、处理顺序问题）。",
                "summary": """reducer 是「多个值怎么合成一个」的声明。
没有它，同一步写同一个键就报错；有它，并行与循环才能安全累加。
顺序敏感的场景不要依赖 `operator.add` 的完成顺序。""",
                "next_lesson": "下一节看内置的 `add_messages` 和怎么写自己的 reducer。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-15-01",
                        "name": "reducer 的作用与声明方式",
                        "goal": "能复现多值写入冲突并用 reducer 解决。",
                        "minutes": 40,
                        "criteria": "能写出 `Annotated[list, operator.add]` 并说明它解决的是哪一步的问题。",
                        "requires": ["langgraph-agent-14-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-15-01-1",
                        "kp": 0,
                        "title": "给计数字段加 reducer 合适吗",
                        "description": "并行两个分支都想给 `total` 加 1，应该加 `operator.add` 吗？",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": """不合适。若两个分支都执行 `return {"total": state["total"] + 1}`，两者读到的都是同一个旧值，
再配合 reducer 会得到 `旧值+1 + 旧值+1`，结果比预期大。

正确写法：让每个分支返回「自己的增量」`return {"total": 1}`，由 reducer 累加：

class State(TypedDict):
    total: Annotated[int, operator.add]""",
                        "explanation": "reducer 负责合并，节点只该返回「本次增量」。节点自己先读再加，等于把合并做了两遍。",
                    },
                    {
                        "code": "lg-ex-15-01-2",
                        "kp": 0,
                        "title": "顺序能保证吗",
                        "description": "`operator.add` 合并出的列表顺序，是否等于节点定义的先后顺序？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """不保证。顺序取决于各分支实际的完成顺序，而并行执行的完成顺序受网络、调度影响。

因此：① 测试里不要断言列表顺序，或者先排序再断言；② 业务流程如果依赖顺序（例如「先检索再摘要」），就不该并行，应该用普通边串起来；③ 需要稳定顺序又要并行时，让每个分支返回带序号的结果，在汇聚节点统一排序。""",
                        "explanation": "并行 = 放弃顺序保证。需要顺序就串行，或者在合并时显式排序。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-15-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "reducer 的签名是？",
                        "options": [
                            ("A", "`(state) -> dict`"),
                            ("B", "`(旧值, 新值) -> 合并值`"),
                            ("C", "`(新值) -> 旧值`"),
                            ("D", "`() -> 默认值`"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "两个入参一个返回值：拿到旧值与本次新值，返回合并后的结果。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-15-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只有并行分支才需要 reducer，循环里不需要。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "循环里同一节点反复写同一键，同样属于「同一步多值」问题，也需要 reducer 才能累加。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-15-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`BadState` 报错发生在什么阶段？",
                        "options": [
                            ("A", "编译时"),
                            ("B", "两个分支执行完、合并结果时"),
                            ("C", "第一个分支执行时"),
                            ("D", "`invoke` 返回后"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "两个分支都执行完，合并阶段发现同一个键有两个值，才报错。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-15-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`GoodState` 的结果为什么是两个元素？",
                        "options": [
                            ("A", "节点各执行了两次"),
                            ("B", "`operator.add` 把两个列表拼接了"),
                            ("C", "初始值里本来有两个"),
                            ("D", "框架自动补了一个"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`operator.add` 对列表就是拼接：旧列表 + 新列表，两个分支各贡献一个元素。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-15-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "哪些字段需要 reducer？给出两条判断标准。",
                        "options": [],
                        "answer": """① 「多个来源可能同时写它」的字段需要。典型是并行分支的结果列表、循环里的历史记录。
② 「语义上是累积的」字段需要，例如消息历史、已检索来源、执行轨迹。

反过来，以下不需要：单写者的字段（只有一个节点写它）、要求「整值替换」的字段（例如当前状态枚举、最新答案）。给后者加 `operator.add` 会得到荒诞结果——字符串被拼接、状态码被累加。""",
                        "explanation": "判断标准是「谁会写」和「语义是否累积」，不是「是不是列表」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-15-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给 `latency_ms` 字段声明一个 reducer，使多个分支的耗时相加。写出字段声明。",
                        "options": [],
                        "answer": {"value": "class State(TypedDict):\n    latency_ms: Annotated[int, operator.add]\n\n# 各分支只返回自己的增量\ndef branch_a(state: State) -> dict:\n    return {\"latency_ms\": 12}"},
                        "explanation": "耗时天然可加，但分支必须返回「自己的耗时」而不是「累计值」，否则会重复累加。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-15-lesson-02",
                "title": "内置与自定义 reducer",
                "objectives": """1. 能用 `operator.add` 实现列表与数字的累加；
2. 能用 `add_messages` 管理消息历史，并知道它会把裸字符串转成消息；
3. 能写一个自定义 reducer 实现「追加去重」；
4. 能说明 reducer 应该是纯函数、且不能做副作用。""",
                "why_learn": """`add_messages` 是 Agent 里最常用的 reducer，但它有隐含行为；
自定义 reducer 则是处理「去重」「按 key 合并」的唯一手段。""",
                "concepts": """**`operator.add`**：通用累加，列表拼接、数字相加。
**`add_messages`**：专用于消息列表，支持按 id 更新或删除。
**隐含转换**：`add_messages` 会把裸字符串转成 `HumanMessage`，容易造成意外。
**自定义 reducer**：普通二元函数即可，适合去重、按 key 覆盖等。
**纯函数要求**：reducer 会被调用多次，不能在里面写库、发消息。""",
                "plain": """`operator.add` 是「接在后面」，最朴素。
`add_messages` 是「带编号的接龙」：同编号的会替换，新的追加，还能标记删除。
自己写的 reducer 则是按你的业务规矩来：重复的不加、同 key 的覆盖。
三种都要，取决于这一列到底在记什么。""",
                "syntax": """**三种写法**

```python
import operator
from typing import Annotated
from langgraph.graph.message import add_messages

class State(TypedDict):
    tags: Annotated[list[str], merge_unique]     # 自定义
    plain: list[str]                             # 无 reducer
    history: Annotated[list, add_messages]       # 内置
```

- 自定义 reducer 就是普通函数：`def merge(old, new) -> merged`。
- `add_messages` 会规范化元素类型，裸字符串变成 `HumanMessage`。
- reducer 必须返回合并后的完整值，不能原地修改。""",
                "example_code": '''import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


def merge_unique(left: list[str], right: list[str]) -> list[str]:
    """自定义 reducer：追加但去重。"""
    result = list(left)
    for item in right:
        if item not in result:
            result.append(item)
    return result


class State(TypedDict):
    tags: Annotated[list[str], merge_unique]
    plain: list[str]
    history: Annotated[list, add_messages]


def add_tags(state: State) -> dict:
    return {"tags": ["python", "graph"], "plain": ["python", "graph"]}


def add_more(state: State) -> dict:
    return {"tags": ["graph", "agent"], "plain": ["graph", "agent"]}


builder = StateGraph(State)
builder.add_node("first", add_tags)
builder.add_node("second", add_more)
builder.add_edge(START, "first")
builder.add_edge("first", "second")
builder.add_edge("second", END)
graph = builder.compile()

out = graph.invoke({"tags": [], "plain": [], "history": [HumanMessage("你好")]})
print("自定义去重 reducer：", out["tags"])
print("同结构但无 reducer：", out["plain"])
print()

print("=== add_messages 的行为 ===")
out2 = graph.invoke({
    "tags": [],
    "plain": [],
    "history": [HumanMessage("你好"), AIMessage("在的"), "裸字符串会被当成什么？"],
})
for index, message in enumerate(out2["history"]):
    print(f"  {index}: {type(message).__name__} {message.content!r}")''',
                "code_lines": """1. `merge_unique` 是普通函数，两个参数一个返回值，可直接单元测试。
2. `list(left)` 先复制，保证不修改旧值——reducer 也必须是纯函数。
3. `tags` 用自定义 reducer：`graph` 出现两次，去重后只剩一份。
4. `plain` 没有 reducer：第二个节点把第一个节点的结果整组覆盖。
5. `history` 用 `add_messages`，初始给一条 `HumanMessage`。
6. 传入裸字符串时，`add_messages` 把它转成 `HumanMessage`——这是它的隐含行为。
7. 最终历史共 3 条，顺序与传入顺序一致。""",
                "output": """# 程序输出
自定义去重 reducer： ['python', 'graph', 'agent']
同结构但无 reducer： ['graph', 'agent']

=== add_messages 的行为 ===
  0: HumanMessage '你好'
  1: AIMessage '在的'
  2: HumanMessage '裸字符串会被当成什么？'""",
                "mistakes": """- 自定义 reducer 里直接 `left.append(...)` 再返回 `left`，修改了旧值。
- 以为 `add_messages` 只接受消息对象，实际裸字符串也会被转换，导致历史里多出 `HumanMessage`。
- 给字符串字段加了 `operator.add`，结果变成了拼接。
- 在 reducer 里发通知或写日志，被调用多次时重复触发。
- reducer 里抛异常没有兜底，整个合并阶段失败。""",
                "error_analysis": """合并后旧数据丢了
—— reducer 返回了新值但没包含旧值（忘了 `left + right`）。

消息历史出现意外的 `HumanMessage`
—— 代码里传了裸字符串而不是 `AIMessage`。用 `add_messages` 时显式构造消息对象。

`TypeError: unsupported operand type(s) for +`
—— `operator.add` 用在了不支持相加的类型上（例如 dict）。改用自定义 reducer。""",
                "beginner_practice": """1. 把 `merge_unique` 改成「保留最新 3 条」，观察 `tags` 长度。
2. 给 `plain` 也加上 `merge_unique`，确认两个字段结果一致。""",
                "advanced_practice": """写一个「按 id 覆盖」的 reducer（同 id 替换、新 id 追加），
说明它和 `add_messages` 的行为有什么异同，以及什么时候需要自己实现。""",
                "quiz_note": "本节 6 道题：2 道基础理解（三种 reducer 的适用面、纯函数要求）+ 2 道代码阅读（读去重结果、读消息转换）+ 2 道应用练习（改写 reducer、选对类型）。",
                "summary": """`operator.add` 通用、`add_messages` 专用于消息、自定义 reducer 处理业务规则。
reducer 必须纯：不改旧值、不做副作用、返回完整合并结果。
`add_messages` 会转换裸字符串，传消息时显式构造对象。""",
                "next_lesson": "下一章接入大模型：把模型调用放进节点里。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-15-02",
                        "name": "内置与自定义 reducer 的写法",
                        "goal": "能选用合适的 reducer，并写出纯函数的自定义合并逻辑。",
                        "minutes": 40,
                        "criteria": "能写出追加去重的 reducer，并说明 `add_messages` 的规范化行为。",
                        "requires": ["langgraph-agent-15-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-15-02-1",
                        "kp": 0,
                        "title": "保留最新 N 条",
                        "description": "写一个 reducer，只保留最新的 3 条记录（旧的丢弃）。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def keep_last_three(left: list[str], right: list[str]) -> list[str]:
    return (list(left) + list(right))[-3:]''',
                        "explanation": "先拼接再取尾部，逻辑简单且不修改入参。这类「有界累积」适合日志、轨迹类字段，能防止状态无限膨胀。",
                    },
                    {
                        "code": "lg-ex-15-02-2",
                        "kp": 0,
                        "title": "reducer 能有副作用吗",
                        "description": "在 reducer 里打印一条日志，会有什么问题？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """打印本身危害不大，但它暴露了一个危险习惯：reducer 会被调用多次。

真实问题出现在有实际副作用时：① 发通知会重复发送；② 写库会写入多条；③ 调用计数会多算。
更隐蔽的是，reducer 的调用次数依赖内部实现（合并路径可能不同），你无法假设「一定调用一次」。

所以规则是：reducer 只做「纯计算」，日志放到节点里打。""",
                        "explanation": "判断副作用能否放进某个位置，先问「它会被执行几次，我能不能确定」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-15-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`add_messages` 最适合用在哪种字段？",
                        "options": [
                            ("A", "计数器"),
                            ("B", "消息历史"),
                            ("C", "当前状态枚举"),
                            ("D", "配置项"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它专为消息列表设计，支持按 id 更新与删除，计数器或枚举用它会出错。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-15-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "自定义 reducer 可以原地修改旧值再返回，只要能拿到正确结果。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "原地修改会污染旧快照，导致历史状态被改写、回放不一致。reducer 必须返回新值。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-15-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`tags` 结果是 3 个元素而 `plain` 只有 2 个，原因是？",
                        "options": [
                            ("A", "`tags` 有去重 reducer，`plain` 被覆盖"),
                            ("B", "`tags` 执行了两次"),
                            ("C", "`plain` 字段没声明"),
                            ("D", "顺序不同"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`tags` 把两次结果合并去重得到 3 个；`plain` 没有 reducer，第二次整组覆盖只剩 2 个。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-15-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "裸字符串进入 `history` 后变成了什么类型？",
                        "options": [
                            ("A", "`str`"),
                            ("B", "`HumanMessage`"),
                            ("C", "`AIMessage`"),
                            ("D", "`ToolMessage`"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`add_messages` 会把非消息对象规范化为 `HumanMessage`，这是它的隐含行为，容易造成意外。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-15-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说 reducer 是「状态约定」而不是「节点逻辑」？",
                        "options": [],
                        "answer": """因为 reducer 声明在状态字段上，对所有写这个字段的节点一视同仁。

它回答的是「这个字段允许多少种写法的合并」，而不是「某个节点要怎么算」。节点只负责产出增量，合并规则由状态统一约束。

这个位置很重要：如果合并规则写在节点里，两个节点各自维护一套，早晚不一致；写在状态上，就变成了全局唯一的约定，改一处即全局生效，也便于审阅。""",
                        "explanation": "「约束放在数据结构上，而不是散在逻辑里」是减少不一致的通用手段。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-15-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个按 id 覆盖的 reducer：同 id 用新值替换，新 id 追加。",
                        "options": [],
                        "answer": {"value": "def upsert_by_id(left: list[dict], right: list[dict]) -> list[dict]:\n    merged = {item[\"id\"]: item for item in left}\n    for item in right:\n        merged[item[\"id\"]] = item\n    return list(merged.values())"},
                        "explanation": "用字典按 id 归并，天然实现「同 id 覆盖、新 id 追加」。这也是 `add_messages` 内部思路的简化版。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
