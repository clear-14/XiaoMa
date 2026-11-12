"""LangGraph Agent 开发：第 10—12 章。

第 10 章讲构建与编译这两步的规则，第 11 章把节点函数写到不出错，
第 12 章讲状态更新里最容易踩的两类坑：全量覆盖与并行冲突。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 10 章
    {
        "code": "langgraph-agent-10",
        "order_index": 10,
        "title": "图创建和编译",
        "description": "注册节点、连接边、编译成可执行对象。",
        "lessons": [
            {
                "code": "langgraph-agent-10-lesson-01",
                "title": "add_node 与 add_edge",
                "objectives": """1. 能正确注册节点与连接边，并知道重名会立刻报错；
2. 能识别「注册了但没连边」的悬空节点，并说明它为什么不报错；
3. 能解释节点名与函数名的关系；
4. 能在结构出错时按「入口 → 可达性 → 出口」顺序排查。""",
                "why_learn": """构图阶段的两个错误最容易被忽略：重名节点直接抛异常（好查），
悬空节点静默不执行（难查）。分不清这两类，调试会非常耗时。""",
                "concepts": """**`add_node(名字, 函数)`**：名字是图里的标识，函数是真正执行的代码。
**重名**：同一个名字注册两次会抛 `ValueError`，不会静默覆盖。
**悬空节点**：注册了但没有任何边连到它，编译能通过，运行时永远不执行。
**名字与函数名分离**：可以让多个名字指向同一个函数（例如不同配置的同一段逻辑）。
**注册顺序无关**：执行顺序由边决定。""",
                "plain": """注册节点像给办公室挂门牌：重名会当场被拦下（两个 301 室，邮差会送错）；
但挂了牌却没写进楼层指引的房间，就永远不会有人进去——门牌还在，只是没人知道它存在。
前者会立刻报错，后者安安静静地错着，这才是麻烦的地方。""",
                "syntax": """**注册与连边**

```python
builder.add_node("step", step_fn)     # 名字 + 函数
builder.add_node("orphan", other_fn)  # 注册了但后面不连边
builder.add_edge(START, "step")
builder.add_edge("step", END)
```

- 重名会抛 `ValueError: Node 'xxx' already present.`
- 悬空节点不报错，但永远不执行。
- 一个函数可以注册成多个名字，用途不同、逻辑相同。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    n: int
    note: str


def step(state: State) -> dict:
    return {"n": state["n"] + 1}


def other(state: State) -> dict:
    return {"note": "ok"}


print("=== 重复注册同名节点 ===")
b = StateGraph(State)
b.add_node("step", step)
try:
    b.add_node("step", other)
    print("  未报错")
except ValueError as exc:
    print("  ValueError:", exc)
b.add_edge(START, "step")
b.add_edge("step", END)
print("  step 的实际行为：", b.compile().invoke({"n": 0, "note": ""}))

print()
print("=== 注册但没连边的节点 ===")
b2 = StateGraph(State)
b2.add_node("step", step)
b2.add_node("orphan", other)
b2.add_edge(START, "step")
b2.add_edge("step", END)
print("  编译通过，运行结果：", b2.compile().invoke({"n": 0, "note": ""}))
print("  orphan 执行了吗：没有，note 仍是空字符串")

