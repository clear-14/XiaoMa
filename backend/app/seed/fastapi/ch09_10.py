"""FastAPI 后端开发：第 9—10 章（统一异常处理与中间件、CORS 与同步异步接口）。"""

CHAPTERS: list[dict] = [
    {
        "code": "fastapi-backend-09",
        "title": "统一异常处理与中间件",
        "description": "错误响应要一致，横切逻辑要能复用。",
        "order_index": 9,
        "lessons": [
            {
                "code": "fastapi-backend-09-lesson-01",
                "objectives": """1. 能把业务异常映射成统一结构的错误响应；
2. 会注册自定义异常处理器，覆盖框架默认行为；
3. 能统一 422 校验错误的结构，供前端按字段定位；
4. 知道哪些异常该暴露、哪些必须隐藏。""",
                "why_learn": """默认的 404 是 `{"detail": "Not Found"}`，校验错误是 `{"detail": [ ... ]}`，业务异常可能是 500 加一段 traceback。
前端要写三套解析逻辑，监控也统计不清。统一异常处理就是把这些出口收敛成一种结构。""",
                "concepts": """**异常处理器**：`@app.exception_handler(异常类)` 注册，返回 `JSONResponse`。
**业务异常**：自定义异常类承载错误码与上下文，与 HTTP 细节解耦。
**校验异常**：`RequestValidationError` 专门处理 422，可自定义结构。
**兜底处理器**：`Exception` 处理器负责记录日志并返回 500，绝不返回 traceback。
**处理器必须 async**：Starlette 会 await 处理器，同步函数会导致错误。""",
                "plain": """异常处理器像公司的统一客服：不管问题出在哪个部门，客户听到的都是同一套话术与工单号。
业务异常是「内部工单」：写明问题类型与定位信息，但不会把内部系统名、堆栈直接念给客户。
兜底处理器是最后一道：真出了没预料到的问题，也回一句「系统繁忙，工单号 XXX」，同时把细节写进日志。""",
                "syntax": """**API 说明**

```python
@app.exception_handler(TaskNotFound)
async def handler(request: Request, exc: TaskNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"code": "...", "message": "..."})
```

- 处理器签名固定为 `(request, exc)`。
- `RequestValidationError` 处理 422；`StarletteHTTPException` 处理框架抛出的 HTTP 异常。
- 统一结构建议至少含 `code`（机器可读）与 `message`（人可读）。""",
                "example_code": '''from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(title="统一异常处理示例")


class TaskNotFound(Exception):
    def __init__(self, task_id: int) -> None:
        self.task_id = task_id


@app.exception_handler(TaskNotFound)
async def handle_task_not_found(request: Request, exc: TaskNotFound) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"code": "TASK_NOT_FOUND", "message": f"任务 {exc.task_id} 不存在"},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "参数校验失败",
            "errors": [{"loc": list(err["loc"]), "msg": err["msg"]} for err in exc.errors()],
        },
    )


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict:
    if task_id > 100:
        raise TaskNotFound(task_id)
    return {"id": task_id}''',
                "code_lines": """1. `TaskNotFound` 只带业务信息（哪个任务），不关心 HTTP 状态码。
2. `@app.exception_handler(TaskNotFound)` 把「抛这个异常」与「返回什么响应」绑定。
3. 处理器签名必须是 `(request, exc)`，且用 `async def`——Starlette 会 await 它。
4. 返回 `JSONResponse` 而不是字典，才能自定义状态码与响应头。
5. 校验处理器把默认的 `detail` 改写成 `code/message/errors` 三段式。
6. `err["loc"]` 是元组，转成 list 才能安全序列化为 JSON 数组。
7. 业务代码只 `raise TaskNotFound(...)`，不关心响应格式，职责清晰。""",
                "output": """curl http://127.0.0.1:8000/tasks/101
HTTP/1.1 404 Not Found
{"code":"TASK_NOT_FOUND","message":"任务 101 不存在"}

curl "http://127.0.0.1:8000/tasks/abc"
HTTP/1.1 422 Unprocessable Entity
{"code":"VALIDATION_ERROR","message":"参数校验失败",
"errors":[{"loc":["path","task_id"],"msg":"Input should be a valid integer, unable to parse string as an integer"}]}

curl http://127.0.0.1:8000/tasks/1
{"id":1}""",
                "mistakes": """- 处理器写成普通 `def`，得到 `TypeError: object JSONResponse can't be used in 'await' expression`。
- 只处理自定义异常，忘了框架抛的 `HTTPException` 仍是老结构，前端还得兼容两套。
- 把 `str(exc)` 或 traceback 放进响应，泄漏内部路径与实现。
- 在处理器里再抛异常，导致 500 套 500。
- 只改状态码不改结构，前端依然难以统一解析。""",
                "error_analysis": """`TypeError: object JSONResponse can't be used in 'await' expression`
—— 处理器写成了同步函数。改成 `async def`。

自定义 404 不生效
—— 注册的异常类与实际抛出的不一致（比如抛的是 `HTTPException`，却注册了 `TaskNotFound`）。

500 响应里出现 traceback
—— 没有兜底处理器，框架把调试信息带了出来。生产环境应关闭 debug 并加 `Exception` 处理器。""",
                "beginner_practice": """1. 加一个 `PermissionDenied` 异常与处理器，返回 403 与统一结构。
2. 注册 `StarletteHTTPException` 处理器，把默认的 `{"detail": ...}` 也改成统一结构。""",
                "advanced_practice": """设计一套错误码规范：至少包含「资源不存在 / 参数非法 / 未认证 / 无权限 / 冲突」五类，
说明 code 的命名规则、是否要把 code 写进文档、以及前端如何按 code 做不同的兜底动作。""",
                "quiz_note": "本节 6 道题：2 道基础理解（处理器作用、为什么用 async）+ 2 道代码阅读（读响应结构、读 loc）+ 2 道应用练习（加处理器、改结构）。",
                "summary": """业务异常用自定义类表达，处理器负责把它翻译成统一结构的响应。
处理器必须 `async def` 且返回 `JSONResponse`，才能自定义状态码。
校验错误单独处理，保留 `loc` 让前端能按字段定位。""",
                "next_lesson": "下一节写中间件：在请求进出的路上统一记录耗时与追踪 ID。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-09-01",
                        "name": "统一异常处理与错误结构",
                        "goal": "能把业务异常与校验异常收敛成统一结构的错误响应。",
                        "minutes": 40,
                        "criteria": "能注册自定义异常与校验异常处理器，并说清为什么必须是 async。",
                        "requires": ["fastapi-backend-08-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-09-01-1",
                        "kp": 0,
                        "title": "加一个 403 处理器",
                        'description': '定义 `PermissionDenied`，用处理器返回 403 与 `{"code":"FORBIDDEN","message":...}`，并给一个会抛它的接口。',
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class PermissionDenied(Exception):
    pass


@app.exception_handler(PermissionDenied)
async def handle_forbidden(request: Request, exc: PermissionDenied) -> JSONResponse:
    return JSONResponse(status_code=403, content={"code": "FORBIDDEN", "message": "没有权限"})


@app.get("/admin")
def admin() -> dict:
    raise PermissionDenied()''',
                        "explanation": "结构与 404 保持一致，前端只需按 code 分支处理，不用为每种错误写一套解析。",
                    },
                    {
                        "code": "fa-ex-09-01-2",
                        "kp": 0,
                        "title": "统一 HTTPException 结构",
                        "description": "注册 `StarletteHTTPException` 处理器，把框架默认的 detail 转成 code/message 结构，并注意保留原有状态码。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": f"HTTP_{exc.status_code}", "message": exc.detail},
    )''',
                        "explanation": "必须用 Starlette 的 HTTPException 注册（FastAPI 的继承自它），且要沿用 exc.status_code，否则全变成 500。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-09-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "自定义异常处理器必须写成什么形式？",
                        "options": [
                            ("A", "async def handler(request, exc) 并返回 Response"),
                            ("B", "def handler(exc) 并返回 dict"),
                            ("C", "async def handler(exc) 并返回 dict"),
                            ("D", "class Handler 继承 Exception"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "Starlette 会 await 处理器，所以必须 async；返回 JSONResponse 才能控制状态码。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-09-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "统一错误结构的价值有？（多选）",
                        "options": [
                            ("A", "前端只需一套解析逻辑"),
                            ("B", "监控可按 code 聚合错误"),
                            ("C", "能自动修复业务 bug"),
                            ("D", "避免把内部实现细节暴露给调用方"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "统一结构只能规范输出，不会自动修复逻辑错误，C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-09-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "请求 `/tasks/101` 得到的响应体是？",
                        "options": [
                            ("A", '{"detail":"Not Found"}'),
                            ("B", '{"code":"TASK_NOT_FOUND","message":"任务 101 不存在"}'),
                            ("C", '{"id":101}'),
                            ("D", "500 错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`task_id > 100` 抛出 `TaskNotFound`，由注册的处理器生成统一结构。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-09-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把 `str(exc)` 直接放进响应体，有助于前端更快定位问题。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "异常字符串常含内部路径、SQL 或依赖名，属于信息泄漏；细节应进日志，响应只给稳定的 code 与面向用户的 message。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-09-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全注册语句，使 `TaskNotFound` 走自定义处理器。横线处应填什么？\n\n```python\n____(TaskNotFound)\nasync def handle_task_not_found(request, exc): ...\n```",
                        "options": [
                            ("A", "@app.exception_handler"),
                            ("B", "@app.error_handler"),
                            ("C", "@app.catch"),
                            ("D", "@app.on_error"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "FastAPI 提供的是 `exception_handler`；其余名字都不存在。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-09-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么业务异常类不该直接继承 `HTTPException`？",
                        "answer": {"value": "业务层一旦依赖 HTTPException，就把「业务规则」和「HTTP 传输」绑死了——同一段逻辑换成 CLI、定时任务或消息队列调用时无法复用，也无法在不改业务代码的前提下调整错误码映射。更好的做法是定义纯业务异常，在接口层（或异常处理器）统一翻译成 HTTP 响应。"},
                        "explanation": "核心是分层：业务不懂 HTTP，接口层负责翻译。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-09-lesson-02",
                "objectives": """1. 会写 HTTP 中间件，在请求进出时执行逻辑；
2. 理解中间件的执行顺序（洋葱模型）；
3. 能给每个请求生成追踪 ID 并写回响应头；
4. 知道中间件与依赖的分工边界。""",
                "why_learn": """接口耗时、请求 ID、响应头、访问日志——这些每请求都要做的事，不可能在每个接口里写一遍。
中间件位于「所有请求的必经之路」，用一处代码覆盖所有接口，还能在响应回来后补充信息。""",
                "concepts": """**中间件**：包裹整个请求处理流程的函数，`call_next(request)` 前后各有一段逻辑。
**洋葱模型**：后注册的中间件在外层，请求先进外层、响应后出外层。
**追踪 ID**：入口生成或透传 `x-request-id`，写日志与响应头，便于串起一次调用链。
**与依赖的区别**：依赖作用在接口级、能拿到类型化参数；中间件作用在全局、只能看 Request。""",
                "plain": """中间件像小区的门禁：进门前刷卡登记，出门时再看一眼有没有带东西出去。
不管你去哪一户（哪个接口），门禁都在那儿，所以「每请求都要做的事」交给它最省。
但它只知道你进出，不知道你去哪户干什么——具体业务参数还得靠依赖与接口自己处理。""",
                "syntax": """**API 说明**

```python
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.3f}"
    return response
```

- 必须 `async def`，必须 `await call_next(request)`。
- 想在异常时也记录，需要 `try/finally` 包住。
- 中间件里不要做重活（如查库），否则每个请求都变慢。""",
                "example_code": '''import time
import uuid

from fastapi import FastAPI, Request

app = FastAPI(title="中间件示例")


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:8]
    start = time.perf_counter()
    response = await call_next(request)
    cost = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-ms"] = f"{cost:.1f}"
    print(f"request_id={request_id} path={request.url.path} cost_ms={cost:.1f}")
    return response


@app.get("/tasks")
def list_tasks() -> list[dict]:
    return [{"id": 1, "title": "写周报"}]


@app.get("/slow")
def slow() -> dict:
    time.sleep(0.05)
    return {"ok": True}''',
                "code_lines": """1. `@app.middleware("http")` 注册一个 HTTP 中间件，对所有路由生效。
2. 优先透传调用方带来的 `x-request-id`，没有就生成 8 位随机串——这样跨服务能串起来。
3. `time.perf_counter()` 比 `time.time()` 更适合测耗时，不受系统时钟调整影响。
4. `await call_next(request)` 才是真正执行后续处理（含依赖与接口函数）。
5. 响应回来后可以继续改响应头，这是中间件独有的能力。
6. 耗时同时写进响应头与日志：前端能在网络面板看到，后端能按 request_id 检索。
7. 中间件对 `/tasks` 与 `/slow` 一视同仁，不需要在每个接口里重复。""",
                "output": """curl -i http://127.0.0.1:8000/tasks
HTTP/1.1 200 OK
x-request-id: 3f9a1c2d
x-process-time-ms: 0.6

[{"id":1,"title":"写周报"}]

curl -i -H "x-request-id: trace-001" http://127.0.0.1:8000/slow
HTTP/1.1 200 OK
x-request-id: trace-001
x-process-time-ms: 50.4

# 服务端日志
request_id=trace-001 path=/slow cost_ms=50.4""",
                "mistakes": """- 忘了 `await call_next(request)`，直接返回自己的 Response，接口完全不执行。
- 中间件写成 `def`，`call_next` 无法 await。
- 在中间件里查数据库或调外部接口，所有请求都被拖慢。
- 生成新 request_id 却不透传上游的，跨服务追踪断链。
- 把业务判断（如权限）写进中间件，导致规则分散、难测试。""",
                "error_analysis": """`RuntimeError: No response returned.`
—— 中间件没有把 `call_next` 的结果返回，或提前 return 了 None。

`TypeError: object coroutine can't be used in 'await' expression`
—— `call_next` 前少了 `await`。

接口返回 200 但响应头没有 X-Request-ID
—— 中间件注册在 include_router 之后不生效？实际原因多是异常路径提前返回，没走到加头那段。""",
                "beginner_practice": """1. 给中间件加 `try/finally`，保证异常时也打印 request_id 与耗时。
2. 新增 `/boom` 接口抛异常，验证日志里仍有记录。""",
                "advanced_practice": """实现「慢请求告警」：耗时超过 200ms 时在日志里打 WARNING 并带上路径与 request_id，
说明为什么告警阈值要可配置，以及如何避免日志被高频慢请求刷爆。""",
                "quiz_note": "本节 6 道题：2 道基础理解（中间件作用、执行顺序）+ 2 道代码阅读（读响应头、读异常路径）+ 2 道应用练习（加 try/finally、加告警）。",
                "summary": """中间件包裹所有请求，`call_next` 前后分别是「进入前」与「响应后」。
必须 `async def` 且 `await call_next`，否则接口不会执行。
每请求都要做的事（追踪 ID、耗时、响应头）放中间件，业务判断放依赖或服务层。""",
                "next_lesson": "下一节讲 CORS：前端在 3000 端口调 8000 端口，为什么浏览器先发一个 OPTIONS。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-09-02",
                        "name": "HTTP 中间件与请求追踪",
                        "goal": "能编写中间件统一记录耗时与追踪 ID。",
                        "minutes": 35,
                        "criteria": "能写出给响应加 request-id 与耗时头的中间件，并解释异常路径的处理。",
                        "requires": ["fastapi-backend-09-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-09-02-1",
                        "kp": 0,
                        "title": "异常也要记日志",
                        "description": "把中间件改成 try/finally 形式，保证接口抛异常时仍打印 request_id 与耗时，并新增一个必然抛异常的接口验证。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:8]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        cost = (time.perf_counter() - start) * 1000
        print(f"request_id={request_id} path={request.url.path} cost_ms={cost:.1f}")
    response.headers["X-Request-ID"] = request_id
    return response''',
                        "explanation": "日志放在 finally 里才能覆盖异常路径；响应头只能在成功路径加，因为异常时没有 response 对象。",
                    },
                    {
                        "code": "fa-ex-09-02-2",
                        "kp": 0,
                        "title": "中间件还是依赖",
                        "description": "判断以下四件事该放中间件还是依赖：① 生成请求 ID ② 校验当前用户权限 ③ 记录响应耗时 ④ 解析分页参数。",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''① 中间件（全局、无需类型化参数）
② 依赖（需要按接口区分、要拿到用户对象、要能单测替换）
③ 中间件（横切所有请求）
④ 依赖（要类型化校验并注入接口）''',
                        "explanation": "判断标准：是否需要类型化参数与按接口差异化 → 依赖；否则全局横切 → 中间件。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-09-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "中间件里 `await call_next(request)` 的作用是？",
                        "options": [
                            ("A", "继续执行后续中间件与接口"),
                            ("B", "重新发送一次请求"),
                            ("C", "记录日志"),
                            ("D", "终止请求"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "它是调用链的下一环，缺了它接口函数根本不会执行。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-09-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于中间件，正确的说法有？（多选）",
                        "options": [
                            ("A", "后注册的中间件更靠外层"),
                            ("B", "可以修改响应头"),
                            ("C", "适合做重 IO 操作，如查库"),
                            ("D", "对所有路由生效"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "中间件在每个请求上都执行，做重 IO 会整体拖慢服务，C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-09-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "带 `x-request-id: trace-001` 请求 `/slow`，响应头里的 `x-request-id` 是？",
                        "options": [("A", "新生成的随机串"), ("B", "trace-001"), ("C", "空"), ("D", "不存在")],
                        "answer": {"value": "B"},
                        "explanation": "中间件优先透传调用方带来的 ID，便于跨服务追踪。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-09-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "中间件里拿不到接口函数解析好的 Pydantic 模型对象。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "A"},
                        "explanation": "中间件只看得到原始 Request，参数解析发生在更内层；需要类型化数据请用依赖。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-09-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全中间件，使响应带上 `X-Request-ID`。横线处应填什么？\n\n```python\n@app.middleware(\"http\")\nasync def add_trace_id(request: Request, call_next):\n    response = ____\n    response.headers[\"X-Request-ID\"] = \"abc123\"\n    return response\n```",
                        "options": [
                            ("A", "await call_next(request)"),
                            ("B", "call_next(request)"),
                            ("C", "await request"),
                            ("D", "return call_next(request)"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`call_next` 是协程，必须 await；少了 await 会拿到 coroutine 对象，改 headers 直接报错。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-09-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么不该把权限校验写在中间件里？",
                        "answer": {"value": "① 中间件拿不到类型化参数与依赖解析结果，只能按路径字符串硬编码规则，容易漏；② 无法按接口差异化声明，规则分散在全局；③ 不好单测，也难以在测试里整体替换。正解是用依赖（如 `Depends(require_admin)`）挂在需要的路由或 router 上，规则可见、可测、可组合。"},
                        "explanation": "核心是「可声明、可测试、按接口差异化」三点。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "fastapi-backend-10",
        "title": "CORS 与同步异步接口",
        "description": "跨域要配对，异步要用对。",
        "order_index": 10,
        "lessons": [
            {
                "code": "fastapi-backend-10-lesson-01",
                "objectives": """1. 能解释浏览器的同源策略与预检请求；
2. 会用 `CORSMiddleware` 按白名单配置跨域；
3. 知道 `allow_origins=["*"]` 与 `allow_credentials` 不能同时生效；
4. 能通过响应头判断跨域配置是否真的生效。""",
                "why_learn": """前端跑在 `localhost:3000`、后端在 `8000`，浏览器会把它们当成「不同源」并拦掉响应。
报错信息还特别容易误导：`No 'Access-Control-Allow-Origin' header`，看起来像后端没返回，实际是浏览器没让你看。""",
                "concepts": """**同源**：协议 + 域名 + 端口三者完全相同。
**简单请求与预检**：非简单请求（自定义头、PUT/DELETE、JSON）先发 `OPTIONS` 预检。
**CORS 响应头**：`Access-Control-Allow-Origin`、`-Methods`、`-Headers`、`-Credentials`。
**通配与凭据互斥**：`allow_origins=["*"]` 时浏览器拒绝携带凭据。
**允许来源要精确**：写具体域名，不要用正则拼。""",
                "plain": """同源策略像小区门禁的默认规则：只认本小区的访客。
CORS 是物业给外来访客开的通行条，由「后端」签发，浏览器负责检查。
预检请求是访客先来问一句「我能带工具箱进吗」，物业回一张清单，访客才真正上门。
通行条上写「所有人」时，就不能同时要求「必须刷身份证」（凭据），这是浏览器定死的规矩。""",
                "syntax": """**API 说明**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

- `allow_origins` 必须是完整来源（含协议与端口），不要带路径。
- 需要 Cookie/Authorization 时设 `allow_credentials=True`，此时不能用 `*`。
- `max_age` 可缓存预检结果，减少 OPTIONS 次数。""",
                "example_code": '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CORS 示例")

ALLOWED_ORIGINS = ["http://localhost:3000", "https://xiaoma.example.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)


@app.get("/tasks")
def list_tasks() -> list[dict]:
    return [{"id": 1, "title": "写周报"}]''',
                "code_lines": """1. `ALLOWED_ORIGINS` 集中声明白名单，避免散落在各处。
2. `add_middleware` 必须在应用启动前调用，且顺序影响外层关系。
3. `allow_credentials=True` 允许浏览器带上 Cookie 与 Authorization。
4. `allow_methods` 显式列出用到的方法，比 `["*"]` 更可控。
5. `allow_headers` 要包含前端实际发送的自定义头，否则预检不通过。
6. `expose_headers` 让前端 JS 能读到自定义响应头（默认只能读少数几个）。
7. `max_age=600` 让浏览器缓存预检结果 10 分钟，减少 OPTIONS 请求。""",
                "output": """# 预检请求（浏览器自动发起）
curl -i -X OPTIONS http://127.0.0.1:8000/tasks \\
  -H "Origin: http://localhost:3000" \\
  -H "Access-Control-Request-Method: POST" \\
  -H "Access-Control-Request-Headers: content-type"
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:3000
access-control-allow-methods: GET, POST, PATCH, DELETE
access-control-allow-headers: Content-Type, Authorization, X-Request-ID
access-control-allow-credentials: true
access-control-max-age: 600

# 不在白名单的来源：没有 allow-origin 头，浏览器拦下响应
curl -i -X OPTIONS http://127.0.0.1:8000/tasks -H "Origin: http://evil.example.com"
HTTP/1.1 200 OK
（无 access-control-allow-origin）""",
                "mistakes": """- `allow_origins=["*"]` 同时 `allow_credentials=True`，浏览器直接拒绝带凭据请求。
- 把来源写成 `localhost:3000`（漏了 `http://`），永远不匹配。
- 只配了 `allow_methods` 没配 `allow_headers`，带 `Content-Type: application/json` 的 POST 预检失败。
- 以为报错是后端 500，其实后端正常返回、浏览器拦了响应。
- 用 `allow_origin_regex=".*"` 图省事，等于对全网开放。""",
                "error_analysis": """`No 'Access-Control-Allow-Origin' header is present on the requested resource`
—— 来源不在白名单，或中间件没注册。用 curl 加 `Origin` 头看响应头是否出现。

`The value of the 'Access-Control-Allow-Origin' header must not be the wildcard '*' when the request's credentials mode is 'include'`
—— `*` 与凭据互斥。改成具体来源列表。

预检返回 405
—— OPTIONS 被路由或网关拦了。确认中间件在应用层生效，且反向代理透传 OPTIONS。""",
                "beginner_practice": """1. 把白名单改成只允许 `http://localhost:3000`，用 curl 验证其他来源没有 allow-origin 头。
2. 去掉 `expose_headers`，观察前端读不到 `X-Request-ID`。""",
                "advanced_practice": """生产环境同时有「同域部署」与「分离部署」两种形态：
说明同域时是否还需要 CORS、分离部署时白名单如何按环境配置，以及预检请求对延迟的影响与优化手段。""",
                "quiz_note": "本节 6 道题：2 道基础理解（同源、预检）+ 2 道代码阅读（读响应头、读配置冲突）+ 2 道应用练习（修白名单、加 expose）。",
                "summary": """同源由协议、域名、端口共同决定，端口不同就算跨域。
CORS 由后端签发响应头，浏览器负责检查；非简单请求会先发 OPTIONS 预检。
`allow_origins=["*"]` 与 `allow_credentials=True` 不能共存，白名单要写完整来源。""",
                "next_lesson": "下一节讲 def 与 async def：为什么在 async 接口里写 `time.sleep` 会拖垮整个服务。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-10-01",
                        "name": "CORS 跨域配置",
                        "goal": "能按白名单配置跨域，并解释预检请求与凭据限制。",
                        "minutes": 30,
                        "criteria": "能配出带凭据的跨域并说清为什么不能用通配。",
                        "requires": ["fastapi-backend-09-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-10-01-1",
                        "kp": 0,
                        "title": "修好跨域配置",
                        "description": "下面的配置在带 Cookie 时失败，指出问题并给出正确写法：`allow_origins=[\"*\"], allow_credentials=True`。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://xiaoma.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)''',
                        "explanation": "带凭据时必须回显具体来源，浏览器不接受 `*`；白名单要与实际前端地址一致。",
                    },
                    {
                        "code": "fa-ex-10-01-2",
                        "kp": 0,
                        "title": "用 curl 验证跨域",
                        "description": "写出验证跨域是否生效的两条 curl 命令（一条在白名单、一条不在），并说明看哪个响应头。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''curl -i -X OPTIONS http://127.0.0.1:8000/tasks -H "Origin: http://localhost:3000"
curl -i -X OPTIONS http://127.0.0.1:8000/tasks -H "Origin: http://evil.example.com"

看 access-control-allow-origin 是否回显对应来源；不在白名单时应缺失该头。''',
                        "explanation": "不要只靠浏览器控制台，curl 能看到原始响应头，更容易判断是「后端未返回」还是「浏览器拦截」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-10-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "前端在 `http://localhost:3000`，后端在 `http://localhost:8000`，这属于？",
                        "options": [("A", "同源"), ("B", "跨域（端口不同）"), ("C", "跨协议"), ("D", "同一主机即同源")],
                        "answer": {"value": "B"},
                        "explanation": "同源要求协议、域名、端口三者一致，端口不同即为跨域。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-10-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些请求会触发预检 OPTIONS？（多选）",
                        "options": [
                            ("A", "带自定义头 `X-Request-ID` 的 GET"),
                            ("B", "`Content-Type: application/json` 的 POST"),
                            ("C", "PUT 请求"),
                            ("D", "不带自定义头的 GET"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "简单请求（GET/HEAD/POST + 有限 Content-Type + 无自定义头）不预检，D 不触发。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-10-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "来源不在白名单时，示例服务的预检响应是什么样？",
                        "options": [
                            ("A", "403 且带错误信息"),
                            ("B", "200 但没有 access-control-allow-origin 头"),
                            ("C", "500"),
                            ("D", "直接断开连接"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "CORS 中间件只是不回显 allow-origin，浏览器据此拦截；服务端状态码仍是 200。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-10-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`expose_headers` 决定前端 JS 能读取哪些自定义响应头。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "A"},
                        "explanation": "跨域时默认只能读少数安全头，自定义头（如 X-Request-ID）需要通过 expose_headers 暴露。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-10-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全配置，使 `http://localhost:3000` 允许跨域且可带凭据。横线处应填什么？\n\n```python\napp.add_middleware(CORSMiddleware, ____, allow_credentials=True)\n```",
                        "options": [
                            ("A", 'allow_origins=["http://localhost:3000"]'),
                            ("B", 'allow_origins=["*"]'),
                            ("C", 'allow_origin="localhost:3000"'),
                            ("D", 'origins="http://localhost:3000"'),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "参数名是 `allow_origins`，值必须是含协议与端口的完整来源列表；`*` 与凭据互斥。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-10-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "同域部署（前端由同一域名提供服务并反向代理到后端）时还需要 CORS 吗？为什么？",
                        "answer": {"value": "通常不需要。浏览器看到的是同一个来源（协议、域名、端口一致），不存在跨域限制，请求直接由反向代理转发给后端。但要注意：如果前端页面从别的域名嵌入、或存在多个前端域名共用一套后端，仍需为这些来源配置 CORS；另外 CORS 不是访问控制手段，真正的权限校验必须在后端做。"},
                        "explanation": "要点：同源即无需 CORS；但 CORS 不能替代鉴权，这是常被混淆的一点。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-10-lesson-02",
                "objectives": """1. 能说清 `def` 与 `async def` 接口在线程/事件循环上的差别；
2. 能判断一段代码是否会阻塞事件循环；
3. 会用 `run_in_threadpool` 或异步库处理阻塞调用；
4. 能为不同场景选择合适的接口写法。""",
                "why_learn": """在 `async def` 里写一句 `time.sleep(1)` 或同步 `requests.get`，单进程的整个服务会卡住一秒——所有并发请求一起等。
这不是「慢一点」，而是把并发能力直接归零。理解这一点，才知道什么时候该用异步。""",
                "concepts": """**事件循环**：单线程调度协程，遇到 `await` 才切换。
**def 接口**：FastAPI 放进线程池执行，不阻塞事件循环，但有线程数上限。
**async def 接口**：直接在事件循环里执行，里面不能有阻塞调用。
**阻塞的代价**：事件循环被占住时，其他请求全部排队。
**正确做法**：阻塞 IO 用 `def`（线程池）或异步客户端；CPU 密集交给进程池/队列。""",
                "plain": """事件循环像一个服务员：点单、上菜、结账都由他一人跑，但他只在「等厨房」的时候去招呼下一桌。
`await` 就是「等厨房」的那一下，这时他能去别桌。
如果你让他在原地盯着锅看（阻塞调用），所有桌就都干等着——看着只是一个接口慢，实际是全店停摆。""",
                "syntax": """**API 说明**

```python
@app.get("/sync")
def sync_ep():            # 线程池执行，可安全调用阻塞库
    return blocking_io()

@app.get("/async")
async def async_ep():     # 事件循环执行，只能用异步库
    return await async_io()

from starlette.concurrency import run_in_threadpool
result = await run_in_threadpool(blocking_io)
```

- 判断标准：库里有没有 `async` 版本？有就用 async；只有同步版就用 `def` 或 `run_in_threadpool`。
- CPU 密集任务不要放线程池，会拖慢进程，应交给独立进程或队列。""",
                "example_code": '''import asyncio
import time

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

app = FastAPI(title="同步与异步示例")


def blocking_io(seconds: float = 0.2) -> str:
    time.sleep(seconds)          # 模拟阻塞调用：同步库、磁盘、外部 HTTP
    return f"slept {seconds}s"


@app.get("/sync")
def sync_endpoint() -> dict:
    # def 接口：FastAPI 放进线程池，阻塞不影响事件循环
    return {"mode": "sync", "result": blocking_io()}


@app.get("/async")
async def async_endpoint() -> dict:
    # async 接口：用 asyncio.sleep，等待期间让出事件循环
    await asyncio.sleep(0.2)
    return {"mode": "async"}


@app.get("/async-safe")
async def async_safe() -> dict:
    # async 接口里必须调用阻塞库时，交给线程池
    result = await run_in_threadpool(blocking_io)
    return {"mode": "async-safe", "result": result}


@app.get("/async-wrong")
async def async_wrong() -> dict:
    # 反例：在协程里直接阻塞，整个事件循环被占住
    return {"mode": "wrong", "result": blocking_io()}''',
                "code_lines": """1. `blocking_io` 用 `time.sleep` 模拟同步库调用，这是最常见的阻塞来源。
2. `/sync` 用 `def`：FastAPI 自动放进线程池，事件循环空出来处理别的请求。
3. `/async` 用 `asyncio.sleep`：等待时让出事件循环，这是异步该有的样子。
4. `run_in_threadpool` 让 async 接口安全调用阻塞函数，兼顾两种世界。
5. `/async-wrong` 是反例：`async def` 里直接 `time.sleep`，事件循环被占住。
6. 四个接口共用同一个阻塞函数，差别只在「谁来执行它」。
7. 用压测工具并发请求 `/async-wrong` 与 `/sync`，能直观看到吞吐差异。""",
                "output": """curl http://127.0.0.1:8000/async
{"mode":"async"}

curl http://127.0.0.1:8000/sync
{"mode":"sync","result":"slept 0.2s"}

# 10 个并发请求 /async-wrong：总耗时约 2.0s（串行，事件循环被逐个占住）
# 10 个并发请求 /sync：总耗时约 0.2—0.4s（线程池并行）
# 10 个并发请求 /async：总耗时约 0.2s（协程并发）

# 结论：/async-wrong 在并发下等于把自己变成了单线程串行服务""",
                "mistakes": """- 在 `async def` 里用 `requests`、`time.sleep`、同步数据库驱动。
- 以为写成 `async def` 就自动变快——里面全是阻塞调用时反而更慢。
- 把 CPU 密集计算放进线程池，GIL 下依然串行，还占满线程。
- `def` 接口里做超长任务，把线程池占满，后续请求排队。
- 混用同步 Session 与 async 接口，导致连接被长时间占用。""",
                "error_analysis": """接口在压测下延迟随并发线性上升
—— 典型的事件循环被阻塞。检查 `async def` 里是否有同步 IO。

`RuntimeError: This event loop is already running`
—— 在协程里调用了会自己启动事件循环的同步库（如 `asyncio.run`）。

线程池被打满后请求超时
—— `def` 接口里有长任务。给线程池设上限，把长任务移到后台任务或队列。""",
                "beginner_practice": """1. 用 `ab` 或 `wrk` 各压 10 并发，比较 `/sync` 与 `/async-wrong` 的总耗时。
2. 把 `/async-wrong` 改成 `run_in_threadpool` 版本，再压一次。""",
                "advanced_practice": """设计一个「导出报表」接口：需要 30 秒 CPU 计算。
说明为什么不能直接放 async 接口、也不适合放线程池，给出你的方案（后台任务 + 轮询/回调 + 队列），并说明如何告知前端进度。""",
                "quiz_note": "本节 6 道题：2 道基础理解（def 与 async 区别、阻塞代价）+ 2 道代码阅读（判断哪段会阻塞）+ 2 道应用练习（改写法、选方案）。",
                "summary": """`def` 接口跑在线程池，`async def` 跑在事件循环；后者不允许阻塞调用。
事件循环被占住时所有并发请求一起排队，这是异步最常见的性能事故。
同步库用 `def` 或 `run_in_threadpool`，异步库用 `await`，CPU 密集交给进程或队列。""",
                "next_lesson": "下一节接数据库：把 SQLAlchemy 会话做成依赖，接口层不写 SQL。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-10-02",
                        "name": "同步与异步接口及阻塞识别",
                        "goal": "能判断接口该用 def 还是 async def，并识别阻塞调用。",
                        "minutes": 45,
                        "criteria": "能指出一段 async 代码里的阻塞点，并给出两种修法。",
                        "requires": ["fastapi-backend-10-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-10-02-1",
                        "kp": 0,
                        "title": "找出阻塞点",
                        "description": "下面代码有什么问题？给出两种修法：\n```python\n@app.get(\"/report\")\nasync def report():\n    data = requests.get(\"https://api.example.com/report\").json()\n    time.sleep(1)\n    return data\n```",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''问题：async 接口里用了 requests 与 time.sleep 两个阻塞调用，事件循环被占住。
修法一：改成 def 接口，交给线程池执行。
修法二：保持 async，改用 httpx.AsyncClient 与 asyncio.sleep。''',
                        "explanation": "两种修法对应「换执行位置」与「换异步库」两条思路，都能恢复并发能力。",
                    },
                    {
                        "code": "fa-ex-10-02-2",
                        "kp": 0,
                        "title": "CPU 密集任务该放哪",
                        "description": "30 秒的报表计算，为什么既不该放 async 接口也不该放线程池？给出方案。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''放 async：事件循环被占 30 秒，整个服务停摆。
放线程池：GIL 下 CPU 计算无法并行，还会占满线程导致其他请求排队。
方案：接口只负责创建任务并立即返回 202 + task_id，计算交给独立进程/任务队列（Celery、RQ、后台 worker），前端轮询 /tasks/{id} 或订阅进度。''',
                        "explanation": "关键是把「长耗时计算」移出请求-响应周期，接口只做提交与查询。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-10-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`def` 定义的接口在 FastAPI 中如何执行？",
                        "options": [
                            ("A", "放入线程池执行"),
                            ("B", "直接在事件循环执行"),
                            ("C", "每次新建一个进程"),
                            ("D", "由 uvicorn 转成协程"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "FastAPI 对同步函数用线程池包装，避免阻塞事件循环；`async def` 才直接在事件循环里跑。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-10-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列调用放在 `async def` 接口里会阻塞事件循环的是？（多选）",
                        "options": [
                            ("A", "time.sleep(1)"),
                            ("B", "requests.get(url)"),
                            ("C", "await asyncio.sleep(1)"),
                            ("D", "同步数据库驱动执行查询"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "`await asyncio.sleep` 会让出事件循环，正是异步的正确用法。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-10-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "并发 10 个请求 `/async-wrong`（每个阻塞 0.2 秒），总耗时最接近？",
                        "options": [("A", "0.2 秒"), ("B", "2 秒"), ("C", "0.02 秒"), ("D", "无法确定")],
                        "answer": {"value": "B"},
                        "explanation": "事件循环被逐个占住，10 个请求串行执行，约 10 × 0.2 = 2 秒。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-10-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把接口从 `def` 改成 `async def` 就一定能提升并发能力。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "只有内部调用改为非阻塞（异步库/await）才有收益；否则反而把线程池的隔离性丢了。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-10-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全代码，使 async 接口安全调用阻塞函数 `blocking_io()`。横线处应填什么？\n\n```python\nfrom starlette.concurrency import run_in_threadpool\n\n@app.get(\"/safe\")\nasync def safe():\n    result = ____\n    return {\"result\": result}\n```",
                        "options": [
                            ("A", "await run_in_threadpool(blocking_io)"),
                            ("B", "run_in_threadpool(blocking_io)"),
                            ("C", "await blocking_io()"),
                            ("D", "threading.Thread(target=blocking_io)"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`run_in_threadpool` 返回可等待对象，必须 await；不 await 拿到的是未执行的结果对象。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-10-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "团队既有同步 ORM 代码，又要上异步 FastAPI，你会怎么决策？",
                        "answer": {"value": "两条路：① 保持同步 ORM，接口统一用 `def`（线程池），并发靠多 worker 与连接池，改造成本最低；② 逐步迁移到异步驱动（如 asyncpg/aiosqlite + AsyncSession），接口改 `async def`，但要注意不能在协程里混用同步会话。决策依据是并发规模与现有代码量：QPS 不高时方案 ① 更划算；已明确要扛高并发且愿意改造，才走 ②。绝不能混着写，否则连接被长时间占用、事件循环被阻塞。"},
                        "explanation": "要点是「两条路都可行，但不能混」，并给出判断依据（并发规模与改造成本）。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
