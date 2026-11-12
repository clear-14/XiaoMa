"""LangGraph Agent 开发：第 28 章（综合项目）。

个人 AI 学习 Agent：把前面 27 章用到的零件装成一个能用的东西。
5 个课时对应需求给出的 6 条要求，最后一节用接口与测试收口。

版本口径（实测）：langgraph 1.2.20、langchain-core 1.7.6、fastapi 0.162.0。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 28 章
    {
        "code": "langgraph-agent-28",
        "order_index": 28,
        "title": "综合项目：个人 AI 学习 Agent",
        "description": "把 State、路由、工具、检查点、中断与接口装成一个能用的学习助手。",
        "lessons": [
            {
                "code": "langgraph-agent-28-lesson-01",
                "title": "需求拆解与图设计",
                "objectives": """1. 能把六条需求逐条映射到节点、边与装配项；
2. 能画出「先分类、再分支」的主干，并说明每条支路的终止条件；
3. 能判断哪些步骤该合并成一个节点、哪些必须拆开；
4. 能写出可编译的骨架图，先跑通结构再填实现。""",
                "why_learn": """直接开写代码，很容易变成「一个巨大节点干了所有事」。
先画图、再写代码，能提前发现「这条分支没有出口」「这个状态字段没人写」这类结构问题。""",
                "concepts": """**六条需求的落点**：识别问题 → `classify`；读资料 → `retrieve` / `read_chapter`；调工具 → 只读工具白名单；存状态 → 检查点；选流程 → 条件边；对外 → 接口层。
**主干形状**：`START → classify → (分支) → END`。
**分支设计**：概念与章节各走一条检索支路，进度直接回答，记笔记进审批。
**节点粒度**：一件事一个节点；「检索」与「读某一章」行为不同，就分成两个。
**骨架优先**：先让图编译通过、能跑通空实现，再逐个填内容。""",
                "plain": """这一步看起来很「文档」，其实是整个项目最省钱的一步。

先在纸上把事情拆成「谁做什么」：谁负责判断问题类型、谁负责找资料、谁负责组织语言、谁负责等人点头。
拆完你就有了一张表，每一行对应一个节点，节点之间的箭头就是边。

拆完再问三个问题。第一个：每条支路最后都能走到 `END` 吗？第二个：每个状态字段都有人写、
也有人读吗？第三个：有没有哪个节点同时在干两件不相关的事？

这三个问题在代码里很难看出来，在图上很显眼。示例里我先把节点职责、路由表打印出来，
再编译一个「空实现」的骨架——它能跑通，但每个节点都返回固定值。

骨架能跑通之后，再一个个把假值换成真实逻辑。顺序反了，你会在一堆真实逻辑里找结构 bug。""",
                "syntax": """**设计表 → 骨架 → 填充**

```python
# 1) 先列表：需求 -> 落点
REQUIREMENTS = [("识别用户问题", "classify：归类"), ...]

# 2) 再定路由表：一个 intent 一个去处
ROUTES = {"concept": "retrieve", "chapter": "read_chapter",
          "progress": "progress", "note": "review"}

# 3) 装配骨架
builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route, ROUTES)
builder.add_edge("retrieve", "answer")
builder.add_edge("answer", END)
```

- 路由表用「短键 → 节点名」，让分类逻辑与节点命名解耦。
- 每个分支节点都要有一条通往 `END` 的边，编译不会替你检查这一点。
- 骨架阶段每个节点先返回固定值，验证结构。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    question: str
    intent: str
    docs: list
    answer: str


REQUIREMENTS = [
    ("识别用户问题", "classify：把问题归到 concept / chapter / progress / note 四类"),
    ("读取课程相关知识", "retrieve：按 intent 检索课程资料，写入 docs"),
    ("调用允许使用的工具", "tools：只挂检索与读取两类只读工具"),
    ("保存对话状态", "compile(checkpointer=...)：按 user_id 建线程"),
    ("根据条件选择工作流", "route：依据 intent 走不同支路"),
    ("通过 FastAPI 提供接口", "answer 之后由接口层返回，写操作经 review 确认"),
]

NODES = {
    "classify": "读 question，判定 intent",
    "retrieve": "按 intent 检索，产出 docs",
    "answer": "读 docs 与历史，产出 answer",
    "review": "写操作前挂起，等人确认",
}

ROUTES = {"concept": "retrieve", "chapter": "retrieve", "progress": "answer", "note": "review"}


def classify(state: State) -> dict:
    q = state["question"]
    if "进度" in q or "学到哪" in q:
        intent = "progress"
    elif "笔记" in q or "记一下" in q:
        intent = "note"
    elif "章" in q:
        intent = "chapter"
    else:
        intent = "concept"
    return {"intent": intent}


def retrieve(state: State) -> dict:
    return {"docs": ["第 6 章 State"]}


def answer(state: State) -> dict:
    return {"answer": "State 是节点之间传递的数据。"}


def review(state: State) -> dict:
    return {"answer": "等待确认"}


def route(state: State) -> str:
    return state["intent"]


print("=== 六个要求怎么落到图上 ===")
for i, (need, how) in enumerate(REQUIREMENTS, 1):
    print(f"{i}. {need:18s} -> {how}")

print()
print("=== 节点职责 ===")
for name, duty in NODES.items():
    print(f"  {name:10s} {duty}")

print()
print("=== 路由表 ===")
for intent, target in ROUTES.items():
    print(f"  intent={intent:9s} -> {target}")

builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("retrieve", retrieve)
builder.add_node("answer", answer)
builder.add_node("review", review)
builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route, ROUTES)
builder.add_edge("retrieve", "answer")
builder.add_edge("answer", END)
builder.add_edge("review", END)
graph = builder.compile()

