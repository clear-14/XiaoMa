"""Python 大模型 API 应用开发：第 7—9 章（多轮对话、上下文管理、Streaming）。"""

CHAPTERS: list[dict] = [
    {
        "code": "llm-api-07",
        "title": "多轮对话",
        "description": "让对话记得该记的，答得上刚才那句。",
        "order_index": 7,
        "lessons": [
            {
                "code": "llm-api-07-lesson-01",
                "objectives": """1. 能用一个类维护「历史 + 本轮问题」的完整消息序列；
2. 知道每轮结束后要立刻把模型回复追加进历史；
3. 能解释「模型本身不记事，记忆全靠你回传」；
4. 能写出一个可连续对话三轮的最小实现。""",
                "why_learn": """模型没有会话记忆：你第二句问「那它呢」，它能答上来完全是因为你把第一句一起发了过去。
不维护历史，多轮对话就退化成若干个互不相关的问题。""",
                "concepts": """**无状态调用**：每次请求都是一次独立推理，服务端不保存你的对话。
**历史回传**：把此前的 user/assistant 消息按顺序放进 `messages`。
**追加时机**：拿到回复后立刻追加 assistant，否则下一轮模型看不到自己说过什么。
**顺序保证**：历史顺序即对话顺序，乱序会让模型误解指代关系。""",
                "plain": """把模型想成一个每次见面都失忆的顾问：你要把上次聊的要点复述给他，他才能接着聊。
复述的方式就是把「我说了什么、他说了什么」按顺序排好一起递过去。
所以「记忆」其实存在你这边，模型只负责基于这份记录继续推理。""",
                "syntax": """**API 说明**

```python
class Conversation:
    def __init__(self, client, system: str):
        self.client = client
        self.messages = [{"role": "system", "content": system}]

    def ask(self, question: str) -> str:
        self.messages.append({"role": "user", "content": question})
        reply = self.client.chat(self.messages)["content"]
        self.messages.append({"role": "assistant", "content": reply})
        return reply
```

- `messages` 是唯一状态，类只负责追加与回传。
- 先追加 user 再请求，保证模型看到本轮问题。
- 拿到回复立刻追加 assistant，为下一轮做准备。""",
                "example_code": '''import os

import httpx


class LLMClient:
    def __init__(self, base_url: str, model: str, api_key: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, messages: list[dict]) -> dict:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers,
            json={"model": self.model, "messages": messages, "temperature": 0.3},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "content": data["choices"][0]["message"]["content"],
            "usage": data.get("usage", {}),
        }


class Conversation:
    def __init__(self, client: LLMClient, system: str):
        self.client = client
        self.messages = [{"role": "system", "content": system}]
        self.total_tokens = 0

    def ask(self, question: str) -> str:
        self.messages.append({"role": "user", "content": question})
        result = self.client.chat(self.messages)
        self.messages.append({"role": "assistant", "content": result["content"]})
        self.total_tokens += result["usage"].get("total_tokens", 0)
        return result["content"]

    def history(self) -> list[dict]:
        return [item for item in self.messages if item["role"] != "system"]


client = LLMClient(
    base_url=os.environ.get("LLM_BASE_URL", "https://api.example-a.com/v1"),
    model=os.environ.get("LLM_MODEL", "chat-large"),
    api_key=os.environ.get("LLM_API_KEY", ""),
)
conv = Conversation(client, system="你是一名耐心的 Python 助教，回答控制在三句话内。")
for question in ["什么是列表推导式？", "那它和生成器表达式有什么区别？", "给我一个例子"]:
    print("用户:", question)
    print("助手:", conv.ask(question))
print("历史条数:", len(conv.history()), "累计 token:", conv.total_tokens)''',
                "code_lines": """1. `LLMClient` 负责协议细节，`Conversation` 只负责消息序列，职责分开。
2. `messages` 在构造时放入 system，之后只做追加，不重排。
3. `ask` 先追加 user，再整段回传——这是多轮对话能成立的关键一步。
4. 回复内容立刻追加为 assistant，下一轮模型才能看到自己说过的话。
5. `total_tokens` 累计用量，为后面的成本统计留出字段。
6. `history()` 过滤掉 system，便于展示「纯对话内容」。
7. 三轮提问里第二句用了「那它」，能答对完全依赖历史被正确回传。""",
                "output": """# 请求体（第三轮，节选）
{"model":"chat-large","messages":[
  {"role":"system","content":"你是一名耐心的 Python 助教，回答控制在三句话内。"},
  {"role":"user","content":"什么是列表推导式？"},
  {"role":"assistant","content":"列表推导式是用一行表达式生成列表的写法，如 [x*2 for x in nums]。"},
  {"role":"user","content":"那它和生成器表达式有什么区别？"},
  {"role":"assistant","content":"前者一次性生成列表占内存，后者按需产出值更省内存。"},
  {"role":"user","content":"给我一个例子"}
]}

# 程序输出
用户: 给我一个例子
助手: 例如 sum(x*x for x in range(10)) 用生成器表达式求平方和，不占额外内存。
历史条数: 6 累计 token: 412""",
                "mistakes": """- 只保存用户问题，不保存模型回复，第二轮开始模型就失忆。
- 每轮都新建消息列表，只放 system + 本次问题，等于单轮问答。
- 把历史按时间倒序存，模型对指代关系判断错乱。
- 忘记累计用量，成本统计永远是 0。
- 在历史里塞入调试用的注释消息，模型把注释当事实。""",
                "error_analysis": """第二轮回答「你说的是什么列表？」
—— 历史没被回传或 assistant 消息缺失。打印请求体确认条数与顺序。

对话越长越慢、越贵
—— 历史线性增长，每轮都把全部历史重发一遍。这是下一章「上下文管理」要解决的问题。

指代错乱（「它」指错了对象）
—— 历史顺序错或中间被裁剪掉了关键轮次。检查裁剪策略是否保留了最近两轮。""",
                "beginner_practice": """1. 把 `ask` 改成返回 `(回复, 条数)`，观察条数每轮如何增长。
2. 故意不追加 assistant，连问两轮，观察第二轮的回答质量变化。""",
                "advanced_practice": """给 `Conversation` 加一个「重置」方法，并说明重置时应该保留什么（system）、清掉什么（历史），
以及重置前后用量统计该如何处理。""",
                "quiz_note": "本节 6 道题：2 道基础理解（无状态、追加时机）+ 2 道代码阅读（读 ask、读 history）+ 2 道应用练习（改返回值、加重置）。",
                "summary": """模型无状态，多轮记忆靠客户端回传历史。
每轮先追加 user、请求后追加 assistant，顺序不能乱。
历史会线性增长，成本和延迟都要提前考虑。""",
                "next_lesson": "下一节解决「多个用户同时聊」的串台问题。",
                "knowledge_points": [
                    {
                        "code": "llm-api-07-01",
                        "name": "对话状态与历史回传",
                        "goal": "能维护可连续多轮的对话消息序列。",
                        "minutes": 35,
                        "criteria": "能写出带 system、可连续三轮对话并统计用量的会话类。",
                        "requires": ["llm-api-06-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-07-01-1",
                        "kp": 0,
                        "title": "补上追加逻辑",
                        "description": "补全 `ask`：先追加 user，调用后追加 assistant，并返回回复文本。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''def ask(self, question: str) -> str:
    self.messages.append({"role": "user", "content": question})
    reply = self.client.chat(self.messages)["content"]
    self.messages.append({"role": "assistant", "content": reply})
    return reply''',
                        "explanation": "两句 append 分别对应「模型需要看到的问题」与「模型下次需要看到的自己」，缺一条多轮就断。",
                    },
                    {
                        "code": "llm-ex-07-01-2",
                        "kp": 0,
                        "title": "为什么不存服务端",
                        "description": "为什么兼容协议里没有「会话 ID」这个概念？如果产品需要跨设备继续对话，该怎么实现？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''协议本身是无状态的：服务端不保存上下文，每次请求自带全部消息，这样便于水平扩展与多厂商兼容。
跨设备继续对话需要应用层自己存储：把消息按会话 ID 落库（或对象存储），登录后按会话 ID 读回并重新拼成 messages 发出去。
注意存储时要区分「展示用历史」与「发送用历史」——前者可能包含未发送的草稿、失败消息。''',
                        "explanation": "无状态是协议的设计选择，持久化与跨端是应用层的责任。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-07-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "多轮对话能「记得上文」的根本原因是？",
                        "options": [
                            ("A", "客户端把历史消息一起发给模型"),
                            ("B", "服务端保存了会话状态"),
                            ("C", "模型有长期记忆"),
                            ("D", "token 会自动累积"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "兼容协议是无状态调用，记忆完全来自每次请求携带的 messages。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-07-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "要让第二轮对话正确使用第一轮信息，必须做到哪些？（多选）",
                        "options": [
                            ("A", "把第一轮 user 消息放进 messages"),
                            ("B", "把第一轮 assistant 回复放进 messages"),
                            ("C", "保持消息顺序与真实对话一致"),
                            ("D", "每轮重新生成一个新的 system 消息"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "system 每轮重复会稀释规则并浪费 token；历史成对且有序才是关键。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-07-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "若把 `self.messages.append({\"role\": \"assistant\", ...})` 删掉，第二轮会发生什么？",
                        "options": [
                            ("A", "模型看不到自己上一轮的回答，指代与承接会出错"),
                            ("B", "接口报 400"),
                            ("C", "token 用量减半"),
                            ("D", "没有影响"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "历史里只有 user 消息时，模型看到的是一串独立问题，无法承接上一轮结论。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-07-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`history()` 过滤掉 system 的目的是？",
                        "options": [
                            ("A", "展示「纯对话内容」，避免把规则文本当成聊天记录"),
                            ("B", "减少 token 消耗"),
                            ("C", "提高安全性"),
                            ("D", "让模型忘记规则"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "这只是展示层的过滤，发送给模型的 messages 仍然包含 system。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-07-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全代码，把模型回复追加进历史。横线处应填什么？\n\n```python\nself.messages.____({\"role\": \"assistant\", \"content\": reply})\n```",
                        "options": [("A", "append"), ("B", "extend"), ("C", "update"), ("D", "insert")],
                        "answer": {"value": "A"},
                        "explanation": "追加一条消息用 `append`；`extend` 会把字典按 key 展开成多个元素。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-07-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "十轮对话后，用户说「你刚才说的第二点再展开」，历史很长。你会怎么保证模型找得到「第二点」？",
                        "answer": {"value": "① 保留最近若干轮原文，确保「刚才」在窗口内；② 对更早的历史做摘要，并把「关键结论列表」显式写进 system 或摘要消息，例如「此前已给出三点：A/B/C」；③ 若用户经常引用具体条目，可在每轮回复里要求模型输出编号，便于后续定位；④ 裁剪时优先保留含编号结论的 assistant 消息，而不是简单按时间丢最早的；⑤ 必要时用工具或检索在历史里定位相关片段再注入。核心是「结构化保留结论」而不是「尽量多留原文」。"},
                        "explanation": "长对话的可靠性来自「结论被结构化保存」，而不是把全部原文硬塞进窗口。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-07-lesson-02",
                "objectives": """1. 能按会话 ID 隔离多份历史，避免用户之间串台；
2. 能保证每个会话独立持有自己的 system 规则；
3. 能设计会话的创建、读取与过期清理；
4. 能说明为什么会话状态不能放在进程内存里跨请求使用。""",
                "why_learn": """单用户单会话的示例能跑，一上线就出事：A 用户看到 B 用户的对话，或者助教突然变成客服。
会话隔离与角色一致性是多用户场景的底线。""",
                "concepts": """**会话 ID**：标识一份独立历史，通常用 UUID，由服务端生成。
**隔离原则**：读历史必须按会话 ID 查，绝不共用同一个列表。
**角色绑定**：system 与场景一起存在会话上，切换场景等于新会话。
**生命周期**：设置过期时间与上限，避免无限增长。
**存储位置**：会话要能跨请求、跨进程读取，因此不能只放进程内存。""",
                "plain": """会话像酒店房间：每人一间、各有房卡，走错房间就会看到别人的东西。
前台（服务端）发房卡（会话 ID），清洁（过期清理）按时收房。
如果把所有客人的行李堆在大堂（全局变量），谁来都能翻——这就是串台。""",
                "syntax": """**API 说明**

```python
class SessionStore:
    def create(self, system: str) -> str:
        session_id = str(uuid.uuid4())
        self._data[session_id] = {"system": system, "messages": []}
        return session_id

    def get(self, session_id: str) -> dict | None:
        return self._data.get(session_id)
```

- `create` 生成 ID 并把 system 一起存进去，保证角色跟着会话走。
- `get` 返回 `None` 时上层要当作「会话不存在」，不要自动新建。
- 生产实现要换成数据库或 Redis，接口保持不变。""",
                "example_code": '''import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    session_id: str
    system: str
    messages: list[dict] = field(default_factory=list)
    turns: int = 0


class SessionStore:
    def __init__(self, max_turns: int = 20):
        self._data: dict[str, Session] = {}
        self.max_turns = max_turns

    def create(self, system: str) -> str:
        session_id = str(uuid.uuid4())
        self._data[session_id] = Session(session_id=session_id, system=system)
        return session_id

    def get(self, session_id: str) -> Session | None:
        return self._data.get(session_id)

    def append(self, session_id: str, role: str, content: str) -> None:
        session = self._data[session_id]
        if role not in {"user", "assistant"}:
            raise ValueError(f"非法角色：{role}")
        session.messages.append({"role": role, "content": content})
        if role == "user":
            session.turns += 1

    def payload(self, session_id: str) -> list[dict]:
        session = self._data[session_id]
        return [{"role": "system", "content": session.system}] + session.messages

    def expired(self) -> list[str]:
        return [sid for sid, item in self._data.items() if item.turns >= self.max_turns]


store = SessionStore(max_turns=3)
alice = store.create("你是报销助手，只回答报销相关问题。")
bob = store.create("你是 IT 支持助手，只解决系统使用问题。")

store.append(alice, "user", "差旅费怎么报？")
store.append(alice, "assistant", "在系统里提交报销单并附发票。")
store.append(bob, "user", "VPN 连不上")

print("Alice 历史:", store.payload(alice)[1:])
print("Bob 历史:", store.payload(bob)[1:])
print("ALICE 的 system:", store.get(alice).system)
print("需清理的会话:", store.expired())''',
                "code_lines": """1. `Session` 把「ID + 规则 + 历史 + 轮数」放在一起，规则不会串到别的会话。
2. `create` 用 `uuid4` 生成不可猜的 ID，避免顺序号被枚举出他人会话。
3. `get` 找不到时返回 `None`，把「不存在」与「空会话」区分开。
4. `append` 校验角色白名单，阻止外部传入 system 篡改规则。
5. `payload` 每次按「当前 system + 本会话历史」重新拼装，保证规则永远在首位。
6. `expired` 用轮数判定过期，实际项目可换成时间戳。
7. 打印两个会话的历史，能直观看到彼此独立、system 各自不同。""",
                "output": """# 示例输出
Alice 历史: [{'role': 'user', 'content': '差旅费怎么报？'}, {'role': 'assistant', 'content': '在系统里提交报销单并附发票。'}]
Bob 历史: [{'role': 'user', 'content': 'VPN 连不上'}]
ALICE 的 system: 你是报销助手，只回答报销相关问题。
需清理的会话: []""",
                "mistakes": """- 用全局 `messages` 列表服务所有用户，直接串台。
- 会话 ID 用自增整数，可以被枚举，等于把你的历史开放给别人。
- 切换助手类型时只改 system 不换会话，导致规则与历史矛盾。
- 会话存进程内存，多 worker 下同一个用户两次请求读到不同历史。
- 没有过期策略，会话表无限增长，查询越来越慢。""",
                "error_analysis": """用户反馈「看到了别人的对话」
—— 历史存在全局变量或按用户 ID 取错了 key。先查存储键是否包含会话 ID。

同一用户刷新后历史消失
—— 会话存在进程内存且请求打到了另一个 worker。改用共享存储。

助手突然开始回答无关问题
—— system 被历史里的内容覆盖，或会话被复用到另一个场景。检查 system 是否随会话绑定。""",
                "beginner_practice": """1. 给 `SessionStore` 加 `delete(session_id)`，并说明删除后旧 ID 再用会怎样。
2. 把 `expired` 改成按「最后活跃时间超过 30 分钟」判定。""",
                "advanced_practice": """把 `SessionStore` 换成基于 SQLite 或 Redis 的实现，保持方法签名不变；
说明为什么「接口不变、实现可换」对上线后的扩容与迁移很重要。""",
                "quiz_note": "本节 6 道题：2 道基础理解（隔离原则、为什么不能放内存）+ 2 道代码阅读（读 payload、读 append 校验）+ 2 道应用练习（加删除、换存储）。",
                "summary": """会话按 ID 隔离，规则随会话绑定。
ID 必须不可猜，读不到就当作不存在，不要静默新建。
会话要放共享存储并设过期，接口保持不变便于替换实现。""",
                "next_lesson": "下一章解决历史越来越长的问题：token 预算与裁剪。",
                "knowledge_points": [
                    {
                        "code": "llm-api-07-02",
                        "name": "会话隔离与生命周期",
                        "goal": "能按会话隔离历史并管理过期与存储位置。",
                        "minutes": 35,
                        "criteria": "能写出按会话 ID 存取历史的存储类，并说明多 worker 下的存储要求。",
                        "requires": ["llm-api-07-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-07-02-1",
                        "kp": 0,
                        "title": "加删除与幂等",
                        "description": "实现 `delete(session_id)`，删除不存在的会话时不报错；并说明为什么删除要幂等。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''def delete(self, session_id: str) -> bool:
    return self._data.pop(session_id, None) is not None''',
                        "explanation": "网络重试或用户连点两次都会重复删除，幂等能避免「第二次删就报 500」。",
                    },
                    {
                        "code": "llm-ex-07-02-2",
                        "kp": 0,
                        "title": "换存储的代价",
                        "description": "把会话从进程内存迁到 Redis，需要改哪些地方？哪些不能变？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''要改：读写的具体实现（get / append / expired），序列化方式（JSON），过期策略（用 Redis TTL 代替轮数判断），并发控制（同一会话并发追加要加锁或用原子操作）。
不能变：对外方法签名与返回结构、system 与历史一起存储的约定、读不到时返回 None 的语义。
另外要考虑：Redis 不可用时的降级（报错还是走只读），以及数据迁移与双写过渡。''',
                        "explanation": "接口稳定是迁移的前提；一旦上层依赖了 Redis 细节，替换成本会指数上升。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-07-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "会话 ID 为什么建议用 UUID 而不是自增整数？",
                        "options": [
                            ("A", "自增 ID 可被枚举，容易读到他人会话"),
                            ("B", "UUID 更短"),
                            ("C", "自增 ID 无法存储"),
                            ("D", "UUID 能减少 token"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "可预测的 ID 等于把访问控制交给运气，必须用不可猜的随机标识。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-07-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "多 worker 部署下，会话存储必须满足哪些条件？（多选）",
                        "options": [
                            ("A", "多个进程都能读到同一份历史"),
                            ("B", "支持过期清理"),
                            ("C", "读不到时能明确区分「不存在」"),
                            ("D", "只存在进程内存中以获得最快速度"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "进程内存不共享，正是多 worker 下历史时有时无的根因。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-07-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`payload` 每次重新拼装 `system + messages`，而不是把 system 存在 messages 里，好处是？",
                        "options": [
                            ("A", "规则不会被历史追加操作打乱位置，也不会被用户输入覆盖"),
                            ("B", "节省内存"),
                            ("C", "支持多语言"),
                            ("D", "减少一次网络请求"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "system 与历史分开存放，拼装时永远在最前，避免「system 跑到中间」导致的规则失效。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-07-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`append` 对角色做白名单校验，能挡住哪类攻击？",
                        "options": [
                            ("A", "通过注入 system 消息篡改会话规则"),
                            ("B", "SQL 注入"),
                            ("C", "暴力破解会话 ID"),
                            ("D", "重放攻击"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "外部若能追加 system 消息，等于直接改写规则，这是提示注入的常见入口。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-07-02-5",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "用户切换助手类型（从报销助手改成 IT 助手）时，可以复用同一个会话，只改 system。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "旧历史与新规则会矛盾，模型容易混淆场景；切换场景应新建会话。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-07-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "会话过期清理怎么做才不会误删正在进行的对话？",
                        "answer": {"value": "① 用「最后活跃时间」而不是「创建时间」判定过期；② 每次读写都刷新该时间（滑动过期）；③ 清理任务分批执行并记录日志，便于回溯误删；④ 删除后保留一段时间的墓碑记录（只留 ID 与时间），避免用户刷新后被当成新会话而丢失上下文；⑤ 对长会话设「归档」而不是直接删，允许用户查看历史但不再继续。核心是「活跃即续期 + 可恢复」。"},
                        "explanation": "过期策略必须基于活跃度，且删除要可解释、可恢复，否则会制造「对话突然没了」的投诉。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "llm-api-08",
        "title": "上下文管理",
        "description": "上下文窗口有限，得决定记什么忘什么。",
        "order_index": 8,
        "lessons": [
            {
                "code": "llm-api-08-lesson-01",
                "objectives": """1. 能估算一次请求的 token 占用并算出预算；
2. 能实现「保留 system + 最近 N 轮」的裁剪策略；
3. 能说明为什么不能简单地按条数裁剪；
4. 知道超长输入会以什么形式失败。""",
                "why_learn": """历史每轮都全量重发，二十轮之后必然撞上上下文窗口。
撞上时的表现不是「答得差一点」，而是直接报错或截断输入——用户看到的是功能不可用。""",
                "concepts": """**上下文窗口**：输入 + 输出的 token 上限，各模型不同。
**预算**：`窗口 - 预留输出 - system 占用`，剩给历史的额度。
**估算**：无精确分词器时按字符数估算（中文约 1 字 1 token，英文约 4 字符 1 token），并按 20% 余量保守处理。
**裁剪策略**：保留 system、保留最近 N 轮、必要时保留含关键结论的轮次。
**失败形态**：超限通常报 400 或把输入截断，两者都会导致答非所问。""",
                "plain": """上下文像一个固定大小的背包：装得下就全带，装不下就必须取舍。
取舍的原则不是「平均丢」，而是「先保规则、再保最近、最后保结论」。
最怕的是把所有东西硬塞，结果背包拉链崩了（请求直接失败）。""",
                "syntax": """**API 说明**

```python
def estimate_tokens(text: str) -> int:
    return len(text) // 2          # 粗估：中文偏保守

def fit(messages: list[dict], budget: int) -> list[dict]:
    kept = [messages[0]]           # system 必留
    for item in reversed(messages[1:]):
        cost = estimate_tokens(item["content"])
        if cost > budget:
            break
        kept.insert(1, item)
        budget -= cost
    return kept
```

- 估算函数要说明「粗估」的前提，不能假装精确。
- 从最新一条往前保留，符合「最近最重要」的直觉。
- `budget` 是剩余额度，逐条扣减。""",
                "example_code": '''WINDOW = 8000
RESERVED_OUTPUT = 1000


def estimate_tokens(text: str) -> int:
    """粗估：中文按 1 字 1 token，英文按 4 字符 1 token，取偏保守的值。"""
    chinese = sum(1 for ch in text if "\\u4e00" <= ch <= "\\u9fff")
    others = len(text) - chinese
    return int(chinese + others / 3)


def budget_for(history: list[dict], system: str) -> int:
    return WINDOW - RESERVED_OUTPUT - estimate_tokens(system)


def fit(messages: list[dict], budget: int) -> tuple[list[dict], int]:
    kept = [messages[0]]
    dropped = 0
    for item in reversed(messages[1:]):
        cost = estimate_tokens(item["content"])
        if cost > budget:
            dropped += 1
            continue
        kept.insert(1, item)
        budget -= cost
    return kept, dropped


system = "你是报销助手，回答不超过三句话，不编造政策条款。"
history = [
    {"role": "system", "content": system},
    {"role": "user", "content": "差旅住宿标准是多少？"},
    {"role": "assistant", "content": "一线城市每晚 600 元，其他城市 400 元。"},
    {"role": "user", "content": "那餐补呢？"},
    {"role": "assistant", "content": "每天 100 元，按实际出差天数计算。"},
    {"role": "user", "content": "发票丢了还能报吗？"},
]

budget = budget_for(history, system)
kept, dropped = fit(history, budget)
print("可用预算:", budget)
print("保留条数:", len(kept), "丢弃条数:", dropped)
print("最后一条:", kept[-1]["content"])''',
                "code_lines": """1. `WINDOW` 与 `RESERVED_OUTPUT` 是两个显式常量，预算计算不再拍脑袋。
2. `estimate_tokens` 分开统计中文与其它字符，比 `len(text)/2` 更贴近实际。
3. 用 `\\u4e00`—`\\u9fff` 判断汉字区间，避免把标点算成汉字。
4. `budget_for` 先扣掉输出预留，再把剩余额度交给历史，顺序决定会不会被输出挤爆。
5. `fit` 从最新一条往前遍历，保证「最近说过的」优先保留。
6. 单条就超预算时直接跳过并计数，而不是让整个请求失败。
7. 返回丢弃条数，便于在日志里观察裁剪频率——频繁裁剪说明该上摘要了。""",
                "output": """# 示例输出
可用预算: 6964
保留条数: 6 丢弃条数: 0
最后一条: 发票丢了还能报吗？

# 历史很长时的输出（第 30 轮）
可用预算: 6964
保留条数: 9 丢弃条数: 43
最后一条: 上个月的报销单还能改吗？""",
                "mistakes": """- 用 `len(text)` 当 token 数，中文长文会严重低估。
- 忘记给输出预留额度，输入刚好占满窗口，输出直接被截断。
- 按「条数」裁剪而不看长度，一条长文本就能把预算吃光。
- 裁剪时把 system 也丢掉，模型失去规则约束。
- 裁剪后不成对（只剩 user 没有 assistant），模型误解对话结构。""",
                "error_analysis": """`400 maximum context length exceeded`
—— 输入加输出超过窗口。先降 `max_tokens`，再裁剪历史。

回答突然变短、`finish_reason` 为 `length`
—— 输入占满了窗口，输出没有空间。预留额度必须显式扣除。

裁剪后模型开始胡编政策条款
—— system 被裁掉了，或保留了问题却丢了「不知道就说不知道」的规则。system 永不参与裁剪。""",
                "beginner_practice": """1. 把 `WINDOW` 改成 2000，观察丢弃条数的变化。
2. 给 `fit` 加一条规则：至少保留最近 4 条消息（2 轮），不足时不再裁剪。""",
                "advanced_practice": """设计一套「分层裁剪」策略：system 永久保留、最近 3 轮原文保留、更早的轮次压缩成一条摘要消息、
关键结论单独抽成「要点列表」。说明各层的预算占比与优先级顺序。""",
                "quiz_note": "本节 6 道题：2 道基础理解（窗口含义、为什么要预留输出）+ 2 道代码阅读（读 estimate、读 fit）+ 2 道应用练习（改窗口、设计分层策略）。",
                "summary": """预算 = 窗口 − 输出预留 − system 占用，先算再拼。
估算要保守，中文长文尤其不能按字符数直接当 token。
裁剪保 system、保最近、保成对，并记录裁剪频率。""",
                "next_lesson": "下一节用摘要把「丢掉的历史」压成几句话。",
                "knowledge_points": [
                    {
                        "code": "llm-api-08-01",
                        "name": "Token 预算与历史裁剪",
                        "goal": "能在预算内裁剪历史并保证规则与最近上下文不丢。",
                        "minutes": 40,
                        "criteria": "能写出预算计算与从新到旧的裁剪函数，并说明 system 与输出预留为何必须保留。",
                        "requires": ["llm-api-07-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-08-01-1",
                        "kp": 0,
                        "title": "至少保留两轮",
                        "description": "修改 `fit`：无论预算多紧，都至少保留最近 4 条消息（2 轮问答）。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def fit(messages: list[dict], budget: int, min_keep: int = 4) -> tuple[list[dict], int]:
    kept = [messages[0]]
    dropped = 0
    for index, item in enumerate(reversed(messages[1:])):
        cost = estimate_tokens(item["content"])
        force = index < min_keep
        if cost > budget and not force:
            dropped += 1
            continue
        kept.insert(1, item)
        budget -= cost
    return kept, dropped''',
                        "explanation": "保底策略保证「刚才说的」不丢，代价是可能略微超出预算——真实实现要配合降低 `max_tokens` 兜底。",
                    },
                    {
                        "code": "llm-ex-08-01-2",
                        "kp": 0,
                        "title": "估算为什么不能精确",
                        "description": "为什么课程里用「粗估 + 余量」而不是声称能精确计算 token？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 精确计数需要与厂商完全一致的分词器，不同厂商、不同模型版本的分词规则不同；
② 消息本身还有角色、分隔符等结构开销，按纯文本算必然偏低；
③ 厂商可能随时调整分词实现，硬编码的精确值会悄悄失效。
因此工程上用「保守估算 + 实测校准」：先用偏高的估算保安全，再拿响应里的 usage 回填，统计偏差并调整系数。''',
                        "explanation": "承认估算的误差并留余量，比追求「看起来精确」更可靠；usage 是唯一的真值来源。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-08-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "上下文窗口限制的是什么？",
                        "options": [
                            ("A", "输入与输出加起来的 token 上限"),
                            ("B", "仅输入的 token 上限"),
                            ("C", "并发请求数"),
                            ("D", "历史轮数"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "窗口是输入 + 输出的总和，所以必须给输出预留空间。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-08-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "裁剪历史时哪些内容应优先保留？（多选）",
                        "options": [
                            ("A", "system 规则"),
                            ("B", "最近两轮问答"),
                            ("C", "包含关键结论的历史消息"),
                            ("D", "最早的寒暄与开场白"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "开场白信息密度最低，是最先该丢的部分。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-08-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`estimate_tokens` 里中文按 1 字 1 token、其它按 3 字符 1 token，这种估算相对 `len/2` 的优势是？",
                        "options": [
                            ("A", "中文长文本不再被严重低估"),
                            ("B", "计算速度更快"),
                            ("C", "能精确匹配厂商分词"),
                            ("D", "可以省掉 usage 统计"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "中文一个字常占一个 token 甚至更多，按字符数除以 2 会低估一半以上，导致预算算错。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-08-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`fit` 从 `reversed(messages[1:])` 遍历，且用 `insert(1, item)` 插回，结果是？",
                        "options": [
                            ("A", "保留的消息顺序与原顺序一致"),
                            ("B", "保留的消息顺序反转"),
                            ("C", "只保留最后一条"),
                            ("D", "system 被移到末尾"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "倒序遍历 + 固定插到位置 1，相当于从后往前填，最终顺序仍是从早到晚。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-08-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全预算计算，为输出预留 1000 token。横线处应填什么？\n\n```python\nbudget = WINDOW - ____ - estimate_tokens(system)\n```",
                        "options": [("A", "RESERVED_OUTPUT"), ("B", "max_tokens"), ("C", "budget"), ("D", "WINDOW")],
                        "answer": {"value": "A"},
                        "explanation": "用常量表达「给输出留的额度」，比每次写死数字更清晰，也便于按场景调整。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-08-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "日志显示裁剪频率从每天 3 次涨到每小时 200 次，你会怎么排查与处理？",
                        "answer": {"value": "先分类：是单会话变长（用户聊得久）、还是平均输入变长（用户粘贴长文档）、还是预算被调小（配置变更）。① 看分布：按会话统计轮数与单条长度，确认是长尾还是普遍变长；② 看类型：若大量是长文档粘贴，应改为「先摘要/检索再注入」而不是硬塞；③ 看规则：确认 system 是否膨胀（例如把整份知识库写进规则）；④ 处理：开启摘要压缩、把历史落库并按需检索、给超长输入单独的入口与提示。同时把裁剪次数、丢弃条数做成指标，配合告警阈值。"},
                        "explanation": "裁剪频繁是症状，原因可能是输入形态变化或配置漂移；先分型再对症，避免一味调大窗口。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-08-lesson-02",
                "objectives": """1. 能用模型把早期对话压成一段摘要；
2. 能设计「摘要 + 最近若干轮原文」的混合结构；
3. 能说明摘要该保留什么、丢什么；
4. 能评估摘要方案的成本与风险。""",
                "why_learn": """直接丢弃早期历史会丢关键信息：用户第一句说的预算上限、已确认的结论都可能消失。
摘要用几十个 token 换回这些事实，是长会话最划算的一笔交易。""",
                "concepts": """**滚动摘要**：把「旧摘要 + 被丢弃的若干轮」再次压缩，形成新摘要。
**保留要素**：已确认的事实、约束条件、用户偏好、未完成的待办。
**丢弃要素**：寒暄、重复解释、被推翻的方案。
**位置**：摘要作为一条 system 附加消息或单独标记的消息，放在历史之前。
**成本**：每次摘要本身也要一次调用，需按频率控制（如每 6 轮一次）。""",
                "plain": """摘要像会议纪要：不记录每句闲聊，只留「定了什么、还差什么」。
纪要在手，后面的人不用翻完整录音也能接着开会。
但纪要也会漏——所以最近的讨论仍保留原文，纪要只覆盖更早的部分。""",
                "syntax": """**API 说明**

```python
SUMMARY_PROMPT = (
    "把下面的对话压缩成不超过 120 字的摘要，只保留：已确认的事实、约束条件、未完成事项。"
    "不要包含寒暄与重复内容。"
)

def summarize(client, old_summary: str, dropped: list[dict]) -> str:
    text = old_summary + "\\n" + "\\n".join(f"{m['role']}: {m['content']}" for m in dropped)
    return client.chat([
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": text},
    ])["content"]
```

- 摘要 Prompt 明确「只保留三类信息」，避免压成流水账。
- 传入旧摘要，实现滚动压缩而不是每次重头来过。
- 摘要调用本身也消耗 token，要控制触发频率。""",
                "example_code": '''SUMMARY_RULES = "只保留已确认的事实、约束条件与未完成事项，不写寒暄，不超过 120 字。"


def should_summarize(turns: int, every: int = 6) -> bool:
    return turns > 0 and turns % every == 0


def build_summary_input(old_summary: str, dropped: list[dict]) -> str:
    lines = [f"已有摘要：{old_summary or '无'}"]
    for item in dropped:
        lines.append(f"{item['role']}: {item['content']}")
    return "\\n".join(lines)


def fake_summarize(text: str) -> str:
    """离线桩：把输入压成固定格式，便于观察结构。"""
    has_budget = "预算" in text
    return (
        "用户为市场部，报销需在 30 天内提交；"
        + ("已确认差旅住宿上限 600 元/晚；" if has_budget else "")
        + "待办：补充发票扫描件。"
    )


old_summary = "用户为市场部，咨询差旅报销标准。"
dropped = [
    {"role": "user", "content": "我们市场部出差住宿预算上限是多少？"},
    {"role": "assistant", "content": "一线城市 600 元/晚，其他城市 400 元/晚。"},
    {"role": "user", "content": "报销有提交时限吗？"},
    {"role": "assistant", "content": "需在费用发生后 30 天内提交。"},
]

print("是否触发摘要:", should_summarize(turns=6))
print("摘要输入:")
print(build_summary_input(old_summary, dropped))
print("新摘要:", fake_summarize(build_summary_input(old_summary, dropped)))''',
                "code_lines": """1. `SUMMARY_RULES` 明确三类保留信息，摘要结果才可控。
2. `should_summarize` 用轮数取模控制频率，避免每轮都调一次模型。
3. `build_summary_input` 把旧摘要与新丢弃的轮次拼在一起，实现滚动压缩。
4. 角色前缀 `user:` / `assistant:` 保留对话归属，摘要时不易张冠李戴。
5. `fake_summarize` 是离线桩：演示结构，真实实现换成模型调用。
6. 摘要里显式保留「待办」，这是长会话最容易丢、也最影响体验的信息。
7. 打印中间结果，便于人工检查摘要是否漏掉关键约束。""",
                "output": """# 示例输出
是否触发摘要: True
摘要输入:
已有摘要：用户为市场部，咨询差旅报销标准。
user: 我们市场部出差住宿预算上限是多少？
assistant: 一线城市 600 元/晚，其他城市 400 元/晚。
user: 报销有提交时限吗？
assistant: 需在费用发生后 30 天内提交。
新摘要: 用户为市场部，报销需在 30 天内提交；已确认差旅住宿上限 600 元/晚；待办：补充发票扫描件。""",
                "mistakes": """- 摘要 Prompt 不限定保留内容，结果压成一堆无用概括。
- 只摘要不保留最近原文，导致「刚才说的」也被压掉。
- 每轮都触发摘要，成本翻倍且摘要越来越失真。
- 摘要里丢掉数字与单位（600 元/晚 → 有住宿标准），关键约束失效。
- 摘要结果没有落库，进程重启后长会话直接失忆。""",
                "error_analysis": """摘要后模型开始给出与之前矛盾的答案
—— 摘要遗漏了已确认结论，或把「候选方案」写成了「已确认」。在摘要 Prompt 里区分「已确认」与「待定」。

成本比不摘要还高
—— 触发过频，或摘要输入本身过长。按轮数节流，并只摘「将被丢弃的部分」。

长会话第二轮就忘了约束
—— 摘要没被放进 messages。检查拼装顺序：摘要应在 system 之后、最近历史之前。""",
                "beginner_practice": """1. 把 `every` 改成 3，观察摘要触发频率的变化并估算额外成本。
2. 在 `SUMMARY_RULES` 里加一条「保留所有金额与日期」，对比摘要结果的差异。""",
                "advanced_practice": """设计「摘要 + 结构化记忆」双轨方案：除自然语言摘要外，再维护一个键值型事实表（预算、截止日期、已确认方案），
说明两者如何协同、冲突时以谁为准。""",
                "quiz_note": "本节 6 道题：2 道基础理解（摘要保留什么、为什么要滚动）+ 2 道代码阅读（读触发条件、读拼接）+ 2 道应用练习（调节流、设计双轨）。",
                "summary": """摘要覆盖「被丢弃的旧轮次」，最近几轮仍保留原文。
只保留事实、约束与待办，数字与日期必须原样留下。
摘要要节流、要落库，并明确「已确认」与「待定」的区别。""",
                "next_lesson": "下一章讲流式输出：让用户先看到第一个字。",
                "knowledge_points": [
                    {
                        "code": "llm-api-08-02",
                        "name": "滚动摘要与长会话",
                        "goal": "能用摘要压缩早期历史并保留关键约束。",
                        "minutes": 40,
                        "criteria": "能写出触发条件、拼装输入与摘要 Prompt，并说明摘要必须保留的三类信息。",
                        "requires": ["llm-api-08-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-08-02-1",
                        "kp": 0,
                        "title": "加一条保留规则",
                        "description": "在摘要规则里加入「保留所有金额、日期与截止条件」，并说明为什么这类信息最容易被压掉。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''SUMMARY_RULES = (
    "只保留已确认的事实、约束条件与未完成事项，不写寒暄，不超过 120 字；"
    "所有金额、日期、期限必须原样保留，不得改写或省略。"
)''',
                        "explanation": "模型倾向把具体数字概括成「有相关标准」，而数字恰恰是后续判断的依据，必须在规则里点名保留。",
                    },
                    {
                        "code": "llm-ex-08-02-2",
                        "kp": 0,
                        "title": "摘要与原文的边界",
                        "description": "如果用户问「我刚才说的预算是多少」，而该轮已被摘要，怎么保证答对？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 摘要里原样保留数字（规则约束）；② 更稳妥的做法是同时维护结构化事实表（预算=600 元/晚），回答此类问题时直接把事实表内容注入上下文；③ 对「我刚才说的 X」这类指代，可用检索在被摘要的原始历史里定位并回填；④ 关键结论（金额、日期、编号）不应只存在于自然语言摘要中。自然语言摘要负责语义连贯，结构化记忆负责精确复述。''',
                        "explanation": "精确信息用结构存、模糊语义用摘要存，两者分工是长会话可靠性的关键。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-08-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "滚动摘要（rolling summary）指的是？",
                        "options": [
                            ("A", "把旧摘要与新增被丢弃的轮次一起压缩成新摘要"),
                            ("B", "每次都从第一轮重新摘要全部历史"),
                            ("C", "只摘要最近一轮"),
                            ("D", "把摘要翻译成英文"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "滚动意味着增量推进：旧摘要 + 新丢弃部分 → 新摘要，成本可控且信息连续。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-08-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "摘要必须保留哪些信息？（多选）",
                        "options": [
                            ("A", "已确认的事实与结论"),
                            ("B", "约束条件（预算、期限、范围）"),
                            ("C", "未完成事项"),
                            ("D", "开场的寒暄与自我介绍"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "寒暄信息密度最低，正是摘要该丢的部分。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-08-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`should_summarize(turns=6, every=6)` 返回什么？",
                        "options": [
                            ("A", "True"),
                            ("B", "False"),
                            ("C", "6"),
                            ("D", "抛异常"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "6 % 6 == 0 且 turns > 0，触发摘要。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-08-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`build_summary_input` 里保留 `user:` / `assistant:` 前缀的作用是？",
                        "options": [
                            ("A", "让摘要能区分谁说了什么，减少张冠李戴"),
                            ("B", "减少 token"),
                            ("C", "满足协议要求"),
                            ("D", "便于排序"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "摘要时丢失角色归属，容易把用户的假设写成助手的结论。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-08-02-5",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "摘要做得越频繁、越详细，长会话效果就越好。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "每次摘要都是一次有损压缩且有额外成本；过频会让细节持续流失，反而更差。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-08-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如何评估「加摘要」这个改动到底值不值？",
                        "answer": {"value": "从三个维度量化：① 效果：用固定的多轮测试集（含「引用早期约束」的追问）比较加摘要前后的答对率；② 成本：统计平均每会话的输入 token 与调用次数，算出加摘要后的增量成本；③ 体验：首字延迟与失败率（超窗口导致的 400）。若答对率提升明显、成本增幅可接受（如 <20%），则值得；若主要是长尾会话受益，可改为「超过阈值才启用」的条件策略。"},
                        "explanation": "把「要不要摘要」变成可比较的三组数字，而不是凭感觉决定。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "llm-api-09",
        "title": "Streaming 流式输出",
        "description": "让用户先看到第一个字，而不是等十秒。",
        "order_index": 9,
        "lessons": [
            {
                "code": "llm-api-09-lesson-01",
                "objectives": """1. 能读懂 SSE 的 `data:` 行结构与 `[DONE]` 结束标记；
2. 能从每个增量块里取出 `delta.content` 并拼接；
3. 能处理「一个数据块包含多行」「一行只有空行」的情况；
4. 能解释流式与非流式在响应结构上的差异。""",
                "why_learn": """长回答等十秒才出现，用户会以为卡死。
流式把等待变成「逐字出现」，感知延迟从十秒降到几百毫秒——这是体感差距最大的一项优化。""",
                "concepts": """**SSE**：服务端推送事件，每行 `data: {json}`，以空行分隔事件。
**增量结构**：流式响应里是 `choices[0].delta`，不是 `message`。
**结束标记**：最后一行通常是 `data: [DONE]`，收到即停止。
**首块**：第一个块可能只有 `role`，没有内容，要跳过空内容。
**拼接**：所有 `delta.content` 顺序相加才是完整回答。""",
                "plain": """流式像水龙头滴水：不是等一桶水接满再给你，而是一滴一滴流出来。
每一滴（delta）单独看没意义，按顺序接起来才是那桶水。
`[DONE]` 就是关水龙头的信号，看到它就该停，而不是继续等。""",
                "syntax": """**API 说明**

```python
with httpx.stream("POST", url, headers=headers, json={**payload, "stream": True}) as response:
    for line in response.iter_lines():
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break
        chunk = json.loads(data)
        delta = chunk["choices"][0]["delta"].get("content")
        if delta:
            yield delta
```

- 请求体要显式带 `"stream": True`，否则返回整段。
- `iter_lines()` 逐行读，天然按 `\\n` 切分。
- `delta` 可能没有 `content`（首块或工具调用块），必须判空。""",
                "example_code": '''import json

RAW_LINES = [
    'data: {"choices":[{"delta":{"role":"assistant"}}]}',
    "",
    'data: {"choices":[{"delta":{"content":"流式"}}]}',
    'data: {"choices":[{"delta":{"content":"输出"}}]}',
    'data: {"choices":[{"delta":{"content":"就是把"}}]}',
    'data: {"choices":[{"delta":{"content":"回答分块返回。"}}]}',
    "",
    "data: [DONE]",
]


def parse_stream(lines: list[str]) -> str:
    parts: list[str] = []
    for line in lines:
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):].strip()
        if payload == "[DONE]":
            break
        chunk = json.loads(payload)
        choices = chunk.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if content:
            parts.append(content)
    return "".join(parts)


text = parse_stream(RAW_LINES)
print("拼接结果:", text)
print("块数:", len([line for line in RAW_LINES if line.startswith("data: ")]) - 1)''',
                "code_lines": """1. 只用 `startswith("data: ")` 过滤，跳过空行与注释行（`:` 开头的心跳）。
2. `line[6:]` 去掉前缀，注意 `data: ` 带一个空格，长度是 6。
3. 先判断 `[DONE]` 再 `json.loads`，否则会解析失败。
4. `choices` 可能为空（例如仅返回用量），判空后再取第 0 个。
5. `delta` 用 `.get` 取，避免首块只有 `role` 时 `KeyError`。
6. 只拼接有内容的块，空字符串不参与，避免多余的空片段。
7. 最后 `"".join(parts)`：顺序拼接，不能排序或去重。""",
                "output": """# 示例输入（服务端推送的原始行）
data: {"choices":[{"delta":{"role":"assistant"}}]}

data: {"choices":[{"delta":{"content":"流式"}}]}
data: {"choices":[{"delta":{"content":"输出"}}]}
data: {"choices":[{"delta":{"content":"就是把"}}]}
data: {"choices":[{"delta":{"content":"回答分块返回。"}}]}

data: [DONE]

# 程序输出
拼接结果: 流式输出就是把回答分块返回。
块数: 4""",
                "mistakes": """- 用 `message.content` 取流式内容，永远是空的（流式用 `delta`）。
- 忘记请求体加 `"stream": True`，以为服务端不支流式。
- 把 `[DONE]` 也丢进 `json.loads`，抛 `JSONDecodeError`。
- 每块都覆盖而不是拼接，最后只剩最后一句话。
- 用 `split(",")` 手工切 JSON，遇到内容里含逗号就崩。""",
                "error_analysis": """`json.decoder.JSONDecodeError: Expecting value`
—— 把 `[DONE]` 或空行送去解析。先判前缀与结束标记。

拼接结果缺字
—— 用了 `text = delta` 覆盖写法，或跳过了首块之后的某些块。用列表收集再 join。

中文出现乱码或半个字
—— 按字节切分而非按行切分。用 `iter_lines()` 让客户端处理边界。""",
                "beginner_practice": """1. 在 `RAW_LINES` 里加一行 `: ping`，确认解析结果不受影响。
2. 把 `parse_stream` 改成返回 `(text, chunk_count)`，统计实际有效块数。""",
                "advanced_practice": """把手写解析改成用 `httpx.stream` 实时读取：边接收边打印，
并统计首块到达时间与总耗时，说明这两个指标对体验的意义。""",
                "quiz_note": "本节 6 道题：2 道基础理解（delta 与 message 区别、DONE 作用）+ 2 道代码阅读（读前缀判断、读判空）+ 2 道应用练习（加心跳行、改实时读取）。",
                "summary": """流式响应用 `delta`，非流式用 `message`，两者结构不同。
按行读取、跳过非 data 行、先判 `[DONE]` 再解析。
增量按顺序拼接，任何时候都不要覆盖。""",
                "next_lesson": "下一节处理流式的坏情况：断线、超时与半截输出。",
                "knowledge_points": [
                    {
                        "code": "llm-api-09-01",
                        "name": "SSE 增量解析",
                        "goal": "能解析 SSE 数据行并正确拼接增量内容。",
                        "minutes": 40,
                        "criteria": "能写出跳过非 data 行、处理 DONE、判空 delta 的解析函数。",
                        "requires": ["llm-api-08-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-09-01-1",
                        "kp": 0,
                        "title": "补全解析分支",
                        "description": "补全：遇到 `[DONE]` 时停止循环，否则解析并取 `delta.content`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''for line in lines:
    if not line.startswith("data: "):
        continue
    payload = line[6:].strip()
    if payload == "[DONE]":
        break
    chunk = json.loads(payload)
    delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
    if delta.get("content"):
        parts.append(delta["content"])''',
                        "explanation": "顺序是「过滤 → 判结束 → 解析 → 判空 → 收集」，任何一步颠倒都会在脏数据上抛异常。",
                    },
                    {
                        "code": "llm-ex-09-01-2",
                        "kp": 0,
                        "title": "流式与整段的取舍",
                        "description": "列出三个适合流式、三个不适合流式的场景，并说明判断依据。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''适合：① 长文本生成（写作、总结）② 聊天对话 ③ 边生成边朗读/字幕。
不适合：① 需要结构化校验后再使用的 JSON 输出（半截 JSON 无法解析）② 需要计费/审核后再展示的场景 ③ 结果很短且必须整体一致（如单个标签分类）。
判断依据：用户是否需要「尽早看到」以及「半成品是否有用」。半成品无用时应等完整结果再校验、再展示。''',
                        "explanation": "流式的价值在「渐进可用」，如果中间态对用户无意义，流式只会增加复杂度。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-09-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "流式响应里取增量文本应读哪个字段？",
                        "options": [
                            ("A", "choices[0].delta.content"),
                            ("B", "choices[0].message.content"),
                            ("C", "usage.completion_tokens"),
                            ("D", "id"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "流式用 `delta`，整段响应用 `message`；混用会取到空值。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-09-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "解析 SSE 时必须处理哪些情况？（多选）",
                        "options": [
                            ("A", "空行与心跳注释行"),
                            ("B", "`[DONE]` 结束标记"),
                            ("C", "首块只有 role 没有 content"),
                            ("D", "把每块当成完整 JSON 文档存储"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "每块只是片段，不能当完整文档存；其余三项都是必须判空的边界。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-09-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`line[len(\"data: \"):]` 中长度取 6 而不是 5，原因是？",
                        "options": [
                            ("A", "前缀包含冒号后的一个空格"),
                            ("B", "JSON 以空格开头"),
                            ("C", "为了兼容 CRLF"),
                            ("D", "避免索引越界"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`data:` 后有一个空格，长度是 6；取 5 会留下前导空格，JSON 解析仍可能成功但格式不规范。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-09-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例里 `if content:` 判断去掉会怎样？",
                        "options": [
                            ("A", "拼接结果不变，但可能混入 None 导致类型错误"),
                            ("B", "结果会少字"),
                            ("C", "会陷入死循环"),
                            ("D", "会解析失败"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "空内容块拼进去没有意义，但 `None` 参与 `join` 会抛 `TypeError`，所以判空是必须的。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-09-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全请求体，开启流式返回。横线处应填什么？\n\n```python\npayload = {\"model\": model, \"messages\": messages, ____: True}\n```",
                        "options": [("A", "\"stream\""), ("B", "\"streaming\""), ("C", "\"sse\""), ("D", "\"chunked\"")],
                        "answer": {"value": "A"},
                        "explanation": "兼容协议的开关字段名就是 `stream`，写成 `streaming` 会被忽略而返回整段。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-09-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "前端把流式内容渲染成一跳一跳的，中间还偶尔卡顿，可能的原因有哪些？",
                        "answer": {"value": "① 服务端未关闭缓冲（反向代理或框架的响应缓冲导致攒够一批才下发）；② 后端按「行」转发但没及时 flush；③ 网络层 TCP 缓冲与 Nagle 算法合并了小包；④ 前端按固定间隔批量渲染而非收到即渲染；⑤ 上游本身出块慢（模型首 token 慢）。排查顺序：先看服务端日志里每块的时间戳，再看代理配置（`X-Accel-Buffering: no`、禁用 gzip 缓冲），最后看前端渲染节流策略。"},
                        "explanation": "卡顿多半来自「缓冲」而不是模型慢，逐层确认时间戳是唯一可靠的办法。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-09-lesson-02",
                "objectives": """1. 能在流式过程中处理断线、超时与异常；
2. 能区分「已输出部分内容」与「完全失败」两种情况；
3. 能写出带结束标记与错误事件的后端透传；
4. 知道流式场景下计费与用量该怎么拿。""",
                "why_learn": """流式把「一次请求」变成「一段持续连接」，失败形态也随之变化：
可能出了半句话再断、可能首块迟迟不来、可能末尾的用量丢失。这些都需要单独处理。""",
                "concepts": """**首块超时**：连接建立但迟迟没有数据，需要设「首块超时」而不是整体超时。
**半截输出**：已经显示了一部分再失败，前端要保留已显示内容并标注「未完成」。
**结束事件**：自定义 `event: done` 与 `event: error`，让前端明确收尾。
**用量获取**：多数厂商在最后一个块里返回 `usage`，也可能需要额外参数开启。
**重试**：流式中途失败通常不能「续传」，只能整体重试，要提示用户会重新开始。""",
                "plain": """流式像直播：可能开场就掉线，也可能播到一半黑屏。
观众最不能接受的是「黑屏了却不知道结束了没有」——所以要明确播「结束」或「故障」的信号。
已经播出去的内容收不回来，重播只能从头开始，这点要提前告诉用户。""",
                "syntax": """**API 说明（后端透传骨架）**

```python
def stream_chat(url, headers, payload):
    yield "event: start\\ndata: {}\\n\\n"
    try:
        with httpx.stream("POST", url, headers=headers, json=payload, timeout=60.0) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                ...
                yield f"data: {json.dumps({'delta': text}, ensure_ascii=False)}\\n\\n"
    except httpx.HTTPError as exc:
        yield f"event: error\\ndata: {json.dumps({'message': str(exc)})}\\n\\n"
    finally:
        yield "event: done\\ndata: {}\\n\\n"
```

- `event:` 行区分事件类型，`data:` 行放负载，末尾空行表示事件结束。
- `finally` 里发 `done`，保证前端一定能收到收尾信号。
- 异常转成 `error` 事件，不要直接抛给框架（会导致连接被硬断）。""",
                "example_code": '''import json


class StreamError(Exception):
    """流式过程中的可恢复错误。"""


def stream_chat(chunks: list[str], fail_at: int | None = None):
    """模拟后端透传：把上游增量转成 SSE 事件流。"""
    yield "event: start\\ndata: {}\\n\\n"
    collected: list[str] = []
    try:
        for index, chunk in enumerate(chunks):
            if fail_at is not None and index == fail_at:
                raise StreamError("上游连接中断")
            collected.append(chunk)
            payload = {"delta": chunk, "index": index}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\\n\\n"
    except StreamError as exc:
        payload = {"message": str(exc), "partial": "".join(collected)}
        yield f"event: error\\ndata: {json.dumps(payload, ensure_ascii=False)}\\n\\n"
    finally:
        payload = {"chars": sum(len(item) for item in collected)}
        yield f"event: done\\ndata: {json.dumps(payload, ensure_ascii=False)}\\n\\n"


for event in stream_chat(["流式", "失败", "要保留", "已输出内容"], fail_at=2):
    print(event, end="")''',
                "code_lines": """1. 先发 `start` 事件，让前端知道连接已建立，可以开始渲染占位。
2. `collected` 累积已发送的增量，用于失败时告诉前端「已收到多少」。
3. 每块都有 `index`，前端可据此发现丢块或乱序。
4. `except` 里把异常转成 `error` 事件，并把 `partial` 一起带出去。
5. `except` 里不外抛异常，避免框架直接断开连接导致前端收不到任何收尾信号。
6. `finally` 一定发 `done`，无论成功或失败，前端据此关闭 loading 状态。
7. `done` 里带统计信息（字符数），便于核对前端渲染是否完整。""",
                "output": """# 正常结束的事件流
event: start
data: {}

data: {"delta": "流式", "index": 0}

data: {"delta": "失败", "index": 1}

event: done
data: {"chars": 6}

# 中途失败的事件流（fail_at=2）
event: start
data: {}

data: {"delta": "流式", "index": 0}

data: {"delta": "失败", "index": 1}

event: error
data: {"message": "上游连接中断", "partial": "流式失败"}

event: done
data: {"chars": 4}""",
                "mistakes": """- 流式里直接 `raise`，框架返回 500 且前端一个字都收不到。
- 没有 `done` 事件，前端 loading 一直转。
- 失败后自动重试整段，用户看到内容重复出现两遍。
- 只设整体超时，首块迟迟不来时用户干等一分钟。
- 以为流式就没有用量，忽略最后一块里的 `usage`。""",
                "error_analysis": """前端一直显示「生成中」
—— 缺少 `done`/`error` 收尾事件。用 `finally` 保证一定发出。

内容出现重复段落
—— 中途失败后自动整体重试，而前端没清空旧内容。重试前先发 `event: reset` 或让前端清屏。

`httpx.ReadTimeout` 出现在长时间无数据后
—— 只配了整体超时。改用 `httpx.Timeout(connect=5, read=15)` 之类的分段超时。""",
                "beginner_practice": """1. 把 `fail_at` 改成 0，观察「一个字都没出就失败」时的事件序列。
2. 在 `done` 事件里加上 `usage` 字段（模拟从最后一块取），说明它为什么可能为空。""",
                "advanced_practice": """设计前端契约：`start` / `data` / `error` / `done` 四类事件分别对应什么 UI 状态，
断线后如何提示用户「重新生成会从头开始」，并把已生成内容保留为草稿。""",
                "quiz_note": "本节 6 道题：2 道基础理解（收尾事件、首块超时）+ 2 道代码阅读（读 finally、读 error 事件）+ 2 道应用练习（改 fail_at、设计前端契约）。",
                "summary": """流式必须发收尾事件：`done` 或 `error`，用 `finally` 保证。
失败时带上已输出内容，前端保留半成品而不是清空。
流式通常无法续传，重试要告知用户会从头开始。""",
                "next_lesson": "下一章把输出从「一段话」变成「可校验的数据」。",
                "knowledge_points": [
                    {
                        "code": "llm-api-09-02",
                        "name": "流式异常与收尾事件",
                        "goal": "能在流式中处理失败并保证前端收到收尾信号。",
                        "minutes": 40,
                        "criteria": "能写出带 start/data/error/done 四类事件并用 finally 收尾的透传函数。",
                        "requires": ["llm-api-09-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-09-02-1",
                        "kp": 0,
                        "title": "补上收尾事件",
                        "description": "补全 `finally` 块，保证无论如何都发送 `event: done`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''finally:
    payload = {"chars": sum(len(item) for item in collected)}
    yield f"event: done\\ndata: {json.dumps(payload, ensure_ascii=False)}\\n\\n"''',
                        "explanation": "`finally` 在异常路径上同样执行，这是「前端一定收到收尾信号」的唯一可靠写法。",
                    },
                    {
                        "code": "llm-ex-09-02-2",
                        "kp": 0,
                        "title": "重试还是续传",
                        "description": "流式输出到一半断了，产品问「能不能接着刚才的继续生成」，你怎么回答？",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''多数兼容实现不提供「续传」语义：连接断开后没有可复用的流上下文。可以做的近似方案是：把已生成内容作为 assistant 消息放入历史，再让模型「继续写，不要重复已写内容」。
但这有两个代价：① 会重新计费输入（已写内容要作为输入再发一遍）；② 模型可能仍出现重复或风格不一致。
因此产品上应明确告知用户「重新生成会从头开始」，把半成品保留为草稿，让用户选择「继续」或「重来」。''',
                        "explanation": "诚实说明能力边界，比假装支持续传而在结果里制造重复更专业。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-09-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "为什么收尾事件要放在 `finally` 里？",
                        "options": [
                            ("A", "保证异常路径也能发出结束信号"),
                            ("B", "性能更好"),
                            ("C", "能减少 token"),
                            ("D", "满足 HTTP 协议要求"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "只有 `finally` 在正常与异常两条路径上都会执行，收尾才不会漏。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-09-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "流式中途失败时，一个合格的实现应当做到什么？（多选）",
                        "options": [
                            ("A", "把已输出内容一起返回或保留"),
                            ("B", "发送错误事件说明原因"),
                            ("C", "仍然发送结束事件"),
                            ("D", "静默重试并清空前端内容"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "静默重试会导致内容重复或用户困惑；应当明确告知并让用户选择。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-09-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`fail_at=2` 时，示例输出了几个 `data:` 块？",
                        "options": [("A", "2"), ("B", "4"), ("C", "1"), ("D", "0")],
                        "answer": {"value": "A"},
                        "explanation": "index 0、1 正常发出，index 2 抛出异常，因此只有两个数据块。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-09-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`error` 事件里带上 `partial` 字段的意义是？",
                        "options": [
                            ("A", "让前端保留已生成内容并标注未完成"),
                            ("B", "方便计费"),
                            ("C", "用于重试计数"),
                            ("D", "压缩传输体积"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "半成品对用户仍有价值，丢掉会让用户觉得白等了；带上它才能做「保留草稿」。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-09-02-5",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "流式请求只需要设置一个整体超时就够了。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "整体超时无法覆盖「首块迟迟不来」：需要分别设置连接超时与读取超时。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-09-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如何在前端做到「断线后保留草稿，重试不重复计费感知糟糕」？",
                        "answer": {"value": "① 收到 `error` 时把 `partial` 内容固化到本地草稿，界面标注「未生成完」；② 提供两个按钮：继续（把草稿作为 assistant 历史再请求，提示可能重复）与重来（清空重新生成）；③ 重来时后端不要再自动重试，避免用户看到两份内容；④ 在 `done` 事件里返回本次用量，前端展示「本次消耗」而不是把两次合并成一次；⑤ 记录失败率与平均已生成长度，用于判断是否是模型侧不稳定。"},
                        "explanation": "把「不可续传」这一事实转化成显式的产品选择，是处理流式失败最稳的方式。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
