"""LangGraph Agent 开发：第 5—9 章。

这五章是「拆零件」：Graph 讲结构，State 讲数据，Node 讲函数，Edge 讲走向，
StateGraph 才把它们组装起来。前四节刻意不建图——用纯数据结构和普通函数演示，
让读者在没有框架干扰的情况下看清每个概念本身的形状。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 5 章
    {
        "code": "langgraph-agent-05",
        "order_index": 5,
        "title": "Graph",
        "description": "用图的语言描述流程：谁在跑，跑完去哪。",
        "lessons": [
            {
                "code": "langgraph-agent-05-lesson-01",
                "title": "图、节点与边",
                "objectives": """1. 能用「节点 + 边」描述一个流程，并区分有向图与树；
2. 能判断一张图里哪些节点不可达、是否存在环；
3. 能解释为什么有环不一定是错误——循环也是一种合法的图结构；
4. 能说出「入口唯一」这个约束在工程上的意义。""",
                "why_learn": """图的第一个好处不是「跑得快」，而是「能被检查」。
一个流程能不能走通、有没有死路、会不会绕不回来，都可以在动手写节点之前先算出来。""",
                "concepts": """**节点**：图里的一个步骤，用名字标识。
**边**：从一个节点指向另一个节点的箭头，表示「做完 A 之后去 B」。
**有向图**：边有方向，A→B 不等于 B→A。
**可达性**：从入口出发能不能走到某个节点；走不到就是死节点。
**环**：沿着边能回到自己。Agent 的「再来一轮」本质上就是环，但必须有出口。""",
                "plain": """把流程画成地铁线路图就懂了：站点是节点，线路是边，箭头是方向。
有些站根本不在任何一条线路上——那就是写了但没接上的死节点。
有些线路绕一圈回到原点——那就是环，能不能坐回来取决于有没有「出站口」。""",
                "syntax": """**本节术语**

```text
EDGES   邻接表：节点 -> 后继节点列表
ENTRY   入口节点，整张图从这里开始
可达      从入口能走到的节点集合
环        能沿着边回到自身的路径
拓扑序    把有环图去掉环之后的线性顺序
```

- 可达性用广度优先，环检测用深度优先三色标记（未访问 / 在栈上 / 已完成）。
- 本节不引入框架，只用字典和列表。""",
                "example_code": '''EDGES: dict[str, list[str]] = {
    "classify": ["retrieve", "smalltalk"],
    "retrieve": ["summarize"],
    "summarize": ["answer"],
    "answer": [],
    "smalltalk": [],
}
ENTRY = "classify"


def reachable(start: str, edges: dict[str, list[str]]) -> list[str]:
    """广度优先：从入口出发能走到哪些节点。"""
    seen: list[str] = []
    queue = [start]
    while queue:
        node = queue.pop(0)
        if node in seen:
            continue
        seen.append(node)
        queue.extend(edges.get(node, []))
    return seen


def find_cycle(edges: dict[str, list[str]]) -> list[str] | None:
    """深度优先三色标记：0 未访问、1 在栈上、2 已完成。"""
    color: dict[str, int] = {node: 0 for node in edges}
    stack: list[str] = []

    def dfs(node: str) -> list[str] | None:
        color[node] = 1
        stack.append(node)
        for nxt in edges.get(node, []):
            if color.get(nxt, 0) == 1:
                return stack[stack.index(nxt):] + [nxt]
            if color.get(nxt, 0) == 0:
                found = dfs(nxt)
                if found:
                    return found
        color[node] = 2
        stack.pop()
        return None

    for node in edges:
        if color[node] == 0:
            found = dfs(node)
            if found:
                return found
    return None


print("入口：", ENTRY)
print("可达节点：", reachable(ENTRY, EDGES))
print("不可达节点：", sorted(set(EDGES) - set(reachable(ENTRY, EDGES))))
print("是否有环：", find_cycle(EDGES))

LOOPED = dict(EDGES)
LOOPED["answer"] = ["classify"]
print()
print("加入回边后：")
print("  可达节点：", reachable(ENTRY, LOOPED))
print("  环：", " -> ".join(find_cycle(LOOPED) or []))''',
                "code_lines": """1. `EDGES` 是邻接表，用普通字典就能完整描述一张有向图。
2. `reachable` 用队列做广度优先，`seen` 同时承担去重和结果收集。
3. `set(EDGES) - set(reachable(...))` 直接算出「写了但接不上」的死节点。
4. `find_cycle` 用三种颜色区分未访问、正在访问、已完成，这是有向图环检测的标准写法。
5. 当遇到「正在栈上」的节点，说明绕回来了，`stack.index(nxt)` 截出环的起点。
6. `LOOPED` 造了一条 `answer → classify` 的回边，用来对比有环与无环的差别。
7. 输出显示：加回边后可达节点不变，但环被识别出来——说明有环不等于不可达。""",
                "output": """# 程序输出
入口： classify
可达节点： ['classify', 'retrieve', 'smalltalk', 'summarize', 'answer']
不可达节点： []
是否有环： None

加入回边后：
  可达节点： ['classify', 'retrieve', 'smalltalk', 'summarize', 'answer']
  环： classify -> retrieve -> summarize -> answer -> classify""",
                "mistakes": """- 只写了节点没连边，节点成了永远执行不到的孤岛。
- 把「有环」直接当成错误，结果把合法的重试循环也删了。
- 一张图里有两个入口，执行器不知道从哪个开始。
- 用递归做环检测但不标记「已完成」，重复访问同一子图，复杂度暴涨。
- 只看代码不看结构，漏掉「某条分支走到死路」的问题。""",
                "error_analysis": """某个节点永远不执行
—— 它不在任何一条从入口出发的路径上。先算可达集合，再看差集。

流程跑不完
—— 存在环且没有出口。用 `find_cycle` 定位环，再检查环上哪个节点应该有条件出边。

`RecursionError` 在环检测里出现
—— 递归深度等于路径长度。图很大时改成显式栈迭代。""",
                "beginner_practice": """1. 在 `EDGES` 里加一个 `citation` 节点但不连边，观察「不可达节点」的变化。
2. 把 `retrieve` 的后继改成 `["summarize", "answer"]`，看是否产生新的分支。""",
                "advanced_practice": """写一个 `topological_order(edges)`：当图无环时返回一个可执行顺序，有环时返回 `None` 并指出环的位置。
说明为什么真实的 Agent 图经常不是无环的，以及此时「顺序」这个概念要怎么退化。""",
                "quiz_note": "本节 6 道题：2 道基础理解（节点与边、可达性）+ 2 道代码阅读（读可达集合、读环检测）+ 2 道应用练习（找死节点、判断有环是否合理）。",
                "summary": """图 = 节点 + 有向边；结构本身可以被检查。
