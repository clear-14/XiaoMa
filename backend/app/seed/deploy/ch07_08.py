"""软件工程与项目部署：第 7—8 章（日志与排障、综合项目部署实战）。"""

CHAPTERS: list[dict] = [
    # ==================================================================
    # 第 7 章 日志与排障
    # ==================================================================
    {
        "code": "software-engineering-deploy-07",
        "title": "日志与排障",
        "description": "线上问题靠证据定位，而不是靠猜。",
        "order_index": 7,
        "lessons": [
            {
                "code": "software-engineering-deploy-07-lesson-01",
                "objectives": """1. 能设计可检索的结构化日志格式；
2. 能正确使用日志级别，避免 DEBUG 灌满磁盘、ERROR 掩盖细节；
3. 会用请求 ID 把一次调用的多行日志串起来；
4. 能在日志中自动脱敏密钥与个人信息。""",
                "why_learn": """出问题时你有的不是现场，只有日志。
如果日志是「出错了」三个字，你只能靠猜；如果是结构化的一条 JSON，含请求 ID、用户、耗时、错误码，
你可以直接定位到那一次调用。日志质量决定了排障速度。""",
                "concepts": """**结构化日志**：JSON 或键值对，字段可被检索与聚合，而不是拼字符串。
**级别语义**：DEBUG（开发细节）、INFO（关键业务节点）、WARNING（可恢复异常）、ERROR（需人工介入）、CRITICAL（服务不可用）。
**请求 ID**：一次请求生成唯一 ID，贯穿所有日志，跨服务也能串起来。
**脱敏**：密钥、令牌、手机号、邮箱在写入前处理，日志是长期留存的数据。
**采样与轮转**：高频日志要采样，文件要按大小/时间轮转，否则磁盘会被写满。""",
                "plain": """日志像行车记录仪：平时没人看，出事时是唯一证据。
只录"出事了"没用，要录"几点几分、哪辆车、什么速度、撞了谁"。
请求 ID 是这次行程的编号，同一趟的所有片段都能凭编号找齐。
级别是"哪些要留、留多细"：DEBUG 是维修工看的全量数据，INFO 是运维需要的路标。
日记本还会写满——所以要有轮转：旧的归档，新的接着写。""",
                "syntax": """```python
import logging
import uuid

from fastapi import Request

logger = logging.getLogger("xiaoma.api")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/tasks/{task_id}")
def read_task(task_id: int, request: Request) -> dict:
    logger.info(
        "task.read",
        extra={"request_id": request.state.request_id, "task_id": task_id},
    )
    ...
```

- `extra=` 让字段进入 LogRecord，配合 JSON formatter 输出结构化字段。
- 不要用 f-string 拼日志内容，会失去检索能力，也更容易泄漏密钥。""",
                "example_code": '''# app/logging_config.py：JSON 日志 + 请求 ID + 脱敏
import json
import logging
import re
import sys
from datetime import datetime, timezone

SENSITIVE = re.compile(r"(sk-[A-Za-z0-9]{6})[A-Za-z0-9]+")


def mask(text: str) -> str:
    """把形如 sk-xxxx 的密钥替换为前 6 位 + ****。"""
    return SENSITIVE.sub(lambda m: f"{m.group(1)}****", text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": mask(record.getMessage()),
        }
        for key in ("request_id", "user_id", "path", "status", "duration_ms", "error_code"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = mask(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())''',
                "code_lines": """1. `SENSITIVE` 正则匹配 `sk-` 开头的密钥，命中后只保留前 6 位。
2. `JsonFormatter` 输出单行 JSON：既便于人读，也能被 ELK/Loki 直接解析字段。
3. 时间戳统一用 UTC + 毫秒，跨时区排查时不用换算。
4. `getattr(record, key, None)` 取出 `extra=` 传入的自定义字段，缺失就跳过。
5. `mask` 同时作用于消息与异常堆栈——堆栈里也可能带出请求参数中的密钥。
6. `configure_logging` 清空默认 handler，避免日志重复输出。
7. `level.upper()` 让 `info` 和 `INFO` 都能用，减少配置出错。""",
                "output": """{"ts":"2026-11-09T14:55:01.231Z","level":"INFO","logger":"xiaoma.api","msg":"task.read","request_id":"a1b2c3d4e5f6","user_id":"u-01","path":"/api/v1/tasks/42","status":200,"duration_ms":12}
{"ts":"2026-11-09T14:55:03.882Z","level":"ERROR","logger":"xiaoma.api","msg":"调用模型失败 key=sk-abc123****","request_id":"a1b2c3d4e5f6","error_code":"llm_timeout","duration_ms":60012}

# 按请求 ID 串起来看
$ grep '"request_id":"a1b2c3d4e5f6"' app.log | jq -c '{level,msg,duration_ms}'
{"level":"INFO","msg":"task.read","duration_ms":12}
{"level":"ERROR","msg":"调用模型失败 key=sk-abc123****","duration_ms":60012}

# 统计各接口 P95 耗时
$ cat app.log | jq -r 'select(.duration_ms) | "\\(.path) \\(.duration_ms)"' | sort -k2 -n | tail -3
/api/v1/chat/stream 8421
/api/v1/export 12033
/api/v1/chat/stream 15208""",
                "mistakes": """- 用 f-string 拼日志：`logger.info(f"user {u} did {x}")`，无法按字段检索。
- 生产环境开 DEBUG，一周写几十 GB 日志还拖慢服务。
- 日志里打印完整请求体，把密码、令牌一起写进去。
- 每个请求生成多个 ID，或者在异步任务里丢失了 request_id。
- 日志文件不轮转，磁盘满了导致服务崩溃——用日志排查问题的工具变成了故障原因。""",
                "error_analysis": """日志里找不到某个请求
—— 中间件没生效（路由顺序），或异步任务在独立上下文里没传 request_id。

`KeyError: 'request_id'`
—— `request.state.request_id` 未设置就访问。中间件要在 `call_next` 之前赋值。

JSON 日志无法解析
—— 消息里混入了换行或未转义字符。`json.dumps` 会处理，但手工拼接就会坏。

日志量暴涨
—— 循环里打 INFO，或把整个响应体打进日志。给高频日志降级或采样。""",
                "beginner_practice": """1. 给项目加上请求 ID 中间件，验证响应头里有 `X-Request-ID`，日志里能按它串起来。
2. 把一条 f-string 日志改成结构化 `extra=` 写法，对比检索体验。""",
                "advanced_practice": """设计日志方案：JSON 格式、字段清单、级别策略（哪些用 INFO、哪些用 WARNING）、
脱敏规则、轮转与保留。完成后回答：为什么日志里不该记录完整请求体与响应体？""",
                "quiz_note": "本节 6 道题：2 道基础理解（日志级别、请求 ID 作用）+ 2 道输出阅读（读 JSON 日志、读脱敏结果）+ 2 道应用练习（选对写法、判断脱敏必要性）。",
                "summary": """结构化日志让字段可检索、可聚合，是排障的基础。
请求 ID 把一次调用的所有日志串成一条线。
级别要克制：生产 INFO 起，DEBUG 只在需要时临时打开。
日志长期留存，写之前就要脱敏；同时必须轮转，否则会变成故障源。""",
                "next_lesson": "有了日志，下一节按「入口—服务—依赖—数据」逐层定位线上故障。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-07-01",
                        "name": "结构化日志与请求追踪",
                        "goal": "能输出含请求 ID 的结构化日志，并正确分级、脱敏与轮转。",
                        "minutes": 35,
                        "criteria": "能实现请求 ID 中间件与 JSON formatter，并用 grep/jq 按字段检索出一次完整调用链路。",
                        "requires": ["software-engineering-deploy-06-04"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-07-01-1",
                        "kp": 0,
                        "title": "改造这条日志",
                        "description": """现有代码：

```python
logger.info(f"用户 {user_id} 调用模型失败，key={api_key}，耗时 {ms}ms")
```

指出问题并改写成结构化写法（含脱敏）。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''问题：
1. 泄漏密钥：`key={api_key}` 把完整 Key 写进日志，日志成了泄漏源；
2. 无法检索：f-string 拼成一段文本，想按 user_id 聚合只能正则硬匹配；
3. 级别不当：模型调用失败属于可恢复异常，多数场景应是 WARNING 或 ERROR（视是否影响用户）；
4. 字段名缺失：`耗时` 无法被程序解析。

改写：
```python
logger.warning(
    "llm.call_failed",
    extra={
        "user_id": user_id,
        "key_masked": mask_key(api_key),
        "duration_ms": ms,
        "error_code": "llm_timeout",
    },
)
```

这样既能按 `user_id` 聚合错误率，也无法从日志还原出可用密钥。''',
                        "explanation": """日志字段化之后，"统计某用户失败率"这类问题从写脚本变成一条查询。""",
                    },
                    {
                        "code": "sed-ex-07-01-2",
                        "kp": 0,
                        "title": "补全请求 ID 中间件",
                        "description": """补全中间件：优先复用客户端传入的 `X-Request-ID`，没有则生成，
并把它写进 `request.state` 与响应头。""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''```python
import uuid
from fastapi import Request

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id      # 必须在 call_next 之前
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

要点：
1. 复用客户端 ID 可以让跨服务链路串起来；但要限制长度与字符集，避免日志注入；
2. `request.state` 赋值必须在 `call_next` 之前，否则下游拿不到；
3. 响应头返回该 ID，用户报障时可以直接提供，比"大概几点几分"精确得多。''',
                        "explanation": "请求 ID 的价值在跨服务与跨日志：一处生成，处处引用。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-07-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "生产环境通常应把日志级别设为？",
                        "options": [
                            ("A", "DEBUG"),
                            ("B", "INFO"),
                            ("C", "ERROR"),
                            ("D", "关闭日志"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "INFO 覆盖关键业务节点；DEBUG 会写出巨量日志并影响性能，只在排障时临时开启。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-07-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "结构化日志相比字符串拼接的优势有？（多选）",
                        "options": [
                            ("A", "字段可被检索与聚合"),
                            ("B", "便于接入日志平台做统计"),
                            ("C", "自动让程序更快"),
                            ("D", "便于统一做脱敏处理"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 与日志格式无关；结构化反而略增开销，但换来的是可分析性。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-07-01-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "日志输出 `key=sk-abc123****`，说明？",
                        "options": [
                            ("A", "密钥本身就是这样"),
                            ("B", "已做脱敏处理，只保留前缀"),
                            ("C", "密钥被截断导致不可用"),
                            ("D", "日志被截断"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "脱敏保留少量前缀便于辨认，完整值不出现在日志中。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-07-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": """日志每行一条 JSON 且都带 `request_id`。写出按单个请求还原调用链的命令，并说明输出能回答什么问题。""",
                        "answer": {"reference": "`grep '\"request_id\":\"a1b2\"' app.log` 取出该请求的全部日志行，再按 `ts` 排序即得到完整调用链：可以回答请求经过了哪些环节、耗时集中在哪一步、错误发生在哪里。", "keywords": ["grep", "request_id", "排序", "调用链"]},
                        "explanation": "这就是请求 ID 的核心价值：把分散的日志还原成一次调用的完整故事。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-07-01-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "在日志中附带自定义字段（如 user_id），应使用 logging 的哪个参数？",
                        "options": [
                            ("A", "extra="),
                            ("B", "fields="),
                            ("C", "context="),
                            ("D", "meta="),
                        ],
                        "answer": {"value": "A"},
                        "explanation": """`extra={"user_id": ...}` 把字段挂到 LogRecord 上，formatter 再输出。""",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-07-01-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "日志只需要记录错误，正常请求不用记，这样可以节省空间。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": """没有正常路径的基线，就无法判断"变慢""错误率升高"。INFO 级关键节点是必需的。""",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-07-lesson-02",
                "objectives": """1. 能按「入口 → 服务 → 依赖 → 数据」四层定位故障；
2. 能针对 502、504、空响应、超时给出排查顺序；
3. 会用请求 ID 在日志中还原一次失败调用；
4. 能区分「配置问题」「资源问题」「代码问题」三类根因。""",
                "why_learn": """线上报障只给你一句话：「打不开了」。
没有固定排查顺序，就会在十几个可能里随机试，既慢又容易改出新问题。
把排查拆成四层，每层用一个命令验证，能在一两分钟内把范围缩小到一层。""",
                "concepts": """**四层模型**：入口（DNS/代理/证书）→ 服务（进程/健康）→ 依赖（数据库/缓存/外部 API）→ 数据（内容/索引/一致性）。
**502 与 504**：前者代理连不上上游，后者上游响应超时。
**空响应**：200 但 body 为空，多为前端解析失败或后端返回 None。
**根因三分**：配置（改个变量就好）、资源（磁盘/内存/连接数）、代码（要发版）。
**先止血后定位**：影响面大时先回退再查，不要在故障中做实验。""",
                "plain": """排查像修水管：先看水表有没有水（入口），再看自家总阀（服务），
再看是不是楼下停水（依赖），最后才拆管看里面堵没堵（数据）。
跳步会浪费大量时间——比如"页面打不开"就去改代码，实际是证书过期。
止血和定位是两件事：水漫出来先关总阀（回退），再慢慢找漏点。""",
                "syntax": """**四层排查命令**

```bash
# 1. 入口：DNS、证书、代理
nslookup xiaoma.example.com
curl -I https://xiaoma.example.com
openssl s_client -connect xiaoma.example.com:443 -servername xiaoma.example.com < /dev/null

# 2. 服务：进程与健康
docker compose ps
curl -fsS http://127.0.0.1:3000/api/v1/health
docker compose logs --tail 50 backend

# 3. 依赖：数据库与外部接口
docker compose exec backend python -c "import sqlite3;print(sqlite3.connect('/app/data/xiaoma.db').execute('select 1').fetchone())"
docker compose exec frontend sh -c "wget -qO- http://backend:8000/api/v1/health"

# 4. 数据：内容是否真的在
docker compose exec backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/xiaoma.db')
print('courses', c.execute('select count(*) from courses').fetchone()[0])
"
```

- 每层只用一个命令做"通过/不通过"判断，不通过就停在这一层。
- 四层全通过而问题仍在 → 大概率是前端缓存或浏览器侧。""",
                "example_code": '''# 场景：用户报「课程体系打不开」，按四层定位

# ---------- 第 1 层：入口 ----------
curl -sI https://xiaoma.example.com/
# HTTP/2 200    ← 入口正常
curl -s https://xiaoma.example.com/api/v1/health
# {"status":"ok","version":"1.4.1"}   ← 代理到后端也通

# ---------- 第 2 层：服务 ----------
docker compose ps
# xiaoma-backend    Up 2 hours (healthy)
# xiaoma-frontend   Up 2 hours (healthy)     ← 服务正常

# ---------- 第 3 层：依赖 ----------
curl -s "https://xiaoma.example.com/api/v1/courses/llm-api" | head -c 120
# {"id":"...","code":"llm-api","knowledge_point_count":0,   ← 异常：0！

# ---------- 第 4 层：数据 ----------
docker compose exec -T backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/xiaoma.db')
for t in ('courses','chapters','lessons','knowledge_points','course_contents'):
    print(t, c.execute(f'SELECT count(*) FROM {t}').fetchone()[0])
"
# courses 7
# chapters 93
# lessons 175
# knowledge_points 31         ← 只有 31 个（应为 194）
# course_contents 0           ← 正文完全没有

# ---------- 结论 ----------
# 根因：容器数据卷里的库只跑过 seed-courses，缺教材种子。
# 处置：补跑 5 个种子命令（幂等），并修启动脚本防止复发。
docker compose exec backend python -m app.cli seed-textbook
docker compose exec backend python -m app.cli seed-phase4a''',
                "code_lines": """1. 第 1 层用两条命令：页面可达 + 健康接口可达，能立刻区分"整站挂了"还是"某个功能坏了"。
2. 第 2 层看容器与健康状态：Up 但 unhealthy 说明进程在但服务不可用。
3. 第 3 层直接请求具体业务接口，把范围从"整站"缩到"一个功能"。
4. 关键动作：看响应里的具体字段（`knowledge_point_count: 0`），而不是只看 200。
5. 第 4 层查数据库实际行数，用数据说话——这一步能区分"代码过滤掉了"和"数据本来就没有"。
6. 对比预期值（194）与实际值（31），量化缺口，根因就浮出来了。
7. 结论直接对应处置方式：数据缺失 → 补种子，而不是改代码或调配置。""",
                "output": """$ curl -sI https://xiaoma.example.com/ | head -1
HTTP/2 200

$ docker compose ps
NAME              STATUS
xiaoma-backend    Up 2 hours (healthy)
xiaoma-frontend   Up 2 hours (healthy)

$ curl -s "http://127.0.0.1:3000/api/v1/courses/llm-api" \\
  | python -c "import json,sys;d=json.load(sys.stdin);print(d['chapter_count'],d['lesson_count'],d['knowledge_point_count'])"
16 32 0

$ docker compose exec -T backend python -c "
import sqlite3
c=sqlite3.connect('/app/data/xiaoma.db')
print('kp', c.execute('select count(*) from knowledge_points').fetchone()[0])
print('contents', c.execute('select count(*) from course_contents').fetchone()[0])
"
kp 31
contents 0

# 补种子后
$ docker compose exec backend python -m app.cli seed-phase4c
教材种子完成：新增知识点 32，新增内容 32，...

$ curl -s "http://127.0.0.1:3000/api/v1/courses/llm-api" \\
  | python -c "import json,sys;print(json.load(sys.stdin)['knowledge_point_count'])"
32""",
                "mistakes": """- 一上来就改代码，跳过"数据是否真的在"这一层。
- 只看 HTTP 200 就判断正常，不看响应体里的业务字段。
- 在故障期间直接 `down -v` 重置环境，把现场证据全毁了。
- 只查应用日志，不看代理日志（`error.log` 里明确写着 502/504 的原因）。
- 把多个问题混在一起改，改完不知道哪个生效、哪个引入了新问题。""",
                "error_analysis": """**502 Bad Gateway**
排查：`docker compose ps`（上游在不在）→ `docker compose logs backend`（起来了吗）→ 网络是否同一 compose 网络。

**504 Gateway Timeout**
排查：`error.log` 是否 `upstream timed out` → 接口是否慢（慢查询/外部 API）→ 该 location 的超时是否够。

**200 但响应体为空 / 页面空白**
排查：响应体是否 `null` 或空数组 → 数据库是否有数据 → 前端是否因字段缺失渲染失败。

**整站 5xx 且有迁移记录**
排查：迁移是否失败。`docker compose logs backend` 里会有迁移报错，此时应先恢复到上一个镜像。

**只有部分用户报错**
排查：是否证书链问题、CDN 缓存、地域网络；用 `curl` 从不同出口验证。""",
                "beginner_practice": """1. 按四层模型排查一次"页面打不开"，记录每层用的命令与结论。
2. 人为删掉数据库里的一张表数据，用四层模型定位到"数据层"。""",
                "advanced_practice": """构造一个"接口 504"的场景（例如在接口里 `time.sleep(200)`），
用四层模型定位，并说明：为什么这类问题不该靠改代码解决，而应调超时或改异步？""",
                "quiz_note": "本节 6 道题：2 道基础理解（四层模型、止血优先）+ 2 道输出阅读（读 502/504 日志、读数据行数）+ 2 道应用练习（选对排查顺序、判断根因类型）。",
                "summary": """排查按四层走：入口 → 服务 → 依赖 → 数据，每层一个命令做通过/不通过判断。
502 是连不上，504 是太慢，两者方向完全不同。
200 不等于正常，要看响应体里的业务字段。
影响面大时先回退止血，再在安全环境里定位。""",
                "next_lesson": "故障之后要提前发现——下一节讲监控指标与告警阈值。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-07-02",
                        "name": "四层排障法与常见故障定位",
                        "goal": "能按入口-服务-依赖-数据四层定位故障，并区分配置/资源/代码三类根因。",
                        "minutes": 40,
                        "criteria": "能在不看答案的情况下按四层走完一次真实故障定位，并正确判断应补数据、调配置还是改代码。",
                        "requires": ["software-engineering-deploy-07-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-07-02-1",
                        "kp": 0,
                        "title": "给现象配排查路径",
                        "description": """三个现象，各写出第一层该查什么、用什么命令。
(1) 整站打开是 502
(2) 页面能开，但所有接口 504
(3) 页面能开，接口 200 但列表是空的""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''(1) 502：先查服务层——上游是否在跑。
```bash
docker compose ps
docker compose logs --tail 50 backend
```
若后端 Exited，看日志里的启动错误（配置校验、迁移失败）。

(2) 504：先查入口层日志定位是哪一跳慢。
```bash
tail -50 /var/log/nginx/error.log | grep timed out
curl -o /dev/null -w "%{time_total}\\n" http://127.0.0.1:8000/api/v1/health
```
区分"后端整体慢"还是"某个接口慢"，再看该接口是否依赖外部服务。

(3) 200 但空：直接跳到数据层。
```bash
docker compose exec -T backend python -c "
import sqlite3;c=sqlite3.connect('/app/data/xiaoma.db')
print(c.execute('select count(*) from knowledge_points').fetchone()[0])"
```
数据为 0 → 种子未跑；数据有但接口返回空 → 查询条件/软删除/发布状态过滤问题。

三个现象对应三层不同的第一站，这就是固定顺序的价值。''',
                        "explanation": """先按现象选层，再按层选命令，比"从日志第一行开始读"高效得多。""",
                    },
                    {
                        "code": "sed-ex-07-02-2",
                        "kp": 0,
                        "title": "根因分类",
                        "description": """判断下列四个故障各属于配置、资源还是代码问题，并说明处置方式。
(1) 磁盘写满导致服务不可用
(2) 生产日志级别是 DEBUG，磁盘一周涨 40GB
(3) 接口返回 500，堆栈显示除零
(4) 证书过期""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''(1) 资源问题：清理旧镜像/日志，并加磁盘告警与轮转策略。不需要发版。
(2) 配置问题：改 LOG_LEVEL 并重建容器，同时把它写进差异清单防复发。不需要发版。
(3) 代码问题：需要修复并发布新版本；紧急时先回退到上一个版本止血。
(4) 配置/运维问题：续期证书并 reload，同时检查自动续期链路。

分类的意义在于决定"要不要发版、要多久"：
配置与资源类通常分钟级解决，代码类要走发布流程。''',
                        "explanation": "先分类再动手，能避免用发版去解决一个改配置就好的问题。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-07-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "四层排障法的正确顺序是？",
                        "options": [
                            ("A", "数据 → 依赖 → 服务 → 入口"),
                            ("B", "入口 → 服务 → 依赖 → 数据"),
                            ("C", "代码 → 日志 → 数据库 → 网络"),
                            ("D", "随机尝试，哪个快先试哪个"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "从外到内逐层排除，每层一个命令判断通过与否，范围快速收敛。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-07-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "页面能打开但功能异常，应优先检查？（多选）",
                        "options": [
                            ("A", "业务接口的响应体内容"),
                            ("B", "数据库是否有对应数据"),
                            ("C", "DNS 是否解析"),
                            ("D", "查询条件是否过滤掉了数据"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": """C 已被"页面能打开"排除，说明 DNS 与入口正常。""",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-07-02-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "日志 `upstream timed out (110: Connection timed out)` 对应客户端看到的状态码是？",
                        "options": [("A", "502"), ("B", "504"), ("C", "500"), ("D", "408")],
                        "answer": {"value": "B"},
                        "explanation": "超时是 504；连接被拒或无效响应是 502。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-07-02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """接口返回正常但字段为 0：

```
{"chapter_count":16,"lesson_count":32,"knowledge_point_count":0}
```

下一步最该做的是？""",
                        "options": [
                            ("A", "改前端渲染逻辑"),
                            ("B", "查数据库对应表的实际行数"),
                            ("C", "重启 Docker"),
                            ("D", "重新申请证书"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "字段为 0 要么数据缺失，要么被过滤。查行数能一步区分。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-07-02-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "影响大量用户且能秒级回退时，正确的第一动作是？",
                        "options": [
                            ("A", "先回退止血，再定位"),
                            ("B", "先定位根因，再决定回退"),
                            ("C", "先扩容"),
                            ("D", "先通知用户等待"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "不要在生产故障中做实验。回退是秒级操作，定位可以之后在安全环境做。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-07-02-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "HTTP 200 就说明接口完全正常，不需要检查响应体。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "200 只表示请求被处理，业务失败可能仍以 200 返回，必须看响应体字段。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-07-lesson-03",
                "objectives": """1. 能定义四类关键指标（可用性、延迟、错误率、饱和度）；
2. 能为每类指标设置合理阈值，并区分「告警」与「看板」；
3. 能设计容量预警（磁盘、连接数、内存）；
4. 知道告警太多会导致「告警疲劳」，如何收敛。""",
                "why_learn": """用户报障永远比监控晚。一次证书过期在 90 天后爆发，但如果监控证书剩余天数，你能提前 15 天知道。
监控的价值不是"看板好看"，而是"在用户之前发现"。而告警太多等于没有告警——没人会认真看一天 200 条通知。""",
                "concepts": """**四黄金信号**：延迟（Latency）、流量（Traffic）、错误（Errors）、饱和度（Saturation）。
**告警 vs 看板**：告警是"需要人现在动手"，看板是"随时可查"。混在一起会导致告警疲劳。
**容量预警**：磁盘 80%（预警）/90%（告警）、内存持续 >85%、数据库连接数接近上限。
**阈值要分层**：warning 提前量、critical 需要立即响应。
**告警必须可执行**：每条告警都应附带"该怎么办"的链接或概要。""",
                "plain": """监控像体检：血压偏高（预警）提醒你调整作息，胸痛（告警）要立刻去急诊。
如果每天给你发 200 条"注意身体"的短信，你很快就会全部忽略——这就是告警疲劳。
好指标是可行动的：看到它你就知道下一步做什么。看到"CPU 62%"你什么都做不了，
看到"磁盘 91%，预计 6 小时后写满"你知道该清理还是扩容。""",
                "syntax": """**四黄金信号对应指标**

```
延迟   : p50 / p95 / p99 响应时间（按接口分）
流量   : QPS、并发连接数
错误   : 5xx 比例、业务失败率、模型调用失败率
饱和度 : 磁盘使用率、内存使用率、CPU、数据库连接数
```

**阈值示例**

| 指标 | 预警 | 告警 | 说明 |
|---|---|---|---|
| 5xx 比例 | > 1%（5 分钟） | > 5%（5 分钟） | 需同时看绝对请求量 |
| p95 延迟 | > 2s | > 5s | 按接口分别设 |
| 磁盘使用率 | > 80% | > 90% | 结合增长速度预估写满时间 |
| 证书剩余天数 | < 21 天 | < 7 天 | 提前量要大于续期失败后的排查时间 |
| 容器重启次数 | > 3 次/小时 | > 10 次/小时 | 频繁重启是崩溃循环的信号 |

**采集示例（Docker 层面）**

```bash
docker stats --no-stream --format "table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.NetIO}}"
df -h /                        # 磁盘
docker compose ps              # 健康状态
```""",
                "example_code": '''# scripts/check_capacity.sh：一条命令输出关键容量信号
#!/usr/bin/env bash
set -euo pipefail

echo "== 磁盘 =="
df -h / | awk 'NR==2 {print "使用率 " $5 "，剩余 " $4}'

echo "== 容器资源 =="
docker stats --no-stream --format "table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}"

echo "== 健康状态 =="
docker compose ps --format "table {{.Name}}\\t{{.Status}}"

echo "== 证书剩余天数 =="
end=$(date -d "$(openssl x509 -in /etc/letsencrypt/live/xiaoma.example.com/fullchain.pem \\
      -noout -enddate | cut -d= -f2)" +%s 2>/dev/null || echo 0)
now=$(date +%s)
if [ "$end" -gt 0 ]; then
  echo "剩余 $(( (end - now) / 86400 )) 天"
else
  echo "证书读取失败"
fi

echo "== 备份最新时间 =="
ls -lt /backup/*.db 2>/dev/null | head -1 | awk '{print $6, $7, $8, $9}'

echo "== 接口延迟（3 次取均值）=="
for i in 1 2 3; do
  curl -s -o /dev/null -w "%{time_total}\\n" http://127.0.0.1:3000/api/v1/health
done | awk '{s+=$1} END {printf "均值 %.3f 秒\\n", s/NR}'

echo "== 日志体积 =="
du -sh /app/data/logs 2>/dev/null || echo "无日志目录"''',
                "code_lines": """1. 磁盘是容器环境最常见的隐性故障源：日志、镜像、备份都会涨。
2. `docker stats` 给出 CPU 与内存实时用量，能发现"内存缓慢上涨"（泄漏特征）。
3. 健康状态比进程存在更重要：`unhealthy` 要立即看，不要等到用户报障。
4. 证书剩余天数是最容易被忽略的定时炸弹，必须纳入检查。
5. 备份最新时间能验证"备份任务今天有没有跑"——很多事故发现时备份已停更一周。
6. 接口延迟用 3 次均值减少抖动，单次数值容易误判。
7. 日志体积单独统计：它是磁盘增长的主要来源，也是可以主动压缩的部分。""",
                "output": """$ ./scripts/check_capacity.sh
== 磁盘 ==
使用率 46%，剩余 52G
== 容器资源 ==
NAME              CPU %     MEM USAGE / LIMIT
xiaoma-backend    1.24%     186.4MiB / 7.7GiB
xiaoma-frontend   0.31%     92.1MiB / 7.7GiB
== 健康状态 ==
xiaoma-backend    Up 3 hours (healthy)
xiaoma-frontend   Up 3 hours (healthy)
== 证书剩余天数 ==
剩余 78 天
== 备份最新时间 ==
Nov 9 22:55 /backup/xiaoma-20261109-225501.db
== 接口延迟（3 次取均值）==
均值 0.014 秒
== 日志体积 ==
38M     /app/data/logs

# 磁盘告警期的样子
$ df -h /
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        59G   54G  2.1G  97% /

# 告警消息（可执行）
[CRITICAL] 磁盘使用率 97%，按近 7 天增速预计 4 小时后写满
处置：1) docker system prune -f 2) 清理 /app/data/logs 3) 检查备份保留策略
链接：https://wiki.internal/runbook/disk-full""",
                "mistakes": """- 只监控 CPU，不监控磁盘与证书，结果被最常见的问题打穿。
- 每条请求超时就告警，一天几百条，最后全部静音。
- 告警没有处置建议，收到的人不知道该做什么。
- 阈值拍脑袋定：p95 延迟在正常业务下本来就是 3 秒，却设 2 秒告警。
- 只做看板不做告警，等于只是把问题可视化，没人会盯着看。""",
                "error_analysis": """告警风暴（同一故障触发几百条）
—— 缺少聚合与抑制：应按服务与故障类型聚合，或在根因告警后抑制衍生告警。

告警长期静音、出事没通知
—— 告警疲劳导致。减少低价值告警，只保留"需要立刻动手"的。

`docker stats` 显示内存持续上涨不回落
—— 内存泄漏特征。先加重启策略止血，再定位（通常与缓存无上限或连接未关闭有关）。

备份时间停留在几天前
—— 备份任务静默失败。必须监控"最后一次成功时间"，而不是"备份文件是否存在"。""",
                "beginner_practice": """1. 写一个容量检查脚本，输出磁盘、容器资源、证书剩余天数、备份时间。
2. 为核心接口定三档延迟阈值，说明为什么 p95 比均值更适合做告警。""",
                "advanced_practice": """为项目设计告警清单：指标、阈值（预警/告警）、触发后的处置动作、是否可自动恢复。
验收：清单里每条告警都能回答"收到后我要做什么"，且总条数不超过 10 条。""",
                "quiz_note": "本节 6 道题：2 道基础理解（四黄金信号、告警疲劳）+ 2 道输出阅读（读容量脚本输出、读告警文本）+ 2 道应用练习（选对阈值、判断该告警还是看板）。",
                "summary": """四黄金信号：延迟、流量、错误、饱和度，覆盖绝大多数线上问题。
告警只留给"需要现在动手"的事，其余放看板。
容量要预警而非等爆：磁盘、证书、备份时效、连接数都要盯。
每条告警都要能回答"收到后做什么"，否则就是噪音。""",
                "next_lesson": "前面都是单点能力，最后一章把前端、后端、数据库与 Agent 服务一起上线。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-07-03",
                        "name": "监控指标与容量告警",
                        "goal": "能基于四黄金信号定义指标与阈值，并设计可执行的容量告警。",
                        "minutes": 35,
                        "criteria": "能产出不超过 10 条的告警清单，每条都含阈值与处置动作，并覆盖磁盘、证书与备份时效。",
                        "requires": ["software-engineering-deploy-07-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-07-03-1",
                        "kp": 0,
                        "title": "收敛告警",
                        "description": """现有 12 条告警：4 条是"接口响应超过 1.5 秒"、3 条是"CPU 超过 60%"、
2 条是"内存超过 70%"、2 条是"证书 30 天内到期"、1 条是"磁盘 95%"。
如何收敛成一份可执行的清单？""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''问题诊断：
- 4 条"响应超 1.5 秒"过于敏感且重复：应合并为一条按接口的 p95 阈值，且阈值按基线定（若常态 1.2 秒，1.5 秒会天天响）。
- 3 条"CPU 60%"属于看板指标，不是告警：CPU 60% 通常无需动手。
- 2 条"内存 70%"同理，改为"持续 15 分钟 > 85%"才有意义。
- 2 条证书告警重复：合并为"剩余 < 21 天预警、< 7 天告警"。
- 磁盘 95% 才告警太晚：应为 80% 预警、90% 告警。

收敛后（6 条）：
1. [告警] 5xx 比例 > 5%（5 分钟）
2. [告警] 核心接口 p95 > 5 秒（5 分钟）
3. [告警] 磁盘 > 90%（预警 80%）
4. [告警] 证书剩余 < 7 天（预警 21 天）
5. [告警] 容器频繁重启 > 10 次/小时
6. [告警] 备份最后成功时间 > 36 小时

其余全部移入看板。每条都要附处置链接。''',
                        "explanation": "告警的数量与可信度成反比：条数越少，被认真对待的概率越高。",
                    },
                    {
                        "code": "sed-ex-07-03-2",
                        "kp": 0,
                        "title": "为什么监控备份时效",
                        "description": """为什么"备份最后成功时间"比"备份文件是否存在"更重要？举例说明。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''因为备份会"静默失败"：
- cron 任务因为权限变化失败了，但旧备份文件还在 → 检查"是否存在"仍然通过；
- 磁盘满了导致备份写入中断，可能留下一个 0 字节或半截的文件 → 存在但不可用；
- 数据库名改了，备份脚本还指向旧路径 → 每天"成功"但备的是空内容。

监控"最后成功时间"（例如超过 36 小时未更新就告警）能覆盖这三种情况：
它检查的是"最近一次真的成功了吗"，而不是"有没有留下痕迹"。

配套做法：
1. 备份脚本要输出明确成功标记（含行数与 integrity_check 结果）；
2. 监控读取该标记的时间戳；
3. 定期跑恢复演练，验证备份内容可用（前两节讲过）。''',
                        "explanation": """监控要盯"真实的成功"，而不是"看起来存在的产物"。""",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-07-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "四黄金信号不包括？",
                        "options": [
                            ("A", "延迟"),
                            ("B", "错误"),
                            ("C", "饱和度"),
                            ("D", "代码行数"),
                        ],
                        "answer": {"value": "D"},
                        "explanation": "黄金信号是延迟、流量、错误、饱和度，与代码规模无关。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-07-03-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "导致告警疲劳的常见原因有？（多选）",
                        "options": [
                            ("A", "阈值过于敏感，正常波动也触发"),
                            ("B", "同类告警重复多条"),
                            ("C", "告警没有处置建议"),
                            ("D", "告警只发给一个人"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 与疲劳关系不大；前三者会让接收者逐渐忽略所有告警。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-07-03-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """告警文本：

```
[CRITICAL] 磁盘使用率 97%，按近 7 天增速预计 4 小时后写满
处置：1) docker system prune -f 2) 清理日志 3) 检查备份保留策略
```

这条告警好在哪里？""",
                        "options": [
                            ("A", "用了红色图标"),
                            ("B", "给出了影响预测与可执行的处置步骤"),
                            ("C", "包含 CPU 数据"),
                            ("D", "发送给了所有人"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "可执行性是好告警的核心：收到就知道做什么，不需要再查文档。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-07-03-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`docker stats` 显示某容器内存持续上涨、重启后回落，这通常说明？",
                        "options": [
                            ("A", "正常缓存行为，无需关注"),
                            ("B", "可能存在内存泄漏"),
                            ("C", "CPU 不足"),
                            ("D", "网络抖动"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "持续上涨且重启后回落是泄漏的典型特征；若只是缓存会趋于稳定。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-07-03-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "磁盘使用率应在什么区间设置预警与告警更合理？",
                        "options": [
                            ("A", "预警 80%，告警 90%"),
                            ("B", "预警 95%，告警 99%"),
                            ("C", "预警 50%，告警 60%"),
                            ("D", "只在 100% 时告警"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "要留出清理或扩容的时间窗口；95% 才预警往往来不及处理。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-07-03-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "CPU 使用率 60% 应该配置为告警，让人立刻处理。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "60% 属于正常波动，无需动手。这类指标应放看板，告警只留给需要立刻行动的情况。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },

    # ==================================================================
    # 第 8 章 综合项目部署实战
    # ==================================================================
    {
        "code": "software-engineering-deploy-08",
        "title": "综合项目部署实战",
        "description": "把前端、后端、数据库与 Agent 服务一起上线。",
        "order_index": 8,
        "lessons": [
            {
                "code": "software-engineering-deploy-08-lesson-01",
                "objectives": """1. 能把前端、后端、数据库三者的连接关系画清楚并验证；
2. 能定位跨域、代理、会话三类联调问题；
3. 会为前后端分离与同源代理两种架构做取舍；
4. 能设计一条覆盖核心链路的联调验收清单。""",
                "why_learn": """单看每个服务都正常，合在一起就出问题——这是联调阶段的典型状态。
原因通常是"谁访问谁"的路径没人完整走过一遍：前端以为调的是同源接口，
后端以为前端会带 Cookie，代理以为路径会原样转发。
联调的本质是把这条链路每一跳都验证一次。""",
                "concepts": """**两种架构**：同源代理（前端服务端转发 `/api`）与前后端分离（浏览器直连后端，需 CORS）。
**同源代理的优势**：无 CORS、Cookie 与令牌自动携带、后端可不暴露端口。
**CORS 三要素**：`Access-Control-Allow-Origin`、`-Methods`、`-Headers`，凭证请求下 Origin 不能为 `*`。
**会话载体**：Cookie（同源自动带）与 Bearer Token（需前端显式加头）。
**联调清单**：静态页 → 健康接口 → 业务读接口 → 业务写接口 → 长连接/流式。""",
                "plain": """同源代理像公司前台统一收发：外面只认前台地址，内部转给各部门，不需要每个部门都对外挂牌。
前后端分离像各部门直接对外，那就要给每个部门配通行证规则（CORS），少一条就有人进不来。
联调就是"从大门走到工位"实地走一遍：门禁（DNS/证书）、前台（代理）、部门（后端）、
档案柜（数据库）、最后是实时对讲（流式）有没有延迟。""",
                "syntax": """**同源代理（推荐）**

```python
# Next.js: app/api/v1/[...path]/route.ts
const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000";

async function proxy(request: Request, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const url = new URL(request.url);
  const target = `${BACKEND}/api/v1/${path.join("/")}${url.search}`;
  const upstream = await fetch(target, {
    method: request.method,
    headers: request.headers,
    body: request.method === "GET" ? undefined : request.body,
    duplex: "half",
  } as RequestInit);
  return new Response(upstream.body, {
    status: upstream.status,
    headers: upstream.headers,
  });
}
```

**前后端分离（需 CORS）**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],   # 凭证模式下不能是 *
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- 同源代理不需要 CORS 配置，这是它最实际的优势。
- 分离架构要显式列出前端域名，`*` 与 `allow_credentials=True` 不能共存。""",
                "example_code": '''# 联调验收：按链路顺序逐跳验证（每步都要通过才往下走）

# ---- 1. 静态资源（前端容器） ----
curl -sI http://127.0.0.1:3000/ | head -3
# HTTP/1.1 200 OK

# ---- 2. 健康接口（代理链路） ----
curl -s http://127.0.0.1:3000/api/v1/health
# {"status":"ok","service":"xiaoma-backend","version":"1.4.1"}

# ---- 3. 业务读接口（代理 + 数据库） ----
curl -s http://127.0.0.1:3000/api/v1/courses | python -c "
import json,sys
d = json.load(sys.stdin)
items = d if isinstance(d, list) else d.get('items', [])
print('courses:', len(items))
print('with_kp:', sum(1 for c in items if c['knowledge_point_count'] > 0))
"
# courses: 7
# with_kp: 7

# ---- 4. 业务写接口（跨服务写库） ----
curl -s -X POST http://127.0.0.1:3000/api/v1/daily-tasks/self-study \\
  -H "Content-Type: application/json" \\
  -d '{"knowledge_point_code":"software-engineering-deploy-01-01"}'
# {"task":{...},"created":true}

# ---- 5. 流式接口（代理不缓冲） ----
curl -N -s -X POST http://127.0.0.1:3000/api/v1/chat/stream \\
  -H "Content-Type: application/json" \\
  -d '{"message":"用一个例子解释 Docker 分层"}'
# data: {"delta":"Docker"} ...
# data: {"done":true}

# ---- 6. 反向确认：后端未被直接暴露 ----
curl -s -o /dev/null -w "%{http_code}\\n" http://127.0.0.1:8000/api/v1/health
# 000（连接失败）—— 符合预期''',
                "code_lines": """1. 第 1 步只验证前端容器本身能返回页面，排除"整站不可达"。
2. 第 2 步验证代理链路：前端 → 后端，这是最常见的断点（`BACKEND_INTERNAL_URL` 配错）。
3. 第 3 步验证读路径：代理 + 业务查询 + 数据库三者一起工作。
4. 关键做法：不只看 200，而是统计 `with_kp` 数量，确认业务数据真的完整。
5. 第 4 步验证写路径：会真正落库，能暴露事务、外键、约束问题。
6. 第 5 步专门验证流式：如果代理缓冲没关，这里会表现为"卡住然后一次性输出"。
7. 第 6 步是反向确认：后端不该对宿主机暴露，`000` 才是正确结果。""",
                "output": """$ ./scripts/smoke_test.sh
[1/6] 静态资源 ... 200 OK
[2/6] 健康接口 ... {"status":"ok","version":"1.4.1"}
[3/6] 业务读接口 ... courses=7 with_kp=7
[4/6] 业务写接口 ... created=true
[5/6] 流式接口 ... first_chunk=0.31s total=2.8s
[6/6] 后端隔离 ... backend_unreachable=true (预期)

联调通过：6/6

# 典型失败输出
[2/6] 健康接口 ... 502
  → 前端 BACKEND_INTERNAL_URL=http://127.0.0.1:8000（应为 http://backend:8000）

[5/6] 流式接口 ... first_chunk=8.2s（应为 <1s）
  → 代理未关闭 proxy_buffering

[3/6] 业务读接口 ... courses=7 with_kp=0
  → 数据缺失：检查课程种子是否执行""",
                "mistakes": """- 前端容器里配 `127.0.0.1:8000`，代理转发永远失败。
- 分离架构用 `allow_origins=["*"]` 且带凭证，浏览器直接拒绝。
- 只在浏览器里点着测，没做脚本化验收，回归时全靠人肉。
- 验证只看 200，没检查业务字段，导致"接上了但数据是空的"被漏过。
- 流式接口没单独验证，上线后才发现回复要等 8 秒才出现。""",
                "error_analysis": """浏览器报 `CORS policy: No 'Access-Control-Allow-Origin'`
—— 分离架构没配 CORS，或 Origin 不在白名单。注意凭证模式下不能用 `*`。

`502` 从代理返回
—— `BACKEND_INTERNAL_URL` 写成了 `127.0.0.1`，或服务名拼错。

页面正常但所有接口 401
—— 同源代理没转发 `Authorization` 或 `Cookie` 头。检查代理是否原样透传 headers。

流式要等很久才出字
—— 代理缓冲未关（见上一章）；也可能是后端自己在缓冲（`yield` 前做了全量计算）。

`000` 出现在第 2 步而非第 6 步
—— 说明前端容器没起来，或端口不对。""",
                "beginner_practice": """1. 写一个 6 步联调脚本，按「静态 → 健康 → 读 → 写 → 流式 → 隔离」顺序验证。
2. 故意把 `BACKEND_INTERNAL_URL` 改成 127.0.0.1，观察脚本在第几步失败、报什么。""",
                "advanced_practice": """为项目做架构取舍：同源代理 vs 前后端分离。
列出至少四条对比维度（CORS、部署复杂度、CDN 缓存、跨域调试成本），并给出你的选择与理由。
再回答：如果必须分离部署，CORS、Cookie 与预检请求分别要注意什么？""",
                "quiz_note": "本节 6 道题：2 道基础理解（同源代理优势、CORS 凭证限制）+ 2 道输出阅读（读联调脚本、读 502 原因）+ 2 道应用练习（选对配置、判断验证顺序）。",
                "summary": """同源代理免 CORS、可隐藏后端端口，是前后端部署的首选。
分离架构必须显式配 CORS，且凭证模式下 Origin 不能是 `*`。
联调要按链路逐跳验证，每步都有明确的通过标准（含业务字段）。
反向确认"后端不可直接访问"同样是一条验收项。""",
                "next_lesson": "普通接口能通了，但 Agent 服务是长耗时与流式，需要单独设计，下一节讲。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-08-01",
                        "name": "前后端与数据库联调",
                        "goal": "能按链路顺序完成前后端与数据库的联调验收，并定位跨域与代理问题。",
                        "minutes": 45,
                        "criteria": "能写出 6 步联调脚本并全部通过，且在代理地址配错时准确指出失败步骤与原因。",
                        "requires": ["software-engineering-deploy-07-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-08-01-1",
                        "kp": 0,
                        "title": "定位联调失败点",
                        "description": """联调脚本第 2 步失败：

```
[1/6] 静态资源 ... 200 OK
[2/6] 健康接口 ... 502
```

说明问题在哪一层，写出三条最可能的原因。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''第 1 步通过说明前端容器与自己监听的端口正常；第 2 步 502 说明
"前端 → 后端"这一跳断了，问题在代理配置或后端本身。

三条最可能原因：
1. `BACKEND_INTERNAL_URL` 配成 `http://127.0.0.1:8000`——容器内指向自己，应改为 `http://backend:8000`；
2. 后端容器未启动或已退出：`docker compose ps` 会显示 Exited，`logs` 里能看到原因（迁移失败、配置校验失败）；
3. 两个服务不在同一 Compose 网络：服务名无法解析（`getent hosts backend` 返回空）。

排查顺序：先看 `docker compose ps`（后端在不在），再 `docker compose exec frontend env | grep BACKEND`（地址对不对），
最后 `docker compose exec frontend sh -c "wget -qO- http://backend:8000/api/v1/health"`（能不能通）。''',
                        "explanation": "第几步失败直接对应链路哪一跳，这就是分步验证的价值。",
                    },
                    {
                        "code": "sed-ex-08-01-2",
                        "kp": 0,
                        "title": "CORS 与凭证",
                        "description": """分离架构下浏览器报 CORS 错误，后端配置是：

```python
allow_origins=["*"]
allow_credentials=True
```

问题在哪？怎么改？""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''问题：按 CORS 规范，当 `allow_credentials=True`（允许携带 Cookie / 凭证）时，
`Access-Control-Allow-Origin` **不能为 `*`**，必须是具体来源。浏览器会直接拒绝响应。

改法：
```python
allow_origins=["https://app.example.com", "http://localhost:3000"]
allow_credentials=True
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
allow_headers=["Authorization", "Content-Type"]
```

补充要点：
1. 前端域名必须精确匹配（协议 + 域名 + 端口），`https://app.example.com/` 多一个斜杠都可能不匹配；
2. 若同时支持多个环境，用配置项注入白名单，不要硬编码；
3. 走同源代理则完全不需要这些——这也是推荐同源代理的实际原因。''',
                        "explanation": "凭证模式下的 CORS 限制是规范强制的，不是浏览器 bug。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-08-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "同源代理相比前后端分离部署的最大优势是？",
                        "options": [
                            ("A", "前端渲染更快"),
                            ("B", "免 CORS 且后端无需对外暴露端口"),
                            ("C", "不需要数据库"),
                            ("D", "自动实现 HTTPS"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "浏览器只与前端同源通信，代理在服务端转发，绕过了 CORS 与端口暴露问题。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-08-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "联调验收应包含哪些步骤？（多选）",
                        "options": [
                            ("A", "静态页可访问"),
                            ("B", "健康接口经代理可达"),
                            ("C", "业务写接口能落库"),
                            ("D", "后端端口对宿主机可直接访问"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 通常应是**不可**访问；能直接访问说明暴露了内部服务。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-08-01-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """第 3 步输出：

```
[3/6] 业务读接口 ... courses=7 with_kp=0
```

说明？""",
                        "options": [
                            ("A", "链路通了但数据缺失"),
                            ("B", "代理配置错误"),
                            ("C", "后端未启动"),
                            ("D", "证书过期"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "能拿到 7 门课程说明读链路通；`with_kp=0` 说明知识点数据没写入。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-08-01-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "第 6 步 `curl http://127.0.0.1:8000` 返回 `000`，这是？",
                        "options": [
                            ("A", "错误，后端应该可访问"),
                            ("B", "正常，后端未映射到宿主机是预期行为"),
                            ("C", "说明后端崩溃"),
                            ("D", "说明代理失败"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "后端只 `expose`，由前端代理访问；直接访问失败正是隔离生效的证明。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-08-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": """同源代理场景下，前端容器（Next.js 服务端）要访问后端容器。写出 `XIAOMA_API_BASE_URL` 应配置的值，并说明为什么不能用 `127.0.0.1`。""",
                        "answer": {"reference": "配置为 `http://backend:8000`，用 compose 的服务名在同一网络内解析。容器内的 `127.0.0.1` 指向容器自身，那里没有后端进程，连接会被拒绝。", "keywords": ["http://backend:8000", "服务名", "127.0.0.1", "容器自身"]},
                        "explanation": "容器内用服务名解析；127.0.0.1 指向自身，宿主机 IP 也绕路且通常不可达。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-08-01-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只要接口返回 200，就说明联调通过。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": """必须校验业务字段（如知识点数量、写入是否成功），否则"接口通了但数据是空的"会被放过。""",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-08-lesson-02",
                "objectives": """1. 能识别 Agent/LLM 服务与前馈接口的差异（长耗时、流式、外部依赖）；
2. 能为长耗时请求设置合理的超时分级（代理、网关、应用、模型）；
3. 能设计并发与降级策略（限流、队列、超时兜底文案）；
4. 能处理"上游慢"导致的连接堆积问题。""",
                "why_learn": """普通接口 50ms 返回，Agent 接口可能要 30 秒还在流式输出。
如果沿用同一套超时与并发配置，会出现两种极端：
超时太短——用户看到「回答被中断」；没有并发限制——一个慢请求占满 worker，整站变慢。
Agent 服务必须单独设计资源边界。""",
                "concepts": """**超时分级**：代理读超时 > 应用超时 > 模型调用超时，层层递减才不会被上层提前掐断。
**流式 vs 一次性**：流式能降低"首字节时间"，感知更快，但占用连接更久。
**并发控制**：信号量/限流器限制同时在处理的模型请求数，避免内存与配额被打满。
**降级**：模型不可用时返回明确提示与可继续的操作，而不是空白转圈。
**连接堆积**：慢上游 + 无限制并发 = 连接池耗尽，表现为"所有接口都变慢"。""",
                "plain": """普通接口像点快餐：几十秒内出餐，窗口快进快出。
Agent 接口像定制蛋糕：要等、要占着工位、还可能中途缺料（模型超时）。
你不能用快餐窗口的规则去管蛋糕订单——否则要么蛋糕被扔出去（超时太短），
要么所有人挤在窗口等（并发无限制），后面点快餐的人也吃不上。
正确做法是：给蛋糕单独立窗口（独立超时）、限号（并发上限）、缺料时告知（降级）。""",
                "syntax": """**超时分级（从外到内递减）**

```nginx
# 代理层：最长
location /api/v1/chat/ {
    proxy_read_timeout 600s;
}
```

```python
# 应用层：比代理短，留出序列化与网络余量
AGENT_TIMEOUT = 120     # 秒

# 模型调用层：最短，失败快、可重试
LLM_TIMEOUT = 60
```

**并发限制**

```python
import asyncio

_semaphore = asyncio.Semaphore(8)   # 同时最多 8 个模型请求

async def call_model(payload: dict) -> str:
    async with _semaphore:
        return await _do_call(payload)
```

- 顺序必须是：代理 600s > 应用 120s > 模型 60s。反了就会被上层先掐断。
- 信号量放在进程内只能限制单实例；多实例需要外部限流（Redis 计数器）。""",
                "example_code": '''# app/services/agent_runner.py：超时 + 并发 + 降级
import asyncio
import logging

from app.config import settings

logger = logging.getLogger("xiaoma.agent")

# 同时处理中的 Agent 请求上限，防止慢请求占满所有 worker
_AGENT_SEMAPHORE = asyncio.Semaphore(8)
AGENT_TIMEOUT = settings.agent_timeout_seconds      # 默认 120
FALLBACK_MESSAGE = (
    "这次回答没能完成：模型服务响应超时。"
    "你可以稍后重试，或换个更具体的问题继续。"
)


async def run_agent(message: str, knowledge_point_code: str | None) -> str:
    try:
        async with _AGENT_SEMAPHORE:
            return await asyncio.wait_for(
                _execute(message, knowledge_point_code),
                timeout=AGENT_TIMEOUT,
            )
    except asyncio.TimeoutError:
        logger.warning(
            "agent.timeout",
            extra={"timeout_s": AGENT_TIMEOUT, "kp": knowledge_point_code},
        )
        return FALLBACK_MESSAGE
    except Exception as exc:                      # noqa: BLE001
        logger.error(
            "agent.failed",
            extra={"error": str(exc)[:200], "kp": knowledge_point_code},
        )
        return "处理这条消息时出错了，已记录。你可以重试或换个问法。"


async def _execute(message: str, knowledge_point_code: str | None) -> str:
    """真正调用模型的内部实现（含意图识别与子图执行）。"""
    ...''',
                "code_lines": """1. `Semaphore(8)` 限制同时进行的 Agent 请求数：慢请求不会无限堆积。
2. `asyncio.wait_for` 给整条 Agent 链路设总超时，覆盖意图识别 + 子图 + 模型调用。
3. 超时不抛 500 给用户，而是返回可读的兜底文案——这是降级而非失败。
4. `logger.warning` 记录超时与对应知识点，便于统计"哪些请求最常超时"。
5. 兜底文案要给出下一步动作（稍后重试 / 换问法），而不是只说"出错了"。
6. 异常分支单独记录，且截断错误信息避免日志爆量。
7. 超时分级：代理 600s > 应用 120s > 模型 60s，任何一层倒挂都会导致"莫名被中断"。""",
                "output": """# 正常流式（首字节快）
$ curl -N -s -X POST http://127.0.0.1:3000/api/v1/chat/stream \\
  -H "Content-Type: application/json" -d '{"message":"解释一下流式输出"}'
data: {"delta":"流式"}
data: {"delta":"输出"}
data: {"done":true}
# 首字节约 0.3s，总耗时约 4s

# 模型超时后的降级响应
$ curl -s -X POST http://127.0.0.1:3000/api/v1/chat \\
  -H "Content-Type: application/json" -d '{"message":"一个特别复杂的问题"}'
{"message":"这次回答没能完成：模型服务响应超时。你可以稍后重试，或换个更具体的问题继续。"}

# 日志
{"level":"WARNING","logger":"xiaoma.agent","msg":"agent.timeout","timeout_s":120,"kp":"software-engineering-deploy-03-01"}

# 并发压测：8 个并发时开始排队
$ for i in $(seq 1 12); do curl -s -o /dev/null -w "%{http_code} %{time_total}\\n" \\
    -X POST http://127.0.0.1:3000/api/v1/chat -d '{"message":"hi"}' & done; wait
200 3.12
200 3.28
...
200 9.84      ← 后 4 个排队等待，未失败""",
                "mistakes": """- 代理超时 60s，应用超时 120s：用户在 60s 时被代理掐断，应用还在算。
- 不限制并发，几个慢请求把 worker 占满，普通接口也开始超时。
- 模型超时直接冒泡成 500，用户只看到"服务器错误"。
- 流式接口在发送前做了全量计算，首字节仍然很慢。
- 兜底文案写"系统繁忙请稍后再试"，没有告诉用户还能做什么。""",
                "error_analysis": """用户看到「回答被中断」但后端日志无异常
—— 被代理的 `proxy_read_timeout` 掐断，日志里没有 ERROR。检查超时是否分级倒挂。

`504` 集中在 Agent 接口
—— 该 location 的超时不够，或应用层总超时比代理还长。

所有接口一起变慢，`docker stats` 显示 CPU 不高
—— 连接/worker 被慢请求占满。加剧时间监控与并发限制。

模型侧报 429（限流）
—— 并发太高超出配额。降低信号量上限或加队列与退避重试。""",
                "beginner_practice": """1. 给 Agent 接口加上并发信号量与总超时，验证第 9 个并发请求是排队而不是直接失败。
2. 人为让模型调用超时，确认用户看到的是兜底文案而不是 500。""",
                "advanced_practice": """设计 Agent 服务的资源边界：并发上限、总超时、模型超时、重试策略、降级文案、监控指标。
验收：(1) 超时分级从外到内递减；(2) 超限时有明确行为；(3) 能说明为什么流式的首字节时间比总耗时更值得优化。""",
                "quiz_note": "本节 6 道题：2 道基础理解（超时分级、并发限制作用）+ 2 道输出阅读（读降级响应、读压力测试结果）+ 2 道应用练习（选对超时配置、判断降级写法）。",
                "summary": """Agent 接口是长耗时 + 流式 + 外部依赖，必须与普通接口分开配置。
超时必须分级递减：代理 > 应用 > 模型，倒挂会导致莫名中断。
并发限制保护的是整站，不只是 Agent 自己。
降级要给出可执行的下一步，而不是一句"出错了"。""",
                "next_lesson": "最后一节：把所有检查项汇成清单，上线前逐条打勾，上线后复盘。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-08-02",
                        "name": "Agent 服务超时、并发与降级",
                        "goal": "能为长耗时流式接口设计分级超时、并发上限与可读降级。",
                        "minutes": 40,
                        "criteria": "能给出从代理到模型层层递减的超时配置，并证明并发超限时请求排队而非失败。",
                        "requires": ["software-engineering-deploy-08-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-08-02-1",
                        "kp": 0,
                        "title": "修掉超时倒挂",
                        "description": """配置如下，用户经常反馈"回答说到一半就断了"，后端日志没有报错。
指出问题并给出正确配置。

```
代理 proxy_read_timeout: 60s
应用 AGENT_TIMEOUT: 120s
模型 LLM_TIMEOUT: 90s
```""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''问题：超时倒挂。代理 60s 最短，会在应用还在计算时把连接掐断，
所以后端日志里没有 ERROR（应用没报错，是连接被外部关闭了）。

正确配置（从外到内递减）：
```
代理 proxy_read_timeout: 600s
应用 AGENT_TIMEOUT: 120s
模型 LLM_TIMEOUT: 60s
```

理由：
1. 代理必须最长，它是最后一道兜底，不能先于应用放弃；
2. 应用总超时覆盖意图识别 + 子图 + 模型调用，120s 含余量；
3. 模型超时最短，失败可重试，且不应吃掉应用的全部预算。

排查技巧：用户看到中断但后端无 ERROR 时，优先怀疑代理或网关超时。''',
                        "explanation": "「后端没报错但用户被中断」是超时倒挂的典型指纹。",
                    },
                    {
                        "code": "sed-ex-08-02-2",
                        "kp": 0,
                        "title": "写一条可用的降级文案",
                        "description": """模型超时时，当前返回 `{"detail": "Internal Server Error"}`。
改写为对用户有用的降级响应，并说明设计原则。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''```json
{
  "message": "这次回答没能完成：模型服务响应超时。你可以稍后重试，或换个更具体的问题继续。",
  "retryable": true,
  "error_code": "agent_timeout"
}
```

设计原则：
1. **说清发生了什么**（模型超时），而不是"服务器错误"；
2. **告诉用户还能做什么**（稍后重试 / 换问法），给出选择而不是死路；
3. **标出可重试性**（`retryable: true`），前端据此显示"重试"按钮；
4. **带错误码**（`agent_timeout`），便于用户报障时提供、也便于统计分布；
5. **不暴露内部细节**（不要返回堆栈、上游 URL、密钥片段）。

注意：这条响应仍应是 HTTP 200 或 504 中的一种明确选择，并在前后端统一。
业务降级通常返回 200 + `error_code`；链路级超时用 504 更符合语义。''',
                        "explanation": """降级不是"优雅地失败"，而是"把失败变成一条可执行的提示"。""",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-08-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "正确的超时分级顺序（从长到短）是？",
                        "options": [
                            ("A", "模型 > 应用 > 代理"),
                            ("B", "代理 > 应用 > 模型"),
                            ("C", "三者必须相同"),
                            ("D", "代理 > 模型 > 应用"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "外层必须比内层更宽容，否则外层会先掐断内层还在进行的处理。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-08-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "为 Agent 服务做并发限制能带来？（多选）",
                        "options": [
                            ("A", "避免慢请求占满 worker"),
                            ("B", "保护模型配额不被打爆"),
                            ("C", "让每个请求更快完成"),
                            ("D", "让超限请求排队而不是失败"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 不成立：限流可能让单个请求等待更久，换来的是整体稳定。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-08-02-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """用户反馈"回答说到一半断了"，但后端日志无 ERROR。最可能原因是？""",
                        "options": [
                            ("A", "模型返回了空内容"),
                            ("B", "代理的读超时短于应用总超时，连接被外部关闭"),
                            ("C", "数据库锁"),
                            ("D", "前端渲染 bug"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "应用侧没报错说明它还在执行，是外部先把连接关了——典型超时倒挂。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-08-02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "压测 12 个并发，前 8 个 3 秒返回、后 4 个 9 秒返回且都是 200。说明？",
                        "options": [
                            ("A", "有并发限制，超限请求排队执行"),
                            ("B", "都失败了"),
                            ("C", "并发限制未生效"),
                            ("D", "模型更慢"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "信号量 8 生效：后 4 个等待前序释放配额，符合预期设计。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-08-02-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "限制同时进行的模型请求为 8 个，Python 里应使用？",
                        "options": [
                            ("A", "asyncio.Semaphore(8)"),
                            ("B", "threading.Lock()"),
                            ("C", "time.sleep(8)"),
                            ("D", "os.cpu_count()"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "信号量允许多达 8 个协程同时进入临界区，9 个及以上排队等待。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-08-02-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "模型超时时直接返回 500 与堆栈信息，方便用户自查问题。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "堆栈会泄漏实现细节且对用户无用。应返回可读降级文案与错误码。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-08-lesson-03",
                "objectives": """1. 能使用一份可执行的上线检查清单逐项验收；
2. 能组织一次发布复盘，区分「触发因素」与「根因」；
3. 能把复盘结论转成具体的改进项与负责人；
4. 理解「无指责复盘」为什么能提高系统可靠性。""",
                "why_learn": """上线前靠清单，上线后靠复盘。
清单解决"忘记检查"，复盘解决"同一个坑踩两次"。
很多团队每次都出事、每次都总结，但下次照样出事——因为总结停在"下次注意"，没有变成机制。""",
                "concepts": """**上线清单**：把易漏必查项固化成可勾选条目，覆盖配置、数据、安全、回滚、观测。
**触发因素 vs 根因**：触发是"最后一次点击"，根因是"为什么这个点击能造成破坏"。
**改进项要具体**：有动作、有负责人、有截止时间，否则不是改进是愿望。
**无指责复盘**：追系统而非追人，人才会如实说明细节，隐藏信息才是最大风险。
**复盘沉淀**：把结论写进清单与自动化，让同类问题不再依赖记忆。""",
                "plain": """上线像飞机起飞前的检查单：机长不会因为"飞了一万次"就跳过，因为跳过的那一次可能就是事故。
复盘像赛后录像分析：不是找谁踢飞了点球，而是看为什么会在那个位置丢球。
无指责不是"不追究"，而是"先拿到真实信息"——怕被罚的人会说"我不知道"，那你就永远找不到根因。
改进项必须落到"谁、什么时候、做什么"，否则下次开会还是这几句话。""",
                "syntax": """**上线检查清单（可复制使用）**

```markdown
## 发布前
- [ ] 当前服务健康（/api/v1/health 返回 ok）
- [ ] 已备份数据（含 .secret_key）
- [ ] 数据库迁移已验证（在副本上跑过）
- [ ] 关键配置已核对（差异清单逐项）
- [ ] 上一个可用镜像标签已记录
- [ ] 磁盘空间充足（> 20%）

## 发布中
- [ ] 只更新目标服务（--no-deps）
- [ ] 健康检查通过（不是只看容器 Up）
- [ ] 观察窗口 ≥ 5 分钟，错误率正常

## 发布后
- [ ] 核心链路冒烟（读 / 写 / 流式）
- [ ] 日志无新增 ERROR 峰值
- [ ] 版本号与变更记录已更新
- [ ] 回退预案确认可执行
```

**复盘记录模板**

```markdown
## 事件：2026-11-09 课程内容缺失
- 影响：6 门课程无法学习，持续 2 小时
- 触发：用户切换课程页面
- 根因：容器启动脚本只跑了 3 个种子命令，缺 5 个教材种子
- 为什么没被发现：验收只检查"课程能打开"，没检查"知识点数量"
- 改进项：
  1. 修复 entrypoint.sh（负责人 A，已上线）
  2. 冒烟脚本增加"各课程知识点数 > 0"断言（负责人 B，本周）
  3. 上线清单增加"数据完整性校验"（负责人 C，下次发布前）
```""",
                "example_code": '''# scripts/preflight.sh：把清单里能自动化的部分变成脚本
#!/usr/bin/env bash
set -euo pipefail

FAIL=0
say() { printf "[%s] %s\\n" "$1" "$2"; }

# 1. 服务健康
if curl -fsS http://127.0.0.1:3000/api/v1/health > /dev/null 2>&1; then
  say OK "服务健康"
else
  say FAIL "服务不健康，停止发布"; FAIL=1
fi

# 2. 磁盘空间
usage=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
if [ "$usage" -lt 80 ]; then say OK "磁盘 ${usage}%"; else say FAIL "磁盘 ${usage}% 过高"; FAIL=1; fi

# 3. 数据完整性（本次事故的教训）
kp=$(docker compose exec -T backend python -c "
import sqlite3;c=sqlite3.connect('/app/data/xiaoma.db')
print(c.execute('SELECT count(*) FROM knowledge_points').fetchone()[0])" | tr -d "\\r")
if [ "$kp" -ge 190 ]; then say OK "知识点 $kp"; else say FAIL "知识点仅 $kp，疑似种子未跑"; FAIL=1; fi

# 4. 备份时效
latest=$(ls -t /backup/*.db 2>/dev/null | head -1 || true)
if [ -n "$latest" ]; then say OK "最近备份 $(basename "$latest")"; else say FAIL "无备份"; FAIL=1; fi

# 5. 记录回退标签
say INFO "当前镜像标签：$(docker inspect xiaoma-backend --format '{{.Config.Image}}')"

exit "$FAIL"''',
                "code_lines": """1. `set -euo pipefail` 让脚本在任何异常时立即失败，不继续误判。
2. 每条检查都输出明确结论（OK/FAIL），而不是只有最终通过/失败。
3. 第 3 条是这次事故的直接产物：把"知识点数量"变成断言，同类问题不可能再漏过。
4. 阈值 190 而不是精确 194：允许内容小幅调整，但能卡住"31 个"这种明显缺失。
5. `tr -d "\\r"` 清除 Windows 换行，否则数值比较会失败——这是实操中真实踩过的坑。
6. 第 5 条输出当前镜像标签，回退时直接可用，不需要临场查。
7. `exit "$FAIL"` 让 CI/脚本能据此判断是否继续发布。""",
                "output": """$ ./scripts/preflight.sh
[OK] 服务健康
[OK] 磁盘 46%
[OK] 知识点 194
[OK] 最近备份 xiaoma-20261109-225501-112233.db
[INFO] 当前镜像标签：xiaoma-backend:v1.4.1
exit=0

# 数据缺失时
$ ./scripts/preflight.sh
[OK] 服务健康
[OK] 磁盘 46%
[FAIL] 知识点仅 31，疑似种子未跑
[OK] 最近备份 xiaoma-20261107-101200-334455.db
[INFO] 当前镜像标签：xiaoma-backend:v1.4.1
exit=1

# 复盘记录（片段）
## 事件：课程内容缺失
- 触发：用户切换课程页
- 根因：entrypoint.sh 缺 5 个教材种子命令
- 为什么没发现：验收只看"页面能打开"
- 改进：修复脚本 / 增加数据完整性断言 / 清单加校验项
- 负责人与截止：A 已上线，B 本周，C 下次发布前""",
                "mistakes": """- 清单写了但没人真的逐项打勾，出事后才补签。
- 复盘只写"加强测试"，没有负责人与截止时间，下次照样发生。
- 把根因归到"某人操作失误"，于是同类问题在其他地方继续发生。
- 只复盘大事故，放过小问题——小问题正是大事故的预演。
- 复盘结论没有回到清单与自动化，全靠人的记忆。""",
                "error_analysis": """清单执行流于形式（勾了但没做）
—— 把能自动化的项改成脚本断言，人工只负责无法自动化的判断。

同类问题重复发生
—— 复盘改进项没有落到机制（清单/脚本/校验），只是"口头承诺"。

复盘时信息不全、互相推诿
—— 缺少无指责氛围，参与者倾向隐藏细节。先明确"目的是改进系统，不是追责"。

发布通过但用户仍报问题
—— 冒烟覆盖不足。把用户报障的路径加进冒烟脚本，形成闭环。""",
                "beginner_practice": """1. 把清单里能自动化的五项写成 `preflight.sh`，本地跑通。
2. 用复盘模板写一次最近遇到的真实问题，区分触发与根因。""",
                "advanced_practice": """为项目建立"问题 → 清单/脚本"的闭环：
挑选过去三个真实问题，各写一条对应的自动化断言或清单项，并说明如何验证它真的能拦住同类问题。""",
                "quiz_note": "本节 6 道题：2 道基础理解（触发 vs 根因、无指责复盘）+ 2 道输出阅读（读 preflight 结果、读复盘记录）+ 2 道应用练习（选对改进项写法、判断清单价值）。",
                "summary": """上线靠清单解决"忘记检查"，复盘解决"重复踩坑"。
触发因素是最后一根稻草，根因是系统为什么允许它造成破坏。
改进项必须有动作、负责人、截止时间，否则只是愿望。
把结论写回清单与脚本，才算真正闭环。""",
                "next_lesson": "课程到此结束。接下来建议用自己的项目完整走一遍：从测试、容器、编排到发布与复盘。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-08-03",
                        "name": "上线清单与无指责复盘",
                        "goal": "能把易漏项固化成可执行清单与脚本断言，并产出含负责人与截止的改进项。",
                        "minutes": 35,
                        "criteria": "能写出覆盖配置/数据/回滚/观测的上线清单，并完成一次含触发、根因、改进项的复盘记录。",
                        "requires": ["software-engineering-deploy-08-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-08-03-1",
                        "kp": 0,
                        "title": "区分触发与根因",
                        "description": """事件：某次发布后「课程体系」页面报错。
过程：开发合并了一个前端改动 → 发布 → 用户切换课程 → 报错。
请指出触发因素、直接原因、根本原因，并各写一条改进项。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''- 触发因素：用户切换课程标签页（只是让问题暴露的动作，不是问题本身）。
- 直接原因：该课程在数据库里没有知识点，接口返回空列表，前端未处理空状态而抛错。
- 根本原因：发布流程缺少"数据完整性"验收；同时前端对空数据没有兜底渲染。
  更深一层：容器启动脚本缺少教材种子命令，导致数据从来就不完整，且无人发现。

改进项：
1. 前端为空列表增加空状态文案（负责人 A，本周）——治直接原因；
2. 冒烟脚本增加"各课程 knowledge_point_count > 0"断言（负责人 B，本周）——治流程缺口；
3. entrypoint.sh 补齐 5 个种子命令（负责人 C，已上线）——治根本原因；
4. 上线清单增加"数据完整性校验"一项（负责人 D，下次发布前）——防复发。

注意：不要写成"加强测试"这种无法验收的表述。''',
                        "explanation": "把三层拆开，改进项才能各就各位，否则容易只修表象。",
                    },
                    {
                        "code": "sed-ex-08-03-2",
                        "kp": 0,
                        "title": "把清单变成脚本",
                        "description": """清单里有"确认知识点数据完整"这一项，人工检查容易漏。
写出对应的自动化断言（shell + python 片段）。""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''```bash
kp=$(docker compose exec -T backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/xiaoma.db')
print(c.execute('SELECT count(*) FROM knowledge_points').fetchone()[0])
" | tr -d "\\r")

if [ "${kp:-0}" -ge 190 ]; then
  echo "[OK] 知识点 $kp"
else
  echo "[FAIL] 知识点仅 ${kp:-0}，疑似种子未跑"
  exit 1
fi
```

要点：
1. 阈值用 190 而非精确 194，允许内容小幅调整，同时能拦住"31 个"这种明显缺失；
2. `tr -d "\\r"` 处理 Windows 换行，否则数值比较报错；
3. `${kp:-0}` 兜住命令失败时的空值，避免 `[: : integer expression expected`；
4. 失败要 `exit 1`，让流程真正中断，而不是打印警告继续发布。''',
                        "explanation": """把清单项变成断言，是让检查从"靠自觉"变成"靠机制"的唯一方式。""",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-08-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "复盘中的「触发因素」指的是？",
                        "options": [
                            ("A", "系统为什么会允许问题造成破坏"),
                            ("B", "让问题暴露出来的那个动作或事件"),
                            ("C", "负责人的失误"),
                            ("D", "监控告警时间"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "触发只是最后一根稻草；根因是系统为什么允许它造成后果。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-08-03-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "一条合格的复盘改进项应包含？（多选）",
                        "options": [
                            ("A", "具体动作"),
                            ("B", "负责人"),
                            ("C", "截止时间"),
                            ("D", "「下次注意」"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 无法验收也无法追踪，是最常见的无效改进。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-08-03-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`preflight.sh` 输出 `[FAIL] 知识点仅 31，疑似种子未跑` 且 `exit=1`，说明？",
                        "options": [
                            ("A", "检查通过"),
                            ("B", "数据完整性断言发现异常，发布应被阻断"),
                            ("C", "脚本有语法错误"),
                            ("D", "磁盘满"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "这正是把事故教训固化成断言的形态：同类问题不可能再被放过。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-08-03-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "复盘记录里写「改进：加强测试」，问题在于？",
                        "options": [
                            ("A", "没有负责人、动作与截止，无法验收与追踪"),
                            ("B", "字数太少"),
                            ("C", "测试不重要"),
                            ("D", "应该写成加强监控"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "这类表述听起来正确，但无法执行，下次仍会发生同样问题。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-08-03-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "把清单项变成可靠断言，失败时必须？",
                        "options": [
                            ("A", "打印警告后继续"),
                            ("B", "以非零码退出，让流程中断"),
                            ("C", "记录到日志后忽略"),
                            ("D", "发一封邮件"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "只警告不中断等于没检查；`exit 1` 才能让 CI 或脚本真正停下。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-08-03-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "无指责复盘意味着不追究任何责任，因此容易导致同样问题反复发生。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": """无指责是为了获取真实信息以便改进系统；反复发生的根源是改进项没落地，不是"不追责"。""",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
