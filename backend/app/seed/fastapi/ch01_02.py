"""FastAPI 后端开发：第 1—4 章（API 基础、安装启动、路由与路径参数、查询参数）。

用户要求的 10 个教学模块与数据库 15 列的对应关系（全书统一）：

| 需求模块 | 数据库列 |
| --- | --- |
| 本节目标 | learning_objectives |
| 核心知识 | concept_explanation（+ plain_explanation 通俗解释） |
| API 说明 | syntax_explanation（装饰器 / 函数签名 / 参数与返回值说明） |
| 完整代码示例 | example_code |
| 逐行解析 | code_explanation |
| 请求和响应示例 | example_output（含 curl 请求与真实响应体） |
| 常见错误 | common_mistakes（+ error_analysis 报错原文与成因） |
| 实战练习 | beginner_exercises / advanced_exercises（+ practice 题库） |
| 小测验 | quiz_note（+ questions 六道题） |
| 学习总结 | summary（+ next_lesson 下一课建议） |
"""

CHAPTERS: list[dict] = [
    {
        "code": "fastapi-backend-01",
        "title": "Web 后端与 API 基础",
        "description": "先想清楚请求怎么来、响应怎么回，再动手写代码。",
        "order_index": 1,
        "lessons": [
            {
                "code": "fastapi-backend-01-lesson-01",
                "objectives": """1. 说清一次 HTTP 请求由哪几部分组成；
2. 能按语义选择 GET / POST / PUT / PATCH / DELETE；
3. 能用状态码准确表达「成功、建好、没找到、参数错、服务器错」；
4. 理解幂等与安全，知道为什么重试 GET 是安全的。""",
                "why_learn": """后端工程师每天在做的事，本质是「收到请求，返回响应」。不理解请求怎么走、状态码代表什么，写出来的接口就会出现「删除成功却返回 200 带错误信息」「重复提交建出两条数据」这类问题，前端也没法根据状态码做统一处理。""",
                "concepts": """**请求行**：方法 + 路径 + 协议版本，如 `GET /tasks/42 HTTP/1.1`。
**请求头**：键值对，承载内容类型、认证令牌、客户端信息。
**请求体**：POST/PUT/PATCH 携带的数据，通常是 JSON。
**响应状态码**：三位数字，1xx 信息、2xx 成功、3xx 重定向、4xx 客户端错、5xx 服务端错。
**幂等**：同样的请求执行一次和执行多次，服务端状态一致。GET、PUT、DELETE 幂等，POST 不幂等。
**安全**：不会改变服务端状态的方法（GET、HEAD）称为安全方法，可以被爬虫或预取随意调用。""",
                "plain": """把后端想成一家餐厅：请求是点菜单，方法是「点菜 / 加菜 / 改菜 / 退菜」，路径是桌号，请求体是具体要求。
状态码是服务员的回话：200 是「好的马上来」，201 是「新菜已下单」，404 是「菜单上没这道菜」，422 是「你说的做法厨房做不了」。
幂等就是「同一句话重复说三遍，结果和说一遍一样」——所以「加一份米饭」不幂等，「把米饭改成两碗」幂等。""",
                "syntax": """**API 说明（HTTP 语义速查）**

| 方法 | 典型路径 | 语义 | 幂等 | 常用成功码 |
| --- | --- | --- | --- | --- |
| GET | `/tasks`、`/tasks/42` | 读取 | 是 | 200 |
| POST | `/tasks` | 新建 | 否 | 201 |
| PUT | `/tasks/42` | 整体替换 | 是 | 200 / 204 |
| PATCH | `/tasks/42` | 局部更新 | 否（名义上不保证） | 200 |
| DELETE | `/tasks/42` | 删除 | 是 | 204 |

**常用状态码**：200 成功、201 已创建、204 成功但无响应体、400 请求格式错、401 未认证、403 无权限、404 不存在、409 冲突、422 参数校验失败、500 服务端异常。""",
                "example_code": '''import json

# 一个不依赖框架的最小「请求 → 响应」处理器，先把 HTTP 语义跑通
ROUTES = ("GET", "POST", "DELETE")


def handle(method: str, path: str) -> tuple[int, dict | None]:
    if method == "GET" and path == "/tasks":
        return 200, {"items": ["写周报", "交报表"]}
    if method == "POST" and path == "/tasks":
        return 201, {"id": 3, "title": "订会议室"}
    if method == "GET" and path.startswith("/tasks/"):
        return 200, {"id": 42, "title": "写周报", "done": False}
    if method == "DELETE" and path.startswith("/tasks/"):
        return 204, None
    return 404, {"detail": "Not Found"}


CASES = [
    ("GET", "/tasks"),
    ("POST", "/tasks"),
    ("GET", "/tasks/42"),
    ("DELETE", "/tasks/42"),
    ("PUT", "/tasks/42"),
]

for method, path in CASES:
    status, body = handle(method, path)
    text = "(无响应体)" if body is None else json.dumps(body, ensure_ascii=False)
    print(method, path, "->", status, text)''',
                "code_lines": """1. `ROUTES` 只用来提示支持哪几个方法，真正的分派靠下面的 `if` 判断。
2. 函数签名 `tuple[int, dict | None]` 明确「返回状态码 + 响应体」，204 时响应体为 `None`。
3. 第一条分支处理列表查询，返回 200，这是最常见的「读」操作。
4. 第二条分支处理新建，返回 201 而不是 200——201 专门表示「资源被创建了」。
5. `/tasks/` 用 `startswith` 匹配，模拟路径参数；真实框架会自动把 `42` 提取成参数。
6. `DELETE` 返回 204 且不带响应体，这是删除成功的标准写法。
7. 最后的 `return 404` 是兜底分支：没匹配上任何路由就说明资源不存在。
8. 循环里用 `json.dumps(..., ensure_ascii=False)` 打印中文，避免输出成 `\\u5199`。""",
                "output": """# 示例中的输出（等价于五次请求的响应）

GET /tasks -> 200 {"items": ["写周报", "交报表"]}
POST /tasks -> 201 {"id": 3, "title": "订会议室"}
GET /tasks/42 -> 200 {"id": 42, "title": "写周报", "done": false}
DELETE /tasks/42 -> 204 (无响应体)
PUT /tasks/42 -> 404 {"detail": "Not Found"}

# 真实服务里的请求与响应
curl -i http://127.0.0.1:8000/tasks/42
HTTP/1.1 200 OK
content-type: application/json

{"id":42,"title":"写周报","done":false}""",
                "mistakes": """- 删除成功却返回 200 并带一段说明文字，前端无法统一处理。
- 新建接口返回 200，调用方无法判断是否真的创建成功。
- 用 GET 做删除（如 `GET /tasks/42/delete`），爬虫或预取会误删数据。
- 所有错误都返回 200，把错误信息塞进响应体，监控和告警全部失效。
- 400 与 422 混用：格式不合法用 400，字段校验失败用 422。""",
                "error_analysis": """`curl: (52) Empty reply from server`
—— 服务没启动或启动失败。先看 uvicorn 日志，常见原因是端口被占用或代码有语法错误。

`{"detail":"Method Not Allowed"}` 返回 405
—— 路径存在但方法不对。查一下接口定义的是 POST 还是 PUT。

状态码 500 但日志里没有业务异常
—— 未捕获异常被框架兜底。看 traceback 的最后一行，通常是依赖缺失或空值访问。""",
                "beginner_practice": """1. 把示例改成：`PATCH /tasks/42` 返回 200 与更新后的对象。
2. 给 `PUT /tasks/42` 补一条分支，返回 200 与整体替换后的对象。""",
                "advanced_practice": """为「提交订单」设计接口：说明路径、方法、成功状态码、重复提交时应该返回什么，
并解释为什么不幂等的 POST 需要幂等键（Idempotency-Key）来防重复下单。""",
                "quiz_note": "本节 6 道题：2 道基础理解（状态码语义、幂等判断）+ 2 道代码阅读（读分派函数）+ 2 道应用练习（补分支、设计接口）。",
                "summary": """一次请求由请求行、请求头、请求体组成；响应用状态码 + 响应体表达结果。
GET/PUT/DELETE 幂等，POST 不幂等；GET 是安全方法，不能改数据。
状态码要精确：201 表示创建、204 表示成功无内容、422 表示字段校验失败。""",
                "next_lesson": "下一节讲 REST 资源设计与 JSON 契约：路径怎么起名、分页筛选放哪里、前后端用什么结构对齐。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-01-01",
                        "name": "HTTP 方法、状态码与幂等",
                        "goal": "能按语义选择 HTTP 方法与状态码，并判断一次请求是否幂等。",
                        "minutes": 30,
                        "criteria": "给出任意一个业务动作，能说清该用哪个方法、返回哪个状态码、是否幂等。",
                        "requires": [],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-01-01-1",
                        "kp": 0,
                        "title": "判断幂等性与状态码",
                        "description": "对「新建任务 / 查询任务列表 / 把任务标记完成 / 删除任务」四个动作，分别写出方法、是否幂等、成功状态码，并说明理由。",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''新建任务：POST /tasks，不幂等，201。重复提交会建出多条。
查询列表：GET /tasks，幂等，200。不改状态，重试无副作用。
标记完成：PATCH /tasks/42，名义上不幂等，200。重复执行结果一致，但语义上不保证。
删除任务：DELETE /tasks/42，幂等，204。第二次删除返回 404，但服务端状态一致。''',
                        "explanation": "关键是把「结果状态一致」和「响应码一致」区分开：DELETE 第二次返回 404 仍然算幂等。",
                    },
                    {
                        "code": "fa-ex-01-01-2",
                        "kp": 0,
                        "title": "补一个 PATCH 分支",
                        "description": "在示例的 handle 函数里补上 PATCH 分支：返回 200 与更新后的任务对象；再补上 PUT 返回 200 的分支。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def handle(method: str, path: str) -> tuple[int, dict | None]:
    if method == "GET" and path == "/tasks":
        return 200, {"items": ["写周报"]}
    if method == "PATCH" and path.startswith("/tasks/"):
        return 200, {"id": 42, "title": "写周报", "done": True}
    if method == "PUT" and path.startswith("/tasks/"):
        return 200, {"id": 42, "title": "写周报", "done": True, "owner": "u1"}
    return 404, {"detail": "Not Found"}''',
                        "explanation": "PATCH 只返回被修改后的完整对象即可；PUT 表示整体替换，返回的对象应包含全部字段。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-01-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "新建资源成功、且需要返回新资源内容时，最合适的状态码是？",
                        "options": [("A", "200"), ("B", "201"), ("C", "204"), ("D", "302")],
                        "answer": {"value": "B"},
                        "explanation": "201 Created 表示资源已创建，通常配合 Location 响应头返回新资源地址；204 不带响应体，无法返回新资源。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-01-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列关于 HTTP 方法与幂等的说法，正确的是？（多选）",
                        "options": [
                            ("A", "GET 是安全方法，不应修改服务端状态"),
                            ("B", "PUT 幂等，重复提交同样的内容结果一致"),
                            ("C", "POST 幂等，所以可以放心重试"),
                            ("D", "DELETE 幂等，第二次删除返回 404 也仍然幂等"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "POST 不幂等，重复提交会产生多条资源，这正是需要幂等键的原因。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-01-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例代码中执行 `handle(\"DELETE\", \"/tasks/42\")` 返回什么？",
                        "options": [
                            ("A", "200 与删除结果"),
                            ("B", "204 与 None"),
                            ("C", "404 与错误信息"),
                            ("D", "抛出异常"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "DELETE 分支命中 `path.startswith(\"/tasks/\")`，返回 (204, None)，所以打印时显示「(无响应体)」。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-01-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把删除接口写成 `GET /tasks/42/delete` 也能工作，因此可以这样设计。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "GET 是安全方法，浏览器预取、爬虫、代理缓存都可能触发它，用它做删除会造成误删。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-01-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全分支：当方法为 PATCH 且路径以 `/tasks/` 开头时，返回 200 和 `{\"id\": 42, \"done\": True}`。横线处应填什么？\n\n```python\nif ____ and path.startswith(\"/tasks/\"):\n    return 200, {\"id\": 42, \"done\": True}\n```",
                        "options": [
                            ("A", 'method == "PATCH"'),
                            ("B", 'method = "PATCH"'),
                            ("C", 'method == PATCH'),
                            ("D", 'method != "PATCH"'),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "比较用 `==`，字符串要加引号；`=` 是赋值，`PATCH` 未加引号会被当成变量名而报 NameError。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-01-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "前端反馈「保存按钮点两次会建出两条任务」，请说明原因与两种修法。",
                        "answer": {"value": "POST 不幂等，重复提交就会重复创建。修法一：前端提交后禁用按钮并做防抖；修法二：客户端生成幂等键随请求发送，服务端对同一幂等键只处理一次（或建唯一约束兜底）。"},
                        "explanation": "答案要同时覆盖「为什么」和「怎么修」，且修法应落在幂等键或唯一约束这类服务端可控手段上。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-01-lesson-02",
                "objectives": """1. 能按资源（名词复数）设计路径，而不是按动作设计；
2. 能判断一个信息应该放在路径、查询串还是请求体里；
3. 能写出统一的 JSON 错误结构；
4. 能为列表接口设计分页、筛选与排序参数。""",
                "why_learn": """路径一旦上线就很难改，前端、移动端、第三方都在调用。按动作起名（`/getTaskList`、`/deleteTask`）会让接口数量爆炸，也没法复用缓存与权限规则；按资源起名则天然对应数据库里的一张表，增删改查都由方法区分。""",
                "concepts": """**资源（resource）**：名词，通常是复数，如 `/tasks`、`/users`。
**集合与单体**：`/tasks` 是集合，`/tasks/42` 是集合中的一个成员。
**层级关系**：从属资源用嵌套路径，如 `/users/7/tasks`。
**参数三处分工**：定位资源用路径参数；筛选、分页、排序用查询参数；创建与更新用请求体。
**统一错误结构**：`{"detail": "..."}` 是最小约定，复杂场景再加 `code`、`field`。
**版本化**：路径前缀 `/v1`，或请求头 `Accept-Version`。""",
                "plain": """设计路径像给文件柜贴标签：先分抽屉（`/tasks`），再分文件夹（`/tasks/42`），不要写「打开第三个抽屉的动作」。
查询参数像筛选条件：你要「第 2 页、只看未完成的」，这些不是资源身份的一部分，而是同一份资源的不同看法，所以放在问号后面。
请求体像填表：新建或修改时要提交的内容比较多，塞进 URL 会又长又难读，所以放在 body 里。""",
                "syntax": """**API 说明（路径与参数分工）**

```
GET    /v1/tasks?done=false&page=2&size=20     # 列表：筛选 + 分页
GET    /v1/tasks/42                            # 单体
POST   /v1/tasks                               # 新建，body 带字段
PATCH  /v1/tasks/42                            # 局部更新
DELETE /v1/tasks/42                            # 删除
GET    /v1/users/7/tasks                       # 从属资源
```

**统一错误结构**

```json
{"detail": "任务不存在", "code": "TASK_NOT_FOUND"}
```

要点：路径里只出现名词与 ID；分页参数用 `page/size` 或 `limit/offset`，全站统一一套。""",
                "example_code": '''import json

# 用数据描述一份接口契约，再检查路径设计是否合规
ENDPOINTS = [
    {"method": "GET", "path": "/v1/tasks", "query": ["done", "page", "size"]},
    {"method": "GET", "path": "/v1/tasks/42", "query": []},
    {"method": "POST", "path": "/v1/tasks", "query": []},
    {"method": "PATCH", "path": "/v1/tasks/42", "query": []},
    {"method": "DELETE", "path": "/v1/tasks/42", "query": []},
    {"method": "GET", "path": "/v1/users/7/tasks", "query": ["page"]},
]

BAD_PATHS = ["/getTaskList", "/deleteTask/42", "/task_list"]

VERBS = ("get", "create", "update", "delete", "list", "add", "remove")


def check(path: str) -> list[str]:
    problems = []
    if any(word in path.lower() for word in VERBS):
        problems.append("路径里出现了动作词")
    if "_" in path:
        problems.append("路径用了下划线，建议用连字符")
    return problems


for item in ENDPOINTS:
    query = "&".join(item["query"]) or "-"
    print(f'{item["method"]:<6} {item["path"]:<20} query={query}')

print("---- 不合规示例 ----")
for path in BAD_PATHS:
    print(path, "->", check(path))

print("---- 统一错误结构 ----")
print(json.dumps({"detail": "任务不存在", "code": "TASK_NOT_FOUND"}, ensure_ascii=False))''',
                "code_lines": """1. `ENDPOINTS` 用列表描述接口清单，这是写代码前先对齐契约的最小形式。
2. 每个元素包含方法、路径、查询参数三部分，正好对应「参数放哪里」的分工。
3. `query` 里有 `done/page/size` 说明筛选与分页走查询串，不进路径。
4. `BAD_PATHS` 收集三种常见坏设计：动作式、下划线式、复数混乱。
5. `VERBS` 是动作词表，用 `in path.lower()` 判断路径里是否混入动作。
6. `check()` 返回问题列表——返回列表而不是布尔值，才能一次列出全部问题。
7. 打印时用 `:<6` / `:<20` 对齐列宽，让清单可读。
8. 最后打印统一错误结构，说明错误响应也要有稳定字段。""",
                "output": """GET    /v1/tasks             query=done&page&size
GET    /v1/tasks/42          query=-
POST   /v1/tasks             query=-
PATCH  /v1/tasks/42          query=-
DELETE /v1/tasks/42          query=-
GET    /v1/users/7/tasks     query=page
---- 不合规示例 ----
/getTaskList -> ['路径里出现了动作词']
/deleteTask/42 -> ['路径里出现了动作词']
/task_list -> ['路径用了下划线，建议用连字符']
---- 统一错误结构 ----
{"detail": "任务不存在", "code": "TASK_NOT_FOUND"}

# 真实接口的请求与响应
curl "http://127.0.0.1:8000/v1/tasks?done=false&page=1&size=20"
{"items":[{"id":1,"title":"写周报","done":false}],"total":1,"page":1,"size":20}

curl http://127.0.0.1:8000/v1/tasks/999
HTTP/1.1 404 Not Found
{"detail":"任务不存在","code":"TASK_NOT_FOUND"}""",
                "mistakes": """- 用动作起名：`/getTasks`、`/createTask`，动词与 HTTP 方法重复。
- 层级过深：`/v1/users/7/projects/3/tasks/42/comments/9`，改一次要动一串。
- 分页参数各接口不一致，有的 `page`，有的 `offset`，前端要写两套。
- 错误响应有的返回字符串、有的返回对象，前端得靠猜。
- 把敏感字段（如 `password`）直接放进响应体。""",
                "error_analysis": """`404 Not Found` 但路径看着没错
—— 多半是末尾多了斜杠或少了 `/v1` 前缀。对比 `openapi.json` 里登记的路径最准。

`{"detail":"Not Found"}` 与自定义错误结构不一致
—— 说明这个 404 是框架抛的，没走你的异常处理器。统一异常处理见第 9 章。

列表接口返回全部数据导致超时
—— 契约里没定分页。先加 `page/size` 默认值，再给 `total` 让前端能算总页数。""",
                "beginner_practice": """1. 为「标签」资源写出 5 个端点的路径与方法（列表、单体、新建、改名、删除）。
2. 把 `/getTaskList` 改成合规路径，并说明方法应该是什么。""",
                "advanced_practice": """设计「任务评论」的接口契约：路径层级、分页方式、错误结构各写清楚；
再说明当评论量很大时，为什么列表接口更适合用游标分页而不是 `page/size`。""",
                "quiz_note": "本节 6 道题：2 道基础理解（参数放哪里、路径命名）+ 2 道代码阅读（读契约检查函数）+ 2 道应用练习（改坏路径、设计分页）。",
                "summary": """路径用名词复数表达资源，方法表达动作；从属资源用嵌套路径。
定位用路径参数、筛选用查询参数、提交用请求体，三者不要混。
错误响应要有稳定结构，分页参数全站统一一套。""",
                "next_lesson": "下一节开始装环境：建虚拟环境、装 FastAPI 与 uvicorn，把第一个接口跑起来。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-01-02",
                        "name": "REST 资源设计与 JSON 契约",
                        "goal": "能按资源设计路径，并为列表接口定出分页、筛选与错误结构。",
                        "minutes": 30,
                        "criteria": "能给出一组不含动作词的路径，并说明每个参数该放路径、查询串还是请求体。",
                        "requires": [],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-01-02-1",
                        "kp": 0,
                        "title": "把动作式接口改成资源式",
                        "description": "把 `/getTaskList`、`/createTask`、`/updateTaskStatus`、`/deleteTask/42` 四个路径改写成 REST 风格，并写出各自的方法与成功状态码。",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''GET    /v1/tasks                 200   列表
POST   /v1/tasks                 201   新建
PATCH  /v1/tasks/42              200   局部更新（含状态）
DELETE /v1/tasks/42              204   删除''',
                        "explanation": "改写要点：去掉动作词，资源用复数名词，动作交给 HTTP 方法；状态变更用 PATCH 而不是新路径。",
                    },
                    {
                        "code": "fa-ex-01-02-2",
                        "kp": 0,
                        "title": "给列表接口补分页契约",
                        "description": "为 `GET /v1/tasks` 设计分页与筛选参数，写出参数名、类型、默认值与响应体的分页字段，并说明非法参数该返回什么。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''参数：done: bool | None = None，page: int = 1（>=1），size: int = 20（1..100）
响应：{"items": [...], "total": 128, "page": 1, "size": 20}
非法参数（size=0 或 page=-1）返回 422，响应体由校验层给出具体字段与原因。''',
                        "explanation": "分页三件套 items/total/page/size 足够前端算页数；参数范围要显式约束，否则会出现 size=100000 拖垮数据库。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-01-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "「查询第 2 页、只看未完成的任务」，这两个条件应该放在哪里？",
                        "options": [
                            ("A", "都放路径：`/tasks/2/false`"),
                            ("B", "都放查询参数：`/tasks?page=2&done=false`"),
                            ("C", "都放请求体"),
                            ("D", "page 放路径，done 放请求体"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "筛选与分页不改变资源身份，属于「同一集合的不同视图」，应放查询参数；GET 请求通常不带请求体。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-01-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列路径设计中，符合 REST 风格的是？（多选）",
                        "options": [
                            ("A", "GET /v1/tasks"),
                            ("B", "POST /v1/tasks/42/complete"),
                            ("C", "DELETE /v1/tasks/42"),
                            ("D", "GET /v1/users/7/tasks"),
                        ],
                        "answer": {"values": ["A", "C", "D"]},
                        "explanation": "B 用路径表达动作，应改为 `PATCH /v1/tasks/42` 并在请求体里带 `{\"done\": true}`。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-01-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`check(\"/task_list\")` 返回什么？",
                        "options": [
                            ("A", "空列表"),
                            ("B", "['路径用了下划线，建议用连字符']"),
                            ("C", "['路径里出现了动作词']"),
                            ("D", "抛出异常"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`/task_list` 没有动作词，但包含下划线，所以只命中第二条规则。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-01-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "列表接口只要返回 `items` 就够，`total` 可有可无。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "缺 `total` 前端无法判断还有没有下一页，只能靠「返回条数少于 size」推测，最后一页边界容易出错。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-01-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全检查函数：当路径里出现动作词时追加一条问题描述。横线处应填什么？\n\n```python\ndef check(path):\n    problems = []\n    if ____:\n        problems.append(\"路径里出现了动作词\")\n    return problems\n```",
                        "options": [
                            ("A", "any(word in path.lower() for word in VERBS)"),
                            ("B", "path in VERBS"),
                            ("C", "VERBS in path"),
                            ("D", "any(path.lower() for word in VERBS)"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "要判断「任意一个动作词出现在路径中」，用 `any(... for ...)`；`path in VERBS` 判断整个路径是否等于某个词，`VERBS in path` 类型不匹配。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-01-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "评论量到千万级时，为什么 `page/size` 分页会变慢？给出替代方案。",
                        "answer": {"value": "`page/size` 用 OFFSET 跳过前 N 行，越往后扫的行越多，深分页会全表扫描。替代方案是游标分页：用上一页最后一条的排序键（如 id 或 created_at）作为 `cursor`，查询条件变成 `WHERE id < cursor ORDER BY id DESC LIMIT size`，复杂度与页码无关。"},
                        "explanation": "要点是「OFFSET 越深越慢」与「游标分页依赖稳定排序键」两句话，能说出 id/时间戳作游标即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "fastapi-backend-02",
        "title": "FastAPI 安装与项目启动",
        "description": "从零装好依赖，把第一个接口跑起来并看懂自动文档。",
        "order_index": 2,
        "lessons": [
            {
                "code": "fastapi-backend-02-lesson-01",
                "objectives": """1. 能在虚拟环境里装好 FastAPI 与 uvicorn，并说清两者分工；
2. 能写出最小应用并用 uvicorn 启动；
3. 能打开 /docs、/redoc 与 /openapi.json 并读懂它们的关系；
4. 能定位三种最常见的启动失败。""",
                "why_learn": """很多人卡在第一步：装完包却起不来服务，或者起来了打不开文档。搞清楚「FastAPI 是框架、uvicorn 是服务器」这件事，后面的调试会顺很多——报错到底来自代码、依赖还是进程，一眼能分清。""",
                "concepts": """**ASGI**：异步 Web 服务器与应用的接口标准，FastAPI 应用是一个 ASGI 应用。
**uvicorn**：ASGI 服务器，负责监听端口、解析 HTTP、把请求交给应用。
**虚拟环境**：项目独立的依赖目录，避免不同项目的版本互相污染。
**自动文档**：FastAPI 依据类型注解生成 OpenAPI 描述，再渲染成 /docs（Swagger UI）与 /redoc。
**热重载**：`--reload` 监听文件变化自动重启，只用于开发。""",
                "plain": """FastAPI 像一份写好的菜谱，uvicorn 像灶台和传菜口。
菜谱本身不会做菜，得有灶台把订单传进来、把做好的菜送出去。
虚拟环境像给这个项目单独配一套厨具，别人家的锅不会混进来。
/docs 是自动生成的菜单：你把「要什么参数、返回什么」写清楚，它就画出一份可以点着试的菜单。""",
                "syntax": """**API 说明**

```python
from fastapi import FastAPI

app = FastAPI(title="任务管理 API", version="1.0.0")
```

- `FastAPI(...)` 的常用参数：`title`（文档标题）、`version`（版本号）、`description`（简介）、`docs_url`（文档路径，设为 None 可关闭）。
- 启动命令：`uvicorn main:app --reload`（`main` 是文件名，`app` 是应用变量）。
- 启动命令参数：

| 参数 | 作用 |
| --- | --- |
| `main:app` | 模块名:应用变量名 |
| `--reload` | 开发时热重载 |
| `--host 0.0.0.0` | 允许外部访问 |
| `--port 8000` | 指定端口 |

访问 `/docs`（可交互）、`/redoc`（纯文档）、`/openapi.json`（机器可读描述）。""",
                "example_code": '''from fastapi import FastAPI

app = FastAPI(title="任务管理 API", version="1.0.0", description="小码教学示例")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def read_root() -> dict:
    return {"message": "任务管理 API", "docs": "/docs"}''',
                "code_lines": """1. `from fastapi import FastAPI` 导入框架主类，整个应用只实例化一次。
2. `app = FastAPI(...)` 创建应用对象；`title/version/description` 会直接显示在文档页顶部。
3. `@app.get("/health")` 是装饰器：把下面的函数注册为「GET /health」的处理函数。
4. `def health() -> dict` 用普通函数即可，返回字典会被自动序列化成 JSON。
5. 返回值里的 `status` 字段是健康检查约定，容器与负载均衡会轮询这个接口。
6. 第二个路由用 `/` 返回文档地址，方便本地启动后直接找到入口。""",
                "output": """# 启动
$ uvicorn main:app --reload
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [27364] using WatchFiles
INFO:     Application startup complete.

# 请求与响应
curl http://127.0.0.1:8000/health
{"status":"ok"}

curl http://127.0.0.1:8000/
{"message":"任务管理 API","docs":"/docs"}

# 自动文档
GET /docs        -> 可交互的 Swagger UI，能直接点 Try it out
GET /openapi.json -> {"openapi":"3.1.0","info":{"title":"任务管理 API","version":"1.0.0"},"paths":{...}}""",
                "mistakes": """- 在项目根目录之外启动 uvicorn，报 `Could not import module "main"`。
- 没激活虚拟环境就启动，报 `ModuleNotFoundError: No module named 'fastapi'`。
- 生产环境也带 `--reload`，多进程下反复重启且更耗内存。
- 改了代码没重启也没开 reload，误以为接口没生效。
- 把应用变量改名成 `api` 却仍用 `main:app` 启动。""",
                "error_analysis": """`ModuleNotFoundError: No module named 'fastapi'`
—— 依赖装在别的环境里。先 `where python` 确认当前解释器，再在虚拟环境里 `pip install fastapi uvicorn`。

`ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`
—— 端口被占用。换 `--port 8001`，或找到占用进程结束它。

`ERROR: Error loading ASGI app. Could not import module "main".`
—— 模块名与文件名不一致，或不在同一目录。确认文件叫 `main.py`、变量叫 `app`。""",
                "beginner_practice": """1. 把应用标题改成「任务管理 API（练习版）」，启动后在 /docs 顶部确认已生效。
2. 新增 `GET /version` 接口，返回 `{"version": "1.0.0"}`。""",
                "advanced_practice": """用 `--reload` 与不带 `--reload` 各启动一次，修改一行返回值并观察行为差异；
再说明为什么生产环境推荐「多进程 + 反向代理」而不是热重载。""",
                "quiz_note": "本节 6 道题：2 道基础理解（框架与服务器分工、文档路径）+ 2 道代码阅读（读最小应用）+ 2 道应用练习（补路由、排查启动失败）。",
                "summary": """FastAPI 是应用框架，uvicorn 是运行它的 ASGI 服务器，两者缺一不可。
应用只需实例化一次，路由用装饰器注册，返回字典自动变 JSON。
/docs、/redoc、/openapi.json 都来自同一份 OpenAPI 描述，改代码即改文档。""",
                "next_lesson": "下一节讲路由与路径参数：URL 里的 42 怎么变成函数里带类型的参数。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-02-01",
                        "name": "FastAPI 应用与 uvicorn 启动",
                        "goal": "能独立装好环境、启动服务并读懂自动文档。",
                        "minutes": 40,
                        "criteria": "能从零启动一个带两个接口的服务，并说出 /docs 与 openapi.json 的关系。",
                        "requires": [],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-02-01-1",
                        "kp": 0,
                        "title": "最小应用三件套",
                        "description": "写一个 main.py：含 /health、/version、/ 三个接口，启动后逐个用 curl 验证并截图 /docs 顶部标题。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''from fastapi import FastAPI

app = FastAPI(title="任务管理 API（练习版）", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict:
    return {"version": "1.0.0"}


@app.get("/")
def root() -> dict:
    return {"docs": "/docs"}''',
                        "explanation": "三个接口都用 GET，返回值都是字典；验证时注意 /docs 顶部标题应与 FastAPI(title=...) 一致。",
                    },
                    {
                        "code": "fa-ex-02-01-2",
                        "kp": 0,
                        "title": "三种启动失败排查",
                        "description": "分别制造「端口占用」「模块找不到」「变量名不对」三种失败，记录报错原文并写出定位方法。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''端口占用：Errno 10048 → 换端口或结束占用进程。
模块找不到：Could not import module "main" → 确认工作目录与文件名、变量名。
依赖缺失：ModuleNotFoundError: No module named 'fastapi' → 确认解释器与虚拟环境。
定位顺序：先看报错类型，再看当前目录，最后确认 pip 装在哪。''',
                        "explanation": "三种错误分属「进程/路径/依赖」三类，按这个顺序排查能覆盖大部分启动问题。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-02-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`uvicorn main:app --reload` 中 `main:app` 的含义是？",
                        "options": [
                            ("A", "文件 main.py 里的 app 变量"),
                            ("B", "包 main 里的 app 模块"),
                            ("C", "函数 main 的参数 app"),
                            ("D", "端口 8000 的别名"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "格式固定为「模块路径:应用实例名」，模块路径由文件名（不含 .py）决定。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-02-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列关于 FastAPI 与 uvicorn 的说法，正确的是？（多选）",
                        "options": [
                            ("A", "FastAPI 应用是 ASGI 应用"),
                            ("B", "uvicorn 负责监听端口与解析 HTTP"),
                            ("C", "FastAPI 自带生产级多进程管理"),
                            ("D", "--reload 适合开发，不适合生产"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "多进程管理要靠 gunicorn/多 worker 或容器编排，FastAPI 本身不提供进程管理。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-02-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "访问 `/health` 得到的响应体是？",
                        "options": [
                            ("A", '{"status":"ok"}'),
                            ("B", '{"health":"ok"}'),
                            ("C", "ok"),
                            ("D", "204 无内容"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "函数返回字典 `{\"status\": \"ok\"}`，FastAPI 自动序列化为等价的 JSON。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-02-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把 `FastAPI(title=...)` 里的 title 改掉后，必须手动修改 openapi.json 文件。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "openapi.json 是运行时根据代码生成的，没有实体文件需要手工维护。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-02-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全一个返回版本号的接口，使 /docs 中出现该路由。横线处应填什么？\n\n```python\n____\ndef version() -> dict:\n    return {\"version\": \"1.0.0\"}\n```",
                        "options": [
                            ("A", '@app.get("/version")'),
                            ("B", '@app.route("/version")'),
                            ("C", 'app.get("/version")'),
                            ("D", '@app.GET("/version")'),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "FastAPI 用方法名小写的装饰器，且必须带 @ 才能完成注册；`route` 与全大写 `GET` 都不是 FastAPI 的写法。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-02-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "同事说「代码改了但接口没变」，请给出三条排查方向并说明依据。",
                        "answer": {"value": "① 是否开了 --reload：没开则进程还在跑旧代码，需手动重启；② 是否启动了多个进程或旧进程未退出，请求被旧进程处理；③ 是否改错了文件（例如改的是副本或另一个目录下的同名文件），可用 /docs 里的路由列表与代码比对。"},
                        "explanation": "三条分别对应「重载机制」「进程状态」「文件定位」，是最常见的三类原因。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
