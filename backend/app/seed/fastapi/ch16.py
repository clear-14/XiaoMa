"""FastAPI 后端开发：第 16 章（综合项目：任务管理 API）。

五个课时对应需求给出的九个步骤：
1 创建项目（步骤 1）→ 2 拆分路由与数据模型（步骤 2、3）→ 3 连接 SQLite 与 CRUD（步骤 4、5）
→ 4 接入认证与接口校验（步骤 6、7）→ 5 编写测试与整理配置（步骤 8、9）。
"""

CHAPTERS: list[dict] = [
    {
        "code": "fastapi-backend-16",
        "title": "综合项目：任务管理 API",
        "description": "把前面 23 个主题串成一个能测试、能部署的小项目。",
        "order_index": 16,
        "lessons": [
            {
                "code": "fastapi-backend-16-lesson-01",
                "objectives": """1. 能按分层结构建出项目骨架；
2. 能写出带 lifespan 与健康检查的入口文件；
3. 能说明每个目录的职责边界；
4. 能跑通「启动 → 访问 → 看到文档」的闭环。""",
                "why_learn": """项目一开始目录乱，后面每加一个功能都在还债：路由、模型、配置、测试全堆在 `main.py`。
先定结构再写代码，是让后面五个课时不返工的前提。""",
                "concepts": """**入口层**：`app/main.py` 只负责创建应用、挂路由、注册异常处理。
**路由层**：`app/routers/` 按资源拆分。
**数据层**：`app/models/`（ORM 模型）、`app/schemas/`（出入参模型）、`app/db/`（引擎与会话）。
**业务层**：`app/services/` 放业务规则与事务。
**公共层**：`app/core/` 放配置、日志、安全工具。
**测试**：`tests/` 与 `app` 平级。""",
                "plain": """项目结构像厨房的分区：切菜区、烹饪区、洗碗区。
东西混放时，找一把刀要翻三个抽屉；分区之后，每个人都知道去哪拿、用完放哪。
入口文件就是传菜口：只负责把单子递进去，不在那里炒菜。""",
                "syntax": """**项目结构（本项目的最终形态）**

```
taskapi/
├── app/
│   ├── main.py            # 创建应用、挂路由、注册异常处理、lifespan
│   ├── core/
│   │   ├── config.py      # Settings（pydantic-settings）
│   │   └── security.py    # 口令哈希、JWT 签发校验
│   ├── db/session.py      # engine、SessionLocal、get_session
│   ├── models/task.py     # Task / User ORM 模型
│   ├── schemas/task.py    # TaskCreate / TaskOut / Token
│   ├── repositories/task_repo.py
│   ├── services/task_service.py
│   └── routers/
│       ├── auth.py
│       └── tasks.py
├── tests/
│   ├── conftest.py
│   └── test_tasks.py
├── requirements.txt
└── .env.example
```

约定：依赖方向只能是「路由 → 服务 → 仓储 → 模型」，反向引用即视为设计问题。""",
                "example_code": '''from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.db.session import engine
from app.models.task import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 开发期直接建表；生产用 Alembic 迁移
    Base.metadata.create_all(bind=engine)
    print(f"启动完成，数据库：{settings.database_url}")
    yield
    engine.dispose()
    print("已释放连接池")


def create_app() -> FastAPI:
    application = FastAPI(
        title="任务管理 API",
        version="1.0.0",
        description="小码 FastAPI 综合项目",
        lifespan=lifespan,
    )

    @application.get("/health", tags=["system"], summary="健康检查")
    def health() -> dict:
        return {"status": "ok"}

    return application


app = create_app()''',
                "code_lines": """1. `lifespan` 里建表只是开发便利，生产环境应交给 Alembic 迁移。
2. `engine.dispose()` 在关闭时释放连接池，避免进程退出时连接悬挂。
3. `create_app()` 用工厂函数创建应用，测试里可以造独立实例。
4. `title/version/description` 直接决定 /docs 顶部信息。
5. `/health` 挂在 `system` 标签下，探针与文档分组都清楚。
6. 入口文件不出现任何 SQL、业务判断与路由实现——它只做组装。""",
                "output": """$ uvicorn app.main:app --reload
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
启动完成，数据库：sqlite+pysqlite:///./taskapi.db

curl http://127.0.0.1:8000/health
{"status":"ok"}

# /docs 顶部
任务管理 API  1.0.0
小码 FastAPI 综合项目

# 项目目录
$ find app -name "*.py" | sort
app/core/config.py
app/db/session.py
app/main.py
app/models/task.py
...""",
                "mistakes": """- 把路由、模型、SQL 全写进 `main.py`，后面拆不动。
- 入口文件里 `create_all` 又在生产用，导致表结构与迁移不一致。
- 目录名随意（`utils`、`common`、`misc` 混用），职责说不清。
- 配置读取散落在各处，换个环境要改很多文件。
- 没有 `.env.example`，新同事不知道要配哪些变量。""",
                "error_analysis": """`ModuleNotFoundError: No module named 'app'`
—— 从错误目录启动。应在项目根目录执行 `uvicorn app.main:app`。

`RuntimeError: Event loop is closed`（启动阶段）
—— 在 lifespan 里用了已关闭的事件循环资源，检查初始化顺序。

`sqlalchemy.exc.OperationalError: unable to open database file`
—— 数据库路径不存在或没有权限。统一用相对项目根的路径或绝对路径。""",
                "beginner_practice": """1. 建出上述目录并在每个包下放 `__init__.py`，跑通 `/health`。
2. 写一份 `.env.example`，列出 `APP_DATABASE_URL`、`APP_JWT_SECRET`、`APP_DEBUG`。""",
                "advanced_practice": """为这个结构补充「依赖方向检查」：用脚本扫描 `app/` 下的 import，
断言 routers 不直接 import models 之外的 db 细节、services 不 import routers。说明这个检查能挡住什么设计退化。""",
                "quiz_note": "本节 6 道题：2 道基础理解（分层职责、入口文件该做什么）+ 2 道代码阅读（读 lifespan、读工厂函数）+ 2 道应用练习（补目录、写 env 示例）。",
                "summary": """入口只做组装：创建应用、挂路由、注册异常与生命周期。
分层依赖单向：路由 → 服务 → 仓储 → 模型，反向引用即设计问题。
先定结构与配置，再写功能，能省掉大量返工。""",
                "next_lesson": "下一节拆路由、写模型：把任务相关的接口按资源组织起来。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-16-01",
                        "name": "项目骨架与分层职责",
                        "goal": "能建出分层清晰、可扩展的项目目录并跑通入口。",
                        "minutes": 35,
                        "criteria": "能说清每个目录的职责边界，并让 /health 正常返回。",
                        "requires": ["fastapi-backend-15-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-16-01-1",
                        "kp": 0,
                        "title": "跑通骨架",
                        "description": "按结构建目录与空模块，写 main.py 与 config.py，启动后访问 /health 与 /docs 均正常。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")
    database_url: str = "sqlite+pysqlite:///./taskapi.db"
    jwt_secret: str = "change-me"
    debug: bool = False


settings = Settings()

# app/main.py 见本节示例，启动命令
# uvicorn app.main:app --reload''',
                        "explanation": "先让最小闭环跑起来，再往里填功能；一开始就写全套容易在错误的结构上越走越远。",
                    },
                    {
                        "code": "fa-ex-16-01-2",
                        "kp": 0,
                        "title": "依赖方向检查",
                        "description": "写出检查思路：如何用脚本发现「services 反向 import routers」这类问题？",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''遍历 app/ 下所有 .py，用 ast 解析 import 语句，按目录归层（routers/services/repositories/models），
定义允许的边（routers→services→repositories→models），出现反向边即报错并输出文件与行号。
可接入 CI，作为结构性回归测试。''',
                        "explanation": "用 AST 而不是字符串匹配，能避免注释与字符串里的误报。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-16-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`app/main.py` 最适合承担什么职责？",
                        "options": [
                            ("A", "创建应用、挂路由、注册异常与生命周期"),
                            ("B", "写所有业务的 SQL"),
                            ("C", "定义数据库表结构"),
                            ("D", "存放业务规则"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "入口是组装层，业务在服务层、查询在仓储层、表结构在模型层。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列属于合理分层约定的有？（多选）",
                        "options": [
                            ("A", "routers 不直接写 SQL"),
                            ("B", "services 不 import routers"),
                            ("C", "models 依赖 routers 取参数"),
                            ("D", "配置集中在 core/config.py"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "models 是最底层，依赖 routers 会造成循环依赖，C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `engine.dispose()` 在什么时候执行？",
                        "options": [
                            ("A", "收到关闭信号、lifespan 结束时"),
                            ("B", "每个请求结束时"),
                            ("C", "启动时"),
                            ("D", "每次查询后"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`yield` 之后的代码在应用关闭阶段执行，用于释放连接池。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "开发期用 `create_all` 建表、生产也用同一套，可以省掉迁移工具。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "`create_all` 不会修改已有表结构，生产变更必须走迁移，否则会出现「代码已更新、表结构没变」。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全工厂函数，使应用带上 lifespan。横线处应填什么？\n\n```python\ndef create_app() -> FastAPI:\n    return FastAPI(title=\"任务管理 API\", ____)\n```",
                        "options": [
                            ("A", "lifespan=lifespan"),
                            ("B", "events=lifespan"),
                            ("C", "startup=lifespan"),
                            ("D", "on_startup=lifespan"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "FastAPI 的参数名是 `lifespan`；`on_startup` 是旧的 `on_event` 体系的写法。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-16-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么项目里要放 `.env.example`，而不是直接提交 `.env`？",
                        "answer": {"value": "`.env.example` 只列键名与示例值，告诉新同事需要配哪些变量，不含真实秘密；`.env` 含真实密钥，提交后任何有仓库权限的人（以及 CI 日志、误 fork）都能拿到。正确做法是 `.env` 加入 `.gitignore`，秘密由部署环境注入。"},
                        "explanation": "要点是「示例文件承担说明职责，真实文件承担秘密职责」，两者不能合并。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-16-lesson-02",
                "objectives": """1. 能写出任务的请求模型与响应模型；
2. 能把任务路由拆成独立 APIRouter 并挂载；
3. 能设计分页与筛选参数；
4. 能保证输出结构不泄漏内部字段。""",
                "why_learn": """模型与路由是接口的门面：字段定义错了，前端就要返工；路由没拆开，后面加认证与校验时会互相缠绕。
这一步把契约先定下来，后面填实现就只是「往里填」。""",
                "concepts": """**出入参分离**：`TaskCreate`（可写）与 `TaskOut`（可读）分开。
**路由前缀**：`APIRouter(prefix="/tasks", tags=["tasks"])`。
**分页参数**：`page/size` 带范围约束，响应含 `total`。
**统一响应**：列表返回 `{items,total,page,size}`，与前端约定一致。
**字段裁剪**：`response_model` 决定输出，内部字段（如 `owner_id`）默认不暴露。""",
                "plain": """模型是「表格模板」：谁来填都一样，栏目固定。
路由是「分类文件夹」：任务相关的单据都放这个夹子，别处不塞。
两者定好之后，实现只是填空；定不好，后面每加一个字段都要前后端一起改。""",
                "syntax": """**API 说明（app/schemas/task.py）**

```python
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    done: bool = False

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=50)
    done: bool | None = None

class TaskOut(BaseModel):
    id: int
    title: str
    done: bool

class TaskList(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    size: int
```

`TaskUpdate` 全部字段可选，用于 PATCH：不传即不改。""",
                "example_code": '''from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.task import TaskCreate, TaskList, TaskOut, TaskUpdate
from app.services.task_service import TaskService, get_task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskList, summary="任务列表")
def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
    done: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TaskList:
    items, total = service.list_tasks(done=done, page=page, size=size)
    return TaskList(items=items, total=total, page=page, size=size)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED, summary="创建任务")
def create_task(payload: TaskCreate, service: Annotated[TaskService, Depends(get_task_service)]) -> TaskOut:
    return service.create_task(payload)


@router.patch("/{task_id}", response_model=TaskOut, summary="更新任务")
def update_task(
    task_id: int,
    payload: TaskUpdate,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskOut:
    task = service.update_task(task_id, payload)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除任务")
def delete_task(task_id: int, service: Annotated[TaskService, Depends(get_task_service)]) -> None:
    if not service.delete_task(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")''',
                "code_lines": """1. `router` 带 prefix 与 tags，挂载后所有路径都在 `/tasks` 下并归到 tasks 组。
2. `@router.get("")` 的空字符串表示「就是前缀本身」。
3. 每个接口都通过 `Depends(get_task_service)` 拿服务，路由层不碰数据库。
4. 列表接口返回 `TaskList` 而非裸数组，前端能直接算总页数。
5. `TaskUpdate` 全字段可选，PATCH 不传的字段保持不变。
6. 404 用 `HTTPException` 表达，后续统一异常处理会把它变成统一结构。
7. 删除声明 204 且返回 None，符合「成功无响应体」的规范。""",
                "output": """curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":"写周报"}'
HTTP/1.1 201 Created
{"id":1,"title":"写周报","done":false}

curl "http://127.0.0.1:8000/tasks?done=false&page=1&size=20"
{"items":[{"id":1,"title":"写周报","done":false}],"total":1,"page":1,"size":20}

curl -X PATCH http://127.0.0.1:8000/tasks/1 -H "Content-Type: application/json" -d '{"done":true}'
{"id":1,"title":"写周报","done":true}

curl -i -X DELETE http://127.0.0.1:8000/tasks/999
HTTP/1.1 404 Not Found
{"detail":"任务不存在"}""",
                "mistakes": """- 列表返回裸数组，前端无法知道总数。
- `TaskUpdate` 字段设为必填，PATCH 变成 PUT。
- 路由里直接 `session.execute(select(...))`，把查询写进接口层。
- 出参模型包含 `owner_id`、`deleted_at` 等内部字段。
- router 前缀与路由路径都写 `/tasks`，拼出 `/tasks/tasks`。""",
                "error_analysis": """`422` 出现在空请求体
—— `TaskCreate` 的 `title` 必填。检查请求体是否带 `Content-Type: application/json`。

`ResponseValidationError: Input should be a valid list`
—— 列表接口返回了裸数组但 `response_model=TaskList`。要么返回完整结构，要么改模型。

`404` 访问 `/tasks/tasks`
—— 前缀重复，检查 router prefix 与路由路径。""",
                "beginner_practice": """1. 给 `TaskCreate` 加 `priority: int = Field(default=1, ge=1, le=5)`，并让 `TaskOut` 也返回它。
2. 给列表接口加 `q` 关键词参数，按标题模糊筛选。""",
                "advanced_practice": """设计「按标签筛选 + 多字段排序」的列表接口：说明参数如何声明、
排序字段如何用白名单映射到列对象，以及如何避免 `size` 过大拖垮数据库。""",
                "quiz_note": "本节 6 道题：2 道基础理解（出入参分离、列表结构）+ 2 道代码阅读（读 PATCH 语义、读 204）+ 2 道应用练习（补字段、加筛选）。",
                "summary": """出参模型决定前端拿到什么，入参模型决定能写什么，两者分开。
路由按资源拆分，前缀只声明一次，路径写 `""` 或 `/{id}`。
列表统一返回 `items/total/page/size`，PATCH 模型字段全可选。""",
                "next_lesson": "下一节接 SQLite：把服务层与仓储层填上，让 CRUD 真正落库。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-16-02",
                        "name": "任务路由与出入参模型",
                        "goal": "能拆出任务路由并定好出入参与分页结构。",
                        "minutes": 40,
                        "criteria": "能写出 4 个任务接口的路由骨架，且 PATCH 语义正确。",
                        "requires": ["fastapi-backend-16-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-16-02-1",
                        "kp": 0,
                        "title": "补 priority 字段",
                        "description": "给创建/更新/输出模型都加上 `priority`（1—5，默认 1），并说明 PATCH 时不传该字段应如何处理。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    done: bool = False
    priority: int = Field(default=1, ge=1, le=5)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=50)
    done: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=5)


class TaskOut(BaseModel):
    id: int
    title: str
    done: bool
    priority: int''',
                        "explanation": "更新模型里 `None` 表示「不改」，服务层用 `model_dump(exclude_unset=True)` 只覆盖传了的字段。",
                    },
                    {
                        "code": "fa-ex-16-02-2",
                        "kp": 0,
                        "title": "列表结构为什么不能是裸数组",
                        "description": "从分页、扩展性、前端解析三个角度说明裸数组的问题。",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''分页：裸数组无法携带 total，前端只能靠「返回条数 < size」猜最后一页；
扩展性：以后要加 has_more、next_cursor 时无处安放，只能破坏性改结构；
前端解析：统一从 res.items 取数据，比「有时是数组有时是对象」稳定得多。''',
                        "explanation": "列表响应从一开始就定成对象结构，是成本最低的扩展余量。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-16-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "PATCH 接口的更新模型应如何定义字段？",
                        "options": [
                            ("A", "全部可选，默认 None，不传即不改"),
                            ("B", "全部必填，要求整体替换"),
                            ("C", "全部只读"),
                            ("D", "只允许改主键"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "PATCH 是局部更新，字段必须可选；全部必填是 PUT 的语义。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "列表接口返回 `items/total/page/size` 的好处有？（多选）",
                        "options": [
                            ("A", "前端可计算总页数"),
                            ("B", "便于以后扩展 has_more 等字段"),
                            ("C", "减少数据库查询次数"),
                            ("D", "响应结构统一，解析逻辑稳定"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "响应结构不会影响查询次数，分页本身才是控制数据量的手段，C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`DELETE /tasks/999`（不存在）返回什么？",
                        "options": [("A", "204"), ("B", "404 与「任务不存在」"), ("C", "500"), ("D", "200 与 false")],
                        "answer": {"value": "B"},
                        "explanation": "服务层返回 False 时路由抛 404，保持与查询接口一致的错误语义。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "路由层直接调用 `session.execute(...)` 能让代码更短，是推荐做法。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "查询应在仓储层、业务在服务层；路由层写 SQL 会让复用、测试与事务控制全部变难。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全路由装饰器，使列表接口返回 200 且使用 TaskList 结构。横线处应填什么？\n\n```python\n@router.get(\"\", ____, summary=\"任务列表\")\ndef list_tasks(...): ...\n```",
                        "options": [
                            ("A", "response_model=TaskList"),
                            ("B", "response_model=TaskOut"),
                            ("C", "model=TaskList"),
                            ("D", "returns=TaskList"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "列表接口要用列表模型；写成 TaskOut 会触发 ResponseValidationError。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-16-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "服务层如何区分「字段没传」与「字段传了 null」？",
                        "answer": {"value": "用 `payload.model_dump(exclude_unset=True)`：只导出调用方实际传了的字段，未传的键根本不出现在字典里。若业务需要支持显式置空，则要区分 `exclude_unset` 与 `exclude_none`，并在字段上允许 `None` 值语义（如清空截止时间），两者语义不能混。"},
                        "explanation": "关键 API 是 `exclude_unset`；混用 `exclude_none` 会让「显式置空」失效。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-16-lesson-03",
                "objectives": """1. 能配置 SQLite 引擎与会话依赖；
2. 能写出任务与用户两张表的 ORM 模型与关系；
3. 能在仓储层完成 CRUD 与分页查询；
4. 能处理「会话生命周期」与「事务提交」的边界。""",
                "why_learn": """前面用内存字典糊弄过去的存储，到这里要换成真正的数据库。
一旦落库，分页、事务、关系、并发都会变成必须面对的问题——这也是把 CRUD 做对的分水岭。""",
                "concepts": """**SQLite 连接**：`sqlite+pysqlite:///./taskapi.db`，多线程需关闭 `check_same_thread`。
**模型关系**：`Task.owner_id` 外键指向 `users.id`。
**仓储 CRUD**：`add/flush/commit`、`select().where().offset().limit()`。
**计数查询**：`select(func.count()).select_from(...)` 与列表查询共用过滤条件。
**会话边界**：依赖里提交、异常回滚，仓储只管操作。""",
                "plain": """数据库像档案室：模型是档案柜的格子定义，仓储是管理员，会话是你这一次进档案室的通行证。
通行证一进一出算一次；出门时要么把改动登记入册（提交），要么整页作废（回滚）。
分页像一次只调十份档案：调太多会堆满桌子，调太少要跑很多趟。""",
                "syntax": """**API 说明（app/db/session.py）**

```python
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},   # SQLite 专用
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

切换 PostgreSQL 时去掉 `connect_args` 即可，其余代码不变。""",
                "example_code": '''from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository:
    """任务的数据访问层：只做查询与持久化，不含业务规则。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_tasks(self, *, owner_id: int, done: bool | None, page: int, size: int) -> tuple[Sequence[Task], int]:
        conditions = [Task.owner_id == owner_id]
        if done is not None:
            conditions.append(Task.done.is_(done))
        total = self.session.scalar(
            select(func.count()).select_from(Task).where(*conditions)
        ) or 0
        rows = self.session.scalars(
            select(Task)
            .where(*conditions)
            .order_by(Task.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        return rows, total

    def get(self, task_id: int) -> Task | None:
        return self.session.get(Task, task_id)

    def create(self, payload: TaskCreate, owner_id: int) -> Task:
        task = Task(title=payload.title, done=payload.done, owner_id=owner_id)
        self.session.add(task)
        self.session.flush()
        return task

    def update(self, task: Task, payload: TaskUpdate) -> Task:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        self.session.flush()
        return task

    def delete(self, task: Task) -> None:
        self.session.delete(task)
        self.session.flush()''',
                "code_lines": """1. `conditions` 列表先构造过滤条件，计数与列表查询共用，避免两处不一致。
2. `select(func.count()).select_from(Task)` 是标准计数写法，比 `len(rows)` 准确（不受分页影响）。
3. `.offset((page - 1) * size).limit(size)` 是分页核心，页码从 1 开始。
4. `session.get(Task, task_id)` 按主键查询，命中缓存时不发 SQL。
5. `flush()` 让新对象立即拿到主键，但不结束事务——提交由依赖层负责。
6. `model_dump(exclude_unset=True)` 只取调用方传了的字段，实现 PATCH 语义。
7. 仓储层不 `commit`，事务边界统一在会话依赖里，保证「一个请求一个事务」。""",
                "output": """curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":"写周报"}'
{"id":1,"title":"写周报","done":false}

curl "http://127.0.0.1:8000/tasks?page=1&size=20"
{"items":[{"id":1,"title":"写周报","done":false}],"total":1,"page":1,"size":20}

# 数据库文件
$ sqlite3 taskapi.db "select id,title,done,owner_id from tasks;"
1|写周报|0|1

# 分页参数越界
curl "http://127.0.0.1:8000/tasks?size=101"
{"detail":[{"type":"less_than_equal","loc":["query","size"],"msg":"Input should be less than or equal to 100"}]}""",
                "mistakes": """- 用 `len(rows)` 当总数，分页后永远等于 size。
- 计数查询与列表查询过滤条件不一致，出现「total 与 items 对不上」。
- 仓储层里 `commit()`，导致一个请求里多次提交、无法整体回滚。
- SQLite 忘记 `check_same_thread=False`，多线程下报错。
- 分页偏移写成 `page * size`，第一页就跳过一页。""",
                "error_analysis": """`total` 恒等于 `size`
—— 用 `len(rows)` 代替了 count 查询。

`sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`
—— 未设置 `check_same_thread=False`，或会话跨线程复用。

`IntegrityError: NOT NULL constraint failed: tasks.owner_id`
—— 创建时没带 owner_id。检查是否从当前用户取值。""",
                "beginner_practice": """1. 实现 `TaskRepository.get` 的调用方：`GET /tasks/{id}`，找不到返回 404。
2. 把 `order_by` 换成 `Task.title`，验证列表顺序变化。""",
                "advanced_practice": """为「按状态统计数量」写一个仓储方法（`select(Task.done, func.count()).group_by(Task.done)`），
并说明为什么这类聚合查询更适合放仓储层而不是在接口里临时拼。""",
                "quiz_note": "本节 6 道题：2 道基础理解（会话边界、分页偏移）+ 2 道代码阅读（读计数查询、读 flush）+ 2 道应用练习（补 get、加统计）。",
                "summary": """引擎与会话工厂在 `db/session.py`，会话依赖负责提交/回滚/关闭。
仓储层只做查询与持久化，用 `flush` 拿主键、用 `exclude_unset` 实现 PATCH。
分页用 `offset/limit`，总数用 count 查询且与列表共用过滤条件。""",
                "next_lesson": "下一节接认证：登录发令牌，任务只属于自己。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-16-03",
                        "name": "SQLite 连接与仓储 CRUD",
                        "goal": "能把 CRUD 落到 SQLite，并保持分页与事务正确。",
                        "minutes": 45,
                        "criteria": "能写出带分页与计数的仓储方法，且总数与列表一致。",
                        "requires": ["fastapi-backend-16-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-16-03-1",
                        "kp": 0,
                        "title": "补 get 与统计",
                        "description": "写 `GET /tasks/{task_id}` 与 `GET /tasks/stats`（返回 done 与未完成数量），路由放到 tasks router 里且注意顺序。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''@router.get("/stats", response_model=TaskStats, summary="任务统计")
def task_stats(service: Annotated[TaskService, Depends(get_task_service)]) -> TaskStats:
    return service.stats()


@router.get("/{task_id}", response_model=TaskOut, summary="任务详情")
def get_task(task_id: int, service: Annotated[TaskService, Depends(get_task_service)]) -> TaskOut:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task''',
                        "explanation": "`/stats` 必须写在 `/{task_id}` 之前，否则会被当成 id 解析并返回 422。",
                    },
                    {
                        "code": "fa-ex-16-03-2",
                        "kp": 0,
                        "title": "总数与列表对不上",
                        "description": "接口返回 total=100 但 items 只有 3 条，可能是什么原因？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① total 用了不带分页的查询但 items 带了额外过滤条件（或反之）；
② 计数查询与列表查询的条件列表不是同一份，重构时漏改一处；
③ 多租户/权限过滤只加在其中一个查询上（很常见）。
修法：把过滤条件抽成一个方法，两个查询都调用它。''',
                        "explanation": "根因几乎总是「两处条件不一致」，所以要让它们共用同一份条件构造逻辑。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-16-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`session.flush()` 与 `session.commit()` 的区别是？",
                        "options": [
                            ("A", "flush 发送 SQL 但不结束事务，commit 提交事务"),
                            ("B", "flush 提交事务，commit 只发 SQL"),
                            ("C", "两者完全等价"),
                            ("D", "flush 只能用于查询"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`flush` 让改动落到数据库连接（拿到自增主键），但仍可回滚；`commit` 才真正结束事务。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-03-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于分页实现，正确的有？（多选）",
                        "options": [
                            ("A", "偏移为 (page - 1) * size"),
                            ("B", "size 必须有上限"),
                            ("C", "总数用 count 查询而不是 len(items)"),
                            ("D", "深分页时 OFFSET 越大越快"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "OFFSET 越大需要跳过的行越多，是变慢而不是变快，D 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-03-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`create` 方法里 `flush()` 的作用是？",
                        "options": [
                            ("A", "让新任务立即获得自增 id"),
                            ("B", "提交事务"),
                            ("C", "关闭会话"),
                            ("D", "清空会话缓存"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`flush` 发送 INSERT 并回填主键，事务仍由外层依赖提交。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-03-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "仓储层负责 `commit()` 能让代码更清晰，是推荐做法。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "仓储提交会让「一个请求一个事务」的边界被切碎，无法整体回滚；事务应由会话依赖或服务层统一控制。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-03-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全分页偏移。横线处应填什么？\n\n```python\n.offset(____)\n.limit(size)\n```",
                        "options": [
                            ("A", "(page - 1) * size"),
                            ("B", "page * size"),
                            ("C", "page + size"),
                            ("D", "size - 1"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "页码从 1 开始，第一页偏移必须为 0。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-16-03-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么 `GET /tasks/stats` 必须写在 `GET /tasks/{task_id}` 之前？",
                        "answer": {"value": "路由按声明顺序匹配：先声明的 `/{task_id}` 会把 `stats` 当作路径参数，`int` 转换失败返回 422，导致 `/stats` 永远访问不到。固定路径必须排在动态路径之前。"},
                        "explanation": "这条规则在第 3 章已经踩过一次，项目里仍是最常见的 422 来源。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-16-lesson-04",
                "objectives": """1. 能实现注册、登录与令牌签发；
2. 能用依赖注入当前用户；
3. 能让任务天然属于当前用户（而不是客户端指定）；
4. 能补齐业务校验与统一错误结构。""",
                "why_learn": """没有认证的任务 API 等于公用白板：任何人都能看、能改。
接入认证后，`owner_id` 必须来自令牌而不是请求体——这一点做错，越权就回来了。""",
                "concepts": """**注册**：校验邮箱唯一，密码哈希后入库。
**登录**：校验口令，签发 access_token。
**当前用户依赖**：解析令牌 → 查用户 → 不存在或禁用即 401。
**归属绑定**：创建任务时 `owner_id = current_user.id`，绝不接受客户端传 owner。
**资源级校验**：查到的任务 `owner_id` 不匹配即 403（管理员例外）。""",
                "plain": """认证像发工牌：注册是入职，登录是刷卡领牌。
工牌上写着你是谁，所以填单子时不用自己写名字——名字由工牌决定，写错了也没用。
这就是为什么 `owner_id` 必须来自令牌：让客户自己填，等于让访客自己写工号。""",
                "syntax": """**API 说明（app/routers/auth.py + app/core/deps.py）**

```python
def get_current_user(
    token: Annotated[str, Depends(bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    payload = decode_token(token)
    user = session.scalar(select(User).where(User.email == payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(401, "用户不存在或已禁用", headers={"WWW-Authenticate": "Bearer"})
    return user
```

服务层接收 `current_user` 并用于归属判断，路由层不直接写权限逻辑。""",
                "example_code": '''from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_token, verify_password
from app.db.session import get_session
from app.models.task import User
from app.schemas.task import Token, UserCreate, UserOut
from app.services.user_service import UserService, get_user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="注册")
def register(payload: UserCreate, service: Annotated[UserService, Depends(get_user_service)]) -> UserOut:
    if service.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="邮箱已注册")
    return service.create_user(payload)


@router.post("/login", response_model=Token, summary="登录")
def login(
    payload: UserCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Token:
    user = session.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    return Token(access_token=create_token(sub=user.email), token_type="bearer")


@router.get("/me", response_model=UserOut, summary="当前用户")
def me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return user''',
                "code_lines": """1. 注册先查邮箱是否存在，返回 409 而不是 500——并发下再由唯一索引兜底。
2. `create_user` 内部完成口令哈希，路由层不接触明文密码的存储细节。
3. 登录失败统一提示「邮箱或密码不正确」，不区分「用户不存在」与「密码错」，避免账号枚举。
4. `create_token(sub=user.email)` 把身份写进令牌，有效期由签发函数控制。
5. `/auth/me` 用 `get_current_user` 依赖，路由函数只负责返回。
6. 所有出口都走 `response_model`，确保 `password_hash` 不会出现在响应里。""",
                "output": """curl -X POST http://127.0.0.1:8000/auth/register -H "Content-Type: application/json" \
  -d '{"email":"lisi@example.com","password":"s3cret-pass"}'
HTTP/1.1 201 Created
{"id":1,"email":"lisi@example.com"}

curl -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" \\
  -d '{"email":"lisi@example.com","password":"s3cret-pass"}'
{"access_token":"eyJhbGci...","token_type":"bearer"}

curl -H "Authorization: Bearer eyJhbGci..." http://127.0.0.1:8000/auth/me
{"id":1,"email":"lisi@example.com"}

curl -X POST http://127.0.0.1:8000/tasks -H "Authorization: Bearer eyJhbGci..." \\
  -H "Content-Type: application/json" -d '{"title":"写周报","owner_id":999}'
{"id":1,"title":"写周报","done":false}   # owner_id 被忽略，实际取当前用户""",
                "mistakes": """- 创建任务时接受客户端传的 `owner_id`，直接造成越权。
- 登录失败提示「用户不存在」，被用来枚举账号。
- 响应模型含 `password_hash`，注册接口把哈希返回给前端。
- 令牌没有过期时间，泄漏后长期可用。
- 权限判断只写在列表接口，详情与更新接口漏掉。""",
                "error_analysis": """`401` 出现在刚登录后
—— 令牌没带 `Bearer ` 前缀，或用了过期令牌。

`409` 注册但邮箱确实没注册过
—— 查重时大小写没统一（`Lisi@` 与 `lisi@`），入库前应统一转小写。

任务创建成功但 `owner_id` 是别人
—— 直接取了请求体字段。必须用 `current_user.id` 覆盖。""",
                "beginner_practice": """1. 给任务创建接口加「忽略客户端 owner_id」的处理，并用两个账号验证隔离。
2. 把登录失败提示改成统一文案，确认不再泄漏账号是否存在。""",
                "advanced_practice": """设计「团队任务」：任务属于团队，成员可读写、外部人不可见。
说明 owner_id 与 team_id 如何配合、列表查询如何避免漏过滤，以及如何为这套规则写测试。""",
                "quiz_note": "本节 6 道题：2 道基础理解（owner 来源、登录提示）+ 2 道代码阅读（读 409、读响应模型）+ 2 道应用练习（改归属、加隔离测试）。",
                "summary": """认证链路：注册哈希入库、登录签发令牌、依赖解析当前用户。
`owner_id` 必须来自令牌，绝不接受客户端传值。
权限校验覆盖列表、详情、修改、删除全部入口，缺一处就是越权。""",
                "next_lesson": "最后一节：写测试、整理配置，把项目交付出去。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-16-04",
                        "name": "项目接入认证与归属校验",
                        "goal": "能把认证接进项目并让数据按用户隔离。",
                        "minutes": 45,
                        "criteria": "能用两个账号验证「看不到、改不了他人任务」。",
                        "requires": ["fastapi-backend-16-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-16-04-1",
                        "kp": 0,
                        "title": "归属绑定",
                        "description": "改任务创建逻辑：忽略请求体里的 owner_id，改用当前用户；并写一条「A 看不到 B 的任务」的验证步骤。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''@router.post("", response_model=TaskOut, status_code=201)
def create_task(
    payload: TaskCreate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskOut:
    return service.create_task(payload, owner_id=user.id)

# 验证：A 登录建任务 -> B 登录请求 /tasks，items 中不含 A 的任务''',
                        "explanation": "服务层签名要求显式传 owner_id，从设计上就堵住「客户端指定归属」这条路。",
                    },
                    {
                        "code": "fa-ex-16-04-2",
                        "kp": 0,
                        "title": "不泄漏账号是否存在",
                        "description": "为什么登录失败要统一提示？如果不统一，攻击者能做什么？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''统一提示避免账号枚举。若不统一，攻击者可批量提交邮箱，根据「用户不存在」与「密码错误」的差异筛选出已注册邮箱，
再针对这些账号做撞库或钓鱼，成功率大幅提高。''',
                        "explanation": "账号枚举本身不直接失陷，但它是后续攻击的放大器，属于必须堵的低成本风险。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-16-04-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "创建任务时 `owner_id` 应来自哪里？",
                        "options": [
                            ("A", "当前登录用户（令牌解析结果）"),
                            ("B", "请求体里的 owner_id"),
                            ("C", "查询参数"),
                            ("D", "随机生成"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "归属由身份决定，客户端传值等于允许冒名创建，是典型越权入口。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-04-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "接入认证后仍必须做权限校验的接口有？（多选）",
                        "options": [
                            ("A", "任务列表"),
                            ("B", "任务详情"),
                            ("C", "任务更新与删除"),
                            ("D", "健康检查"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "健康检查是公开探针，不需要用户身份；其余三个都必须校验归属。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-04-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "请求体带 `owner_id: 999` 创建任务后，实际归属是？",
                        "options": [
                            ("A", "999"),
                            ("B", "当前令牌对应的用户"),
                            ("C", "NULL"),
                            ("D", "随机用户"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "服务层用 `user.id` 覆盖，请求体里的 owner_id 被忽略（模型里也不应声明它）。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-04-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "注册接口返回 `UserOut` 就足以保证密码哈希不会泄漏。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "A"},
                        "explanation": "`response_model=UserOut` 会按模型裁剪字段；但仍建议服务层就不返回该字段，双重保障。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-04-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全依赖声明，使接口拿到当前用户。横线处应填什么？\n\n```python\ndef create_task(payload: TaskCreate, ____, service: Annotated[TaskService, Depends(get_task_service)]):\n    ...\n```",
                        "options": [
                            ("A", "user: Annotated[User, Depends(get_current_user)]"),
                            ("B", "user = get_current_user()"),
                            ("C", "user: User"),
                            ("D", "user: Annotated[User, get_current_user]"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "必须包在 `Depends(...)` 里，框架才会执行依赖并注入结果。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-16-04-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如何用测试保证「用户之间数据隔离」这条约束不会退化？",
                        "answer": {"value": "在测试里固定创建两个用户与各自的任务，然后：① A 的令牌请求 `/tasks`，断言 items 中不含 B 的任务；② A 请求 `/tasks/{B的任务id}` 断言 403 或 404；③ A 尝试 PATCH/DELETE B 的任务断言 403。把这些断言放进回归用例，任何人改坏权限都会立刻失败。"},
                        "explanation": "关键是「双用户 + 覆盖四类入口」，只测列表会漏掉详情与写操作。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-16-lesson-05",
                "objectives": """1. 能用 TestClient + fixture 写出覆盖核心路径的测试；
2. 能用 `dependency_overrides` 隔离测试数据库；
3. 能整理出可交付的配置文件与启动说明；
4. 能给出项目的验收清单并逐项自检。""",
                "why_learn": """项目交付的标准不是「我本机能跑」，而是「别人拉下来照文档能跑，改完代码测试能发现回归」。
这一步把这些补齐，项目才算完成。""",
                "concepts": """**conftest.py**：共享 fixture 的入口，pytest 自动加载。
**测试库隔离**：内存 SQLite + 每用例建表，或用事务回滚。
**override**：`app.dependency_overrides[get_session] = ...` 替换真实会话。
**配置整理**：`requirements.txt`、`.env.example`、`README` 启动说明。
**验收清单**：接口能用、测试能过、配置齐全、文档可访问。""",
                "plain": """交付像交房：不能只说「我家住着挺舒服」，得把水电图、钥匙、保修单一起给。
测试就是验收单：别人按单子逐项打勾，就知道这房子能不能住。
配置与文档是钥匙和说明书——缺了它们，房子再好别人也进不去。""",
                "syntax": """**API 说明（tests/conftest.py）**

```python
@pytest.fixture
def client():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_session():
        session = TestingSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

注意：内存库在每个连接上是独立的，需配合 `StaticPool` 或直接用同一连接。""",
                "example_code": '''from fastapi.testclient import TestClient


def auth_header(client: TestClient, email: str = "lisi@example.com") -> dict:
    client.post("/auth/register", json={"email": email, "password": "s3cret-pass"})
    token = client.post(
        "/auth/login", json={"email": email, "password": "s3cret-pass"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_list_task(client: TestClient) -> None:
    headers = auth_header(client)
    created = client.post("/tasks", json={"title": "写周报"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["title"] == "写周报"

    listed = client.get("/tasks", headers=headers)
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "写周报"


def test_tasks_are_isolated_between_users(client: TestClient) -> None:
    alice = auth_header(client, "alice@example.com")
    bob = auth_header(client, "bob@example.com")

    client.post("/tasks", json={"title": "alice 的任务"}, headers=alice)
    bob_tasks = client.get("/tasks", headers=bob).json()

    assert bob_tasks["total"] == 0
    assert bob_tasks["items"] == []


def test_unauthenticated_request_is_rejected(client: TestClient) -> None:
    assert client.get("/tasks").status_code == 401''',
                "code_lines": """1. `auth_header` 把「注册 + 登录 + 组头」封装成辅助函数，用例读起来只剩业务。
2. 每个用例自己造数据，不依赖执行顺序。
3. 断言分三层：状态码、关键字段、副作用（列表里能查到）。
4. 隔离用例用两个账号：alice 建任务，bob 的列表必须为空。
5. 未认证用例断言 401，保证认证不会被误删。
6. `client` 由 fixture 提供，内部换成内存库，不碰真实数据。""",
                "output": """# 请求与响应
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/tasks
{"items":[],"total":0,"page":1,"size":20}

curl -i http://127.0.0.1:8000/tasks
HTTP/1.1 401 Unauthorized
{"detail":"Not authenticated"}

# 测试输出
$ pytest -q
....                                                                     [100%]
4 passed in 1.03s

# 覆盖情况
$ pytest --cov=app -q
Name                        Stmts   Miss  Cover
app/routers/tasks.py           42      3    93%
app/routers/auth.py            28      2    93%
app/services/task_service.py   35      5    86%
TOTAL                         210     28    87%

# 配置检查
$ python -c "from app.core.config import settings; print(settings.database_url)"
sqlite+pysqlite:///./taskapi.db

# 启动
$ uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2""",
                "mistakes": """- 测试连真实数据库，跑几次数据就乱了。
- 用例间共享注册用户，第二次跑报 409。
- 只测成功路径，权限与 401 从不验证。
- 忘记 `app.dependency_overrides.clear()`，污染其它测试文件。
- 交付缺 `.env.example`，别人不知道要配什么。""",
                "error_analysis": """`409 邮箱已注册` 在第二次跑测试时出现
—— 测试库没隔离。用内存库或每个用例清表。

`sqlite3.OperationalError: no such table: tasks`
—— 测试库没建表。fixture 里要 `Base.metadata.create_all(engine)`。

`401` 出现在已带令牌的请求
—— 令牌来自另一个测试库的用户，库被重建后用户不存在。确保注册与请求用同一个 client。""",
                "beginner_practice": """1. 补一条「A 无法修改 B 的任务」用例，断言 403。
2. 写出 `.env.example` 与 README 的三行启动说明。""",
                "advanced_practice": """给项目加一份交付自检清单：接口清单、测试覆盖、配置项、部署命令、已知限制。
说明每项如何被自动验证（测试、脚本或 CI），而不是靠人工记忆。""",
                "quiz_note": "本节 6 道题：2 道基础理解（fixture 隔离、override 清理）+ 2 道代码阅读（读隔离用例、读 401）+ 2 道应用练习（补 403 用例、写自检清单）。",
                "summary": """测试用内存库 + fixture 隔离，每个用例自带数据。
`dependency_overrides` 用完必须清理，否则污染其它用例。
交付要含配置示例、启动说明与验收清单，别人照做能跑起来才算完成。""",
                "next_lesson": "本项目到此完成。可以回看第 1 章，用「请求—响应—状态码」的视角重新审视整个项目。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-16-05",
                        "name": "项目测试与交付配置",
                        "goal": "能用测试固化核心行为，并整理出可交付的配置与说明。",
                        "minutes": 40,
                        "criteria": "能跑通包含认证与隔离的 4 条用例，并给出可照做的启动步骤。",
                        "requires": ["fastapi-backend-16-04"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-16-05-1",
                        "kp": 0,
                        "title": "补一条越权用例",
                        "description": "写用例：A 与 B 各自注册，A 创建任务，B 尝试 PATCH 该任务应得到 403。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def test_cannot_update_others_task(client: TestClient) -> None:
    alice = auth_header(client, "alice@example.com")
    bob = auth_header(client, "bob@example.com")

    task_id = client.post("/tasks", json={"title": "alice 的任务"}, headers=alice).json()["id"]
    resp = client.patch(f"/tasks/{task_id}", json={"done": True}, headers=bob)

    assert resp.status_code == 403''',
                        "explanation": "用例必须自己造数据并自己断言，不依赖前面的用例；403 与 404 的选择要在项目内统一。",
                    },
                    {
                        "code": "fa-ex-16-05-2",
                        "kp": 0,
                        "title": "交付自检清单",
                        "description": "列出交付前必须逐项确认的五件事，并说明每件能否被自动化验证。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 接口可用：用冒烟脚本逐个打一遍（可自动化）；
② 测试通过：pytest（可自动化）；
③ 配置齐全：.env.example 与 README 对齐，启动时校验必填项（半自动，可脚本检查键名）；
④ 文档可访问：请求 /openapi.json 断言 200（可自动化）；
⑤ 已知限制与迁移方式写清楚（人工）。''',
                        "explanation": "能被自动化验证的项应放进 CI，人工项要写进模板，避免每次靠记忆。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-16-05-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "测试用例之间互相影响，最可能的原因是？",
                        "options": [
                            ("A", "共享了数据库或全局状态且未重置"),
                            ("B", "断言写得太多"),
                            ("C", "用了 TestClient"),
                            ("D", "用例数量太多"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "隔离问题的根源是共享可变状态；fixture 的职责就是每个用例重建干净环境。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-05-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "交付一个后端项目时，应该包含？（多选）",
                        "options": [
                            ("A", ".env.example"),
                            ("B", "启动与测试命令说明"),
                            ("C", "requirements.txt 锁定依赖"),
                            ("D", "测试用例"),
                        ],
                        "answer": {"values": ["A", "B", "C", "D"]},
                        "explanation": "四项都是「别人能跑起来、能改得动」的必要条件。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-16-05-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`test_tasks_are_isolated_between_users` 断言了什么？",
                        "options": [
                            ("A", "bob 的任务列表为空"),
                            ("B", "alice 能删 bob 的任务"),
                            ("C", "两人共享任务"),
                            ("D", "未登录返回 401"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "该用例验证数据隔离：bob 看不到 alice 创建的任务。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-05-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "测试只覆盖成功路径就够了，异常路径可以手工验证。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "异常路径（401/403/404/422）恰恰是最容易在重构中悄悄失效的部分，必须用测试固化。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-16-05-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全 fixture 收尾语句，清除依赖替换。横线处应填什么？\n\n```python\n@pytest.fixture\ndef client():\n    app.dependency_overrides[get_session] = override_get_session\n    with TestClient(app) as c:\n        yield c\n    ____\n```",
                        "options": [
                            ("A", "app.dependency_overrides.clear()"),
                            ("B", "app.dependency_overrides = {}"),
                            ("C", "del app.dependency_overrides"),
                            ("D", "app.dependencies.clear()"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "用 `clear()` 清空字典最安全；直接赋空字典虽可行但会替换对象引用，可能影响其它 fixture。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-16-05-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如何让「交付自检」不再依赖人工记忆？",
                        "answer": {"value": "把可验证项写成脚本或 CI 步骤：① `/openapi.json` 与 `/health` 冒烟脚本；② pytest + 覆盖率阈值；③ 检查 `.env.example` 的键与 Settings 字段一致（用反射比对）；④ 启动一次容器验证迁移与种子；⑤ 生成一份自动汇总的检查结果。人工只负责评审结果与已知限制的更新。"},
                        "explanation": "核心是把「检查清单」变成「可执行脚本」，否则清单很快会流于形式。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
