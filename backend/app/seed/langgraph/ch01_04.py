"""LangGraph Agent 开发：第 1—4 章。

教学顺序约定：第 1—3 章只建立概念，不写图——避免在读者还不知道 State 与 Node
是什么的时候，就被要求看懂一张复杂的 Agent 图。第 4 章先跑通一个最小图，
让读者看到「完整形态长什么样」，第 5—12 章再逐块拆开。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 1 章
    {
        "code": "langgraph-agent-01",
        "order_index": 1,
        "title": "AI Agent 基础概念",
        "description": "先弄清 Agent 是什么，再看它和普通对话差在哪。",
        "lessons": [
            {
                "code": "langgraph-agent-01-lesson-01",
                "title": "什么是 AI Agent",
                "objectives": """1. 能用一句话说清 Agent 与「固定工作流」「普通对话」的区别；
2. 能说出 Agent 的三个必备要素：目标、可用动作、决策依据；
3. 能判断一个需求该写成固定流程还是 Agent；
4. 能解释为什么 Agent 必须配步数上限。""",
                "why_learn": """很多人把「提示词写得很长」叫作 Agent，结果上线后发现它只会按固定套路回答。
先把定义分清，后面写图的时候才不会把「流程」误当成「智能」。""",
                "concepts": """**Agent**：拿到一个目标，自己决定下一步做什么，做完看结果，再决定下一步。
**三要素**：目标（要达成什么）、可用动作（能做哪些事）、决策依据（凭什么选这个动作）。
**与固定工作流的区别**：固定流程的步骤由开发者写死，Agent 的步骤在运行时才确定。
**与普通对话的区别**：普通对话一次生成就结束，Agent 会多轮「做—看—想」。
**能力边界**：Agent 只能用你给它的动作，不会自己长出新能力。""",
                "plain": """固定工作流像流水线：不管来什么零件，都依次经过车、铣、磨三道工序。
Agent 像便利店店员：顾客说要退换货，他先看小票、再看商品状态，然后决定是直接退、换货还是叫店长。
工序是写死的，店员的选择是当场判断的——判断依据是你给他的规则和工具。""",
                "syntax": """**本节术语**

```text
Agent          能自主决定下一步的流程
固定工作流      步骤由开发者预先写死
可用动作        工具 / 函数 / 接口，Agent 只能在其中选
决策依据        规则、模型判断，或两者结合
步数上限        防止无限循环的安全阀
```

- 本节示例用 `@dataclass` 描述「Agent 规格」，不涉及任何框架。
- 判断标准：**如果换一个输入，步骤顺序会变，就该考虑 Agent；如果永远一样，写死更省事。**""",
                "example_code": '''from dataclasses import dataclass, field


@dataclass
class Capability:
    name: str
    description: str


@dataclass
class AgentSpec:
    goal: str
    capabilities: list[Capability] = field(default_factory=list)
    max_steps: int = 3


# 意图 -> 需要的动作。真实项目里这一步由模型判断，这里先用关键词代替
INTENT_RULES: list[tuple[tuple[str, ...], str]] = [
    (("章", "讲什么", "哪里讲"), "检索课程资料"),
    (("多少", "差几", "进度"), "调用计算器"),
]


def fixed_workflow(question: str) -> list[str]:
    """固定工作流：不管问什么都走同一条流水线。"""
    return ["检索资料", "整理答案", "输出回答"]


def agent_plan(question: str, spec: AgentSpec) -> list[str]:
    """Agent：先看问题命中哪类意图，再决定走哪条路。"""
    steps: list[str] = []
    for keywords, action in INTENT_RULES:
        if any(word in question for word in keywords) and action not in steps:
            steps.append(action)
    if not steps:
        steps.append("直接作答")
    steps.append("组织回答")
    return steps[: spec.max_steps]


spec = AgentSpec(
    goal="回答小码课程的学习问题",
    capabilities=[
        Capability("检索课程资料", "在课程正文里找相关章节"),
        Capability("调用计算器", "算学习进度与剩余课时"),
    ],
    max_steps=3,
)

for q in ["第 6 章讲什么", "我还差多少课时学完", "你好"]:
    print("问题：", q)
    print("  固定工作流 ->", fixed_workflow(q))
    print("  Agent 计划 ->", agent_plan(q, spec))

print()
print("Agent 规格：", spec.goal)
print("可用能力：", [c.name for c in spec.capabilities])
print("步数上限：", spec.max_steps)''',
                "code_lines": """1. `Capability` 只描述「有这个动作」，不含实现——和后面工具声明是同一个思路。
2. `AgentSpec` 把目标、动作、上限打包，Agent 的行为受这份规格约束。
3. `INTENT_RULES` 是决策依据的极简版：真实项目里换成模型判断，结构不变。
4. `fixed_workflow` 三次输出完全一样，说明它根本没看问题内容。
5. `agent_plan` 每次都重新判断，不同问题得到不同步骤——这就是「运行时决定」。
6. `steps[: spec.max_steps]` 截断，防止动作越界，是上限的第一道闸。
7. 最终打印规格与能力清单，Agent 能做什么由这份清单决定，不是由提示词决定。""",
                "output": """# 程序输出
问题： 第 6 章讲什么
  固定工作流 -> ['检索资料', '整理答案', '输出回答']
  Agent 计划 -> ['检索课程资料', '组织回答']
问题： 我还差多少课时学完
  固定工作流 -> ['检索资料', '整理答案', '输出回答']
  Agent 计划 -> ['调用计算器', '组织回答']
问题： 你好
  固定工作流 -> ['检索资料', '整理答案', '输出回答']
  Agent 计划 -> ['直接作答', '组织回答']

Agent 规格： 回答小码课程的学习问题
可用能力： ['检索课程资料', '调用计算器']
步数上限： 3""",
                "mistakes": """- 把「提示词写得长」当成 Agent，实际步骤仍然是写死的。
- 只给目标不给可用动作，Agent 想做事却没工具可调。
- 没有步数上限，遇到模型反复调同一个工具就停不下来。
- 用关键词替换模型判断后不做兜底，遇到没见过的问法就崩。
- 把固定流程硬改成 Agent，凭空多出不确定性和调试成本。""",
                "error_analysis": """`KeyError: 'capabilities'`
—— 用字典直接取值但规格里没这个键。用 `field(default_factory=list)` 给默认值，或取值前判断。

输出里所有问题都是同一串步骤
—— 说明「决策」其实没生效，检查判断条件是否覆盖了真实输入，或干脆退回固定流程。""",
                "beginner_practice": """1. 给 `INTENT_RULES` 加一条「作业」相关意图，观察三组问题的计划变化。
2. 把 `max_steps` 改成 1，看计划被截断成什么样，体会上限的作用。""",
                "advanced_practice": """把「关键词判断」换成一个可替换的决策函数接口（例如接收 question 返回动作名），
让规则版和模型版可以互换，并说明这样改之后测试要怎么写才不受实现影响。""",
                "quiz_note": "本节 6 道题：2 道基础理解（三要素、与固定流程的区别）+ 2 道代码阅读（读计划输出、读截断逻辑）+ 2 道应用练习（判断该不该用 Agent、补兜底分支）。",
                "summary": """Agent 的核心不是提示词，而是「运行时决定下一步」。