print()
print("=== 同一个函数注册成两个名字 ===")
b3 = StateGraph(State)
b3.add_node("first", step)
b3.add_node("second", step)
b3.add_edge(START, "first")
b3.add_edge("first", "second")
b3.add_edge("second", END)
print("  结果：", b3.compile().invoke({"n": 0, "note": ""}))''',
                "code_lines": """1. 第一次 `add_node("step", step)` 成功注册。
2. 第二次同名注册立刻抛 `ValueError`，说明框架不做静默覆盖。
3. 报错之后 `step` 仍是第一次注册的那个函数，`n` 从 0 变 1。
4. `orphan` 注册成功，但没有任何边指向它。
5. 编译不报错，运行也正常结束，但 `note` 始终为空——节点从未执行。
6. 第三次实验把同一个 `step` 注册成两个名字，两个名字先后被执行。
7. 结果 `n=2`，证明「名字」只是标识，行为由函数决定。""",
                "output": """# 程序输出
=== 重复注册同名节点 ===
  ValueError: Node `step` already present.
  step 的实际行为： {'n': 1, 'note': ''}

=== 注册但没连边的节点 ===
  编译通过，运行结果： {'n': 1, 'note': ''}
  orphan 执行了吗：没有，note 仍是空字符串

=== 同一个函数注册成两个名字 ===
  结果： {'n': 2, 'note': ''}""",
                "mistakes": """- 复制粘贴节点注册时忘了改名，编译期就抛 `ValueError`。
- 注册了一堆节点只连了一部分，剩下的成了悬空节点，运行结果「少了几步」。
- 以为 `add_node` 的顺序决定执行顺序，把节点挪来挪去调顺序。
- 节点名用中文、空格或特殊字符，日志里难检索。
- 同一个逻辑复制成两份函数，其实注册两次同一个函数就够。""",
                "error_analysis": """`ValueError: Node 'xxx' already present.`
—— 同名注册两次。给其中一个改名，或确认是否真的需要两个节点。

某些步骤「没生效」但没有任何报错
—— 悬空节点。检查该节点是否有入边，用图结构导出功能核对。

`ValueError: Node 'xxx' is not a valid node name`
—— 节点名里含非法字符，或与保留名（`__start__`、`__end__`）冲突。""",
                "beginner_practice": """1. 把 `orphan` 连上 `b2.add_edge("step", "orphan")`，观察 `note` 是否被写入。
2. 给 `b3` 再加一个名字指向 `step`，预测最终的 `n`。""",
                "advanced_practice": """设计一个「同一函数、两套参数」的场景（例如「检索」在快答模式与精读模式下配置不同），
说明用两个节点名还是一个节点加状态字段更合适，并给出理由。""",
                "quiz_note": "本节 6 道题：2 道基础理解（重名行为、悬空节点）+ 2 道代码阅读（读运行结果、读 n 的累加）+ 2 道应用练习（连上悬空节点、排查少执行）。",
                "summary": """重名节点会在注册时立刻报错，好查。
悬空节点不报错、永不执行，必须靠结构检查发现。
名字只是标识，多个名字可以指向同一个函数。""",
                "next_lesson": "下一节看 `compile` 做了什么，以及编译产物能干什么。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-10-01",
                        "name": "节点注册与边连接的规则",
                        "goal": "能正确注册节点、连接边，并识别重名与悬空节点。",
                        "minutes": 35,
                        "criteria": "能解释重名为什么报错、悬空为什么静默，并给出各自的排查方法。",
                        "requires": ["langgraph-agent-09-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-10-01-1",
                        "kp": 0,
                        "title": "找出悬空节点",
                        "description": "给一份注册列表与边列表，写代码找出「注册了但没有入边」的节点。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''nodes = {"classify", "retrieve", "summarize", "cite"}
edges = {("__start__", "classify"), ("classify", "retrieve"), ("retrieve", "summarize")}

targets = {dst for _, dst in edges}
orphan = sorted(nodes - targets)
print("悬空节点：", orphan)   # ['cite']''',
                        "explanation": "只要不在任何一条边的终点集合里，就是没人调用它。入口节点也一样要检查入边（`__start__` 算）。",
                    },
                    {
                        "code": "lg-ex-10-01-2",
                        "kp": 0,
                        "title": "两个名字还是一个节点",
                        "description": "「快答模式检索」与「精读模式检索」逻辑相同、只是参数不同。用两个节点名还是加一个状态字段？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''优先用「一个节点 + 状态字段」。

理由：① 图结构里只出现一个「检索」，读图时不会误以为有两条不同的业务路径；
② 参数差异放在状态里，可以被日志、持久化、人工修改统一覆盖；
③ 改检索逻辑只改一处，不会出现两处逻辑漂移。

什么时候用两个名字：两种模式的执行路径本身不同（例如精读要多轮检索、快答只查一次），
此时它们已经是两个节点，共用底层函数即可（`add_node("search_fast", search)` 与 `add_node("search_deep", search)`）。''',
                        "explanation": "判据是「业务路径是否相同」，而不是「参数是否相同」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-10-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "同一个名字调用两次 `add_node` 会怎样？",
                        "options": [
                            ("A", "后者覆盖前者"),
                            ("B", "抛 `ValueError`"),
                            ("C", "静默忽略第二次"),
                            ("D", "两个节点都保留"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "框架不允许重名，直接报错而不是静默覆盖，这是好事——错误早暴露。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-10-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "注册了但没有连任何边的节点，编译时会报错。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "编译不报错，运行时该节点永远不执行——这是最难发现的一类结构问题。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-10-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第二个实验里 `note` 为什么还是空字符串？",
                        "options": [
                            ("A", "`other` 函数写错了"),
                            ("B", "`orphan` 没有入边，从未执行"),
                            ("C", "`note` 被覆盖了"),
                            ("D", "State 没声明 note"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`orphan` 是悬空节点，虽然注册成功，但执行路径里没有它，所以它的返回值从未参与合并。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-10-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第三个实验最终 `n` 是多少？",
                        "options": [
                            ("A", "0"),
                            ("B", "1"),
                            ("C", "2"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "两个名字都指向 `step`，先后执行两次，每次 `+1`，得到 2。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-10-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「悬空节点」比「重名节点」更难排查？",
                        "options": [],
                        "answer": {"value": """重名节点在构建阶段就抛异常，程序根本跑不到运行期，错误位置明确。

悬空节点则全程静默：注册成功、编译成功、运行成功，只是结果「少了一步」。表现为某个字段一直是初始值、某段逻辑从未触发。排查时要先怀疑业务逻辑，最后才想到结构——而结构问题恰恰在代码里看不出来，必须把注册列表和边列表放一起比对。

工程对策：写一个结构自检（注册集合减去边终点集合），在测试里断言为空。"""},
                        "explanation": "「静默正确」比「立刻报错」危险得多，这也是要主动加结构断言的原因。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-10-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "把 `orphan` 接入主流程（放在 `step` 之后、`END` 之前），写出改动后的三条边。",
                        "options": [],
                        "answer": {"value": "b2.add_edge(START, \"step\")\nb2.add_edge(\"step\", \"orphan\")\nb2.add_edge(\"orphan\", END)"},
                        "explanation": "接入节点必须替换原来的出边，而不是新增一条——否则 `step` 会有两条出边，形成歧义。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-10-lesson-02",
                "title": "compile 与运行",
                "objectives": """1. 能说清构建器与编译产物的区别；
2. 能用 `get_graph()` 读出节点与边的结构并核对；
3. 能解释「同一个图连续调用互不影响」意味着什么；
4. 能判断什么时候该重新编译、什么时候可以复用。""",
                "why_learn": """编译不只是「把 builder 变成 graph」。
它是一次结构校验，也是运行期配置的入口——理解这一点，后面接入持久化和流式时才不会乱。""",
                "concepts": """**构建器**：`StateGraph`，只有 `compile`，没有 `invoke`。
**编译产物**：`CompiledStateGraph`，可以 `invoke`、`stream`，也能导出结构。
**结构导出**：`get_graph()` 返回节点与边，可用于自检与画图。
**无跨调用状态**：默认不带持久化时，每次 `invoke` 都是独立的一次执行。
**复用**：编译一次、多次调用是常态；结构变了才需要重新编译。""",
                "plain": """构建器像图纸，编译产物像按图纸造好的机器。
图纸上不能「按下启动」——你只能改图纸；造好的机器才能开机。
同一台机器连续开两次，两次之间不会残留上一批次的零件（除非你外挂了储物柜，那是后面的持久化）。""",
                "syntax": """**编译与调用**

```python
builder = StateGraph(State)
...
graph = builder.compile()        # 得到 CompiledStateGraph
graph.invoke({"n": 0})           # 每次调用独立
structure = graph.get_graph()    # 导出节点与边
```

- 构建器没有 `invoke`，调用它会 `AttributeError`。
- `get_graph().nodes` 会额外包含 `__start__` 与 `__end__`。
- `compile()` 可以重复调用，每次返回新的编译产物。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    n: int


def inc(state: State) -> dict:
    return {"n": state["n"] + 1}


builder = StateGraph(State)
builder.add_node("inc", inc)
builder.add_edge(START, "inc")
builder.add_edge("inc", END)

print("构建器类型：", type(builder).__name__)
print("构建器有 invoke 吗：", hasattr(builder, "invoke"))
print("构建器有 compile 吗：", hasattr(builder, "compile"))

graph = builder.compile()
print("编译产物类型：", type(graph).__name__)
print("有 invoke 吗：", hasattr(graph, "invoke"))

structure = graph.get_graph()
print()
print("图里的节点：", sorted(structure.nodes))
print("边：")
for edge in structure.edges:
    print(f"  {edge.source:10s} -> {edge.target}")

print()
print("第一次：", graph.invoke({"n": 0}))
print("第二次：", graph.invoke({"n": 0}))
print("两次一致，说明没有跨调用残留")
print("传入已有状态：", graph.invoke({"n": 99}))''',
                "code_lines": """1. `builder` 的类型是 `StateGraph`，它只有构建能力。
2. `hasattr(builder, "invoke")` 为 False——图纸不能开机。
3. `compile()` 返回 `CompiledStateGraph`，这才是可执行对象。
4. `get_graph().nodes` 除了 `inc` 还有 `__start__` 与 `__end__`，它们是内置节点。
5. 遍历 `edges` 能逐条核对走向，这是「结构自检」的原材料。
6. 连续两次 `invoke({"n": 0})` 都得到 1，证明没有跨调用状态泄漏。
7. 传入 `{"n": 99}` 得到 100，说明入参就是初始状态，节点在它基础上计算。""",
                "output": """# 程序输出
构建器类型： StateGraph
构建器有 invoke 吗： False
构建器有 compile 吗： True
编译产物类型： CompiledStateGraph
有 invoke 吗： True

图里的节点： ['__end__', '__start__', 'inc']
边：
  __start__  -> inc
  inc        -> __end__

第一次： {'n': 1}
第二次： {'n': 1}
两次一致，说明没有跨调用残留
传入已有状态： {'n': 100}""",
                "mistakes": """- 拿着 `StateGraph` 构建器直接 `invoke`，忘了 `compile()`。
- 每次调用都重新 `compile()` 一次，构建开销白付，还容易把两个产物搞混。
- 用 `get_graph().nodes` 里没有自己的节点名，就断定节点没注册——其实注册名和函数名可以不同。
- 认为不传持久化也会有跨调用记忆，结果第二次调用又从初始状态开始。
- 把 `invoke` 的返回值当成「本次更新」，其实它是**完整状态**，两个键都在。""",
                "error_analysis": """`AttributeError: 'StateGraph' object has no attribute 'invoke'`
—— 忘了 `compile()`。

`TypeError: compile() got an unexpected keyword argument`
—— 参数名写错，或该参数属于更高版本。先确认版本文档。

两次调用结果不一致（在没引入持久化时）
—— 节点内部有可变全局状态。节点应该是纯函数。""",
                "beginner_practice": """1. 把 `compile()` 调用两次，比较两个产物的 `get_graph()` 是否一致。
2. 打印 `len(structure.edges)`，核对是否等于自己连的边数加内置边。""",
                "advanced_practice": """把「构建 + 编译」封装成一个 `build_graph()` 工厂函数，在模块级别调用一次并复用。
说明这样改之后，单元测试要怎么拿到「干净的图」，以及为什么要避免在函数内部编译。""",
                "quiz_note": "本节 6 道题：2 道基础理解（构建器与产物、无跨调用状态）+ 2 道代码阅读（读结构导出、读两次调用）+ 2 道应用练习（封装工厂、判断何时重编）。",
                "summary": """构建器只能编译，编译产物才能运行。
`get_graph()` 把结构摊开，是自检和画图的入口。
默认每次调用独立，跨调用的记忆要靠持久化显式开启。""",
                "next_lesson": "下一章细看节点函数本身：签名、返回值、异常各有什么讲究。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-10-02",
                        "name": "编译产物、结构导出与调用语义",
                        "goal": "能区分构建器与编译产物，并用结构导出核对图。",
                        "minutes": 35,
                        "criteria": "能说出 `compile` 的三个作用，并解释为什么连续调用互不影响。",
                        "requires": ["langgraph-agent-10-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-10-02-1",
                        "kp": 0,
                        "title": "结构自检",
                        "description": "写 `check_structure(graph, expected_edges)`：把实际边与期望边对比，返回缺失与多余的边。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def check_structure(graph, expected_edges: set[tuple[str, str]]) -> dict:
    actual = {(e.source, e.target) for e in graph.get_graph().edges}
    return {
        "missing": sorted(expected_edges - actual),
        "extra": sorted(actual - expected_edges),
    }


expected = {("__start__", "inc"), ("inc", "__end__")}
print(check_structure(graph, expected))''',
                        "explanation": "把结构声明成期望集合，任何一次误删边或误加边都能在测试里立刻暴露。",
                    },
                    {
                        "code": "lg-ex-10-02-2",
                        "kp": 0,
                        "title": "该在哪编译",
                        "description": "应该把 `compile()` 放在模块加载时，还是放在每个请求的处理函数里？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''默认放模块加载时（或应用启动时），只编译一次。

原因：① 编译包含结构校验，每请求做一次是纯浪费；② 编译产物是不可变的执行计划，可以安全复用；③ 启动时编译能把「图结构写错」变成「服务起不来」，而不是「某个请求偶发失败」。

什么情况需要重新编译：结构本身随配置变化（例如按租户裁剪可用节点）。这种场景应该按「配置」缓存编译产物，而不是每次请求都编译。''',
                        "explanation": "「启动即失败」是让结构错误最早暴露的方式，也是这里推荐在启动时编译的核心理由。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-10-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`StateGraph` 与 `CompiledStateGraph` 的关系是？",
                        "options": [
                            ("A", "同一个东西的两个名字"),
                            ("B", "前者是构建器，后者是可运行的执行计划"),
                            ("C", "后者是前者的子类"),
                            ("D", "两者可以互换使用"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "构建器负责收集结构，编译产物负责执行。构建器没有 `invoke`，不能互换。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-10-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "不引入持久化时，同一个 graph 连续 `invoke` 两次会共享状态。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "默认每次调用都是独立的执行，状态不跨调用保留；共享需要显式配置持久化。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-10-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`get_graph().nodes` 里为什么有 `__start__` 与 `__end__`？",
                        "options": [
                            ("A", "自己注册的"),
                            ("B", "它们是内置的入口与出口节点"),
                            ("C", "是 bug"),
                            ("D", "是节点函数的返回值"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`START` 与 `END` 在结构上也是节点，所以导出时会出现在节点列表里。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-10-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`graph.invoke({\"n\": 99})` 返回 100 说明什么？",
                        "options": [
                            ("A", "状态被缓存了"),
                            ("B", "入参就是初始状态，节点在它基础上计算"),
                            ("C", "节点被执行了 99 次"),
                            ("D", "有隐藏的累加逻辑"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`invoke` 的入参直接作为初始状态，`inc` 读 99 加 1 得 100。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-10-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说 `compile()` 同时是一次「校验」？",
                        "options": [],
                        "answer": {"value": """编译期要能确定执行计划，就必须先把结构性问题挡掉：入口是否存在、节点是否都可达、边的两端是否都注册过、状态 schema 是否可合并。

这些检查如果留到运行期，错误会出现在「某个请求跑到一半」，日志里只能看到一堆业务调用。放在编译期，就变成「服务启动失败」，错误信息直接指向结构。

所以把编译放在启动阶段，等于免费获得一次结构体检。"""},
                        "explanation": "编译期校验是「错误左移」的典型手段，成本几乎为零。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-10-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "把图的构建与编译封装成 `build_graph()`，并在模块级调用一次得到 `GRAPH`。",
                        "options": [],
                        "answer": {"value": "def build_graph():\n    builder = StateGraph(State)\n    builder.add_node(\"inc\", inc)\n    builder.add_edge(START, \"inc\")\n    builder.add_edge(\"inc\", END)\n    return builder.compile()\n\n\nGRAPH = build_graph()"},
                        "explanation": "工厂函数便于测试时重建，模块级常量保证运行时只编译一次，两者兼顾。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 11 章
    {
        "code": "langgraph-agent-11",
        "order_index": 11,
        "title": "节点函数",
        "objectives": """1. 能写出符合约定的节点函数：一个参数、返回 dict；
2. 能预测五种常见返回值形态各自的运行结果；
3. 能解释「返回未声明的键」为什么是静默失败；
4. 能决定节点内的异常该抛出还是该捕获。""",
        "lessons": [
            {
                "code": "langgraph-agent-11-lesson-01",
                "title": "函数签名与返回值",
                "objectives": """1. 能写出符合约定的节点函数：一个参数、返回 dict；
2. 能预测五种常见返回值形态各自的运行结果；
3. 能解释「返回未声明的键」为什么是静默失败；
4. 能决定节点内的异常该抛出还是该捕获。""",
                "why_learn": """节点写错的方式就那么几种，但每种的表现差别很大：
有的立刻报错，有的静默丢弃，有的把异常直接透给调用方。认清这五种，调试能省一半时间。""",
                "concepts": """**约定签名**：`def node(state) -> dict`，一个参数、返回 dict。
**正常增量**：只含要更新的键，最安全。
**未声明的键**：不报错，但被直接丢弃——静默失败。
**返回 `None`**：不报错，状态保持不变，常用于「只做副作用」的节点。
**返回非 dict**：抛 `InvalidUpdateError: Expected dict, got ...`。
**抛异常**：原样透出，整个 `invoke` 失败。""",
                "plain": """节点交回来的东西要能「填进表格」：
交一张只写了改动项的便签，最清楚；交一张写了表格上没有的栏目，登记员看都不看就扔掉；
什么都不交也行，表格保持原样；交一整页小说，登记员直接退回来；
交的时候手抖撕了纸，整个流程当场中断。

五种情况，只有第一种是好的。""",
                "syntax": """**五种返回值**

```python
def ok(state): return {"n": state["n"] + 1}       # 正常
def extra(state): return {"not_in_state": 1}      # 静默丢弃
def none(state): pass                              # 状态不变
def wrong(state): return "完成"                    # InvalidUpdateError
def boom(state): raise ValueError("内部错误")      # 异常透出
```

- 想让节点「只做副作用、不改状态」，返回 `None` 或 `{}` 都可以。
- 校验返回值是否落在 State 的键里，应当在代码评审和测试里做，不要指望运行时。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    n: int
    note: str


def ok(state: State) -> dict:
    return {"n": state["n"] + 1}


def unknown_key(state: State) -> dict:
    return {"missing_field": 1}          # State 里没有这个键


def returns_none(state: State) -> None:
    pass                                 # 什么都没返回


def returns_str(state: State) -> str:
    return "完成"                        # 返回类型错了


def raises(state: State) -> dict:
    raise ValueError("节点内部出错")


def run(fn) -> object:
    builder = StateGraph(State)
    builder.add_node("node", fn)
    builder.add_edge(START, "node")
    builder.add_edge("node", END)
    try:
        return builder.compile().invoke({"n": 0, "note": ""})
    except Exception as exc:
        return f"{type(exc).__name__}: {str(exc).splitlines()[0]}"


CASES = [
    ("正常返回增量", ok),
    ("返回未声明的键", unknown_key),
    ("什么都不返回", returns_none),
    ("返回字符串", returns_str),
    ("节点抛异常", raises),
]

for label, fn in CASES:
    print(f"{label:12s} -> {run(fn)}")''',
                "code_lines": """1. `ok` 返回单键增量，`n` 从 0 变成 1，`note` 保持不变。
2. `unknown_key` 返回的键不在 State 里，结果里看不到它——既不报错也不生效。
3. `returns_none` 什么都不返回，状态原样返回，`invoke` 正常结束。
4. `returns_str` 返回字符串，触发 `InvalidUpdateError: Expected dict, got 完成`。
5. `raises` 抛出的异常原样透给调用方，不是包装成框架异常。
6. `run` 把三种结果（dict / 异常字符串）统一成可打印形式，方便一次看完五种行为。
7. 只有第一种是「正确」，第二种和第三种是「静默」，后两种是「显式失败」。""",
                "output": """# 程序输出
正常返回增量       -> {'n': 1, 'note': ''}
返回未声明的键      -> {'n': 0, 'note': ''}
什么都不返回       -> {'n': 0, 'note': ''}
返回字符串        -> InvalidUpdateError: Expected dict, got 完成
节点抛异常        -> ValueError: 节点内部出错""",
                "mistakes": """- 字段名打错（`step` 写成 `steps`），返回被静默丢弃，查半天以为没执行。
- 节点里 `return state.append(x)`，返回了 `None`，改动丢了。
- 返回列表或字符串，运行时报 `Expected dict`。
- 节点里 `try/except` 吞掉所有异常，返回空 dict，上游看到「成功但没结果」。
- 把「只做副作用」的节点写成返回整份状态，反而覆盖了别的字段。""",
                "error_analysis": """某个字段一直是初始值
—— 节点返回的键名与 State 里不一致，被静默丢弃。核对拼写，或加返回值校验测试。

`InvalidUpdateError: Expected dict, got ...`
—— 返回值不是 dict。检查 `return` 语句，尤其是链式调用写成了 `return a.update(b)`。

整个 `invoke` 直接抛业务异常
—— 节点没有捕获。如果这是「该失败就失败」的场景，保持透出；如果要降级，在节点内捕获并写错误字段。""",
                "beginner_practice": """1. 把 `unknown_key` 的键名改成 `note`，观察结果变化。
2. 让 `returns_none` 打印一句话再返回，确认「有副作用但不改状态」是合法的。""",
                "advanced_practice": """给节点加一层返回值校验装饰器：返回的键不在 State 里就抛异常。
说明这样改之后，哪些原本静默的 bug 会变成显式报错，代价是什么。""",
                "quiz_note": "本节 6 道题：2 道基础理解（约定签名、None 的语义）+ 2 道代码阅读（读五种结果、读静默丢弃）+ 2 道应用练习（改键名、写校验装饰器）。",
                "summary": """节点必须返回 dict（或 None），其余形态要么报错要么静默。
返回未声明的键不报错但被丢弃——最需要警惕的一类。
异常是否捕获取决于业务：该失败的让它透出，能降级的在节点内处理。""",
                "next_lesson": "下一章看状态更新里的两类硬伤：全量覆盖与并行冲突。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-11-01",
                        "name": "节点签名与五种返回值形态",
                        "goal": "能预测不同返回值的行为，并避免静默失败。",
                        "minutes": 35,
                        "criteria": "能说出返回未声明键与返回 None 的区别，并解释为什么前者危险。",
                        "requires": ["langgraph-agent-10-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-11-01-1",
                        "kp": 0,
                        "title": "返回值校验装饰器",
                        "description": "写 `check_keys(allowed)` 装饰器，节点返回的键不在 `allowed` 里就抛 `KeyError`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''import functools


def check_keys(allowed: set[str]):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(state):
            result = fn(state)
            if result is None:
                return None
            unknown = set(result) - allowed
            if unknown:
                raise KeyError(f"节点返回了未声明的键：{sorted(unknown)}")
            return result

        return wrapper

    return decorator


@check_keys(set(State.__required_keys__))
def safe_node(state: State) -> dict:
    return {"note": "ok"}''',
                        "explanation": "把「键必须合法」从约定升级成断言，静默失败就变成了显式失败。装饰器不改节点逻辑，只加一层守门。",
                    },
                    {
                        "code": "lg-ex-11-01-2",
                        "kp": 0,
                        "title": "异常该不该吞",
                        "description": "节点里调用外部接口失败时，应该捕获后返回错误字段，还是直接抛出？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''取决于这条失败「有没有可用的降级路径」。

该捕获的情形：接口是可选增强（例如「推荐相关课程」），失败时仍能给出主答案。做法是捕获后写入 `error` 字段并返回部分结果，让下游决定怎么呈现。

该抛出的情形：接口是必需数据（例如「查订单状态」却没有订单），继续跑只会产出错误答案。这时应抛出，让上层统一处理并给用户明确提示。

关键是：不要「捕获后返回空 dict」。那既没降级信息，也掩盖了失败，是最难查的形态。''',
                        "explanation": "捕获异常必须伴随「可观测的降级信号」，否则等于把失败藏起来。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-11-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "节点函数的标准签名是？",
                        "options": [
                            ("A", "`def node(state, config) -> dict`"),
                            ("B", "`def node(state) -> dict`"),
                            ("C", "`def node() -> dict`"),
                            ("D", "`def node(state) -> None`"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "标准形态是一个参数（状态）和一个 dict 返回值。需要额外上下文时用别的方式注入，不改签名。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-11-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "节点返回 `None` 会让整个执行失败。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "返回 `None` 合法，表示「不改状态」，常用于只做副作用的节点。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-11-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`unknown_key` 那行结果是 `{'n': 0, 'note': ''}`，说明？",
                        "options": [
                            ("A", "节点没执行"),
                            ("B", "返回值被丢弃，状态未变"),
                            ("C", "节点抛了异常被捕获"),
                            ("D", "State 自动扩容"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "节点确实执行了，但返回的键不在 State 里，合并时被忽略，所以状态原样。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-11-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`returns_str` 抛出的异常类型是？",
                        "options": [
                            ("A", "`TypeError`"),
                            ("B", "`ValueError`"),
                            ("C", "`InvalidUpdateError`"),
                            ("D", "`KeyError`"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "返回值类型不符会被合并逻辑拒绝，抛 `InvalidUpdateError`，并明确写出收到的类型。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-11-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「返回未声明的键」比「返回字符串」更危险？",
                        "options": [],
                        "answer": {"value": """返回字符串会立刻抛 `InvalidUpdateError`，错误位置、原因都写清楚了，改一下就好。

返回未声明的键则完全静默：节点执行了、没报错、流程继续，只是那个值凭空消失。表现是「某个字段一直是初始值」，排查时会先怀疑上游没写、再怀疑合并逻辑，最后才发现是键名拼写。

危险在于它把「代码错误」伪装成「业务没数据」，浪费的时间远多于一次显式报错。对策是在测试里断言关键字段确实被写入。"""},
                        "explanation": "判断危险程度的标尺不是「错误大小」，而是「暴露得够不够快」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-11-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个只做副作用、不改状态的 `log_node`：打印当前 `n`，不返回任何东西。",
                        "options": [],
                        "answer": {"value": "def log_node(state: State) -> None:\n    print(f\"[log] 当前 n={state['n']}\")"},
                        "explanation": "返回 `None` 是合法的「只观察」节点，适合在流程中插入观测点而不影响数据。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ---------------------------------------------------------------- 第 12 章
    {
        "code": "langgraph-agent-12",
        "order_index": 12,
        "title": "状态更新",
        "description": "返回增量还是整份状态，结果差别很大。",
        "lessons": [
            {
                "code": "langgraph-agent-12-lesson-01",
                "title": "部分更新与全量更新",
                "objectives": """1. 能区分「返回增量」与「返回整份状态」；
2. 能演示全量更新在跨轮次调用时把状态写回旧值；
3. 能解释为什么在单次调用里看不出差别；
4. 能给出「必须返回增量」的三条理由。""",
                "why_learn": """返回整份状态在第一次跑的时候完全正常，第二轮才出问题——
这类 bug 在本地很难复现，上线后却会让「进度」「计数器」这类字段莫名回退。""",
                "concepts": """**部分更新**：只返回要改的键，其余字段由执行器保留。
**全量更新**：返回包含所有字段的 dict，等于把旧值也一起写回。
**单轮无害**：同一次调用里，全量更新写入的值恰好等于当前值，看不出问题。
**跨轮有害**：节点把状态缓存到实例属性后，下一轮返回的是上一轮快照。
**根因**：合并规则是「按返回值覆盖」，返回了什么就覆盖什么。""",
                "plain": """交接单上改了「数量」那一栏，你却在交回时把整张单子按「自己印象里的样子」重抄了一遍。
第一次重抄时内容刚好一样，看不出来；第二次单子上已经有了别人写的新内容，
你再照着上次的重抄，那些新内容就被抹掉了——你并不是想改它们，只是抄错了版本。""",
                "syntax": """**两种写法**

```python
# 部分更新（推荐）
def node(state):
    return {"answer": "新答案"}

# 全量更新（危险）
def node(state):
    return {**state, "answer": "新答案"}
```

- 全量更新在「与当前状态完全一致」时结果相同，所以单轮测不出问题。
- 一旦节点内部缓存了状态（实例属性、闭包、全局变量），全量更新就会写回过期数据。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    steps: int
    answer: str


# 真实事故形态：节点把自己「第一次见到的状态」存到实例属性上
class Writer:
    def __init__(self) -> None:
        self.snapshot: dict | None = None

    def partial(self, state: State) -> dict:
        return {"answer": "部分更新写的"}

    def full(self, state: State) -> dict:
        if self.snapshot is None:
            self.snapshot = dict(state)          # 缓存第一次见到的整份状态
        return {**self.snapshot, "answer": "全量更新写的"}


def bump(state: State) -> dict:
    return {"steps": state["steps"] + 1}


def build(method: str, writer: Writer):
    builder = StateGraph(State)
    builder.add_node("bump", bump)
    builder.add_node("write", getattr(writer, method))
    builder.add_edge(START, "bump")
    builder.add_edge("bump", "write")
    builder.add_edge("write", END)
    return builder.compile()


for method in ("partial", "full"):
    writer = Writer()
    graph = build(method, writer)
    print(f"=== {method} ===")
    print("  第 1 次（steps=0）：", graph.invoke({"steps": 0, "answer": ""}))
    print("  第 2 次（steps=10）：", graph.invoke({"steps": 10, "answer": ""}))
    print()''',
                "code_lines": """1. `Writer` 把「第一次见到的状态」存到 `self.snapshot`，这是模拟缓存旧值的写法。
2. `partial` 只返回 `answer`，`steps` 完全不在返回值里，执行器保留原值。
3. `full` 用 `{**self.snapshot, ...}` 把旧快照整体写回，等于覆盖所有字段。
4. 第一轮两者结果相同（`steps` 都是 1），因为此时快照正好等于当前状态。
5. 第二轮 `partial` 得到 `steps=11`，正常基于新入参计算。
6. 第二轮 `full` 得到 `steps=1`，被第一轮的快照覆盖——入参 10 被抹掉了。
7. 差别只在第二轮暴露，这就是这类 bug 难复现的原因。""",
                "output": """# 程序输出
=== partial ===
  第 1 次（steps=0）： {'steps': 1, 'answer': '部分更新写的'}
  第 2 次（steps=10）： {'steps': 11, 'answer': '部分更新写的'}

=== full ===
  第 1 次（steps=0）： {'steps': 1, 'answer': '全量更新写的'}
  第 2 次（steps=10）： {'steps': 1, 'answer': '全量更新写的'}""",
                "mistakes": """- 以为 `return {**state, ...}` 和 `return {...}` 效果一样，单轮测试也确实一样。
- 把状态存到节点对象的属性里「方便下次用」，于是下一次用了过期数据。
- 用全局变量或类属性缓存状态，多请求并发时互相污染。
- 为了「保险」把整份状态返回，结果每个节点都在覆盖别人的更新。
- 只在单轮里测节点，从不测「同一个 graph 连续调用两次」。""",
                "error_analysis": """计数器第二轮从 11 变回 1
—— 某节点返回了旧快照。检查是否有 `self.xxx = state` 这类缓存。

并发请求间状态互相串
—— 节点用了模块级或类级可变变量。状态只能通过参数传递。

某个字段在图上明明没写过却变了
—— 有节点返回了整份状态，把自己的旧值带了回来。""",
                "beginner_practice": """1. 把 `full` 里的 `self.snapshot` 改成每次都用当前 `state`，观察第二轮结果。
2. 给 `partial` 也加一个缓存但不用它，确认「存了不用」不会出问题。""",
                "advanced_practice": """写一个静态检查脚本：扫描节点函数体，发现 `return state` 或 `{**state, ...}` 就报warning。
说明这条规则的例外情况（例如「确实需要整体替换状态」的场景）该怎么标注。""",
                "quiz_note": "本节 6 道题：2 道基础理解（增量与全量、为何单轮看不出）+ 2 道代码阅读（读两轮结果、定位缓存）+ 2 道应用练习（修节点、写检查）。",
                "summary": """返回增量是默认正确姿势，返回整份状态会覆盖别人的更新。
单轮测试永远发现不了这个问题，必须测连续两轮。
节点内不要缓存状态，状态只能通过参数进出。""",
                "next_lesson": "下一节看另一类硬伤：两个节点同时写同一个键。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-12-01",
                        "name": "部分更新与全量更新的差别",
                        "goal": "能识别并修复「返回旧快照」导致的状态回退。",
                        "minutes": 35,
                        "criteria": "能构造一个第二轮才暴露的回退案例，并说明根因。",
                        "requires": ["langgraph-agent-11-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-12-01-1",
                        "kp": 0,
                        "title": "修掉回退",
                        "description": "下面的节点导致第二轮 `steps` 回退，改掉它。\n\n```python\nclass Node:\n    def __init__(self):\n        self.cache = None\n    def run(self, state):\n        if self.cache is None:\n            self.cache = dict(state)\n        return {**self.cache, \"answer\": \"ok\"}\n```",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class Node:
    def run(self, state: dict) -> dict:
        return {"answer": "ok"}''',
                        "explanation": "删掉缓存、只返回增量即可。这个节点本来就不需要读历史状态，缓存纯属多余。",
                    },
                    {
                        "code": "lg-ex-12-01-2",
                        "kp": 0,
                        "title": "什么情况真的需要全量",
                        "description": "有没有必须返回整份状态的场景？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''极少，但不是没有：

① 需要整体重置状态（例如「开始新会话」节点要把所有字段清空）；
② 状态来自外部全量快照（例如从数据库读回一整条记录，字段集合与 State 一致）；
③ 用 `Overwrite` 语义显式替换某个带 reducer 的字段（这是更高阶的用法，第 15 章之后才需要）。

即使在这三种情况下，也应该写「显式构造完整值」而不是「把入参原样返回」——前者意图明确，
后者很容易在字段增加后悄悄带上不该带的值。''',
                        "explanation": "「全量」本身不是错，「无意识地全量」才是错。区别在于是否显式、是否有意。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-12-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`return {**state, \"answer\": \"x\"}` 相比 `return {\"answer\": \"x\"}` 多了什么风险？",
                        "options": [
                            ("A", "更慢"),
                            ("B", "把状态里的旧值一并写回，可能覆盖别人的更新"),
                            ("C", "类型不匹配"),
                            ("D", "没有风险"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "展开运算符把当前所有字段都放进返回值，合并时整份覆盖——包括不该动的字段。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-12-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "全量更新的问题在第一次调用时就能发现。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "第一次调用时旧快照等于当前状态，结果完全相同。差别要到第二轮才暴露。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-12-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第二轮 `full` 的结果里 `steps` 是多少？",
                        "options": [
                            ("A", "0"),
                            ("B", "1"),
                            ("C", "11"),
                            ("D", "10"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "第一轮缓存的快照里 `steps=1`，第二轮把它整体写回，入参 10 被覆盖。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-12-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "为什么 `partial` 的第二轮结果正确？",
                        "options": [
                            ("A", "它缓存了状态"),
                            ("B", "它只返回 `answer`，`steps` 根本不在返回值里"),
                            ("C", "它清空了状态"),
                            ("D", "执行器特殊处理了它"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "不返回的字段不会被覆盖，所以 `bump` 写入的 `steps=11` 得以保留。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-12-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如何用测试稳定地抓住「全量更新回退」这类 bug？",
                        "options": [],
                        "answer": {"value": """关键是**测连续两次调用，且两次入参不同**。

做法：同一个编译产物先 `invoke({"steps": 0})`，再 `invoke({"steps": 10})`，断言第二次结果里 `steps == 11`。
任何「第二轮回到第一轮的值」的写法都会被抓到。

再补一条更狠的：断言「除了目标字段，其它字段在两次调用之间互不影响」。这样连「部分覆盖」也能测出来。"""},
                        "explanation": "这类 bug 的特征是「跨调用」，测试用例必须跨调用才能复现。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-12-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写 `reset_node`：把 `steps` 归零、`answer` 清空，要求显式构造完整值而不是返回入参。",
                        "options": [],
                        "answer": {"value": "def reset_node(state: State) -> dict:\n    return {\"steps\": 0, \"answer\": \"\"}"},
                        "explanation": "重置场景虽然语义上是「全量」，但仍应显式写出每个字段，而不是 `{**state}` 再改——前者在字段增加时会立刻暴露未处理项。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-12-lesson-02",
                "title": "并发写入冲突",
                "objectives": """1. 能构造两个节点并行写同一个键的场景；
2. 能读懂 `InvalidUpdateError` 里「只能收到一个值」的含义；
3. 能解释框架为什么选择报错而不是随便取一个值；
4. 能说出这个限制与第 15 章 Reducer 的关系。""",
                "why_learn": """并行是 Agent 提速的主要手段，并行写冲突是它必然带来的问题。
不理解这条限制，图一旦加并行分支就会莫名其妙崩掉。""",
                "concepts": """**并行分支**：一个节点有多个后继，或 `START` 直接连多个节点。
**同键冲突**：两个并行节点在同一步写同一个键，合并时无法决定取谁。
**报错而不是乱选**：框架抛 `InvalidUpdateError`，避免结果依赖执行顺序。
**解法方向**：声明合并规则（Reducer）——第 15 章的内容。
**规避方式**：让并行节点各写各的键，最后用一个汇聚节点做合并。""",
                "plain": """两个人同时往同一格储物柜里塞东西，管理员必须拦下来问「到底放谁的」。
如果他不问、随手放一个，下次同样的操作可能放另一个——结果就不确定了。
所以正确做法不是「随便选一个」，而是「先约定合并规则」。""",
                "syntax": """**并行结构**

```python
builder.add_edge(START, "a")
builder.add_edge(START, "b")     # a 与 b 并行
builder.add_edge("a", "merge")
builder.add_edge("b", "merge")
```

- 并行节点写**不同**的键：没问题。
- 并行节点写**同一个**键：`InvalidUpdateError: At key 'xxx': Can receive only one value per step.`
- 报错发生在合并阶段，两个节点其实都已经执行完了。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    topic: str
    a: str
    b: str
    shared: str


def node_a(state: State) -> dict:
    print("  [a] 执行")
    return {"a": "来自 a", "shared": "a 写的"}


def node_b(state: State) -> dict:
    print("  [b] 执行")
    return {"b": "来自 b", "shared": "b 写的"}


def merge(state: State) -> dict:
    print(f"  [merge] 看到 shared={state['shared']!r}")
    return {}


builder = StateGraph(State)
builder.add_node("a", node_a)
builder.add_node("b", node_b)
builder.add_node("merge", merge)
builder.add_edge(START, "a")
builder.add_edge(START, "b")
builder.add_edge("a", "merge")
builder.add_edge("b", "merge")
builder.add_edge("merge", END)

print("=== 两个并行节点写同一个键 ===")
try:
    result = builder.compile().invoke({"topic": "x", "a": "", "b": "", "shared": ""})
    print("  结果：", result)
except Exception as exc:
    print("  ", type(exc).__name__, ":", str(exc).splitlines()[0])

print()
print("=== 各写各的键 ===")


def safe_a(state: State) -> dict:
    return {"a": "来自 a"}


def safe_b(state: State) -> dict:
    return {"b": "来自 b"}


def pick(state: State) -> dict:
    """汇聚节点负责合并：它是唯一写 shared 的地方。"""
    return {"shared": f"{state['a']} + {state['b']}"}


b2 = StateGraph(State)
b2.add_node("a", safe_a)
b2.add_node("b", safe_b)
b2.add_node("pick", pick)
b2.add_edge(START, "a")
b2.add_edge(START, "b")
b2.add_edge("a", "pick")
b2.add_edge("b", "pick")
b2.add_edge("pick", END)
print("  结果：", b2.compile().invoke({"topic": "x", "a": "", "b": "", "shared": ""}))''',
                "code_lines": """1. `a` 与 `b` 都从 `START` 出发，构成并行分支。
2. 两个节点都返回 `shared` 键，各自写了一个不同的值。
3. 打印显示两个节点都执行了——冲突不是在执行时发现的。
4. 冲突在合并阶段爆发，抛 `InvalidUpdateError`，指明是 `shared` 这个键。
5. 报错信息后半句给出方向：需要给这个键声明合并规则（`Annotated`）。
6. 第二段改成「各写各的键」，两个节点分别写 `a` 和 `b`，没有冲突。
7. 用一个汇聚节点 `pick` 做合并，它是唯一写 `shared` 的地方，顺序可控。""",
                "output": """# 程序输出
=== 两个并行节点写同一个键 ===
  [a] 执行
  [b] 执行
   InvalidUpdateError : At key 'shared': Can receive only one value per step. Use an Annotated key to handle multiple values.

=== 各写各的键 ===
  结果： {'topic': 'x', 'a': '来自 a', 'b': '来自 b', 'shared': '来自 a + 来自 b'}""",
                "mistakes": """- 加了并行分支，但两个分支都写 `answer`，一加就崩。
- 以为报错说明「并行执行失败」，其实两个节点都跑完了，失败的是合并。
- 为了绕开报错，随便删掉一个分支的返回值，导致数据丢失。
- 在并行节点里写同一个列表（`sources`），期望自动合并。
- 用「先跑完再看谁后写」的思路设计，忽略了并行顺序本就不保证。""",
                "error_analysis": """`InvalidUpdateError: At key 'xxx': Can receive only one value per step`
—— 同一步多个节点写同一个键。要么改成各写各的键，要么给该键声明合并规则。

并行分支的结果「随机」——看起来有时是 A 有时是 B
—— 说明用了某种「最后写入胜出」的机制。这在并行下不可接受，必须显式定义合并。

加了并行后某个字段丢了
—— 某个分支没返回该字段，而另一个分支返回了整份旧状态，把它覆盖了。""",
                "beginner_practice": """1. 让 `safe_a` 也返回 `shared`，观察是否重新报错。
2. 把 `pick` 的合并逻辑改成「取较长的那个」，验证汇聚节点可以自定义规则。""",
                "advanced_practice": """假设业务确实需要「两个并行检索同时往 sources 里追加」，设计两种方案
（各写各的键后汇总 / 声明合并规则），比较它们在可读性、可测试性和失败处理上的差别。""",
                "quiz_note": "本节 6 道题：2 道基础理解（并行冲突的成因、为什么报错）+ 2 道代码阅读（读报错时机、读避坑写法）+ 2 道应用练习（改结构、设计方案）。",
                "summary": """并行节点写同一个键，合并阶段必然报错。
报错不是缺陷，而是拒绝「让结果依赖执行顺序」。
解法只有两个：各写各的键后汇总，或显式声明合并规则。""",
                "next_lesson": "下一章开始讲路由：让图按数据决定走向，包括条件边、Command 与并行分发。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-12-02",
                        "name": "并行写入冲突与合并阶段报错",
                        "goal": "能构造并读懂并行写同键的冲突，并用两种方式规避。",
                        "minutes": 35,
                        "criteria": "能说出报错发生在合并阶段而非执行阶段，并给出两种解法。",
                        "requires": ["langgraph-agent-12-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-12-02-1",
                        "kp": 0,
                        "title": "改成不冲突的结构",
                        "description": "两个并行节点都想写 `summary`，改成不报错的结构并保留两份结果。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def a(state: State) -> dict:
    return {"a": "摘要 A"}


def b(state: State) -> dict:
    return {"b": "摘要 B"}


def combine(state: State) -> dict:
    return {"summary": f"{state['a']} / {state['b']}"}


builder.add_node("a", a)
builder.add_node("b", b)
builder.add_node("combine", combine)
builder.add_edge(START, "a")
builder.add_edge(START, "b")
builder.add_edge("a", "combine")
builder.add_edge("b", "combine")
builder.add_edge("combine", END)''',
                        "explanation": "各写各的键 + 一个汇聚节点，是并行场景最稳的写法：合并规则集中在一个地方，可测试。",
                    },
                    {
                        "code": "lg-ex-12-02-2",
                        "kp": 0,
                        "title": "为什么不随便取一个",
                        "description": "框架为什么不干脆「取最后一个写入的值」，而要直接报错？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''因为「最后一个」在并行执行里没有确定含义。两个节点真的同时跑，谁先完成取决于网络、CPU 调度，
同一份输入跑两次可能得到不同结果——这就是不可复现。

不可复现的后果：测试无法稳定通过、线上问题无法回放、用户看到的结果随机变化。

相比之下，报错把「你必须定义合并语义」这件事摆到台面上。代价是一次编译/运行失败，收益是确定的行为。
在工程上，确定失败远好于不确定地「成功」。''',
                        "explanation": "「报错」在这里是一种设计选择：用显式失败换取确定性。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-12-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "两个并行节点写同一个键，什么时候报错？",
                        "options": [
                            ("A", "第一个节点执行时"),
                            ("B", "合并阶段"),
                            ("C", "编译时"),
                            ("D", "不会报错"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "两个节点都会执行完，冲突在把结果合并进状态时才被发现。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-12-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "并行节点写不同的键是允许的。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "只要键不重叠就没有合并歧义，这是并行最常用的安全写法。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-12-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "报错信息里的 `At key 'shared'` 指的是？",
                        "options": [
                            ("A", "节点名"),
                            ("B", "State 里发生冲突的字段"),
                            ("C", "边的名字"),
                            ("D", "函数参数名"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它精确指到「哪个键」冲突，顺着这个键就能找到写它的两个节点。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-12-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第二段为什么能成功？",
                        "options": [
                            ("A", "减少了并行"),
                            ("B", "两个并行节点各写各的键，冲突消失"),
                            ("C", "删掉了一个节点"),
                            ("D", "换了状态类型"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`a` 写 `a`、`b` 写 `b`，键不重叠；`shared` 只由汇聚节点 `pick` 写。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-12-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "并行分支下，「最后写入胜出」为什么不可接受？",
                        "options": [],
                        "answer": {"value": """因为「最后」依赖执行时序，而并行时序不保证。同一份输入跑两次，可能第一次 A 后写、第二次 B 后写，结果不同。

这带来三个连锁问题：① 测试会间歇性失败，团队开始「重跑一遍」而不查原因；② 线上问题无法复现，日志里两次调用的输入一模一样、输出却不同；③ 用户侧表现为「同一个问题问两次答案不同」，直接损伤信任。

确定性是这类系统的基本要求，任何把结果交给时序的设计都应该被拒绝。"""},
                        "explanation": "判断一个设计好不好，先问「同样输入跑两次结果一样吗」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-12-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个汇聚节点 `combine`：把并行分支的 `a`、`b` 两个字段合成 `summary`，格式为「A｜B」。",
                        "options": [],
                        "answer": {"value": "def combine(state: State) -> dict:\n    return {\"summary\": f\"{state.get('a', '')}｜{state.get('b', '')}\"}"},
                        "explanation": "汇聚节点是唯一写合并字段的地方，合并规则集中一处，容易测试也容易改。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
