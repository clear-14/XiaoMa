"""FastAPI 后端开发：第 6—8 章（Pydantic 校验、Depends 依赖注入、路由模块化）。"""

CHAPTERS: list[dict] = [
    {
        "code": "fastapi-backend-06",
        "title": "Pydantic 模型与数据校验",
        "description": "把校验规则写进模型，让非法输入在入口被拦住。",
        "order_index": 6,
        "lessons": [
            {
                "code": "fastapi-backend-06-lesson-01",
                "objectives": """1. 会用 `Field` 声明长度、范围、正则与文档描述；
2. 会用别名兼容前端命名，并允许用字段名传参；
3. 能读懂 `Field` 约束在 /docs 与 422 里的体现；
4. 知道哪些校验该写在模型、哪些属于业务校验。""",
                "why_learn": """同一个 `title`，前端可能传 `title`，移动端可能传 `taskTitle`；`priority` 可能是 1—5，也可能是 0—10。
把这些规则写进模型，校验、文档、错误提示一次到位；写在函数体里，则永远只有你自己知道。""",
                "concepts": """**Field**：为单个字段声明约束与元信息（`min_length`、`ge`、`pattern`、`description`、`examples`）。
**别名**：`alias="ownerEmail"` 让对外用驼峰、对内用下划线。
**populate_by_name**：允许用字段名或别名传参，兼容两种调用方。
**校验分层**：格式与范围写模型；「任务是否属于当前用户」这类要查库的规则放业务层。""",
                "plain": """模型像表单：每个格子写清楚「必填、最多几个字、只能填数字」。
别名像表单上的「曾用名」：有人按新名字交，有人按老名字交，系统都认，但内部只用一个名字处理。
分层的道理也简单：格子本身能判断的（是不是空、多长）当场退单；需要查档案才能判断的（这人有没有权限）得进业务环节。""",
                "syntax": """**API 说明**

```python
class TaskCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=50, description="任务标题")
    priority: int = Field(default=1, ge=1, le=5)
    owner_email: str = Field(alias="ownerEmail")
```

- `model_config` 用 `ConfigDict`（Pydantic v2 写法），可统一定义别名策略、去空格等行为。
- 常用约束：`min_length/max_length`、`ge/le/gt/lt`、`pattern`、`multiple_of`。
- `examples` 会进入 OpenAPI，让文档自带示例值。""",
                "example_code": '''from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=50, description="任务标题")
    priority: int = Field(default=1, ge=1, le=5, description="优先级 1—5")
    owner_email: str = Field(alias="ownerEmail", pattern=r"^[^@]+@[^@]+\\.[^@]+$")
    tags: list[str] = Field(default_factory=list, max_length=5)


valid = TaskCreate(title="  写周报  ", ownerEmail="lisi@example.com", tags=["周报"])
print("title 已去空格:", repr(valid.title))
print("别名转字段名:", valid.owner_email)
print("默认优先级:", valid.priority)

for bad in ({"title": "", "ownerEmail": "lisi@example.com"}, {"title": "写周报", "ownerEmail": "lisi"}):
    try:
        TaskCreate(**bad)
    except Exception as exc:
        print("被拒绝:", exc.errors()[0]["type"], exc.errors()[0]["loc"])''',
                "code_lines": """1. `model_config = ConfigDict(...)` 是 Pydantic v2 的配置入口，替代 v1 的内部 Config 类。
2. `str_strip_whitespace=True` 自动去掉首尾空格，避免「看起来是空」的标题通过校验。
3. `Field(min_length=1, max_length=50)` 在模型层拦住空串与超长标题。
4. `ge=1, le=5` 把优先级限制在 1—5，越界直接报错而不是入库后才发现。
5. `alias="ownerEmail"` 让请求体用驼峰；`populate_by_name=True` 允许代码里用 `owner_email`。
6. `pattern` 用正则校验邮箱格式，只做「形状检查」，不验证邮箱是否真实存在。
7. `default_factory=list` 避免可变默认值被多个实例共享这个经典坑。
8. 循环里两种非法输入分别触发 `string_too_short` 与 `string_pattern_mismatch`。""",
                "output": """title 已去空格: '写周报'
别名转字段名: lisi@example.com
默认优先级: 1
被拒绝: string_too_short ('title',)
被拒绝: string_pattern_mismatch ('ownerEmail',)

# 在接口中的请求与响应
curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" \\
  -d '{"title":"写周报","ownerEmail":"lisi@example.com","priority":9}'
HTTP/1.1 422 Unprocessable Entity
{"detail":[{"type":"less_than_equal","loc":["body","priority"],
"msg":"Input should be less than or equal to 5","input":9,"ctx":{"le":5}}]}""",
                "mistakes": """- 用 `tags: list[str] = []` 作默认值，多个实例共享同一个列表。
- 别名写成 `alias="ownerEmail"` 却仍用 `ownerEmail` 取值（模型属性名是 `owner_email`）。
- 把 `min_length` 用到 `int` 字段上，Pydantic 会报配置错误。
- 用 `pattern` 校验邮箱是否存在（正则只能看形状）。
- 把需要查库的业务规则写进模型，导致模型依赖数据库会话。""",
                "error_analysis": """`PydanticUserError: 'min_length' is not a valid constraint for int`
—— 数值字段要用 `ge/le`，长度约束只适用于字符串与容器。

`ValidationError: 1 validation error for TaskCreate`
—— 构造模型时校验失败。用 `exc.errors()` 查看 `type` 与 `loc`，不要只打印整段异常。

`422` 说缺少 `ownerEmail`
—— 别名与字段名不匹配，且没开 `populate_by_name`。""",
                "beginner_practice": """1. 给 `title` 加 `strip_whitespace` 与 `max_length=20`，验证超长标题被拒。
2. 给 `priority` 换成 `Literal[1, 2, 3]`，比较与 `ge/le` 的报错差异。""",
                "advanced_practice": """为「注册」设计模型：邮箱正则、密码长度与强度、昵称长度、手机号可选。
说明哪些规则适合放在模型里，哪些必须放到业务层，并给出理由。""",
                "quiz_note": "本节 6 道题：2 道基础理解（Field 约束、别名）+ 2 道代码阅读（读配置、读 422）+ 2 道应用练习（补约束、换 Literal）。",
                "summary": """`Field` 把长度、范围、正则与文档描述写在字段上，校验与文档一次完成。
别名兼容不同客户端的命名，`populate_by_name` 让代码继续用字段名。
格式与范围放模型，需要查库的规则放业务层。""",
                "next_lesson": "下一节写自定义校验器：跨字段的「截止时间必须晚于开始时间」该放在哪里。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-06-01",
                        "name": "Pydantic Field 约束与别名",
                        "goal": "能用 Field 与别名定义可校验、可文档化的字段。",
                        "minutes": 35,
                        "criteria": "能写出带长度、范围、正则约束的模型，并解释 422 的 type 含义。",
                        "requires": ["fastapi-backend-05-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-06-01-1",
                        "kp": 0,
                        "title": "给注册模型加约束",
                        "description": "写 `RegisterIn`：email（正则）、password（8—32 位）、nickname（1—20 位）、phone（可选，11 位数字）。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''class RegisterIn(BaseModel):
    email: str = Field(pattern=r"^[^@]+@[^@]+\\.[^@]+$")
    password: str = Field(min_length=8, max_length=32)
    nickname: str = Field(min_length=1, max_length=20)
    phone: str | None = Field(default=None, pattern=r"^1\\d{10}$")''',
                        "explanation": "可选字段用 `| None = None`，正则仍会校验已传的值；密码长度用 min/max_length 而非 ge/le。",
                    },
                    {
                        "code": "fa-ex-06-01-2",
                        "kp": 0,
                        "title": "别名兼容两套命名",
                        "description": "让同一个模型既能接收 `ownerEmail` 也能接收 `owner_email`，并说明配置项。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''owner_email: str = Field(alias="ownerEmail")
model_config = ConfigDict(populate_by_name=True)

populate_by_name=True 允许用字段名传参；不设它就只能用别名。''',
                        "explanation": "对外兼容两种命名、对内只有一个属性名，是渐进式改造接口的常用手段。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-06-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要给整数字段限制范围 1—5，应使用？",
                        "options": [
                            ("A", "Field(ge=1, le=5)"),
                            ("B", "Field(min_length=1, max_length=5)"),
                            ("C", "Field(pattern=\"1-5\")"),
                            ("D", "Field(range=(1, 5))"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "数值约束用 `ge/le/gt/lt`；`min_length` 只适用于字符串与容器。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-06-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "`model_config = ConfigDict(str_strip_whitespace=True)` 带来的效果有？（多选）",
                        "options": [
                            ("A", "字符串首尾空格被去掉"),
                            ("B", "只含空格的标题会变成空串并被 min_length 拦住"),
                            ("C", "字符串中间的连续空格也会被合并"),
                            ("D", "影响所有 str 字段"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "它只处理首尾空格，不合并中间空格，C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-06-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`TaskCreate(title=\"  写周报  \", ownerEmail=\"lisi@example.com\")` 之后 `title` 的值是？",
                        "options": [("A", "'  写周报  '"), ("B", "'写周报'"), ("C", "空串"), ("D", "报错")],
                        "answer": {"value": "B"},
                        "explanation": "`str_strip_whitespace=True` 在解析阶段就去掉首尾空格。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-06-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`alias=\"ownerEmail\"` 之后，代码里应通过 `task.ownerEmail` 访问该字段。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "别名只影响外部输入输出，模型属性名仍是 `owner_email`。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-06-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全字段声明：昵称必填、长度 1—20。横线处应填什么？\n\n```python\nnickname: str = ____\n```",
                        "options": [
                            ("A", 'Field(min_length=1, max_length=20)'),
                            ("B", 'Field(ge=1, le=20)'),
                            ("C", 'Field(len=20)'),
                            ("D", 'Field(min=1, max=20)'),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "字符串长度约束是 `min_length/max_length`；`ge/le` 用于数值。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-06-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "「任务标题在同一个项目内不能重复」这条规则该写进模型还是业务层？说明理由。",
                        "answer": {"value": "写业务层（或数据库唯一约束）。它需要查询已有数据，属于跨记录的业务规则，模型只掌握当前输入，无法知道库里状态。正确做法是在服务层查询后返回 409，并用唯一索引兜底并发写入。"},
                        "explanation": "判断标准是「是否需要外部状态」：需要查库就属于业务规则，模型只做形状校验。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-06-lesson-02",
                "objectives": """1. 会用 `field_validator` 处理单字段规则；
2. 会用 `model_validator(mode="after")` 表达跨字段规则；
3. 能组织嵌套模型与列表模型；
4. 能读懂 422 里的 `loc` 路径，快速定位是哪个字段、哪一层。""",
                "why_learn": """「截止时间必须晚于开始时间」「确认密码必须与密码一致」这类规则，单个字段自己判断不了。
把它们写成校验器，错误会自动变成结构化 422，前端能直接标红对应输入框，而不是弹一个「操作失败」。""",
                "concepts": """**field_validator**：校验单个字段，`mode="before"` 处理原始输入，`mode="after"` 处理已转换值。
**model_validator**：`mode="after"` 拿到整个模型，做跨字段判断。
**嵌套模型**：字段类型是另一个模型或模型列表，校验会递归进入。
**422 的 loc**：数组形式，如 `["body", "subtasks", 0, "title"]`，逐层指出位置。""",
                "plain": """字段校验器像安检的单项检查：这件行李里有没有液体。
模型校验器像整体检查：行李之间能不能互相带（打火机不能和易燃物放一起）。
嵌套模型就是「大包里有小包」，安检会打开小包继续查，报错时会告诉你「第 0 个小包里的标题不合格」。""",
                "syntax": """**API 说明**

```python
class TaskCreate(BaseModel):
    title: str
    start_at: datetime | None = None
    due_at: datetime | None = None
    subtasks: list[SubTask] = []

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str: ...

    @model_validator(mode="after")
    def check_due(self): ...
```

- 校验器用 `@classmethod` 装饰，返回值必须是处理后的值。
- 抛 `ValueError("说明")`，FastAPI 会转成 422 的 `msg`。
- 嵌套列表错误会在 `loc` 里带上索引。""",
                "example_code": '''from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class SubTask(BaseModel):
    title: str = Field(min_length=1, max_length=30)
    done: bool = False


class TaskCreate(BaseModel):
    title: str
    start_at: datetime | None = None
    due_at: datetime | None = None
    subtasks: list[SubTask] = []

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("标题不能只有空白字符")
        return value.strip()

    @model_validator(mode="after")
    def check_due_after_start(self):
        if self.start_at and self.due_at and self.due_at <= self.start_at:
            raise ValueError("截止时间必须晚于开始时间")
        return self


ok = TaskCreate(title=" 写周报 ", subtasks=[{"title": "列要点"}])
print("标题:", ok.title, "子任务:", len(ok.subtasks))

for payload in (
    {"title": "   "},
    {"title": "写周报", "start_at": "2026-11-10T09:00:00", "due_at": "2026-11-09T09:00:00"},
    {"title": "写周报", "subtasks": [{"title": ""}]},
):
    try:
        TaskCreate(**payload)
    except Exception as exc:
        error = exc.errors()[0]
        print("被拒绝:", error["loc"], "|", error["msg"])''',
                "code_lines": """1. `SubTask` 是被复用的嵌套模型，包含自己的字段约束。
2. `subtasks: list[SubTask] = []` 让列表元素也走一遍校验。
3. `@field_validator("title")` 只拦标题字段；`@classmethod` 是必须的写法。
4. 抛 `ValueError` 而不是 `assert`，前者会被包成 422 的 `msg`。
5. 返回值 `value.strip()` 决定进入模型的实际内容——校验器可以顺手做规范化。
6. `@model_validator(mode="after")` 拿到的 `self` 已完成字段级校验，可安全比较两个时间。
7. `return self` 不能省，否则模型构造失败。
8. 循环里三种非法输入分别命中字段校验、跨字段校验与嵌套校验，`loc` 逐层指出位置。""",
                "output": """标题: 写周报 子任务: 1
被拒绝: ('title',) | Value error, 标题不能只有空白字符
被拒绝: ('due_at',) | Value error, 截止时间必须晚于开始时间
被拒绝: ('subtasks', 0, 'title') | String should have at least 1 character

# 接口层面的请求与响应
curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" \\
  -d '{"title":"写周报","start_at":"2026-11-10T09:00:00","due_at":"2026-11-09T09:00:00"}'
HTTP/1.1 422 Unprocessable Entity
{"detail":[{"type":"value_error","loc":["body"],
"msg":"Value error, 截止时间必须晚于开始时间","input":{...}}]}""",
                "mistakes": """- 忘了 `@classmethod`，得到 `PydanticUserError: field_validator must be classmethod`。
- `mode="after"` 的校验器忘了 `return self`，模型构造直接失败。
- 在字段校验器里访问其他字段（拿不到），跨字段规则必须用 `model_validator`。
- 抛 `HTTPException` 而不是 `ValueError`，导致变成 5xx 或错误结构不一致。
- 只看 `msg` 不看 `loc`，多字段报错时分不清哪条对应哪个输入框。""",
                "error_analysis": """`PydanticUserError: field_validator must be classmethod`
—— 漏写 `@classmethod`。

`Value error, 截止时间必须晚于开始时间` 且 `loc` 为 `["body"]`
—— 跨字段校验失败定位在整体而非某字段，这是 `model_validator` 的固有行为，前端要按消息提示而非字段标红。

`500` 而不是 `422`
—— 校验器里抛了非 ValueError（如 KeyError），框架不会转成校验错误。""",
                "beginner_practice": """1. 给 `SubTask.title` 加「不能包含换行」的校验器。
2. 把 `check_due_after_start` 改成「两者都必须同时提供或同时为空」。""",
                "advanced_practice": """实现「确认密码」校验：`password` 与 `password_confirm` 必须一致，
并说明为什么错误应挂在 `password_confirm` 上而不是整体；再讨论校验器与接口层重复校验的取舍。""",
                "quiz_note": "本节 6 道题：2 道基础理解（校验器类型、loc 含义）+ 2 道代码阅读（读 return self、读嵌套 loc）+ 2 道应用练习（补校验器、定位错误）。",
                "summary": """单字段规则用 `field_validator`，跨字段规则用 `model_validator(mode="after")`。
校验器用 `@classmethod`，抛 `ValueError`，并返回处理后的值/`self`。
嵌套模型的错误在 `loc` 里带索引，前端可据此精确定位输入框。""",
                "next_lesson": "下一节讲 Depends：分页、配置、数据库会话怎么抽成可复用的依赖。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-06-02",
                        "name": "自定义校验器与嵌套模型",
                        "goal": "能写出单字段与跨字段校验器，并读懂嵌套模型的 422。",
                        "minutes": 45,
                        "criteria": "能实现「截止时间晚于开始时间」的校验，并说清 loc 各段含义。",
                        "requires": ["fastapi-backend-06-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-06-02-1",
                        "kp": 0,
                        "title": "确认密码校验",
                        "description": "在注册模型上加 `password_confirm`，两者不一致时报错，并让错误尽量指向 `password_confirm`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class RegisterIn(BaseModel):
    password: str = Field(min_length=8, max_length=32)
    password_confirm: str

    @model_validator(mode="after")
    def check_confirm(self):
        if self.password != self.password_confirm:
            raise ValueError("两次输入的密码不一致")
        return self''',
                        "explanation": "跨字段只能用 model_validator；若想让错误落到具体字段，可在错误消息里明确写出字段名，或改用 field_validator 配合 context。",
                    },
                    {
                        "code": "fa-ex-06-02-2",
                        "kp": 0,
                        "title": "读 loc 定位字段",
                        "description": "给出 `loc` 为 `['body','subtasks',2,'title']` 的 422，说明是哪个字段错了、该怎么提示用户。",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''请求体里 subtasks 数组第 3 个元素（索引 2）的 title 校验失败。
提示应为「第 3 个子任务的标题不合法」，而不是泛泛的「参数错误」。''',
                        "explanation": "loc 是逐层路径：body → 字段名 → 数组索引 → 子字段，前端可据此定位到具体输入框。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-06-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要校验「截止时间晚于开始时间」，应该用？",
                        "options": [
                            ("A", "field_validator(\"due_at\")"),
                            ("B", "model_validator(mode=\"after\")"),
                            ("C", "Field(gt=\"start_at\")"),
                            ("D", "在接口函数里写 if"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "跨字段比较需要拿到整个模型，`field_validator` 只能看到单个字段的值。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-06-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "写校验器时必须注意的点有？（多选）",
                        "options": [
                            ("A", "用 @classmethod 装饰"),
                            ("B", "抛 ValueError 表达校验失败"),
                            ("C", "model_validator(mode=\"after\") 要 return self"),
                            ("D", "校验器里应直接抛 HTTPException"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "校验器抛 HTTPException 会绕过校验错误结构，D 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-06-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`{'title':'写周报','subtasks':[{'title':''}]}` 的 422 中 `loc` 是？",
                        "options": [
                            ("A", "['body','title']"),
                            ("B", "['body','subtasks','title']"),
                            ("C", "['body','subtasks',0,'title']"),
                            ("D", "['body']"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "嵌套列表会带上元素索引 0，指向第一个子任务的 title。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-06-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "在 `field_validator(\"title\")` 里可以访问 `self.due_at`。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "字段校验器的第一个参数是单个值，不是模型实例，拿不到其他字段。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-06-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全装饰器，使其校验 `title` 字段。横线处应填什么？\n\n```python\n____\n@classmethod\ndef title_not_blank(cls, value: str) -> str: ...\n```",
                        "options": [
                            ("A", '@field_validator("title")'),
                            ("B", '@validator("title")'),
                            ("C", '@field_validate("title")'),
                            ("D", '@model_validator("title")'),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "Pydantic v2 用 `field_validator`；`validator` 是 v1 的旧写法。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-06-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "前端说「只收到一句参数错误，不知道改哪」，你如何让 422 变得可定位？",
                        "answer": {"value": "保留框架默认的 422 结构（detail 数组含 loc/type/msg/input），不要自己 catch 后拼成一句话；前端按 loc 逐层映射到表单项，必要时在 msg 里写清业务含义（如「第 3 个子任务标题不能为空」）。如果必须自定义响应结构，也要保留 loc 与 msg 两个字段。"},
                        "explanation": "核心是「结构化错误 + 前端按 loc 映射」，而不是把所有错误压成一句自然语言。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "fastapi-backend-07",
        "title": "Depends 依赖注入",
        "description": "把分页、配置、会话与鉴权抽成可替换的依赖。",
        "order_index": 7,
        "lessons": [
            {
                "code": "fastapi-backend-07-lesson-01",
                "objectives": """1. 会用 `Depends` 声明依赖，并在函数里直接拿到结果；
2. 理解「同一请求内同名依赖只执行一次」的缓存行为；
3. 会用 `yield` 依赖管理需要释放的资源；
4. 能把分页、配置、会话这类横切逻辑抽成可复用依赖。""",
                "why_learn": """分页参数、配置读取、数据库会话、当前用户——这些逻辑几乎每个接口都要用。
复制粘贴会让改一处要改十处；写成依赖后，接口签名里只声明「我需要什么」，具体怎么来由依赖负责，测试时还能整体替换。""",
                "concepts": """**依赖**：一个可调用对象，FastAPI 在调用接口前执行它，把返回值注入参数。
**声明方式**：`param: Annotated[类型, Depends(可调用)]`。
**缓存**：同一请求内同一个依赖只执行一次，多个接口参数可共享结果。
**yield 依赖**：`yield` 之前是准备，之后是清理，异常路径也会执行清理。
**可替换性**：测试时用 `app.dependency_overrides` 换掉依赖。""",
                "plain": """依赖像公司里的公共设施：你不用自己发电，插上就用。
「这个请求需要分页参数」等于在工位上插了个插座，谁需要谁插，不用各自造一套。
yield 依赖像借用会议室：进门登记、出门关灯，哪怕会开到一半吵起来（抛异常），关门这件事也必须做。""",
                "syntax": """**API 说明**

```python
def pagination(page: int = 1, size: int = 20) -> dict: ...

@app.get("/tasks")
def list_tasks(pager: Annotated[dict, Depends(pagination)]): ...

def get_db():
    db = connect()
    try:
        yield db
    finally:
        db.close()
```

- 依赖也可以是类，FastAPI 会调用其 `__init__`。
- `yield` 依赖的清理逻辑在响应发送后执行，异常也会触发。
- 依赖里可以继续声明依赖，形成层级。""",
                "example_code": '''from typing import Annotated

from fastapi import Depends, FastAPI, Header

app = FastAPI(title="依赖注入示例")

CALLS = {"pagination": 0, "db": 0}


def pagination(page: int = 1, size: int = 20) -> dict:
    CALLS["pagination"] += 1
    return {"page": page, "size": size, "offset": (page - 1) * size}


def current_user(x_token: Annotated[str | None, Header()] = None) -> dict:
    return {"id": 1, "name": "lisi", "token": x_token}


def get_db():
    CALLS["db"] += 1
    db = {"connected": True}
    try:
        yield db
    finally:
        db["connected"] = False


@app.get("/tasks")
def list_tasks(
    pager: Annotated[dict, Depends(pagination)],
    user: Annotated[dict, Depends(current_user)],
    db: Annotated[dict, Depends(get_db)],
) -> dict:
    return {"pager": pager, "user": user["name"], "db_connected": db["connected"]}


@app.get("/stats")
def stats(pager: Annotated[dict, Depends(pagination)]) -> dict:
    return {"page": pager["page"], "calls": CALLS["pagination"]}''',
                "code_lines": """1. `pagination` 是普通函数，参数就是查询参数，返回值会被注入接口。
2. `CALLS` 计数器用来观察依赖被执行的次数（真实项目里换成日志或指标）。
3. `current_user` 演示依赖里也能声明参数：它自己从请求头取 `x-token`。
4. `get_db` 用 `yield`：`yield` 前准备资源，`finally` 里释放，异常路径也会执行。
5. 接口签名用 `Annotated[dict, Depends(...)]`，一眼能看出「这个参数来自依赖」。
6. `db["connected"]` 在接口执行期间为 True，说明清理发生在响应之后。
7. `/stats` 也用了 `pagination`，但它是另一个请求，计数会再加一——缓存只在单次请求内有效。""",
                "output": """curl -H "x-token: abc" "http://127.0.0.1:8000/tasks?page=2&size=10"
{"pager":{"page":2,"size":10,"offset":10},"user":"lisi","db_connected":true}

curl http://127.0.0.1:8000/stats?page=3
{"page":3,"calls":1}

# 说明：同一次请求内若两个参数依赖同一个函数，该函数只会执行一次；
# 换一个请求会重新执行，计数继续累加。""",
                "mistakes": """- 在依赖里自己 `print` 或写日志来「确认执行次数」，被缓存误导。
- `yield` 依赖里把清理写在 `yield` 之后但没放进 `finally`，异常时资源泄漏。
- 依赖函数名与接口参数名相同导致覆盖，实际拿到的是普通参数。
- 把 `Depends` 写在默认值位置却忘了 `Annotated`，类型提示丢失。
- 在依赖里吞掉异常（`try/except: pass`），接口拿到半初始化的资源。""",
                "error_analysis": """`422 missing` 且指向依赖里的查询参数
—— 依赖声明的参数同样参与校验，缺必填参数会拦在依赖层。

`RuntimeError: generator didn't yield`
—— `yield` 依赖没有真正 `yield`（比如写在了 if 分支里）。

接口始终拿到 `None`
—— 依赖函数没写 return（或返回值被覆盖）。""",
                "beginner_practice": """1. 新增依赖 `require_token`：请求头缺 `x-token` 时抛 401，有则返回用户。
2. 把 `pagination` 的 `size` 上限设为 100，确认 422 生效。""",
                "advanced_practice": """把「数据库会话」改成依赖：用 `yield` 提供会话，正常结束时提交、异常时回滚。
说明为什么提交/回滚要放在依赖层而不是每个接口里，并指出这样做的一个局限。""",
                "quiz_note": "本节 6 道题：2 道基础理解（Depends 作用、yield 清理）+ 2 道代码阅读（读缓存、读依赖参数）+ 2 道应用练习（补 401 依赖、改 size 上限）。",
                "summary": """`Depends` 把横切逻辑抽成可复用单元，接口只声明需要什么。
同一请求内同一依赖只执行一次；换请求会重新执行。
`yield` 依赖负责准备与清理，清理必须写在 `finally` 里。""",
                "next_lesson": "下一节把这些依赖按资源拆进多个文件：APIRouter 与 prefix/tags。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-07-01",
                        "name": "Depends 依赖注入与 yield 释放",
                        "goal": "能声明依赖、组合依赖，并用 yield 管理资源生命周期。",
                        "minutes": 50,
                        "criteria": "能写出一个带清理逻辑的 yield 依赖，并解释依赖缓存的边界。",
                        "requires": ["fastapi-backend-06-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-07-01-1",
                        "kp": 0,
                        "title": "401 令牌依赖",
                        "description": "写 `require_token` 依赖：缺少 `x-token` 时返回 401，有值时返回 `{\"token\": ...}`，并在两个接口上使用。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''from fastapi import Header, HTTPException


def require_token(x_token: Annotated[str | None, Header()] = None) -> dict:
    if not x_token:
        raise HTTPException(status_code=401, detail="缺少访问令牌")
    return {"token": x_token}


@app.get("/me")
def me(user: Annotated[dict, Depends(require_token)]) -> dict:
    return user''',
                        "explanation": "依赖里抛 HTTPException 与接口里抛效果一致；两个接口复用同一份判断，避免各写一遍。",
                    },
                    {
                        "code": "fa-ex-07-01-2",
                        "kp": 0,
                        "title": "依赖缓存的边界",
                        "description": "同一次请求里两个参数都依赖 `pagination`，函数会执行几次？换成两次请求呢？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''同一请求内执行 1 次（结果被缓存，两个参数共享同一对象）；
两次请求各执行 1 次，共 2 次——缓存的作用域是单次请求，不是进程。''',
                        "explanation": "理解这一点才能正确放置「每次请求都要新建」的资源（如数据库会话）。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-07-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`Depends` 的核心作用是？",
                        "options": [
                            ("A", "把可复用的准备逻辑注入接口参数"),
                            ("B", "自动生成数据库表"),
                            ("C", "替代 Pydantic 校验"),
                            ("D", "控制路由匹配顺序"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "依赖负责「准备接口需要的东西」，校验仍由参数与模型完成。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-07-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 yield 依赖，正确的说法有？（多选）",
                        "options": [
                            ("A", "yield 之前是准备逻辑"),
                            ("B", "清理逻辑应放在 finally 中"),
                            ("C", "接口抛异常时清理逻辑不会执行"),
                            ("D", "适合管理数据库会话、文件句柄等资源"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "`finally` 保证异常路径也执行清理，C 恰好说反了。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-07-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "请求 `/tasks?page=2&size=10` 时返回的 `offset` 是？",
                        "options": [("A", "2"), ("B", "10"), ("C", "20"), ("D", "1")],
                        "answer": {"value": "B"},
                        "explanation": "`(2 - 1) * 10 = 10`，这正是 SQL 里 OFFSET 要用的值。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-07-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "两个接口共用一个依赖函数时，第二次请求不会重新执行该依赖。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "缓存只在单次请求内生效，每次新请求都会重新执行依赖。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-07-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全签名，使 `user` 来自 `require_token` 依赖。横线处应填什么？\n\n```python\ndef me(____) -> dict:\n    return user\n```",
                        "options": [
                            ("A", "user: Annotated[dict, Depends(require_token)]"),
                            ("B", "user = require_token()"),
                            ("C", "user: dict = Depends"),
                            ("D", "Depends(require_token)"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "依赖要通过注解声明，框架才知道在调用前执行它。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-07-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么把「会话提交/回滚」放进依赖层，而不是每个接口末尾各写一次？",
                        "answer": {"value": "① 一致性：所有接口走同一套提交/回滚逻辑，不会漏写；② 异常安全：异常路径由 finally 统一回滚，避免半成功写入；③ 可测试：测试里可整体替换依赖，不碰真实数据库。局限是「一个请求一个事务」的粒度较粗，跨多事务的复杂业务仍需在服务层显式控制。"},
                        "explanation": "答案要覆盖一致性、异常安全、可测试三点，并指出粒度过粗这个真实局限。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "fastapi-backend-08",
        "title": "路由模块化",
        "description": "一个文件写不下所有接口时，就该拆路由了。",
        "order_index": 8,
        "lessons": [
            {
                "code": "fastapi-backend-08-lesson-01",
                "objectives": """1. 会用 `APIRouter` 按资源拆分路由；
2. 会用 `include_router` 统一挂载并加前缀；
3. 会用 `prefix` 与 `tags` 让文档分组清晰；
4. 能规划 `/v1` 版本前缀与模块边界。""",
                "why_learn": """接口超过二十个，`main.py` 会变成几百行的「万能文件」：改任务接口要滚动过用户接口，冲突不断。
按资源拆 router 之后，每个文件对应一个资源，冲突面小，也方便以后按模块拆分服务。""",
                "concepts": """**APIRouter**：轻量路由器，用法与 `FastAPI` 一致，可单独声明路由与依赖。
**include_router**：把 router 挂到应用上，可再加一层 `prefix`。
**tags**：文档分组标签，同一 router 的路由会归到一组。
**路径拼接**：`include_router` 的 prefix + router 的 prefix + 路由路径。
**空路径**：`@router.get("")` 表示「就是前缀本身」。""",
                "plain": """APIRouter 像把一本厚手册拆成分册：任务一册、用户一册。
`include_router` 是把分册装进同一个封套，封套上再写「第一版」（`/v1`）。
分册的好处是各写各的，谁也不会翻错页；坏处是得记住封套上的编号规则，否则路径会拼出 `/v1/tasks/tasks`。""",
                "syntax": """**API 说明**

```python
router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("")            # 最终路径 = include 的 prefix + /tasks
def list_tasks(): ...

app.include_router(router, prefix="/v1")
```

- `include_router(router, prefix="/v1", tags=["v1"])` 可再叠加前缀与标签。
- `dependencies=[Depends(...)]` 可给整个 router 统一加依赖（如鉴权）。
- `responses={404: {...}}` 可统一声明错误响应。""",
                "example_code": '''from fastapi import APIRouter, FastAPI

tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])
users_router = APIRouter(prefix="/users", tags=["users"])


@tasks_router.get("")
def list_tasks() -> list[dict]:
    return [{"id": 1, "title": "写周报"}]


@tasks_router.get("/{task_id}")
def get_task(task_id: int) -> dict:
    return {"id": task_id}


@users_router.get("/{user_id}")
def get_user(user_id: int) -> dict:
    return {"id": user_id, "name": "lisi"}


app = FastAPI(title="路由模块化示例")
app.include_router(tasks_router, prefix="/v1")
app.include_router(users_router, prefix="/v1")''',
                "code_lines": """1. 两个 `APIRouter` 各带 `prefix` 与 `tags`，相当于两个资源分册。
2. `@tasks_router.get("")` 的空字符串表示「前缀本身」，最终路径是 `/v1/tasks`。
3. router 上的路由写法与 `app` 完全一致，迁移成本低。
4. `include_router(..., prefix="/v1")` 在最外层再套一层版本前缀。
5. 最终路径由「include 前缀 + router 前缀 + 路由路径」拼接而成。
6. `tags` 会让 /docs 按 tasks、users 分组，接口一多也不乱。""",
                "output": """# 请求与响应
curl http://127.0.0.1:8000/v1/tasks
[{"id":1,"title":"写周报"}]

curl http://127.0.0.1:8000/v1/tasks/42
{"id":42}

curl http://127.0.0.1:8000/v1/users/7
{"id":7,"name":"lisi"}

# /docs 中按标签分组
tasks : GET /v1/tasks, GET /v1/tasks/{task_id}
users : GET /v1/users/{user_id}

# 常见拼接错误
GET /v1/tasks/tasks   -> 404（prefix 写重复了）""",
                "mistakes": """- router 的 `prefix="/tasks"` 与 `@router.get("/tasks")` 重复，拼出 `/v1/tasks/tasks`。
- `include_router` 时又加了一次相同前缀，路径翻倍。
- 所有 router 都用同一个 tag，文档里依然一大坨。
- 把 `app = FastAPI()` 写进每个 router 文件，启动多个互不相干的应用。
- 忘记 `include_router`，接口写好却访问不到。""",
                "error_analysis": """`404 Not Found` 但路由明明写了
—— 忘了 `app.include_router(...)`，或 prefix 拼错。

路径出现两段重复（`/v1/tasks/tasks`）
—— router 前缀与路由路径都写了 `/tasks`。路由路径应写 `""` 或 `"/{id}"`。

`AssertionError: Prefix and path cannot be both empty`
—— `@router.get("")` 且 router 没设前缀。给 router 一个 prefix，或把路径写成 `"/"`。""",
                "beginner_practice": """1. 新增 `tags_router`，提供 `/v1/tags` 的列表接口，并确认 /docs 多出一个分组。
2. 故意把 prefix 写重复，观察实际路径与 404 表现。""",
                "advanced_practice": """规划一个小项目的路由拆分：任务、用户、标签、健康检查四个 router，
说明各自前缀、标签、是否需要统一鉴权依赖，以及 `/v1` 升级到 `/v2` 时如何做到新旧并存。""",
                "quiz_note": "本节 6 道题：2 道基础理解（APIRouter 作用、路径拼接）+ 2 道代码阅读（读最终路径、读 404）+ 2 道应用练习（加 router、修重复前缀）。",
                "summary": """用 `APIRouter` 按资源拆文件，用 `include_router` 统一挂载。
最终路径 = include 前缀 + router 前缀 + 路由路径，任一层写重复都会出错。
`prefix` 管路径、`tags` 管文档分组，两者配合让接口规模可控。""",
                "next_lesson": "下一节处理错误：让所有异常都返回同一种结构的响应。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-08-01",
                        "name": "APIRouter 拆分与前缀标签",
                        "goal": "能按资源拆分路由并正确规划前缀与标签。",
                        "minutes": 50,
                        "criteria": "能拆出两个 router 并说清最终路径的拼接规则。",
                        "requires": ["fastapi-backend-07-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-08-01-1",
                        "kp": 0,
                        "title": "拆出标签 router",
                        "description": "新增 `tags_router`（前缀 /tags，标签 tags），提供列表与新建两个接口，挂到 /v1 下。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''tags_router = APIRouter(prefix="/tags", tags=["tags"])


@tags_router.get("")
def list_tags() -> list[dict]:
    return [{"id": 1, "name": "工作"}]


@tags_router.post("", status_code=201)
def create_tag(payload: dict) -> dict:
    return {"id": 2, "name": payload["name"]}


app.include_router(tags_router, prefix="/v1")''',
                        "explanation": "`""` 表示前缀本身，列表与新建都是 `/v1/tags`，靠方法区分。",
                    },
                    {
                        "code": "fa-ex-08-01-2",
                        "kp": 0,
                        "title": "修好重复前缀",
                        "description": "`APIRouter(prefix=\"/tasks\")` 配 `@router.get(\"/tasks\")` 会得到什么路径？怎么改？",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''会得到 /tasks/tasks（再叠加 include 的 /v1 就是 /v1/tasks/tasks）。
改法：路由路径写成 ""（列表）或 "/{task_id}"（单体），前缀只在一处声明。''',
                        "explanation": "记住「前缀只写一次」这条规则，能避免绝大多数路径错乱。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-08-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`APIRouter(prefix=\"/tasks\")` 中 `@router.get(\"\")` 的最终路径（include 无额外前缀）是？",
                        "options": [("A", "/tasks"), ("B", "/"), ("C", "/tasks/"), ("D", "空路径不可访问")],
                        "answer": {"value": "A"},
                        "explanation": "空字符串表示「就是前缀本身」，得到 `/tasks`。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-08-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "`include_router` 支持的常用参数有？（多选）",
                        "options": [
                            ("A", "prefix"),
                            ("B", "tags"),
                            ("C", "dependencies"),
                            ("D", "database_url"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "`database_url` 不是路由参数，数据库配置应由依赖或配置对象提供。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-08-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `GET /v1/users/7` 返回什么？",
                        "options": [
                            ("A", '{"id":7,"name":"lisi"}'),
                            ("B", '{"user_id":7}'),
                            ("C", "404"),
                            ("D", '{"id":1,"name":"lisi"}'),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`user_id` 为 7，返回体里 id 取的是传入值。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-08-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "同一个 router 的路由必须写在同一个文件里才能被 include。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "router 是对象，可以在多个文件里导入并继续装饰，只要最终 include 一次即可。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-08-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全挂载语句，使 router 挂在 /v1 下并在文档里显示为 tasks 组。横线处应填什么？\n\n```python\napp.____(tasks_router, prefix=\"/v1\")\n```",
                        "options": [
                            ("A", "include_router"),
                            ("B", "add_router"),
                            ("C", "register"),
                            ("D", "mount"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "FastAPI 的方法是 `include_router`；`mount` 用于挂载子应用（如静态文件）。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-08-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "要把 `/v1` 升级到 `/v2` 且不破坏老客户端，你会怎么组织路由？",
                        "answer": {"value": "保留 `/v1` 的 include 不动，同时准备一套 `/v2` router（可复用服务层，只改出入参），用两个 include 挂同一批服务。这样老客户端继续走 v1，新客户端走 v2，服务层只有一份逻辑；等 v1 调用量归零再下线，并提前在文档与响应头（如 Deprecation）中告知。"},
                        "explanation": "关键点是「服务层复用 + 版本只体现在路由与模型」，避免复制整个业务逻辑。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