目标、可用动作、决策依据，三样缺一不可。
没有步数上限的 Agent 不是智能，是隐患。""",
                "next_lesson": "下一节把这个「决定下一步」的过程展开成一个循环。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-01-01",
                        "name": "Agent 三要素与适用边界",
                        "goal": "能判断一个需求该用 Agent 还是固定工作流，并说明 Agent 的三要素。",
                        "minutes": 30,
                        "criteria": "能举出「步骤随输入变化」的例子，并指出目标、可用动作、决策依据分别是什么。",
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-01-01-1",
                        "kp": 0,
                        "title": "给 Agent 补一个动作",
                        "description": "给 `AgentSpec` 增加「查询学习记录」能力，并在 `INTENT_RULES` 里加一条对应意图，使「我上周学了什么」能命中它。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''INTENT_RULES.append((("上周", "学过什么", "学习记录"), "查询学习记录"))

spec.capabilities.append(
    Capability("查询学习记录", "按时间范围查已完成的课时")
)''',
                        "explanation": "能力清单和意图规则要成对增加：只加能力不加规则，Agent 永远选不到它；只加规则不加能力，选中后无法执行。",
                    },
                    {
                        "code": "lg-ex-01-01-2",
                        "kp": 0,
                        "title": "该不该写成 Agent",
                        "description": "「用户上传发票，系统依次做 OCR、校验税号、写库」这个需求，该用固定工作流还是 Agent？说明理由。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''用固定工作流。

理由：三个步骤的先后顺序与输入无关，任何一张发票都走同一条路；失败处理也是确定的
（OCR 失败就返回重拍提示）。引入 Agent 只会让步骤变得不可预测——同样的发票可能被
走出不同路径，排查成本上升，收益为零。

判断标准：步骤顺序是否随输入变化。不变化就用固定流程，变化才需要 Agent。''',
                        "explanation": "Agent 带来的是灵活性和不确定性，两者是同一件事。没有「步骤需要变」的需求时，固定流程更可靠。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-01-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "Agent 与固定工作流最本质的区别是？",
                        "options": [
                            ("A", "使用了更大的模型"),
                            ("B", "步骤在运行时才确定"),
                            ("C", "提示词更长"),
                            ("D", "响应速度更快"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "固定工作流的步骤由开发者写死；Agent 根据当前输入和已有观察决定下一步，控制流在运行时才成形。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-01-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "一个可运行的 Agent 至少需要哪些要素？（多选）",
                        "options": [
                            ("A", "目标"),
                            ("B", "可用动作（工具）"),
                            ("C", "决策依据"),
                            ("D", "独立的 GPU 服务器"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "目标决定要做什么，动作决定能做什么，决策依据决定怎么选。算力属于部署条件，不是 Agent 的构成要素。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-01-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `fixed_workflow` 对三个不同问题返回完全相同的列表，这说明？",
                        "options": [
                            ("A", "函数有 bug"),
                            ("B", "它没有读取 question 参数去影响步骤"),
                            ("C", "Python 缓存了返回值"),
                            ("D", "问题太相似"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "函数签名收了 question 但没用它决定步骤，所以输出恒定——这正是「固定工作流」的定义性特征。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-01-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`steps[: spec.max_steps]` 在 `max_steps=1` 时，对「第 6 章讲什么」会返回什么？",
                        "options": [
                            ("A", "['检索课程资料']"),
                            ("B", "['检索课程资料', '组织回答']"),
                            ("C", "[]"),
                            ("D", "抛出 IndexError"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "切片取前 1 个元素。这暴露了截断的风险：可能把「组织回答」这一步裁掉，所以上限要按最坏情况留够。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-01-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么 Agent 必须设置步数上限？请给出一个没有上限会出问题的具体场景。",
                        "options": [],
                        "answer": {"value": "模型可能反复调用同一个工具而始终拿不到能推进的信息（例如检索一直返回空结果），流程就不会终止，既烧调用费用又让用户一直等待。设上限后，达到上限可以降级为「给出当前已有的最好答案 + 提示信息不足」，把不可控变成可控。"},
                        "explanation": "上限不是性能优化，是正确性保障：它保证流程一定会结束。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-01-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补一个兜底分支：当 `INTENT_RULES` 一条都没命中时，除了「直接作答」，还应记录一条可观测的日志。写出这段代码。",
                        "options": [],
                        "answer": {"value": "if not steps:\n    print(f\"[agent] 未命中任何意图，走兜底：{question}\")\n    steps.append(\"直接作答\")"},
                        "explanation": "兜底分支最容易被忽略，也最能反映线上真实分布——记录未命中的问题，才能持续改进意图规则。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-01-lesson-02",
                "title": "思考—行动—观察循环",
                "objectives": """1. 能画出「思考 → 行动 → 观察」的最小循环；
2. 能说明观察结果如何影响下一轮思考；
3. 能写出带终止条件的循环，并区分「正常结束」与「达到上限」；
4. 能解释为什么记录「已经做过什么」比记录「做了几次」更重要。""",
                "why_learn": """Agent 的所有复杂度，最后都落在这个循环上。
循环写不对，要么提前退出答非所问，要么停不下来。""",
                "concepts": """**思考**：根据问题和已知信息，决定下一步做什么。
**行动**：执行选定的动作，通常是一次工具调用。
**观察**：拿到动作的结果，并把它加入已知信息。
**终止条件**：某个动作表示「可以回答了」，或达到步数上限。
**状态累积**：每一轮的观察都要留下来，否则下一轮会重复劳动。""",
                "plain": """找钥匙的过程就是这个循环：想「可能在玄关」（思考），去摸一下鞋柜（行动），
摸到了／没摸到（观察），再想「那可能在客厅」（下一轮思考）。
你不会摸完鞋柜又去摸鞋柜第二遍——因为你记得已经摸过了。""",
                "syntax": """**本节术语**

```text
think()     根据已知信息决定下一步动作
act()       执行动作，返回观察结果
observe     把结果并入已知信息（示例里用 done 集合 + 列表）
is_done()   判断是否该结束
MAX_STEPS   步数上限，防止不终止
```

- 循环用 `for ... else`：正常 `break` 不进 `else`，跑满上限才进 `else`，正好区分两种结束方式。
- `done` 用集合记录已完成的动作，避免「已做过还再做」。""",
                "example_code": '''MAX_STEPS = 4


def think(question: str, done: set[str]) -> str:
    """决定下一步做什么：这里用规则代替模型。"""
    if "检索资料" not in done:
        return "检索资料"
    if "课时" in question and "统计课时" not in done:
        return "统计课时"
    return "作答"


def act(step: str, question: str) -> str:
    """执行动作，返回观察结果。"""
    if step == "检索资料":
        return "找到了 3 门相关课程"
    if step == "统计课时":
        return "合计 175 课时"
    return f"已根据以上信息回答：{question}"


def is_done(step: str) -> bool:
    return step == "作答"


question = "这 3 门课合计多少课时"
done: set[str] = set()
trace: list[str] = []

for step_no in range(1, MAX_STEPS + 1):
    step = think(question, done)
    result = act(step, question)
    done.add(step)
    trace.append(f"第 {step_no} 轮：想={step} 观察={result}")
    print(trace[-1])
    if is_done(step):
        break
else:
    print("达到步数上限仍未完成")

print()
print("轮次：", len(trace))
print("已完成的动作：", sorted(done))''',
                "code_lines": """1. `think` 只读 `done` 和问题，不产生副作用——决策要能被单独测试。
2. `act` 只执行一个动作并返回结果，不做判断——动作与决策分离，才好替换成真实工具。
3. `done.add(step)` 是「观察」的落地：把这一轮做过什么记下来。
4. `for ... else` 的 `else` 只在没 `break` 时执行，正好对应「跑满上限」。
5. `is_done` 判断放在动作执行之后，保证「作答」这一步真的产出了答案。
6. 打印 `trace` 保留全过程，出问题时能看出是哪一轮走偏。
7. 最后统计 `done`，能一眼看出哪些动作被执行过、有没有重复。""",
                "output": """# 程序输出
第 1 轮：想=检索资料 观察=找到了 3 门相关课程
第 2 轮：想=统计课时 观察=合计 175 课时
第 3 轮：想=作答 观察=已根据以上信息回答：这 3 门课合计多少课时

轮次： 3
已完成的动作： ['作答', '检索资料', '统计课时']""",
                "mistakes": """- 用「做了几次」判断是否完成，导致同一动作重复执行。
- 忘了把观察结果写回已知信息，下一轮又从头开始。
- 终止条件写在动作之前，最后一次动作做了却没人用。
- 没有 `else` 分支，跑满上限时静默结束，看不出是失败。
- 决策函数带副作用（例如顺手写了文件），一测就多出脏数据。""",
                "error_analysis": """循环次数总是等于 `MAX_STEPS`
—— 终止条件永远不成立。检查 `done` 是否真的被写入，或判断用的键名与实际动作名不一致。