可达性回答「能不能走到」，环检测回答「会不会绕回来」。
有环不是错误，没有出口的环才是。""",
                "next_lesson": "下一章拆第二个零件：图里流转的数据——State。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-05-01",
                        "name": "有向图的节点、边、可达性与环",
                        "goal": "能用邻接表描述流程，并检查可达性与环。",
                        "minutes": 30,
                        "criteria": "能算出可达节点集合与死节点，并说明有环与死循环的区别。",
                        "requires": ["langgraph-agent-04-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-05-01-1",
                        "kp": 0,
                        "title": "找出死节点",
                        "description": "给定邻接表，写一段代码列出所有从入口不可达的节点。\n\n```python\nEDGES = {\"a\": [\"b\"], \"b\": [\"c\"], \"c\": [], \"orphan\": [\"b\"], \"dead\": []}\n```",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''seen = reachable("a", EDGES)
dead = sorted(set(EDGES) - set(seen))
print("不可达：", dead)   # ['dead', 'orphan']''',
                        "explanation": "`orphan` 虽然有出边，但没人指向它，所以从入口走不到——有出边不等于可达。",
                    },
                    {
                        "code": "lg-ex-05-01-2",
                        "kp": 0,
                        "title": "有环是不是 bug",
                        "description": "Agent 图里出现环，一定说明设计有问题吗？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''不一定。Agent 的核心机制「调工具→看结果→再决定」本身就是环，没有环就无法多轮推进。

判断标准不是「有没有环」，而是「环上有没有出口」：

- 环上有条件出边，且条件一定会随状态推进而满足 → 合法，例如「最多重试 3 次」。
- 环上没有任何出边，或条件永远不满足 → 死循环，必须修。

工程上还要加第二道保险：步数上限。因为「条件最终会满足」这件事依赖模型输出，不能只靠推理保证。''',
                        "explanation": "把「有环」和「死循环」分开，是理解 Agent 图结构的关键一步。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-05-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "图里的「边」表示什么？",
                        "options": [
                            ("A", "节点之间的数据格式"),
                            ("B", "执行顺序：做完 A 之后去 B"),
                            ("C", "节点的执行时间"),
                            ("D", "节点的数量"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "边描述的是控制流走向，不是数据格式；数据由 State 描述。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-05-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "一个节点只要写了出边，就一定能从入口到达。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "可达性看的是「有没有从入口过来的路径」。有出边的孤立节点照样不可达。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-05-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "原图的可达节点里包含 `smalltalk` 吗？",
                        "options": [
                            ("A", "包含，因为 classify 有指向它的边"),
                            ("B", "不包含，它是孤立节点"),
                            ("C", "不包含，因为它没有出边"),
                            ("D", "无法判断"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`classify` 的出边里包含 `smalltalk`，广度优先会走到它。没有出边只代表它是终点，不影响可达。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-05-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`find_cycle` 里 `color[node] == 1` 代表什么？",
                        "options": [
                            ("A", "节点已完成"),
                            ("B", "节点正在当前递归栈上，还没退出"),
                            ("C", "节点从未访问"),
                            ("D", "节点是入口"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "1 表示「在栈上」。遇到栈上的节点说明绕回来了，这就是环的判定依据。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-05-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么工程上要求 Agent 图只有唯一入口？",
                        "options": [],
                        "answer": {"value": """执行器需要一个确定的起点来初始化状态和调度。多个入口意味着「同一次运行该从哪开始」变成不确定，调用方必须额外传参指定，而这层信息很快就会和业务参数混在一起。

替代方案不是多入口，而是「单入口 + 入口处的条件路由」：所有请求都进同一个入口节点，由它在图内部决定去哪。这样入口稳定，分叉逻辑集中在可测试的一个函数里。"""},
                        "explanation": "把「分叉」放在图内部而不是入口处，是可控性的来源。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-05-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个 `has_path(edges, src, dst)`：判断从 `src` 是否存在一条路径到达 `dst`，返回布尔值。",
                        "options": [],
                        "answer": {"value": "def has_path(edges: dict[str, list[str]], src: str, dst: str) -> bool:\n    if src == dst:\n        return True\n    seen = {src}\n    queue = [src]\n    while queue:\n        node = queue.pop(0)\n        for nxt in edges.get(node, []):\n            if nxt == dst:\n                return True\n            if nxt not in seen:\n                seen.add(nxt)\n                queue.append(nxt)\n    return False"},
                        "explanation": "这是可达性的单点版本，测试「某条分支是否真能走通」时最常用，比打印整张图快。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ---------------------------------------------------------------- 第 6 章
    {
        "code": "langgraph-agent-06",
        "order_index": 6,
        "title": "State",
        "description": "状态是图的血液，定义好它后面才稳。",
        "lessons": [
            {
                "code": "langgraph-agent-06-lesson-01",
                "title": "状态结构与类型约束",
                "objectives": """1. 能用 `TypedDict` 定义一个图的 State；
2. 能区分「必填键」与「可选键」，并说清它们在运行期的真实约束；
3. 能解释为什么 `TypedDict` 不做运行期校验，以及这对调试意味着什么；
4. 能设计一份「字段够用但不冗余」的状态结构。""",
                "why_learn": """状态是节点之间唯一的通信方式。
字段少了要反复重算，字段多了每个节点都在猜「这个键现在是什么」，两种都会让图变得难改。""",
                "concepts": """**State**：一份在整个图里共享的数据结构，所有节点读它、写它的增量。
**`TypedDict`**：用类语法声明「有哪些键、各是什么类型」，运行期仍是普通 `dict`。
**必填键**：默认所有声明的键都是必填；用 `NotRequired` 标可选，或用 `total=False` 全可选。
**运行期不校验**：类型注解只服务静态检查器，赋值错类型不会报错，直到用的时候才炸。
**设计原则**：只放「节点之间需要共享」的东西，中间变量留在节点内部。""",
                "plain": """State 像一张贴在工位之间的交接单：上一道工序把结果写上去，下一道工序照着单子干活。
单子上印了「数量：数字」这一栏，但没人真去核对——你填了「三箱」，单子也照样传下去，
直到仓库真正去数的时候才发现不对。类型注解就是那行印刷体，靠自觉，不靠强制。""",
                "syntax": """**State 定义**

```python
from typing import TypedDict

class State(TypedDict):
    question: str
    answer: str
    sources: list[str]
    steps: int
```

**可选字段**

```python
from typing import NotRequired

class State(TypedDict):
    question: str
    error: NotRequired[str]
```

- `State.__required_keys__` 与 `__optional_keys__` 可以在运行期查看必填与可选键。
- `State.__annotations__` 给出每个字段的声明类型。
- 这三个属性在调试「字段到底叫什么」时非常有用。""",
                "example_code": '''from typing import TypedDict


class State(TypedDict):
    question: str
    answer: str
    sources: list[str]
    steps: int


def init_state(question: str) -> State:
    return {"question": question, "answer": "", "sources": [], "steps": 0}


print("必填键：", sorted(State.__required_keys__))
print("可选键：", sorted(State.__optional_keys__))
print("字段类型：", State.__annotations__)
print()

state = init_state("State 是什么")
print("初始状态：", state)

# TypedDict 只在静态检查阶段起作用，运行期完全不校验
state["steps"] = "三步"          # type: ignore[typeddict-item]
print("把 steps 写成字符串后：", state["steps"], "| 类型：", type(state["steps"]).__name__)

extra = {"question": "只有问题"}
print("只给一个键也不报错：", extra)
print()

# 真实事故形态：字符串拼数字
try:
    print(state["steps"] + 1)
except TypeError as exc:
    print("运行到用时才炸：", exc)''',
                "code_lines": """1. `TypedDict` 用类语法声明键和类型，比裸 dict 多了静态检查能力。
2. `__required_keys__` 列出必填键，本例四个键全是必填。
3. `__optional_keys__` 为空，因为没用 `NotRequired` 标可选。
4. `__annotations__` 打印出 `steps` 声明为 `int`，可作为「文档」直接看。
5. 把 `steps` 赋成中文数字，Python 完全不拦——这是运行期不校验的直接证据。
6. 只给一个键的 dict 也能创建，缺键同样不报错。
7. 直到执行加法时才抛 `TypeError`，说明错误被推迟到了「用」的那一刻。""",
                "output": """# 程序输出
必填键： ['answer', 'question', 'sources', 'steps']
可选键： []
字段类型： {'question': <class 'str'>, 'answer': <class 'str'>, 'sources': list[str], 'steps': <class 'int'>}

初始状态： {'question': 'State 是什么', 'answer': '', 'sources': [], 'steps': 0}
把 steps 写成字符串后： 三步 | 类型： str
只给一个键也不报错： {'question': '只有问题'}

运行到用时才炸： can only concatenate str (not "int") to str""",
                "mistakes": """- 以为定义了 `TypedDict` 就有运行期校验，线上被字符串污染后查很久。
