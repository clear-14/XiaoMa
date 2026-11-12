"""FastAPI 后端开发：第 5—6 章（HTTP 方法与请求响应体、Pydantic 模型与数据校验）。"""

CHAPTERS: list[dict] = [
    {
        "code": "fastapi-backend-05",
        "title": "HTTP 方法与请求响应体",
        "description": "五种方法各司其职，请求体与响应体各管一头。",
        "order_index": 5,
        "lessons": [
            {
                "code": "fastapi-backend-05-lesson-01",
                "objectives": """1. 能用同一个路径配合五种方法实现完整的增删改查；
2. 能正确设置 201/204 等成功状态码；
3. 理解幂等与「重复提交」在代码里的表现；
4. 会用 `HTTPException` 表达 404/409 等业务错误。""",
                "why_learn": """同一个 `/tasks/{task_id}`，GET 是查询、PUT 是整体替换、PATCH 是局部修改、DELETE 是删除。
方法用错，缓存、重试、网关行为都会跟着错。状态码设错，前端只能靠猜字段判断成败。""",
                "concepts": """**方法即语义**：路径标识资源，方法标识动作。
**PUT 与 PATCH**：PUT 要求提交完整字段并整体替换；PATCH 只提交要改的字段。
**状态码声明**：装饰器 `status_code=` 决定成功响应的默认码。
**HTTPException**：抛出让框架生成标准错误响应，含状态码与 `detail`。
**幂等落地**：PUT/DELETE 重复调用结果一致，第二次 DELETE 返回 404 也算幂等。""",
                "plain": """把 `/tasks/42` 想成一个抽屉：GET 是打开看看，PUT 是把抽屉里的东西全部换成新的，PATCH 是只换其中一件，DELETE 是清空。
方法就是你对抽屉做的动作，动作用错，别人后续要「重复确认一次」时就可能把东西换两遍。
状态码是你的回执：换好了写「已完成」，本来就是空的写「没这东西」，别一律写「一切正常」。""",
                "syntax": """**API 说明**

```python
@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(...): ...

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(...) -> None: ...

raise HTTPException(status_code=404, detail="任务不存在")
```

- `status.HTTP_201_CREATED` 比裸写 201 可读。
- 204 表示无响应体，函数应返回 `None`。
- `HTTPException` 的 `detail` 会放进 `{"detail": ...}`。""",
                "example_code": '''from fastapi import FastAPI, HTTPException, status

app = FastAPI(title="方法语义示例")

TASKS: dict[int, dict] = {1: {"id": 1, "title": "写周报", "done": False}}


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict:
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TASKS[task_id]


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: dict) -> dict:
    new_id = max(TASKS) + 1 if TASKS else 1
    TASKS[new_id] = {"id": new_id, "title": payload.get("title", ""), "done": False}
    return TASKS[new_id]


@app.put("/tasks/{task_id}")
def replace_task(task_id: int, payload: dict) -> dict:
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="任务不存在")
    TASKS[task_id] = {"id": task_id, "title": payload["title"], "done": payload["done"]}
    return TASKS[task_id]


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: dict) -> dict:
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.update(payload)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int) -> None:
    if TASKS.pop(task_id, None) is None:
        raise HTTPException(status_code=404, detail="任务不存在")''',
                "code_lines": """1. 五个函数共用同一组路径，靠装饰器的方法区分行为，这是 REST 的核心写法。
2. `status_code=status.HTTP_201_CREATED` 让新建成功返回 201 而不是 200。
3. `raise HTTPException(404, ...)` 让「不存在」有统一响应体，不用手写 Response。
4. PUT 里直接取 `payload["title"]`：整体替换要求字段齐全，缺了就报 500 以外的错（正常应由模型校验拦住）。
5. PATCH 用 `task.update(payload)` 只覆盖传入字段，未传的保持原值。
6. `TASKS.pop(task_id, None)` 给了默认值，删不存在的返回 None，据此判断 404。
7. DELETE 声明 204 且函数返回 `None`，响应不带 body，符合规范。""",
                "output": """curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":"交报表"}'
HTTP/1.1 201 Created
{"id":2,"title":"交报表","done":false}

curl -X PATCH http://127.0.0.1:8000/tasks/2 -d '{"done":true}' -H "Content-Type: application/json"
{"id":2,"title":"交报表","done":true}

curl -X PUT http://127.0.0.1:8000/tasks/2 -d '{"title":"交月报","done":true}' -H "Content-Type: application/json"
{"id":2,"title":"交月报","done":true}

curl -i -X DELETE http://127.0.0.1:8000/tasks/2
HTTP/1.1 204 No Content

curl -i http://127.0.0.1:8000/tasks/2
HTTP/1.1 404 Not Found
{"detail":"任务不存在"}""",
                "mistakes": """- 用 POST 做「更新」，导致同一操作重复执行产生多条记录。
- DELETE 返回 200 并附一段说明，前端还得解析 body 才知道成败。
- PUT 却只要求传部分字段，语义变成 PATCH，调用方无法判断「没传」是「清空」还是「不改」。
- 用 `dict` 直接收请求体，字段拼错也不报错（应改用模型，见下一节）。
- 抛 `HTTPException` 时把内部异常信息原样返回，泄漏实现细节。""",
                "error_analysis": """`500 KeyError: 'title'`
—— PUT 请求体缺字段。用 Pydantic 模型声明必填字段，让框架返回 422 而不是 500。

`{"detail":"Method Not Allowed"}`（405）
—— 路径对但方法没注册。检查装饰器是 `@app.put` 还是 `@app.patch`。

`204` 响应却带着 body
—— 函数里 return 了内容。204 必须返回 None。""",
                "beginner_practice": """1. 给 `POST /tasks` 增加「标题重复则返回 409」的判断。
2. 把 PUT 换成「字段缺失时报 422」的实现（提示：用 Pydantic 模型）。""",
                "advanced_practice": """实现「标记完成」的两种写法：`PATCH /tasks/{id}` 传 `{"done": true}` 与
`POST /tasks/{id}/complete`，对比二者在幂等、缓存、文档可读性上的差异，并给出你的选择与理由。""",
                "quiz_note": "本节 6 道题：2 道基础理解（方法语义、状态码）+ 2 道代码阅读（读 PUT/PATCH 差异、读 204）+ 2 道应用练习（补 409、改状态码）。",
                "summary": """路径标识资源，方法标识动作；五个方法配合构成完整 CRUD。
201 表示创建成功、204 表示成功无响应体，二者都不该用 200 代替。
PUT 整体替换、PATCH 局部更新，语义差别要在文档里写清。""",
                "next_lesson": "下一节用 Pydantic 模型约束请求体与响应体，把「字段拼错」这类问题挡在入口。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-05-01",
                        "name": "HTTP 方法语义与状态码实现",
                        "goal": "能用五种方法实现 CRUD，并为每种操作选对状态码。",
                        "minutes": 35,
                        "criteria": "能写出 201/204/404 都正确的五个接口，并解释 PUT 与 PATCH 的区别。",
                        "requires": ["fastapi-backend-04-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-05-01-1",
                        "kp": 0,
                        "title": "补一个 409 冲突",
                        'description': '给 `POST /tasks` 加判断：标题已存在时返回 409 与 `{"detail": "任务标题已存在"}`。',
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: dict) -> dict:
    title = payload.get("title", "")
    if any(task["title"] == title for task in TASKS.values()):
        raise HTTPException(status_code=409, detail="任务标题已存在")
    new_id = max(TASKS) + 1 if TASKS else 1
    TASKS[new_id] = {"id": new_id, "title": title, "done": False}
    return TASKS[new_id]''',
                        "explanation": "409 Conflict 用于「请求本身合法但与现有状态冲突」，比 400 更精确。",
                    },
                    {
                        "code": "fa-ex-05-01-2",
                        "kp": 0,
                        "title": "PUT 与 PATCH 的行为对比",
                        "description": "对同一个任务先后发 PUT（只传 title）与 PATCH（只传 title），记录响应差异并解释原因。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''PUT 只传 title 会导致 done 丢失（示例里直接取 payload["done"]，缺字段会报错）。
PATCH 只传 title 时 done 保持原值，因为 update 只覆盖传入键。
结论：PUT 要求调用方提供完整表示，PATCH 允许部分更新。''',
                        "explanation": "这正是不该用 dict 收请求体的原因——用模型能把「必填」写在契约里。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-05-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`@app.delete(..., status_code=204)` 的处理函数应该返回什么？",
                        "options": [("A", '{"deleted": true}'), ("B", "None"), ("C", "被删除的对象"), ("D", "任意字符串")],
                        "answer": {"value": "B"},
                        "explanation": "204 明确表示无响应体，返回内容会与语义冲突，也可能触发响应长度校验错误。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-05-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列做法正确的是？（多选）",
                        "options": [
                            ("A", "新建成功返回 201"),
                            ("B", "资源不存在返回 404"),
                            ("C", "标题重复返回 200 并在 body 里写错误"),
                            ("D", "删除成功返回 204"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "错误状态用 200 会让前端、监控、网关都无法识别失败，C 是反模式。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-05-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `PATCH /tasks/1` 传 `{\"done\": true}` 后，任务 1 的 `title` 会变成什么？",
                        "options": [("A", "空字符串"), ("B", "仍然是「写周报」"), ("C", "报错"), ("D", "null")],
                        "answer": {"value": "B"},
                        "explanation": "`task.update(payload)` 只覆盖 `done` 键，`title` 保持原值。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-05-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "第二次 DELETE 同一个任务返回 404，说明 DELETE 不是幂等方法。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "幂等看的是服务端状态是否一致，两次调用后资源都不存在，因此仍然幂等。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-05-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全装饰器，使新建成功返回 201。横线处应填什么？\n\n```python\n@app.post(\"/tasks\", ____)\ndef create_task(...): ...\n```",
                        "options": [
                            ("A", "status_code=status.HTTP_201_CREATED"),
                            ("B", "status=201"),
                            ("C", "code=201"),
                            ("D", "response_status=201"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "参数名是 `status_code`，FastAPI 没有 `status`/`code` 这类装饰器参数。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-05-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么用 `dict` 接收请求体是坏习惯？至少给出两条后果。",
                        "answer": {"value": "① 没有字段校验：拼错、缺字段都不报 422，直到业务代码抛 KeyError 变成 500；② 没有文档：/docs 里请求体只有「任意对象」，调用方无法知道该传什么；③ 无法限制多余字段与类型（如把 done 传成字符串 \"false\" 会被当成真值）。"},
                        "explanation": "答案要落在「校验、文档、类型」三点上，任两条即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-05-lesson-02",
                "objectives": """1. 会用 `BaseModel` 定义请求体与响应体；
2. 能用 `response_model` 控制出参字段，避免泄漏内部数据；
3. 能区分入参模型与出参模型，理解为什么不共用一个类；
4. 会用 `status_code` 与 `response_model` 组合出规范接口。""",
                "why_learn": """用 `dict` 收请求体的问题在上一节已经看到：字段拼错要到运行时才炸。
出参更危险——直接把 ORM 对象或内部字典返回，密码哈希、内部备注、软删除标记全都会漏出去。""",
                "concepts": """**请求体模型**：函数参数标注为 `BaseModel` 子类，FastAPI 自动从 JSON body 解析。
**响应模型**：`response_model=TaskOut` 按出参模型过滤字段并生成文档。
**入出分离**：`TaskCreate`（可含密码）与 `TaskOut`（绝不含密码）应是两个模型。
**嵌套与列表**：`response_model=list[TaskOut]` 表示数组响应。
**状态码组合**：新建用 `201` + `response_model`，语义与结构都明确。""",
                "plain": """请求体模型像入职登记表：栏目固定，填错、漏填都会被退回重填。
响应模型像对外发布的通知：只用登记表里的部分信息，身份证号这类内部信息不会出现在通知上。
两者分开，等于「收得严、给得少」——这正是接口该有的姿势。""",
                "syntax": """**API 说明**

```python
class TaskCreate(BaseModel):
    title: str
    done: bool = False

class TaskOut(BaseModel):
    id: int
    title: str
    done: bool

@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate) -> TaskOut: ...
```

- 参数标注模型 → 从请求体解析；`response_model` 只影响输出与文档。
- 函数可返回 ORM 对象或字典，`response_model` 会按声明裁剪。
- 列表响应用 `response_model=list[TaskOut]`。""",
                "example_code": '''from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="请求响应体示例")

TASKS: dict[int, dict] = {1: {"id": 1, "title": "写周报", "done": False, "owner_id": 7}}


class TaskCreate(BaseModel):
    title: str
    done: bool = False


class TaskOut(BaseModel):
    id: int
    title: str
    done: bool


@app.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> dict:
    new_id = max(TASKS) + 1 if TASKS else 1
    TASKS[new_id] = {"id": new_id, "title": payload.title, "done": payload.done, "owner_id": 7}
    return TASKS[new_id]


@app.get("/tasks", response_model=list[TaskOut])
def list_tasks() -> list[dict]:
    return list(TASKS.values())''',
                "code_lines": """1. `TaskCreate` 只声明可写字段，`id` 由服务端生成，不出现在请求体里。
2. `done: bool = False` 给默认值，调用方不传就是未完成。
3. `payload: TaskCreate` 让框架把 body 解析成模型对象，字段访问用 `payload.title`。
4. `response_model=TaskOut` 决定输出字段：`owner_id` 被裁掉，不会泄漏给调用方。
5. 函数返回的是内部字典（含 `owner_id`），序列化时按模型过滤——这是「收得严、给得少」。
6. `response_model=list[TaskOut]` 用于列表接口，输出自动变成数组。
7. `status.HTTP_201_CREATED` 与 `response_model` 同时声明，语义与结构都不含糊。""",
                "output": """curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":"交报表"}'
HTTP/1.1 201 Created
{"id":2,"title":"交报表","done":false}

# owner_id 被 response_model 过滤掉
curl http://127.0.0.1:8000/tasks
[{"id":1,"title":"写周报","done":false},{"id":2,"title":"交报表","done":false}]

# 字段类型不对
curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":123}'
HTTP/1.1 422 Unprocessable Entity
{"detail":[{"type":"string_type","loc":["body","title"],
"msg":"Input should be a valid string","input":123}]}""",
                "mistakes": """- 入参与出参共用一个模型，导致 `password` 或内部字段被返回。
- 没写 `response_model`，返回 ORM 对象时把全部列都暴露出去。
- 在响应模型里加 `id: int` 却在创建时还没生成 id，返回 None 触发校验错。
- 列表接口用单个模型，前端拿到数组却按对象解析。
- 以为 `response_model` 会改变函数返回值类型（其实只是序列化时的裁剪与文档声明）。""",
                "error_analysis": """`ResponseValidationError: Input should be a valid integer`
—— 返回的对象字段类型与 `response_model` 不符（常见是 id 还是 None 或字符串）。

`422 string_type` 出现在 `body.title`
—— 请求体字段类型错误。按 `detail` 里的 `loc` 定位到具体字段。

返回结果少了字段
—— 多半是 `response_model` 没声明该字段，或模型里漏写。""",
                "beginner_practice": """1. 给 `TaskCreate` 加 `priority: int = 1`，并确认它出现在 /docs 的请求体示例里。
2. 故意把 `title` 传成数字，记录 422 的完整结构。""",
                "advanced_practice": """设计「用户」的入参与出参模型：注册时收密码，查询时绝不能返回密码哈希。
写出两个模型并说明除了 `response_model` 之外，还需要哪些手段（如日志脱敏、审计）保证不泄漏。""",
                "quiz_note": "本节 6 道题：2 道基础理解（入出分离、response_model 作用）+ 2 道代码阅读（读字段过滤、读 422）+ 2 道应用练习（补模型、改列表响应）。",
                "summary": """请求体用 `BaseModel` 声明，字段类型与必填性即契约。
`response_model` 决定输出字段，能把内部字段裁掉，也是文档来源。
入参与出参必须是两个模型：收得严、给得少。""",
                "next_lesson": "下一节深入 Pydantic：用 Field 加约束、用别名兼容前端命名、用校验器表达业务规则。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-05-02",
                        "name": "请求体与响应体模型",
                        "goal": "能用入参/出参模型控制请求字段与响应字段。",
                        "minutes": 40,
                        "criteria": "能写出创建接口的入参与出参模型，并解释 response_model 的裁剪行为。",
                        "requires": ["fastapi-backend-05-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-05-02-1",
                        "kp": 0,
                        "title": "入出分离的用户模型",
                        "description": "写 `UserCreate`（含 password）与 `UserOut`（含 id、email，不含 password），并给出注册接口。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''class UserCreate(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str


@app.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate) -> dict:
    return {"id": 1, "email": payload.email, "password": "hashed-in-db"}''',
                        "explanation": "即使函数返回里带了 password，`response_model=UserOut` 也会把它裁掉——但正解是不返回它。",
                    },
                    {
                        "code": "fa-ex-05-02-2",
                        "kp": 0,
                        "title": "列表响应模型",
                        "description": "把列表接口改成返回 `list[TaskOut]`，并说明如果误写成 `TaskOut` 会发生什么。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''写成 list[TaskOut] 时输出为 JSON 数组。
误写成 TaskOut 会触发 ResponseValidationError：输入是列表，但模型期望对象。''',
                        "explanation": "响应模型也是校验器，声明错了会在序列化阶段直接报错，而不是悄悄输出错误结构。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-05-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`response_model` 的主要作用是？",
                        "options": [
                            ("A", "校验并裁剪响应字段，同时生成文档"),
                            ("B", "校验请求体"),
                            ("C", "设置状态码"),
                            ("D", "加密响应内容"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "请求体由参数注解决定，状态码由 `status_code` 决定，`response_model` 只管输出。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-05-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "为什么入参模型与出参模型要分开？（多选）",
                        "options": [
                            ("A", "出参不应包含密码等敏感字段"),
                            ("B", "入参可写字段与出参可读字段本来就不同"),
                            ("C", "分开后 /docs 更清晰"),
                            ("D", "Pydantic 不允许同一个类被复用两次"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "Pydantic 完全允许复用，D 是错的；分开是设计与安全的需要。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-05-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`GET /tasks` 的响应里为什么不包含 `owner_id`？",
                        "options": [
                            ("A", "函数没返回该字段"),
                            ("B", "`response_model=TaskOut` 没有声明该字段，序列化时被裁掉"),
                            ("C", "owner_id 是私有字段"),
                            ("D", "JSON 不支持整数字段"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "内部字典里有 `owner_id`，但出参模型没声明它，输出阶段被过滤。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-05-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只在 `TaskCreate` 里声明 `id`，就能让调用方自定义新建任务的 ID。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "`TaskCreate` 没声明 `id` 就收不到该字段；即使声明了，让客户端决定主键也会带来冲突与越权风险。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-05-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全装饰器，使响应按 `TaskOut` 裁剪且成功码为 201。横线处应填什么？\n\n```python\n@app.post(\"/tasks\", ____)\ndef create_task(payload: TaskCreate): ...\n```",
                        "options": [
                            ("A", "response_model=TaskOut, status_code=201"),
                            ("B", "model=TaskOut, status=201"),
                            ("C", "response_model=TaskOut, code=201"),
                            ("D", "responses=TaskOut"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "两个参数名分别是 `response_model` 与 `status_code`。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-05-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "接口返回了 `password_hash` 字段，除了加 `response_model`，还应从哪几个层面补救？",
                        "answer": {"value": "① 数据层：查询时就不取该列（select 指定列）；② 序列化层：出参模型不声明该字段，必要时 `model_config` 禁止多余字段；③ 日志层：记录响应体时脱敏；④ 测试层：加一条断言「响应体中不含 password」，把约束固化下来。"},
                        "explanation": "四个层面覆盖「不取、不给、不记、不易复发」，只答 response_model 不够。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