`NameError: name 'question' is not defined`
—— 函数里用了外层变量却没当参数传。显式传参，别依赖闭包里的隐式状态。

同一动作被执行两次
—— 判断「是否做过」时用了列表包含整个句子（`"检索" in done` 永远为假），改成集合存动作名。""",
                "beginner_practice": """1. 把 `MAX_STEPS` 改成 2，观察输出是否走到 `else` 分支。
2. 把 `question` 换成不含「课时」的问题，看需要几轮、是否仍能正常结束。""",
                "advanced_practice": """把 `think` 改成由「当前已知信息」直接推导（不再依赖 `done` 集合），
说明这样改之后是否还会重复动作，以及为什么需要额外手段（例如记录已调用参数）来避免重复。""",
                "quiz_note": "本节 6 道题：2 道基础理解（循环三要素、终止时机）+ 2 道代码阅读（读 for-else、读 done 集合）+ 2 道应用练习（改上限、排查重复执行）。",
                "summary": """Agent 的骨架就是这个循环：想、做、看，再来一次。
观察必须写回已知信息，否则循环等于没转。
上限与终止条件要分开写：一个是正常出口，一个是安全阀。""",
                "next_lesson": "下一节把这个循环放到「普通对话」旁边对照，看清差别到底在哪。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-01-02",
                        "name": "思考—行动—观察循环与终止条件",
                        "goal": "能写出带终止条件和步数上限的循环，并区分正常结束与超限结束。",
                        "minutes": 30,
                        "criteria": "能说明观察结果如何进入下一轮，并用 for-else 区分两种结束方式。",
                        "requires": ["langgraph-agent-01-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-01-02-1",
                        "kp": 0,
                        "title": "让循环能处理新动作",
                        "description": "增加一个「查看目录」动作：当问题里出现「目录」「有哪些章」时，先执行它再作答。写出需要改的位置。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def think(question: str, done: set[str]) -> str:
    if "目录" in question or "有哪些章" in question:
        if "查看目录" not in done:
            return "查看目录"
        return "作答"
    if "检索资料" not in done:
        return "检索资料"
    if "课时" in question and "统计课时" not in done:
        return "统计课时"
    return "作答"


def act(step: str, question: str) -> str:
    if step == "查看目录":
        return "共 28 章，第 1 章是 AI Agent 基础概念"
    if step == "检索资料":
        return "找到了 3 门相关课程"
    if step == "统计课时":
        return "合计 175 课时"
    return f"已根据以上信息回答：{question}"''',
                        "explanation": "加动作要同时改 `think`（能选到它）和 `act`（能执行它）。只改一处就会出现「选中了但不会执行」或「会执行但永远选不到」。",
                    },
                    {
                        "code": "lg-ex-01-02-2",
                        "kp": 0,
                        "title": "为什么用集合而不是计数",
                        "description": "如果把 `done: set[str]` 改成 `steps: int` 只记次数，会出现什么问题？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''计数只能回答「做了几次」，回答不了「做过哪些」。

具体问题：① 无法判断某个动作是否已做过，容易重复执行同一个动作；
② 加动作后，判断逻辑要跟着改数字，改错就漏步或空转；
③ 出问题时看不到执行顺序，排查只能靠猜。

集合记录的是「做过什么」，天然幂等；需要顺序时再用列表同时保留 trace。''',
                        "explanation": "状态的设计决定了判断能写多准。用集合表达「已完成的动作」比用计数器更贴近语义。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-01-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "循环里的「观察」这一步，本质上做了什么？",
                        "options": [
                            ("A", "把动作结果并入已知信息"),
                            ("B", "重新执行一次动作"),
                            ("C", "重置所有状态"),
                            ("D", "通知用户"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "观察的结果必须成为下一轮思考的输入，否则循环会重复同样的动作。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-01-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只要设置了 `MAX_STEPS`，就不需要再写终止条件了。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "上限只是安全阀，保证一定会停；没有正常终止条件的话，每次都跑满上限，既慢又浪费调用。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-01-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "把 `MAX_STEPS` 设为 2、问题为「这 3 门课合计多少课时」，输出会是什么？",
                        "options": [
                            ("A", "打印 3 轮并正常结束"),
                            ("B", "打印 2 轮后打印「达到步数上限仍未完成」"),
                            ("C", "直接抛异常"),
                            ("D", "打印 2 轮后静默退出"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "两轮只做完「检索资料」和「统计课时」，没走到「作答」，循环跑满后进入 `else`。这说明上限要按最坏路径留够。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-01-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`for ... else` 中的 `else` 在什么情况下执行？",
                        "options": [
                            ("A", "循环体抛异常时"),
                            ("B", "循环正常跑完、没有被 `break` 时"),
                            ("C", "每次循环结束后"),
                            ("D", "条件为假时"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`else` 是「没被 break 打断」的分支，正好用来表示「跑满上限仍未完成」，比加一个标志变量更简洁。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-01-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如果 `act` 里直接修改了 `question`（例如拼接上检索结果），会带来什么风险？",
                        "options": [],
                        "answer": {"value": "问题文本会被越改越长，且每一轮判断都基于被改过的文本：① 终止条件可能永远不成立（关键词被稀释）；② 无法区分「用户原话」和「加工后的文本」，出问题难以回放；③ 若做了持久化，历史记录会被污染。正确做法是把原始问题和观察结果分成两个字段，观察只追加不改原问题。"},
                        "explanation": "输入是事实，观察是增量。混在一起后，任何一次重跑都会得到不同结果——这在 Agent 里是致命的。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-01-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给循环加一条保护：如果连续两轮都选中同一个动作，立即中止并打印原因。写出这段代码。",
                        "options": [],
                        "answer": {"value": "last: str | None = None\nfor step_no in range(1, MAX_STEPS + 1):\n    step = think(question, done)\n    if step == last:\n        print(f\"连续两轮选中 {step}，中止\")\n        break\n    last = step\n    ..."},
                        "explanation": "「连续重复同一动作」是死循环最常见的形态，比步数上限更早发现问题，也能给出更准确的错误信息。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 2 章
    {
        "code": "langgraph-agent-02",
        "order_index": 2,
        "title": "Agent 与普通大模型对话的区别",
        "description": "差别不在模型，而在谁决定下一步。",
        "lessons": [
            {
                "code": "langgraph-agent-02-lesson-01",
                "title": "一次生成与多步决策",
                "objectives": """1. 能说清「一次生成」与「多步决策」在控制流上的差别；
2. 能识别哪些问题一次生成就够、哪些必须多步；
3. 能解释多步决策为什么能拿到模型不知道的实时数据；
4. 能说明多步决策带来的新成本：延迟、失败面、可观测性。""",
                "why_learn": """这是整门课的分水岭：从这一节起，你的程序不再「调用一次模型拿一段文本」，
而是「调用若干次模型和工具，直到拿到能回答的数据」。""",
                "concepts": """**一次生成**：一次请求、一次响应，控制流是一条直线。
**多步决策**：先判断需要什么，再取数据，再计算，最后生成；控制流有分支和循环。
**事实来源**：一次生成只能靠模型记忆，多步决策可以用工具把事实喂进去。
**新成本**：多步意味着更多次调用、更长延迟、更多可能失败的点位。
**判断标准**：回答是否需要「模型不知道的、会变的、需要计算的」信息。""",
                "plain": """一次生成像闭卷考试：只能写脑子里记得的，记错了也照写。
多步决策像开卷考试加计算器：先翻目录找章节（取数据），再用计算器算（计算），
最后写答案。答案对不对，取决于你有没有真的去翻书，而不是取决于你记性好不好。""",
                "syntax": """**本节术语**

```text
一次生成    一次请求 → 一次响应，流程结束
多步决策    判断 → 取数 → 计算 → 生成，可能多轮
事实来源    工具返回的真实数据
失败面      可能出错的位置数量
```