- 把所有中间变量都塞进 State，字段越来越多，没人能说清每个键的语义。
- 该可选的字段设成必填，调用方每次都要传一堆空值。
- 字段名用 `data`、`info` 这类含糊词，半年后自己也不知道里面是什么。
- 用 `dict` 代替 `TypedDict`，IDE 补全和静态检查全部失效。""",
                "error_analysis": """`KeyError: 'sources'`
—— 节点读了 State 里没有的键，或调用方传入时漏了必填键。先用 `__required_keys__` 核对。

`TypeError: can only concatenate str (not "int") to str`
—— 某个字段被写成了错误类型。`TypedDict` 不会帮你拦，要在节点入口处自己校验。

`TypeError: 'type' object is not subscriptable`
—— 用了 `list[str]` 但 Python 版本低于 3.9。本课程要求 3.10 以上。""",
                "beginner_practice": """1. 给 State 加一个 `NotRequired` 的 `error` 字段，观察必填/可选键的变化。
2. 写一个 `validate(state)`，检查 `steps` 是不是 `int`，不是就抛带字段名的异常。""",
                "advanced_practice": """同一个业务流程，如果要求「状态字段不超过 5 个」，你会把哪些字段挪到节点内部？
给出取舍标准，并说明挪走之后「重跑某一步」还能不能复现。""",
                "quiz_note": "本节 6 道题：2 道基础理解（State 的作用、TypedDict 的约束力）+ 2 道代码阅读（读必填键、读类型不校验）+ 2 道应用练习（设计字段、写校验）。",
                "summary": """State 是节点之间唯一的通信通道，字段设计直接决定图好不好改。
`TypedDict` 提供声明与静态检查，不提供运行期校验。
运行期的问题要在节点入口自己校验，别指望类型注解。""",
                "next_lesson": "下一节看状态在节点之间到底怎么被读写和合并。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-06-01",
                        "name": "State 结构定义与类型约束",
                        "goal": "能用 TypedDict 定义状态，并说清必填/可选与运行期行为。",
                        "minutes": 35,
                        "criteria": "能写出含必填与可选字段的 State，并解释为什么需要在运行时自行校验。",
                        "requires": ["langgraph-agent-05-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-06-01-1",
                        "kp": 0,
                        "title": "加一个可选字段",
                        "description": "给 State 加 `error: NotRequired[str]`，并写 `has_error(state)` 判断是否出错。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''from typing import NotRequired, TypedDict


class State(TypedDict):
    question: str
    answer: str
    sources: list[str]
    steps: int
    error: NotRequired[str]


def has_error(state: State) -> bool:
    return bool(state.get("error"))''',
                        "explanation": "可选字段要用 `.get()` 读，直接 `state[\"error\"]` 会 `KeyError`——这是可选字段最常见的坑。",
                    },
                    {
                        "code": "lg-ex-06-01-2",
                        "kp": 0,
                        "title": "字段该不该进 State",
                        "description": "「调用模型时用的 temperature」这个值该放进 State 吗？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''默认不该。判据是：**这个值需要在两个及以上节点之间共享，或被持久化、被人工修改吗？**

- 如果只有「调模型」那一个节点用，它属于配置，应该放在节点外部（构造时注入），放进 State 只会让状态里混入不变的常量。
- 如果用户可以在界面上调温度，并且后续节点需要知道「这次回答是用什么温度生成的」，那它就有了共享语义，可以进 State。
- 如果要做 A/B 对比并回放历史，温度也需要持久化，进 State 就合理。

结论：State 放「会随流程变化、且多方需要读」的数据；静态配置放节点外部。''',
                        "explanation": "字段进不进 State，本质是问「它是不是流程的一部分」，而不是「它有没有用」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-06-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "State 在图里的作用是什么？",
                        "options": [
                            ("A", "保存代码"),
                            ("B", "在节点之间共享数据"),
                            ("C", "控制节点数量"),
                            ("D", "定义边的方向"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "节点不直接互相调用，全靠读写同一份状态来传递信息。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-06-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "定义 `TypedDict` 后，给字段赋错误类型会立刻抛出异常。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`TypedDict` 只服务静态检查，运行期就是普通 dict，赋值不做类型校验。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-06-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `__optional_keys__` 为什么是空的？",
                        "options": [
                            ("A", "因为 Python 版本太低"),
                            ("B", "因为四个字段都没标 `NotRequired`"),
                            ("C", "因为 State 没有初始化"),
                            ("D", "因为用了 TypedDict"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`TypedDict` 默认所有键都是必填，只有显式标注 `NotRequired` 或 `total=False` 才会进可选集合。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-06-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`state[\"steps\"] = \"三步\"` 之后执行 `state[\"steps\"] + 1` 的结果是？",
                        "options": [
                            ("A", "返回 4"),
                            ("B", "返回「三步1」"),
                            ("C", "抛 TypeError"),
                            ("D", "返回 None"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "字符串不能和整数相加，异常被推迟到使用处才出现——这正是运行期不校验的代价。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-06-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说「字段太多」和「字段太少」都会让图难维护？",
                        "options": [],
                        "answer": {"value": """字段太少时，节点之间无法传递必要信息，只能重复计算或去查外部数据，既慢又容易不一致；改动一处逻辑要连带改多个节点的取数方式。

字段太多时，状态变成一个大口袋：每个节点都要判断「这个键现在有没有值、是谁写的」，可空字段的组合爆炸；持久化时把大量中间变量一起写盘，回放和迁移成本上升；新人接手无法判断哪些字段是契约、哪些是临时产物。

合适的粒度是「节点之间确实需要共享的最小集合」，中间变量留在节点内部。"""},
                        "explanation": "状态设计是这门课里最容易返工的部分，一开始多花十分钟定字段，后面能省几小时。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-06-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写 `validate_state(state)`：缺必填键或 `steps` 不是 int 时，抛出带字段名的 `ValueError`。",
                        "options": [],
                        "answer": {"value": "def validate_state(state: dict) -> None:\n    for key in State.__required_keys__:\n        if key not in state:\n            raise ValueError(f\"缺少必填字段：{key}\")\n    if not isinstance(state[\"steps\"], int):\n        raise ValueError(f\"steps 应为 int，实际是 {type(state['steps']).__name__}\")"},
                        "explanation": "把校验做成一个函数，在图的入口调用一次，就能把「运行到一半才炸」提前到「进来的第一秒就炸」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-06-lesson-02",
                "title": "状态的读写与生命周期",
                "objectives": """1. 能说清节点「读全量、写增量」的规则；
2. 能手动模拟执行器的合并过程，并预测每一步的状态；
3. 能解释为什么「覆盖式合并」会让累积型字段丢数据；
4. 能判断一个字段该用覆盖还是累加语义（为第 15 章 Reducer 铺垫）。""",
                "why_learn": """很多人写图时最大的困惑是「我明明 append 了，为什么最后只有一条」。
答案就在合并规则里：默认是覆盖，不是累加。""",
                "concepts": """**读全量**：节点收到的参数是合并后的完整状态。
**写增量**：节点只返回要改的字段，不必回传整份状态。
**默认合并**：同名键被返回值覆盖（相当于 `dict.update`）。
**累积需求**：来源列表、消息历史这类字段需要「追加」而不是「替换」。
**合并规则的位置**：默认规则写在执行器里，累积语义要靠 Reducer 声明（第 15 章）。""",
                "plain": """交接单传下去，下一道工序只在「结果」那一栏写上自己的结论，其他栏不动——这叫写增量。
如果他把整张单子重抄一遍、只抄自己记得的内容，前面写的就全丢了——这叫覆盖。
真实事故几乎都是后者：不是没写，是被覆盖了。""",
                "syntax": """**合并规则**

```python
merged = dict(state)      # 先复制旧状态
merged.update(update)     # 再用返回值覆盖同名键
```

