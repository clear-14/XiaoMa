"""FastAPI 后端开发：第 15—16 章（日志配置与部署、综合项目：任务管理 API）。"""

CHAPTERS: list[dict] = [
    {
        "code": "fastapi-backend-15",
        "title": "日志、配置与部署",
        "description": "能跑起来只是开始，能稳定运行才算交付。",
        "order_index": 15,
        "lessons": [
            {
                "code": "fastapi-backend-15-lesson-01",
                "objectives": """1. 能配置分级日志并输出结构化字段；
2. 知道日志里绝不能出现哪些内容；
3. 会用 `pydantic-settings` 从环境变量读取配置；
4. 能区分「配置」与「秘密」，并给出分层方案。""",
                "why_learn": """出问题时第一反应是看日志：没有请求 ID、没有关键字段，只能靠猜。
配置写死在代码里，换个环境就要改代码重新发布；密钥进了仓库，等于公开。这两件事都在上线前必须解决。""",
                "concepts": """**日志级别**：DEBUG/INFO/WARNING/ERROR/CRITICAL，生产一般 INFO 起步。
**结构化字段**：用 `extra={...}` 附加 request_id、user_id、path，便于检索。
**脱敏**：密码、令牌、完整密钥、身份证等不得进日志。
**配置来源**：环境变量 > `.env` 文件 > 代码默认值。
**pydantic-settings**：用模型声明配置项，自动做类型转换与校验。""",
                "plain": """日志像行车记录仪：平时没人看，出事时全靠它。
记录仪要拍「时间、位置、发生了什么」，只拍一片模糊的马路没用——这就是结构化字段的意义。
配置像车上的座椅调节：不同司机（环境）各自调，不该焊死在车架上；密钥则是车钥匙，绝不能贴在挡风玻璃上。""",
                "syntax": """**API 说明**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")
    database_url: str = "sqlite+pysqlite:///./app.db"
    debug: bool = False
```

- 环境变量名 = `env_prefix` + 字段名大写，如 `APP_DATABASE_URL`。
- 未提供时用默认值；类型自动转换（`"true"` → `True`）。
- 用 `@lru_cache` 包装 `get_settings()`，避免每次请求都读环境。""",
                "example_code": '''import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("xiaoma.api")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    database_url: str = "sqlite+pysqlite:///./app.db"
    debug: bool = False
    jwt_secret: str = "change-me-in-production"
    log_level: str = "INFO"


settings = Settings()
logger.setLevel(settings.log_level)

logger.info(
    "应用启动",
    extra={"debug": settings.debug, "database": settings.database_url.split("///")[-1]},
)
logger.warning("使用默认密钥，仅限本地开发", extra={"env": "local"})

try:
    1 / 0
except ZeroDivisionError:
    logger.exception("计算失败", extra={"request_id": "trace-001", "path": "/reports"})''',
                "code_lines": """1. `basicConfig` 设定全局格式：时间、级别、模块名、消息，四段足够定位。
2. `getLogger("xiaoma.api")` 用模块名做 logger 名，方便按模块调级别。
3. `Settings` 用 `pydantic-settings` 声明配置，`env_prefix="APP_"` 统一前缀避免与系统变量冲突。
4. 字段都有默认值，本地不配环境变量也能跑；生产用环境变量覆盖。
5. 日志里只打印数据库文件名，不打印完整连接串（可能含账号密码）。
6. `logger.warning` 提示默认密钥风险——这类「配置隐患」应该主动告警。
7. `logger.exception` 在 except 里使用，会自动带上 traceback，比 `error` 更适合排查。""",
                "output": """# 请求与响应
curl http://127.0.0.1:8000/health
{"status":"ok"}

# 服务端日志
2026-11-08 17:20:31,204 INFO xiaoma.api 应用启动
2026-11-08 17:20:31,205 WARNING xiaoma.api 使用默认密钥，仅限本地开发
2026-11-08 17:20:31,206 ERROR xiaoma.api 计算失败
Traceback (most recent call last):
  File "demo.py", line 26, in <module>
    1 / 0
ZeroDivisionError: division by zero

# 环境变量覆盖
$ APP_DEBUG=true APP_LOG_LEVEL=DEBUG uvicorn app.main:app
# 日志级别随之变为 DEBUG，debug 字段为 true""",
                "mistakes": """- 把密码、令牌、完整连接串打进日志。
- 生产仍用 DEBUG 级别，日志量爆炸还可能带敏感信息。
- 配置写死在代码里，多环境要改代码。
- 密钥提交进 Git（`.env` 未加入 `.gitignore`）。
- 只用 `print`，没有级别也没有时间戳，出问题无法按时间检索。""",
                "error_analysis": """`pydantic_core.ValidationError: Input should be a valid boolean`
—— 环境变量写了 `APP_DEBUG=1` 之类无法解析的值。布尔用 `true/false`。

配置读取不到（一直用默认值）
—— 文件名不是 `.env`、工作目录不对，或前缀不匹配（写成 `DATABASE_URL` 而非 `APP_DATABASE_URL`）。

日志重复打印两遍
—— 既调用了 `basicConfig` 又给 root logger 加了 handler。统一在一处配置。""",
                "beginner_practice": """1. 加一个 `APP_LOG_LEVEL=DEBUG` 环境变量，验证日志级别变化。
2. 给设置对象加 `max_page_size: int = 100`，并说明它该被哪个依赖使用。""",
                "advanced_practice": """设计一套多环境配置方案：local / staging / prod。
说明各环境配置文件如何组织、密钥如何注入（不落盘）、以及启动时如何校验「关键配置缺失就拒绝启动」。""",
                "quiz_note": "本节 6 道题：2 道基础理解（配置来源、日志脱敏）+ 2 道代码阅读（读 extra、读 exception）+ 2 道应用练习（加配置项、改日志级别）。",
                "summary": """日志要有级别、时间、模块与结构化字段；异常用 `logger.exception` 保留堆栈。
密码、令牌、完整密钥绝不能进日志。
配置用 `pydantic-settings` 从环境变量读取，密钥不入库、不入仓库。""",
                "next_lesson": "下一节部署：多进程、反向代理、健康检查与优雅退出。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-15-01",
                        "name": "日志配置与配置管理",
                        "goal": "能配置结构化日志并用 pydantic-settings 管理分层配置。",
                        "minutes": 50,
                        "criteria": "能写出带 extra 字段的日志与带默认值的配置模型，并说清哪些内容不能进日志。",
                        "requires": ["fastapi-backend-14-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-15-01-1",
                        "kp": 0,
                        "title": "加一个配置项并用起来",
                        "description": "给 `Settings` 加 `max_page_size: int = 100`，在分页依赖里使用它作为 size 上限。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")
    max_page_size: int = 100


settings = Settings()


def pagination(size: int = 20) -> dict:
    if size > settings.max_page_size:
        raise HTTPException(status_code=422, detail="size 超出上限")
    return {"size": size}''',
                        "explanation": "把上限做成配置，不同环境可以调，不需要改代码；校验逻辑仍集中在依赖里。",
                    },
                    {
                        "code": "fa-ex-15-01-2",
                        "kp": 0,
                        "title": "日志里能写什么",
                        "description": "判断以下内容能否进日志：① request_id ② 用户密码 ③ 完整 SQL 与参数 ④ 用户 ID ⑤ Authorization 头。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 可以，且应该有；
② 绝对不行；
③ 谨慎：生产一般只记慢查询与耗时，完整参数可能含敏感信息；
④ 可以（用于排查）；
⑤ 不行，令牌等价于密码。''',
                        "explanation": "判断标准：该信息泄漏后能否被直接用于登录或获取他人数据。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-15-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`Settings` 中字段 `database_url`，`env_prefix=\"APP_\"`，对应的环境变量名是？",
                        "options": [("A", "APP_DATABASE_URL"), ("B", "DATABASE_URL"), ("C", "app_database_url"), ("D", "APP.DATABASE_URL")],
                        "answer": {"value": "A"},
                        "explanation": "前缀 + 字段名大写，以下划线连接。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-15-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些不应出现在日志中？（多选）",
                        "options": [
                            ("A", "用户密码"),
                            ("B", "Authorization 头"),
                            ("C", "request_id"),
                            ("D", "完整 JWT"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "request_id 是排查必需的追踪信息，不敏感；其余三项泄漏后可直接冒用身份。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-15-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `logger.exception(...)` 相比 `logger.error(...)` 多了什么？",
                        "options": [
                            ("A", "自动附带当前异常的 traceback"),
                            ("B", "更高的日志级别"),
                            ("C", "自动发送告警"),
                            ("D", "自动脱敏"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`exception` 只能在 except 块中使用，会自动把堆栈写进日志，排查效率更高。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-15-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把 `.env` 提交到仓库没问题，只要仓库是私有的。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "私有仓库仍会因成员变动、误 fork、CI 日志等途径泄漏；秘密应通过环境变量或密钥管理服务注入且不落盘。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-15-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全日志语句，使日志带上 request_id 字段。横线处应填什么？\n\n```python\nlogger.info(\"处理完成\", ____={\"request_id\": \"trace-001\"})\n```",
                        "options": [("A", "extra"), ("B", "context"), ("C", "fields"), ("D", "kwargs")],
                        "answer": {"value": "A"},
                        "explanation": "logging 的标准参数是 `extra`，其中的键会合并到日志记录的属性里。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-15-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如何做到「关键配置缺失就拒绝启动」，而不是运行时才报错？",
                        "answer": {"value": "在 Settings 里把关键项声明为必填（不给默认值），pydantic-settings 会在实例化时抛 ValidationError；再在 lifespan 启动阶段读取一次配置并显式校验（如密钥长度、连接串格式、生产环境禁止默认密钥），失败就记录日志并让进程退出。这样部署时立刻失败，而不是等到第一个请求进来才暴露问题。"},
                        "explanation": "核心是「启动即校验（fail fast）」，把配置问题前移到部署阶段。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-15-lesson-02",
                "objectives": """1. 会按多进程方式启动服务，并解释 worker 与并发的对应关系；
2. 知道生产为什么不用 `--reload`；
3. 能配置健康检查、优雅退出与反向代理头；
4. 能写出一个可用的 Dockerfile 启动命令。""",
                "why_learn": """本地 `uvicorn --reload` 只能应付一个人开发。
生产要面对并发、进程崩溃重启、灰度发布与滚动更新——这些都需要正确的启动方式与生命周期管理。""",
                "concepts": """**Worker**：独立进程，各自持有一个事件循环；CPU 核数决定合适数量。
**不用 reload**：热重载会起 watcher 进程，多 worker 下反复重启。
**优雅退出**：收到 SIGTERM 后停止接收新请求，处理完存量请求再退出。
**反向代理**：Nginx 负责 TLS、静态资源、限流，并转发真实客户端 IP。
**健康检查**：`/health` 用于探针，需轻量且能反映依赖状态。""",
                "plain": """单进程像一个人值班：他再快，也只能同时处理有限的事。
多 worker 像多请几个人，每人一个窗口——但窗口之间的记事本不共享，所以会话状态不能放在进程内存里。
优雅退出像交接班：先把手上这单做完再走，而不是把盘子一放就跑。""",
                "syntax": """**API 说明**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
```

- `--workers` 设置进程数，通常为 CPU 核数或 2×核数+1（IO 密集可更高）。
- `--proxy-headers` 让应用信任 `X-Forwarded-For`，正确取到客户端 IP。
- `lifespan` 在启动/关闭时执行初始化与清理，替代已弃用的 `@app.on_event`。""",
                "example_code": '''from contextlib import asynccontextmanager

from fastapi import FastAPI

STATE: dict[str, bool] = {"ready": False}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化连接池、加载配置、预热缓存
    STATE["ready"] = True
    print("startup: 资源已就绪")
    try:
        yield
    finally:
        # 关闭：释放连接池，等待存量请求结束
        STATE["ready"] = False
        print("shutdown: 资源已释放")


app = FastAPI(title="生产部署示例", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok" if STATE["ready"] else "starting"}


@app.get("/ready")
def ready() -> dict:
    return {"ready": STATE["ready"]}''',
                "code_lines": """1. `asynccontextmanager` 定义 lifespan，取代旧版 `@app.on_event("startup")`。
2. `yield` 之前是启动逻辑，之后（`finally`）是关闭逻辑。
3. 把就绪状态放在模块级字典，接口据此回答探针——真实项目里换成连接池状态。
4. `/health` 用于存活探针：进程活着就返回 200，不查外部依赖。
5. `/ready` 用于就绪探针：依赖就绪才返回 ready，避免流量打到还没准备好的进程。
6. 关闭阶段释放连接池，是优雅退出的关键一步，否则可能出现「进程已停但连接未回收」。""",
                "output": """# 多进程启动
$ uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
INFO:     Started parent process [41022]
INFO:     Started server process [41024]
INFO:     Application startup complete.

# 探针
curl http://127.0.0.1:8000/health
{"status":"ok"}
curl http://127.0.0.1:8000/ready
{"ready":true}

# 优雅退出
$ kill -TERM 41022
INFO:     Shutting down
startup: 资源已就绪
shutdown: 资源已释放
INFO:     Finished server process [41024]""",
                "mistakes": """- 生产用 `--reload`，watcher 与多 worker 冲突，日志里反复重启。
- `--workers` 设成 32 而机器只有 4 核，进程互相抢 CPU。
- 把会话/限流计数放进程内存，多 worker 下数据不一致。
- 没有 `/health`，容器编排无法判断实例是否可用。
- 直接用 `uvicorn` 暴露公网，不做反向代理，TLS 与限流全缺。""",
                "error_analysis": """多 worker 下登录状态时有时无
—— 会话存在进程内存里。改用数据库/Redis 或 JWT 这类无状态方案。

`Invalid HTTP request received.` 且客户端 IP 全是代理地址
—— 没开 `--proxy-headers`，或 Nginx 未传 `X-Forwarded-For`。

滚动更新时出现 502
—— 进程被直接 kill，没有优雅退出。配置 `--timeout-graceful-shutdown` 并让编排先摘流量。""",
                "beginner_practice": """1. 用 `--workers 2` 启动，观察日志里出现多个 server process。
2. 用 `kill -TERM` 停止，确认打印了 shutdown 日志。""",
                "advanced_practice": """为一个真实项目写部署方案：进程数怎么定、健康检查怎么配、滚动更新时如何做到零 502、
日志如何收集，并给出一份 Dockerfile 的关键指令。""",
                "quiz_note": "本节 6 道题：2 道基础理解（worker 作用、为什么不用 reload）+ 2 道代码阅读（读 lifespan、读探针）+ 2 道应用练习（配 worker、写部署方案）。",
                "summary": """生产用多 worker 启动，不要开 `--reload`；进程数按核数与 IO 特性定。
`lifespan` 管理启动与关闭，关闭阶段要释放资源。
`/health` 判存活、`/ready` 判就绪，配合反向代理与优雅退出做到滚动更新不掉请求。""",
                "next_lesson": "下一节进入综合项目，从建目录开始把前面 23 个主题串起来。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-15-02",
                        "name": "生产部署与生命周期管理",
                        "goal": "能按生产要求启动服务并配置探针与优雅退出。",
                        "minutes": 45,
                        "criteria": "能写出带 lifespan 的应用，并说明多 worker 下哪些状态不能放内存。",
                        "requires": ["fastapi-backend-15-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-15-02-1",
                        "kp": 0,
                        "title": "补一个 lifespan",
                        "description": "给应用加 lifespan：启动时打印配置环境，关闭时释放一个模拟连接池；并说明为什么不能用 `@app.on_event`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"启动，环境={settings.env}")
    pool = {"open": True}
    try:
        yield {"pool": pool}
    finally:
        pool["open"] = False
        print("连接池已释放")

app = FastAPI(lifespan=lifespan)''',
                        "explanation": "`on_event` 已在较新版本中被标记弃用，`lifespan` 能同时覆盖启动与关闭且用上下文管理器表达更清晰。",
                    },
                    {
                        "code": "fa-ex-15-02-2",
                        "kp": 0,
                        "title": "worker 数与状态存放",
                        "description": "4 核机器、接口以数据库 IO 为主，worker 数怎么定？哪些状态不能放进程内存？",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''IO 密集型可设 (2×4)+1 ≈ 9，实际以压测为准；CPU 密集型接近核数。
不能放进程内存的状态：会话、限流计数、缓存、任务进度、WebSocket 连接表——多 worker 之间不共享。
放 Redis/数据库，或改成无状态（JWT + 客户端持有）。''',
                        "explanation": "多进程模型下内存不共享，这是所有「状态放哪」问题的根源。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-15-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "生产环境不建议使用 `--reload` 的原因是？",
                        "options": [
                            ("A", "会启动 watcher 进程并反复重启，与多 worker 冲突且耗资源"),
                            ("B", "会让接口返回 500"),
                            ("C", "会禁用 OpenAPI 文档"),
                            ("D", "会导致数据库不可用"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "热重载是开发期便利功能，生产应固定代码版本并稳定运行。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-15-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "生产部署通常需要的配置有？（多选）",
                        "options": [
                            ("A", "多 worker 或多进程"),
                            ("B", "健康检查接口"),
                            ("C", "反向代理与 TLS"),
                            ("D", "--reload 便于热更新"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "生产不用热重载，更新应通过重新发布/滚动更新完成。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-15-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `/ready` 在 `shutdown` 阶段会返回什么？",
                        "options": [("A", "{\"ready\": false}"), ("B", "{\"ready\": true}"), ("C", "404"), ("D", "连接被拒绝")],
                        "answer": {"value": "A"},
                        "explanation": "`finally` 里把 `STATE[\"ready\"]` 置为 False，进程尚未退出时探针就能读到 false。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-15-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把限流计数器存在进程内存里，在多 worker 部署下依然准确。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "每个 worker 各有一份内存，计数互不可见，总限额会被放大 N 倍。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-15-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全启动命令，使应用开 4 个进程并信任代理头。横线处应填什么？\n\n```bash\nuvicorn app.main:app --host 0.0.0.0 --port 8000 ____ --proxy-headers\n```",
                        "options": [("A", "--workers 4"), ("B", "--threads 4"), ("C", "--processes=4"), ("D", "--worker=4")],
                        "answer": {"value": "A"},
                        "explanation": "uvicorn 的参数是 `--workers`；`--threads` 是线程数，语义不同。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-15-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "滚动更新时如何避免 502？",
                        "answer": {"value": "① 先让新实例通过 `/ready` 探针再加入负载均衡；② 旧实例收到 SIGTERM 后先被摘流量，再等待存量请求处理完（`--timeout-graceful-shutdown`）；③ 关闭阶段释放连接池；④ 反向代理对上游做健康检查并重试；⑤ 更新分批进行，观察错误率再继续。"},
                        "explanation": "关键在于「先摘流量，再优雅退出」，顺序反了就会出现请求打到已退出进程的情况。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