- 示例用两个纯函数对比，不涉及模型调用，先看清控制流差异。
- 关键差别只有一个：**多步决策的输出依赖运行时取回的数据，一次生成的输出只依赖输入。**""",
                "example_code": '''# 普通对话：一次生成，模型看不到任何实时数据
def one_shot(question: str) -> str:
    return f"（凭记忆回答）{question}：大概 40 课时吧。"


# 多步决策：先判断要什么数据，再取，再算，最后答
def multi_step(question: str) -> str:
    if "课时" not in question:
        return f"（直接回答）{question}"

    total = 175          # 查库得到的课时总数
    if "还剩" in question or "差" in question:
        finished = 62    # 查进度得到的已完成课时
        return f"你已完成 {finished} 课时，还剩 {total - finished} 课时（合计 {total}）。"
    return f"这门课合计 {total} 课时。"


for q in ["LangGraph 课有多少课时", "LangGraph 课我还剩多少课时", "你好"]:
    print("问题：", q)
    print("  一次生成 ->", one_shot(q))
    print("  多步决策 ->", multi_step(q))''',
                "code_lines": """1. `one_shot` 不看任何外部数据，输出里的「40 课时」是编的。
2. `multi_step` 第一步先判断「要不要取数据」，这一步就是决策。
3. `total = 175` 模拟查库：真实项目里换成查课程表或调接口。
4. `finished = 62` 只在需要时才查，避免为不需要的信息付代价。
5. 计算放在代码里做，不让模型心算——数字类事实一律交给代码。
6. 三个问题分别走到「取数+计算」「取数」「直接回答」三条路径。
7. 对比输出可见：一次生成的答案对「还剩多少」这种问题完全不可用。""",
                "output": """# 程序输出
问题： LangGraph 课有多少课时
  一次生成 -> （凭记忆回答）LangGraph 课有多少课时：大概 40 课时吧。
  多步决策 -> 这门课合计 175 课时。
问题： LangGraph 课我还剩多少课时
  一次生成 -> （凭记忆回答）LangGraph 课我还剩多少课时：大概 40 课时吧。
  多步决策 -> 你已完成 62 课时，还剩 113 课时（合计 175）。
问题： 你好
  一次生成 -> （凭记忆回答）你好：大概 40 课时吧。
  多步决策 -> （直接回答）你好""",
                "mistakes": """- 把「多轮对话」当成「多步决策」：前者只是历史变长，控制流没变。
- 让模型自己算数，结果 175-62 算成 103。
- 所有问题都走完整多步流程，简单寒暄也要查库，延迟翻倍。
- 只在提示词里写「请查数据库」，模型没有工具，只能编。
- 忽略了多步带来的失败面：任一环节失败都要有降级路径。""",
                "error_analysis": """模型回答的课时数每次都不同
—— 它在估算而不是取值。数字、日期、库存这类事实必须由代码提供。

「你好」也走了完整流程，响应很慢
—— 缺少「是否需要外部数据」的前置判断。加一层意图识别，闲聊直接短路。

多步流程中间某步超时，整体没有任何输出
—— 没有降级路径。每步都要能给出「拿不到时说什么」。""",
                "beginner_practice": """1. 给 `multi_step` 加一条「推荐下一门课」的分支，需要读取「已学课程」数据。
2. 把 `total` 改成从字典读取，模拟不同课程有不同课时。""",
                "advanced_practice": """为 `multi_step` 设计一个「失败也能答」的版本：取数失败时返回什么、
计算缺参数时返回什么、模型生成失败时返回什么，分别写清并说明用户看到的话术。""",
                "quiz_note": "本节 6 道题：2 道基础理解（控制流差异、何时该多步）+ 2 道代码阅读（读判断分支、读计算来源）+ 2 道应用练习（设计降级、识别伪多步）。",
                "summary": """一次生成只依赖输入，多步决策依赖运行时取回的数据。
多步的价值是「事实可控」，代价是延迟、失败面和复杂度。
数字和事实交给代码，模型只负责组织语言。""",
                "next_lesson": "下一节看：既然要多步、要分支、要循环，用什么结构来表达最清楚。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-02-01",
                        "name": "一次生成与多步决策的控制流差异",
                        "goal": "能判断一个问题需要一次生成还是多步决策，并说明事实来源从哪里来。",
                        "minutes": 30,
                        "criteria": "能指出多步决策中「判断是否取数」这一步的位置，并说明缺了它会怎样。",
                        "requires": ["langgraph-agent-01-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-02-01-1",
                        "kp": 0,
                        "title": "识别伪多步",
                        "description": "下面这个函数看起来是多步，其实不是。指出问题并改写。\n\n```python\ndef answer(q):\n    if \"课时\" in q:\n        return one_shot(q)\n    return one_shot(q)\n```",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''问题：两个分支都调用 `one_shot`，控制流没有真正分叉，事实来源仍然是模型记忆。

改写：

def answer(q: str) -> str:
    if "课时" not in q:
        return one_shot(q)
    total = 175
    return f"这门课合计 {total} 课时。"''',
                        "explanation": "多步的判据是「是否引入了外部事实」，不是「代码里有没有 if」。分支走向同一个数据源时，仍然是单步。",
                    },
                    {
                        "code": "lg-ex-02-01-2",
                        "kp": 0,
                        "title": "算数该谁做",
                        "description": "为什么「175 - 62 = ?」不让模型算，而要写在代码里？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''模型做的是「生成最可能的文本」，不是「执行确定的运算」。同样输入可能得到不同结果，
大数相减、小数位、单位换算都容易出错，而且错了无法察觉——它不会告诉你「我不确定」。

代码算就三个好处：结果确定、可测试、出错能定位到行。

所以分工是：模型负责理解问题和组织语言，代码负责取值与计算。''',
                        "explanation": "这条分工是 AI 应用的稳定性底线。凡是有唯一正确答案的部分，都往代码挪。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-02-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "判断一个问题是否需要多步决策，最直接的依据是？",
                        "options": [
                            ("A", "问题长度"),
                            ("B", "回答是否需要模型不知道的、会变的数据"),
                            ("C", "使用什么模型"),
                            ("D", "用户是否着急"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "需要外部事实就必须取数，取数就是多步；纯语言组织类问题一次生成就够。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-02-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "「多轮对话」和「多步决策」是同一件事。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "多轮对话是历史消息变长，控制流仍是「一问一答」；多步决策是多轮「想—做—看」，控制流本身就变了。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-02-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中「你好」走的是哪条路径？",
                        "options": [
                            ("A", "查库 + 计算"),
                            ("B", "查库"),
                            ("C", "直接回答，不查任何数据"),
                            ("D", "抛出异常"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "`\"课时\" not in question` 命中，直接返回。这个短路省掉了一次无谓的数据查询。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-02-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "如果把 `total` 改成模型生成的值，最可能出现什么问题？",
                        "options": [
                            ("A", "程序变慢"),
                            ("B", "同一问题多次询问得到不同课时数"),
                            ("C", "代码无法运行"),
                            ("D", "无法换行"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "生成是概率性的，同一个事实每次都可能不同。用户连着问两次得到两个答案，信任立刻崩塌。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-02-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "多步决策相比一次生成，多出了哪些成本？至少说三点。",
                        "options": [],
                        "answer": {"value": "① 延迟：多一次取数/计算就多一段等待，串行时叠加明显；② 失败面：每个环节都可能超时、报错、返回空；③ 调用成本：可能多次请求模型；④ 可观测性：出问题要知道是哪一步，需要额外记录；⑤ 状态管理：要在步骤之间传递和合并数据，设计不当会互相覆盖。"},
                        "explanation": "把成本讲清楚，才能在方案评审时说清「这个需求值不值得上 Agent」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-02-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "为取数环节加降级：查不到 `total` 时，返回一句「暂时查不到课时信息」，不要抛异常给用户。写出代码。",
                        "options": [],
                        "answer": {"value": "def get_total() -> int | None:\n    return COURSES.get(\"langgraph-agent\")\n\n\ndef multi_step(question: str) -> str:\n    if \"课时\" not in question:\n        return one_shot(question)\n    total = get_total()\n    if total is None:\n        return \"暂时查不到课时信息，请稍后再试。\"\n    return f\"这门课合计 {total} 课时。\""},
                        "explanation": "降级要落在「用户能看到一句话」，而不是「日志里有异常」。异常留给日志，话术留给用户。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ---------------------------------------------------------------- 第 3 章
    {
        "code": "langgraph-agent-03",
        "order_index": 3,
        "title": "LangGraph 的作用",
        "description": "多步、带分支和循环的流程，需要图来表达。",
        "lessons": [
            {
                "code": "langgraph-agent-03-lesson-01",
                "title": "从链式调用到图编排",
                "objectives": """1. 能说出链式调用在什么情况下不够用；