- 节点返回值里**没有**的键，保持原值。
- 节点返回值里**有**的键，整值替换，不做智能合并。
- 想让列表累加，必须在返回值里自己算好新列表，或声明 Reducer。""",
                "example_code": '''def apply_update(state: dict, update: dict) -> dict:
    """执行器的合并规则：同名字段被 update 覆盖。"""
    merged = dict(state)
    merged.update(update)
    return merged


state = {"question": "State 是什么", "answer": "", "sources": ["大纲"], "steps": 0}
print("初始：", state)

step1 = apply_update(state, {"answer": "草稿：状态是共享数据", "steps": state["steps"] + 1})
print("节点 1 后：", step1)

step2 = apply_update(step1, {"answer": step1["answer"] + "（已校对）", "steps": step1["steps"] + 1})
print("节点 2 后：", step2)

# 覆盖式合并的陷阱：新来源把旧来源整个替换掉
step3 = apply_update(step2, {"sources": ["第 6 章"]})
print("节点 3 后：", step3)
print("注意 sources 从", step2["sources"], "变成了", step3["sources"], "——旧值被覆盖")
print()


# 想累加就必须显式写合并逻辑
def merge_sources(old: list[str], new: list[str]) -> list[str]:
    result = list(old)
    for item in new:
        if item not in result:
            result.append(item)
    return result


step4 = apply_update(step3, {"sources": merge_sources(step3["sources"], ["第 13 章"])})
print("手动累加后：", step4["sources"])
print()

# 原始 state 没有被改动，说明 apply_update 返回新对象
print("原始 state 仍是：", state)
print("是同一个对象吗：", state is step4)''',
                "code_lines": """1. `apply_update` 只有两行，但这就是执行器合并状态的全部秘密。
2. `dict(state)` 先复制，保证不修改传入的旧状态。
3. 节点 1 只返回两个字段，`question` 和 `sources` 原样保留。
4. 节点 2 读取 `step1["answer"]` 累加文字，说明节点能看到上游写入的值。
5. 节点 3 返回 `{"sources": ["第 6 章"]}`，旧值 `["大纲"]` 被整组替换。
6. `merge_sources` 显式算好合并结果，再交给覆盖式规则——效果等价于累加。
7. 最后比较 `is`，证明每次合并都产生新对象，旧状态不被污染。""",
                "output": """# 程序输出
初始： {'question': 'State 是什么', 'answer': '', 'sources': ['大纲'], 'steps': 0}
节点 1 后： {'question': 'State 是什么', 'answer': '草稿：状态是共享数据', 'sources': ['大纲'], 'steps': 1}
节点 2 后： {'question': 'State 是什么', 'answer': '草稿：状态是共享数据（已校对）', 'sources': ['大纲'], 'steps': 2}
节点 3 后： {'question': 'State 是什么', 'answer': '草稿：状态是共享数据（已校对）', 'sources': ['第 6 章'], 'steps': 2}
注意 sources 从 ['大纲'] 变成了 ['第 6 章'] ——旧值被覆盖

手动累加后： ['第 6 章', '第 13 章']

原始 state 仍是： {'question': 'State 是什么', 'answer': '', 'sources': ['大纲'], 'steps': 0}
是同一个对象吗： False""",
                "mistakes": """- 以为 `return {"sources": ["新值"]}` 是「追加」，实际是「整组替换」。
- 节点里直接 `state["sources"].append(...)` 再返回整份状态，破坏不可变性。
- 返回整份状态而不是增量，导致上游的修改被旧快照覆盖。
- 依赖「合并顺序」做逻辑，一旦并行执行顺序变化结果就变。
- 用同一个字段既做累积又做重置，语义含混。""",
                "error_analysis": """累积列表最后只剩一条
—— 每次返回的是新列表而不是合并后的列表，覆盖规则把前面的全丢了。

`InvalidUpdateError: At key 'xxx': Can receive only one value per step`
—— 同一步有多个节点写同一个键。需要 Reducer（第 15 章）。

某字段莫名回到初始值
—— 某个节点返回了整份状态快照（含旧值），覆盖了中间节点的更新。""",
                "beginner_practice": """1. 把 `step3` 的返回值改成 `{"sources": merge_sources(step2["sources"], ["第 6 章"])}`，观察变化。
2. 在节点 2 里故意返回整份 `step1`，看 `steps` 会不会倒退。""",
                "advanced_practice": """设计一份「谁能写哪个字段」的约定表（读/写矩阵），说明它如何避免两个节点互相覆盖，
并指出这份约定在并行执行时会遇到什么新问题。""",
                "quiz_note": "本节 6 道题：2 道基础理解（读全量写增量、默认合并规则）+ 2 道代码阅读（预测状态、识别覆盖）+ 2 道应用练习（改累加、设计读写矩阵）。",
                "summary": """节点读全量、写增量，执行器按「同键覆盖」合并。
列表类字段默认会被替换，想累加必须显式处理。
合并永远产生新对象，旧状态不被污染——这是能回放的前提。""",
                "next_lesson": "下一章拆第三个零件：Node，也就是写这些返回值的函数。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-06-02",
                        "name": "状态的读取与增量合并规则",
                        "goal": "能预测每一步合并后的状态，并识别覆盖导致的丢数据。",
                        "minutes": 35,
                        "criteria": "能手写合并函数复现覆盖行为，并说明累加语义需要什么机制。",
                        "requires": ["langgraph-agent-06-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-06-02-1",
                        "kp": 0,
                        "title": "追加而不是替换",
                        "description": "现有节点写成 `return {\"sources\": [\"第 7 章\"]}`，导致旧来源丢失。改成追加语义。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def add_sources(state: dict) -> dict:
    return {"sources": [*state["sources"], "第 7 章"]}''',
                        "explanation": "用解包构造新列表，既实现追加又不修改原列表——两个要求同时满足。",
                    },
                    {
                        "code": "lg-ex-06-02-2",
                        "kp": 0,
                        "title": "为什么不能直接 append",
                        "description": "`state[\"sources\"].append(\"第 7 章\")` 然后 `return state` 有什么问题？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''三个问题：

① 修改了传入的对象。执行器传进来的状态可能被其它节点共享或已持久化，就地修改会让「历史快照」跟着变，回放结果不再可复现。
② 返回整份状态，等于把旧值一起写回。若此期间别的字段被更新过，会被这份旧快照覆盖。
③ 副作用让节点不再纯：同一个节点用同一份输入跑两次，第二次列表里会多一条，测试无法稳定断言。

正确写法是构造新列表返回增量。''',
                        "explanation": "「不改入参、只返增量」既是框架要求，也是可测试性的前提。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-06-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "节点返回 `{\"answer\": \"新\"}` 时，状态里其它字段会怎样？",
                        "options": [
                            ("A", "被清空"),
                            ("B", "保持不变"),
                            ("C", "变成 None"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "只覆盖返回值里出现的键，没出现的键保持原值——这正是「写增量」的意义。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-06-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "节点返回 `{\"sources\": [\"新\"]}` 会把新值追加到原有列表后面。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "默认合并是整值替换，不是追加。想追加必须自己把旧列表和新值拼好。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-06-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "节点 2 之后 `steps` 是多少？",
                        "options": [
                            ("A", "0"),
                            ("B", "1"),
                            ("C", "2"),
                            ("D", "3"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "每个节点都在上一轮基础上 `+1`，两次累加得到 2。这说明节点读到的确实是合并后的最新值。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-06-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`state is step4` 为 False 说明什么？",
                        "options": [
                            ("A", "合并失败了"),
                            ("B", "每次合并都产生新对象，原状态未被修改"),
                            ("C", "状态里有可变对象"),
                            ("D", "steps 类型不对"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "返回新对象是「不可变更新」的实现方式，保证历史快照不被后续修改影响。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-06-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「同一步内两个节点写同一个键」会被框架拒绝？",
                        "options": [],
                        "answer": {"value": """因为默认合并规则只能回答「一个值覆盖另一个」，无法回答「两个值怎么合成一个」。如果框架随便选一个，结果就依赖执行顺序——并行时顺序不保证，同一份输入可能得到不同结果，这属于不可复现的 bug。

