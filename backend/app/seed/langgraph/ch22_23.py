"""LangGraph Agent 开发：第 22—23 章。

第 22 章让流程「停下来等人」：`interrupt` 挂起、`Command(resume=...)` 恢复，并把它用成审批流；
第 23 章把一段流程打包成子图：当节点用、看清边界、必要时手动做父子状态映射。

版本口径（实测）：langgraph 1.2.20、langgraph-checkpoint 4.3.1。
"""

CHAPTERS = [
    # ---------------------------------------------------------------- 第 22 章
    {
        "code": "langgraph-agent-22",
        "order_index": 22,
        "title": "Interrupt",
        "description": "在图中间停下来，等一个真实的人回答，再接着跑。",
        "lessons": [
            {
                "code": "langgraph-agent-22-lesson-01",
                "title": "中断与恢复",
                "objectives": """1. 能在节点里用 `interrupt(payload)` 挂起流程，并读懂返回的 `__interrupt__`；
2. 能用 `Command(resume=...)` 把人的回答送回去，让节点从原位继续；
3. 能说出挂起时 `next` 指向哪、为什么 `answer` 还是空的；
4. 能解释为什么「传 `None` 继续」不会恢复，以及没装检查点时中断为什么无法恢复。""",
                "why_learn": """有些步骤机器不该自己决定：退款、发邮件、删数据。你需要一个能真正暂停、等人回话、再继续的机制。
中断是「人机协作」的开关，也是第 26 章对外接口里「审核中」状态的来源。""",
                "concepts": """**`interrupt(value)`**：在节点里调用它，流程立刻挂起，`value` 会原样送到调用方。
**`__interrupt__`**：`invoke` 返回值里多出的键，装着挂起信息（`value`、`id`）。
**恢复**：用 `graph.invoke(Command(resume=回答), cfg)`；`interrupt(...)` 的返回值就是那个回答。
**节点会重跑**：恢复时整个节点函数从头执行，`interrupt` 之前写过的副作用会再来一次。
**`next` 指向挂起的节点**：挂起不是结束，所以 `next` 不为空。
**必须装检查点**：没有检查点，挂起后状态没地儿存，流程永远停在那儿。""",
                "plain": """中断不是「暂停一个正在跑的线程」，而是「在检查点处收工，等人回来再从这个点重启」。

这个区别很重要。恢复的时候，整个节点函数会从头再执行一遍，代码跑到 `interrupt(...)` 那一行时，
框架发现「有人已经回答了」，就把答案当作返回值继续往下走。

所以你写在 `interrupt` 之前的副作用（发消息、写库）在恢复时会执行第二次。
正确写法是把副作用放在 `interrupt` 之后，或者用「先查再做」的方式保证幂等。

还有一个新手常犯的错：想恢复时传 `None` 进去。传 `None` 只是「再跑一次」，
流程重新走到 `interrupt` 会再次挂起——看起来像「恢复没生效」，其实是没用对入口。""",
                "syntax": """**最小组装**

```python
from langgraph.types import Command, interrupt

def ask_human(state: State) -> dict:
    decision = interrupt({"question": "是否同意执行？", "draft": state["draft"]})
    return {"answer": f"人工结论：{decision}"}

graph = builder.compile(checkpointer=InMemorySaver())   # 必须有

out = graph.invoke({...}, cfg)          # 挂起，out["__interrupt__"] 有值
out2 = graph.invoke(Command(resume="同意"), cfg)        # 恢复
```

- `interrupt` 可以返回任意可序列化的值（字符串、字典、布尔）。复杂结构建议用字典。
- 挂起后 `graph.get_state(cfg).next` 指向那个节点，说明「还没跑完」。
- `invoke(None, cfg)` 不会恢复（会再次挂起）；恢复只有 `Command(resume=...)` 这一条路。
- 恢复后 `__interrupt__` 键消失，返回值就是正常的状态。""",
                "example_code": '''from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class State(TypedDict):
    question: str
    draft: str
    answer: str


def draft(state: State) -> dict:
    return {"draft": "退款 199 元已提交"}


def ask_human(state: State) -> dict:
    """跑到这里会停下来，等一个真实的人回答。"""
    decision = interrupt({"question": "是否同意执行？", "draft": state["draft"]})
    print("  用户回复:", decision)
    return {"answer": f"人工结论：{decision}"}


builder = StateGraph(State)
builder.add_node("draft", draft)
builder.add_node("ask_human", ask_human)
builder.add_edge(START, "draft")
builder.add_edge("draft", "ask_human")
builder.add_edge("ask_human", END)
graph = builder.compile(checkpointer=InMemorySaver())

cfg = {"configurable": {"thread_id": "t1"}}
out = graph.invoke({"question": "我要退款", "draft": "", "answer": ""}, cfg)

print("=== 第一次 invoke：挂起 ===")
print("返回的键:", list(out.keys()))
pending = out["__interrupt__"][0]
print("挂在哪个值上:", pending.value)
print("next（下一步执行谁）:", graph.get_state(cfg).next)
print("answer 还是空的:", repr(out["answer"]))

print()
print("=== 用 Command(resume=...) 恢复 ===")
out2 = graph.invoke(Command(resume="同意"), cfg)
print("返回的键:", list(out2.keys()))
print("answer:", out2["answer"])
print("恢复后 next:", graph.get_state(cfg).next)

print()
print("=== 传 None 不会恢复 ===")
cfg2 = {"configurable": {"thread_id": "t2"}}
graph.invoke({"question": "再退一次", "draft": "", "answer": ""}, cfg2)
again = graph.invoke(None, cfg2)
print("又挂起了:", again.get("__interrupt__") is not None, "| answer:", repr(again["answer"]))''',
                "code_lines": """1. `ask_human` 只做一件事：把「要审批什么」打包递给外面，然后等一个回答。
2. `interrupt({...})` 的参数会原样出现在 `__interrupt__[0].value` 里，所以里面要放人看得懂的信息。
3. 挂起时 `invoke` 仍然正常返回，只是多一个 `__interrupt__` 键——它不是异常。
4. `next` 是 `('ask_human',)`：节点还没跑完，所以这条线不是「结束」而是「暂停」。
5. `answer` 还是空字符串，因为 `return` 那一行根本没执行——中断发生在 `return` 之前。
6. 恢复用 `Command(resume="同意")`，这个值成为 `interrupt(...)` 的返回值，节点继续往下走到 `return`。
7. 恢复后返回的键里没有 `__interrupt__`，说明流程真的走完了。
8. 最后一段：`invoke(None, cfg)` 让流程从头再跑，于是又挂在同一个位置——`None` 不是「恢复」的意思。""",
                "output": """# 程序输出
=== 第一次 invoke：挂起 ===
返回的键: ['question', 'draft', 'answer', '__interrupt__']
挂在哪个值上: {'question': '是否同意执行？', 'draft': '退款 199 元已提交'}
next（下一步执行谁）: ('ask_human',)
answer 还是空的: ''

=== 用 Command(resume=...) 恢复 ===
  用户回复: 同意
返回的键: ['question', 'draft', 'answer']
answer: 人工结论：同意
恢复后 next: ()

=== 传 None 不会恢复 ===
又挂起了: True | answer: ''""",
                "mistakes": """- 想恢复时传 `None` 或传用户输入：只有 `Command(resume=...)` 能恢复。
- 没装 checkpointer 就调 `interrupt`：能挂起，但永远恢复不了，线程就废在那儿。
- 把副作用写在 `interrupt` 之前：恢复时节点重跑，副作用执行两次（比如发了两条通知）。
- `interrupt` 的 `value` 传了一个巨大的对象：它会存进检查点，白白撑大存储。
- 挂起后忘记把 `__interrupt__` 透给前端：用户界面上什么都看不到，只有一个「卡住」的请求。
- 同一个线程并发多次 `invoke` 等不同的中断：状态会互相覆盖，要按线程串行处理。""",
                "error_analysis": """挂起后怎么都恢复不了
—— 十有八九是没装 checkpointer，或者恢复时用了另一个 `thread_id`。

`answer` 一直是空
—— 流程还停在 `interrupt` 那一行。看 `next` 是否为空，就能判断「跑完了」还是「挂起了」。

恢复后副作用重复执行
—— 节点是从头重跑的。把副作用挪到 `interrupt` 之后，或做幂等处理。

`TypeError: Command() missing ...`
—— `Command` 的参数名是 `resume`，不是 `value` 或 `input`。

恢复时报线程不存在
—— `thread_id` 拼错了，或检查点是内存版而进程已重启。""",
                "beginner_practice": """1. 把 `Command(resume="同意")` 改成 `Command(resume={"approved": True})`，观察 `answer` 的内容。
2. 在 `draft` 里加一句 `print`，然后恢复一次，确认它有没有被执行两次。""",
                "advanced_practice": """设计一个「两次确认」的流程：第一次确认金额、第二次确认收款方，两次都通过才执行。
说明状态该怎么记、拒绝时怎么退出，以及用户中途离开（不恢复）时线程该怎么清理。""",
                "quiz_note": "本节 6 道题：2 道基础理解（恢复用什么入口、挂起后 `next` 的含义）+ 2 道代码阅读（为什么 `answer` 是空、传 `None` 为什么又挂起）+ 2 道应用练习（写中断节点、设计两次确认）。",
                "summary": """`interrupt` 在检查点处收工，`Command(resume=...)` 从那里重启。
恢复时节点从头重跑，副作用要放在中断之后或做幂等。
挂起不是结束：`next` 不为空，`__interrupt__` 有值，`answer` 还是空的。""",
                "next_lesson": "知道了怎么停、怎么续，下一节把它用成一个真正的审批流：通过就执行，拒绝就走另一条路。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-22-01",
                        "name": "中断与恢复",
                        "goal": "能用 `interrupt` 挂起流程并用 `Command` 恢复，且不重复副作用。",
                        "minutes": 45,
                        "criteria": "能解释恢复时节点重跑的后果，并说明为什么必须装检查点。",
                        "requires": ["langgraph-agent-21-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-22-01-1",
                        "kp": 0,
                        "title": "把副作用挪对位置",
                        "description": "下面这段代码在恢复时会发两条通知，改成只发一条。\n\n```python\ndef review(state):\n    notify(\"已提交审批\")\n    decision = interrupt({\"action\": state[\"action\"]})\n    return {\"decision\": decision}\n```",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def review(state: State) -> dict:
    decision = interrupt({"action": state["action"]})
    notify(f"审批完成：{decision}")      # 放在 interrupt 之后
    return {"decision": decision}''',
                        "explanation": "`interrupt` 之前的代码在恢复时会再执行一次。要么把副作用挪到之后，要么用「先查已发送记录再发」的幂等写法。",
                    },
                    {
                        "code": "lg-ex-22-01-2",
                        "kp": 0,
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "title": "为什么必须装检查点",
                        "description": "中断功能为什么离不开 checkpointer？",
                        "answer": """因为「挂起」的本质是「把当前状态存下来，然后结束这次调用」。

`interrupt` 一执行，进程里就没有正在等待的东西了：这次 `invoke` 直接返回，函数栈已经销毁。
下次用户回来，系统必须从某个地方恢复出「跑到哪了、状态是什么、下一步该执行谁」——
这三样东西只存在于检查点里。

没有检查点会发生什么？示例验证过：`interrupt` 仍然能挂起、`__interrupt__` 仍然返回，
但状态没被存下来，你再也找不到这条线，也就无法恢复。表现是「流程卡死了」。

所以中断与检查点是一对：检查点负责「存得住」，中断负责「停得下」。
这也是为什么第 20 章要放在第 22 章前面。""",
                        "explanation": "理解「挂起 = 结束这次调用 + 存档」，才能理解为什么恢复要靠 `thread_id` 找回存档。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-22-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "恢复一个挂起的流程，正确的方式是？",
                        "options": [
                            ("A", "`graph.invoke(None, cfg)`"),
                            ("B", "`graph.invoke(Command(resume=回答), cfg)`"),
                            ("C", "`graph.invoke({\"answer\": 回答}, cfg)`"),
                            ("D", "重新 `compile` 一次"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "只有 `Command(resume=...)` 会被当成「对中断的回答」。传 `None` 会再跑一次并再次挂起，示例第 3 段就是证据。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-22-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "挂起时 `get_state(cfg).next` 为空元组，表示流程已经跑完。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "挂起时 `next` 指向那个还没跑完的节点（示例里是 `('ask_human',)`）。`next` 为空才是跑完。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-22-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "第一次 `invoke` 返回后，为什么 `answer` 还是空字符串？",
                        "options": [
                            ("A", "因为 `answer` 字段没在 State 里声明"),
                            ("B", "因为 `interrupt` 在 `return` 之前就挂起了，那一行没执行"),
                            ("C", "因为 `ask_human` 没有返回值"),
                            ("D", "因为检查点把 `answer` 清空了"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "中断发生在函数中间，`return` 语句根本没走到。恢复后节点重跑，才会写 `answer`。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-22-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "最后一段 `invoke(None, cfg2)` 的结果说明什么？",
                        "options": [
                            ("A", "`None` 表示「没有新输入」，流程重跑并再次挂起"),
                            ("B", "`None` 表示「取消中断」"),
                            ("C", "`None` 会被当成空字符串的回答"),
                            ("D", "`None` 会清空该线程的历史"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`None` 只是「不提供输入、接着已有状态跑」，而 `interrupt` 仍然没有答案，于是又挂一次。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-22-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "恢复时节点会从头重跑，这对代码写法有什么要求？",
                        "options": [],
                        "answer": """两条要求。

① 副作用后置：发通知、写库、扣款这类动作放在 `interrupt` 之后，避免「恢复一次做两次」。

② 无法后置的必须幂等：比如「提交审批单」必须在挂起前做（否则人看不到待审内容），那就用唯一键去重，
先查「这张单是否已提交」，再决定要不要提交。

判断方法：把节点函数想象成「可能被执行 N 次」。凡是执行两次会出问题的语句，都要处理。

这条纪律不只适用于中断：任何带重试、带恢复的流程，节点都必须是「可重复执行」的。
第一次写的时候觉得麻烦，上线出过一次重复扣款就懂了。""",
                        "explanation": "「节点可能重跑」是图编排的基本假设，中断只是让它显性化。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-22-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个审批节点：挂起时告诉外面「要审批哪个动作」，恢复后把结论写进 `decision`。",
                        "options": [],
                        "answer": {
                            "value": "def review(state: State) -> dict:\n    decision = interrupt(\n        {\"action\": state[\"action\"], \"options\": [\"approve\", \"reject\"]}\n    )\n    return {\"decision\": decision}"
                        },
                        "explanation": "`interrupt` 的返回值就是恢复时传进来的东西，可以直接当结论用；把可选项一起递出去，前端才好渲染按钮。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-22-lesson-02",
                "title": "审批流设计",
                "objectives": """1. 能把高风险动作放在人工确认之后，形成「提议 → 审批 → 执行 / 取消」；
2. 能用条件边根据审批结论走不同支路，并把拒绝原因带回给用户；
3. 能设计中断时递出去的载荷（人需要看到什么才能做决定）；
4. 能说明审批流里哪些信息必须落库、哪些可以留在状态里。""",
                "why_learn": """真实业务里，「Agent 直接执行」几乎不可接受：退款、改权限、发对外邮件都要有人点头。
审批流不是加一个 `if`，而是把「决策权」和「执行权」分开，并且两条路都要走通。""",
                "concepts": """**三段式**：`propose`（算出要做什么）→ `review`（挂起等人）→ 分支执行。
**条件边**：审批结论决定走 `execute` 还是 `cancel`，不要在一个节点里用 `if` 混着写。
**载荷设计**：递出去的信息要够人做判断——动作内容、影响范围、可选项。
**结构化结论**：`resume` 传字典（`{"approved": bool, "reason": str}`），比传「同意」两个字好处理。
**拒绝路径**：也要有明确产出（原因、后续建议），不能只是「什么都不做」。
**审计**：谁审的、什么时候、结论是什么，必须落库；状态只存「这条流程的当前结论」。""",
                "plain": """审批流的关键不是「停下来」，而是「停下来之后两条路都能走通」。

只做「通过就执行」的流程是不完整的：用户点了拒绝，系统要么报错，要么默默结束，
两种都很难看。正确做法是把拒绝也当成一种正常结果，给出原因和下一步建议。

第二个关键是「递出去什么」。人要做判断，得看到具体动作、影响范围和可选项。
只递一句「是否同意」等于让人盲签。

第三个关键是「结论的结构」。传一句「同意」当然能跑，但后面想统计通过率、
想区分「同意但要求改金额」就没法做了。用字典，把决定和理由分开。""",
                "syntax": """**三段式骨架**

```python
def review(state: State) -> dict:
    decision = interrupt({"action": state["action"], "options": ["approve", "reject"]})
    return {"decision": decision}


def route(state: State) -> str:
    return "execute" if state["decision"].get("approved") else "cancel"


builder.add_conditional_edges("review", route, {"execute": "execute", "cancel": "cancel"})
```

**恢复时传结构化结论**

```python
graph.invoke(Command(resume={"approved": True}), cfg)
graph.invoke(Command(resume={"approved": False, "reason": "金额需主管复核"}), cfg)
```

- 结论用字典：`approved` 决定分支，`reason` 用于给用户解释。
- 审批节点只负责「拿到结论」，不要在里面写执行逻辑。
- 取消路径也要写状态（`result`），否则前端拿不到任何反馈。""",
                "example_code": '''from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class State(TypedDict):
    action: str
    decision: dict
    result: str


def propose(state: State) -> dict:
    return {"action": "退款 199 元"}


def review(state: State) -> dict:
    """高风险动作之前停下，等人给结论。"""
    decision = interrupt({"action": state["action"], "options": ["approve", "reject"]})
    print("  人工决定:", decision)
    return {"decision": decision}


def execute(state: State) -> dict:
    return {"result": f"已执行：{state['action']}"}


def cancel(state: State) -> dict:
    return {"result": f"已取消（原因：{state['decision'].get('reason', '未说明')}）"}


def route(state: State) -> str:
    return "execute" if state["decision"].get("approved") else "cancel"


builder = StateGraph(State)
builder.add_node("propose", propose)
builder.add_node("review", review)
builder.add_node("execute", execute)
builder.add_node("cancel", cancel)
builder.add_edge(START, "propose")
builder.add_edge("propose", "review")
builder.add_conditional_edges("review", route, {"execute": "execute", "cancel": "cancel"})
builder.add_edge("execute", END)
builder.add_edge("cancel", END)
graph = builder.compile(checkpointer=InMemorySaver())


def run(thread: str, reply: dict) -> str:
    cfg = {"configurable": {"thread_id": thread}}
    out = graph.invoke({"action": "", "decision": {}, "result": ""}, cfg)
    print(f"  [{thread}] 挂起，待审动作:", out["__interrupt__"][0].value["action"])
    out2 = graph.invoke(Command(resume=reply), cfg)
    return out2["result"]


print("=== 同意 ===")
print("  结果:", run("t-approve", {"approved": True}))

print()
print("=== 拒绝 ===")
print("  结果:", run("t-reject", {"approved": False, "reason": "金额需主管复核"}))''',
                "code_lines": """1. `propose` 只算出「要做什么」，不执行——执行权在后面两个分支里。
2. `review` 把动作和可选项一起递出去，人才能做判断；它自己不判断，只负责收集结论。
3. `route` 是纯函数：读结论，返回分支名。判断逻辑集中在一处，好测。
4. `execute` 是真正的副作用节点：只有在人批准之后才会被走到。
5. `cancel` 也要产出 `result`，并且把拒绝原因带进去——拒绝不是「什么都不做」。
6. `run` 封装了「发起 + 挂起 + 恢复」三步，让两条路径的对比更直观。
7. 同意与拒绝用不同的 `thread_id`，互不干扰；这也是真实系统里「每次审批一条线程」的做法。
8. 两次运行打印的「待审动作」一样，说明挂起时递出去的载荷是稳定的，与后面的结论无关。""",
                "output": """# 程序输出
=== 同意 ===
  [t-approve] 挂起，待审动作: 退款 199 元
  人工决定: {'approved': True}
  结果: 已执行：退款 199 元

=== 拒绝 ===
  [t-reject] 挂起，待审动作: 退款 199 元
  人工决定: {'approved': False, 'reason': '金额需主管复核'}
  结果: 已取消（原因：金额需主管复核）""",
                "mistakes": """- 只实现「通过」路径，拒绝时抛异常或静默结束——用户看不到任何反馈。
- 在 `review` 节点里直接写执行逻辑：一恢复就绕过了审批，形同虚设。
- `resume` 传「同意」字符串，后面想区分「同意但改金额」就没办法了。
- 载荷只递一句「是否同意」，审批人看不到要批什么、影响多大。
- 审批结论只放在状态里，不落库：换个检查点后端或清理历史后，审计证据就没了。
- 拒绝对话里直接结束线程，却不告诉用户「可以改小金额再试」。
- 多个审批共用一个 `thread_id`：两次审批的状态互相覆盖。""",
                "error_analysis": """恢复后直接执行了，没等审批
—— 执行逻辑写在了 `review` 里，或者在 `interrupt` 之前就调用了。

拒绝后返回 500
—— `cancel` 分支没写返回值，或 `decision` 是空字典导致 `.get` 拿到默认值后又拼错字段。

`KeyError: 'decision'`
—— `route` 读的键没在 State 里声明，写入时被静默丢弃（第 12 章）。

审批界面拿不到待审内容
—— `interrupt` 的载荷没透给前端。要把 `__interrupt__[0].value` 整个返回给界面。""",
                "beginner_practice": """1. 给 `propose` 加一个「金额」字段，并在载荷里带上它，让审批人能看到金额。
2. 把 `cancel` 的返回值改成同时写 `result` 与 `decision`，观察最终状态。""",
                "advanced_practice": """设计一个「两级审批」：金额小于 500 只需一级，大于 500 需要两级。
说明你会用两个中断节点、还是一个节点里两次 `interrupt`，以及两种做法的取舍。""",
                "quiz_note": "本节 6 道题：2 道基础理解（审批流的三段、结论为什么用字典）+ 2 道代码阅读（`route` 怎么决定的、为什么拒绝也要写 `result`）+ 2 道应用练习（设计载荷、两级审批）。",
                "summary": """三段式：提议 → 审批（中断）→ 分支执行。
结论用结构化字典，拒绝路径也要有明确产出。
执行权放在审批之后，审计信息落库而不是只留在状态里。""",
                "next_lesson": "流程越来越长，一张图会画不下。下一章用子图把一段流程打包起来复用。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-22-02",
                        "name": "审批流设计",
                        "goal": "能设计通过 / 拒绝都完整的审批流程。",
                        "minutes": 40,
                        "criteria": "能说明执行权为什么必须在审批之后，并写出两条分支。",
                        "requires": ["langgraph-agent-22-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-22-02-1",
                        "kp": 0,
                        "title": "补一条拒绝路径",
                        "description": "现有代码在拒绝时直接 `END`，什么也不写。补一个 `cancel` 节点，让用户知道为什么没执行、下一步能做什么。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def cancel(state: State) -> dict:
    reason = state["decision"].get("reason", "未说明")
    return {
        "result": f"未执行：{state['action']}（原因：{reason}）。可修改金额后重新提交。",
        "decision": {**state["decision"], "handled": True},
    }


builder.add_edge("cancel", END)''',
                        "explanation": "拒绝路径要给出「为什么」和「然后呢」。只写「未执行」，用户只会再问一遍。",
                    },
                    {
                        "code": "lg-ex-22-02-2",
                        "kp": 0,
                        "title": "载荷该递什么",
                        "description": "审批中断时，`interrupt` 的载荷应该包含哪些字段？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """四个字段够用，多一个都是负担。

① `action`：具体要做什么，用人话写。「退款 199 元给订单 20241108-01」比「执行退款」有用得多。

② `impact`：影响范围与不可逆性。「将扣减账户余额，不可撤销」——这是审批人最需要的判断依据。

③ `options`：可选项。只给「同意 / 拒绝」时前端只能渲染两个按钮；给 `["approve", "reject", "modify"]`
就能多一条改参数的路。

④ `ref`：关联标识（订单号、用户 id）。用于审批人自己去查更多信息，也用于审计。

不要放进去的：整段对话历史（太大，且与决策无关）、内部 trace id（对审批人无意义）、
模型原始输出（可能含幻觉，会干扰判断）。

一句话标准：审批人只看这个载荷，能不能做出负责的决定。能，就够了。""",
                        "explanation": "载荷设计的目标是「支持决策」，不是「把上下文全倒出去」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-22-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "审批流里，真正的副作用（退款、发信）应该放在哪？",
                        "options": [
                            ("A", "`propose` 里，先做再问"),
                            ("B", "审批节点 `review` 里，边问边做"),
                            ("C", "审批通过之后的分支节点里"),
                            ("D", "任意位置，只要最后记录一下"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "决策权与执行权必须分开。放在审批之前，等于「先斩后奏」，审批就成了摆设。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-22-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`resume` 传字符串「同意」和传 `{\"approved\": True}` 在功能上完全等价。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "只判断「通过与否」时看似等价，但结构化结论能携带原因、修改项、审批人等信息，后续统计与二次处理都靠它。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-22-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`route` 函数为什么写成 `state[\"decision\"].get(\"approved\")`，而不是 `state[\"decision\"][\"approved\"]`？",
                        "options": [
                            ("A", "因为 `approved` 一定存在，用 `.get` 更快"),
                            ("B", "因为结论可能缺字段（比如只传了 `reason`），`.get` 返回 `None` 会走 `cancel` 分支，比抛 `KeyError` 稳"),
                            ("C", "因为 `decision` 是字符串"),
                            ("D", "因为状态里不能存布尔值"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "外部输入不可信，缺字段是常态。`.get` 让「没明确批准」自动落到安全的一侧——拒绝。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-22-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "为什么 `cancel` 节点也要返回 `result`？",
                        "options": [
                            ("A", "因为 `result` 是必填字段"),
                            ("B", "因为拒绝也是一种正常结果，前端和用户都需要看到明确反馈"),
                            ("C", "因为不写会报错"),
                            ("D", "因为 `END` 之前必须写状态"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "拒绝路径不写状态，接口返回的就是空结果，用户不知道发生了什么。两条路都要有产出。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-22-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "审批中断时，`interrupt` 的载荷应该包含哪些信息？",
                        "options": [],
                        "answer": """目标是「只看这个载荷就能做出负责的决定」。四个字段够用：

`action`：具体做什么，带关键参数（退款 199 元给哪张订单）。
`impact`：影响范围与是否可逆（扣余额、不可撤销）。
`options`：可选项，至少 approve / reject，必要时加 modify。
`ref`：关联标识，供查证与审计。

不该放的：整段对话历史、内部 trace id、模型原始输出（会干扰判断，也撑大存储）。

判断标准：审批人看完这个载荷，能不能签字。能，就够了。""",
                        "explanation": "载荷是给「人」的界面，不是给机器的日志。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-22-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个 `route` 函数与条件边配置：批准走 `execute`，否则走 `cancel`。",
                        "options": [],
                        "answer": {
                            "value": "def route(state: State) -> str:\n    return \"execute\" if state[\"decision\"].get(\"approved\") else \"cancel\"\n\n\nbuilder.add_conditional_edges(\n    \"review\",\n    route,\n    {\"execute\": \"execute\", \"cancel\": \"cancel\"},\n)\nbuilder.add_edge(\"execute\", END)\nbuilder.add_edge(\"cancel\", END)"
                        },
                        "explanation": "映射表把两个分支都显式列出，读代码的人一眼看到「一共两条路」。兜底落在 `cancel` 上，是安全侧。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ---------------------------------------------------------------- 第 23 章
    {
        "code": "langgraph-agent-23",
        "order_index": 23,
        "title": "Subgraph",
        "description": "把一段流程打包成子图，父图只关心它的输入输出。",
        "lessons": [
            {
                "code": "langgraph-agent-23-lesson-01",
                "title": "子图定义与调用",
                "objectives": """1. 能把编译好的子图直接当节点加进父图；
2. 能说明子图边界：父图只看到「一个节点」，看不到内部节点；
3. 能用 `draw_mermaid(xray=True)` 展开子图内部；
4. 能判断什么时候该拆子图，而不是继续往一张图里加节点。""",
                "why_learn": """一张图上十几个节点时，读图的人已经看不清主干。子图让你把「一段流程」当成一个积木，
父图保持可读，子图还能单独测试、单独复用。""",
                "concepts": """**子图**：一个编译好的图，可以直接作为节点加进另一个图。
**边界**：父图视角里它就是一个节点，共享同一份 State（父子 schema 兼容时）。
**`xray=True`**：导出结构时展开子图内部，节点名带前缀（`pre:clean`）。
**复用**：同一张子图可以被多个父图使用，也可以在一个父图里出现多次。
**拆分时机**：步骤超过 6—8 个、某段流程要被复用、某段需要独立测试或独立权限。
**检查点**：子图可以用父图的检查点，也可以自带——本节先用最简单的共享方式。""",
                "plain": """子图不是「另一个程序」，它就是一张图，只是被当成一个节点塞进更大的图里。

这意味着两件事：父图看到它时，只看到一个节点、一份输入、一份输出；
而它内部可以有任意多个节点、分支、循环，父图不用管。

好处是可读性与可测性：父图只画主干（预处理 → 主流程 → 后处理），
预处理内部有几句话、怎么分支，去子图里看。要改预处理，也只动那一张图。

代价是「看不见」。父图导出的结构里只有 `pre` 一个框，出问题时你得知道去看子图。
`xray=True` 就是干这个的：把子图摊开，节点名会带上 `pre:` 前缀。

判断要不要拆：一张图超过七八个节点、或者某段流程第二次被用到，就该拆了。""",
                "syntax": """**两种接法**

```python
sub_graph = sub_builder.compile()

# 1) 直接用（父子 schema 兼容）
builder.add_node("pre", sub_graph)

# 2) 手动包装（schema 不同，见下一节）
def call_sub(state):
    out = sub_graph.invoke({"raw": state["question"], "result": ""})
    return {"answer": out["result"]}

builder.add_node("call_sub", call_sub)
```

- 直接接要求父子状态「有共享键」，否则子图收到的是空字典。
- 编译好的子图才能当节点；未编译的 `StateGraph` 不行。
- `get_graph(xray=True)` 展开内部结构，节点名形如 `pre:clean`。
- 子图内部的 `START/END` 是它自己的边界，与父图无关。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    text: str
    summary: str
    final: str


def clean(state: State) -> dict:
    return {"text": state["text"].strip()}


def shorten(state: State) -> dict:
    return {"summary": state["text"][:10] + "…"}


sub = StateGraph(State)
sub.add_node("clean", clean)
sub.add_node("shorten", shorten)
sub.add_edge(START, "clean")
sub.add_edge("clean", "shorten")
sub.add_edge("shorten", END)
sub_graph = sub.compile()


def polish(state: State) -> dict:
    return {"final": f"【摘要】{state['summary']}"}


builder = StateGraph(State)
builder.add_node("pre", sub_graph)          # 编译好的子图直接当节点
builder.add_node("polish", polish)
builder.add_edge(START, "pre")
builder.add_edge("pre", "polish")
builder.add_edge("polish", END)
graph = builder.compile()

out = graph.invoke({"text": "   LangGraph 的子图可以当作节点使用   ", "summary": "", "final": ""})
print("结果:", out)
print()
print("父图节点:", sorted(graph.get_graph().nodes.keys()))
print()
print("=== 父图 Mermaid ===")
print(graph.get_graph().draw_mermaid())
print()
print("=== 展开子图内部 ===")
print(graph.get_graph(xray=True).draw_mermaid())''',
                "code_lines": """1. 子图用同一个 `State`，三个字段在父子之间共享——这是「直接当节点」的前提。
2. `clean` 去掉首尾空格，`shorten` 截前 10 个字符，两步都很简单，方便观察谁做了什么。
3. `sub.compile()` 之后才能当节点；未编译的 `StateGraph` 加进去会报类型错误。
4. 父图只有 `pre` 与 `polish` 两个节点，`pre` 就是整张子图。
5. 结果里 `text` 已被去空格、`summary` 已生成——说明子图内部的状态变化透到了父图。
6. `get_graph().nodes` 只列出父图的节点名，看不到 `clean`/`shorten`。
7. Mermaid 里 `pre` 是一个普通节点，一条入边一条出边。
8. `xray=True` 之后才能看到 `subgraph pre` 里的两个节点，名字是 `pre:clean`、`pre:shorten`。""",
                "output": """# 程序输出
结果: {'text': 'LangGraph 的子图可以当作节点使用', 'summary': 'LangGraph …', 'final': '【摘要】LangGraph …'}

父图节点: ['__end__', '__start__', 'polish', 'pre']

=== 父图 Mermaid ===
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	pre(pre)
	polish(polish)
	__end__([<p>__end__</p>]):::last
	__start__ --> pre;
	pre --> polish;
	polish --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc


=== 展开子图内部 ===
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	polish(polish)
	__end__([<p>__end__</p>]):::last
	__start__ --> pre\\3aclean;
	pre\\3ashorten --> polish;
	polish --> __end__;
	subgraph pre
	pre\\3aclean(clean)
	pre\\3ashorten(shorten)
	pre\\3aclean --> pre\\3ashorten;
	end
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
""",
                "mistakes": """- 把未编译的 `StateGraph` 直接 `add_node`：必须 `compile()` 之后才能当节点。
- 父子 `State` 用同一个 TypedDict 却改了字段名：父图写不进去，子图读不到（下一节细讲）。
- 以为子图会继承父图的输入：它只拿到「父子共享的那些键」。
- 在父图里给子图内部节点连线：连不到，父图只认子图这一个节点名。
- 拆得太碎：每个节点都做成子图，图反而更难读。
- 调试时只看父图结构，找不到问题在哪：用 `xray=True` 展开。""",
                "error_analysis": """`TypeError: Expected a Runnable, callable or dict`
—— `add_node` 拿到了未编译的 `StateGraph`。先 `compile()`。

子图「什么都没做」
—— 父子状态没有共享键，子图收到空字典。检查两边 `TypedDict` 的字段名。

子图内部报 `KeyError`
—— 它以为有某个字段，实际父图没传。这就是下一节要解决的映射问题。

父图上找不到子图内部节点
—— 正常现象。要看内部结构用 `get_graph(xray=True)`。""",
                "beginner_practice": """1. 把 `pre` 节点的名字改成 `预处理`，看 Mermaid 里子图内部节点名前缀是否跟着变。
2. 给子图再加一个节点，观察父图的节点数量有没有变化。""",
                "advanced_practice": """把「检索 + 重排 + 摘要」做成一张子图，让它在父图里出现两次（一次查课程、一次查错题）。
说明两次调用怎么区分数据、状态怎么避免互相覆盖。""",
                "quiz_note": "本节 6 道题：2 道基础理解（子图当节点的前提、父图能看到什么）+ 2 道代码阅读（为什么节点里没有 `clean`、`xray` 有什么用）+ 2 道应用练习（何时拆子图、同一子图用两次）。",
                "summary": """编译好的子图可以直接当节点，父图只看到边界。
内部状态变化会透到父图——前提是共享同一批键。
`xray=True` 是排查子图问题的入口。""",
                "next_lesson": "如果父子状态不一样呢？下一节讲两种映射办法，以及它们各自的代价。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-23-01",
                        "name": "子图定义与调用",
                        "goal": "能把子图当节点接入父图，并展开查看内部结构。",
                        "minutes": 40,
                        "criteria": "能说明子图边界，并使用 `xray=True` 定位问题。",
                        "requires": ["langgraph-agent-22-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-23-01-1",
                        "kp": 0,
                        "title": "拆一张子图出来",
                        "description": "现有父图有 `fetch`、`clean`、`rank`、`summarize`、`answer` 五个节点。把前三步拆成子图，写出装配代码。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''sub = StateGraph(State)
sub.add_node("fetch", fetch)
sub.add_node("clean", clean)
sub.add_node("rank", rank)
sub.add_edge(START, "fetch")
sub.add_edge("fetch", "clean")
sub.add_edge("clean", "rank")
sub.add_edge("rank", END)
sub_graph = sub.compile()

builder = StateGraph(State)
builder.add_node("prepare", sub_graph)      # 前三步打包
builder.add_node("summarize", summarize)
builder.add_node("answer", answer)
builder.add_edge(START, "prepare")
builder.add_edge("prepare", "summarize")
builder.add_edge("summarize", "answer")
builder.add_edge("answer", END)''',
                        "explanation": "拆分点选在「一段有明确输入输出的处理」上：准备阶段的输入是查询、输出是排好序的资料，边界清楚。",
                    },
                    {
                        "code": "lg-ex-23-01-2",
                        "kp": 0,
                        "title": "子图用两次",
                        "description": "同一张子图在父图里用两次（查课程、查错题），怎么避免两次结果互相覆盖？",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": """两种做法，取决于两次调用是并行还是串行。

① 串行 + 不同字段：子图读取的输入键不同（`course_query` / `mistake_query`），
写入的输出键也不同（`course_docs` / `mistake_docs`）。用同一个子图对象，靠外部状态区分即可。

② 并行 + reducer：两次调用同时跑，写同一个 `docs` 键。必须给该键配 `operator.add` 之类的合并函数，
否则同一步两次写入会报 `Can receive only one value per step`（第 15 章）。若还要区分来源，
就写进带来源标记的结构，再在合并函数里去重。

要点：子图本身不需要知道「这是第几次调用」，它只负责「读我该读的、写我该写的」。
区分的责任在父图的状态设计上。

如果两次调用的输入输出结构差异很大，也可以考虑做成两张子图——复用不是目的，可读才是。""",
                        "explanation": "复用子图的前提是「输入输出能被父图区分」，这属于状态设计问题，不是子图的问题。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-23-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "把子图当节点加进父图，前提是什么？",
                        "options": [
                            ("A", "子图必须先 `compile()`"),
                            ("B", "子图节点数不能超过 3 个"),
                            ("C", "子图不能有条件边"),
                            ("D", "子图必须与父图用不同的 State"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "只有编译后的图才是可执行对象。未编译的 `StateGraph` 加进 `add_node` 会报类型错误。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-23-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "父图导出的结构里能直接看到子图内部的所有节点。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "默认只显示子图这一个节点。要看内部得用 `get_graph(xray=True)`。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-23-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`父图节点:` 打印出 `['__end__', '__start__', 'polish', 'pre']`，为什么没有 `clean` 和 `shorten`？",
                        "options": [
                            ("A", "因为它们没注册"),
                            ("B", "因为它们在子图内部，父图只认 `pre` 这一个节点"),
                            ("C", "因为子图没编译"),
                            ("D", "因为 `get_graph` 只返回前 4 个"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "这就是子图边界的直观体现：父图看到的是一个节点，不是一个内部结构。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-23-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "展开后的节点名是 `pre:clean` 而不是 `clean`，原因是什么？",
                        "options": [
                            ("A", "子图节点被重命名了"),
                            ("B", "`xray` 用「父节点名:子节点名」的方式避免重名"),
                            ("C", "冒号是 Mermaid 的语法要求"),
                            ("D", "因为 `clean` 在父图里也存在"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "同一个子图可能被用多次，也可能内部节点与父图节点同名，加前缀才能唯一标识。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-23-01-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "什么时候应该把一段流程拆成子图？",
                        "options": [],
                        "answer": """三个信号，出现任意一个就考虑拆。

① 父图读不清了：节点超过 7—8 个，主干被细节淹没。拆完之后父图应该能「一眼看懂顺序」。

② 这段流程要被复用：同一套「检索 + 重排 + 摘要」在多处出现，复制粘贴必然分叉。

③ 需要独立测试或独立权限：某段流程想单独跑用例、想用不同的重试策略、想让不同的人维护。

反过来说，不该拆的情况：只有一个节点、或者拆完父子状态要来回映射三四个字段（映射成本高于收益）。
下一节会看到，映射是要写代码的，不是免费的。

一条经验：拆分点选在「输入输出都清楚」的地方。边界模糊时先别拆，等它稳定了再抽。""",
                        "explanation": "拆分的目的是降低阅读成本，不是追求结构上的「模块化」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-23-01-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写出「编译子图、加入父图、连接入口与出口」的代码。",
                        "options": [],
                        "answer": {
                            "value": "sub_graph = sub_builder.compile()\n\nbuilder = StateGraph(State)\nbuilder.add_node(\"prepare\", sub_graph)\nbuilder.add_node(\"answer\", answer)\nbuilder.add_edge(START, \"prepare\")\nbuilder.add_edge(\"prepare\", \"answer\")\nbuilder.add_edge(\"answer\", END)\ngraph = builder.compile()"
                        },
                        "explanation": "关键只有一行 `add_node(\"prepare\", sub_graph)`：之后父图把它当普通节点连线即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "langgraph-agent-23-lesson-02",
                "title": "父子状态映射",
                "objectives": """1. 能复现「父子 schema 不同导致子图收到空字典」的问题；
2. 能用包装节点手动做输入输出映射；
3. 能说明映射层该写在哪、为什么不该把它塞进子图；
4. 能判断「改 schema 共享」与「加映射层」哪种更划算。""",
                "why_learn": """真实项目里，子图往往来自别处：可能是另一个团队写的，可能要先复用一段现成流程。
它的状态结构和你父图不一样，直接接会得到 `KeyError`——而且报错位置在子图内部，很难查。""",
                "concepts": """**共享键**：父子 schema 有同名字段时，子图能直接拿到值。
**没有共享键**：子图收到的是空字典（`{}`），随后 `KeyError`。
**包装节点**：写一个普通节点，把父状态转成子输入，调 `sub_graph.invoke(...)`，再把输出映射回父状态。
**映射方向**：输入映射（父 → 子）与输出映射（子 → 父），两边都要写。
**映射层的归属**：写在父图侧，子图保持「不知道外面长什么样」。
**取舍**：改 schema 共享最简单，但耦合；映射层解耦，但多一层代码与一次状态转换。""",
                "plain": """两个图要对接，得说同一种「语言」——也就是状态字段名。

父子用同一个 schema 时，子图直接读到父状态里的值，什么都不用做。
一旦字段名不一样，子图拿到的是空字典：它按自己的字段去取，取不到就报 `KeyError`。
报错发生在子图内部，栈里全是子图的节点名，你会以为是子图写错了。

解法是加一层翻译：在父图里写一个普通节点，把父状态转成子图要的输入，
调 `sub_graph.invoke(...)`，再把结果转回父状态的字段。

这层翻译应该放在父图这边。理由是：子图是「可复用的零件」，它不应该知道调用者长什么样；
换一个父图来用它，翻译逻辑跟着换，子图本身不用改。

如果两边其实可以统一 schema，那更省事——共享字段、直接接。代价是两个图从此绑在一起，
改字段要一起改。选哪种，看这段子图是「自家的一段流程」还是「别人的一个服务」。""",
                "syntax": """**手动映射的标准写法**

```python
def call_sub(state: ParentState) -> dict:
    out = sub_graph.invoke({"raw": state["question"], "result": ""})   # 父 -> 子
    return {"answer": out["result"]}                                   # 子 -> 父


builder.add_node("call_sub", call_sub)
```

- 子图输入要给全，缺字段同样会 `KeyError`。
- 返回值只写父图关心的字段，别把子图的整个状态倒回去。
- `call_sub` 是普通节点，所以它同样要遵守「返回增量、不改原状态」。
- 需要把子图的中间结果也带出来时，显式挑字段，不要 `return out`。""",
                "example_code": '''from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class SubState(TypedDict):
    raw: str
    result: str


class ParentState(TypedDict):
    question: str
    answer: str


def work(state: SubState) -> dict:
    print("  子图收到:", state)
    return {"result": state["raw"].upper()}


sub = StateGraph(SubState)
sub.add_node("work", work)
sub.add_edge(START, "work")
sub.add_edge("work", END)
sub_graph = sub.compile()

print("=== 直接把子图当节点（schema 无共享键）===")
builder = StateGraph(ParentState)
builder.add_node("sub", sub_graph)
builder.add_edge(START, "sub")
builder.add_edge("sub", END)
try:
    print(builder.compile().invoke({"question": "hi", "answer": ""}))
except KeyError as exc:
    print("KeyError :", exc)

print()
print("=== 包一层节点做映射 ===")


def call_sub(state: ParentState) -> dict:
    out = sub_graph.invoke({"raw": state["question"], "result": ""})
    return {"answer": out["result"]}


builder2 = StateGraph(ParentState)
builder2.add_node("call_sub", call_sub)
builder2.add_edge(START, "call_sub")
builder2.add_edge("call_sub", END)
print(builder2.compile().invoke({"question": "hi", "answer": ""}))''',
                "code_lines": """1. 子图的 `SubState` 只有 `raw` 与 `result`；父图的 `ParentState` 只有 `question` 与 `answer`——完全没有同名字段。
2. 直接把子图当节点接上去，父图传进去的 `{"question": ..., "answer": ...}` 对子图来说「一个都不认识」。
3. 子图启动时按自己的 schema 取字段，能拿到的只有空字典，所以 `work` 打印出 `{}`。
4. `state["raw"]` 取不到，抛 `KeyError: 'raw'`——报错在子图内部，很容易误判成子图的问题。
5. 第二段写一个普通节点 `call_sub`，显式把 `question` 映射成 `raw`，并补上 `result` 的初值。
6. `sub_graph.invoke(...)` 的返回值是子图的完整状态，这里只取 `out["result"]`。
7. 返回 `{"answer": ...}`，把子图的结果映射回父图的字段。
8. 结果 `{'question': 'hi', 'answer': 'HI'}`：父状态没被子图的字段污染，只有 `answer` 被更新。""",
                "output": """# 程序输出
=== 直接把子图当节点（schema 无共享键）===
  子图收到: {}
KeyError : 'raw'

=== 包一层节点做映射 ===
  子图收到: {'raw': 'hi', 'result': ''}
{'question': 'hi', 'answer': 'HI'}""",
                "mistakes": """- 以为子图会自动继承父状态：只继承「同名字段」，名字不同就是空。
- 子图输入漏给字段：`invoke({"raw": ...})` 少了 `result`，子图一读就 `KeyError`。
- 映射节点里 `return out`：把子图的 `raw`、`result` 全倒回父状态，父 schema 没有的键被静默丢弃。
- 把映射逻辑写进子图内部（子图里判断「调用者是谁」）：子图从此不可复用。
- 父子 schema 强行统一：两段流程本不相干，却因为一次复用绑死在一起。
- 映射时丢掉了元信息（比如来源、耗时），排查时不知道这条答案是子图给的。""",
                "error_analysis": """`KeyError: 'raw'`，报错位置在子图节点里
—— 父子没有共享键。要么统一 schema，要么加映射节点。

子图收到 `{}`
—— 同上。父状态里没有任何一个键与子图 schema 同名。

加映射后父状态多出一堆陌生字段
—— 映射节点 `return` 了整个子图状态。只挑需要的字段返回。

子图里改了值，父图看不到
—— 只写了输入映射，没写输出映射。子图的返回值要显式映射回父字段。""",
                "beginner_practice": """1. 把 `SubState` 的 `raw` 改名为 `question`，删掉映射节点直接接子图，观察是否还能跑通。
2. 在 `call_sub` 里打印 `out`，看看子图的完整状态长什么样。""",
                "advanced_practice": """写一个通用的映射节点工厂：传入「父→子」与「子→父」两个函数，返回一个可复用的节点函数。
说明这种写法在什么规模下开始有价值，以及它带来的调试成本。""",
                "quiz_note": "本节 6 道题：2 道基础理解（共享键的作用、映射层该放哪）+ 2 道代码阅读（为什么子图收到 `{}`、`return out` 有什么问题）+ 2 道应用练习（统一 schema 还是加映射、写映射节点）。",
                "summary": """父子有同名字段才能直连；没有就收到空字典。
映射层写在父图侧：输入转一遍、输出挑字段转回来。
统一 schema 省代码但耦合，映射层解耦但多一层。""",
                "next_lesson": "图能停、能拆、能存档了。下一章往外看：怎么把执行过程一段段推给前端。",
                "knowledge_points": [
                    {
                        "code": "langgraph-agent-23-02",
                        "name": "父子状态映射",
                        "goal": "能在父子 schema 不同时正确完成双向映射。",
                        "minutes": 45,
                        "criteria": "能复现空字典问题，并写出带输入 / 输出映射的包装节点。",
                        "requires": ["langgraph-agent-23-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "lg-ex-23-02-1",
                        "kp": 0,
                        "title": "补全映射节点",
                        "description": "父状态有 `query` 与 `docs`，子图需要 `raw` 与 `ranked`。写出映射节点。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def call_rank(state: ParentState) -> dict:
    out = sub_graph.invoke({"raw": state["query"], "ranked": []})
    return {"docs": out["ranked"]}''',
                        "explanation": "输入把 `query` 转成 `raw`、补上 `ranked` 初值；输出把 `ranked` 转成 `docs`。两边都只碰自己需要的字段。",
                    },
                    {
                        "code": "lg-ex-23-02-2",
                        "kp": 0,
                        "title": "统一 schema 还是加映射",
                        "description": "子图来自另一个团队。改 schema 共享，还是写映射层？给出判断依据。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": """看「谁控制子图」。

如果子图是自家的一段流程、以后会一起演进：统一 schema 更划算。少一层转换、少一个 bug 点，
状态在父子之间是同一份，调试时心智负担最低。

如果子图来自另一个团队、或要复用现成组件：写映射层。理由是耦合方向——
统一 schema 意味着对方改字段你就崩，而你无法控制对方的发版节奏。

还有一个中间做法：子图对外暴露「输入输出契约」（一两个字段），内部自己转换。
这样父图只需要映射一两个字段，子图内部随便改。

判断口诀：能改就统一，不能改就映射；两边都不能改，就约定契约。

无论选哪种，都别让子图知道调用者的字段名——那是把耦合藏起来，不是消除它。""",
                        "explanation": "技术选型背后是「谁有权改」，不是「哪种写法更短」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-lg-23-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "父子 schema 没有同名键时，把子图直接当节点会发生什么？",
                        "options": [
                            ("A", "框架自动按位置映射"),
                            ("B", "子图收到空字典，读字段时 `KeyError`"),
                            ("C", "编译阶段就报错"),
                            ("D", "子图被跳过"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "示例里 `work` 打印出 `{}`，紧接着 `KeyError: 'raw'`。编译不会报错，问题要到运行时才出现。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-23-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "映射逻辑应该写在子图内部，让子图自己去适配不同的父图。",
                        "options": [
                            ("A", "正确"),
                            ("B", "错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "映射写在父图侧，子图保持「不知道外面长什么样」。否则子图一旦被第二个父图复用，就得改它。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-lg-23-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "为什么第一段是 `KeyError: 'raw'` 而不是「子图没执行」？",
                        "options": [
                            ("A", "因为子图确实执行了，只是拿到的状态是空的"),
                            ("B", "因为 `work` 没注册"),
                            ("C", "因为 `ParentState` 缺字段"),
                            ("D", "因为 `sub_graph` 没编译"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "从 `子图收到: {}` 这行可以看出它确实跑起来了，只是按自己的 schema 取不到任何值。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-23-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "映射节点里写 `return out`（子图完整状态）会有什么后果？",
                        "options": [
                            ("A", "父状态里多出 `raw`、`result` 等父 schema 没有的键，被静默丢弃"),
                            ("B", "报 `InvalidUpdateError`"),
                            ("C", "覆盖父状态全部字段"),
                            ("D", "子图会再执行一次"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "父 schema 未声明的键会被丢掉（第 12 章）。看起来「没生效」，实际是写了但被过滤。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-lg-23-02-5",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "子图来自别的团队，你该统一 schema 还是加映射层？为什么？",
                        "options": [],
                        "answer": """加映射层。核心不是代码量，而是「谁有权改」。

统一 schema 意味着你和对方的字段名必须一直保持一致：对方发版改了个名字，你这边立刻崩，
而你无法控制对方的节奏。这种耦合在跨团队场景下几乎必然出事。

映射层把耦合收在一处：一个节点、两段转换。对方改字段，你只改这个节点；
父图其他部分完全不受影响。

更好的做法是约定「契约」：子图只暴露一两个输入字段与一两个输出字段，
内部结构随便改。这样映射量最小，双方也都有演进空间。

只有在子图是自家的一段流程、会和你一起改的时候，统一 schema 才更划算——
少一层转换，调试时状态是同一份，心智负担最低。""",
                        "explanation": "跨团队协作里，「能不能改对方」比「哪种写法更优雅」重要得多。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-lg-23-02-6",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个映射节点：父状态 `query` → 子图 `raw`，子图 `result` → 父状态 `answer`。",
                        "options": [],
                        "answer": {
                            "value": "def call_sub(state: ParentState) -> dict:\n    out = sub_graph.invoke({\"raw\": state[\"query\"], \"result\": \"\"})\n    return {\"answer\": out[\"result\"]}"
                        },
                        "explanation": "输入映射要给全子图 schema 的字段，输出映射只挑父图关心的字段——两头都不能省。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