2. 能用「节点 + 依赖 + 走向」三要素描述一张图；
3. 能解释图编排带来的三个好处：可分支、可复用、可恢复；
4. 能判断一个需求用链式还是用图更合适。""",
                "why_learn": """链式调用写起来快，但一旦有分支、循环和失败重试，代码就会变成一层套一层的 if。
图把「谁在跑、跑完去哪」从代码里抽出来，变成可看、可改、可测的结构。""",
                "concepts": """**链式调用**：一步接一步，上一步的输出直接当下一步的输入，适合线性流程。
**图编排**：用节点表示步骤、用边表示走向，流程结构与业务代码分离。
**分支**：同一个节点可以有多条出边，按条件选一条。
**复用**：节点不关心自己被谁调用，可以接到任何位置。
**可恢复**：流程结构明确后，才能「从某一步继续」——这是后面 Checkpointer 的前提。""",
                "plain": """链式调用像接力跑：棒子只能往下一个人手里传，路线提前画好。
图编排像地铁线路图：同一个站可以有几个方向，换乘点能去不同的线，
某一段停运了还能绕行——线路是画出来的，不是藏在跑的人脑子里。""",
                "syntax": """**本节术语**

```text
节点(node)   一个步骤，输入是共享数据，输出是增量
边(edge)     走向声明：A 之后去 B
依赖(deps)   本步骤需要哪些上游结果先就绪
分支          一个节点有多条出边，按条件选
```

- 本节用字典描述图，不引入框架，目的是先看清「图」到底比「链」多了什么。
- 判断标准：**如果流程里出现 if/while 来改变步骤顺序，就该考虑图。**""",
                "example_code": '''# 链式调用：一条直线，每步只认识上一步
def chain_pipeline(question: str) -> str:
    text = retrieve(question)
    text = summarize(text)
    return answer(text)


def retrieve(question: str) -> str:
    return "第 6 章讲 State、Node、Edge；第 13 章讲条件路由。"


def summarize(text: str) -> str:
    return text[:12] + "…"


def answer(text: str) -> str:
    return f"根据资料：{text}"


# 图编排：用依赖表描述「谁读谁的结果」，节点从共享结果里取上游输出
NODES = {
    "classify": {"needs": [], "run": lambda q, d: "课程问题" if "章" in q else "闲聊"},
    "retrieve": {"needs": ["classify"], "run": lambda q, d: retrieve(q)},
    "summarize": {"needs": ["retrieve"], "run": lambda q, d: d["retrieve"][:12] + "…"},
    "answer": {"needs": ["summarize"], "run": lambda q, d: f"根据资料：{d['summarize']}"},
    "smalltalk": {"needs": ["classify"], "run": lambda q, d: "你好，我是学习助手。"},
}

NEXT = {"classify": ["retrieve"], "retrieve": ["summarize"], "summarize": ["answer"]}


def run_graph(question: str, entry: str = "classify") -> dict:
    done: dict[str, str] = {}
    pending = [entry]

    while pending:
        name = pending.pop(0)
        node = NODES[name]
        if any(dep not in done for dep in node["needs"]):
            pending.append(name)          # 依赖没就绪，排到队尾
            continue
        done[name] = node["run"](question, done)
        if name == "classify":
            # 图上可以分叉：不同分类走不同分支
            pending = ["smalltalk"] if done[name] == "闲聊" else list(NEXT["classify"])
        else:
            pending.extend(NEXT.get(name, []))
    return done


print("链式：", chain_pipeline("第 6 章讲什么"))
print()
for q in ["第 6 章讲什么", "你好"]:
    print("图编排：", q)
    for key, value in run_graph(q).items():
        print(f"   {key:10s} -> {value}")''',
                "code_lines": """1. `chain_pipeline` 里三步的顺序写死在代码中，想插一步必须改函数体。
2. `NODES` 用 `needs` 声明依赖，流程结构变成数据，改结构不用改执行逻辑。
3. `run` 接收 `(question, done)`：`done` 就是共享结果，节点从中读上游输出。
4. `summarize` 读的是 `d["retrieve"]`，节点之间通过共享数据传递，而不是函数返回值串联。
5. `pending` 队列 + 依赖检查，保证节点只在依赖就绪后执行。
6. `classify` 之后有两个可能去向，这是链式调用做不到的分支。
7. `NEXT` 只描述「正常走向」，特殊分支在 `classify` 后单独处理。""",
                "output": """# 程序输出
链式： 根据资料：第 6 章讲 State…

图编排： 第 6 章讲什么
   classify   -> 课程问题
   retrieve   -> 第 6 章讲 State、Node、Edge；第 13 章讲条件路由。
   summarize  -> 第 6 章讲 State…
   answer     -> 根据资料：第 6 章讲 State…
图编排： 你好
   classify   -> 闲聊
   smalltalk  -> 你好，我是学习助手。""",
                "mistakes": """- 用图写线性流程，多了一堆结构却没有任何分支，纯属增加复杂度。
- 节点之间靠函数返回值串联，共享数据形同虚设，等于又写回了链式。
- 忘了检查依赖，节点在上游还没产出时就读数据，拿到空值。
- 分支只处理了「正常」那条，没写兜底，遇到意外输入直接卡住。
- 循环没有出口，`pending` 队列永不空。""",
                "error_analysis": """`KeyError: 'retrieve'`
—— 节点读了一个还没执行的上游结果。检查 `needs` 是否声明了该依赖。

程序卡死不结束
—— `pending` 里同一个节点被反复追加。检查依赖条件是否永远无法满足，以及是否缺少退出判断。

`RecursionError` / 内存暴涨
—— 分支逻辑把节点重新加回队列却没有状态推进，形成死循环。""",
                "beginner_practice": """1. 在 `NEXT` 里给 `answer` 加一条回到 `classify` 的边，观察是否形成循环、如何退出。
2. 增加一个 `check_sources` 节点，插在 `retrieve` 与 `summarize` 之间。""",
                "advanced_practice": """把 `summarize` 拆成两个可并行的节点（摘要 + 提取关键词），
说明在共享数据上用字典合并会遇到什么问题，以及需要什么样的合并规则——这正是后面 Reducer 要解决的。""",
                "quiz_note": "本节 6 道题：2 道基础理解（链与图的差别、何时用图）+ 2 道代码阅读（读依赖检查、读分支）+ 2 道应用练习（加节点、预判合并问题）。",
                "summary": """链式适合线性流程，图适合有分支和循环的流程。