框架的做法是直接报错，要求显式声明合并规则（Reducer）。把「怎么合并」交回给开发者，是保证确定性的唯一办法。"""},
                        "explanation": "这条规则直接引向第 15 章：Reducer 不是可选项，是并行写入的必需品。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-06-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写 `bump(state)`，返回把 `steps` 加一并把 `sources` 追加「新来源」的增量（不修改原状态）。",
                        "options": [],
                        "answer": {"value": "def bump(state: dict) -> dict:\n    return {\n        \"steps\": state[\"steps\"] + 1,\n        \"sources\": [*state[\"sources\"], \"新来源\"],\n    }"},
                        "explanation": "两个字段都用「算好新值再返回」的方式，天然满足不可变要求。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 7 章
    {
        "code": "langgraph-agent-07",
        "order_index": 7,
        "title": "Node",
        "description": "节点是函数：接状态、返增量、不改原对象。",
        "lessons": [
            {
                "code": "langgraph-agent-07-lesson-01",
                "title": "节点是什么",
                "objectives": """1. 能写出符合约定的节点函数：一个参数、返回 dict；
2. 能演示「就地修改入参」带来的真实后果；
3. 能说明节点为什么应该是纯函数；
4. 能判断一段逻辑该拆成几个节点。""",
                "why_learn": """节点是最小的工作单元，也是最容易写坏的地方。
一旦节点偷偷改了入参，整个图的调试就会变成猜谜。""",
                "concepts": """**节点**：接收当前状态、返回要更新的字段的函数。
**纯函数**：同样的输入得到同样的输出，不修改外部状态。
**不改入参**：传进来的状态可能被共享或已持久化，就地修改会污染历史。
**返回增量**：只返回改动的键，不返回整份状态。
**拆分粒度**：一个节点做一件「能被单独测试」的事。""",
                "plain": """节点像流水线上的一道工序：拿到零件（状态），做一个动作，交出结果（增量）。
规矩是「只改自己手里的那份副本」——如果他把手伸回去改上一道工序已经交出去的东西，
后面所有记录就都乱了，出了问题也查不出是哪一道改的。""",
                "syntax": """**节点签名**

```python
def node_name(state: State) -> dict:
    ...
    return {"field": new_value}
```

- 参数只有一个：当前状态。
- 返回值必须是 dict（或 `Command`，第 13 章讲）。
- 返回的键必须在 State 里声明过，否则报错。
- 节点内可以 `print`，但正式项目应改用结构化日志。""",
                "example_code": '''# 坏节点：直接修改传进来的状态，并返回整份状态
def bad_node(state: dict) -> dict:
    state["sources"].append("坏节点偷偷加的")
    state["answer"] = "坏节点写的"
    return state


# 好节点：不改入参，只返回要更新的字段
def good_node(state: dict) -> dict:
    return {
        "answer": "好节点写的",
        "sources": [*state["sources"], "好节点加的"],
    }


state = {"question": "State 是什么", "answer": "", "sources": ["大纲"]}
print("调用前：", state)

result = bad_node(state)
print("坏节点返回：", result)
print("调用后的原状态：", state, "← 被改动了")
print("是同一个对象吗：", result is state)
print()

fresh = {"question": "State 是什么", "answer": "", "sources": ["大纲"]}
out = good_node(fresh)
print("好节点返回：", out)
print("调用后的原状态：", fresh, "← 没被改动")
print("是同一个对象吗：", out is fresh)''',
                "code_lines": """1. `bad_node` 的 `state["sources"].append(...)` 直接改了传进来的列表对象。
2. 它把 `state` 原样返回，所以返回值就是入参本身——`result is state` 为 True。
3. 打印「调用后的原状态」，可以看到调用方的数据被改了，这是最典型的污染。
4. `good_node` 用解包 `[*state["sources"], "好节点加的"]` 造了一个新列表。
5. 它只返回两个键的增量，`question` 不在返回值里，也就不会被覆盖。
6. `fresh` 调用后保持原样，`out is fresh` 为 False，证明没有共享对象。
7. 同一份逻辑，两种写法在「是否可测试、是否可回放」上差别巨大。""",
                "output": """# 程序输出
调用前： {'question': 'State 是什么', 'answer': '', 'sources': ['大纲']}
坏节点返回： {'question': 'State 是什么', 'answer': '坏节点写的', 'sources': ['大纲', '坏节点偷偷加的']}
调用后的原状态： {'question': 'State 是什么', 'answer': '坏节点写的', 'sources': ['大纲', '坏节点偷偷加的']} ← 被改动了
是同一个对象吗： True

好节点返回： {'answer': '好节点写的', 'sources': ['大纲', '好节点加的']}
调用后的原状态： {'question': 'State 是什么', 'answer': '', 'sources': ['大纲']} ← 没被改动
是同一个对象吗： False""",
                "mistakes": """- 在节点里 `state["list"].append(...)`，以为只改了自己那份。
- 返回整份 `state`，把上游的中间结果一并写回，覆盖掉别的更新。
- 节点里做太多事：检索、调用模型、写库全塞一起，出错无法定位。
- 节点返回值里出现 State 未声明的键，运行时才报错。
- 用全局变量在节点之间传数据，看起来能跑，一并发就串。""",
                "error_analysis": """历史记录莫名变化
—— 某个节点就地修改了可变对象（list/dict），而持久化的快照引用的是同一个对象。

`InvalidUpdateError: Expected dict, got ...`
—— 节点返回了非 dict（例如返回列表、字符串）。检查 return 语句。

某字段在两个节点之间「倒退」
—— 后一个节点返回了整份旧状态快照，覆盖了前一个节点的更新。""",
                "beginner_practice": """1. 把 `good_node` 改成返回整份 `fresh`，再观察 `answer` 与 `sources` 的最终值。
2. 写第三个节点 `note(state)`，返回一个 State 里没有的键，观察报错信息。""",
                "advanced_practice": """把一个「检索 + 摘要 + 引用标注」的节点拆成三个，说明拆分依据（可否单独测试、是否会被复用），
并指出拆完之后状态里需要新增哪些字段。""",
                "quiz_note": "本节 6 道题：2 道基础理解（节点约定、纯函数的意义）+ 2 道代码阅读（读对象同一性、读污染后果）+ 2 道应用练习（改写节点、判断拆分粒度）。",
                "summary": """节点 = 一个参数 + 一个 dict 返回值。
