"""Python 进阶与工程实践：第 9—10 章（项目目录结构、日志与配置）。"""

CHAPTERS: list[dict] = [
    {
        "code": "python-advanced-09",
        "title": "项目目录结构",
        "description": "用 src 布局与包划分让项目能被别人接手。",
        "order_index": 9,
        "lessons": [
            {
                "code": "python-advanced-09-lesson-01",
                "objectives": """1. 说清 `__init__.py` 与普通目录的区别；
2. 会按职责拆分模块，避免循环导入；
3. 理解 src 布局要解决的问题；
4. 能把入口、配置、源码、测试分开摆放。""",
                "why_learn": """项目超过十个文件后，「东西放哪」就决定了维护成本。
随手在根目录堆脚本，半年后没人说得出哪个是入口；模块互相 import 又容易踩循环导入。
结构不是审美问题，它决定了改一处要动几个文件。""",
                "concepts": """**包** 是带 `__init__.py` 的目录（命名空间包可省略，但项目内约定显式写）。
**模块** 是一个 `.py` 文件；包内的模块用 `from package.module import name` 导入。
**循环导入** 指 A 导入 B、B 又导入 A，Python 会在半初始化状态下报错。
**src 布局** 把源码放在 `src/项目名/` 下，测试只安装后导入，避免「当前目录恰好能 import」的假象。
**分层** 常见为 `api / services / repositories / models`，上层依赖下层，不反向。""",
                "plain": """目录结构像办公室的工位安排：前台接待、财务、仓储各在一处，
找人不用满楼跑。如果所有东西堆在一个房间，短期方便，人一多就没人知道锤子放哪。
src 布局则像「仓库统一发货」：必须先正式入库（安装）才能取货，
防止你误把桌上的样品当成正式库存。""",
                "syntax": """```text
project/
├── pyproject.toml
├── README.md
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py          # 入口
│       ├── core/            # 配置、日志
│       ├── api/             # 接口层
│       ├── services/        # 业务层
│       ├── repositories/    # 数据访问
│       └── models/          # 数据结构
└── tests/
    └── test_main.py
```
导入规则：上层可以导入下层，下层不能导入上层；同层之间尽量通过接口调用。""",
                "example_code": '''from dataclasses import dataclass, field


@dataclass
class Task:
    title: str
    done: bool = False


class InMemoryTaskRepo:
    """数据访问层：只关心怎么存，不关心业务规则。"""

    def __init__(self) -> None:
        self._items: list[Task] = []

    def add(self, task: Task) -> Task:
        self._items.append(task)
        return task

    def list_all(self) -> list[Task]:
        return list(self._items)


class TaskService:
    """业务层：只依赖仓储接口，不直接碰存储细节。"""

    def __init__(self, repo: InMemoryTaskRepo) -> None:
        self.repo = repo

    def create(self, title: str) -> Task:
        if not title.strip():
            raise ValueError("标题不能为空")
        return self.repo.add(Task(title=title))

    def pending_ratio(self) -> float:
        items = self.repo.list_all()
        if not items:
            return 0.0
        pending = sum(1 for task in items if not task.done)
        return pending / len(items)


service = TaskService(InMemoryTaskRepo())
service.create("写周报")
service.create("交报表")
print(service.pending_ratio())

try:
    service.create("   ")
except ValueError as exc:
    print("校验失败：", exc)''',
                "code_lines": """1. `@dataclass` 自动生成 `__init__` 与 `__repr__`，适合只装数据的小对象。
2. `InMemoryTaskRepo` 属于数据访问层，对外只暴露 add / list_all 两个动作。
3. `list_all` 返回 `list(self._items)` 副本，防止调用方直接改内部列表。
4. `TaskService` 只接收一个仓储对象，不关心它是内存还是数据库实现。
5. `create` 先校验标题，再交给仓储保存——业务规则集中在服务层。
6. `pending_ratio` 是纯计算，输入来自仓储，便于单独测试。
7. 组装发生在最外层：`TaskService(InMemoryTaskRepo())`，这叫依赖注入。
8. 最后验证空标题被拦住，说明校验确实在服务层生效。""",
                "output": """1.0
校验失败： 标题不能为空""",
                "mistakes": """- 所有代码堆在 `main.py`，改一个函数要滚动两千行。
- 仓储层反过来 import 服务层，形成循环导入。
- 根目录放一个 `utils.py`，什么都往里塞，最后无人敢删。
- 测试直接靠当前目录导入源码，CI 里安装后路径不同就失败。
- 包名与标准库同名（如 `json.py`），导致导入被遮蔽。""",
                "error_analysis": """`ImportError: cannot import name 'X' from partially initialized module 'app.a' (most likely due to a circular import)`
—— A 与 B 互相导入。把共享部分抽到第三个模块，或把导入移到函数内部延迟执行。

`ModuleNotFoundError: No module named 'app'`
—— 在 src 布局下没安装项目就运行脚本。用 `pip install -e .` 或设置 `PYTHONPATH=src`。

`ImportError: attempted relative import with no known parent package`
—— 直接用 `python src/app/services/task.py` 跑包内文件。应通过入口模块或 `-m` 方式运行。""",
                "beginner_practice": """1. 按本节的目录结构建一个空项目：`src/app/{core,api,services,repositories,models}`，
   每层放一个 `__init__.py` 与一个占位模块。
2. 在 `main.py` 写一个 `main()`，打印各层模块名，验证导入链路通。""",
                "advanced_practice": """把 `InMemoryTaskRepo` 换成文件存储实现（读写 JSON），要求 `TaskService` 一行不改。
说明这次替换验证了分层的哪个性质，以及如果服务层直接读写文件会付出什么代价。""",
                "quiz_note": "本节 6 道题：重点考循环导入识别与分层依赖方向。",
                "summary": """包用 `__init__.py` 标记，导入按 `包.模块` 路径；
分层遵循「上层依赖下层」，服务层只依赖仓储接口；
src 布局强制先安装再导入，避免本地路径假象。""",
                "next_lesson": "下一节讲日志与配置：把 print 换成可检索的日志，把硬编码换成可校验的配置。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-09-01",
                        "name": "包结构、导入与分层",
                        "goal": "能按职责拆分模块、避免循环导入，并用 src 布局组织项目。",
                        "minutes": 35,
                        "criteria": "能独立搭出分层目录，并解释为什么服务层不能反向依赖接口层。",
                        "requires": ["python-advanced-08-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-09-01-1",
                        "kp": 0,
                        "title": "搭一个分层骨架",
                        "description": "创建 src 布局项目骨架（core/api/services/repositories/models + tests），并写 main() 验证各层可导入。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''src/app/main.py
--------------
from app.repositories.task_repo import InMemoryTaskRepo
from app.services.task_service import TaskService


def main() -> None:
    service = TaskService(InMemoryTaskRepo())
    print(service.create("写周报"))


if __name__ == "__main__":
    main()''',
                        "explanation": "入口只做组装，不写业务逻辑；各层通过包路径导入，`python -m app.main` 即可运行。",
                    },
                    {
                        "code": "adv-ex-09-01-2",
                        "kp": 0,
                        "title": "替换存储实现",
                        "description": "用 JSON 文件实现 TaskRepo，保持 TaskService 不变；说明替换验证了分层的哪个性质。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''import json
from pathlib import Path


class JsonTaskRepo:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._items = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    def add(self, task):
        self._items.append({"title": task.title, "done": task.done})
        self.path.write_text(json.dumps(self._items, ensure_ascii=False), encoding="utf-8")
        return task

    def list_all(self):
        return [Task(title=item["title"], done=item["done"]) for item in self._items]''',
                        "explanation": "服务层没变说明它只依赖仓储的行为契约；若服务层直接读写文件，换存储就要改业务代码并重测全部逻辑。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-09-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "关于 `__init__.py`，下列说法正确的是？",
                        "options": [
                            ("A", "它让所在目录被识别为包，并可在导入包时执行初始化代码"),
                            ("B", "它是 Python 解释器的可执行入口"),
                            ("C", "没有它任何目录都无法导入"),
                            ("D", "它必须是空文件"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "常规包里 __init__.py 标记包并执行初始化；命名空间包可以没有它，所以 C 太绝对。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-09-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些做法有助于避免循环导入？（多选）",
                        "options": [
                            ("A", "把共享的数据结构抽到独立模块"),
                            ("B", "在函数内部延迟导入"),
                            ("C", "让下层模块反向导入上层以复用逻辑"),
                            ("D", "用类型检查专用的条件导入处理仅注解用途的依赖"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "反向依赖是循环导入的主要来源，所以 C 错；其余三项都是常见解法。",
                        "difficulty": "advanced",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-09-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面的结构会产生什么问题？
# app/services/user_service.py
from app.api.user_api import build_response

# app/api/user_api.py
from app.services.user_service import UserService''',
                        "answer": {
                            "reference": "两个模块互相导入，形成循环导入。启动时先导入 user_service，它需要 user_api，而 user_api 又回头导入还没初始化完的 user_service，抛 partially initialized module。",
                            "keywords": ["循环导入", "partially initialized", "相互依赖"],
                        },
                        "explanation": "服务层依赖接口层是方向错误；应让接口层调用服务层，服务层不感知 HTTP 结构。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-09-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "在 src 布局下，不安装项目、直接在项目根目录运行 `python src/app/main.py` 也能稳定导入 app 包。",
                        "answer": {"value": False},
                        "explanation": "直接运行文件时 sys.path 指向该文件所在目录，`app` 包本身不可见，通常需要安装或设置 PYTHONPATH。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-09-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写出 src 布局下常见的四层目录与各自职责（各一行说明）。",
                        "answer": {
                            "reference": """src/app/api        接口层：解析请求、返回响应
src/app/services   业务层：校验与业务规则
src/app/repositories 数据访问层：只负责读写存储
src/app/models     数据结构：表模型、Pydantic 模型""",
                            "keywords": ["api", "services", "repositories", "models"],
                        },
                        "explanation": "分层的核心是依赖方向单一：接口→业务→数据访问，任何一层都不反向依赖。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-09-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说「服务层不要直接读写文件或数据库」？请从测试与替换两个角度说明。",
                        "answer": {
                            "reference": "测试角度：服务层直接读写真实存储，测业务规则就必须准备真实文件或数据库，慢且互相污染。替换角度：存储方式一变（内存换 SQLite、换远程库），业务代码要跟着改并重测。把存储收进仓储后，服务层只依赖几个方法，测试可换成假实现，替换存储也不动业务逻辑。",
                            "keywords": ["测试隔离", "替换", "仓储", "假实现"],
                        },
                        "explanation": "两个角度都指向「降低耦合」，能说清具体收益即可。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    {
        "code": "python-advanced-10",
        "title": "日志与配置",
        "description": "把 print 换成可检索的日志，把硬编码换成可校验的配置。",
        "order_index": 10,
        "lessons": [
            {
                "code": "python-advanced-10-lesson-01",
                "objectives": """1. 说清 Logger / Handler / Formatter 的分工；
2. 会按环境设置日志级别与输出目标；
3. 会用环境变量外置配置，区分开发与生产；
4. 会在启动时校验配置，缺失就快速失败。""",
                "why_learn": """用 print 打日志，线上出问题时既分不清严重程度，也没法按模块过滤，
更没法关掉。硬编码的数据库地址则让同一份代码不能跑在两个环境里。
日志与配置是「能上线」和「只能在自己机器上跑」的分界线。""",
                "concepts": """**Logger** 是记录入口，按名字分层级（`app.services.task` 是 `app` 的子级）。
**Handler** 决定日志去哪：控制台、文件、网络。
**Formatter** 决定长什么样：时间、级别、模块名、消息。
**级别** 从低到高：DEBUG、INFO、WARNING、ERROR、CRITICAL，设置某个级别后只输出不低于它的日志。
**配置外置**：把可变参数放环境变量或配置文件，代码只读取，不写死。
**启动即失败**：必需配置缺失时立刻报错退出，而不是运行到一半才崩。""",
                "plain": """日志像医院的病历：谁、什么时候、做了什么、结果如何，一条条记清楚，事后能查。
print 像随口说一句，说完就散了。
配置像家里的总电闸：不同房间（环境）用不同设置，缺了关键开关就该当场跳闸，
而不是等电器烧了才发现。""",
                "syntax": """```python
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("服务启动")


def load_config() -> dict:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("缺少必需配置：DATABASE_URL")
    return {"database_url": database_url}
```""",
                "example_code": '''import logging
import os

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

logger = logging.getLogger("app.task")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
logger.addHandler(handler)
logger.propagate = False

REQUIRED_KEYS = ("DATABASE_URL", "LOG_LEVEL")


def load_config(env=None):
    env = env or os.environ
    missing = [key for key in REQUIRED_KEYS if not env.get(key)]
    if missing:
        raise RuntimeError("缺少必需配置：" + "、".join(missing))
    level_name = env.get("LOG_LEVEL", "INFO").upper()
    if level_name not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise RuntimeError(f"LOG_LEVEL 取值非法：{level_name}")
    return {"database_url": env["DATABASE_URL"], "log_level": level_name}


logger.debug("准备加载配置")
try:
    config = load_config({"DATABASE_URL": "", "LOG_LEVEL": "verbose"})
except RuntimeError as exc:
    logger.error("配置校验失败：%s", exc)

config = load_config({"DATABASE_URL": "sqlite:///data.db", "LOG_LEVEL": "debug"})
logger.setLevel(config["log_level"])
logger.info("配置加载完成：%s", config["database_url"])
logger.debug("调试信息只在 DEBUG 级别可见")''',
                "code_lines": """1. `logging.getLogger("app.task")` 按模块命名，日志里能直接看出是哪个模块打的。
2. `setLevel(logging.DEBUG)` 决定这个 logger 的最低输出级别。
3. `StreamHandler` 把日志打到控制台；换成 FileHandler 就写文件，Formatter 决定格式。
4. `logger.propagate = False` 阻止日志再冒泡到根 logger，避免重复打印。
5. `REQUIRED_KEYS` 列出必需配置，缺任何一项都直接失败，而不是用默认值硬撑。
6. `load_config` 允许注入 env 字典，这样测试不需要真的改环境变量。
7. `missing` 一次性收集所有缺失项，比逐个报错更省排查时间。
8. 第一次调用故意传空值与非法级别，验证两类校验都会拦住并记录 ERROR。
9. `logger.setLevel(config["log_level"])` 用配置值覆盖级别，运行时就能按环境调整。""",
                "output": """14:22:31 DEBUG app.task 准备加载配置
14:22:31 ERROR app.task 配置校验失败：缺少必需配置：DATABASE_URL
14:22:31 INFO app.task 配置加载完成：sqlite:///data.db
14:22:31 DEBUG app.task 调试信息只在 DEBUG 级别可见""",
                "mistakes": """- 用 `logging.basicConfig` 后又在别处 addHandler，导致同一条日志打印两遍。
- 用 f-string 拼日志消息，级别被过滤时也照样执行了格式化开销。
- 把密码、Token 打进日志。
- 生产环境仍用 DEBUG 级别，日志量暴涨还可能泄露敏感信息。
- 配置缺失时用 `or "localhost"` 兜底，把错误藏到运行期。""",
                "error_analysis": """日志重复输出两行
—— 同时配置了根 logger 与子 logger 的 handler，且 propagate 为 True。设 `propagate = False` 或统一在一处配置。

日志一条都不输出
—— 级别设置过高（如 WARNING）而代码用 info；或 logger 没挂 handler 且根 logger 被禁用。

`KeyError: 'DATABASE_URL'`
—— 直接下标取环境变量，缺失就崩。应先校验再取，或给出明确的报错信息。

`ValueError: Unable to configure formatter 'default'`
—— 格式串写错，比如引用了不存在的字段。""",
                "beginner_practice": """1. 把示例改成同时输出到控制台与 `app.log` 文件，验证两边都能看到。
2. 用 `logging.getLogger("app.task.sub")` 打一条日志，观察 name 字段的层级关系。""",
                "advanced_practice": """设计一份启动配置：必需项 `DATABASE_URL`、可选项 `LOG_LEVEL`（默认 INFO）、
`DEBUG`（默认 false）。要求非法值给出具体错误信息，并写三个用例覆盖成功与两类失败。""",
                "quiz_note": "本节 6 道题：重点考级别过滤语义与「配置缺失就失败」的理由。",
                "summary": """Logger 记录、Handler 决定去向、Formatter 决定格式；
级别控制输出多少，按环境调整；配置从环境变量读取并在启动时校验；
记住：**配置错误要当场炸，不要带到运行期**。""",
                "next_lesson": "本课程到此结束，接下来进入「数据库与 Python 数据库开发」，把数据从内存换成真正的数据库。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-10-01",
                        "name": "logging 与配置管理",
                        "goal": "能配置分级日志并外置配置，在启动时校验必需项。",
                        "minutes": 35,
                        "criteria": "能写出按环境调整级别的日志配置，并让缺失配置在启动时报错。",
                        "requires": ["python-advanced-09-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-10-01-1",
                        "kp": 0,
                        "title": "双通道日志",
                        "description": "配置一个 logger，同时输出到控制台与 app.log，格式含时间、级别、模块名与消息。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''import logging

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%H:%M:%S"
)

console = logging.StreamHandler()
console.setFormatter(formatter)

file_handler = logging.FileHandler("app.log", encoding="utf-8")
file_handler.setFormatter(formatter)

logger.addHandler(console)
logger.addHandler(file_handler)
logger.propagate = False
logger.info("双通道日志已就绪")''',
                        "explanation": "两个 handler 共用一个 formatter；propagate 关掉可避免根 logger 再输出一遍。",
                    },
                    {
                        "code": "adv-ex-10-01-2",
                        "kp": 0,
                        "title": "启动配置校验",
                        "description": "实现 load_config：必需 DATABASE_URL，可选 LOG_LEVEL 与 DEBUG，非法值给出具体错误，覆盖成功与两类失败用例。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def load_config(env):
    database_url = env.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("缺少必需配置：DATABASE_URL")

    level = env.get("LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise RuntimeError(f"LOG_LEVEL 取值非法：{level}")

    debug_raw = env.get("DEBUG", "false").lower()
    if debug_raw not in {"true", "false"}:
        raise RuntimeError(f"DEBUG 必须是 true/false：{debug_raw}")

    return {
        "database_url": database_url,
        "log_level": level,
        "debug": debug_raw == "true",
    }''',
                        "explanation": "三类错误分别报错，信息里带上实际值，运维看到日志就知道该改哪一项。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-10-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "Logger、Handler、Formatter 三者的分工是？",
                        "options": [
                            ("A", "Logger 决定格式，Handler 记录，Formatter 输出"),
                            ("B", "Logger 是记录入口，Handler 决定去向，Formatter 决定格式"),
                            ("C", "三者功能相同，可以互相替代"),
                            ("D", "Handler 是入口，Logger 决定格式"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "logger.info 触发记录，handler 决定写到哪里，formatter 决定输出长什么样。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-10-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "把配置放在环境变量里，好处有哪些？（多选）",
                        "options": [
                            ("A", "同一份代码可部署到不同环境"),
                            ("B", "敏感信息不进代码仓库"),
                            ("C", "配置写错时代码会自动修正"),
                            ("D", "便于在容器与 CI 中注入不同配置"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "环境变量不会自动纠正错误值，所以 C 错；其余三项都是外置配置的实际收益。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-10-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面几行会输出几条日志？
import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("app")
log.info("a")
log.warning("b")
log.error("c")''',
                        "answer": {
                            "reference": "输出 2 条：b 与 c。级别设为 WARNING，info 低于该级别被过滤。",
                            "keywords": ["2 条", "b", "c", "过滤"],
                        },
                        "explanation": "级别过滤在记录阶段就生效，低于阈值的调用不会产出日志。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-10-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "日志里使用 `logger.info(\"用户 %s 登录\", name)` 比 `logger.info(f\"用户 {name} 登录\")` 更好。",
                        "answer": {"value": True},
                        "explanation": "参数化写法把格式化推迟到真正输出时；级别被过滤时不会产生格式化开销。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-10-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个 get_logger(name, level) 函数：返回配置好的 logger，输出到控制台、格式含时间与级别、不向上冒泡。",
                        "answer": {
                            "reference": '''import logging


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(handler)
    logger.propagate = False
    return logger''',
                            "keywords": ["getLogger", "setLevel", "StreamHandler", "propagate"],
                        },
                        "explanation": "加 `if not logger.handlers` 判断，重复调用不会叠加 handler 导致重复输出。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-10-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「配置缺失时用默认值兜底」在多数情况下是坏主意？",
                        "answer": {
                            "reference": "兜底值往往只在开发机成立（比如 localhost 数据库），生产缺失配置时会静默连到错误目标，表现为数据写丢或读到空库，而且不报错、很难定位。让启动直接失败，问题在部署阶段就暴露，修复成本最低。",
                            "keywords": ["静默", "连错目标", "启动失败", "暴露"],
                        },
                        "explanation": "核心是「早失败优于静默错」，能举出连错库的具体后果更好。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
]