图把流程结构从代码里抽出来，变成可看可改的数据。
有了明确的结构，才谈得上恢复、并行和可视化。""",
                "next_lesson": "下一章开始动手：先把 LangGraph 装好，跑通一个最小图。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-03-01",
                        "name": "链式调用与图编排的适用边界",
                        "goal": "能说明图相比链多出的能力，并判断需求该用哪种结构。",
                        "minutes": 30,
                        "criteria": "能指出链式在分支、复用、恢复三方面的局限，并给出对应场景。",
                        "requires": ["langgraph-agent-02-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-03-01-1",
                        "kp": 0,
                        "title": "给图加一个节点",
                        "description": "在上面的图里加一个 `cite` 节点，在 `summarize` 之后、`answer` 之前，输出「引用：第 6 章」。写出需要改的两处。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''NODES["cite"] = {
    "needs": ["summarize"],
    "run": lambda q, d: "引用：第 6 章",
}

NEXT["summarize"] = ["cite"]
NEXT["cite"] = ["answer"]''',
                        "explanation": "加节点要同时改「节点定义」和「走向声明」。只加定义不加走向，节点永远不会被执行。",
                    },
                    {
                        "code": "lg-ex-03-01-2",
                        "kp": 0,
                        "title": "链式为什么撑不住",
                        "description": "用链式调用实现「问题分类 → 分类不同走不同处理」会遇到什么具体困难？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''链式只能顺序传值，遇到分支就得在函数内部写 if，把「流程」和「业务」混在一起。

具体困难：① 分支越多，主函数越长，改一条路径要通读全部；② 想复用某一段（比如检索+摘要）只能复制代码或抽函数，抽出来又失去上下文；③ 无法表达「回到之前某一步」；④ 想在某一步暂停（等待人工确认）几乎无法实现，因为调用栈已经压在那里。

图的解法是把「走向」变成声明，执行器只管按声明跑，业务函数不关心自己被谁调用。''',
                        "explanation": "这些困难不是风格问题，而是结构问题：调用栈天然只能表示「线性 + 嵌套」，不能表示任意跳转。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-03-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "图编排相比链式调用，最核心的增益是？",
                        "options": [
                            ("A", "运行更快"),
                            ("B", "流程结构从代码中解耦，可分支、可复用、可恢复"),
                            ("C", "不需要写函数"),
                            ("D", "自动生成提示词"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "速度不是图的卖点。图的价值在于结构可见、可改，从而支撑分支、复用与断点恢复。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-03-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "以下哪些需求适合用图而不是链式？（多选）",
                        "options": [
                            ("A", "按问题类型走不同处理分支"),
                            ("B", "失败后回到上一步重试"),
                            ("C", "三步固定格式转换"),
                            ("D", "中途暂停等人工确认"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "分支、回退重试、暂停后恢复都超出线性调用栈的表达能力；固定三步转换用链式最简单。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-03-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`run_graph` 里 `if any(dep not in done for dep in node[\"needs\"])` 的作用是？",
                        "options": [
                            ("A", "检查节点是否已经执行过"),
                            ("B", "检查上游依赖是否都已产出结果"),
                            ("C", "检查是否死循环"),
                            ("D", "检查返回值类型"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "它保证节点只在依赖就绪后执行，未就绪时先排到队尾，避免读到空数据。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-03-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "如果删掉 `classify` 分支里对 `smalltalk` 的处理，问「你好」会发生什么？",
                        "options": [
                            ("A", "仍然走完整课程问答流程"),
                            ("B", "返回空结果"),
                            ("C", "抛 KeyError"),
                            ("D", "进入死循环"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "分支条件写成「只要不是闲聊就走 retrieve」，闲聊也会被塞进课程问答路径，得到无关答案。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-03-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说「可恢复」是图编排的前提条件？",
                        "options": [],
                        "answer": {"value": "恢复的前提是知道「此刻停在哪一步、之前每步产出了什么」。链式调用里这些信息散落在调用栈和局部变量中，进程一退出就没了，无法定位到「第几步」。图把步骤和走向显式声明出来，执行器可以在每步结束时保存「当前节点 + 共享数据」，下次从该节点继续。没有结构，就没有「从哪继续」这个概念。"},
                        "explanation": "这条因果链一直延伸到第 20 章的 Checkpointer：先有图，才有检查点。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-03-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给 `run_graph` 加一个最大执行步数，超过就停下来并打印已完成的节点。写出改动。",
                        "options": [],
                        "answer": {"value": "def run_graph(question: str, entry: str = \"classify\", max_steps: int = 10) -> dict:\n    done: dict[str, str] = {}\n    pending = [entry]\n    steps = 0\n\n    while pending and steps < max_steps:\n        steps += 1\n        name = pending.pop(0)\n        ...\n    else:\n        if pending:\n            print(f\"达到上限 {max_steps}，未完成：{pending}\")\n    return done"},
                        "explanation": "自己实现的执行器必须自己兜底。真实框架里对应的就是 `recursion_limit`，第 14 章会讲。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ---------------------------------------------------------------- 第 4 章
    {
        "code": "langgraph-agent-04",
        "order_index": 4,
        "title": "LangGraph 项目初始化",
        "description": "把环境装好、把版本钉住，再跑通第一个图。",
        "lessons": [
            {
                "code": "langgraph-agent-04-lesson-01",
                "title": "安装与版本确认",
                "objectives": """1. 能装好 LangGraph 并用代码确认版本；
2. 能解释为什么必须先看版本，再决定抄哪份文档；
3. 能列出本课程依赖的三个包及各自职责；
4. 能在导入失败时快速定位是缺包还是路径变了。""",
                "why_learn": """LangGraph 在 1.0 之后调整过模块位置和若干签名。
照着旧博客抄代码，最常见的报错不是逻辑错，而是「这个导入路径在这一版不存在」。""",
                "concepts": """**三个包的分工**：`langgraph` 提供图与执行器，`langchain-core` 提供消息与模型接口，`langgraph-checkpoint` 提供检查点能力。
**版本先于文档**：先打印版本，再对照该版本的 API，不要跨版本混抄。
**导入自检**：启动时验证关键导入可用，比运行到一半才炸更早暴露问题。
**不要锁死补丁号**：锁到次版本（如 `~=1.2`），既拿到修复又不被大版本突变打穿。""",
                "plain": """这就像装修前先量房：不量就买材料，尺寸一定不对，返工的钱比量房的时间贵得多。
版本号就是这套房子的尺寸——同一段代码在不同版本里，可能连「门在哪」都不一样。
先花两分钟打印版本，能省掉两小时对着报错猜原因。
顺序永远是：先确认环境，再抄别人的代码；环境不对，抄得再准也跑不起来。""",
                "syntax": """**安装（命令行）**

```bash
pip install "langgraph~=1.2"
python -c "import langgraph, importlib.metadata as m; print(m.version('langgraph'))"
```

**本课程实测环境**

```text
langgraph            1.2.20
langchain-core       1.7.6
langgraph-checkpoint 4.3.1
Python               3.14
```

- 示例只用 `importlib.metadata` 读版本，不依赖任何第三方库。
- 用 `~=` 而不是 `==`：允许补丁级更新，避免被一个小修复卡住。""",
                "example_code": '''import importlib.metadata as md

PKG = "langgraph"
MIN_VERSION = (1, 0)


def read_version(name: str) -> str | None:
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return None


def check(minimum: tuple[int, int]) -> str:
    raw = read_version(PKG)
    if raw is None:
        return f"{PKG} 未安装：pip install {PKG}"
    major, minor = (int(x) for x in raw.split(".")[:2])
    if (major, minor) < minimum:
        return f"{PKG} {raw} 低于要求的 {minimum[0]}.{minimum[1]}，请升级"
    return f"{PKG} {raw} 可用"


print(check(MIN_VERSION))
print("langchain-core:", read_version("langchain-core"))
print("checkpoint 插件:", read_version("langgraph-checkpoint"))

# 导入自检：只验证「这一版有没有这个模块」，避免照抄旧版路径
from langgraph.graph import END, START, StateGraph

print("关键导入：StateGraph / START / END 全部就绪")''',
                "code_lines": """1. `read_version` 捕获 `PackageNotFoundError`，把「没装」变成可读的提示，而不是一串 traceback。
2. `raw.split(".")[:2]` 只取主次版本，`"1.2.20"` 得到 `(1, 2)`。
3. 元组比较天然按主、次顺序判断，不需要手写三段 if。
4. 三个包分别打印：缺哪个一目了然。
5. 导入放在版本检查之后：版本不对时先给结论，不让读者被导入报错带偏。
6. 自检只导入本章会用到的三个名字，范围小、信息明确。""",
                "output": """# 程序输出
langgraph 1.2.20 可用
langchain-core: 1.7.6
checkpoint 插件: 4.3.1
关键导入：StateGraph / START / END 全部就绪""",
                "mistakes": """- 用 `pip install langgraph` 但不看版本，抄到 0.x 的写法后到处报导入错误。
- 把 `langgraph`、`langchain`、`langchain-core` 混为一谈，装了没用的包。
- 依赖写 `==` 锁死补丁号，安全补丁出不来。
- 只在报错后猜版本，不在启动时打印版本。
- 把示例里的 `1.2.20` 当成「必须装这个版本」，其实次版本一致即可。""",
                "error_analysis": """`ModuleNotFoundError: No module named 'langgraph'`