不修改入参、只返回增量，这两条决定了图能不能被可靠调试。
一个节点只做一件能单独测试的事。""",
                "next_lesson": "下一章拆第四个零件：Edge，也就是节点之间的走向。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-07-01",
                        "name": "节点函数的约定与纯函数写法",
                        "goal": "能写出不改入参、只返增量的节点，并说明就地修改的危害。",
                        "minutes": 30,
                        "criteria": "能对比「就地修改」与「构造新值」两种写法的结果差异。",
                        "requires": ["langgraph-agent-06-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-07-01-1",
                        "kp": 0,
                        "title": "修好这个节点",
                        "description": "把下面的节点改成不修改入参的版本。\n\n```python\ndef add_tag(state: dict) -> dict:\n    state[\"tags\"].append(\"new\")\n    return state\n```",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def add_tag(state: dict) -> dict:
    return {"tags": [*state["tags"], "new"]}''',
                        "explanation": "只改返回值一处就能修好：用解包造新列表，返回增量而不是整份状态。",
                    },
                    {
                        "code": "lg-ex-07-01-2",
                        "kp": 0,
                        "title": "为什么这事在测试里发现不了",
                        "description": "就地修改的节点，单独写单元测试时为什么往往「测试通过」，上线后才出问题？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''因为单元测试通常只断言「返回值对不对」，而就地修改的节点返回值确实是对的。

问题出在测试没覆盖的部分：① 入参是否被改（需要额外断言原对象未变）；
② 与其它节点组合时的行为（前一个节点刚写入的数据被覆盖）；
③ 持久化之后的行为（历史快照被后续修改污染，回放结果不一致）。

这类 bug 的特征是「单点正确、组合错误」，只有集成测试或不可变约定才能拦住。所以更好的办法不是靠测出来，而是用约定 + 代码评审把它挡在门外。''',
                        "explanation": "能被约定消灭的 bug，不要指望测试来发现——测试是兜底，不是第一道防线。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-07-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "一个节点函数的返回值应该是什么？",
                        "options": [
                            ("A", "整份状态"),
                            ("B", "要更新的字段组成的 dict"),
                            ("C", "字符串"),
                            ("D", "None"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "只返回增量，执行器负责与旧状态合并。返回整份状态会把旧值一起写回。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-07-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "节点里 `state[\"list\"].append(x)` 是安全的，因为 state 是局部变量。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "参数是引用，`append` 改的是调用方持有的同一个列表对象。局部变量名不同，对象是同一个。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-07-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`result is state` 为 True 说明什么？",
                        "options": [
                            ("A", "两者内容相同"),
                            ("B", "返回的就是传入的那个对象本身"),
                            ("C", "发生了深拷贝"),
                            ("D", "state 是空的"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`is` 比较的是对象标识。为 True 表示返回值和入参是同一个对象，节点没有构造新值。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-07-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`good_node` 的返回值里为什么没有 `question` 字段？",
                        "options": [
                            ("A", "忘了写"),
                            ("B", "它没有变化，不需要返回，执行器会保留原值"),
                            ("C", "question 是只读字段"),
                            ("D", "question 会被自动删除"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "返回增量意味着「没变的字段不必出现」。少返回反而更安全，不会覆盖别处的更新。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-07-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "什么样的逻辑适合拆成一个独立节点？给出两条判据。",
                        "options": [],
                        "answer": {"value": """① 能被单独测试：给它一份状态，能明确断言输出增量，不需要启动整张图。例如「检索」和「引用标注」都应该各自成节点。
② 会被不止一个位置复用，或有独立的失败处理：例如「调模型」在多条分支里都要用，且需要单独重试策略。

反例：仅仅为了「看起来步骤多」而拆，会让状态字段膨胀、图结构难读。拆分应该由测试与复用驱动，而不是由视觉整齐驱动。"""},
                        "explanation": "节点数量不是越多越好，判据是「可测试性」和「复用/失败处理是否需要独立」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-07-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写 `summarize_node(state)`：读 `state[\"sources\"]`，返回 `{\"answer\": 拼接结果, \"steps\": +1}`，不修改入参。",
                        "options": [],
                        "answer": {"value": "def summarize_node(state: dict) -> dict:\n    joined = \"、\".join(state.get(\"sources\", []))\n    return {\n        \"answer\": f\"依据 {joined} 给出摘要\" if joined else \"暂无资料\",\n        \"steps\": state[\"steps\"] + 1,\n    }"},
                        "explanation": "用 `.get()` 读可能缺失的字段，避免上游没写时直接 `KeyError`。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ---------------------------------------------------------------- 第 8 章
    {
        "code": "langgraph-agent-08",
        "order_index": 8,
        "title": "Edge",
        "description": "用边描述顺序，用 START 和 END 标注边界。",
        "lessons": [
            {
                "code": "langgraph-agent-08-lesson-01",
                "title": "边与入口出口",
                "objectives": """1. 能说明普通边、入口边、出口边各自的职责；
2. 能解释为什么「一个节点两条无条件出边」是设计错误；
3. 能用 `START` / `END` 标清图的两端；
4. 能读懂图里「没有出边 = 结束」与「显式连 END」的差别。""",
                "why_learn": """边写错是图跑不起来的最常见原因：要么没有入口，要么跑完不知道停，
要么一个节点两条出边、执行器不知道走哪条。""",
                "concepts": """**普通边**：`A → B`，A 执行完必定去 B，没有条件。
**入口边**：`START → 第一个节点`，一张图只能有一个入口。
**出口边**：`某个节点 → END`，显式声明流程结束。
**无出边**：执行器视为该分支结束，但结构上不清晰。
**歧义**：一个节点有多条无条件出边时，执行器无法决定去向，必须改用条件边。""",
                "plain": """边就是路口的路牌。普通边是「只能直行」，写死了方向；
入口边是「从大门进」，一栋楼只有一个大门；出口边是「安全出口」，写上才清楚。
如果一个路口立了两块「直行」路牌指向不同方向，司机只能停在那儿——这就是歧义的边。""",
                "syntax": """**两种边**

```python
builder.add_edge(START, "first")        # 入口
builder.add_edge("first", "second")     # 普通边
builder.add_edge("second", END)         # 出口
```

- `START` 与 `END` 是保留常量，不能拿来当节点名。
- 一张图只有一个 `START` 出边；但可以有多个节点连到 `END`。
- 需要「按条件选路」时要声明条件边，具体写法留到第 13 章。""",
                "example_code": '''START = "__start__"
END = "__end__"

EDGES: dict[str, list[str]] = {
    START: ["classify"],
    "classify": ["retrieve"],
    "retrieve": ["summarize"],
    "summarize": [END],
    END: [],
}


def successors(node: str) -> list[str]:
    return EDGES.get(node, [])


def describe(node: str) -> str:
    nxt = successors(node)
    if not nxt:
        return "终点（没有出边）"
    if nxt == [END]:
        return "指向 END"
    return "指向 " + "、".join(nxt)


for node in EDGES:
    print(f"{node:12s} {describe(node)}")
print()

# 反例：一个节点两条无条件出边，执行器无法决定走哪条
AMBIGUOUS = {
    START: ["classify"],
    "classify": ["retrieve", "smalltalk"],   # 两条边，没有条件
    "retrieve": [END],
    "smalltalk": [END],
}


def pick(edges: dict[str, list[str]], node: str) -> str:
    nxt = edges.get(node, [])
    if len(nxt) > 1:
        return f"歧义：{node} 有 {len(nxt)} 条出边，但没有条件可判断"
    return nxt[0] if nxt else "结束"


for node in ("classify", "retrieve"):
    print(f"{node:12s} -> {pick(AMBIGUOUS, node)}")''',
                "code_lines": """1. `START` 与 `END` 用固定字符串表示，图的两端因此在结构上可识别。
2. `EDGES` 里 `START` 只有一条出边，保证入口唯一。
3. `summarize` 指向 `END`，是显式出口，读图时一眼看到流程边界。
4. `END` 自身没有出边，`describe` 会把它识别为「终点」。
5. `AMBIGUOUS` 里 `classify` 有两条出边，但没有任何条件可以判断。
6. `pick` 遇到多条出边时返回「歧义」而不是随便挑一条——真实框架则会直接报错。
7. 对比 `retrieve`：只有一条出边，可以确定地走到 `END`。""",
                "output": """# 程序输出
__start__    指向 classify
classify     指向 retrieve
retrieve     指向 summarize
summarize    指向 END
__end__      终点（没有出边）

classify     -> 歧义：classify 有 2 条出边，但没有条件可判断
retrieve     -> __end__""",
                "mistakes": """- 忘记连 `START`，编译时报「没有入口」。
- 给一个节点连两条普通边，期望「两条都走」，实际是歧义。
- 用 `"start"` 小写当节点名，和内置常量冲突。
- 多个节点都连到 `END` 时以为是错误，其实完全合法。
- 该连 `END` 的地方什么都不连，图能跑但结构上看不出边界。""",
                "error_analysis": """`ValueError: Graph must have an entrypoint`
—— 没有任何 `add_edge(START, ...)`。

流程图里出现两条实线箭头从一个节点出来
—— 用了两次 `add_edge` 而没加条件。改用条件边。

跑到最后一个节点后报「没有后继」
—— 该节点既没连 `END` 也没连别的节点，处于悬空状态。""",
                "beginner_practice": """1. 把 `summarize` 的出边改成空列表，观察 `describe` 的输出变化。