print()
print("=== 骨架编译 ===")
print("节点:", sorted(graph.get_graph().nodes.keys()))
for question in ("State 是什么", "第 6 章讲什么", "我学到哪了", "帮我记一条笔记"):
    result = graph.invoke({"question": question, "intent": "", "docs": [], "answer": ""})
    print(f"  {question:14s} -> intent={result['intent']:9s} answer={result['answer']}")''',
                "code_lines": """1. `REQUIREMENTS` 是需求表：左边是用户原话，右边是它在图上的落点——这张表后面要对照验收。
2. `NODES` 是职责表：一句话说清每个节点干什么。说不清的节点通常该拆。
3. `ROUTES` 是路由表：`intent` 短键 → 节点名。分类逻辑只产出短键，不直接写节点名。
4. `classify` 用关键词规则代替模型调用，让骨架阶段完全不依赖网络。
5. `route` 只有一行 `return state["intent"]`：它消费分类结论，不做分类。
6. 四个节点都有出口：`retrieve → answer → END`，`review → END`，`progress` 走 `answer`。
7. 骨架能编译、能跑通，但 `retrieve`、`answer` 返回的都是固定假值——这是故意的。
8. 四个问题走完拿到四种 `intent`，说明分类与路由先通了，下一步才换真实现。""",
                "output": """# 程序输出
=== 六个要求怎么落到图上 ===
1. 识别用户问题             -> classify：把问题归到 concept / chapter / progress / note 四类
2. 读取课程相关知识           -> retrieve：按 intent 检索课程资料，写入 docs
3. 调用允许使用的工具          -> tools：只挂检索与读取两类只读工具
4. 保存对话状态             -> compile(checkpointer=...)：按 user_id 建线程
5. 根据条件选择工作流          -> route：依据 intent 走不同支路
6. 通过 FastAPI 提供接口    -> answer 之后由接口层返回，写操作经 review 确认

=== 节点职责 ===
  classify   读 question，判定 intent
  retrieve   按 intent 检索，产出 docs
  answer     读 docs 与历史，产出 answer
  review     写操作前挂起，等人确认

=== 路由表 ===
  intent=concept   -> retrieve
  intent=chapter   -> retrieve
  intent=progress  -> answer
  intent=note      -> review

=== 骨架编译 ===
节点: ['__end__', '__start__', 'answer', 'classify', 'retrieve', 'review']
  State 是什么      -> intent=concept   answer=State 是节点之间传递的数据。
  第 6 章讲什么       -> intent=chapter   answer=State 是节点之间传递的数据。
  我学到哪了          -> intent=progress  answer=State 是节点之间传递的数据。
  帮我记一条笔记        -> intent=note      answer=等待确认""",
                "mistakes": """- 不画图直接写：最后 `answer` 节点涨到 200 行，谁也不敢改。
- 把「检索」和「读某一章」合成一个节点：参数含义不同，代码里到处 `if`。
- 路由函数里做分类：路由变成有副作用的业务代码，无法单测。
- 分支漏了出口：`review` 没连 `END`，流程走到那里就断，编译期不报错。
- 状态字段没人写：`docs` 声明了但 `retrieve` 忘了返回，`answer` 拿到空列表。
- 骨架阶段就接真模型：结构还没定，每改一次边就要跑一次模型，慢且贵。""",
                "error_analysis": """图编译通过但跑起来停在中间
—— 某个节点没有出边。用 `get_graph().nodes` 与 `edges` 对照检查。

`KeyError: 'intent'`
—— 路由表里的键与 `classify` 产出的值不一致，或 `intent` 没在 State 里声明。

`answer` 永远是同一句话
—— 骨架阶段的假值还没替换。这其实是好事：说明结构先跑通了。

流程走不到预期支路
—— 用 `stream_mode="updates"` 打印实际经过的节点，比盯着代码猜快得多。""",
                "beginner_practice": """1. 把 `ROUTES` 里的 `chapter` 改成走一条新节点 `read_chapter`，补上节点与出边，确认仍能跑通。
2. 给 `State` 加一个 `user_id` 字段，思考它该由谁写入。""",
                "advanced_practice": """把这张图拆成「检索子图 + 回答子图」，父图只保留 `classify` 与路由。
说明拆分后哪些状态字段需要在父子之间映射。""",
                "quiz_note": "本节 6 道题：2 道基础理解（六条需求怎么落、为什么要先搭骨架）+ 2 道代码阅读（四个问题为什么拿到四种 intent、`route` 为什么不分类）+ 2 道应用练习（加一条支路、拆子图）。",
                "summary": """先用「需求表 + 节点职责表 + 路由表」把结构定下来。
每个分支都要有通往 `END` 的边，每个状态字段都要有人写、有人读。
骨架能跑通，再替换假实现。""",
                "next_lesson": "结构定了，下一节把假值换成真东西：模型配置与工具白名单。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-28-01",
                        "name": "需求拆解与图设计",
                        "goal": "能把需求映射成节点与边，并写出可编译的骨架。",
                        "minutes": 45,
                        "criteria": "能给出路由表并解释每个分支的出口。",
                        "requires": ["langgraph-agent-27-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-28-01-1",
                        "kp": 0,
                        "title": "补一条支路",
                        "description": "新增需求「查练习」：用户说「有没有练习题」时，走 `quiz` 节点。写出分类规则、节点与边。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''RULES = [("练习", "quiz"), ("进度", "progress"), ("笔记", "note"), ("章", "chapter")]


def quiz(state: State) -> dict:
    return {"answer": "第 6 章有 6 道练习题，其中 2 道代码阅读。"}


builder.add_node("quiz", quiz)
ROUTES["quiz"] = "quiz"
builder.add_edge("quiz", END)

builder.add_conditional_edges("classify", route, ROUTES)''',
                        "explanation": "加一条支路要改三处：分类规则认得出、路由表指得到、节点有出口。少一处就会落到兜底或直接断掉。",
                    },
                    {
                        "code": "lg-ex-28-01-2",
                        "kp": 0,
                        "title": "哪些节点该合并",
                        "description": "「检索资料」和「读某一章」都是取资料，为什么示例把它们分成两个节点？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """因为它们的**输入语义**与**失败方式**不同。

检索：输入是关键词，返回多条候选，可能「没有匹配」。
读章节：输入是精确的章节号，返回一条正文，可能「没有这一章」。

合成一个节点，函数里就得分支判断「这是关键词还是章节号」，还要给两种失败写不同的兜底文案。
结果是：一个函数两个职责，测试要写两套，日志也分不清是哪种失败。

分开之后，每个节点都能用一句话说清职责，也都能单独测。

什么时候可以合并？当两个动作的输入结构、输出结构、失败处理都一致时（比如两个接口都返回同一份
文档列表）。判断标准是「语义」而不是「像不像」。

顺带一条：拆得太碎也不好。如果某个节点只有一行 `return {"x": state["y"]}`，那它不该独立存在。""",
                        "explanation": "节点粒度的标准是「能否用一句话说清职责且能独立测试」，不是越细越好。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-28-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "示例里的 `ROUTES` 表解决什么问题？",
                        "options": [
                            ("A", "决定模型温度"),
                            ("B", "把分类产出的短键映射到具体节点名"),
                            ("C", "定义状态字段类型"),
                            ("D", "控制重试次数"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "分类只产出 `concept` 这类短键，映射表决定它去哪。改节点名时只改表，不动分类逻辑。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "骨架阶段每个节点都返回固定假值，是浪费时间。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它验证的是结构：边接对没、状态字段通不通、分支走不走得到。结构定下来再填实现，返工最少。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "四个问题分别得到 `concept / chapter / progress / note`，说明什么？",
                        "options": [
                            ("A", "模型很强"),
                            ("B", "分类规则按顺序命中，且每个问题都只命中一条"),
                            ("C", "路由表有四个分支"),
                            ("D", "状态被覆盖了四次"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`RULES` 是按顺序判断的，先命中即返回。「帮我记一条笔记」不含「进度」，所以落到 `note`。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "如果把 `builder.add_edge(\"review\", END)` 删掉，会发生什么？",
                        "options": [
                            ("A", "编译报错"),
                            ("B", "编译通过，但流程走到 `review` 后就结束，`answer` 可能是空"),
                            ("C", "自动连到 `answer`"),
                            ("D", "报 `GraphRecursionError`"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "没有出边的节点被视为终点。这类问题编译期不报错，只能靠读图或测试发现。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "骨架阶段该先验证哪三件事？",
                        "options": [],
                        "answer": """① 每条支路都能走到 `END`。没有出边的节点会被当成终点，流程静默断掉，
编译不报错，这类问题最难查。

② 每个状态字段都有人写、也有人读。声明了 `docs` 但没人写，`answer` 就拿到空值；
写了却没人读，说明这个字段多余。

③ 路由表覆盖了分类的所有可能输出。分类可能产出四种 `intent`，路由表就得有四个键，
否则运行到那一条时抛 `KeyError`。

这三件事验证完，这张图的「骨架」就是对的。之后往里填真实逻辑，无论怎么改，
只要不动边与状态结构，行为就不会出结构性问题。""",
                        "explanation": "结构正确性优先于功能正确性——结构错了，功能越对越难改。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-28-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写出「分类 + 路由」的装配代码：`classify` 之后按 `intent` 去四个不同节点，其中两个共用 `retrieve`。",
                        "options": [],
                        "answer": {
                            "value": "ROUTES = {\n    \"concept\": \"retrieve\",\n    \"chapter\": \"read_chapter\",\n    \"progress\": \"progress\",\n    \"note\": \"review\",\n}\n\nbuilder.add_edge(START, \"classify\")\nbuilder.add_conditional_edges(\"classify\", lambda state: state[\"intent\"], ROUTES)\nfor target in set(ROUTES.values()):\n    builder.add_edge(target, END) if target not in {\"retrieve\", \"read_chapter\"} else None\nbuilder.add_edge(\"retrieve\", \"answer\")\nbuilder.add_edge(\"read_chapter\", \"answer\")\nbuilder.add_edge(\"answer\", END)"
                        },
                        "explanation": "关键是「一个键一个去处」，共用的支路靠多个键指向同一节点实现；每个终点都要显式连到 `END`。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-28-lesson-02",
                "title": "模型配置与工具层",
                "objectives": """1. 能把模型配置收在一处，用环境变量管理地址与密钥；
2. 能定义工具白名单，并给参数加「夹紧」这类防御；
3. 能说出「写操作」为什么不放进工具白名单；
4. 能读懂工具 schema，确认模型实际看到什么。""",
                "why_learn": """工具层是这个项目唯一的「对外动作」出口。它写松了，模型一次幻觉就能删数据；
它写紧了，模型又什么都干不了。这条边界必须在代码里划，不能靠提示词。""",
                "concepts": """**配置集中**：`base_url`、`model`、`api_key` 从环境变量读，只在一处构造客户端。
**工具白名单**：`ALLOWED` 字典显式列出可用工具，调用方按名字查，查不到就报错。
**参数防御**：`limit` 这类会放大开销的参数要夹紧（`min/max`），别信调用方。
**只读优先**：检索、读取是只读；写入、删除、发送必须走审批（下一节）。
**schema 检查**：用 `convert_to_openai_tool` 看模型实际收到的描述与必填项。
**描述即权限**：描述里写清「不适用」的场景，减少误调。""",
                "plain": """工具层的设计原则只有一句：**模型只能做你显式允许的事**。

具体落成三件事。第一，工具放在一个白名单字典里，执行时按名字查，查不到就报错——
这比「让模型别乱调」可靠一万倍。

第二，参数要防御。模型会传 `limit=99`，因为它不知道你的库有多贵。夹紧到合理范围，
比在描述里写「请不要超过 3」有效。

第三，写操作不进白名单。删除、扣款、发外部邮件这类动作，必须经过人工确认（下一节），
而不是「模型觉得该做就做」。

最后，别忘了检查模型实际看到什么。用 `convert_to_openai_tool` 把 schema 打出来看一眼，
你会发现有些描述长得超出预期，或者某个参数根本没写说明。""",
                "syntax": """**配置 + 白名单 + 防御**

```python
import os

CONFIG = {
    "base_url": os.environ.get("LLM_BASE_URL", "https://api.example.com/v1"),
    "model": os.environ.get("LLM_MODEL", "chat-small"),
    "api_key": os.environ.get("LLM_API_KEY", ""),
}

@tool
def search_course(keyword: str, limit: int = 3) -> str:
    \"\"\"按关键词检索课程章节。适用于「某概念在哪一章」。\"\"\"
    limit = max(1, min(limit, 3))        # 夹紧
    ...

ALLOWED = {"search_course": search_course, "read_lesson": read_lesson}
```

- 密钥只从环境变量读，不进代码、不进仓库、不进日志。
- 白名单用 `dict`，`ALLOWED[name]` 查不到自然 `KeyError`，这就是「默认拒绝」。
- 写操作不放进 `ALLOWED`，或单独放 `WRITE_TOOLS` 且必须经审批节点。""",
                "example_code": '''from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool


COURSES = {
    "第 6 章": "状态结构：用 TypedDict 声明字段，节点只返回增量。",
    "第 16 章": "接入大模型：模型只是节点里的一次调用。",
    "第 20 章": "Checkpointer：按 thread_id 存每一步的快照。",
}


@tool
def search_course(keyword: str, limit: int = 3) -> str:
    """按关键词检索课程章节，返回命中的章节标题。适用于「某概念在哪一章」。"""
    hits = [f"{k}：{v[:10]}…" for k, v in COURSES.items() if keyword in v or keyword in k]
    limit = max(1, min(limit, 3))          # 参数夹紧：不让调用方放大开销
    return "\\n".join(hits[:limit]) or "没有匹配的章节"


@tool
def read_lesson(chapter: str) -> str:
    """读取某一章的正文摘要。适用于用户明确指定了章节号。"""
    return COURSES.get(chapter, "没有这一章")


ALLOWED = {"search_course": search_course, "read_lesson": read_lesson}
WRITE_TOOLS: set[str] = set()               # 本项目暂不开放写操作

print("=== 白名单里的工具 ===")
for name, fn in ALLOWED.items():
    print(f"  {name:14s} {fn.description[:24]}…")

print()
print("=== 送给模型的工具描述 ===")
for name, fn in ALLOWED.items():
    schema = convert_to_openai_tool(fn)["function"]
    params = list(schema["parameters"]["properties"])
    required = schema["parameters"].get("required", [])
    print(f"  {name:14s} 参数={params} 必填={required}")

print()
print("=== 直接调用 ===")
print("  检索状态：", ALLOWED["search_course"].invoke({"keyword": "状态"}))
print("  读第 20 章：", ALLOWED["read_lesson"].invoke({"chapter": "第 20 章"}))
print("  limit=99 被夹紧：", ALLOWED["search_course"].invoke({"keyword": "章", "limit": 99}).count("\\n") + 1, "条")

print()
print("=== 不在白名单里的名字 ===")
try:
    ALLOWED["delete_all"].invoke({})
except KeyError as exc:
    print("  KeyError:", exc, "（写操作必须先经过审批节点，见 28-4）")''',
                "code_lines": """1. `COURSES` 是一个假数据源。真实项目里换成语料库或数据库查询，接口形状不变。
2. `search_course` 的描述里写了「适用于某概念在哪一章」，这是给模型选工具用的，不是给人看的注释。
3. `limit = max(1, min(limit, 3))` 是参数夹紧：模型传 99 也只返回 3 条，避免一次调用拉爆响应体。
4. `read_lesson` 用 `COURSES.get(..., "没有这一章")` 兜底，不让工具抛异常——异常处理留给 `ToolNode`。
5. `ALLOWED` 是白名单字典，`WRITE_TOOLS` 留空：写操作在这个项目里暂不开放。
6. 打印工具描述时截取前 24 个字符——你能快速确认「模型看到的是不是我想表达的」。
7. schema 打印出参数名与必填项：`limit` 不在必填里，因为它有默认值。
8. 最后一段用 `ALLOWED["delete_all"]` 触发 `KeyError`：白名单之外的名字根本取不到，这是「默认拒绝」。""",
                "output": """# 程序输出
=== 白名单里的工具 ===
  search_course  按关键词检索课程章节，返回命中的章节标题。适用于…
  read_lesson    读取某一章的正文摘要。适用于用户明确指定了章节号…

=== 送给模型的工具描述 ===
  search_course  参数=['keyword', 'limit'] 必填=['keyword']
  read_lesson    参数=['chapter'] 必填=['chapter']

=== 直接调用 ===
  检索状态： 第 6 章：状态结构：用 Typ…
  读第 20 章： Checkpointer：按 thread_id 存每一步的快照。
  limit=99 被夹紧： 3 条

=== 不在白名单里的名字 ===
  KeyError: 'delete_all' （写操作必须先经过审批节点，见 28-4）""",
                "mistakes": """- 把 API Key 写进代码或默认值：跟着仓库泄露，事故级别。
- 把数据库连接、文件删除这类工具直接放进白名单：模型一次幻觉就能造成不可逆损失。
- 相信描述里的「请不要超过 3」：模型不一定遵守，参数必须夹紧。
- 工具内部处理所有异常并返回字符串：`ToolNode` 的错误处理就失效了，模型也分不清成功与失败。
- 工具名取得像函数（`do_search_thing`）：模型选不准，日志也难读。
- 白名单用 `get(name)` 返回 `None` 再继续执行：静默失败，比 `KeyError` 难查得多。""",
                "error_analysis": """`KeyError: 'xxx'`
—— 模型给了白名单外的工具名。这是好事：默认拒绝生效了。可以用 `handle_tool_errors` 把它变成
一条提示消息，让模型自己改（见第 18 章）。

`ValidationError: limit Input should be a valid integer`
—— 模型传了字符串。参数夹紧要放在类型校验之后，或用 pydantic 的 `conint` 约束。

工具返回空字符串
—— 检索没命中。返回「没有匹配」这类明确文案，比空字符串好，模型才知道该换关键词。

密钥相关报错（401）
—— 环境变量没读到。打印配置时务必不要打印密钥本身。""",
                "beginner_practice": """1. 给 `read_lesson` 加一个 `max_chars` 参数并夹紧到 500 以内。
2. 打印 `ALLOWED` 的键，确认写操作不在里面。""",
                "advanced_practice": """设计一个「写工具」的接入方案：怎么标记它是写操作、怎么强制走审批、审批通过后如何执行且不重复执行。""",
                "quiz_note": "本节 6 道题：2 道基础理解（白名单的作用、参数为什么要夹紧）+ 2 道代码阅读（`limit` 为什么不在必填里、`KeyError` 说明什么）+ 2 道应用练习（加参数夹紧、设计写工具接入）。",
                "summary": """配置集中、密钥走环境变量；工具用白名单，默认拒绝。
参数在代码里夹紧，别指望描述能约束模型。
写操作不进白名单，必须走审批。""",
                "next_lesson": "工具有了，下一节让它们真的被动起来：状态设计与条件路由。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-28-02",
                        "name": "模型配置与工具层",
                        "goal": "能搭出配置集中、权限收敛的工具层。",
                        "minutes": 50,
                        "criteria": "能解释白名单与参数夹紧的必要性，并读出工具 schema。",
                        "requires": ["langgraph-agent-28-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-28-02-1",
                        "kp": 0,
                        "title": "给工具加防御",
                        "description": "`read_lesson` 可能返回很长的正文。加 `max_chars` 参数并夹紧到 200—500 之间。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''@tool
def read_lesson(chapter: str, max_chars: int = 200) -> str:
    """读取某一章的正文摘要。适用于用户明确指定了章节号。"""
    text = COURSES.get(chapter, "没有这一章")
    max_chars = max(200, min(max_chars, 500))
    return text[:max_chars]''',
                        "explanation": "夹紧范围取「能读清内容」的下限与「不撑爆上下文」的上限。下限也重要：模型传 1 会得到半句话。",
                    },
                    {
                        "code": "lg-ex-28-02-2",
                        "kp": 0,
                        "title": "写操作为什么不进白名单",
                        "description": "为什么「保存笔记」这类写操作不能像检索一样直接暴露给模型？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """三个原因。

① 不可逆：检索错了只是答案不准，写错了一条笔记、发错了一封邮件是要撤回的。模型没有「后果意识」。

② 不可验证：模型无法判断「这条内容该不该存」。它只知道自己被要求记住点什么，
而用户可能只是在讨论、在假设、在引用别人的话。

③ 需要责任人：写操作要有人签字。出了事能回答「谁批准的」，这是流程要求，不是技术偏好。

正确做法：模型可以提议（生成待写内容），但执行放在审批之后。这也解释了为什么第 22 章的中断
要放在这一章前面——审批依赖中断，中断依赖检查点。

一句话：读操作可以让模型自己决定，写操作必须让人点头。""",
                        "explanation": "权限边界要在代码里划：白名单里没有，模型就调不动，无论它多想调。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-28-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "工具白名单（`ALLOWED` 字典）的核心作用是什么？",
                        "options": [
                            ("A", "让代码更好看"),
                            ("B", "默认拒绝：只有显式列入的工具才能被执行"),
                            ("C", "提高模型调用速度"),
                            ("D", "自动生成工具描述"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "名字不在白名单里就取不到执行体，模型再怎么说也调不动。这是最可靠的权限边界。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "在工具描述里写「limit 请不要超过 3」，模型就一定会遵守。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "描述是建议，不是约束。必须在代码里夹紧（`min/max`），模型传 99 也只返回 3 条。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "schema 打印里 `limit` 不在 `required` 中，原因是什么？",
                        "options": [
                            ("A", "因为它是整型"),
                            ("B", "因为它有默认值 3"),
                            ("C", "因为它在参数列表第二"),
                            ("D", "因为工具只有一个必填参数的限制"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "有默认值即视为可选。想让参数可选，给它默认值；想让它必填，别给。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`ALLOWED[\"delete_all\"]` 抛 `KeyError` 而不是返回 `None`，这有什么好处？",
                        "options": [
                            ("A", "报错信息更详细"),
                            ("B", "失败立刻可见，不会出现「静默没执行」的假成功"),
                            ("C", "性能更好"),
                            ("D", "能自动记录日志"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "静默失败最可怕：用户以为执行了，实际什么都没发生。`KeyError` 至少能在测试与日志里暴露。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「写笔记」这类工具不能直接给模型调用？",
                        "options": [],
                        "answer": """因为写操作的错误不可逆，而且模型无法判断「该不该写」。

模型只知道自己被要求「记住点什么」，但用户可能只是在讨论、在假设、在引用别人的话。
把这些都存成笔记，很快就没有可用性了。

更重要的是责任：写操作要有人签字。审批流的意义不只是防错，还包括「出问题时能回答谁批准的」。

所以正确的设计是：模型可以**提议**写什么，执行放在人工确认之后。
这需要中断（第 22 章）与检查点（第 20 章），也就是说，这个能力是前面章节攒出来的。

一句话：读操作可以让模型自主，写操作必须让人点头。""",
                        "explanation": "权限边界不是「信任模型与否」，而是「错了能不能撤回」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-28-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个只读工具 `list_chapters(subject: str)`，返回该主题下的章节名，并限制最多 5 条。",
                        "options": [],
                        "answer": {
                            "value": "@tool\ndef list_chapters(subject: str, limit: int = 5) -> str:\n    \"\"\"列出某主题下的章节名。适用于用户问「这个方向有哪些章」。\"\"\"\n    matched = [k for k, v in COURSES.items() if subject in v]\n    limit = max(1, min(limit, 5))\n    return \"\\n\".join(matched[:limit]) or \"没有相关章节\""
                        },
                        "explanation": "三件套：写清「什么时候用」的描述、有默认值的可选参数、代码里的上限夹紧。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-28-lesson-03",
                "title": "状态与条件路由",
                "objectives": """1. 能为项目设计状态字段，并说清每个字段谁写谁读；
2. 能用条件边把「一类问题」导向「一条支路」，并保持路由函数纯净；
3. 能用 `stream_mode="updates"` 观察实际走过的路径；
4. 能解释「为什么同一张图能服务四类问题」。""",
                "why_learn": """状态是图的血液，路由是图的神经。这两块设计对了，加需求就是加节点；设计错了，每加一个需求就要改所有节点。""",
                "concepts": """**状态字段清单**：`messages`（历史）、`question`（本轮问题）、`intent`（分类结论）、`docs`（资料）、`answer`（最终回答）。
**读写的对称**：每个字段至少一个写者、一个读者；只写不读的字段是垃圾，只读不写的字段会拿到空值。
**路由纯函数**：只读 `intent`，返回短键，不调模型、不改状态。
**路径可观测**：`updates` 模式按节点名输出，拼起来就是实际路径。
**一图多能**：四条支路共用 `classify` 与 `answer`，差异只在中间。
**检索范围**：`concept` 全库找、`chapter` 精确读，这是路由带来的实质差别。""",
                "plain": """状态设计的检验方法很土但很有效：把字段列出来，左右各写一栏「谁写」「谁读」。

`messages` 由 `answer` 写、由 `answer` 读（下一轮还要用）；`question` 由接口写、由 `classify` 与 `answer` 读；
`intent` 由 `classify` 写、由路由读；`docs` 由检索节点写、由 `answer` 读；`answer` 由终点节点写、由接口读。

任何一栏空着，就有问题。只写不读，说明这个字段没用；只读不写，说明某处漏了赋值。

路由函数要干净。它只做一件事：看 `intent`，返回一个短键。不要在里面调模型、不要改状态、
不要写日志以外的副作用。这样它可以用一行代码测完。

最后，别忘了验证「真的走了那条路」。用 `updates` 模式把节点名按顺序打出来，
比盯着代码猜快得多——你会亲眼看到 `classify -> read_chapter -> answer` 这样的路径。""",
                "syntax": """**状态 + 路由 + 观测**

```python
class AskState(TypedDict):
    messages: Annotated[list, add_messages]   # 历史
    question: str                             # 本轮问题
    intent: str                               # 分类结论
    docs: list                                # 检索结果
    answer: str                               # 最终回答


def route(state: AskState) -> str:
    return state["intent"]        # 纯函数：只读结论，不做判断


builder.add_conditional_edges("classify", route, {
    "concept": "retrieve", "chapter": "read_chapter",
    "progress": "progress", "note": "note",
})

for chunk in graph.stream(inp, stream_mode="updates"):
    print(list(chunk))            # 实际经过的节点
```

- `messages` 用 `add_messages` 累积，其余字段默认覆盖。
- 路由函数不要返回 `None`，也不要漏掉某个 `intent`。
- 用 `updates` 观测路径时，注意 payload 可能是 `None`（节点返回空时）。""",
                "example_code": '''from typing import Annotated, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class AskState(TypedDict):
    messages: Annotated[list, add_messages]
    question: str
    intent: str
    docs: list
    answer: str


COURSES = {
    "第 6 章": "状态结构：节点只返回增量。",
    "第 16 章": "接入大模型：模型只是节点里的一次调用。",
}


class StudyModel(BaseChatModel):
    """离线模型：把资料拼成一句回答，保证示例可复现。"""

    @property
    def _llm_type(self) -> str:
        return "study"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        last = messages[-1].content
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=f"根据课程资料：{last[:36]}"))])


model = StudyModel()

RULES = [
    ("学到哪", "progress"),
    ("进度", "progress"),
    ("笔记", "note"),
    ("章", "chapter"),
]


def classify(state: AskState) -> dict:
    for key, intent in RULES:
        if key in state["question"]:
            return {"intent": intent}
    return {"intent": "concept"}


def retrieve(state: AskState) -> dict:
    """概念类问题：全库按关键词找。"""
    docs = [v for v in COURSES.values() if "状态" in v or "模型" in v]
    return {"docs": docs or ["没有找到相关资料"]}


def read_chapter(state: AskState) -> dict:
    """章节类问题：只读指定的那一章，范围更窄。"""
    docs = [v for k, v in COURSES.items() if k in state["question"]]
    return {"docs": docs or ["没有这一章"]}


def answer(state: AskState) -> dict:
    reply = model.invoke([HumanMessage("；".join(state["docs"]))])
    return {"messages": [reply], "answer": reply.content}


def look_progress(state: AskState) -> dict:
    return {"answer": "你已完成前 20 章，最近一次学习是第 20 章 Checkpointer。"}


def take_note(state: AskState) -> dict:
    return {"answer": f"已记下：{state['question']}"}


builder = StateGraph(AskState)
builder.add_node("classify", classify)
builder.add_node("retrieve", retrieve)
builder.add_node("read_chapter", read_chapter)
builder.add_node("answer", answer)
builder.add_node("progress", look_progress)
builder.add_node("note", take_note)
builder.add_edge(START, "classify")
builder.add_conditional_edges(
    "classify",
    lambda state: state["intent"],
    {
        "concept": "retrieve",
        "chapter": "read_chapter",
        "progress": "progress",
        "note": "note",
    },
)
builder.add_edge("retrieve", "answer")
builder.add_edge("read_chapter", "answer")
builder.add_edge("answer", END)
builder.add_edge("progress", END)
builder.add_edge("note", END)
graph = builder.compile()

print("=== 同一张图，四种问题走四条路 ===")
for question in ("State 是什么", "第 16 章讲什么", "我学到哪了", "帮我记一条笔记"):
    trace, merged = [], {}
    for chunk in graph.stream(
        {"messages": [HumanMessage(question)], "question": question, "intent": "", "docs": [], "answer": ""},
        stream_mode="updates",
    ):
        for node, update in chunk.items():
            trace.append(node)
            merged.update(update)
    print(f"  {question:14s} 路径: {' -> '.join(trace)}")
    print(f"  {'':14s} intent={merged['intent']:9s} answer={merged['answer'][:38]}")''',
                "code_lines": """1. 状态五个字段各司其职：`messages` 存历史、`question` 是本轮问题、`intent` 是结论、`docs` 是资料、`answer` 是输出。
2. `RULES` 按顺序匹配关键词，先命中即返回——这就是「分类」最简形式，先跑通再换模型。
3. `retrieve` 与 `read_chapter` 是两个节点：一个全库找、一个精确读，检索范围不同。
4. `answer` 是两条支路的汇合点：它只读 `docs`，不关心资料是哪个节点放进来的——这就是解耦。
5. `progress` 与 `note` 直接产出 `answer`，不经过模型：能确定性回答的，别浪费一次调用。
6. 条件边用 `lambda state: state["intent"]` 作路由，映射表列出四个去处。
7. 观测路径用 `updates` 模式：把每次 chunk 的键收集起来，就是实际走过的节点序列。
8. 四条路径各不相同，但共用 `classify` 与 `answer`——同一张图服务四类问题。""",
                "output": """# 程序输出
=== 同一张图，四种问题走四条路 ===
  State 是什么      路径: classify -> retrieve -> answer
                 intent=concept   answer=根据课程资料：状态结构：节点只返回增量。；接入大模型：模型只是节点里的一次调
  第 16 章讲什么      路径: classify -> read_chapter -> answer
                 intent=chapter   answer=根据课程资料：接入大模型：模型只是节点里的一次调用。
  我学到哪了          路径: classify -> progress
                 intent=progress  answer=你已完成前 20 章，最近一次学习是第 20 章 Checkpointer。
  帮我记一条笔记        路径: classify -> note
                 intent=note      answer=已记下：帮我记一条笔记""",
                "mistakes": """- 路由函数里调模型或改状态：变成有副作用的业务代码，无法单独测。
- 状态字段只写不读（或只读不写）：前者是垃圾字段，后者会拿到空值。
- 把「进度」这类确定性回答也交给模型：多花一次调用，还可能编错。
- 分支汇合点写成两个 `answer` 节点：逻辑重复，改一处忘另一处。
- 用 `values` 模式观测路径：拿到的是全量状态，看不出经过了哪些节点。
- 关键词规则顺序不当：先判断宽泛的词（如「章」），细分的「笔记」就永远命中不了。""",
                "error_analysis": """`KeyError: 'chapter'`（路由映射表）
—— 分类产出了映射表里没有的键。检查 `RULES` 与映射表是否一一对应。

路径里少了某个节点
—— 该节点没有入边，或条件边把它漏了。用 `updates` 打印实际路径核对。

`answer` 里资料是空的
—— 检索节点返回空 `docs`，而 `answer` 没做兜底。给它一个「没有找到」的分支。

`TypeError` 出现在 `merged.update(update)`
—— 某个节点的 payload 是 `None`。加 `isinstance(update, dict)` 判断。""",
                "beginner_practice": """1. 把 `RULES` 中「章」这条移到最前面，观察「第 16 章讲什么」与「帮我记一条笔记」的分类变化。
2. 给 `progress` 支路加一个 `docs` 读取，让它能引用最近学过的章节名。""",
                "advanced_practice": """把关键词分类换成模型分类（用第 16 章的兼容模型），并说明怎样保证「分类失败时有兜底」、
以及怎么用离线测试覆盖分类结果。""",
                "quiz_note": "本节 6 道题：2 道基础理解（状态字段该谁写谁读、路由函数为什么必须纯净）+ 2 道代码阅读（四种问题为什么路径不同、`answer` 为什么不关心资料来源）+ 2 道应用练习（调整规则顺序、换成模型分类）。",
                "summary": """状态字段要「有人写、有人读」；路由函数只读结论、返回短键。
能确定性回答的支路直接产出结果，别浪费模型调用。
用 `updates` 观测真实路径。""",
                "next_lesson": "流程能走了，下一步让它记得住、还能停下来等人——持久化与人工介入。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-28-03",
                        "name": "状态与条件路由",
                        "goal": "能设计状态字段并用条件边分流四类问题。",
                        "minutes": 50,
                        "criteria": "能说明每个字段的读写方，并用 `updates` 验证路径。",
                        "requires": ["langgraph-agent-28-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-28-03-1",
                        "kp": 0,
                        "title": "给字段加读写方",
                        "description": "新增字段 `sources: list`，记录这条回答引用了哪些章节。写出谁写、谁读，并补代码。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class AskState(TypedDict):
    ...
    sources: list        # 由检索节点写，由 answer 写回引用


def retrieve(state: AskState) -> dict:
    hits = [(k, v) for k, v in COURSES.items() if "状态" in v]
    return {"docs": [v for _, v in hits], "sources": [k for k, _ in hits]}


def answer(state: AskState) -> dict:
    reply = model.invoke([HumanMessage("；".join(state["docs"]))])
    return {"messages": [reply], "answer": reply.content}''',
                        "explanation": "加了字段就要补齐读写两端：`sources` 由检索节点写、由接口层读（返回给前端做引用展示）。只写不读等于没加。",
                    },
                    {
                        "code": "lg-ex-28-03-2",
                        "kp": 0,
                        "title": "确定性回答该不该过模型",
                        "description": "「我学到哪了」这类问题，为什么要单独一个节点直接回答，而不是交给模型？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """三个理由。

① 准确性：进度是数据库里的事实。交给模型，它可能「润色」成错的数字——这类错误用户一看就发现，
信任瞬间归零。

② 成本与延迟：一次模型调用要几百毫秒到几秒。读一条记录是毫秒级。

③ 可测性：`look_progress` 是纯函数，输入输出确定，一行断言就能测。模型输出只能松断言。

判断标准：这个答案能不能从结构化数据里直接查出来？能，就走确定性支路；不能（需要组织语言、
需要跨资料总结），才交给模型。

这也是「混合架构」的典型形态：能用代码算的用代码，需要理解语言的才用模型。
把一切都交给模型，是最贵也最不稳的做法。""",
                        "explanation": "模型该用在「需要理解」的地方，不是「需要查询」的地方。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-28-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "状态字段 `intent` 的「写方」与「读方」分别是谁？",
                        "options": [
                            ("A", "`classify` 写、路由函数读"),
                            ("B", "路由函数写、`answer` 读"),
                            ("C", "接口层写、`classify` 读"),
                            ("D", "`answer` 写、接口层读"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "分类产出结论，路由消费结论。这个分工让分类逻辑与路由逻辑可以各自演化。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-03-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "路由函数里可以调用模型来判断问题类型。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "路由函数应当只读状态、返回短键。调用模型属于「分类」，应该放在 `classify` 节点里。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-03-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "「第 16 章讲什么」的路径是 `classify -> read_chapter -> answer`，而「State 是什么」走的是 `retrieve`。差别在哪？",
                        "options": [
                            ("A", "分类结果不同，映射表把它们导向不同节点"),
                            ("B", "`retrieve` 节点被禁用了"),
                            ("C", "`read_chapter` 会调用两次模型"),
                            ("D", "路径相同，只是打印顺序不同"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "含「章」的问题被判为 `chapter`，走精确读取；其余走全库检索。检索范围不同，答案范围也不同。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-03-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`answer` 节点不关心资料是 `retrieve` 还是 `read_chapter` 放进来的，这带来什么好处？",
                        "options": [
                            ("A", "可以让两条支路共用同一个汇合点，改一次生效两处"),
                            ("B", "可以减少状态字段"),
                            ("C", "可以提高模型准确率"),
                            ("D", "可以跳过路由"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "汇合点只依赖 `docs` 这个契约，不依赖来源。以后再加第三条支路，`answer` 也不用改。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-03-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「我学到哪了」不交给模型回答？",
                        "options": [],
                        "answer": """因为它是「查事实」，不是「理解语言」。

进度是数据库里的确定数据。交给模型有两个风险：一是可能算错或编造（幻觉在数字上尤其致命），
二是每次都要等一次模型调用，几百毫秒到几秒。

用一个节点直接查、直接答，好处是：结果准确、毫秒级返回、纯函数可单测。

判断标准：答案能不能从结构化数据直接查出来？能，就走确定性支路；需要组织语言或跨资料总结，才用模型。

这也是成本最低的架构：模型只处理「非它不可」的部分，其余用代码。""",
                        "explanation": "把模型用在「需要理解」的地方，是成本与可靠性的双赢。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-28-03-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写出条件边装配：四个 `intent` 分别去 `retrieve` / `read_chapter` / `progress` / `note`。",
                        "options": [],
                        "answer": {
                            "value": "builder.add_conditional_edges(\n    \"classify\",\n    lambda state: state[\"intent\"],\n    {\n        \"concept\": \"retrieve\",\n        \"chapter\": \"read_chapter\",\n        \"progress\": \"progress\",\n        \"note\": \"note\",\n    },\n)"
                        },
                        "explanation": "映射表要把四个键列全。少一个，运行到那条问题时就 `KeyError`——而这条路径可能几周才被走到一次。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-28-lesson-04",
                "title": "持久化与人工介入",
                "objectives": """1. 能用检查点让多轮对话接上历史，用 Store 存跨会话数据；
2. 能在写操作前用 `interrupt` 挂起，批准后才落库；
3. 能设计拒绝路径，并验证拒绝后数据没有被写入；
4. 能说明「哪些数据进状态、哪些进 Store、哪些必须落业务库」。""",
                "why_learn": """这是项目里唯一同时涉及「记忆」与「权限」的一节。做对了，Agent 才像个能交付的产品；
做错了，要么每次对话都失忆，要么某天悄悄写坏了用户数据。""",
                "concepts": """**检查点**：按 `thread_id` 存每一步，多轮对话自然接上。
**Store**：按命名空间存跨会话数据（笔记、偏好），`("notes", user_id)`。
**中断**：写操作前 `interrupt({...})`，把「要写什么」递给人看。
**恢复**：`Command(resume={"approved": True})`，批准才落库。
**拒绝路径**：拒绝也要有明确答复，且**不写数据**。
**三层存储**：状态（本轮）、Store（跨会话）、业务库（需要审计与检索的正式数据）。""",
                "plain": """这一节把三样东西装到一起：检查点让对话有记忆，Store 让跨会话有记忆，中断让写操作有人把关。

分工要清楚。检查点存的是「这条会话走到哪了」，它按 `thread_id` 隔离；
Store 存的是「这个人有哪些笔记」，它按用户隔离；真正需要审计、需要被检索的正式数据，
应该进你自己的业务库，而不是 Store 里凑合。

中断的位置很关键：必须在「已经确定要写什么」之后、「真的写进去」之前。
太早了人看不到要写什么，太晚了已经写了。

还有一条容易漏的：拒绝也要有明确答复，并且要验证「确实没写」。
示例里拒绝之后打印了笔记条数，仍然是 1——这才是完整的拒绝路径。""",
                "syntax": """**装配与两段式写操作**

```python
graph = builder.compile(checkpointer=InMemorySaver(), store=store)

def take_note(state, runtime: Runtime) -> dict:
    decision = interrupt({"action": "保存笔记", "content": state["question"]})
    if not decision.get("approved"):
        return {"answer": "已取消保存"}            # 拒绝：不写
    ns = ("notes", state["user_id"])
    runtime.store.put(ns, key, {"text": state["question"]})
    return {"answer": f"已保存到 {ns}"}
```

- `compile` 同时传 `checkpointer` 与 `store`，两者互不依赖。
- `runtime.store` 来自 `Runtime` 注入（第 21 章）。
- 拒绝路径必须有返回值，否则接口拿不到任何反馈。
- 恢复用 `Command(resume={"approved": True})`，不要传 `None`。""",
                "example_code": '''from typing import Annotated, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command, interrupt


class AskState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    question: str
    intent: str
    answer: str


class StudyModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "study"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=f"回答：{messages[-1].content[:20]}"))])


model = StudyModel()
store = InMemoryStore()


def classify(state: AskState) -> dict:
    return {"intent": "note" if "笔记" in state["question"] else "concept"}


def answer(state: AskState) -> dict:
    reply = model.invoke([HumanMessage(state["question"])])
    return {"messages": [reply], "answer": reply.content}


def take_note(state: AskState, runtime: Runtime) -> dict:
    """写操作前停下：等人确认才落库。"""
    decision = interrupt({"action": "保存笔记", "content": state["question"]})
    print("  人工决定:", decision)
    if not decision.get("approved"):
        return {"answer": "已取消保存"}
    ns = ("notes", state["user_id"])
    key = f"note-{len(runtime.store.search(ns)) + 1}"
    runtime.store.put(ns, key, {"text": state["question"]})
    return {"answer": f"已保存到 {ns} / {key}"}


builder = StateGraph(AskState)
builder.add_node("classify", classify)
builder.add_node("answer", answer)
builder.add_node("take_note", take_note)
builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", lambda s: s["intent"], {"concept": "answer", "note": "take_note"})
builder.add_edge("answer", END)
builder.add_edge("take_note", END)
graph = builder.compile(checkpointer=InMemorySaver(), store=store)


def ask(user: str, question: str) -> dict:
    cfg = {"configurable": {"thread_id": f"{user}:main"}}
    return graph.invoke(
        {"messages": [HumanMessage(question)], "user_id": user, "question": question, "intent": "", "answer": ""},
        cfg,
    )


print("=== 1. 同一用户两轮问答（检查点接住历史）===")
first = ask("u1", "State 是什么")
print("  第 1 轮消息数:", len(first["messages"]), "| answer:", first["answer"])
second = ask("u1", "Node 是什么")
print("  第 2 轮消息数:", len(second["messages"]), "| answer:", second["answer"])

print()
print("=== 2. 另一个用户互不影响 ===")
other = ask("u2", "Edge 是什么")
print("  u2 消息数:", len(other["messages"]))

print()
print("=== 3. 写笔记：先挂起 ===")
cfg = {"configurable": {"thread_id": "u1:main"}}
paused = graph.invoke(
    {"messages": [HumanMessage("帮我记一条笔记：State 要返回增量")], "user_id": "u1",
     "question": "帮我记一条笔记：State 要返回增量", "intent": "", "answer": ""},
    cfg,
)
print("  挂起:", paused["__interrupt__"][0].value)
print("  next:", graph.get_state(cfg).next)

print()
print("=== 4. 人工批准后落库 ===")
done = graph.invoke(Command(resume={"approved": True}), cfg)
print("  answer:", done["answer"])
print("  store:", [i.value for i in store.search(("notes", "u1"))])

print()
print("=== 5. 再记一条，这次拒绝 ===")
paused = graph.invoke(
    {"messages": [HumanMessage("帮我记一条笔记：Edge 连接节点")], "user_id": "u1",
     "question": "帮我记一条笔记：Edge 连接节点", "intent": "", "answer": ""},
    cfg,
)
done = graph.invoke(Command(resume={"approved": False}), cfg)
print("  answer:", done["answer"])
print("  笔记条数仍是:", len(store.search(("notes", "u1"))))''',
                "code_lines": """1. `compile` 同时传了检查点与 Store：前者记「会话到哪了」，后者记「这个人有哪些笔记」。
2. `classify` 只判断「是不是记笔记」，其余都走回答支路——项目小节，先抓主干。
3. `answer` 是只读支路：读问题、调模型、写回状态，不碰 Store。
4. `take_note` 是写支路：先 `interrupt` 把待写内容递出去，再根据决定决定写不写。
5. `runtime.store.search(ns)` 用来算「第几条」，也可以直接用 uuid——示例用计数是为了让输出可复现。
6. 第 1、2 段验证检查点：同一用户消息数 2 → 4；换用户又从 2 开始。
7. 第 3 段验证中断：`next` 是 `('take_note',)`，说明停在了写操作之前。
8. 第 4、5 段验证两条路径：批准后 Store 里有 1 条，拒绝后条数仍是 1（没被写进去）。""",
                "output": """# 程序输出
=== 1. 同一用户两轮问答（检查点接住历史）===
  第 1 轮消息数: 2 | answer: 回答：State 是什么
  第 2 轮消息数: 4 | answer: 回答：Node 是什么

=== 2. 另一个用户互不影响 ===
  u2 消息数: 2

=== 3. 写笔记：先挂起 ===
  挂起: {'action': '保存笔记', 'content': '帮我记一条笔记：State 要返回增量'}
  next: ('take_note',)

=== 4. 人工批准后落库 ===
  人工决定: {'approved': True}
  answer: 已保存到 ('notes', 'u1') / note-1
  store: [{'text': '帮我记一条笔记：State 要返回增量'}]

=== 5. 再记一条，这次拒绝 ===
  人工决定: {'approved': False}
  answer: 已取消保存
  笔记条数仍是: 1""",
                "mistakes": """- 把写操作放在 `interrupt` 之前：人还没看到，数据已经写进去了。
- 拒绝路径什么都不返回：接口拿到空结果，用户不知道发生了什么。
- 用状态存跨会话数据：换条会话就丢，用户要重新交代。
- 把正式业务数据也塞进 Store：没有索引、没有审计、没法做后台查询。
- 用 `invoke(None, cfg)` 恢复：不会恢复，只会再挂一次。
- 中断载荷只给一句「是否保存」：审批人看不到要保存什么，只能盲签。
- 同一用户多线程并发写 Store：key 用计数会撞车，要用 uuid 或时间戳。""",
                "error_analysis": """`KeyError: 'notes'` / Store 里查不到
—— 命名空间拼错，或两个 store 实例（一个模块级、一个别处新建）。

恢复后没有落库
—— `resume` 传的不是 `{"approved": True}`，或节点里读字段名拼错。

`session` 里出现两条一样的笔记
—— 节点在恢复时重跑了 `interrupt` 之前的代码。把写操作放在 `interrupt` 之后，或用幂等键。

`GraphRecursionError`
—— 忽略不计：本项目循环在 `take_note` 之后直接 `END`。如果加了重试式回边，要设 `recursion_limit`。

多用户数据串了
—— `thread_id` 没用 `user_id` 拼，或 Store 命名空间用了固定值。""",
                "beginner_practice": """1. 把 `Command(resume={"approved": False})` 换成 `{"approved": True}`，观察笔记条数变化。
2. 打印 `graph.get_state(cfg).values["messages"]`，确认拒绝那次也没把笔记写进历史。""",
                "advanced_practice": """把笔记从 Store 换成真实业务表：设计表结构（用户、内容、状态、审批人、时间），
说明哪些字段必须落库、哪些留在 Store 更方便，以及怎么保证「重复审批不重复写」。""",
                "quiz_note": "本节 6 道题：2 道基础理解（检查点与 Store 的分工、中断该放在哪一步）+ 2 道代码阅读（`next` 为什么是 `take_note`、拒绝后为什么条数不变）+ 2 道应用练习（设计拒绝路径、笔记落业务表）。",
                "summary": """检查点管会话记忆，Store 管跨会话数据，业务库管正式数据。
写操作放在 `interrupt` 之后，批准才落库。
拒绝也要有答复，并且要验证数据确实没被写。""",
                "next_lesson": "最后一节：把这张图包成接口，并用离线测试把它锁住。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-28-04",
                        "name": "持久化与人工介入",
                        "goal": "能让对话有记忆、写操作有人把关。",
                        "minutes": 50,
                        "criteria": "能验证批准与拒绝两条路径，并说清三层存储的分工。",
                        "requires": ["langgraph-agent-28-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-28-04-1",
                        "kp": 0,
                        "title": "让拒绝也可追溯",
                        "description": "拒绝保存时，把「谁拒绝了、拒绝了几次」记下来，方便后面统计。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def take_note(state: AskState, runtime: Runtime) -> dict:
    decision = interrupt({"action": "保存笔记", "content": state["question"]})
    ns = ("notes", state["user_id"])
    if not decision.get("approved"):
        runtime.store.put(ns, f"reject-{uuid4().hex[:8]}", {
            "text": state["question"],
            "status": "rejected",
            "reason": decision.get("reason", "未说明"),
        })
        return {"answer": "已取消保存"}
    runtime.store.put(ns, f"note-{uuid4().hex[:8]}", {"text": state["question"], "status": "saved"})
    return {"answer": "已保存"}''',
                        "explanation": "把拒绝也当成一条记录，才能统计「模型提议的写操作有多少被否决」——这是评估工具设计是否合理的重要指标。",
                    },
                    {
                        "code": "lg-ex-28-04-2",
                        "kp": 0,
                        "title": "三层存储怎么分",
                        "description": "给出「状态 / Store / 业务库」的划分标准，并各举一例。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """按「生命周期」与「是否需要审计」划分。

**状态**：只服务本轮流程。例：`docs`（本轮检索到的资料）、`intent`（本轮分类结论）。
特征：跑完就可以丢，进检查点只为调试与恢复。

**Store**：跨会话、按用户组织的轻量数据。例：用户偏好、笔记草稿、上次学习章节。
特征：读写频繁、结构松散、不需要复杂查询。

**业务库**：需要审计、检索、关联、对账的正式数据。例：笔记正式记录、审批流水、用量与计费。
特征：有唯一约束、有状态机、要能被后台系统查询。

划错的典型症状：把正式笔记只写进 Store，后台想统计「本周新增笔记」时发现查不了；
或者把偏好写进业务表，每加一个偏好就要改表结构。

一句话：状态是「过程」，Store 是「便签」，业务库是「账本」。""",
                        "explanation": "存储分层不是技术细节，它决定了以后能不能查、能不能审、能不能改。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-28-04-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "检查点与 Store 的分工是什么？",
                        "options": [
                            ("A", "检查点存跨会话数据，Store 存单次会话"),
                            ("B", "检查点存会话每步状态，Store 存跨会话的数据"),
                            ("C", "两者完全等价"),
                            ("D", "检查点只能存消息，Store 只能存字符串"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "一个按 `thread_id` 隔离，一个按命名空间（如用户）组织。混用会导致「换会话就失忆」。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-04-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "写操作应该放在 `interrupt` 之前，这样人审批时数据已经保存好了。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "那就成了「先斩后奏」。审批的意义是「批准才执行」，写操作必须在 `interrupt` 之后。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-04-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "挂起时 `next` 打印为 `('take_note',)`，说明什么？",
                        "options": [
                            ("A", "流程已经结束"),
                            ("B", "流程停在 `take_note` 这个节点内部，尚未完成"),
                            ("C", "`take_note` 将要执行两次"),
                            ("D", "图编译失败"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "中断发生在节点中间，节点还没跑完，所以 `next` 指向它。跑完后 `next` 才是空元组。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-04-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第 5 段拒绝之后，「笔记条数仍是 1」这条打印有什么意义？",
                        "options": [
                            ("A", "证明 Store 不支持删除"),
                            ("B", "证明拒绝路径确实没有写入，是完整的负向验证"),
                            ("C", "证明只有一条笔记能存"),
                            ("D", "证明中断生效了两次"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "只断言「返回了已取消」不够，要验证数据层没有被改动。负向验证往往比正向更重要。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-04-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "「保存笔记」这样的功能，数据应该放状态、Store 还是业务库？",
                        "options": [],
                        "answer": """正式笔记要放**业务库**，理由有三。

① 要能被检索与统计：后台要查「某用户本周新增笔记」「哪类笔记最多」，Store 的键值结构做不了。

② 要有审计：谁写的、谁批的、什么时候、改过几次。这是责任链，必须落表。

③ 要有关联：笔记可能关联章节、课程、学习计划。关系型存储在行。

Store 适合放「便签级」的东西：临时草稿、用户偏好、上次看到第几章。它读写快、结构自由，
但不适合当账本。

状态则完全不该存：它属于一条会话，换个入口就没了。

实践里常见组合：正式笔记进业务库，同时把「最近一条笔记摘要」写进 Store，
让 Agent 下一轮能快速引用，不必查库。""",
                        "explanation": "存储选择看「以后要不要查、要不要审、要不要关联」，而不是「现在方便」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-28-04-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个带审批的写节点：挂起 → 批准才写 Store → 拒绝返回明确答复。",
                        "options": [],
                        "answer": {
                            "value": "def take_note(state: AskState, runtime: Runtime) -> dict:\n    decision = interrupt({\"action\": \"保存笔记\", \"content\": state[\"question\"]})\n    if not decision.get(\"approved\"):\n        return {\"answer\": \"已取消保存\"}\n    ns = (\"notes\", state[\"user_id\"])\n    runtime.store.put(ns, f\"note-{uuid4().hex[:8]}\", {\"text\": state[\"question\"]})\n    return {\"answer\": \"已保存\"}"
                        },
                        "explanation": "顺序不能反：先中断、再判断、最后写。key 用 uuid 而不是计数，避免并发撞车。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-28-lesson-05",
                "title": "FastAPI 接口与测试",
                "objectives": """1. 能把整张图包成同步接口与流式接口；
2. 能让「需要审批」的情况在接口层可表达、可恢复；
3. 能写四个离线测试覆盖：正常回答、线程记忆、审批、流式结束；
4. 能对照六条需求做一次完整验收。""",
                "why_learn": """最后一公里：图在本地跑通，和「别人能用」之间差一个接口层；接口写完不测，等于没写。
这一节把前面 27 章的能力收口成一个可验收的东西。""",
                "concepts": """**同步接口**：`/ask` 返回回答与「是否需要审批」标志。
**审批接口**：`/approve` 用 `Command(resume=...)` 继续被挂起的线程。
**流式接口**：`/ask/stream` 用 `stream_mode=["custom","updates"]` 拼 SSE。
**测试四件事**：回答非空、线程记忆、审批挂起与恢复、流式有结束帧。
**`TestClient`**：不起服务也能跑完整链路。
**验收表**：六条需求逐条对应到文件、函数、测试。""",
                "plain": """接口层要解决一个「状态外显」的问题：图在等人审批时，HTTP 请求不能一直挂着。

做法是让 `/ask` 直接返回 `needs_approval: true`，前端据此弹出审批框；
用户点了之后调 `/approve`，服务端用 `Command(resume=...)` 把结论送回去，流程继续。

这样「挂起」对前端就是两个普通请求，不需要长连接、不需要轮询。

测试要覆盖四件事，缺一不可：正常回答（主干通）、线程记忆（检查点生效）、
审批挂起与恢复（写操作被把关）、流式有结束帧（前端不会卡住）。

最后拿第 28-1 节那张需求表逐条对照：每条需求都要能指出「在哪个函数里」「哪个测试覆盖」。
指不出来的，就是没做完。""",
                "syntax": """**两个接口 + 四个测试**

```python
@app.post("/ask", response_model=AskOut)
def ask(payload: AskIn) -> AskOut:
    out = graph.invoke({...}, cfg)
    return AskOut(answer=out.get("answer", ""), thread_id=..., needs_approval="__interrupt__" in out)

@app.post("/approve")
def approve(payload: AskIn) -> dict:
    out = graph.invoke(Command(resume={"approved": True}), cfg)
    return {"answer": out["answer"]}

def test_ask_returns_answer(): ...
def test_thread_keeps_history(): ...
def test_note_requires_approval(): ...
def test_stream_has_done_event(): ...
```

- 「是否需要审批」通过 `"__interrupt__" in out` 判断，别自己维护状态位。
- 流式断言用 `iter_lines()`，别用 `iter_text()`（当前 httpx 版本会报错）。
- 测试用独立 `thread_id`，避免互相污染。""",
                "example_code": '''import json
from typing import Annotated, TypedDict

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field


class AskState(TypedDict):
    messages: Annotated[list, add_messages]
    question: str
    answer: str


class StudyModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "study"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=f"回答：{messages[-1].content[:16]}"))])


model = StudyModel()


def classify(state: AskState) -> dict:
    return {}


def answer(state: AskState) -> dict:
    get_stream_writer()({"stage": "生成回答", "percent": 80})
    reply = model.invoke([HumanMessage(state["question"])])
    return {"messages": [reply], "answer": reply.content}


def ask_human(state: AskState) -> dict:
    decision = interrupt({"action": "保存笔记"})
    return {"answer": "已保存" if decision.get("approved") else "已取消"}


builder = StateGraph(AskState)
builder.add_node("classify", classify)
builder.add_node("answer", answer)
builder.add_node("ask_human", ask_human)
builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", lambda s: "note" if "笔记" in s["question"] else "answer",
                              {"answer": "answer", "note": "ask_human"})
builder.add_edge("answer", END)
builder.add_edge("ask_human", END)
graph = builder.compile(checkpointer=InMemorySaver())

app = FastAPI()


class AskIn(BaseModel):
    user_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=500)


class AskOut(BaseModel):
    answer: str
    thread_id: str
    needs_approval: bool


def thread_of(user_id: str) -> str:
    return f"{user_id}:main"


@app.post("/ask", response_model=AskOut)
def ask(payload: AskIn) -> AskOut:
    cfg = {"configurable": {"thread_id": thread_of(payload.user_id)}}
    out = graph.invoke({"messages": [HumanMessage(payload.question)], "question": payload.question, "answer": ""}, cfg)
    return AskOut(answer=out.get("answer", ""), thread_id=thread_of(payload.user_id),
                  needs_approval="__interrupt__" in out)


@app.post("/approve")
def approve(payload: AskIn) -> dict:
    cfg = {"configurable": {"thread_id": thread_of(payload.user_id)}}
    out = graph.invoke(Command(resume={"approved": True}), cfg)
    return {"answer": out["answer"]}


@app.post("/ask/stream")
def ask_stream(payload: AskIn) -> StreamingResponse:
    cfg = {"configurable": {"thread_id": thread_of(payload.user_id)}}

    def events():
        for mode, chunk in graph.stream(
            {"messages": [HumanMessage(payload.question)], "question": payload.question, "answer": ""},
            cfg,
            stream_mode=["custom", "updates"],
        ):
            if mode == "custom":
                yield f"event: progress\\ndata: {json.dumps(chunk, ensure_ascii=False)}\\n\\n"
            else:
                for node, update in chunk.items():
                    if isinstance(update, dict) and "answer" in update:
                        data = {"node": node, "answer": update["answer"]}
                        yield f"event: message\\ndata: {json.dumps(data, ensure_ascii=False)}\\n\\n"
        yield "event: done\\ndata: {}\\n\\n"

    return StreamingResponse(events(), media_type="text/event-stream")


client = TestClient(app)


def test_ask_returns_answer():
    r = client.post("/ask", json={"user_id": "t1", "question": "State 是什么"})
    assert r.status_code == 200
    assert r.json()["answer"].startswith("回答：")
    assert r.json()["needs_approval"] is False


def test_thread_keeps_history():
    client.post("/ask", json={"user_id": "t2", "question": "第一问"})
    client.post("/ask", json={"user_id": "t2", "question": "第二问"})
    cfg = {"configurable": {"thread_id": "t2:main"}}
    messages = graph.get_state(cfg).values["messages"]
    assert len(messages) == 4, f"两轮应有 4 条消息，实际 {len(messages)}"


def test_note_requires_approval():
    r = client.post("/ask", json={"user_id": "t3", "question": "帮我记一条笔记"})
    assert r.json()["needs_approval"] is True
    r2 = client.post("/approve", json={"user_id": "t3", "question": "帮我记一条笔记"})
    assert r2.json()["answer"] == "已保存"


def test_stream_has_done_event():
    with client.stream("POST", "/ask/stream", json={"user_id": "t4", "question": "State 是什么"}) as resp:
        lines = [line for line in resp.iter_lines() if line]
    assert "event: progress" in lines
    assert "event: message" in lines
    assert lines[-1] == "data: {}", f"最后一帧应是 done，实际 {lines[-1]!r}"


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


print("=== 接口响应 ===")
print(client.post("/ask", json={"user_id": "demo", "question": "State 是什么"}).json())
print()
print("=== 离线测试 ===")
run_all()''',
                "code_lines": """1. 图很小：`classify` 分流，`answer` 回答，`ask_human` 挂起等审批——三条边把四种能力串起来。
2. `classify` 返回空字典：分支判断写在条件边的 lambda 里。项目小时可以接受，变复杂后应搬进节点。
3. `answer` 在调模型前发一条进度事件，供 SSE 使用。
4. `/ask` 用 `"__interrupt__" in out` 判断是否需要审批，不自己维护额外状态位。
5. `/approve` 直接 `Command(resume={"approved": True})`，让被挂起的线程继续。
6. `/ask/stream` 的生成器里，`updates` 的 payload 可能是 `None`——所以先 `isinstance(update, dict)`。
7. 四个测试分别覆盖：正常回答、线程记忆、审批挂起与恢复、流式结束帧。
8. `run_all` 按名字收集 `test_` 函数，等价于 pytest 的收集；换成 pytest 无需改断言。""",
                "output": """# 程序输出
=== 接口响应 ===
{'answer': '回答：State 是什么', 'thread_id': 'demo:main', 'needs_approval': False}

=== 离线测试 ===
PASS test_ask_returns_answer
PASS test_note_requires_approval
PASS test_stream_has_done_event
PASS test_thread_keeps_history

4 passed, 0 failed""",
                "mistakes": """- 让人「等审批」的请求一直挂着：HTTP 超时。应该返回 `needs_approval`，再用第二个请求恢复。
- 自己维护 `is_waiting` 状态位：容易和真实状态不一致，直接看 `__interrupt__`。
- 流式接口里直接用 `update["answer"]`：`None` 时 `TypeError`。
- 测试共用一个 `user_id`：前一个用例的历史污染后一个。
- 只测正常回答：审批、流式、记忆都没覆盖，等于没验收。
- 把 `TestClient` 用在生产：它是测试工具，别部署。
- 接口里重新 `compile` 图：检查点实例被重建，历史全丢。""",
                "error_analysis": """`422` 但前端说「参数都对」
—— `Field` 约束不满足（比如超长）。看 `detail` 里的字段名与原因。

`/approve` 返回 500 或空
—— 该线程没有挂起的中断，`resume` 无处可去；或 `thread_id` 与 `/ask` 时不一致。

流式最后一帧不是 `done`
—— 生成器中途抛异常。加 `try/finally` 保证发出结束帧。

`TypeError: argument of type 'NoneType' is not a container`
—— 忘了 `isinstance(update, dict)`。

测试通过但线上审批卡住
—— 线上用的是异步接口 + 内存检查点：多副本时用户的下一次请求落到别的副本，找不到会话。""",
                "beginner_practice": """1. 给 `/ask` 加一个 `conversation_id` 字段，让一个用户能有多条会话。
2. 给 `test_stream_has_done_event` 加一条断言：`progress` 帧里必须含 `percent` 字段。""",
                "advanced_practice": """对照第 28-1 节的六条需求，做一张验收表：每条需求写出「实现在哪个函数」「被哪个测试覆盖」。
补齐缺失的测试，并说明哪些需求无法用离线测试覆盖、要靠什么手段验证。""",
                "quiz_note": "本节 6 道题：2 道基础理解（挂起为什么不能一直占着请求、`needs_approval` 从哪来）+ 2 道代码阅读（为什么用 `isinstance` 判断、四个测试各覆盖什么）+ 2 道应用练习（验收表、补流式断言）。",
                "summary": """`/ask` 返回 `needs_approval`，`/approve` 用 `Command` 恢复——把挂起变成两个普通请求。
流式接口注意 `payload` 可能为 `None`，结束帧必须有。
四个测试覆盖主干、记忆、审批、流式；再拿需求表逐条验收。""",
                "next_lesson": "课程到这里结束。接下来该你自己加功能了：把笔记落进业务库、把分类换成模型、把检查点换成持久化后端。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-28-05",
                        "name": "接口与验收测试",
                        "goal": "能把整张图包成接口并用离线测试完成验收。",
                        "minutes": 50,
                        "criteria": "能说清挂起如何映射成两个接口，并给出四条验收测试。",
                        "requires": ["langgraph-agent-28-04"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-28-05-1",
                        "kp": 0,
                        "title": "补一条验收测试",
                        "description": "补一个测试：用户拒绝审批时，接口返回「已取消」且线程能继续接受新问题。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def test_reject_keeps_thread_usable():
    client.post("/ask", json={"user_id": "t5", "question": "帮我记一条笔记"})
    r = client.post("/reject", json={"user_id": "t5", "question": "帮我记一条笔记"})
    assert r.json()["answer"] == "已取消"
    r2 = client.post("/ask", json={"user_id": "t5", "question": "State 是什么"})
    assert r2.status_code == 200
    assert r2.json()["needs_approval"] is False''',
                        "explanation": "拒绝之后线程必须回到「可继续」状态——这验证的是中断被正确消费，而不是卡在半路。",
                    },
                    {
                        "code": "lg-ex-28-05-2",
                        "kp": 0,
                        "title": "写验收表",
                        "description": "对照六条需求，写出每条「实现在哪」「由哪个测试覆盖」，并指出哪条无法离线验证。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": """| 需求 | 实现 | 覆盖 |
| --- | --- | --- |
| 识别用户问题 | `classify` | `test_ask_returns_answer`（间接）|
| 读取课程相关知识 | `retrieve` / `read_chapter` | 需补：断言 `docs` 非空 |
| 调用允许使用的工具 | 白名单 `ALLOWED` | `test_note_requires_approval`（负向）|
| 保存对话状态 | `compile(checkpointer=...)` | `test_thread_keeps_history` |
| 根据条件选择工作流 | 条件边 + 路由表 | 需补：四类问题各一条路径断言 |
| 通过 FastAPI 提供接口 | `/ask` `/approve` `/ask/stream` | 四个接口测试 |

无法离线验证的部分：回答的**质量**（准不准、有没有幻觉）。它需要真模型 + 评测集，
用人工打分或模型评审，属于「效果评估」而非「结构测试」。

这张表的价值在于：每条需求都有一个可以指认的落点。指不出来的，就是没做完——
不管代码写了多少行。""",
                        "explanation": "验收的标准是「能指认」，不是「感觉做完了」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-28-05-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "图需要人工审批时，接口应该怎么设计？",
                        "options": [
                            ("A", "让 `/ask` 请求一直挂着等用户点"),
                            ("B", "`/ask` 返回 `needs_approval`，前端再调 `/approve` 恢复"),
                            ("C", "轮询问前端有没有决定"),
                            ("D", "直接返回 500"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "挂起映射成两个普通请求：一个返回「在等审批」，一个提交结论。既不超时，也不需要长连接。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-05-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`needs_approval` 应该由接口自己维护一个布尔状态位。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "直接看返回里有没有 `__interrupt__`。自己维护状态位迟早和真实状态不一致。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-28-05-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "流式生成器里为什么要先判断 `isinstance(update, dict)`？",
                        "options": [
                            ("A", "`updates` 里某些节点的 payload 可能是 `None`"),
                            ("B", "为了类型提示"),
                            ("C", "因为 `dict` 更省内存"),
                            ("D", "因为 `chunk` 永远是列表"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "节点返回空时 payload 是 `None`，直接下标会 `TypeError`。这个错误在流式里表现是「连接断了」。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-05-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`test_thread_keeps_history` 断言 4 条消息，它实际验证了什么？",
                        "options": [
                            ("A", "模型能生成两条消息"),
                            ("B", "检查点按线程累积了两轮对话，记忆生效"),
                            ("C", "接口被调用了四次"),
                            ("D", "`add_messages` 会去重"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "两轮各「用户 + 回答」共 4 条。若检查点没生效，第二次只有 2 条。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-28-05-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "六条需求里，哪一条无法用离线测试验证？该怎么验证？",
                        "options": [],
                        "answer": """「读取课程相关知识」的**质量**，或者说回答是否准确，无法用离线测试验证。

离线测试能验证的是结构：`docs` 有没有被写入、长度是否大于 0、是否来自正确的支路。
但「检索到的资料对不对」「回答有没有编造」需要真实语义判断。

验证手段有三类：

① 评测集：准备 50—100 条真实问题与标准答案，用真模型跑，人工或模型评审打分。

② 对比实验：改 Prompt 或检索策略前后各跑一遍，看指标变化，避免「感觉变好了」。

③ 线上观察：用户追问率、点踩率、人工修正次数。这些是最真实的反馈。

注意这三类都带统计波动，不适合放进「必须全绿」的 CI 门禁。正确做法是两层分开：
结构测试每次提交必跑；效果评估定期跑，看趋势。""",
                        "explanation": "能自动化的验证结构，不能自动化的用评测与数据说话——别混为一谈。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-28-05-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个测试：同一用户两轮提问后，线程里应有 4 条消息。",
                        "options": [],
                        "answer": {
                            "value": "def test_thread_keeps_history():\n    client.post(\"/ask\", json={\"user_id\": \"t2\", \"question\": \"第一问\"})\n    client.post(\"/ask\", json={\"user_id\": \"t2\", \"question\": \"第二问\"})\n    cfg = {\"configurable\": {\"thread_id\": \"t2:main\"}}\n    messages = graph.get_state(cfg).values[\"messages\"]\n    assert len(messages) == 4, f\"两轮应有 4 条消息，实际 {len(messages)}\""
                        },
                        "explanation": "关键是「通过接口发请求，直接读图的状态」——这样既验证了接口，也验证了检查点，不用去解析响应体。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