—— 包没装，或装到了另一个虚拟环境。先确认 `sys.executable` 与 `pip` 是同一环境。

`ImportError: cannot import name 'START' from 'langgraph.graph'`
—— 版本过低（0.x 早期没有 `START`/`END`）。升级到 1.x。

`PackageNotFoundError`
—— `importlib.metadata` 在该环境找不到分发信息，通常还是环境不对。""",
                "beginner_practice": """1. 把 `MIN_VERSION` 改成 `(2, 0)`，观察提示信息如何变化。
2. 打印 `sys.executable`，确认当前用的是哪个 Python 环境。""",
                "advanced_practice": """写一个 `check_env()`：一次检查三个包、打印 Python 版本，并在任一不满足时返回非零退出码，
说明为什么这类检查适合放在 CI 的第一步而不是应用启动时。""",
                "quiz_note": "本节 6 道题：2 道基础理解（三个包分工、为何先看版本）+ 2 道代码阅读（读版本解析、读异常捕获）+ 2 道应用练习（写检查函数、处理导入失败）。",
                "summary": """先装包、再看版本，最后才轮到抄代码。
三个包分工明确：图与执行器、消息与模型接口、检查点。
版本检查放在启动处，问题早暴露。""",
                "next_lesson": "下一节直接跑一个最小图，先看到完整形态。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-04-01",
                        "name": "依赖安装与版本确认",
                        "goal": "能装好依赖、确认版本，并在导入失败时定位原因。",
                        "minutes": 30,
                        "criteria": "能说出三个包各自的职责，并用代码打印版本与关键导入。",
                        "requires": ["langgraph-agent-03-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-04-01-1",
                        "kp": 0,
                        "title": "写一个环境自检",
                        "description": "写 `check_env()`，检查 `langgraph`、`langchain-core`、`langgraph-checkpoint` 三个包是否都装了，缺哪个列出来。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''REQUIRED = ("langgraph", "langchain-core", "langgraph-checkpoint")


def check_env() -> list[str]:
    missing = []
    for name in REQUIRED:
        try:
            version = md.version(name)
        except md.PackageNotFoundError:
            missing.append(name)
        else:
            print(f"{name:24s} {version}")
    return missing


missing = check_env()
if missing:
    print("缺少依赖：", ", ".join(missing))''',
                        "explanation": "把「缺什么」一次性列全，比装一个跑一次、报错一次要快得多。",
                    },
                    {
                        "code": "lg-ex-04-01-2",
                        "kp": 0,
                        "title": "为什么不用 == 锁死",
                        "description": "依赖写成 `langgraph==1.2.20` 有什么问题？应该怎么写？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''`==` 精确锁到补丁号，会带来两个问题：① 官方发布的安全修复与 bug 修复（1.2.21）装不上，
要人工改依赖才能拿到；② 与其它包共用环境时更容易冲突。

推荐 `~=1.2`（等价于 `>=1.2, ==1.*`），锁住主次版本、放开补丁号。真正需要完全可复现时，
用 lock 文件固定全部依赖的精确版本，而不是在 `requirements.txt` 里逐个写 `==`。''',
                        "explanation": "「可复现」和「能升级」要同时满足，靠的是 lock 文件，而不是把人肉版本号写死。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-04-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`langchain-core` 在本课程里主要负责什么？",
                        "options": [
                            ("A", "图与执行器"),
                            ("B", "消息类型与聊天模型接口"),
                            ("C", "检查点存储"),
                            ("D", "HTTP 服务"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`langgraph` 管图，`langchain-core` 管消息与模型抽象，`langgraph-checkpoint` 管检查点。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-04-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只要 `pip install langgraph` 成功，就一定能用教程里的所有导入路径。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "导入路径会随版本变化。同一个包名，不同版本可能在不同模块下，必须先确认版本。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-04-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`raw.split(\".\")[:2]` 对 `\"1.2.20\"` 的结果是？",
                        "options": [
                            ("A", "['1', '2']"),
                            ("B", "['1', '2', '20']"),
                            ("C", "'1.2'"),
                            ("D", "('1', '2', '20')"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "切片取前两个元素，再被 `int()` 转成整数元组，用于比较主次版本。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-04-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "如果包已安装但版本是 `0.6.0`，`check((1, 0))` 返回什么？",
                        "options": [
                            ("A", "「langgraph 0.6.0 可用」"),
                            ("B", "「低于要求的 1.0，请升级」"),
                            ("C", "「未安装」"),
                            ("D", "抛 TypeError"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "元组比较 `(0, 6) < (1, 0)` 为真，走进升级分支——这正是 0.x 代码不能直接用的原因。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-04-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么版本检查要放在「导入之前」？",
                        "options": [],
                        "answer": {"value": "导入失败抛出的信息只告诉你「某个名字不存在」，不会告诉你「因为版本太低」。初学者看到 `ImportError` 往往先去搜导入路径，方向就错了。先比版本再导入，能把结论直接摆出来：是版本不对，不是路径写错。顺序颠倒时，读者要读完整段 traceback 才能回到同一个结论。"},
                        "explanation": "错误信息的可读性直接决定排障速度，这也是把检查写成函数而不是散在注释里的原因。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-04-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补一段代码：若 `langgraph` 版本低于 `(1, 2)`，直接 `raise SystemExit` 并给出安装命令。",
                        "options": [],
                        "answer": {"value": "raw = read_version(\"langgraph\")\nif raw is None:\n    raise SystemExit(\"未安装 langgraph，请执行：pip install 'langgraph~=1.2'\")\nif (int(raw.split(\".\")[0]), int(raw.split(\".\")[1])) < (1, 2):\n    raise SystemExit(f\"langgraph {raw} 过低，请执行：pip install -U 'langgraph~=1.2'\")"},
                        "explanation": "启动即失败（fail fast）比运行到第三个节点才崩更省时间，也让部署问题在启动日志里就能看见。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-04-lesson-02",
                "title": "跑通第一个图",
                "objectives": """1. 能写出一个两节点的最小图并运行；
2. 能读懂 `invoke` 的返回值与 `get_graph().draw_mermaid()` 的输出；
3. 能说出本图里 State、Node、Edge 分别对应代码的哪一部分；
4. 能解释为什么这一节只跑两节点直连、不直接写 Agent。""",
                "why_learn": """先看见完整形态，再拆零件，学习曲线会平缓很多。
这一节的目标只有一个：让图真的跑起来，并且知道自己刚才跑的是什么。""",
                "concepts": """**State**：一个 `TypedDict`，声明图里流转哪些字段。
**Node**：一个函数，参数是当前状态，返回要更新的字段。
**Edge**：`add_edge` 声明「A 之后去 B」；`START` 和 `END` 是内置的入口与出口。
**compile**：把构建期对象变成可执行对象，之后才能 `invoke`。
**返回值**：`invoke` 返回最终状态，是普通 `dict`。""",
                "plain": """这一节像先装配一台最简单的机器：两个齿轮、一根传动轴，通电转起来。
齿轮就是节点，传动轴就是边，机器里流动的油就是状态。
先确认机器能转，第 5 章之后再逐个零件讲清楚。""",
                "syntax": """**本节用到的最小 API**

```python
from typing import TypedDict
from langgraph.graph import END, START, StateGraph

class State(TypedDict):
    question: str
    answer: str

builder = StateGraph(State)          # 1. 声明状态类型
builder.add_node("draft", draft)     # 2. 注册节点
builder.add_edge(START, "draft")     # 3. 连边
builder.add_edge("draft", END)
graph = builder.compile()            # 4. 编译
graph.invoke({...})                  # 5. 运行
```

- `START` / `END` 是保留名，不能用作自己的节点名。
- `invoke` 的入参必须覆盖 State 的必填字段。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    question: str
    answer: str
    reviewed: bool


def draft(state: State) -> dict:
    return {"answer": f"关于「{state['question']}」，先说结论：状态是共享的数据。"}


def review(state: State) -> dict:
    return {"answer": state["answer"] + "（已校对）", "reviewed": True}