2. 给 `AMBIGUOUS` 加一条从 `classify` 到 `END` 的边，判断歧义是否消失。""",
                "advanced_practice": """用「多出口 + 显式 END」重画一张「成功 / 失败 / 需要人工」三条出口的图，
说明为什么三条出口都要显式连 `END`，而不是让执行器自己判断结束。""",
                "quiz_note": "本节 6 道题：2 道基础理解（边的作用、入口唯一）+ 2 道代码阅读（读结构表、识别歧义）+ 2 道应用练习（补出口、判断多出边是否合法）。",
                "summary": """普通边写死顺序，入口边规定起点，出口边划清终点。
一个节点多条无条件出边是设计错误，必须改成条件边。
显式连 END 让结构自解释，也方便后续加检查。""",
                "next_lesson": "下一章把 State、Node、Edge 三块真正拼起来。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-08-01",
                        "name": "普通边、入口与出口",
                        "goal": "能正确连接入口、普通边与出口，并识别歧义结构。",
                        "minutes": 30,
                        "criteria": "能说明 START/END 的作用，并指出一个节点多出边为什么必须用条件边。",
                        "requires": ["langgraph-agent-07-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-08-01-1",
                        "kp": 0,
                        "title": "消除歧义",
                        "description": "`AMBIGUOUS` 里 `classify` 有两条出边。说明两种合法的修法。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''修法一（条件边）：把两条边改由路由函数决定，函数返回 "retrieve" 或 "smalltalk"。

修法二（加中间节点）：classify 只连一个 "dispatch" 节点，由 dispatch 内部判断后
用条件边或 Command 跳转。

两种修法的共同点：把「走哪条」变成运行时可判断的显式决策，而不是两条并列的静态边。''',
                        "explanation": "歧义的根源不是边太多，而是「没有判断依据」。补上判断依据，几条出边都可以。",
                    },
                    {
                        "code": "lg-ex-08-01-2",
                        "kp": 0,
                        "title": "多个节点连 END 合法吗",
                        "description": "`retrieve` 和 `smalltalk` 都直接连到 `END`，这是错误设计吗？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''完全合法，而且很常见。`END` 是汇聚点，多条分支各自结束时都连向它，结构上表达的是「这三条路都到终点」。

要注意的是「出口之后的收尾逻辑」：如果每条分支结束时都需要做同一件事（记日志、发通知），
不应该在三条分支里各写一遍，而是让它们都连到一个统一的 `finalize` 节点，再由它连 `END`。
这样收尾逻辑只有一处，改起来不会漏。''',
                        "explanation": "多出口合法；但「共同收尾」应该收敛到一个节点，否则逻辑会重复三份。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-08-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "普通边 `A → B` 表示什么？",
                        "options": [
                            ("A", "A 和 B 可以并行"),
                            ("B", "A 执行完必定执行 B"),
                            ("C", "B 可选"),
                            ("D", "A 依赖 B 的数据"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "普通边是无条件顺序关系，没有判断依据，所以不能有多条并存。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-08-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "一张图可以有多个节点连到 `END`。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`END` 是汇聚点，多条分支各自结束都连向它，合法且常见。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-08-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`describe(\"summarize\")` 返回什么？",
                        "options": [
                            ("A", "终点（没有出边）"),
                            ("B", "指向 END"),
                            ("C", "指向 retrieve"),
                            ("D", "歧义"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`EDGES[\"summarize\"]` 是 `[END]`，命中「指向 END」分支。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-08-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`pick(AMBIGUOUS, \"retrieve\")` 返回什么？",
                        "options": [
                            ("A", "歧义"),
                            ("B", "__end__"),
                            ("C", "summarize"),
                            ("D", "空字符串"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`retrieve` 只有一条出边且是 `END`，能确定走向，返回 `__end__`。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-08-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说「入口唯一」是工程约束而不是技术限制？",
                        "options": [],
                        "answer": {"value": """技术上执行器完全可以支持多入口，只是需要调用方在每次运行时指定从哪个入口进。

但从工程角度看，多入口带来三个问题：① 调用方必须知道图的内部结构，图不再是一个可以整体调用的黑盒；② 入口参数会与业务参数混在一起，接口不稳定；③ 多个入口可能各自初始化状态，容易造成字段缺失。

所以约定「单入口 + 入口处路由」，把分叉留在图内部，对外只暴露一个入口。这不是做不到，而是这样做更可控。"""},
                        "explanation": "区分「技术上可行」与「工程上应该」，是设计能力的一部分。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-08-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给 `EDGES` 加一个 `finalize` 节点：`summarize` 不再直接连 `END`，而是经 `finalize` 再到 `END`。写出改动。",
                        "options": [],
                        "answer": {"value": "EDGES[\"summarize\"] = [\"finalize\"]\nEDGES[\"finalize\"] = [END]"},
                        "explanation": "把「共同收尾」抽成一个节点，所有分支都经它结束，收尾逻辑只有一处。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ---------------------------------------------------------------- 第 9 章
    {
        "code": "langgraph-agent-09",
        "order_index": 9,
        "title": "StateGraph",
        "description": "把 State、Node、Edge 拼成一个完整图。",
        "lessons": [
            {
                "code": "langgraph-agent-09-lesson-01",
                "title": "把三块组装起来",
                "objectives": """1. 能用 `StateGraph` 把状态、节点、边组装成可运行的图；
2. 能通过节点内的打印观察状态在节点之间的流转；
3. 能解释 `invoke` 的入参与最终返回值的差别；
4. 能独立排查「图跑起来了但结果不对」这类问题。""",
                "why_learn": """前面四章分别讲了数据、函数、走向。这一节把它们拼起来，你会第一次看到
「一份状态从入口流到出口」的完整过程——这是后面所有高级特性的地基。""",
                "concepts": """**`StateGraph`**：构建器，负责收集节点与边，最后编出可执行图。
**注册顺序无关**：`add_node` 的先后不影响执行顺序，执行顺序由边决定。
**执行顺序**：从 `START` 出发，沿边一个个执行，每次把返回值合并进状态。
**入参 vs 返回值**：`invoke` 的入参是初始状态，返回值是跑完后的完整状态。
**观察方式**：在节点里打印「我看到什么」，比在最后看结果更容易定位问题。""",
                "plain": """装一台三层传送带：每层是一个工位，工件（状态）从入口放上去，
第一层做完写下结果，传送到第二层，第二层再补一笔，最后从出口出来。
你在每个工位放一张便签，记下「工件到我手上时是什么样」——出问题时翻便签，就知道是哪一层改坏了。""",
                "syntax": """**组装五步**

```python
builder = StateGraph(State)
builder.add_node("a", node_a)
builder.add_edge(START, "a")
builder.add_edge("a", END)
graph = builder.compile()
graph.invoke({"question": "..."})
```

- `StateGraph(State)` 里的 `State` 决定这份图的状态结构。
- `add_node(名字, 函数)`：名字用于连边与调试。
- `compile()` 之后才能 `invoke`。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    question: str
    sources: list[str]
    answer: str
    steps: int


def classify(state: State) -> dict:
    print(f"[classify] 看到 question={state['question']!r}，已有来源 {len(state['sources'])} 条")
    return {"steps": state["steps"] + 1}


def retrieve(state: State) -> dict:
    print(f"[retrieve] 看到 steps={state['steps']}，开始检索")
    return {"sources": [*state["sources"], "第 6 章 State"], "steps": state["steps"] + 1}


def answer(state: State) -> dict:
    joined = "、".join(state["sources"])
    print(f"[answer] 看到 sources={state['sources']}")
    return {"answer": f"依据 {joined} 回答：状态是节点之间共享的数据。", "steps": state["steps"] + 1}


builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("retrieve", retrieve)
builder.add_node("answer", answer)
builder.add_edge(START, "classify")
builder.add_edge("classify", "retrieve")
builder.add_edge("retrieve", "answer")
builder.add_edge("answer", END)

