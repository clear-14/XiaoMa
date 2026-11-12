"""Python 大模型 API 应用开发：第 16 章综合项目（Python AI 对话助手）。"""

CHAPTERS: list[dict] = [
    {
        "code": "llm-api-16",
        "title": "综合项目：Python AI 对话助手",
        "description": "把 19 个主题串成一个能跑、能扩、能交付的助手。",
        "order_index": 16,
        "lessons": [
            {
                "code": "llm-api-16-lesson-01",
                "objectives": """1. 能把 Base URL、模型名与 Key 集中到一个配置对象里，且只从环境变量读取；
2. 能在启动时校验配置，缺失就立即失败并给出可操作的提示；
3. 能设计出「配置 / 模型 / 客户端 / 会话 / 流式 / 错误」六层拆分的项目结构；
4. 能保证打印配置、提交代码、写日志三种场景都不会泄漏 Key。""",
                "why_learn": """项目一开始就把 Key 写进代码，后面每一次提交都在扩大泄漏面。
先把配置这一层做干净，后面五节课的代码才能放心地放进仓库。""",
                "concepts": """**配置集中**：所有外部差异（地址、模型、超时、上限）只在一处读取。
**只读环境变量**：`os.environ` 是唯一入口，代码里不出现任何字面量密钥。
**启动即校验**：缺变量就抛 `ConfigError`，不要等到第一次调用才 401。
**默认值**：可选参数给默认值，必填参数绝不猜。
**脱敏**：`__repr__` 不打印 Key，日志里只留后四位指纹。
**仓库防护**：`.env` 进 `.gitignore`，只提交 `.env.example` 占位说明。
**六层结构**：`config` / `models` / `client` / `session` / `stream` / `errors`，每层只依赖下一层。""",
                "plain": """配置像家里的总闸：所有电器的开关都接在它后面，跳闸时只需要去一个地方。
如果每个房间自己拉一根线，改一次电压就得挨个房间跑。
而钥匙（Key）不能贴在闸箱外面——它只放在你自己的口袋里，由环境变量递进来。""",
                "syntax": """**项目骨架**

```text
ai_assistant/
├── .env.example          # 提交，只有键名与说明
├── .gitignore            # 忽略 .env 与 __pycache__
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── config.py         # 本节：读环境变量
│   ├── models.py         # 第 2 节：消息模型
│   ├── client.py         # 第 2 节：HTTP 调用
│   ├── session.py        # 第 3 节：多轮与裁剪
│   ├── stream.py         # 第 4 节：流式解析
│   └── errors.py         # 第 5 节：异常分类
└── tests/
    └── test_client.py
```

`.env.example`（可以进仓库，只有键名）：

```text
LLM_API_KEY=请填入你的 Key，本文件不提交真实值
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=chat-small
LLM_READ_TIMEOUT=30
LLM_MAX_TOKENS=800
```

`.gitignore`（必须包含前两行）：

```text
.env
.venv/
__pycache__/
```

运行方式（Key 只存在于当前 shell）：

```bash
export LLM_API_KEY="..."   # 或写进 .env 并用 dotenv 加载
python -m app.config
```""",
                "example_code": '''# app/config.py
import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """配置缺失或非法：启动时就该失败，而不是等第一次调用。"""


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"缺少环境变量 {name}，请参考 .env.example 配置")
    return value


def _optional(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


@dataclass(repr=False)
class Settings:
    api_key: str
    base_url: str
    model: str
    read_timeout: float = 30.0
    max_tokens: int = 800

    def __repr__(self) -> str:
        # 打印配置时绝不能带出 Key：只露地址和模型名
        return f"Settings(base_url={self.base_url!r}, model={self.model!r}, key=***)"


def load_settings() -> Settings:
    return Settings(
        api_key=_require("LLM_API_KEY"),
        base_url=_require("LLM_BASE_URL").rstrip("/"),
        model=_require("LLM_MODEL"),
        read_timeout=float(_optional("LLM_READ_TIMEOUT", "30")),
        max_tokens=int(_optional("LLM_MAX_TOKENS", "800")),
    )


def mask(secret: str) -> str:
    return "***" if len(secret) <= 8 else "***" + secret[-4:]


if __name__ == "__main__":
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"启动失败：{exc}")
        print("请先导出：LLM_API_KEY / LLM_BASE_URL / LLM_MODEL")
    else:
        print(settings)
        print("Key 指纹：", mask(settings.api_key))''',
                "code_lines": """1. `ConfigError` 继承 `RuntimeError`：配置问题属于「部署配置错」，不该被当成普通异常吞掉。
2. `_require` 用 `os.environ.get(name, "")` 再 `.strip()`，空字符串与「没设置」按同一件事处理。
3. `_optional` 是同一个思路的反面：给了默认值就必须能区分「没写」和「写了空」。
4. `@dataclass(repr=False)` 关掉自动生成的 `__repr__`，因为默认实现会把 `api_key` 原样打出来。
5. 自定义 `__repr__` 固定输出 `key=***`，这样 `print(settings)`、日志、异常栈都不会泄漏。
6. `base_url.rstrip("/")` 去掉末尾斜杠，避免拼出 `//chat/completions` 这种双斜杠地址。
7. `mask` 只保留后四位做指纹：足够在多个 Key 之间对照，又不足以还原。
8. `__main__` 分支把失败路径也当正常流程展示，方便第一次跑的人知道缺了什么。""",
                "output": """# 第一次运行：三个变量都还没设置
启动失败：缺少环境变量 LLM_API_KEY，请参考 .env.example 配置
请先导出：LLM_API_KEY / LLM_BASE_URL / LLM_MODEL

# 第二次运行：变量已导出（Key 值只在环境里，代码里没有）
Settings(base_url='https://api.example.com/v1', model='chat-small', key=***)
Key 指纹： ***7890""",
                "mistakes": """- 在模块顶层就调用 `load_settings()`：一 import 就崩，测试与命令行工具全部用不了。
- 用 `os.environ["LLM_API_KEY"]` 直接取：缺变量时抛 `KeyError`，错误信息完全看不出是配置问题。
- 用 `@dataclass` 默认的 `__repr__`：任何一次 `print(config)` 都会把 Key 打进日志。
- 把 `.env` 提交进仓库后再删掉：历史记录里仍然留着，必须换 Key。
- 把 `max_tokens`、`temperature` 硬编码在调用处，改一次要翻好几个文件。""",
                "error_analysis": """`ConfigError: 缺少环境变量 LLM_API_KEY`

这个报错的正确读法是「部署环境不完整」，处置顺序：

① 先确认变量是否真的导出：`echo $LLM_API_KEY` 只看有没有，不要把值打印到聊天窗口；
② 确认作用域：`export` 只对当前 shell 有效，systemd / Docker / 面板部署要各配各的；
③ 确认大小写：环境变量区分大小写，`llm_api_key` 不会命中 `LLM_API_KEY`；
④ 确认没被 `.strip()` 吃掉：从文档复制时常带零宽字符或换行，值看起来有、其实为空。

如果程序跑在容器里，最省事的排查是打印「变量名 + 长度」而不是值：长度 0 就是没传进去。""",
                "beginner_practice": """1. 给 `Settings` 增加 `max_retries` 字段，从 `LLM_MAX_RETRIES` 读取并默认 2，然后打印配置确认新字段生效。
2. 故意把 `LLM_BASE_URL` 设成带末尾斜杠的地址，确认 `repr` 里没有双斜杠。""",
                "advanced_practice": """把配置来源做成可切换的三层：环境变量 > `.env` 文件 > 代码默认值，
并规定「生产环境禁止使用 .env」——用 `APP_ENV=prod` 时若检测到 `.env` 存在就直接启动失败。
再补一个启动自检：打印 `base_url`、`model`、`key 指纹`、`read_timeout` 四项，作为部署日志的第一行。""",
                "quiz_note": "本节 6 道题：2 道基础理解（Key 的正确来源、启动即校验的意义）+ 2 道代码阅读（读 `repr=False`、读 `_require`）+ 2 道应用练习（补全必填读取、判断哪些文件能提交）。",
                "summary": """配置只有一个入口：环境变量；必填缺失就启动失败。
`__repr__` 必须自己写，否则 `print` 就是泄漏点。
`.env` 不提交、`.env.example` 提交，这条规矩要写进仓库而不是写在文档里。""",
                "next_lesson": "配置就位后，下一节写消息模型与第一次真实调用。",
                "knowledge_points": [
                    {
                        "code": "llm-api-16-01",
                        "name": "模型配置与项目骨架",
                        "goal": "能从环境变量装配出可用配置，并搭出分层清晰的项目结构。",
                        "minutes": 40,
                        "criteria": "能写出只读环境变量的配置模块、脱敏的 `__repr__`、以及六层目录骨架。",
                        "requires": ["llm-api-15-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-16-01-1",
                        "kp": 0,
                        "title": "给配置加一层启动自检",
                        "description": "写 `preflight(settings)`：校验 `base_url` 以 `https://` 开头、`read_timeout` 在 5 到 120 之间、`max_tokens` 不超过模型上限，任何一项不满足就抛 `ConfigError`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def preflight(settings: Settings, model_max_tokens: int = 4096) -> None:
    if not settings.base_url.startswith("https://"):
        raise ConfigError("LLM_BASE_URL 必须以 https:// 开头，避免明文传输 Key")
    if not 5 <= settings.read_timeout <= 120:
        raise ConfigError(f"LLM_READ_TIMEOUT 应在 5~120 秒之间，当前 {settings.read_timeout}")
    if not 1 <= settings.max_tokens <= model_max_tokens:
        raise ConfigError(
            f"LLM_MAX_TOKENS 应在 1~{model_max_tokens} 之间，当前 {settings.max_tokens}"
        )''',
                        "explanation": "把「环境问题」和「模型约束」都放在启动阶段检查：便宜、失败快、错误信息能直接指导改配置；运行期再发现就变成线上故障。",
                    },
                    {
                        "code": "llm-ex-16-01-2",
                        "kp": 0,
                        "title": "哪些文件可以进仓库",
                        "description": "列出本项目里可以提交和不能提交的文件，并说明「删除后再提交」为什么不够。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''可以提交：`.env.example`（只有键名与说明）、`.gitignore`、`requirements.txt`、
`app/` 下的源码、`tests/` 下的测试（使用占位 Key）。

不能提交：`.env`（真实 Key）、任何含真实 Key 的脚本或 notebook 输出、
`.venv/`、`__pycache__/`、本地日志与抓包文件。

「删除后再提交」不够，原因有三：
① Git 保留历史，`git log -p` 仍能翻出旧版本里的 Key；
② 已经推送到远端的分支可能被 fork、被缓存、被 CI 日志留存；
③ 即使仓库私有，协作者数量与离职交接都不可控。

正确处置是「先轮换、再清理」：立即在服务商后台吊销并换新 Key，
然后用 `git filter-repo` 之类工具清理历史，最后强制推送并通知所有协作者重新拉取。''',
                        "explanation": "密钥一旦进过版本库，就必须视为已泄漏；清理历史只是止损的第二步，第一步永远是换 Key。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-16-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "关于 API Key 的存放位置，下列做法正确的是？",
                        "options": [
                            ("A", "从环境变量读取，代码与仓库里都不出现值"),
                            ("B", "写在 `config.py` 顶部的常量里，方便修改"),
                            ("C", "写进 `.env.example` 以便同事直接使用"),
                            ("D", "作为函数默认参数传入"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "环境变量是唯一不落在代码与仓库里的入口；`.env.example` 只能放键名与占位说明。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "判断：配置缺失时，等第一次调用返回 401 再报错也一样，没必要在启动时校验。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "启动时失败一次就能定位，运行期失败会被误判成「服务不稳定」，还会消耗重试与告警资源。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`@dataclass(repr=False)` 在这里的作用是？",
                        "options": [
                            ("A", "关掉自动生成的 `__repr__`，改用自定义的不含 Key 的版本"),
                            ("B", "禁止创建该类的实例"),
                            ("C", "让字段变成只读"),
                            ("D", "减少内存占用"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "dataclass 默认 `__repr__` 会打印所有字段，包括 `api_key`；关掉后才轮到自己写安全版本。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`_require` 里先 `.get(name, \"\")` 再 `.strip()`，比直接用 `os.environ[name]` 好在哪里？",
                        "options": [
                            ("A", "把「没设置」和「设置了空值」统一成同一种可读的错误"),
                            ("B", "速度更快"),
                            ("C", "能自动从 .env 读取"),
                            ("D", "可以避免大小写问题"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "直接下标会抛 `KeyError`，信息只有变量名；统一判断能给出「缺什么、去哪儿看」的完整提示。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全代码，让缺少必填变量时抛出配置错误。横线处应填什么？\n\n```python\nvalue = os.environ.get(name, \"\").strip()\nif ____:\n    raise ConfigError(f\"缺少环境变量 {name}\")\n```",
                        "options": [
                            ("A", "not value"),
                            ("B", "value is None"),
                            ("C", "len(value) > 0"),
                            ("D", "value == \"LLM\""),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "空字符串是假值，`not value` 同时覆盖「没设置」和「设成空」两种情况。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-16-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "同事把含真实 Key 的 `.env` 误提交并推送到了远端，按什么顺序处理？",
                        "answer": {"value": "① 立刻轮换：到服务商后台吊销该 Key 并新建，先把泄漏面关掉，不要先研究怎么清理；② 评估影响：查该 Key 的用量与调用来源，确认是否已被使用、有无异常消费；③ 清理仓库：把 `.env` 加入 `.gitignore`，用 `git filter-repo`（或 BFG）从历史中移除并强推；④ 通知协作者重新克隆，因为强推后本地历史会分叉；⑤ 补机制：加 pre-commit 钩子扫描疑似密钥，CI 里加一次同类检查；⑥ 复盘：为什么本地没有 `.env.example` 引导，导致有人直接改了真实文件提交。顺序的关键是「先止血再清理」，先清理历史再换 Key 属于本末倒置。"},
                        "explanation": "密钥泄漏的第一动作永远是吊销，而不是删文件；清理历史只影响未来，不影响已经流出去的那份。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-16-lesson-02",
                "objectives": """1. 能定义 `Message` 模型并把它序列化成协议要求的 `{"role", "content"}`；
2. 能写出封装好的客户端类，把地址、认证、超时收在一处；
3. 能在请求体里正确设置模型名、温度与输出上限；
4. 能从响应里取出 `choices[0].message.content`，并处理 `None` 的情况。""",
                "why_learn": """消息结构是这门课的通用货币：多轮、流式、工具调用都以它为输入输出。
把它定义成类型，后面每个功能都只是「往列表里加一条」。""",
                "concepts": """**Message 模型**：`role` 与 `content` 两个字段，`role` 用 `Literal` 限定取值范围。
**序列化**：`to_dict()` 只输出协议需要的键，避免把内部字段（如时间戳）发给服务端。
**客户端类**：持有 `httpx.Client`，统一注入 `Authorization` 与超时。
**请求体**：`model` / `messages` / `temperature` / `max_tokens` 四项构成最小可用请求。
**响应取值**：`choices[0].message.content` 可能为 `None`，用 `or ""` 兜底。
**可测性**：构造函数接受 `transport`，测试时注入 `MockTransport`，不需要真 Key 与网络。""",
                "plain": """消息列表像一段已经录好的对话脚本：谁说、说了什么，一条一条往下排。
客户端则像传真机，只负责把脚本送出去、把回执拿回来，不关心脚本写了什么。
把这两件事分开，后面加流式、加工具、加裁剪，都不用改发送逻辑。""",
                "syntax": """**消息模型**

```python
@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}
```

**请求体**

```python
{"model": "...", "messages": [...], "temperature": 0.7, "max_tokens": 800}
```

**响应**

```python
{"choices": [{"message": {"role": "assistant", "content": "..."}}],
 "usage": {"prompt_tokens": 26, "completion_tokens": 9}}
```

- `content` 在工具调用场景可能为 `null`，取值时要兜底。
- `temperature` 越高越发散；事实类问答建议 0 到 0.3。
- 不要在客户端里做业务判断（比如「回答太长就重问」），那是上层的职责。""",
                "example_code": '''# app/client.py
import httpx

from app.config import Settings
from app.models import Message


class ChatClient:
    """所有网络细节都收在这里：地址、认证、超时、错误。"""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self._settings = settings
        self._client = httpx.Client(
            base_url=settings.base_url,
            headers={"Authorization": f"Bearer {settings.api_key}"},
            timeout=httpx.Timeout(
                connect=3.0, read=settings.read_timeout, write=10.0, pool=3.0
            ),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ChatClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def complete(self, messages: list[Message], temperature: float = 0.7) -> str:
        payload = {
            "model": self._settings.model,
            "messages": [message.to_dict() for message in messages],
            "temperature": temperature,
            "max_tokens": self._settings.max_tokens,
        }
        response = self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"] or ""


if __name__ == "__main__":
    from app.config import load_settings

    def fake(request: httpx.Request) -> httpx.Response:
        print("请求：", request.method, request.url)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "我是一个中文对话助手。"}}],
                "usage": {"prompt_tokens": 26, "completion_tokens": 9},
            },
        )

    with ChatClient(load_settings(), transport=httpx.MockTransport(fake)) as client:
        print("回复：", client.complete([Message("user", "用一句话介绍你自己")]))''',
                "code_lines": """1. 构造函数收 `transport` 参数，默认 `None` 走真实网络，测试时换成 `MockTransport`。
2. `base_url` 在这里注入，`post("/chat/completions")` 用相对路径，换服务商只改配置。
3. `Authorization` 拼成 `Bearer + 空格 + key`，这是兼容协议的统一写法。
4. `httpx.Timeout` 四个参数分开给，`read` 取配置里的值，因为生成耗时最长。
5. `close` 与 `__enter__` / `__exit__` 让客户端支持 `with`，连接一定会被释放。
6. 请求体只放四项：模型、消息、温度、上限；其他参数按厂商能力再加。
7. `[message.to_dict() for ...]` 做一次显式转换，避免把 `Message` 对象直接丢给 JSON 编码器。
8. `data["choices"][0]["message"]["content"] or ""` 同时处理「缺键」风险与 `None` 值。""",
                "output": """# 运行结果（transport 为本地模拟，不发真实请求）
请求： POST https://api.example.com/v1/chat/completions
回复： 我是一个中文对话助手。""",
                "mistakes": """- 直接把 `Message` 对象塞进 `json=`：`TypeError: Object of type Message is not JSON serializable`。
- 用字符串拼 URL：`base_url + "/chat/completions"` 在 base_url 带斜杠时变成双斜杠。
- 每次调用新建 `httpx.Client`：连接无法复用，高并发下握手开销明显。
- 忘记 `close()`：长跑进程里连接池与文件句柄慢慢泄漏。
- 在客户端里 `except Exception: return ""`：错误被吞成空回复，前端只看到「模型没说话」。""",
                "error_analysis": """`TypeError: Object of type Message is not JSON serializable`

原因：把 `Message` 实例直接放进了 `json=payload`。`httpx` 用标准 `json.dumps`，它不认识自定义类。

三种修法，按推荐顺序：
① 在客户端里显式转换 `[m.to_dict() for m in messages]`（本节做法），职责清晰；
② 给 `Message` 加 `asdict` 或 `to_json` 方法，但仍需在边界处调用；
③ 用 `dataclasses.asdict`，但对嵌套结构与 `Literal` 不友好。

不推荐的第四种：给 `Message` 注册自定义 `JSONEncoder`。它把「序列化规则」藏进全局，
一旦有人加了字段（比如 `tool_call_id`），输出结构会悄悄变化。""",
                "beginner_practice": """1. 给 `complete` 增加 `stop` 参数并透传，观察不同服务商对 `stop` 的支持是否有差异。
2. 把 `temperature` 改成 0，用同一个问题连问三次，比较回答的稳定性。""",
                "advanced_practice": """给客户端加一个「用量回调」：`on_usage(usage: dict)` 在每次成功调用后触发，
默认实现打印 `prompt_tokens` 与 `completion_tokens`。
再把它接到第 13 章的账本上，形成一个不侵入业务代码的成本统计点。""",
                "quiz_note": "本节 6 道题：2 道基础理解（消息的两个字段、认证头写法）+ 2 道代码阅读（读构造函数、读响应取值）+ 2 道应用练习（补全序列化、处理 None 内容）。",
                "summary": """消息是协议里的通用货币，用类型固定下来就不会传错形状。
客户端只做「发出去、拿回来」，不掺业务判断。
`transport` 参数是给测试留的口子，没有它就只能靠真 Key 做验证。""",
                "next_lesson": "单轮跑通后，下一节把历史接上，让助手记得上一句。",
                "knowledge_points": [
                    {
                        "code": "llm-api-16-02",
                        "name": "消息管理与 API 调用",
                        "goal": "能用统一的客户端完成一次带消息结构的调用并取出回复。",
                        "minutes": 45,
                        "criteria": "能定义 `Message` 与 `ChatClient`，正确设置请求体并从响应取回 `content`。",
                        "requires": ["llm-api-16-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-16-02-1",
                        "kp": 0,
                        "title": "让客户端支持多种消息类型",
                        "description": "给 `ChatClient` 增加 `ask(question, system_prompt=None)`：内部拼装 `system` 与 `user` 两条消息并调用 `complete`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def ask(self, question: str, system_prompt: str | None = None) -> str:
    messages: list[Message] = []
    if system_prompt:
        messages.append(Message("system", system_prompt))
    messages.append(Message("user", question))
    return self.complete(messages)''',
                        "explanation": "把「怎么拼消息」收进一个小方法，业务层只传一句话；`system_prompt` 为 `None` 时不加 system 消息，避免空字符串污染上下文。",
                    },
                    {
                        "code": "llm-ex-16-02-2",
                        "kp": 0,
                        "title": "为什么在客户端里不做重试之外的业务判断",
                        "description": "有人说「回复超过 500 字就在客户端截断」，说明这样做的三个问题。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 语义破坏：截断发生在句子中间，用户看到半句话；正确做法是把长度约束放进输出上限或 Prompt。
② 职责混乱：客户端负责传输，截断属于展示层或业务规则；混在一起后，别的调用方（如批处理）会被动继承这条规则。
③ 无法度量：截断后 `usage` 仍按完整输出计费，账面上「花了很多钱但用户只看到一半」，排查时很难对上。
④ 掩盖真实问题：真正该调的是 `max_tokens` 与 Prompt 里的「分点回答」，截断只是把症状藏起来。

合理的边界是：客户端只管重试、超时、错误分类这类传输语义；内容层面的规则放在业务层或 Prompt 里。''',
                        "explanation": "传输层越「聪明」，复用成本越高；把业务规则挡在客户端之外，才能让同一份调用逻辑服务多个场景。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-16-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "兼容协议的 `messages` 里，每条消息必须包含的两个键是？",
                        "options": [
                            ("A", "`role` 与 `content`"),
                            ("B", "`id` 与 `text`"),
                            ("C", "`name` 与 `content`"),
                            ("D", "`role` 与 `timestamp`"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`role` 决定说话者身份，`content` 是内容本身；其余键都属于可选扩展。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "判断：客户端构造时传入 `transport` 只是为了性能优化，测试里用不到。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "`transport` 的主要用途正是测试：注入 `MockTransport` 后可以离线复现 401、429、流式等场景，不需要真 Key。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "构造函数里把 `base_url` 交给 `httpx.Client`，而 `post` 只写相对路径，好处是？",
                        "options": [
                            ("A", "换服务商或环境时只改配置，调用代码一行不动"),
                            ("B", "请求速度更快"),
                            ("C", "可以绕过认证"),
                            ("D", "自动处理重试"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "地址与调用分离，是「同一套代码适配多个兼容端点」的前提。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`return data[\"choices\"][0][\"message\"][\"content\"] or \"\"` 里的 `or \"\"` 解决什么问题？",
                        "options": [
                            ("A", "`content` 可能为 `None`（如工具调用轮次），避免把 `None` 传给上层"),
                            ("B", "防止字段名拼错"),
                            ("C", "处理编码问题"),
                            ("D", "让返回值变成列表"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "工具调用时 `content` 常为 `null`；返回空串能让上层统一按「没说话」处理，而不是到处判 `None`。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全序列化，把消息转成协议要求的字典。横线处应填什么？\n\n```python\ndef to_dict(self) -> dict:\n    return {\"role\": ____, \"content\": self.content}\n```",
                        "options": [("A", "self.role"), ("B", "type(self)"), ("C", "self.__dict__"), ("D", "\"user\"")],
                        "answer": {"value": "A"},
                        "explanation": "`role` 是实例字段，直接取 `self.role`；写死 `\"user\"` 会让 system 消息也变成用户消息。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-16-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "生产环境里客户端实例应该怎么创建与复用？说说你的方案和理由。",
                        "answer": {"value": "① 进程内单例：在应用启动时创建一次 `ChatClient`，通过依赖注入传给各路由，退出时统一 `close()`；② 原因一：`httpx.Client` 内部维护连接池，复用可以省掉 TCP 与 TLS 握手，延迟与 CPU 都更低；③ 原因二：配置只解析一次，避免每个请求都读一遍环境变量；④ 原因三：限流器、账本、用量回调等状态需要挂在客户端上，重复创建会让统计失真；⑤ Web 框架里用 lifespan 管理生命周期（启动建、关闭关），而不是模块级的全局变量；⑥ 多进程部署（如 gunicorn 多 worker）时每个进程各有一份，这是正常的，统计要落到外部存储而不是进程内存。"},
                        "explanation": "客户端是有状态的重资源（连接池、限流器），生命周期应与进程一致；用生命周期钩子而不是模块级单例，才能保证被正确关闭。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-16-lesson-03",
                "objectives": """1. 能把会话状态与「一次请求的消息列表」分开设计；
2. 能实现按轮次与按 token 预算的双重裁剪，并保持消息成对；
3. 能用粗估函数在发送前算清输入规模；
4. 能说明「裁剪」与「摘要」各自适用什么场景。""",
                "why_learn": """上下文窗口是硬上限，历史则是无限增长的。
不裁剪，长会话迟早报「超出上下文长度」；裁得太狠，用户又会觉得助手失忆。""",
                "concepts": """**Session 与 messages 分离**：`history` 长期保存，`build()` 每次生成一份待发送副本。
**双重上限**：先按轮次截断（`MAX_TURNS`），再按 token 预算裁剪（`MAX_CONTEXT_TOKENS`）。
**成对裁剪**：一次丢两条，保证 `user` / `assistant` 成对，不会出现「助手回答了没人问的问题」。
**预留输出预算**：算输入时把预计输出（`max_tokens`）留出来，否则刚好卡满必然被截断。
**粗估函数**：中文按 1 字 1 token、其它按 3 字符 1 token，方向必须偏保守。
**摘要**：把被裁掉的早期对话压成一段事实摘要，插在 system 之后，兼顾长度与记忆。""",
                "plain": """上下文像一张只能写这么多字的纸：新内容一定要写，就得先擦掉最早的一段。
擦的时候要整段擦——只擦掉问题留下答案，读起来就像助手在自言自语。
擦之前先把要写的字算一算，别写着写着发现没地方了。""",
                "syntax": """**裁剪骨架**

```python
kept = history[-MAX_TURNS * 2:]
reserve = estimate_tokens(question) + max_tokens
while kept and tokens_of(kept) + reserve > MAX_CONTEXT_TOKENS:
    kept = kept[2:]          # 整轮丢弃
return [system(SYSTEM_PROMPT), *kept, user(question)]
```

**粗估**

```python
chinese = sum(1 for ch in text if "\\u4e00" <= ch <= "\\u9fff")
other = len(text) - chinese
return chinese + (other + 2) // 3
```

- 估算是「上界思维」：宁可高估 10%，不要低估 1%。
- 真实用量以响应的 `usage.prompt_tokens` 为准，用它校准估算系数。
- 摘要属于「有损压缩」，涉及金额、日期、订单号这类事实要原样保留。""",
                "example_code": '''# app/session.py
from dataclasses import dataclass, field

from app.models import Message, assistant, system, user

SYSTEM_PROMPT = "你是一个简洁的中文助手，每次回答控制在三句话内。"
MAX_CONTEXT_TOKENS = 1200
MAX_TURNS = 6


def estimate_tokens(text: str) -> int:
    """粗估：中文 1 字约 1 token，其它字符约 3 个 1 token；宁可高估。"""
    chinese = sum(1 for ch in text if "\\u4e00" <= ch <= "\\u9fff")
    other = len(text) - chinese
    return chinese + (other + 2) // 3


def tokens_of(messages: list[Message]) -> int:
    return sum(estimate_tokens(message.content) for message in messages)


@dataclass
class Session:
    session_id: str
    history: list[Message] = field(default_factory=list)

    def build(self, question: str) -> list[Message]:
        kept = self.history[-MAX_TURNS * 2:]
        reserve = estimate_tokens(question) + 200  # 给回答预留输出预算
        # 整轮丢弃：一次 pop 两条，保证 user / assistant 始终成对
        while kept and tokens_of(kept) + reserve > MAX_CONTEXT_TOKENS:
            kept = kept[2:]
        return [system(SYSTEM_PROMPT), *kept, user(question)]

    def remember(self, question: str, answer: str) -> None:
        self.history.append(user(question))
        self.history.append(assistant(answer))


if __name__ == "__main__":
    session = Session("s-001")
    for index in range(6):
        session.remember(
            f"第 {index + 1} 轮：" + "退款流程怎么走？" * 40,
            "回答：" + "签收后 7 天内可申请，超过则转人工。" * 12,
        )

    messages = session.build("那超过 7 天呢？")
    print("历史总条数：", len(session.history))
    print("本次发送条数：", len(messages))
    print("预计输入 token：", tokens_of(messages))
    print("首条角色：", messages[0].role, "| 末条角色：", messages[-1].role)
    print("最早保留的一轮是：", messages[1].content[:8])''',
                "code_lines": """1. `Session` 只存 `history`，不存「已拼好的消息」：拼装是每次请求的临时动作。
2. `estimate_tokens` 按字符类型分两段算，`(other + 2) // 3` 用向上取整保证不低估。
3. `tokens_of` 遍历消息累加，裁剪循环与调用方共用同一个口径。
4. `history[-MAX_TURNS * 2:]` 先做一次廉价的轮次截断，避免每次都遍历几千条历史。
5. `reserve = estimate_tokens(question) + 200` 把本次问题与输出预算一起预扣，防止刚好卡满。
6. `while kept and ...` 循环条件带 `kept`，即使单条消息就超预算也不会死循环。
7. `kept = kept[2:]` 一次丢两条：成对裁剪是这个函数唯一不能省的规则。
8. `return [system(...), *kept, user(question)]` 顺序固定：规则在前、历史在中、新问题在最后。""",
                "output": """# 运行结果（6 轮历史，每轮都很长）
历史总条数： 12
本次发送条数： 6
预计输入 token： 1006
首条角色： system | 末条角色： user
最早保留的一轮是： 第 5 轮：退款""",
                "mistakes": """- 用 `kept.pop(0)` 逐条丢：可能丢掉问题留下答案，模型会看到「自己回答自己」。
- 只按轮次裁剪、不按 token：一轮里塞进一篇 8000 字文档就直接超限。
- 忘记给输出预留预算：输入刚好顶满，模型没有空间生成，`finish_reason` 直接是 `length`。
- 把 system 消息也算进裁剪：一丢就等于角色设定消失，回答风格立刻漂移。
- 估算用「英文 4 字符 1 token」的系数套中文：中文会被低估一半以上。
- 直接把 `history` 传给客户端：调用方一旦改动列表，会话状态就被破坏了。""",
                "error_analysis": """`400: This model's maximum context length is 4096 tokens, but your messages resulted in 5200 tokens`

这不是「偶发失败」，而是预算算错了，重试没有意义。排查顺序：

① 核对估算口径：是否只算了 `content`，漏了 system 与本次问题；
② 核对预留：`max_tokens` 是否大于真实剩余空间，服务端要求「输入 + 输出上限 ≤ 窗口」；
③ 找出异常长的那条消息：日志里记每条的 `len(content)` 与估算值，通常是一条检索结果没截断；
④ 修策略：对单条消息设上限（如 2000 token），超长内容先摘要再入上下文；
⑤ 校准系数：用最近 100 次真实 `usage.prompt_tokens` 对比估算值，把系数调到偏保守的一侧。""",
                "beginner_practice": """1. 把 `MAX_CONTEXT_TOKENS` 改成 3000，观察「本次发送条数」如何变化，并解释为什么变多。
2. 把 `kept = kept[2:]` 改成 `kept = kept[1:]`，运行后检查首条历史消息的角色，说明问题在哪。""",
                "advanced_practice": """实现摘要式裁剪：当被裁掉的消息超过 4 条时，把它们交给模型压成三句话的事实摘要，
存进 `session.summary`，并在 `build()` 时作为一条 system 消息插在 `SYSTEM_PROMPT` 之后。
对比两种策略在「用户第 10 轮追问第一轮提到的订单号」这个场景下的表现。""",
                "quiz_note": "本节 6 道题：2 道基础理解（双重上限的作用、为什么要预留输出）+ 2 道代码阅读（读裁剪循环、读估算函数）+ 2 道应用练习（补全成对裁剪、判断超限报错的处理）。",
                "summary": """历史与会话分离，每次请求现拼一份消息列表。
轮次与 token 双重上限，裁剪必须整轮进行。
估算偏保守、预留输出空间，超限报错要当配置问题而不是网络问题。""",
                "next_lesson": "上下文准备就绪，下一节把「一次性返回」换成「边生成边显示」。",
                "knowledge_points": [
                    {
                        "code": "llm-api-16-03",
                        "name": "多轮上下文与上下文裁剪",
                        "goal": "能在固定预算内维护多轮历史，并保证裁剪后对话结构仍然完整。",
                        "minutes": 45,
                        "criteria": "能写出 `Session.build` 的双重裁剪逻辑、成对丢弃与 token 粗估函数。",
                        "requires": ["llm-api-16-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-16-03-1",
                        "kp": 0,
                        "title": "给单条消息加上限",
                        "description": "在 `build` 里对每条历史消息截断到 `MAX_MESSAGE_TOKENS`（默认 600），超出时保留开头与结尾并插入省略标记。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''MAX_MESSAGE_TOKENS = 600


def clip(text: str, limit: int = MAX_MESSAGE_TOKENS) -> str:
    if estimate_tokens(text) <= limit:
        return text
    head = text[: limit * 2 // 3]
    tail = text[-(limit // 3):]
    return f"{head}\\n...（内容过长，已省略中间部分）...\\n{tail}"


def build(self, question: str) -> list[Message]:
    kept = [
        Message(message.role, clip(message.content))
        for message in self.history[-MAX_TURNS * 2:]
    ]
    reserve = estimate_tokens(question) + 200
    while kept and tokens_of(kept) + reserve > MAX_CONTEXT_TOKENS:
        kept = kept[2:]
    return [system(SYSTEM_PROMPT), *kept, user(question)]''',
                        "explanation": "先压单条再压整体：一条超长消息会把其它轮次全部挤掉，先截断它能保住更多对话脉络；保留头尾是因为问题和结论通常分别在两端。",
                    },
                    {
                        "code": "llm-ex-16-03-2",
                        "kp": 0,
                        "title": "裁剪与摘要怎么选",
                        "description": "比较「直接丢弃早期对话」与「压成摘要保留」两种方案，各自适合什么场景。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''直接丢弃：
- 适合客服问答、工具查询等「只看最近几轮」的场景；
- 实现简单、无额外调用成本、结果可预测；
- 缺点是不可逆：一旦丢掉，用户再提第一轮的信息就接不上。

摘要压缩：
- 适合长程任务（写方案、排查故障、多步骤办事），需要记住早先的结论与约束；
- 需要额外一次模型调用，成本与延迟都会增加；
- 有损：必须规定「金额、日期、订单号、人名」原样保留，其余可概括；
- 摘要本身也要有长度上限，否则压缩后的内容又变成新的负担。

工程上常见组合：最近 2 到 3 轮保留原文，更早的压成一段不超过 200 字的摘要，
摘要只在「被裁掉的消息数超过阈值」时重算，避免每轮都多花一次调用。''',
                        "explanation": "选择标准不是「哪个更聪明」，而是「这轮对话是否需要跨越十几轮引用早期事实」；不需要就别付摘要的成本。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-16-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`Session.build()` 为什么不直接返回 `self.history`？",
                        "options": [
                            ("A", "要让裁剪只作用于本次请求，不能改动长期保存的历史"),
                            ("B", "因为 `history` 是元组，不能直接发送"),
                            ("C", "为了减少一次内存拷贝"),
                            ("D", "因为客户端要求列表长度固定"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "裁剪是「本次发送」的策略，历史本身要保留全量；直接返回再就地删改会让会话真的失忆。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-03-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "判断：只要按轮次限制历史条数，就不会再出现超出上下文窗口的报错。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "轮次固定但每轮长度可变：一轮里贴进长文档照样超限，所以还需要按 token 预算裁剪。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-03-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "裁剪循环写成 `kept = kept[2:]` 而不是 `kept.pop(0)`，主要考虑是？",
                        "options": [
                            ("A", "一次丢两条，保持 user / assistant 成对出现"),
                            ("B", "切片比 pop 快"),
                            ("C", "避免修改原历史列表"),
                            ("D", "让 system 消息也被裁掉"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "只丢一条会出现「助手凭空回答」的结构，模型容易跟着跑偏；成对丢弃是维持对话语义的最低要求。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-03-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`reserve = estimate_tokens(question) + 200` 中的 200 代表什么？",
                        "options": [
                            ("A", "为本次回答预留的输出 token 预算"),
                            ("B", "system 消息的长度"),
                            ("C", "消息条数的上限"),
                            ("D", "网络延迟的补偿量"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "服务端要求「输入 + 输出上限」不超过窗口，不预留输出空间就会在生成时被硬截断。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-03-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全循环，使预算不足时持续丢弃最早的整轮对话。横线处应填什么？\n\n```python\nwhile kept and tokens_of(kept) + reserve > MAX_CONTEXT_TOKENS:\n    ____\n```",
                        "options": [
                            ("A", "kept = kept[2:]"),
                            ("B", "kept = kept[:-1]"),
                            ("C", "break"),
                            ("D", "kept.clear()"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "从头部整轮移除才能既缩小预算、又保持后续消息对完整；`kept[:-1]` 会把最新一轮删掉。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-16-03-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "用户抱怨「助手忘了第一轮说过的订单号」，在不放宽窗口的前提下你能怎么改？",
                        "answer": {"value": "① 结构化记忆：把订单号、金额、日期这类关键实体在每轮结束后抽取出来，存进 `session.facts`，并在 `build()` 时作为一条 system 消息固定带上，不参与裁剪；② 摘要替换丢弃：被裁掉的早期对话压成 200 字以内的摘要，明确要求原样保留数字与编号；③ 提升裁剪粒度：改为「保留首轮 + 最近 N 轮」，很多任务的关键约束就在首轮；④ 提示模型主动追问：在 system 里声明「缺少必要信息时先询问，不要猜」；⑤ 前端配合：把已确认的订单号作为结构化字段随请求发送，而不是依赖模型从历史里翻。最稳的是 ① 与 ⑤：把「必须记住的事实」从自然语言历史里挪到结构化字段，就不再受窗口大小影响。"},
                        "explanation": "根因是「重要事实被当成普通历史裁掉了」；解法不是加预算，而是把关键信息提升为不参与裁剪的结构化状态。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-16-lesson-04",
                "objectives": """1. 能开启 `stream: true` 并逐行解析 `data:` 帧；
2. 能在遇到 `[DONE]` 时正确结束，在坏行上跳过而不中断整条流；
3. 能把增量以 SSE 形式透传给前端，并设置防缓冲响应头；
4. 能处理「已输出一部分后中断」的情况，避免重复内容。""",
                "why_learn": """同样一段回答，等 12 秒一次性出现，和边生成边出现，用户感受完全不同。
流式不是优化项，而是对话类产品的默认交互方式。""",
                "concepts": """**`stream: true`**：请求体加这个字段，响应变成 `text/event-stream`。
**帧格式**：每行以 `data:` 开头，空行分隔；最后一条是 `data: [DONE]`。
**增量字段**：`choices[0].delta.content`，可能为空（首帧只带 `role`）。
**容错**：坏行 `json.loads` 失败就跳过；`[DONE]` 用 `return` 而不是 `break` 更明确。
**透传**：后端用 `StreamingResponse` 原样转发，前端用 `EventSource` 或 `fetch` 读取。
**防缓冲**：`X-Accel-Buffering: no` 与 `Cache-Control: no-cache`，避免代理攒够一批才发。
**中断**：客户端断开时生成器会被关闭，要保证 `with` 上下文能释放连接。""",
                "plain": """流式像听人边想边说：第一句出来得很快，你能立刻判断方向对不对。
一次性返回则像等对方写完一整封信再寄过来，中途你完全不知道进展。
代价是每一小段都要处理，断了还得想清楚「已经说出去的部分」怎么办。""",
                "syntax": """**客户端补两个方法**

```python
@property
def model(self) -> str:
    return self._settings.model

def post_stream(self, path: str, payload: dict) -> httpx.Response:
    return self._client.stream("POST", path, json=payload)
```

**后端透传（SSE）**

```python
@app.post("/chat/stream")
def chat_stream(payload: ChatIn):
    def events():
        yield "event: start\\ndata: {}\\n\\n"
        try:
            for piece in stream_chat(client, payload.messages):
                yield f"event: delta\\ndata: {json.dumps({'text': piece}, ensure_ascii=False)}\\n\\n"
        except LLMError as exc:
            yield f"event: error\\ndata: {json.dumps({'code': exc.code})}\\n\\n"
        finally:
            yield "event: done\\ndata: [DONE]\\n\\n"
    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- 必须用 `stream(...)` 上下文管理器，否则响应体会被整体读入内存。
- `iter_lines()` 处理跨包拼接，不要自己按 `chunk` 切。
- 生产环境的 SSE 不要开 gzip，压缩会破坏逐块下发。""",
                "example_code": '''# app/stream.py
import json
from collections.abc import Iterator

import httpx

from app.client import ChatClient
from app.models import Message


def stream_chat(
    client: ChatClient,
    messages: list[Message],
    temperature: float = 0.7,
) -> Iterator[str]:
    """按块产出增量文本；调用方负责把它们推给前端。"""
    payload = {
        "model": client.model,
        "messages": [message.to_dict() for message in messages],
        "temperature": temperature,
        "stream": True,
    }
    with client.post_stream("/chat/completions", payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                return
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue  # 半包或注释行：跳过，不要中断整条流
            for choice in chunk.get("choices", []):
                piece = (choice.get("delta") or {}).get("content")
                if piece:
                    yield piece


if __name__ == "__main__":
    from app.config import load_settings

    CHUNKS = [
        'data: {"choices":[{"delta":{"content":"你好"}}]}',
        'data: {"choices":[{"delta":{"content":"，我是"}}]}',
        'data: {"choices":[{"delta":{"content":"你的助手。"}}]}',
        "data: [DONE]",
    ]

    def fake(request: httpx.Request) -> httpx.Response:
        body = "\\n\\n".join(CHUNKS) + "\\n\\n"
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, content=body.encode()
        )

    client = ChatClient(load_settings(), transport=httpx.MockTransport(fake))
    pieces = 0
    for piece in stream_chat(client, [Message("user", "你好")]):
        pieces += 1
        print(f"[{pieces}] {piece}")
    client.close()''',
                "code_lines": """1. 函数是生成器（`yield`），调用方每拿一块就可以立刻写给前端，不必等整段完成。
2. 请求体里 `stream: True` 是开关；不开的话服务端会返回一个完整 JSON，`iter_lines` 永远等不到 `data:`。
3. `with client.post_stream(...)` 保证连接在生成器结束或异常时被释放。
4. `line.startswith("data:")` 先过滤心跳与注释行，空行是帧分隔符，直接跳过。
5. `line[len("data:"):].strip()` 去掉前缀与多余空格，注意冒号后面可能有一个空格。
6. `[DONE]` 用 `return` 结束，既终止循环也关闭上下文，比 `break` 语义更明确。
7. `except json.JSONDecodeError: continue`：单帧坏掉不该拖垮整条流，这正是流式最常见的故障点。
8. `(choice.get("delta") or {}).get("content")` 双重兜底：首帧只有 `role`，`content` 可能不存在或为 `None`。
9. `if piece:` 过滤空串，避免把无意义的空增量写进 SSE 帧、白白占用带宽。""",
                "output": """# 运行结果（transport 为本地模拟）
[1] 你好
[2] ，我是
[3] 你的助手。

# 后端转发给前端的 SSE 帧（节选）
event: start
data: {}

event: delta
data: {"text": "你好"}

event: delta
data: {"text": "，我是"}

event: done
data: [DONE]""",
                "mistakes": """- 用 `client.post` 而不是 `client.stream`：响应体一次性读完，流式变成「慢一点的一次性返回」。
- 自己按 `chunk` 切分：多字节汉字会被切在中间，出现乱码。
- 把 `json.loads` 失败当成致命错误直接抛：一条注释行就让整段回答中断。
- SSE 响应忘了 `X-Accel-Buffering: no`：Nginx 攒够缓冲区才下发，用户仍然要等。
- 中断后自动从头重发：用户已经看到的内容会重复一遍。
- 在生成器里做重活（查库、调外部接口）：每块都被拖慢，流式失去意义。""",
                "error_analysis": """现象：后端日志显示流正常结束，前端只收到一大段、或什么都没收到。

按这四层排查：
① 传输层：响应头是否 `text/event-stream`，是否被 gzip 压缩（压缩会攒块）；
② 代理层：Nginx / 网关是否开启了缓冲，`X-Accel-Buffering: no` 是否透传；
③ 应用层：`StreamingResponse` 的生成器里是否有同步阻塞调用，导致事件循环被占满；
④ 前端层：用 `EventSource` 时只能发 GET，POST 场景要用 `fetch` + `ReadableStream` 手动解析。

另一个常见现象是「最后一帧丢了」：生成器在 `finally` 里才发 `done`，
而客户端提前断开时 `finally` 仍会执行，但通道已关闭——所以前端必须准备「没有 done 也要收尾」的逻辑。""",
                "beginner_practice": """1. 往 `CHUNKS` 里插入一条 `data: {"choices":[{"delta":{}}]}` 和一条坏行 `data: {oops`，确认程序不崩且输出仍是完整三块。
2. 把 `[DONE]` 那条删掉，观察生成器如何结束，思考为什么「靠连接关闭」也可以但不够可靠。""",
                "advanced_practice": """实现「可续写」的流式：把已生成的文本累计到 `session.partial`，
当连接中断时记录已发送的长度；用户点击「继续」时，把 `assistant` 的部分内容作为历史，
再发一条「请接着上文继续」的 user 消息。
同时在前端保证：续写时清空旧气泡而不是追加，避免出现两段重复。""",
                "quiz_note": "本节 6 道题：2 道基础理解（开流式的字段、`[DONE]` 的作用）+ 2 道代码阅读（读跳过坏行的逻辑、读 delta 取值）+ 2 道应用练习（补全帧前缀剥离、判断前端收不到增量的原因）。",
                "summary": """流式 = `stream: true` + 逐行读 `data:` + 增量取 `delta.content`。
坏帧跳过、`[DONE]` 结束，这两个容错决定了流的健壮性。
透传要关缓冲，中断要能收尾，前端要能处理「没有 done」。""",
                "next_lesson": "最后补齐错误处理与测试，把项目变成可交付的东西。",
                "knowledge_points": [
                    {
                        "code": "llm-api-16-04",
                        "name": "流式输出与前端透传",
                        "goal": "能把模型增量稳定地转发给调用方，并处理中断与结束。",
                        "minutes": 45,
                        "criteria": "能写出 SSE 解析生成器、FastAPI `StreamingResponse` 端点与防缓冲响应头。",
                        "requires": ["llm-api-16-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-16-04-1",
                        "kp": 0,
                        "title": "统计首字延迟",
                        "description": "在 `stream_chat` 里记录「从发请求到产出第一块」的耗时，并在流结束时打印块数与首字延迟。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''import time


def stream_chat(client, messages, temperature: float = 0.7):
    payload = {
        "model": client.model,
        "messages": [m.to_dict() for m in messages],
        "temperature": temperature,
        "stream": True,
    }
    started = time.monotonic()
    first_at: float | None = None
    pieces = 0
    with client.post_stream("/chat/completions", payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            for choice in chunk.get("choices", []):
                piece = (choice.get("delta") or {}).get("content")
                if piece:
                    if first_at is None:
                        first_at = time.monotonic() - started
                    pieces += 1
                    yield piece
    total = time.monotonic() - started
    print(f"首字 {first_at:.2f}s / 共 {pieces} 块 / 总 {total:.2f}s")''',
                        "explanation": "首字延迟（TTFT）才是用户感知的速度，总耗时只影响结算；两个指标分开记，才能判断瓶颈在排队还是在生成。",
                    },
                    {
                        "code": "llm-ex-16-04-2",
                        "kp": 0,
                        "title": "前端用 POST 怎么接 SSE",
                        "description": "`EventSource` 只支持 GET，而对话需要 POST 发送消息，说明前端该怎么实现。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''用 `fetch` + `ReadableStream` 手动解析：

```javascript
const resp = await fetch("/chat/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ messages }),
});
const reader = resp.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const frames = buffer.split("\\n\\n");
  buffer = frames.pop();            // 最后一段可能不完整，留到下次
  for (const frame of frames) {
    // 解析 "event: xxx" 与 "data: yyy"
  }
}
```

要点：
① 必须保留 `buffer` 的残余，网络分包可能把一帧切成两半；
② 用 `TextDecoder(..., {stream: true})` 处理多字节字符跨包；
③ 不要在 `done` 后才渲染，边读边渲染才有意义；
④ 组件卸载或用户点「停止」时调用 `reader.cancel()`，同时通知后端停止生成。''',
                        "explanation": "`EventSource` 的限制在于只能 GET 且不能带自定义头；对话场景必须用流式 `fetch`，而正确性是靠「缓冲区 + 增量解码」保证的。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-16-04-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要开启流式返回，请求体里需要加的字段是？",
                        "options": [
                            ("A", "`\"stream\": true`"),
                            ("B", "`\"async\": true`"),
                            ("C", "`\"chunked\": 1`"),
                            ("D", "`\"sse\": \"on\"`"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "兼容协议用 `stream` 布尔字段开启；其余写法不在协议内，会被忽略。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-04-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "判断：流式响应里每一帧的 `delta.content` 都一定有值。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "首帧通常只带 `role`，结束帧也可能只带 `finish_reason`；所以取值时要兜底并过滤空串。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-04-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`except json.JSONDecodeError: continue` 这段的作用是？",
                        "options": [
                            ("A", "跳过坏帧或注释行，避免一帧异常中断整条流"),
                            ("B", "重试解析失败的那一帧"),
                            ("C", "把错误发给前端"),
                            ("D", "关闭连接"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "流式里出现空行、心跳、非 JSON 内容是常态；容错到「单帧失败不影响整体」才够稳。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-04-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`(choice.get(\"delta\") or {}).get(\"content\")` 为什么要先 `or {}`？",
                        "options": [
                            ("A", "`delta` 可能为 `None`，直接 `.get` 会抛 `AttributeError`"),
                            ("B", "为了提升字典查找速度"),
                            ("C", "为了把 `None` 转成字符串"),
                            ("D", "为了兼容 Python 3.8"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`None.get(...)` 不存在；`or {}` 把空值统一成空字典，后面的 `.get` 才安全。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-04-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全代码，取出以 `data:` 开头那行的实际内容。横线处应填什么？\n\n```python\nif line.startswith(\"data:\"):\n    data = ____\n```",
                        "options": [
                            ("A", "line[len(\"data:\"):].strip()"),
                            ("B", "line.split(\":\")[0]"),
                            ("C", "line[1:]"),
                            ("D", "line.replace(\"data\", \"\")"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "按固定前缀长度切片最稳；`split(\":\")[0]` 取到的是 `data` 本身，`line[1:]` 会留下 `ata:`。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-16-04-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "上线后用户反馈「还是一次性全部出现」，你按什么顺序定位？",
                        "answer": {"value": "① 先看请求：抓包确认请求体里 `stream` 为 `true`，且后端确实调用了 `client.stream` 而不是 `client.post`；② 看响应头：内容类型是否为 `text/event-stream`，是否被 gzip 压缩（压缩会攒块），是否缺少 `X-Accel-Buffering: no`；③ 看代理：Nginx `proxy_buffering` 是否开启、网关是否有统一缓冲或 WAF 聚合；④ 看应用：生成器里是否有同步阻塞调用（同步数据库、同步 HTTP），把事件循环卡住；⑤ 看前端：是否等 `done` 才渲染、是否用了 `EventSource` 而实际是 POST 接口；⑥ 用 `curl -N` 直接打后端接口，若 curl 是逐块输出，问题就在代理或前端，而不在后端。"},
                        "explanation": "逐层排除的关键是先区分「后端没流」与「流被中途拦住」，`curl -N` 是最快的分界点。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-16-lesson-05",
                "objectives": """1. 能把状态码统一翻译成带 `retryable` 的错误对象；
2. 能在客户端里实现有限次重试，并对不可重试错误立即失败；
3. 能用 `MockTransport` 写出不依赖网络与真 Key 的测试；
4. 能整理出可交付的配置、依赖与启动说明。""",
                "why_learn": """功能写完只是「能跑」，加上错误处理与测试才叫「能交付」。
没有测试的项目，每次改配置都要靠手工点一遍，没人敢动第二行。""",
                "concepts": """**错误分类**：`STATUS_MAP` 把状态码映射成「对外码 / 文案 / 是否可重试」。
**单一异常类型**：`LLMError` 带 `code`、`retryable`、`detail`，上层只 catch 一种。
**有限重试**：只在 `retryable` 为真时重试，次数与退避都有上限。
**可测性**：`MockTransport` 按脚本返回响应，测试覆盖成功、401、429 重试三条路径。
**断言重点**：错误码、`retryable` 标记、调用次数、以及「配置不泄漏 Key」。
**交付清单**：`.env.example`、`requirements.txt`、启动命令、健康检查。""",
                "plain": """测试像出门前的检查清单：钥匙、手机、钱包，一样一样确认过再关门。
没有清单也能出门，但总有一次会在楼下发现忘带东西。
清单的价值不是「证明你细心」，而是让每一次出门都一样可靠。""",
                "syntax": """**错误对象**

```python
class LLMError(RuntimeError):
    def __init__(self, code, message, retryable=False, detail=""):
        ...
```

**分类与重试**

```python
response = self._client.post("/chat/completions", json=payload)
if response.status_code >= 400:
    raise classify_response(response)
```

**测试骨架**

```python
def make_client(handler):
    return ChatClient(SETTINGS, transport=httpx.MockTransport(handler))
```

**交付清单**

```text
requirements.txt   httpx / fastapi / uvicorn / pytest
.env.example       LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
启动：uvicorn app.main:app --port 8000
自检：python -m app.config
测试：pytest -q
```

- 测试里用占位 Key，绝不引用真实值。
- 敏感断言要包含「`repr` 不含 Key」这一条，防止有人改回默认 `__repr__`。""",
                "example_code": '''# tests/test_client.py
import httpx
import pytest

from app.client import ChatClient
from app.config import Settings
from app.errors import LLMError
from app.models import Message

# 测试专用占位值，不是真实凭据；绝不提交任何真实 Key
FAKE_KEY = "test-key-not-a-secret"
SETTINGS = Settings(api_key=FAKE_KEY, base_url="https://api.example.com/v1", model="chat-small")


def make_client(handler) -> ChatClient:
    return ChatClient(SETTINGS, transport=httpx.MockTransport(handler))


def test_complete_returns_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "你好"}}]})

    with make_client(handler) as client:
        assert client.complete([Message("user", "hi")]) == "你好"


def test_401_raises_invalid_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"type": "invalid_api_key"}})

    with make_client(handler) as client:
        with pytest.raises(LLMError) as info:
            client.complete([Message("user", "hi")])
    assert info.value.code == "invalid_key"
    assert info.value.retryable is False


def test_retry_on_429_then_success() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"error": {"message": "slow down"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": "好了"}}]})

    with make_client(handler) as client:
        assert client.complete_with_retry([Message("user", "hi")]) == "好了"
    assert calls["n"] == 2


def test_repr_does_not_leak_key() -> None:
    assert FAKE_KEY not in repr(SETTINGS)''',
                "code_lines": """1. `SETTINGS` 在模块级构造一次，用占位 Key；`base_url` 指向 example.com，永远不会打到真实服务。
2. `make_client` 把「构造 + 注入 transport」收成一个函数，三条测试共用，改签名只改一处。
3. `handler` 是普通函数，接收 `request` 返回 `Response`，这就是 `MockTransport` 的契约。
4. `test_complete_returns_content` 验证「最小成功路径」：请求发出去了，返回值取对了。
5. `pytest.raises(LLMError)` 联合 `info.value.code` 断言，比只断言「抛异常」更能锁住行为。
6. `retryable is False` 用 `is` 而不是 `==`：这是个布尔开关，类型错了也要能被发现。
7. `calls` 计数器验证「重试确实发生了一次」，这是重试逻辑唯一的可观测证据。
8. `test_repr_does_not_leak_key` 是一条防回归的哨兵：谁把 `repr=False` 去掉，它立刻失败。""",
                "output": """# 运行
$ pytest -q
....                                                                     [100%]
4 passed in 0.55s

# 交付前自检
$ python -m app.config
Settings(base_url='https://api.example.com/v1', model='chat-small', key=***)""",
                "mistakes": """- 测试里连真实接口：跑一次要花钱、要网络，CI 上必然不稳定。
- 只断言「没抛异常」：错误码与可重试标记全都没锁住，改坏了也不知道。
- 用 `time.sleep` 真实等待重试：测试变慢，且容易在 CI 上超时；把 `BASE_DELAY` 调成 0 或注入假时钟。
- 测试里写真实 Key「方便调试」：泄漏风险直接进版本库。
- 只测成功路径：真实故障全在 401 与 429 上，这部分不测等于没测。""",
                "error_analysis": """`pytest: error: unrecognized arguments` 或 `ModuleNotFoundError: No module named 'app'`

前者通常是没装 `pytest` 或用了别的解释器；后者是工作目录不对——`pytest` 需要能把项目根目录加进 `sys.path`。

三种稳定做法：
① 在项目根目录执行 `python -m pytest`，`-m` 会把当前目录加入 `sys.path`；
② 加 `pyproject.toml` 的 `[tool.pytest.ini_options] pythonpath = ["."]`；
③ 装成可编辑包 `pip install -e .`。

不推荐 `conftest.py` 里手写 `sys.path.insert`：它掩盖了「包结构本身不对」的问题，
换台机器或换个执行目录就会再次失败。""",
                "beginner_practice": """1. 增加一条测试：连续两次 429 后返回 200，断言 `calls["n"] == 3`，验证重试次数上限。
2. 增加一条测试：500 响应，断言最终抛出 `LLMError` 且 `retryable` 为 `True`。""",
                "advanced_practice": """把重试的等待时间变成可注入的：给 `ChatClient` 增加 `sleep=time.sleep` 参数，
测试时传入一个记录调用的假函数，断言「退避序列为 0.5 的幂次且带抖动」。
再补一条端到端测试：从 `load_settings` 到 `stream_chat` 全链路走 `MockTransport`，
验证「配置 → 请求 → 增量 → 错误」四个环节能串起来。""",
                "quiz_note": "本节 6 道题：2 道基础理解（`MockTransport` 的作用、为什么要断言错误码）+ 2 道代码阅读（读 raises 断言、读计数器）+ 2 道应用练习（补全异常断言、设计交付前检查）。",
                "summary": """错误先分类再重试，不可重试的错误立即失败。
测试用 `MockTransport`，覆盖成功、配置错误、限流重试三条路径。
交付清单里必须包含「配置自检」与「`repr` 不泄漏」这两条硬检查。""",
                "next_lesson": "课程到此结束。下一步可以进入 LangGraph，把单轮调用组织成可恢复的多步 Agent。",
                "knowledge_points": [
                    {
                        "code": "llm-api-16-05",
                        "name": "错误处理、测试与交付",
                        "goal": "能让项目在故障下可预期，并用测试锁住关键行为。",
                        "minutes": 45,
                        "criteria": "能写出带 `retryable` 的错误分类、有限重试，以及不依赖网络的 `MockTransport` 测试。",
                        "requires": ["llm-api-16-04"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-16-05-1",
                        "kp": 0,
                        "title": "补一条流式测试",
                        "description": "用 `MockTransport` 返回三段 SSE 数据，断言 `stream_chat` 拼接出的文本等于完整句子，且块数为 3。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def test_stream_joins_chunks() -> None:
    chunks = [
        'data: {"choices":[{"delta":{"content":"你好"}}]}',
        'data: {"choices":[{"delta":{"content":"，世界"}}]}',
        'data: {"choices":[{"delta":{"content":"。"}}]}',
        "data: [DONE]",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        body = "\\n\\n".join(chunks) + "\\n\\n"
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body.encode())

    with make_client(handler) as client:
        pieces = list(stream_chat(client, [Message("user", "hi")]))
    assert len(pieces) == 3
    assert "".join(pieces) == "你好，世界。"''',
                        "explanation": "流式测试要同时验证「块数」与「拼接结果」：只验证拼接会漏掉「一次性吐出全部」这种退化为非流式的情况。",
                    },
                    {
                        "code": "llm-ex-16-05-2",
                        "kp": 0,
                        "title": "交付前检查清单",
                        "description": "列出这个助手交付前必须逐项确认的检查点，并说明每项对应什么风险。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 配置：`python -m app.config` 能打印脱敏配置；风险是部署时缺变量。
② 密钥：仓库里 `git grep` 搜不到真实 Key，`.env` 在 `.gitignore` 中；风险是泄漏。
③ 网络：`base_url` 为 https，超时四项都设置；风险是明文传输与线程挂死。
④ 调用：一次性与流式各跑通一次，`usage` 能取到；风险是接口对不上。
⑤ 上下文：连续 10 轮不超限，裁剪后结构完整；风险是长会话报错。
⑥ 错误：401、429、超时三种情况都有明确文案；风险是用户看到原始堆栈。
⑦ 测试：`pytest -q` 全绿，且不依赖网络；风险是回归无人守。
⑧ 观测：日志含 `request_id`、模型名、耗时、token 用量，不含 Key 与完整 prompt；风险是故障无法定位。
⑨ 依赖：`requirements.txt` 版本可复现，Python 版本写进 README；风险是换机器跑不起来。
⑩ 降级：主模型不可用时有备用模型或明确提示；风险是整体不可用。''',
                        "explanation": "清单的价值在于「每项都能对应一个具体故障」；列不出风险的检查项，通常是多余的仪式。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-16-05-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`httpx.MockTransport` 在测试里的主要作用是？",
                        "options": [
                            ("A", "拦截请求并按脚本返回响应，使测试不依赖网络与真实凭据"),
                            ("B", "加速真实网络请求"),
                            ("C", "自动生成测试用例"),
                            ("D", "缓存上一次的响应"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "它替换传输层，让「发请求」这一步完全可控，从而能稳定复现 401、429、流式等场景。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-05-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "判断：测试只要能跑通成功路径就够了，异常路径上线前手工点一遍即可。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "真实故障几乎都在异常路径；手工点无法覆盖 429、超时、半包中断这些场景，也留不下回归防线。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-16-05-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`assert info.value.retryable is False` 用 `is` 而不是 `==`，好处是？",
                        "options": [
                            ("A", "同时锁住取值与类型，`0` 或 `\"False\"` 这类错误赋值也会被发现"),
                            ("B", "运行速度更快"),
                            ("C", "可以避免 `AttributeError`"),
                            ("D", "兼容旧版本 Python"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`0 == False` 为真，`is` 判断的是同一对象；布尔开关用 `is` 断言更严格。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-05-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`test_retry_on_429_then_success` 里 `calls` 计数器断言的是什么？",
                        "options": [
                            ("A", "重试确实发生了一次，总请求次数为 2"),
                            ("B", "响应内容是否正确"),
                            ("C", "超时时间是否生效"),
                            ("D", "Key 是否被正确读取"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "返回值断言证明「最终成功」，计数器断言证明「过程走了重试」；两者缺一，重试逻辑都可能被改坏而无人察觉。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-16-05-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全断言，验证 401 抛出的错误不可重试。横线处应填什么？\n\n```python\nassert info.value.code == \"invalid_key\"\nassert info.value.______ is False\n```",
                        "options": [("A", "retryable"), ("B", "detail"), ("C", "args"), ("D", "message")],
                        "answer": {"value": "A"},
                        "explanation": "`retryable` 决定上层是否继续重试；认证失败必须为 `False`，否则会白重试浪费额度。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-16-05-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "这个助手要交给另一个团队接手，你会写哪几段文档？每段解决什么问题？",
                        "answer": {"value": "① 一页 README：项目做什么、怎么装依赖、怎么配环境变量、怎么启动、怎么跑测试——解决「拿到手能不能跑起来」；② 配置说明：每个环境变量的含义、是否必填、默认值、取值范围——解决「换环境怎么改」；③ 接口说明：对外暴露的路由、请求与响应结构、错误码表——解决「前端怎么对接」；④ 架构与取舍：六层模块各自职责、为什么这样分层、已知限制（如无持久化、单进程限流）——解决「后面怎么改」；⑤ 运维手册：日志在哪、关键指标（TTFT、错误率、token 用量）、常见故障与处置步骤——解决「出问题怎么办」；⑥ 变更记录：版本、改动点、配置变更——解决「升级时要注意什么」。文档不必长，但每一段都要能回答一个具体问题。"},
                        "explanation": "交接文档的核心是「减少提问次数」：能自己查到答案的地方，就不该靠人问。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