builder = StateGraph(State)
builder.add_node("draft", draft)
builder.add_node("review", review)
builder.add_edge(START, "draft")
builder.add_edge("draft", "review")
builder.add_edge("review", END)

graph = builder.compile()

result = graph.invoke({"question": "State 是什么", "answer": "", "reviewed": False})
print("返回值：", result)
print("类型：", type(result).__name__)
print()
print(graph.get_graph().draw_mermaid())''',
                "code_lines": """1. `State` 用 `TypedDict` 声明三个字段，后续所有节点共享这一份结构。
2. `draft` 只返回 `answer`，`reviewed` 不动——节点返回的是增量，不是整份状态。
3. `review` 读取 `state["answer"]`，说明节点能拿到上游写入的值。
4. `add_edge(START, "draft")` 指定入口；没有这条边，图不知道从哪开始。
5. `add_edge("review", END)` 指定出口；没有这条边，图跑完 `review` 后不知道停。
6. `compile()` 返回可执行对象，未编译的 builder 不能 `invoke`。
7. `draw_mermaid()` 输出文本图，可以直接贴进支持 Mermaid 的编辑器查看结构。""",
                "output": """# 程序输出
返回值： {'question': 'State 是什么', 'answer': '关于「State 是什么」，先说结论：状态是共享的数据。（已校对）', 'reviewed': True}
类型： dict

---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	draft(draft)
	review(review)
	__end__([<p>__end__</p>]):::last
	__start__ --> draft;
	draft --> review;
	review --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc""",
                "mistakes": """- 忘了 `add_edge(START, ...)`，编译时就报「没有入口」。
- 忘了连到 `END`，运行后不知道停在哪。
- 节点里修改 `state` 再返回整个 `state`，造成意外的全量覆盖。
- 用 `"start"` 小写当节点名，和内置 `START` 混淆。
- 直接 `builder.invoke()`，忘了先 `compile()`。""",
                "error_analysis": """`ValueError: Graph must have an entrypoint`
—— 没连 `START`。加 `add_edge(START, 第一个节点)`。

`InvalidUpdateError`
—— 节点返回了 State 里不存在的键，或同一步多个节点写同一个键。先核对字段名。

`TypeError: 'StateGraph' object is not callable`
—— 在 builder 上调用了 `invoke`。先 `compile()` 得到 graph。""",
                "beginner_practice": """1. 在 `draft` 与 `review` 之间插入一个 `check` 节点，观察 Mermaid 图的变化。
2. 把 `invoke` 的入参只留 `{"question": "..."}`，看会发生什么。""",
                "advanced_practice": """把 `review` 改成「当 `answer` 超过 20 字才校对」，说明此时需要引入什么机制才能按条件跳过节点，
并指出这属于哪一章的内容（先不实现）。""",
                "quiz_note": "本节 6 道题：2 道基础理解（三要素对应、compile 的作用）+ 2 道代码阅读（读返回值、读 Mermaid）+ 2 道应用练习（加入口、排查编译错误）。",
                "summary": """最小图 = State 定义 + 两个节点 + 三条边 + compile。
节点只返回增量，状态由执行器合并。
这一节只解决「跑起来」，细节下一章开始逐个拆。""",
                "next_lesson": "下一章拆第一个零件：图到底是什么，节点和边各自负责什么。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-04-02",
                        "name": "最小可运行图",
                        "goal": "能独立写出并运行一个两节点直连的图，读懂返回值。",
                        "minutes": 35,
                        "criteria": "能写出 State/Node/Edge/compile/invoke 五步，并解释 START 与 END 的作用。",
                        "requires": ["langgraph-agent-04-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-04-02-1",
                        "kp": 0,
                        "title": "补一个中间节点",
                        "description": "在 `draft` 和 `review` 之间加 `check` 节点，让它返回 answer 字段并追加「（已查重）」，然后修改相应的边。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def check(state: State) -> dict:
    return {"answer": state["answer"] + "（已查重）"}


builder.add_node("check", check)
builder.add_edge(START, "draft")
builder.add_edge("draft", "check")
builder.add_edge("check", "review")
builder.add_edge("review", END)''',
                        "explanation": "插入节点要改两条边：原来 `draft → review` 变成 `draft → check → review`。只加节点不改边，新节点不会被执行。",
                    },
                    {
                        "code": "lg-ex-04-02-2",
                        "kp": 0,
                        "title": "为什么必须先 compile",
                        "description": "不调用 `compile()` 直接 `builder.invoke()` 会怎样？为什么框架要分成两步？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''`builder.invoke()` 会报 `AttributeError`——`StateGraph` 是构建器，没有 `invoke`。

分成两步的原因：① 构建期要反复改，每次改都重新校验代价高；② `compile` 时可以做一次性校验
（入口是否存在、节点是否都可达、状态 schema 是否合法），把错误提前到编译期；③ 编译产物可以
携带 checkpointer 等运行期配置，同一个图结构能编出不同运行形态。''',
                        "explanation": "「构建」与「执行」分离是这类框架的通用设计，理解了就能明白为什么很多错误在编译时就报。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-04-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`invoke` 返回的值是什么类型？",
                        "options": [
                            ("A", "StateGraph 对象"),
                            ("B", "最终状态的 dict"),
                            ("C", "最后一个节点的返回值"),
                            ("D", "生成器"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "返回的是合并后的完整状态（`TypedDict` 在运行期就是普通 dict），不是单个节点的增量。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-04-02-2",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`compile()` 的主要作用是？",
                        "options": [
                            ("A", "把 Python 编译成字节码"),
                            ("B", "校验图结构并生成可执行对象"),
                            ("C", "执行图"),
                            ("D", "生成文档"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "编译期做结构校验（入口、可达性等），产物才是能 `invoke` 的对象。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-04-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "最终返回的 `answer` 里有「（已校对）」吗？为什么？",
                        "options": [
                            ("A", "有，`review` 写入了这个字段"),
                            ("B", "没有，因为 `draft` 没有返回该字段"),
                            ("C", "没有，因为字段名写错了"),
                            ("D", "有，但类型是 list"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`review` 返回 `{\"answer\": state[\"answer\"] + \"（已校对）\"}`，覆盖了上游写入的值，最终状态里自然带着它。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-04-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "Mermaid 图里 `draft --> review` 表示？",
                        "options": [
                            ("A", "review 依赖 draft 的数据"),
                            ("B", "draft 执行完后必定执行 review"),
                            ("C", "两者可以并行"),
                            ("D", "review 是 draft 的子图"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "实线箭头是普通边，表示固定的先后关系；虚线才是条件边（第 13 章）。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-04-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么这一节只写两节点直连，不直接写一个能调工具的 Agent？",
                        "options": [],
                        "answer": {"value": """因为此时还没讲 State 的类型约束、节点的返回值规则、边的走向含义。直接写 Agent 会把「工具调用协议」「条件路由」「循环终止」三块未知同时压上来，任何一处出错都难以判断是哪块知识缺了。

两节点直连是最小可验证单元：它只包含「状态 → 节点 → 状态 → 节点 → 结束」这一条主线，跑通即证明环境、导入、编译、运行四件事都对。后面每加一个机制（分支、循环、工具、持久化），都是在这条主线上加一个变量，出问题能立刻定位。"""},
                        "explanation": "这是教学顺序的取舍：先建立一条稳定的基线，再逐项加压。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-04-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个只有入口、没有出口的两节点图（省略 `add_edge(\"review\", END)`），预测运行结果并说明原因。",
                        "options": [],
                        "answer": {"value": "把最后一行的 add_edge(\"review\", END) 删掉后：\nbuilder.add_edge(START, \"draft\")\nbuilder.add_edge(\"draft\", \"review\")\n\n运行仍然会返回正确结果，因为 review 之后没有任何出边，执行器视为流程结束。\n但 Mermaid 图里 review 不再连到 __end__，结构上「没有显式出口」，\n复杂图里容易出现「以为结束了其实还有分支没接」的隐患。\n\n工程建议：显式连 END，让结构自解释。"},
                        "explanation": "能跑通和结构清晰是两件事。显式连 END 是让人（和后续维护者）一眼看出流程边界。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