graph = builder.compile()
result = graph.invoke({"question": "State 是什么", "sources": [], "answer": "", "steps": 0})

print()
print("最终状态：")
for key, value in result.items():
    print(f"  {key:10s} = {value!r}")''',
                "code_lines": """1. `State` 声明四个字段，后面所有节点共用这一份结构。
2. `classify` 打印自己收到的 `question` 和来源条数，用来确认状态确实传进来了。
3. `retrieve` 读到 `steps=1`，说明它拿到的是 `classify` 更新后的状态。
4. `retrieve` 用解包造新列表，把「第 6 章 State」追加上去，不修改入参。
5. `answer` 打印 `sources`，可以看到上游追加的结果——这就是「读全量」。
6. 三个节点都在 `steps` 上 `+1`，最终为 3，证明每次合并都基于最新状态。
7. `invoke` 传入初始状态，返回合并后的完整状态；打印时按字段逐行展示，便于核对。""",
                "output": """# 程序输出
[classify] 看到 question='State 是什么'，已有来源 0 条
[retrieve] 看到 steps=1，开始检索
[answer] 看到 sources=['第 6 章 State']

最终状态：
  question   = 'State 是什么'
  sources    = ['第 6 章 State']
  answer     = '依据 第 6 章 State 回答：状态是节点之间共享的数据。'
  steps      = 3""",
                "mistakes": """- 以为 `add_node` 的注册顺序就是执行顺序，实际由边决定。
- 节点名字和函数名不一致，调试时在日志里找不到对应关系。
- 忘记 `compile()`，直接 `invoke`。
- 把初始状态写死成 `{}`，节点读字段时 `KeyError`。
- 在节点里 `print` 整份状态，日志被大量无关字段淹没。""",
                "error_analysis": """某个节点的打印根本没出现
—— 它不在从入口可达的路径上，检查边是否漏连。

`KeyError: 'answer'`
—— 初始状态里没提供该字段，而节点直接下标读取。补初始值或用 `.get()`。

结果里的 `steps` 比预期小
—— 某个节点返回的是旧快照，覆盖了中间更新。检查是否返回了整份 state。""",
                "beginner_practice": """1. 把 `add_node` 的三行顺序倒过来，确认输出顺序不变。
2. 删掉 `builder.add_edge("retrieve", "answer")`，观察哪些节点没执行。""",
                "advanced_practice": """把三个节点合并成两个（classify 与 retrieve 合成一步），
说明合并后哪些调试信息会丢失，以及你会在哪里加回观测点。""",
                "quiz_note": "本节 6 道题：2 道基础理解（注册顺序与执行顺序、compile 的必要性）+ 2 道代码阅读（读状态流转、读最终 steps）+ 2 道应用练习（调整结构、补观测）。",
                "summary": """`StateGraph` 把 State、Node、Edge 收进一个构建器，`compile` 后成为可执行图。
执行顺序由边决定，与注册顺序无关。
在节点里打印「我看到了什么」，是定位状态问题最有效的手段。""",
                "next_lesson": "下一章细看构建与编译这两步：`add_node`/`add_edge` 的规则，以及编译期的校验。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-09-01",
                        "name": "StateGraph 组装与执行顺序",
                        "goal": "能把状态、节点、边组装成可运行图，并观察状态流转。",
                        "minutes": 35,
                        "criteria": "能说明执行顺序由边决定，并通过节点内打印复现状态的逐步变化。",
                        "requires": ["langgraph-agent-08-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-09-01-1",
                        "kp": 0,
                        "title": "加一个引用节点",
                        "description": "在 `answer` 之前插入 `cite` 节点，把 `sources` 里第一项转成「引用：xxx」写进 `answer`。写出新增代码与边的调整。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def cite(state: State) -> dict:
    first = state["sources"][0] if state["sources"] else "无来源"
    return {"answer": f"引用：{first}", "steps": state["steps"] + 1}


builder.add_node("cite", cite)
builder.add_edge("retrieve", "cite")
builder.add_edge("cite", "answer")''',
                        "explanation": "插入节点要改两条边：原来的 `retrieve → answer` 拆成 `retrieve → cite → answer`。",
                    },
                    {
                        "code": "lg-ex-09-01-2",
                        "kp": 0,
                        "title": "结果不对怎么查",
                        "description": "图能跑，但最终 `answer` 里没有检索到的内容。列出你的排查顺序。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 看节点打印：`retrieve` 有没有执行、它看到和返回了什么。若没打印，说明边没连上或不可达。
② 看 `retrieve` 的返回值：是不是构造了新列表（`[*old, new]`）而不是返回旧值。
③ 看 `answer` 的入参：打印 `state["sources"]`，确认它拿到的是追加后的列表。
④ 看是否被覆盖：下游节点是否返回了整份旧快照，把 `sources` 又写回去了。
⑤ 最后才是怀疑状态定义：字段名是否拼错、类型是否不符。

原则：按「数据从哪来 → 经过谁 → 被谁改」的顺序查，不要一上来就怀疑框架。''',
                        "explanation": "调试顺序体现了对执行模型的理解：先确认执行了没，再确认数据对不对，最后才怀疑定义。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-09-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "图的执行顺序由什么决定？",
                        "options": [
                            ("A", "`add_node` 的调用顺序"),
                            ("B", "边的连接关系"),
                            ("C", "函数名的字母序"),
                            ("D", "State 里字段的顺序"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "节点只是注册进构建器，真正的先后关系由边声明，所以注册顺序可以随意。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-09-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`invoke` 的入参和返回值是同一份状态。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "入参是初始状态，返回值是跑完后合并出的新状态，通常字段值和入参不同。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-09-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`retrieve` 打印的 `steps` 是多少？为什么？",
                        "options": [
                            ("A", "0，因为初始值是 0"),
                            ("B", "1，因为 classify 已经加过 1"),
                            ("C", "2，因为两个节点各加一次"),
                            ("D", "不确定"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`classify` 返回 `steps+1` 并被合并，`retrieve` 拿到的是合并后的 1，这证明状态确实在节点间传递。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-09-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "最终 `answer` 里的内容来自哪里？",
                        "options": [
                            ("A", "初始状态传入的值"),
                            ("B", "retrieve 追加的 sources 拼接而成"),
                            ("C", "classify 直接写的"),
                            ("D", "框架自动生成"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`answer` 节点用 `state[\"sources\"]` 拼接文本，而 `sources` 是 `retrieve` 追加进去的。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-09-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么建议在节点里打印「我看到了什么」，而不是只在最后打印结果？",
                        "options": [],
                        "answer": {"value": """只看最终结果，只能知道「不对」，无法知道「在哪一步不对」。状态是逐节点合并出来的，最终值出错可能是任意一个节点写错、漏写或被覆盖。

在节点入口打印关键字段，等于给每一步留了快照：能立刻判断是「数据没传过来」还是「传过来了但被改坏」。这对多节点、带分支的图尤其重要——没有中间快照，只能靠猜。

代价是日志变多，所以正式项目应该改成结构化日志并带节点名，而不是 `print`。"""},
                        "explanation": "可观测性不是上线后才考虑的事，写第一个节点时就该留观测点。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-09-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给 `retrieve` 加一个保护：若 `state[\"sources\"]` 已有内容，就不重复追加同一项。写出改动。",
                        "options": [],
                        "answer": {"value": "def retrieve(state: State) -> dict:\n    item = \"第 6 章 State\"\n    if item in state[\"sources\"]:\n        print(f\"[retrieve] 已存在 {item}，跳过\")\n        return {\"steps\": state[\"steps\"] + 1}\n    return {\"sources\": [*state[\"sources\"], item], \"steps\": state[\"steps\"] + 1}"},
                        "explanation": "重试或循环时最容易产生重复数据，节点自己保证幂等比在下游去重更可靠。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
]
