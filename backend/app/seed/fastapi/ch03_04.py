"""FastAPI 后端开发：第 3—4 章（路由与路径参数、查询参数）。"""

CHAPTERS: list[dict] = [
    {
        "code": "fastapi-backend-03",
        "title": "路由与路径参数",
        "description": "让 URL 里的信息变成有类型的函数参数。",
        "order_index": 3,
        "lessons": [
            {
                "code": "fastapi-backend-03-lesson-01",
                "objectives": """1. 会用 `{name}` 声明路径参数，并让它自动转换成目标类型；
2. 能在一个路径里放多个参数，包括嵌套资源；
3. 理解转换失败时框架返回 422 而不是 500；
4. 知道路径参数与查询参数的分工边界。""",
                "why_learn": """路径参数是接口最常见的输入：查任务要任务 ID、查用户任务要用户名加 ID。如果都当字符串处理，函数里就得写一堆 `int()` 和 try/except；FastAPI 让你在签名里标类型，转换和报错都由框架完成。""",
                "concepts": """**路径参数**：URL 中用 `{}` 占位的一段，如 `/tasks/{task_id}`。
**类型转换**：参数标注 `int` 后，框架把字符串 `"42"` 转成整数 `42`。
**校验失败**：转换不了时返回 422，响应体指出哪个字段、什么类型。
**嵌套资源**：`/users/{username}/tasks/{task_id}` 表达从属关系。
**参数顺序**：函数参数顺序无关，框架按名字匹配路径占位符。""",
                "plain": """路径参数像快递单上的单号：位置固定，内容变化。
标了 `int` 就等于告诉框架「这一段必须是数字」，收到 `abc` 时它会直接拦下来并说明原因，而不是让你的函数在中间某行崩掉。
这就像门卫核对证件：不合格的在门口就被拦，不用等进了办公室才发现问题。""",
                "syntax": """**API 说明**

```python
@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict: ...
```

- `{task_id}` 是占位符，函数里同名参数接收它。
- 标注类型后自动转换：`int`、`float`、`str`、`bool`、`UUID`、`datetime` 都可直接用。
- 转换/校验失败 → 422，`detail[0].loc` 指出出错位置，`detail[0].type` 指出期望类型。
- 路径里多段参数按出现顺序匹配，函数参数可用任意顺序声明。""",
                "example_code": '''from fastapi import FastAPI

app = FastAPI(title="路径参数示例")


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict:
    # task_id 已经是 int，不需要再转换
    return {"id": task_id, "next": task_id + 1}


@app.get("/users/{username}/tasks/{task_id}")
def get_user_task(username: str, task_id: int) -> dict:
    return {"username": username, "task_id": task_id, "owner": username}''',
                "code_lines": """1. `{task_id}` 告诉框架这一段是变量，名字必须与函数参数一致。
2. `task_id: int` 让框架完成转换；能直接参与 `+ 1` 运算，说明类型真的变了。
3. 第二个路由演示嵌套资源：用户名与任务 ID 各占一段。
4. 函数参数顺序与路径中的顺序无关，框架按名字绑定。
5. 两个函数都返回字典，自动序列化成 JSON，不需要手工 `json.dumps`。
6. 若访问 `/tasks/abc`，函数根本不会执行——框架在入口就返回 422。""",
                "output": """# 请求与响应
curl http://127.0.0.1:8000/tasks/42
{"id":42,"next":43}

curl http://127.0.0.1:8000/users/lisi/tasks/7
{"username":"lisi","task_id":7,"owner":"lisi"}

# 类型转换失败：函数未执行，直接 422
curl -i http://127.0.0.1:8000/tasks/abc
HTTP/1.1 422 Unprocessable Entity
{"detail":[{"type":"int_parsing","loc":["path","task_id"],
"msg":"Input should be a valid integer, unable to parse string as an integer",
"input":"abc"}]}""",
                "mistakes": """- 用字符串接 ID 再手工转换，重复实现框架已经做好的事。
- 路径占位符名与函数参数名不一致，报 `TypeError: missing 1 required positional argument`。
- 用 `/tasks/{task_id}/` 结尾带斜杠，与不带斜杠视为两个路径。
- 以为 422 是服务器错误，去查服务端日志（其实是客户端传错类型）。
- 在路径里放可变长文本（如整段描述），URL 会超长且难以缓存。""",
                "error_analysis": """`422 int_parsing` —— 路径段不是合法整数。让调用方修正，或把类型改成 `str` 自行解析。

`TypeError: get_task() missing 1 required positional argument: 'task_id'`
—— 路径写的是 `{id}`，函数写的是 `task_id`。两边名字必须一致。

`404 Not Found` 访问 `/tasks/42/`
—— 末尾斜杠被当成不同路径。统一风格，不要混用。""",
                "beginner_practice": """1. 新增 `GET /projects/{project_id}/tasks/{task_id}`，返回两个 ID 组成的字典。
2. 访问 `/projects/abc/tasks/1`，观察 422 里 `loc` 字段指向哪一段。""",
                "advanced_practice": """把 `task_id` 改成 UUID 类型，构造一个合法与一个非法 UUID 分别请求，
对比两次 422 的 `type` 字段差异，并说明为什么接口用 UUID 更利于公开暴露。""",
                "quiz_note": "本节 6 道题：2 道基础理解（类型转换、参数匹配）+ 2 道代码阅读（读路由、读 422）+ 2 道应用练习（补嵌套路径、改 UUID）。",
                "summary": """路径参数用 `{name}` 声明，标上类型后由框架完成转换与校验。
转换失败返回 422，响应体指出位置与期望类型，函数不会执行。
占位符名与函数参数名必须一致；嵌套资源用多段路径表达从属关系。""",
                "next_lesson": "下一节处理路径冲突与取值约束：为什么 `/tasks/latest` 会被 `/tasks/{task_id}` 抢走。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-03-01",
                        "name": "路径参数与类型转换",
                        "goal": "能声明单段与多段路径参数，并正确处理转换失败。",
                        "minutes": 30,
                        "criteria": "能写出嵌套资源路径，并解释 422 与 500 的区别。",
                        "requires": [],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-03-01-1",
                        "kp": 0,
                        "title": "嵌套资源路径",
                        "description": "写两个接口：`/projects/{project_id}/tasks/{task_id}` 与 `/projects/{project_id}`，后者返回该项目下的任务数（用一个字典模拟数据）。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''from fastapi import FastAPI

app = FastAPI()
TASKS = {1: [{"id": 10}, {"id": 11}], 2: []}


@app.get("/projects/{project_id}")
def get_project(project_id: int) -> dict:
    return {"id": project_id, "tasks": len(TASKS.get(project_id, []))}


@app.get("/projects/{project_id}/tasks/{task_id}")
def get_project_task(project_id: int, task_id: int) -> dict:
    return {"project_id": project_id, "task_id": task_id}''',
                        "explanation": "两个参数都标 int；用字典 get 兜底避免 KeyError，接口层不该因为数据缺失抛 500。",
                    },
                    {
                        "code": "fa-ex-03-01-2",
                        "kp": 0,
                        "title": "UUID 路径参数",
                        "description": "把任务 ID 换成 UUID 类型，写出接口，并说明非法 UUID 请求的响应差异。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''from uuid import UUID

@app.get("/tasks/{task_id}")
def get_task(task_id: UUID) -> dict:
    return {"id": str(task_id)}

非法 UUID 返回 422，type 为 uuid_parsing；合法但不存在时由业务返回 404。''',
                        "explanation": "关键区分：格式错是 422（校验层），格式对但查不到是 404（业务层）。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-03-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "访问 `/tasks/abc`（接口声明 `task_id: int`）会得到？",
                        "options": [("A", "200 与字符串 abc"), ("B", "422 参数校验失败"), ("C", "500 服务器错误"), ("D", "404 不存在")],
                        "answer": {"value": "B"},
                        "explanation": "类型转换发生在进入函数之前，失败属于客户端输入问题，返回 422 并说明原因。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-03-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于路径参数，正确的说法有？（多选）",
                        "options": [
                            ("A", "占位符名必须与函数参数名一致"),
                            ("B", "标注类型后框架自动转换"),
                            ("C", "函数参数顺序必须与路径顺序一致"),
                            ("D", "多段参数可写在同一个路径里"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "参数按名字绑定，顺序无所谓，所以 C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-03-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "请求 `/tasks/42` 时示例接口返回的 `next` 值是多少？",
                        "options": [("A", "42"), ("B", "43"), ("C", '"421"'), ("D", "报错")],
                        "answer": {"value": "B"},
                        "explanation": "`task_id` 已被转成 int，`task_id + 1` 得到 43。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-03-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "路径参数声明为 `str` 时，访问 `/tasks/abc` 也会返回 422。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "任何路径段都能当字符串，`str` 类型不会转换失败，因此返回 200。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-03-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全嵌套路径的参数声明，使 `task_id` 为整数。横线处应填什么？\n\n```python\n@app.get(\"/users/{username}/tasks/{task_id}\")\ndef get_user_task(username: str, ____) -> dict: ...\n```",
                        "options": [
                            ("A", "task_id: int"),
                            ("B", "task_id = int"),
                            ("C", "int(task_id)"),
                            ("D", "task_id: \"int\""),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "注解用冒号；`= int` 是默认值写法，`int(task_id)` 不是参数声明。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-03-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么公开接口更愿意用 UUID 而不是自增 ID 做路径参数？",
                        "answer": {"value": "自增 ID 会暴露数据规模（看到 id=1000 就知道有多少条），也容易被顺序遍历枚举；UUID 不可预测、可在客户端或离线生成，合并多库数据时也不会冲突。代价是占用空间更大、索引局部性更差。"},
                        "explanation": "能同时说出「不可枚举」与「可预生成」两项收益，并提一句存储/索引代价即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-03-lesson-02",
                "objectives": """1. 能解释「固定路径被动态路径抢走」的原因并正确排序；
2. 会用 `Enum` 限定路径取值，让文档直接给出可选值；
3. 会用 `Path` 与 `Annotated` 给路径参数加范围约束；
4. 能读懂 422 里枚举与范围校验的报错。""",
                "why_learn": """`/tasks/latest` 写成 404 是新手最常见的坑：路由按声明顺序匹配，先声明的 `{task_id}` 会把 `latest` 当成 ID。
另一类问题更隐蔽——路径参数没有范围约束，`task_id=-1` 一路传到 SQL 才报错。约束应该写在入口。""",
                "concepts": """**匹配顺序**：FastAPI 按注册顺序逐条匹配，先命中的生效。
**固定优先**：把 `/tasks/latest` 这类固定路径写在动态路径之前。
**枚举约束**：`class Status(str, Enum)` 让参数只能取枚举成员，文档自动列出可选值。
**Path 约束**：`Annotated[int, Path(ge=1, le=10000)]` 声明范围并写入 OpenAPI。
**422 结构**：`loc` 指出位置，`ctx` 给出约束值，`type` 说明规则。""",
                "plain": """路由匹配像排队办事：窗口按顺序叫号，第一个能吃下你这张单子的窗口就把你接走。
`{task_id}` 这个窗口「什么都能办」，所以排在它后面的专窗 `/tasks/latest` 永远叫不到人。
把它挪到前面，等于给专窗优先叫号——规则简单，但顺序错了就是 404。""",
                "syntax": """**API 说明**

```python
class TaskStatus(str, Enum):
    todo = "todo"
    done = "done"

@app.get("/tasks/latest")                                   # 固定路径放前面
def latest(): ...

@app.get("/tasks/{task_id}")
def get_task(task_id: Annotated[int, Path(ge=1, le=10000)]): ...

@app.get("/tasks/status/{status}")
def by_status(status: TaskStatus): ...
```

- `Enum` 继承 `str` 让取值直接序列化为字符串。
- `Path(ge=..., le=...)` 的范围会写进 OpenAPI，前端能看到约束。
- 枚举不匹配时 422 的 `ctx.expected` 会列出全部合法值。""",
                "example_code": '''from enum import Enum
from typing import Annotated

from fastapi import FastAPI, Path

app = FastAPI(title="路径约束示例")


class TaskStatus(str, Enum):
    todo = "todo"
    doing = "doing"
    done = "done"


@app.get("/tasks/latest")
def latest() -> dict:
    return {"id": 99, "title": "最新任务"}


@app.get("/tasks/status/{status}")
def by_status(status: TaskStatus) -> dict:
    return {"status": status.value, "finished": status is TaskStatus.done}


@app.get("/tasks/{task_id}")
def get_task(task_id: Annotated[int, Path(ge=1, le=10000)]) -> dict:
    return {"id": task_id}''',
                "code_lines": """1. `TaskStatus` 继承 `str` 与 `Enum`，取值既能校验又能直接当字符串用。
2. `/tasks/latest` 必须写在 `/tasks/{task_id}` 之前，否则会被当成 id 处理。
3. `/tasks/status/{status}` 声明在动态路径之前，避免 `status` 被当 id。
4. `status: TaskStatus` 让框架按枚举校验，非法值直接 422 并列出可选值。
5. `status is TaskStatus.done` 用枚举成员比较，比比较字符串更安全（拼错会立刻发现）。
6. `Annotated[int, Path(...)]` 把范围约束写进签名，同时进入 OpenAPI 文档。
7. `ge=1` 拒绝 0 与负数，`le=10000` 挡住异常大的值，避免无意义查询。""",
                "output": """# 请求与响应
curl http://127.0.0.1:8000/tasks/latest
{"id":99,"title":"最新任务"}

curl http://127.0.0.1:8000/tasks/status/done
{"status":"done","finished":true}

curl http://127.0.0.1:8000/tasks/status/unknown
HTTP/1.1 422 Unprocessable Entity
{"detail":[{"type":"enum","loc":["path","status"],
"msg":"Input should be 'todo', 'doing' or 'done'",
"input":"unknown","ctx":{"expected":"'todo', 'doing' or 'done'"}}]}

curl http://127.0.0.1:8000/tasks/0
{"detail":[{"type":"greater_than_equal","loc":["path","task_id"],
"msg":"Input should be greater than or equal to 1","input":"0","ctx":{"ge":1}}]}""",
                "mistakes": """- 把 `/tasks/latest` 写在 `/tasks/{task_id}` 后面，永远 404 或 422。
- 用裸字符串比较状态（`status == "done"`），拼错不报错。
- 用 `> 0` 之类的判断写在函数体里，约束不进文档也没统一报错。
- 枚举成员名与值混用，导致序列化出 `TaskStatus.done` 这种字符串。
- 忘了 `Path` 的约束只在路径参数生效，查询参数要用 `Query`。""",
                "error_analysis": """`422 int_parsing` 出现在 `/tasks/latest`
—— 说明它被 `{task_id}` 抢走了。把固定路径声明移到前面。

`422 enum` 且 `input` 是拼错的值
—— 枚举校验生效。对照 `ctx.expected` 修正调用方传值。

`AssertionError: Param: task_id can only be a request body param`
—— 把 `Path()` 用在了非路径参数上。查询参数要用 `Query()`。""",
                "beginner_practice": """1. 新增固定路径 `/tasks/count`，要求它在 `/tasks/{task_id}` 之前生效。
2. 给枚举加一个 `archived` 状态，验证文档与报错同步更新。""",
                "advanced_practice": """设计「按状态 + 分页」查询任务列表的接口，说明状态用枚举校验、
分页用查询参数校验分别该用什么工具，并解释为什么不把约束写在函数体里。""",
                "quiz_note": "本节 6 道题：2 道基础理解（匹配顺序、枚举作用）+ 2 道代码阅读（读路由顺序、读 422）+ 2 道应用练习（调整顺序、加约束）。",
                "summary": """路由按声明顺序匹配，固定路径必须写在动态路径之前。
枚举限定取值、Path 限定范围，两者都会进入 OpenAPI 文档。
约束写在签名里，错误由框架统一返回 422，函数体只处理业务。""",
                "next_lesson": "下一节讲查询参数：`?page=2&size=20` 怎么声明、怎么校验、怎么拼出分页。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-03-02",
                        "name": "路由顺序、枚举与路径约束",
                        "goal": "能避免路径冲突，并用枚举与范围约束住路径取值。",
                        "minutes": 35,
                        "criteria": "能解释 `/tasks/latest` 为什么 404，并写出带范围约束的路径参数。",
                        "requires": ["fastapi-backend-03-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-03-02-1",
                        "kp": 0,
                        "title": "修好被抢走的路由",
                        "description": "给定三个路由（`/tasks/{task_id}`、`/tasks/count`、`/tasks/latest`）顺序写反的代码，调整顺序并说明匹配过程。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''@app.get("/tasks/count")
def count() -> dict: ...


@app.get("/tasks/latest")
def latest() -> dict: ...


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict: ...

# 匹配时 count/latest 先命中固定路径，其余才落到动态路径''',
                        "explanation": "固定路径越具体越靠前；`{task_id}` 是兜底，必须放最后。",
                    },
                    {
                        "code": "fa-ex-03-02-2",
                        "kp": 0,
                        "title": "给状态加枚举",
                        "description": "用 Enum 定义 todo/doing/done 三态，写 `/tasks/status/{status}` 接口，并说明非法值返回什么。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''class TaskStatus(str, Enum):
    todo = "todo"
    doing = "doing"
    done = "done"

@app.get("/tasks/status/{status}")
def by_status(status: TaskStatus) -> dict:
    return {"status": status.value}

非法值返回 422，type=enum，ctx.expected 列出三个合法值。''',
                        "explanation": "枚举既有类型校验又能进文档；返回值用 `.value` 避免序列化出成员名字。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-03-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`/tasks/latest` 返回 422 而不是 200，最可能的原因是？",
                        "options": [
                            ("A", "路由声明顺序错误，被 `{task_id}` 先匹配"),
                            ("B", "latest 不是合法整数"),
                            ("C", "缺少查询参数"),
                            ("D", "响应模型错误"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`{task_id}` 先注册就会先匹配，`latest` 被当作 int 转换失败，返回 422。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-03-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "使用 Enum 作为路径参数类型带来的好处有？（多选）",
                        "options": [
                            ("A", "非法值自动返回 422"),
                            ("B", "OpenAPI 文档列出可选值"),
                            ("C", "自动把值转成大写"),
                            ("D", "代码里可用成员比较，拼错即时发现"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "枚举不会做大小写转换，C 是错的。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-03-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "请求 `/tasks/status/done` 时返回的 `finished` 是？",
                        "options": [("A", "true"), ("B", "false"), ("C", '"done"'), ("D", "null")],
                        "answer": {"value": "A"},
                        "explanation": "`status is TaskStatus.done` 为真，所以 `finished` 是布尔 true。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-03-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`Path(ge=1)` 的约束也会出现在 openapi.json 里。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "A"},
                        "explanation": "Path/Query 的约束会写入参数 schema，前端与调用方都能看到。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-03-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全声明，使 `task_id` 必须是 1 到 10000 之间的整数。横线处应填什么？\n\n```python\nfrom typing import Annotated\nfrom fastapi import Path\n\ndef get_task(task_id: ____) -> dict: ...\n```",
                        "options": [
                            ("A", "Annotated[int, Path(ge=1, le=10000)]"),
                            ("B", "Path(int, ge=1, le=10000)"),
                            ("C", "int = Path(ge=1, le=10000)"),
                            ("D", "Annotated[Path, int(1, 10000)]"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "现代写法是 `Annotated[类型, 约束]`；C 也能跑但把约束当成了默认值，语义不对。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-03-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么不建议在函数体里写 `if task_id < 1: raise ...`？",
                        "answer": {"value": "函数体里的判断不会进入 OpenAPI，调用方看不到约束；错误也需要手写 raise，口径不一致。写在签名里（Path/Query）能让文档、校验、错误响应三件事一次完成，函数体只保留业务逻辑。"},
                        "explanation": "要点：约束应作为契约的一部分暴露给调用方，而不是藏在实现里。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "fastapi-backend-04",
        "title": "查询参数",
        "description": "把筛选、分页与排序做成可校验的查询参数。",
        "order_index": 4,
        "lessons": [
            {
                "code": "fastapi-backend-04-lesson-01",
                "objectives": """1. 能区分「有默认值即可选」「无默认值即必填」的查询参数；
2. 会用 `Query` 约束范围、长度，并控制文档展示；
3. 能实现分页、布尔筛选与多值参数；
4. 知道查询参数与请求体的使用边界。""",
                "why_learn": """列表接口几乎都带查询参数，而这正是最容易出问题的地方：`size` 不设上限会被拖垮数据库，布尔值传 `"false"` 被当成真值，多值参数写成逗号串解析出错。这些都应该在入口用声明解决。""",
                "concepts": """**查询参数**：`?` 后面的键值对，非路径的一部分。
**可选与必填**：有默认值 → 可选；无默认值 → 必填，缺失返回 422。
**类型转换**：`bool` 接受 `true/false/1/0/yes/no`；`list[str]` 用重复键表达。
**Query 约束**：`ge/le/gt/lt/min_length/max_length/pattern`，同时写入文档。
**别名**：`alias="page-size"` 让对外用连字符、对内仍用下划线变量。""",
                "plain": """路径参数像身份证号，查询参数像点菜时的备注：「不要辣、少放盐、分两盘」。
同一份菜单（同一个资源），备注不同就是不同的呈现，所以备注不写进菜名里。
约束就是备注的规矩：可以写「微辣中辣特辣」，但不能写「变态辣」——写了厨房也不做，直接退单。""",
                "syntax": """**API 说明**

```python
@app.get("/tasks")
def list_tasks(
    done: bool | None = None,                                  # 可选筛选
    page: Annotated[int, Query(ge=1)] = 1,                      # 有默认值
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    tags: Annotated[list[str] | None, Query()] = None,
    sort: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
): ...
```

- 没有默认值的查询参数是必填；`| None = None` 表示可选。
- `list[str]` 需用 `?tags=a&tags=b` 重复键，或用 `Query()` 声明。
- `pattern` 用正则约束取值，比手写 if 更早拦截。""",
                "example_code": '''from typing import Annotated

from fastapi import FastAPI, Query

app = FastAPI(title="查询参数示例")

TASKS = [{"id": 1, "title": "写周报", "done": False}, {"id": 2, "title": "交报表", "done": True}]


@app.get("/tasks")
def list_tasks(
    done: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
) -> dict:
    items = TASKS
    if done is not None:
        items = [task for task in items if task["done"] is done]
    if q:
        items = [task for task in items if q in task["title"]]
    start = (page - 1) * size
    return {"items": items[start : start + size], "total": len(items), "page": page, "size": size}''',
                "code_lines": """1. `done: bool | None = None` 表示可选筛选，不传就是 None（不是 False）。
2. `Query(ge=1)` 挡住 `page=0` 与负数，避免出现负偏移。
3. `Query(ge=1, le=100)` 给 `size` 设上限，防止一次拉全表。
4. `q` 的长度约束在入口生效，避免超长字符串进到 SQL 的 LIKE。
5. `if done is not None` 而不是 `if done`，避免把 False 当成「没传」。
6. 分页用切片模拟数据库的 OFFSET/LIMIT，真实项目由 SQL 完成。
7. 响应同时给 `total` 与 `page/size`，前端才算得出总页数。""",
                "output": """# 请求与响应
curl "http://127.0.0.1:8000/tasks?done=false"
{"items":[{"id":1,"title":"写周报","done":false}],"total":1,"page":1,"size":20}

curl "http://127.0.0.1:8000/tasks?q=%E5%91%A8&page=1&size=10"
{"items":[{"id":1,"title":"写周报","done":false}],"total":1,"page":1,"size":10}

# 参数越界
curl "http://127.0.0.1:8000/tasks?size=500"
HTTP/1.1 422 Unprocessable Entity
{"detail":[{"type":"less_than_equal","loc":["query","size"],
"msg":"Input should be less than or equal to 100","input":"500","ctx":{"le":100}}]}

# 布尔值写法都合法
?done=true   ?done=1   ?done=yes   均解析为 True；?done=0 为 False""",
                "mistakes": """- `if done:` 判断可选布尔，导致 `done=false` 被当成「没传」。
- `size` 不设上限，`?size=100000` 一次把库拉空。
- 多值参数用逗号拼接再 split，遇到值里本身有逗号就解析错。
- 分页偏移用 `page * size`，第一页就跳过了一整页数据。
- 把筛选字段放进请求体（GET 请求通常无 body，且不利于缓存）。""",
                "error_analysis": """`422 missing` 且 `loc: ["query","page"]`
—— 参数声明成了必填（没有默认值）。要么给默认值，要么在文档里说明必填。

`422 bool_parsing`
—— 传了 `?done=否` 这类值。布尔只接受 true/false/1/0/yes/no（大小写不敏感）。

`?tags=a,b` 只拿到一个元素 `"a,b"`
—— 多值参数要用重复键 `?tags=a&tags=b`。""",
                "beginner_practice": """1. 给列表接口加 `sort` 参数，只允许 `asc` / `desc`，用 `pattern` 约束。
2. 验证 `?page=0` 与 `?size=101` 的报错内容差异。""",
                "advanced_practice": """为「任务列表」设计完整查询参数：状态筛选、关键词、标签多选、排序、分页。
写清每个参数的类型、默认值、约束与在 SQL 中对应的条件，并说明为什么排序字段要用白名单而不是直接拼接。""",
                "quiz_note": "本节 6 道题：2 道基础理解（可选/必填、约束作用）+ 2 道代码阅读（读筛选逻辑、读 422）+ 2 道应用练习（补参数、修分页偏移）。",
                "summary": """有默认值即可选、没默认值即必填；可选布尔要用 `is not None` 判断。
`Query` 负责范围、长度与正则约束，并同步写进文档。
分页偏移是 `(page - 1) * size`，`size` 必须有上限。""",
                "next_lesson": "下一节讲五种 HTTP 方法：同一个 `/tasks/{id}`，为什么换个方法语义就完全不同。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-04-01",
                        "name": "查询参数、分页与 Query 校验",
                        "goal": "能声明可选的筛选与分页参数，并用 Query 约束取值范围。",
                        "minutes": 55,
                        "criteria": "能写出带分页与筛选的列表接口，并解释 422 的触发条件。",
                        "requires": ["fastapi-backend-03-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-04-01-1",
                        "kp": 0,
                        "title": "加分页与排序",
                        "description": "在示例接口里加 `sort: asc|desc`（用 pattern 约束），并让 `size` 超过 100 时返回 422。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''size: Annotated[int, Query(ge=1, le=100)] = 20,
sort: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",

items = sorted(items, key=lambda t: t["id"], reverse=(sort == "desc"))''',
                        "explanation": "约束写在声明里即可；排序方向用布尔映射，避免在 SQL 里拼字符串。",
                    },
                    {
                        "code": "fa-ex-04-01-2",
                        "kp": 0,
                        "title": "修好分页偏移",
                        "description": "下面代码第一页返回的是第二页数据，找出问题并改正：`start = page * size`。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''应为 start = (page - 1) * size。
page 从 1 开始计数，page=1 时偏移必须是 0；否则第一页就跳过了 size 条。''',
                        "explanation": "分页约定要写进文档：页码从 1 开始还是从 0 开始，全站统一。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-04-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "声明 `page: int = 1` 与 `page: int` 的区别是？",
                        "options": [
                            ("A", "前者可选（默认 1），后者必填"),
                            ("B", "前者必填，后者可选"),
                            ("C", "没有区别"),
                            ("D", "前者只能用整数，后者可以用字符串"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "有默认值即视为可选参数，缺省时用默认值；没有默认值就要求调用方必须提供。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-04-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 `Query(ge=1, le=100)`，正确的说法有？（多选）",
                        "options": [
                            ("A", "JSON 里会注明取值范围"),
                            ("B", "越界时返回 422"),
                            ("C", "它会自动把超范围的值截断到边界"),
                            ("D", "约束在进入函数体之前生效"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "校验不会做「截断」这种隐式修正，越界就是拒绝，C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-04-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "请求 `/tasks?done=false` 时返回几条数据？",
                        "options": [("A", "0 条"), ("B", "1 条（写周报）"), ("C", "2 条"), ("D", "422")],
                        "answer": {"value": "B"},
                        "explanation": "`done` 为 False（不是 None），筛选出未完成的任务，只有「写周报」一条。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-04-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把判断写成 `if done:` 与 `if done is not None:` 在 `done=false` 时结果相同。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "`if done:` 遇到 False 会当成「没传」，跳过筛选，导致返回全部数据。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-04-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全声明，使 `size` 默认为 20、最小 1、最大 100。横线处应填什么？\n\n```python\nsize: Annotated[int, ____] = 20\n```",
                        "options": [
                            ("A", "Query(ge=1, le=100)"),
                            ("B", "Query(1, 100)"),
                            ("C", "Query(min=1, max=100)"),
                            ("D", "Query(range=(1, 100))"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "数值约束的参数名是 `ge/le/gt/lt`；`min/max` 不是 Query 的参数名。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-04-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么排序字段不能直接把用户传的字符串拼进 SQL？给出正确做法。",
                        "answer": {"value": "直接拼接会造成 SQL 注入，且非法列名会让查询报错甚至泄露表结构。正确做法是用白名单映射：`SORT_FIELDS = {\"id\": Task.id, \"created\": Task.created_at}`，取不到就回退默认字段，再用 ORM 的 order_by 拼接列对象而不是字符串。"},
                        "explanation": "要点是「白名单映射」+「用列对象而非字符串」，只说「过滤一下」不够。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
