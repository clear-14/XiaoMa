"""Python 大模型 API 应用开发：第 10—12 章（JSON 结构化输出、Function Calling、Tool Calling）。"""

CHAPTERS: list[dict] = [
    {
        "code": "llm-api-10",
        "title": "JSON 结构化输出",
        "description": "把自然语言结果变成程序能直接用的数据。",
        "order_index": 10,
        "lessons": [
            {
                "code": "llm-api-10-lesson-01",
                "objectives": """1. 能用 `response_format` 开启 JSON 输出模式；
2. 能在 Prompt 里描述字段名、类型与取值范围；
3. 能区分「是 JSON」与「符合我的结构」两件事；
4. 能写出带默认值的解析函数，避免缺字段就崩。""",
                "why_learn": """用正则从自然语言里抠字段，是维护成本最高的做法之一。
让模型直接输出 JSON，能把「解析」变成「校验」，稳定性提升一个量级。""",
                "concepts": """**JSON 模式**：请求体加 `response_format={"type": "json_object"}`，要求输出合法 JSON。
**结构约定**：在 Prompt 里列出字段名、类型、取值范围与是否为必填。
**JSON 与 Schema 的差别**：前者只保证语法合法，后者才保证字段符合你的约定。
**解析容错**：`json.loads` 前先去掉可能的代码围栏；缺字段用默认值而不是抛异常。
**校验**：拿到字典后再用 Pydantic 或手写规则校验类型与枚举。""",
                "plain": """JSON 模式像给对方一张固定格式的表单：格子在哪里、填什么类型都规定好。
但表单填了不代表填对——可能把数字填成字符串、把日期写成「下周三」。
所以还要有一道校验：格式对不对，交给程序判断，而不是指望模型自觉。""",
                "syntax": """**API 说明**

```python
payload = {
    "model": model,
    "messages": messages,
    "response_format": {"type": "json_object"},
}
text = result["content"].strip()
data = json.loads(text)
```

- 开启 JSON 模式后，Prompt 里必须明确「输出一个 JSON 对象」，否则部分模型会返回空对象。
- 模型仍可能加上 ```json 围栏，解析前要剥离。
- 开启 JSON 模式不代表字段一定齐全，仍需校验。""",
                "example_code": '''import json

PROMPT = """从下面的招聘信息中抽取结构化字段，只输出一个 JSON 对象，不要解释。
字段要求：
- title: 字符串，职位名称
- city: 字符串，工作城市
- salary_min: 整数，单位千元/月；未提及填 null
- skills: 字符串数组，最多 5 项

招聘信息：{text}
"""

SAMPLE = "招聘 Python 后端工程师，工作地点杭州，月薪 20-30K，要求熟悉 FastAPI、SQLAlchemy 与 Docker。同时了解 Redis 者优先。"

RAW_OUTPUT = """```json
{"title": "Python 后端工程师", "city": "杭州", "salary_min": 20,
 "skills": ["FastAPI", "SQLAlchemy", "Docker", "Redis"]}
```"""


def strip_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\\n", 1)[1] if "\\n" in cleaned else ""
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    return cleaned.strip()


def parse(text: str) -> dict:
    data = json.loads(strip_fence(text))
    return {
        "title": data.get("title") or "",
        "city": data.get("city") or "",
        "salary_min": data.get("salary_min"),
        "skills": list(data.get("skills") or [])[:5],
    }


prompt = PROMPT.format(text=SAMPLE)
print("Prompt 长度:", len(prompt))
print("解析结果:", parse(RAW_OUTPUT))''',
                "code_lines": """1. Prompt 先声明「只输出一个 JSON 对象」，再逐字段写要求，顺序影响遵循度。
2. 字段要求写清类型与单位（整数、千元/月），否则模型会给「20-30K」这种区间。
3. 未提及的字段要求填 `null`，比让模型猜一个数字安全得多。
4. `strip_fence` 处理 ```json 围栏：这类包装在实际返回里非常常见。
5. `split("\\n", 1)` 只切第一行，避免把内容里的换行也切掉。
6. `parse` 对每个字段给默认值，缺字段时返回空值而不是抛 `KeyError`。
7. `[:5]` 把数组截断到约定上限，防止模型超量输出破坏下游逻辑。""",
                "output": """# 请求与响应
POST https://api.example-a.com/v1/chat/completions
{"model":"chat-large","response_format":{"type":"json_object"},
"messages":[{"role":"user","content":"…（抽取要求 + 招聘信息）…"}]}

HTTP/1.1 200 OK
{"choices":[{"message":{"role":"assistant","content":"{\\"title\\": \\"Python 后端工程师\\",
\\"city\\": \\"杭州\\", \\"salary_min\\": 20, \\"skills\\": [\\"FastAPI\\", \\"SQLAlchemy\\", \\"Docker\\", \\"Redis\\"]}"},
"finish_reason":"stop"}]}

# 程序输出
Prompt 长度: 236
解析结果: {'title': 'Python 后端工程师', 'city': '杭州', 'salary_min': 20, 'skills': ['FastAPI', 'SQLAlchemy', 'Docker', 'Redis']}""",
                "mistakes": """- 只写「返回 JSON」，不写字段名，结果结构每次都不一样。
- 以为开了 JSON 模式就不用校验，直接把结果写库。
- 用 `eval` 或 `ast.literal_eval` 解析返回，遇到 `null` 直接失败。
- 不剥离 ``` 围栏，`json.loads` 抛 `Expecting value`。
- 数字字段不限定类型，金额被输出成 `"20-30K"` 字符串。""",
                "error_analysis": """`json.decoder.JSONDecodeError: Expecting value: line 1 column 1`
—— 返回被围栏包裹或前面有解释文字。先剥离再解析，并把原始文本记进日志。

解析成功但字段是 `None`
—— 模型把「未提及」理解成省略字段，而不是输出 `null`。解析层用 `.get` 兜底。

数组字段永远只有一个元素
—— Prompt 里「最多 5 项」被理解成「只给 1 项」。改成「列出全部，最多 5 项，不足则全部列出」。""",
                "beginner_practice": """1. 把 `salary_min` 的约定改成「区间字符串」，观察解析代码要怎么改。
2. 给 `parse` 增加 `language` 字段的默认值 `"未知"`，并说明默认值该选什么。""",
                "advanced_practice": """用 Pydantic 定义抽取结果模型，把「手写 `.get` 兜底」换成模型校验，
并说明校验失败时应该返回什么（抛异常 / 返回部分结果 / 触发重试）。""",
                "quiz_note": "本节 6 道题：2 道基础理解（JSON 模式作用、JSON 与结构的差别）+ 2 道代码阅读（读 strip_fence、读默认值）+ 2 道应用练习（改字段、用 Pydantic 校验）。",
                "summary": """JSON 模式保证语法合法，字段结构仍需自己约定与校验。
Prompt 写清字段名、类型、单位与缺省值。
解析前剥围栏，解析后给默认值并截断超量数组。""",
                "next_lesson": "下一节处理「校验没过」：把错误回喂模型并限制重试。",
                "knowledge_points": [
                    {
                        "code": "llm-api-10-01",
                        "name": "JSON 模式与字段约束",
                        "goal": "能拿到结构稳定、字段可用的 JSON 输出。",
                        "minutes": 40,
                        "criteria": "能写出带字段约定的 Prompt、剥离围栏的解析函数与默认值兜底。",
                        "requires": ["llm-api-09-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-10-01-1",
                        "kp": 0,
                        "title": "补一层字段校验",
                        "description": "给 `parse` 增加校验：`salary_min` 必须是整数或 None，`skills` 必须是字符串列表，不符合时抛 `ValueError`。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def parse(text: str) -> dict:
    data = json.loads(strip_fence(text))
    salary = data.get("salary_min")
    if salary is not None and not isinstance(salary, int):
        raise ValueError(f"salary_min 必须是整数或 null，实际为 {type(salary).__name__}")
    skills = data.get("skills") or []
    if not isinstance(skills, list) or any(not isinstance(s, str) for s in skills):
        raise ValueError("skills 必须是字符串数组")
    return {
        "title": data.get("title") or "",
        "city": data.get("city") or "",
        "salary_min": salary,
        "skills": skills[:5],
    }''',
                        "explanation": "类型校验放在解析层，上层拿到的就是可信数据；失败时抛出明确原因，供重试时回喂模型。",
                    },
                    {
                        "code": "llm-ex-10-01-2",
                        "kp": 0,
                        "title": "为什么不用正则",
                        "description": "比较「正则抠字段」与「JSON 输出 + 校验」两种方案的三点差异。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 稳定性：正则依赖固定措辞，模型换个说法就失配；JSON 有明确分隔符与语法。
② 可维护：新增字段时，正则要重写并回归所有样本；JSON 只需加一条字段约定。
③ 可校验：JSON 能区分「字段缺失 / 类型错误 / 取值越界」，正则需要为每种错误单独设计。
代价：JSON 模式会多消耗一些输出 token，且开启后仍可能不遵守结构，需要校验与重试兜底。''',
                        "explanation": "结构化输出的核心收益是「错误可分类」，而正则往往只能给出「没匹配上」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-10-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "开启 JSON 输出模式应设置哪个请求字段？",
                        "options": [
                            ("A", "response_format={\"type\": \"json_object\"}"),
                            ("B", "format=\"json\""),
                            ("C", "output_type=\"json\""),
                            ("D", "mode=\"json\""),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "这是兼容协议里的字段；其他写法不属于协议，会被忽略。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-10-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "为什么「开了 JSON 模式」仍需要校验？（多选）",
                        "options": [
                            ("A", "只保证语法合法，不保证字段齐全"),
                            ("B", "类型可能与约定不符（如数字变成字符串）"),
                            ("C", "可能多输出数组元素"),
                            ("D", "JSON 模式会让模型变慢"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "模式约束的是语法，不是你的业务约定；速度与正确性是两件事。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-10-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`strip_fence` 中 `split(\"\\n\", 1)` 只切第一刀的原因是？",
                        "options": [
                            ("A", "只去掉围栏那行，保留 JSON 内部的换行"),
                            ("B", "提高解析速度"),
                            ("C", "避免中文乱码"),
                            ("D", "兼容 Windows 换行"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "多切会把 JSON 内容也切碎；限制切分次数是处理围栏的标准做法。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-10-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "若模型返回的 JSON 缺少 `salary_min` 字段，`parse` 的结果是？",
                        "options": [
                            ("A", "该字段为 None，其余字段正常"),
                            ("B", "抛 KeyError"),
                            ("C", "返回空字典"),
                            ("D", "抛 JSONDecodeError"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "用的是 `data.get`，缺字段返回 None，与「未提及填 null」语义一致。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-10-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全解析前的围栏剥离：判断文本是否以三个反引号开头。横线处应填什么？\n\n```python\nif cleaned.____(\"```\"):\n    cleaned = cleaned.split(\"\\n\", 1)[1]\n```",
                        "options": [("A", "startswith"), ("B", "endswith"), ("C", "find"), ("D", "count")],
                        "answer": {"value": "A"},
                        "explanation": "围栏在开头，用 `startswith`；用 `find` 会把内容里出现的反引号也当围栏。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-10-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "上游要求「抽取结果直接写库」。你会怎么设计这条链路才不至于把脏数据写进去？",
                        "answer": {"value": "分四层：① 输出层：JSON 模式 + 字段约定，尽量让模型一次给对；② 解析层：剥围栏、`json.loads`、缺字段给默认值；③ 校验层：用 Pydantic 校验类型、长度、枚举，失败时记录原始输出；④ 落库层：只写校验通过的数据，失败的进入「待人工处理」表并带原始输出与错误原因。另外加一条兜底：写库前对唯一键做去重，避免重试导致重复写入。"},
                        "explanation": "关键是「校验不通过的不要硬写」，并把失败样本保留下来用于优化 Prompt。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-10-lesson-02",
                "objectives": """1. 能用校验错误信息构造「修复请求」；
2. 能设置重试上限并区分「可修复」与「不可修复」错误；
3. 能避免修复循环带来的成本失控；
4. 能记录失败样本用于改进 Prompt。""",
                "why_learn": """即使结构约定得很细，模型仍会偶尔给出不合规的结果。
一次重试能挽回大部分问题，但无限重试会把成本和延迟一起放大。""",
                "concepts": """**修复请求**：把「原始输出 + 校验错误」一起发回，让模型只做修正。
**重试上限**：通常 1—2 次；超过就降级（返回错误 / 用默认值 / 转人工）。
**可修复性**：格式错、字段缺失可修复；内容本身不存在（如原文没有薪资）不可修复。
**温度**：修复时用更低温度，减少再次跑偏。
**留档**：把失败样本存下来，用于补示例、改 Prompt。""",
                "plain": """修复像改作业：把「第三题漏了单位」指出来，学生就知道怎么改。
但如果连续两次都改不对，继续让他改只是浪费时间——这时候该换讲法（改 Prompt）或人工接手。
关键是每次都要说清错在哪，而不是只说「重写一遍」。""",
                "syntax": """**API 说明（修复循环骨架）**

```python
for attempt in range(MAX_RETRY + 1):
    text = call_model(messages)
    try:
        return validate(parse(text))
    except ValidationError as exc:
        if attempt == MAX_RETRY:
            raise
        messages = messages + [
            {"role": "assistant", "content": text},
            {"role": "user", "content": f"上面的输出不符合要求：{exc}。请只输出修正后的 JSON。"},
        ]
```

- 把错误的**原文**带回去，模型才知道改什么。
- 修复轮次计入同一会话，避免上下文丢失。
- 达到上限后抛错或降级，不要静默返回脏数据。""",
                "example_code": '''import json


def validate(data: dict) -> dict:
    if not data.get("title"):
        raise ValueError("title 不能为空")
    salary = data.get("salary_min")
    if salary is not None and not isinstance(salary, int):
        raise ValueError("salary_min 必须是整数或 null")
    return data


def fake_model(messages: list[dict]) -> str:
    """离线桩：第一次故意给错类型，看到错误提示后改对。"""
    last = messages[-1]["content"]
    if "salary_min 必须是整数" in last:
        return '{"title": "后端工程师", "salary_min": 20}'
    return '{"title": "后端工程师", "salary_min": "20-30K"}'


def extract_with_repair(messages: list[dict], max_retry: int = 2) -> tuple[dict, int]:
    attempts = 0
    for attempt in range(max_retry + 1):
        attempts += 1
        text = fake_model(messages)
        try:
            return validate(json.loads(text)), attempts
        except (ValueError, json.JSONDecodeError) as exc:
            if attempt == max_retry:
                raise
            messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"输出不符合要求：{exc}。请只输出修正后的 JSON。"},
            ]
    raise RuntimeError("unreachable")


base = [{"role": "user", "content": "抽取：招聘后端工程师，月薪 20-30K"}]
try:
    data, used = extract_with_repair(base)
    print("成功，重试次数:", used - 1)
    print("结果:", data)
except ValueError as exc:
    print("最终失败:", exc)''',
                "code_lines": """1. `validate` 只做一件事：把「业务约定」写成可执行的检查，失败即抛带原因的异常。
2. 类型检查用 `isinstance(salary, int)`，注意 `True` 也是 int，真实项目要额外排除布尔。
3. `fake_model` 模拟「第一次错、看到错误提示后改对」的真实修复过程。
4. 循环上限 `max_retry + 1` 表示「首次 + N 次修复」，避免写成无限循环。
5. 失败时把模型原输出作为 assistant 消息追加，模型才能看到自己错在哪。
6. 修复提示只要求「输出修正后的 JSON」，不重述全部要求，节省 token。
7. 达到上限后抛异常而不是返回脏数据，让上层决定降级方式。""",
                "output": """# 第一次输出（模拟）
{"title": "后端工程师", "salary_min": "20-30K"}

# 校验失败信息
输出不符合要求：salary_min 必须是整数或 null。请只输出修正后的 JSON。

# 第二次输出
{"title": "后端工程师", "salary_min": 20}

# 程序输出
成功，重试次数: 1
结果: {'title': '后端工程师', 'salary_min': 20}""",
                "mistakes": """- 修复时只说「重试一次」，不告诉模型错在哪，结果大概率还错。
- 无上限重试，遇到模型理解偏差时死循环烧钱。
- 把「原文里没有的信息」当成可修复错误，反复让模型猜。
- 修复用原温度甚至更高温度，越改越偏。
- 失败样本不留档，同一个错反复出现在线上。""",
                "error_analysis": """连续三次都是同一个校验错误
—— 说明 Prompt 的字段约定本身有问题（如单位、类型没写清），改 Prompt 而不是继续重试。

重试后成本翻了三倍
—— 每次修复都把完整历史重发。可只发「原始输出 + 错误 + 目标结构」，减少输入。

修复后字段对了但内容变了
—— 修复提示过宽，模型顺手改了其他字段。要求「只修改不符合的字段，其余原样保留」。""",
                "beginner_practice": """1. 把 `max_retry` 设为 0，观察失败时的异常与提示信息。
2. 在修复提示里加入「其余字段必须原样保留」，说明它防的是什么。""",
                "advanced_practice": """设计一套失败率监控：按「首次成功率 / 一次修复成功率 / 最终失败率」三个指标统计，
并说明哪个指标最能反映 Prompt 质量。""",
                "quiz_note": "本节 6 道题：2 道基础理解（修复请求要素、重试上限）+ 2 道代码阅读（读循环、读追加消息）+ 2 道应用练习（关重试、加监控）。",
                "summary": """修复必须带「原输出 + 具体错误」，否则等于盲目重试。
重试 1—2 次封顶，超限就降级而不是返回脏数据。
同一错误反复出现，说明该改 Prompt，不该继续重试。""",
                "next_lesson": "下一章让模型调用你写好的函数：Function Calling。",
                "knowledge_points": [
                    {
                        "code": "llm-api-10-02",
                        "name": "校验失败的修复循环",
                        "goal": "能用错误回喂与重试上限把结构化输出修到可用。",
                        "minutes": 40,
                        "criteria": "能写出带上限的修复循环，并说明哪些错误可修复、哪些应改 Prompt。",
                        "requires": ["llm-api-10-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-10-02-1",
                        "kp": 0,
                        "title": "只改错的那一个字段",
                        "description": "修改修复提示，要求模型「只修改校验报错的字段，其余原样返回」，并说明收益。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''fix_prompt = (
    f"输出不符合要求：{exc}。"
    "请只修改报错的字段，其余字段与取值必须原样保留，只输出修正后的 JSON。"
)''',
                        "explanation": "限定修改范围能避免「修一个坏三个」，也减少输出 token。",
                    },
                    {
                        "code": "llm-ex-10-02-2",
                        "kp": 0,
                        "title": "可修复与不可修复",
                        "description": "判断以下错误哪些值得重试：① 输出带解释文字 ② 薪资字段原文没有 ③ 数组少了一项 ④ 日期格式不对。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 值得重试（剥离围栏/要求只输出 JSON 即可）；
② 不值得：原文确实没有该信息，重试只会让模型编造，应输出 null 或标记缺失；
③ 值得重试一次（要求「列出全部」），但仍要校验数量上限；
④ 值得重试（给出明确格式示例，如 YYYY-MM-DD）。''',
                        "explanation": "判断标准是「信息是否存在于输入」：不存在就重试只会诱导幻觉。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-10-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "修复请求中必须包含什么，模型才知道怎么改？",
                        "options": [
                            ("A", "模型上一次的原始输出与具体校验错误"),
                            ("B", "仅一句「请重试」"),
                            ("C", "更长的 Prompt"),
                            ("D", "更高的温度"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "没有出错原文与原因，模型只能盲猜，重试成功率极低。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-10-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "如何控制修复循环的成本？（多选）",
                        "options": [
                            ("A", "设置重试上限"),
                            ("B", "修复时只发必要信息（原输出 + 错误 + 目标结构）"),
                            ("C", "同类错误重复出现时改 Prompt 而不是继续重试"),
                            ("D", "把温度调高以获得更多候选"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "调高温度会让输出更不稳定，与「修到合规」的目标相反。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-10-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`for attempt in range(max_retry + 1)` 在 `max_retry=2` 时最多调用几次模型？",
                        "options": [("A", "3 次"), ("B", "2 次"), ("C", "1 次"), ("D", "4 次"),],
                        "answer": {"value": "A"},
                        "explanation": "`+1` 表示首次调用，之后最多两次修复，共 3 次。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-10-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中把模型原始输出追加为 `assistant` 消息，而不是放进 `user`，原因是？",
                        "options": [
                            ("A", "那确实是模型自己说过的话，角色要如实反映"),
                            ("B", "可以减少 token"),
                            ("C", "user 消息不能包含 JSON"),
                            ("D", "为了避免触发审核"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "把模型输出伪装成用户输入会让模型误以为「用户刚给了这段 JSON」，影响对任务的理解。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-10-02-5",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "如果原文里没有薪资信息，可以让模型反复重试直到给出一个数字。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "这是在逼迫模型编造；正确做法是允许 null 或标记缺失字段。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-10-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "请设计三个指标来判断「修复机制是否真的有用」。",
                        "answer": {"value": "① 首次成功率：不重试就合规的比例，反映 Prompt 与 JSON 模式的基本质量；② 修复成功率（条件成功率）：需要重试的样本中最终修好的比例，反映错误回喂是否有效；③ 最终失败率与失败样本分布：按错误类型（缺字段/类型错/多余文字）分类，指导下一步改 Prompt 还是改校验规则。再加一个成本指标：平均每次成功抽取的模型调用次数，用于评估修复带来的额外开销。"},
                        "explanation": "只看「最终成功率」会掩盖首次质量的下降；分层指标才能定位问题在哪一环。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "llm-api-11",
        "title": "Function Calling",
        "description": "让模型申请调用你写好的函数，而不是自己编数。",
        "order_index": 11,
        "lessons": [
            {
                "code": "llm-api-11-lesson-01",
                "objectives": """1. 能用 JSON Schema 声明一个函数的名称、用途与入参；
2. 能读懂响应里的 `tool_calls` 结构；
3. 能区分「模型调用函数」与「模型编造结果」；
4. 能解释 `arguments` 为什么是字符串而不是对象。""",
                "why_learn": """问「现在几点」，模型只能编一个时间。
函数调用让它把「我不知道」变成「请调用这个函数」——事实由你的代码提供，模型只负责决定调什么。""",
                "concepts": """**函数声明**：`tools` 里描述函数名、用途、参数 schema，模型据此判断该不该调。
**`tool_calls`**：模型返回的「调用申请」，包含 `id`、函数名与 `arguments`（JSON 字符串）。
**不执行**：模型永远不会真的执行你的函数，执行是你的事。
**`arguments` 是字符串**：需要自己 `json.loads`，且可能不合 schema。
**结束原因**：此时 `finish_reason` 通常是 `tool_calls`。""",
                "plain": """函数调用像餐厅点菜：客人（模型）说「来一份宫保鸡丁」（调用申请），
厨房（你的代码）才真正去做菜，再把菜端回去。
客人不会自己进厨房炒菜——它只是准确地告诉你它要什么。""",
                "syntax": """**API 说明**

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的实时天气，仅支持中国大陆城市",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名，如杭州"}},
            "required": ["city"],
        },
    },
}]
payload = {"model": model, "messages": messages, "tools": tools}
# 封装成客户端方法时通常写成 chat(messages, tools=TOOLS)
```

- `description` 决定模型「什么时候该调」，写得越具体越准。
- `required` 列出必填参数；缺失时模型可能给出不完整调用。
- 返回值在 `choices[0].message.tool_calls`，可能一次多个。""",
                "example_code": '''import json

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询中国城市当前天气。仅用于询问实时天气，不用于历史天气或气候趋势。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市中文名，如 杭州"},
                    "unit": {"type": "string", "enum": ["c", "f"], "description": "温度单位"},
                },
                "required": ["city"],
            },
        },
    }
]

RESPONSE = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_001",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"city": "杭州", "unit": "c"}',
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ]
}

message = RESPONSE["choices"][0]["message"]
print("结束原因:", RESPONSE["choices"][0]["finish_reason"])
print("是否要求调用:", bool(message.get("tool_calls")))
for call in message["tool_calls"]:
    name = call["function"]["name"]
    args = json.loads(call["function"]["arguments"])
    print("函数:", name, "参数:", args, "调用ID:", call["id"])''',
                "code_lines": """1. `TOOLS` 是声明，不是实现：只告诉模型「有这个能力」，不含任何代码。
2. `description` 明确「什么时候用、什么时候不用」，这是提升选择准确率的关键。
3. `enum` 限制单位取值，避免模型给「摄氏度」「C 度」这类自由文本。
4. `required` 只放城市，单位可缺省——必填项越少越不容易出错。
5. `content` 为 `None`、`finish_reason` 为 `tool_calls` 是这一轮的典型特征。
6. `arguments` 是 JSON **字符串**，必须 `json.loads` 才能拿到参数。
7. 打印 `id`，因为回填结果时要用它把「结果」对回「申请」。""",
                "output": """# 请求与响应
POST https://api.example-a.com/v1/chat/completions
{"model":"chat-large","messages":[{"role":"user","content":"杭州现在多少度？"}],
"tools":[{"type":"function","function":{"name":"get_weather",…}}]}

HTTP/1.1 200 OK
{"choices":[{"message":{"role":"assistant","content":null,
"tool_calls":[{"id":"call_001","type":"function",
"function":{"name":"get_weather","arguments":"{\\"city\\": \\"杭州\\", \\"unit\\": \\"c\\"}"}}]},
"finish_reason":"tool_calls"}]}

# 程序输出
结束原因: tool_calls
是否要求调用: True
函数: get_weather 参数: {'city': '杭州', 'unit': 'c'} 调用ID: call_001""",
                "mistakes": """- 以为模型会执行函数，结果发现只是返回了一个「申请」。
- 把 `arguments` 当字典直接用，报 `'str' object has no attribute 'get'`。
- `description` 写成「查询天气」，模型在问历史天气时也调用。
- 参数不加 `enum`/`required`，模型给出五花八门的取值。
- 一次只处理第一个 `tool_calls`，漏掉并行调用。""",
                "error_analysis": """`TypeError: string indices must be integers`
—— 对 `arguments` 直接下标取值。先 `json.loads`。

模型不调用函数，直接回答
—— `description` 没写清用途，或用户问题不需要外部数据。优化描述，并在 system 里说明「涉及实时数据必须调用工具」。

`finish_reason` 是 `stop` 但内容为空
—— 少数实现会在工具调用轮返回空内容，属于正常，按 `tool_calls` 分支处理即可。""",
                "beginner_practice": """1. 再加一个 `get_time` 工具声明，只描述用途不写实现。
2. 把 `arguments` 改成非法 JSON，观察 `json.loads` 的报错信息。""",
                "advanced_practice": """为一个「查询订单」的函数写声明：说明参数该怎么设计（订单号 vs 手机号）、
如何避免模型传入不存在的参数，以及 `description` 里应该写清哪些边界。""",
                "quiz_note": "本节 6 道题：2 道基础理解（是否执行、arguments 类型）+ 2 道代码阅读（读响应结构、读 json.loads）+ 2 道应用练习（加工具、设计声明）。",
                "summary": """工具声明只描述能力，执行永远在自己的代码里。
`tool_calls[].function.arguments` 是 JSON 字符串，必须解析。
`description` 与参数约束决定模型选得对不对。""",
                "next_lesson": "下一节把执行结果回填，让模型基于真实数据继续回答。",
                "knowledge_points": [
                    {
                        "code": "llm-api-11-01",
                        "name": "函数声明与 tool_calls 解析",
                        "goal": "能声明函数并正确解析模型返回的调用申请。",
                        "minutes": 40,
                        "criteria": "能写出带 required/enum 的工具声明，并解析多个 tool_calls 的名称、参数与 id。",
                        "requires": ["llm-api-10-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-11-01-1",
                        "kp": 0,
                        "title": "补一个工具声明",
                        "description": "为「按订单号查询物流状态」写工具声明：参数只需订单号，且要在描述里说明「仅当用户提供了订单号时调用」。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''TOOLS.append({
    "type": "function",
    "function": {
        "name": "get_logistics",
        "description": "按订单号查询物流状态。仅当用户明确提供订单号时调用；未提供时先追问订单号。",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单号，纯数字，长度 12—20"},
            },
            "required": ["order_id"],
        },
    },
})''',
                        "explanation": "把「没有订单号时先追问」写进描述，能减少模型编造订单号的情况——这是描述比参数更重要的典型场景。",
                    },
                    {
                        "code": "llm-ex-11-01-2",
                        "kp": 0,
                        "title": "为什么是字符串",
                        "description": "为什么协议把 `arguments` 设计成 JSON 字符串，而不是直接给对象？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 渐进生成：流式输出时参数字符是逐段产生的，字符串可以增量拼接，对象做不到「半截」；
② 宽松解析：字符串允许模型先给出近似结构，再由调用方决定严格解析还是容错；
③ 版本兼容：字符串内的 schema 可以独立演进，不影响外层消息结构。
代价是调用方必须显式解析并处理解析失败，这也是为什么参数校验不能省。''',
                        "explanation": "设计动因来自流式与兼容，理解这一点就能明白「为什么要自己 json.loads 并校验」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-11-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "模型返回 `tool_calls` 时，真正执行函数的是？",
                        "options": [
                            ("A", "你自己的代码"),
                            ("B", "模型服务端"),
                            ("C", "协议自动执行"),
                            ("D", "前端浏览器"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "模型只提出调用申请，执行与结果回填都由应用负责，这也是安全边界所在。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-11-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "提升模型选对工具的概率，可以做哪些事？（多选）",
                        "options": [
                            ("A", "把 description 写清用途与边界"),
                            ("B", "用 enum 限制参数取值"),
                            ("C", "只声明必需参数，减少必填项"),
                            ("D", "在 description 里写实现代码"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "描述是给模型看的说明书，塞实现代码只会浪费 token 并干扰判断。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-11-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `finish_reason` 为 `tool_calls`，说明这一轮？",
                        "options": [
                            ("A", "模型希望先调用工具，而不是直接回答"),
                            ("B", "回答被截断"),
                            ("C", "请求失败"),
                            ("D", "触发了内容审核"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "该取值表示本轮以工具调用结束，需要执行后把结果回填再请求一次。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-11-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "若 `message[\"tool_calls\"]` 有两个元素，示例里 `for` 循环会？",
                        "options": [
                            ("A", "逐个解析并打印两次"),
                            ("B", "只处理第一个"),
                            ("C", "报错"),
                            ("D", "合并成一个调用"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "循环覆盖全部调用，这正是支持并行工具调用的最小写法。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-11-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全代码，把参数字符串解析成字典。横线处应填什么？\n\n```python\nargs = ____(call[\"function\"][\"arguments\"])\n```",
                        "options": [("A", "json.loads"), ("B", "json.dumps"), ("C", "str"), ("D", "eval")],
                        "answer": {"value": "A"},
                        "explanation": "`arguments` 是 JSON 字符串，用 `json.loads`；`eval` 会执行任意代码，绝对不能用于模型输出。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-11-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "用户问「明天杭州会下雨吗」，模型没有调用天气工具，直接说「会」。问题出在哪，怎么改？",
                        "answer": {"value": "两个层面：① 声明层面：工具描述写得太窄（如只写「查询当前天气」），或 system 里没要求「涉及天气必须调用工具」；② 行为层面：缺少兜底校验——拿到回答时检查「本轮是否应有工具调用」，若用户问题含实时数据特征却没有 `tool_calls`，应强制重问并附上「请先调用工具获取数据」的指令。另外可以在 Prompt 里明确禁止编造天气，并给出去重试机制：最多一次纠正重试，仍不调用则降级为「暂时无法查询」。"},
                        "explanation": "既要改声明与规则，也要有运行时的「该调未调」检测，二者缺一都会漏。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-11-lesson-02",
                "objectives": """1. 能实现「声明 → 调用 → 回填 → 再推理」的完整闭环；
2. 能正确构造 `role=tool` 的结果消息并带上 `tool_call_id`；
3. 能处理函数内部的异常并把它变成可读的失败结果；
4. 能说明为什么不能把函数结果直接拼进 system。""",
                "why_learn": """只声明不执行，模型拿不到数据；执行后不回填，模型不知道发生了什么。
闭环才是函数调用的全部价值：真实数据进、可靠回答出。""",
                "concepts": """**回填消息**：`{"role": "tool", "tool_call_id": <id>, "content": "<结果>"}`。
**必须配对**：每个 `tool_calls` 的 `id` 都要有一条对应结果，否则接口报错。
**结果格式**：`content` 是字符串，通常放 JSON 文本。
**异常处理**：函数抛错时回填 `{"error": "..."}`，让模型据此解释，而不是让整个请求失败。
**再次请求**：回填后带上完整消息历史再调一次，模型据此生成最终回答。""",
                "plain": """回填像把查到的资料递给答题的人：他知道刚才要了什么、现在拿到了什么，才能继续作答。
资料递错人（`tool_call_id` 对不上）会直接被退回来。
如果这项资料查不到，也该如实告诉他「没查到」，而不是假装没这回事。""",
                "syntax": """**API 说明**

```python
messages.append(message)                                   # 模型的调用申请
for call in message["tool_calls"]:
    result = run_tool(call)
    messages.append({
        "role": "tool",
        "tool_call_id": call["id"],
        "content": json.dumps(result, ensure_ascii=False),
    })
final = client.chat(messages)                              # 带上工具结果再问一次
```

- 必须先把 assistant 的 `tool_calls` 消息追加进去，再追加 tool 消息。
- `content` 必须是字符串，字典要 `json.dumps`。
- 每个 `id` 都要有结果，不能只回填一个。""",
                "example_code": '''import json


def get_weather(city: str, unit: str = "c") -> dict:
    data = {"city": city, "temp": 18, "condition": "多云"}
    if unit == "f":
        data["temp"] = round(data["temp"] * 9 / 5 + 32)
    return data


REGISTRY = {"get_weather": get_weather}


def run_tool(call: dict) -> dict:
    name = call["function"]["name"]
    handler = REGISTRY.get(name)
    if handler is None:
        return {"error": f"未知工具：{name}"}
    try:
        args = json.loads(call["function"]["arguments"] or "{}")
        return handler(**args)
    except TypeError as exc:
        return {"error": f"参数不匹配：{exc}"}
    except Exception as exc:  # 工具内部异常不能打断整个对话
        return {"error": f"工具执行失败：{exc}"}


def fake_chat(messages: list[dict]) -> dict:
    """离线桩：第一次请求工具，看到工具结果后给最终回答。"""
    if any(item["role"] == "tool" for item in messages):
        payload = json.loads(messages[-1]["content"])
        content = f"{payload['city']}现在 {payload['temp']} 度，{payload['condition']}。"
        return {"content": content, "tool_calls": None}
    return {
        "content": None,
        "tool_calls": [
            {
                "id": "call_001",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"city": "杭州"}'},
            }
        ],
    }


messages = [{"role": "user", "content": "杭州现在多少度？"}]
first = fake_chat(messages)
messages.append({"role": "assistant", "content": first["content"], "tool_calls": first["tool_calls"]})

for call in first["tool_calls"]:
    result = run_tool(call)
    print("工具结果:", result)
    messages.append(
        {
            "role": "tool",
            "tool_call_id": call["id"],
            "content": json.dumps(result, ensure_ascii=False),
        }
    )

final = fake_chat(messages)
print("最终回答:", final["content"])''',
                "code_lines": """1. `REGISTRY` 用名字映射函数，模型只能调用白名单里的工具，这是安全底线。
2. 未知工具返回错误结果而不是抛异常，让模型能解释「这个能力不存在」。
3. `arguments or "{}"` 兜住空字符串，避免 `json.loads("")` 报错。
4. `TypeError` 单独捕获：参数不匹配是最常见错误，提示要具体。
5. 兜底 `Exception` 把任何工具异常转成错误结果，避免整个对话中断。
6. 回填消息必须带 `tool_call_id`，与申请一一对应，否则接口会拒绝。
7. 回填后再请求一次，模型才能基于真实数据生成最终回答。""",
                "output": """# 第一轮响应（模型要求调用）
{"choices":[{"message":{"tool_calls":[{"id":"call_001","function":
{"name":"get_weather","arguments":"{\\"city\\": \\"杭州\\"}"}}]},"finish_reason":"tool_calls"}]}

# 回填的消息（节选）
{"role": "tool", "tool_call_id": "call_001", "content": "{\\"city\\": \\"杭州\\", \\"temp\\": 18, \\"condition\\": \\"多云\\"}"}

# 程序输出
工具结果: {'city': '杭州', 'temp': 18, 'condition': '多云'}
最终回答: 杭州现在 18 度，多云。""",
                "mistakes": """- 忘记追加 assistant 的 `tool_calls` 消息，直接只发 tool 消息，接口报错。
- `content` 直接塞字典，序列化失败或变成 Python repr。
- 只回填第一个调用，其余 `id` 没有结果。
- 工具抛异常直接冒泡，整个请求 500，模型没有机会解释。
- 把工具结果拼进 system 消息，位置错乱且会污染规则。""",
                "error_analysis": """`400 An assistant message with 'tool_calls' must be followed by tool messages`
—— 缺少 assistant 消息或漏了某个 `id` 的结果。按 `id` 逐个回填。

`json.decoder.JSONDecodeError` 在工具参数处
—— 模型给了不完整 JSON。捕获后回填 `{"error": "参数解析失败"}`，让它重试一次。

回答里出现「根据工具返回的 undefined」
—— 工具返回了 `None` 或空字典。约定返回结构并保证必有字段。""",
                "beginner_practice": """1. 给 `REGISTRY` 加一个 `get_time` 函数并在桩里调用，观察两轮闭环。
2. 故意传一个未知工具名，确认返回的是错误结果而不是异常。""",
                "advanced_practice": """设计一个工具执行器：支持超时（如 3 秒）、结果截断（超长文本只回前 2000 字）、
以及「危险工具需要人工确认」的闸门，并说明每条限制防的是什么问题。""",
                "quiz_note": "本节 6 道题：2 道基础理解（回填消息要素、为什么要再请求）+ 2 道代码阅读（读 REGISTRY、读异常分支）+ 2 道应用练习（加工具、设计执行器）。",
                "summary": """回填消息必须带 `tool_call_id`，且每个申请都要有结果。
工具异常转成错误结果回填，别让整个对话中断。
先追加 assistant 的调用消息，再追加 tool 结果，顺序不能反。""",
                "next_lesson": "下一章处理多个工具：怎么选、怎么防死循环。",
                "knowledge_points": [
                    {
                        "code": "llm-api-11-02",
                        "name": "工具执行与结果回填",
                        "goal": "能完成「调用 → 执行 → 回填 → 再推理」闭环。",
                        "minutes": 40,
                        "criteria": "能写出带白名单、异常兜底与 tool_call_id 配对的执行与回填逻辑。",
                        "requires": ["llm-api-11-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-11-02-1",
                        "kp": 0,
                        "title": "补上回填消息",
                        "description": "补全代码：把工具结果以 `tool` 角色回填，并带上调用 ID。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''messages.append({
    "role": "tool",
    "tool_call_id": call["id"],
    "content": json.dumps(result, ensure_ascii=False),
})''',
                        "explanation": "三个字段缺一不可：角色决定消息类型，`tool_call_id` 负责配对，`content` 必须是字符串。",
                    },
                    {
                        "code": "llm-ex-11-02-2",
                        "kp": 0,
                        "title": "工具超时怎么办",
                        "description": "某个工具（如外部 API）可能阻塞 30 秒，你会怎么处理，才能不让整轮对话卡死？",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''① 给工具设独立超时（如 3—5 秒），超时后回填 `{"error": "工具超时"}`；
② 工具调用与模型调用分别设超时预算，整体预算不超过用户体验上限；
③ 对慢工具改为异步：先返回「正在查询」，由前端轮询或推送结果；
④ 记录慢工具的 P95 耗时，必要时换数据源或加缓存。
关键是：超时必须变成一条可解释的工具结果，而不是让请求悬挂或 500。''',
                        "explanation": "函数调用的可靠性取决于「最慢的那个工具」，超时预算必须覆盖它。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-11-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "回填工具结果时，消息必须包含哪个字段来与调用配对？",
                        "options": [
                            ("A", "tool_call_id"),
                            ("B", "index"),
                            ("C", "model"),
                            ("D", "name"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "协议用 `tool_call_id` 把结果对回申请；缺了它接口无法判断这是哪次调用的结果。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-11-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "工具执行器应当具备哪些保护？（多选）",
                        "options": [
                            ("A", "只允许调用白名单内的工具"),
                            ("B", "捕获异常并转成错误结果"),
                            ("C", "对结果长度做截断"),
                            ("D", "允许模型直接修改工具实现"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "模型永远不能改代码或绕过白名单，这是函数调用的安全前提。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-11-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`run_tool` 中 `json.loads(call[\"function\"][\"arguments\"] or \"{}\")` 的 `or \"{}\"` 作用？",
                        "options": [
                            ("A", "参数为空字符串时给一个空对象，避免解析报错"),
                            ("B", "提供默认参数值"),
                            ("C", "提升解析速度"),
                            ("D", "防止注入"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "无参工具常返回空字符串或 null，直接 `json.loads` 会抛异常。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-11-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "若工具返回 `{\"error\": \"未找到城市\"}`，示例的最终回答会？",
                        "options": [
                            ("A", "因缺少 temp 字段而抛 KeyError（需要额外处理）"),
                            ("B", "自动重试工具"),
                            ("C", "返回空字符串"),
                            ("D", "返回错误结果本身"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "桩代码直接取 `payload['temp']`，说明「错误结果」也需要在最终生成阶段单独处理。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-11-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全回填消息的角色字段。横线处应填什么？\n\n```python\nmessages.append({\"role\": ____, \"tool_call_id\": call[\"id\"], \"content\": text})\n```",
                        "options": [("A", "\"tool\""), ("B", "\"assistant\""), ("C", "\"user\""), ("D", "\"system\"")],
                        "answer": {"value": "A"},
                        "explanation": "工具结果用 `tool` 角色；写成 user 会被模型当作用户输入，语义完全错位。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-11-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么函数调用的「执行」必须留在自己的服务端，而不能交给前端或模型？",
                        "answer": {"value": "① 权限：工具往往持有数据库或内部接口权限，暴露给前端等于公开；② 可信：模型输出不可信，参数可能被注入构造，必须在服务端校验后再执行；③ 审计：服务端可以记录谁在什么时候调了什么、返回了什么，便于追责与计费；④ 一致：前端版本不可控，逻辑放在服务端才能统一升级。结论：模型只提出申请，执行、校验与审计全部留在服务端。"},
                        "explanation": "函数调用把「模型输出」变成了「可执行动作」，这条链路必须按不可信输入来设计。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "llm-api-12",
        "title": "Tool Calling",
        "description": "多个工具时怎么选、怎么停、怎么不错。",
        "order_index": 12,
        "lessons": [
            {
                "code": "llm-api-12-lesson-01",
                "objectives": """1. 能在同一请求里声明多个工具并观察模型的选择；
2. 能通过「描述区分度」提升选择准确率；
3. 能处理「该调 A 却调了 B」的常见原因；
4. 能设计工具集合的粒度（合并还是拆分）。""",
                "why_learn": """两个工具都能查「订单」，模型就可能选错。
工具多了以后，选择准确率不取决于模型多强，而取决于你的描述写得多清楚。""",
                "concepts": """**选择依据**：只用 `name` + `description` + 参数 schema 判断。
**区分度**：描述要写「什么时候用我、什么时候别用我」。
**粒度**：一个工具做一件事；把「查订单」和「改订单」拆开，别做成一个 `manage_order`。
**重叠处理**：功能相近的工具要在描述里写明优先级或适用条件。
**验证**：用小样本集测「问题 → 期望工具」，量化选择准确率。""",
                "plain": """工具箱里两把看起来一样的螺丝刀，谁都会拿错。
解决办法不是训人，而是在手柄上写清楚「十字 / 一字」。
工具描述就是那把螺丝刀手柄上的字——写清楚，模型才不会拿错。""",
                "syntax": """**API 说明（多工具声明与选择校验）**

```python
TOOLS = [weather_tool, time_tool, order_tool]
payload = {"model": model, "messages": messages, "tools": TOOLS}

CASES = [("杭州天气怎么样", "get_weather"), ("现在几点", "get_time")]
accuracy = sum(pick(q) == expect for q, expect in CASES) / len(CASES)
```

- 工具顺序不影响协议，但影响模型的注意力分配，常用工具可放前面。
- 选择准确率要单独度量，不能靠人工感觉。
- 描述重叠时，模型倾向选「名字更贴近」的那个。""",
                "example_code": '''TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询实时天气（温度、天气现象）。仅用于当下或未来 24 小时的天气；历史天气请勿使用。",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取指定时区的当前时间。仅用于询问现在几点、当前日期。",
            "parameters": {
                "type": "object",
                "properties": {"timezone": {"type": "string", "description": "如 Asia/Shanghai"}},
                "required": ["timezone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "按订单号查询订单当前状态与物流节点。仅在用户给出订单号时使用。",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
]

CASES = [
    ("杭州今天天气怎么样", "get_weather", {"city": "杭州"}),
    ("现在北京时间几点", "get_time", {"timezone": "Asia/Shanghai"}),
    ("订单 20261108001 到哪了", "get_order_status", {"order_id": "20261108001"}),
    ("上周杭州天气如何", None, None),
]


def fake_pick(question: str) -> tuple[str | None, dict | None]:
    """离线桩：按关键词模拟模型的选择行为。"""
    if "订单" in question:
        order_id = "".join(ch for ch in question if ch.isdigit())
        return ("get_order_status", {"order_id": order_id}) if order_id else (None, None)
    if "几点" in question or "日期" in question:
        return "get_time", {"timezone": "Asia/Shanghai"}
    if "天气" in question and "上周" not in question:
        return "get_weather", {"city": "杭州"}
    return None, None


correct = 0
for question, expected_tool, _args in CASES:
    tool, args = fake_pick(question)
    ok = tool == expected_tool
    correct += ok
    print(f"{'通过' if ok else '不符'} | {question} -> {tool} {args}")

print("选择准确率:", correct / len(CASES))''',
                "code_lines": """1. 三个工具的 `description` 都写了「只在什么时候用」，把边界写进描述。
2. `get_weather` 明确排除历史天气，避免它去接「上周天气」这类问题。
3. `get_order_status` 要求用户给出订单号，没有订单号时应追问而不是编造。
4. `CASES` 是选择准确率的评测集：问题 → 期望工具（`None` 表示不该调用）。
5. `fake_pick` 用关键词模拟模型行为，便于离线验证评测逻辑本身。
6. 逐条打印「通过 / 不符」，错例比总分更有用。
7. 最后算准确率，这个数字就是「工具描述质量」的可观测代理指标。""",
                "output": """# 示例输出
通过 | 杭州今天天气怎么样 -> get_weather {'city': '杭州'}
通过 | 现在北京时间几点 -> get_time {'timezone': 'Asia/Shanghai'}
通过 | 订单 20261108001 到哪了 -> get_order_status {'order_id': '20261108001'}
通过 | 上周杭州天气如何 -> None None
选择准确率: 1.0

# 描述写差时（weather 描述只写「查询天气」）
不符 | 上周杭州天气如何 -> get_weather {'city': '杭州'}
选择准确率: 0.75""",
                "mistakes": """- 两个工具描述高度重叠（「查询订单」「查询订单信息」），模型随机选。
- 一个工具包揽增删改查，参数里靠 `action` 区分，导致误操作风险高。
- 描述里只写「能做什么」，不写「什么时候不该用」。
- 工具太多（20+）且描述重复，选择准确率断崖下降。
- 不做选择准确率评测，线上错了才发现。""",
                "error_analysis": """模型总是调用查询工具，即使问题需要修改
—— 缺少对应工具，或描述里没写清「修改请用另一个工具」。补齐工具并写清分工。

同一问题两次选不同工具
—— 温度偏高或两个描述区分度不足。先降温度，再改描述加入排他条件。

参数提取错（把订单号提成手机号）
—— 参数描述不够具体。在 `description` 里给格式示例与长度范围。""",
                "beginner_practice": """1. 再加一个 `cancel_order` 工具，在描述里写清「仅在用户明确要求取消时使用」。
2. 给 `CASES` 补两条「不该调用任何工具」的问题，观察准确率。""",
                "advanced_practice": """当工具数量增加到 12 个时，选择准确率明显下降。请给出三种优化方案
（描述重写、工具分组、两级路由），并说明各自的代价。""",
                "quiz_note": "本节 6 道题：2 道基础理解（选择依据、粒度原则）+ 2 道代码阅读（读描述边界、读评测循环）+ 2 道应用练习（加工具、优化方案）。",
                "summary": """模型只凭名字与描述选工具，描述必须写清「何时用、何时不用」。
一个工具做一件事，别用 action 参数包揽多种操作。
选择准确率要单独评测，错例是最好的改进线索。""",
                "next_lesson": "下一节给工具循环加上限与失败处理，避免死循环。",
                "knowledge_points": [
                    {
                        "code": "llm-api-12-01",
                        "name": "多工具声明与选择评测",
                        "goal": "能用清晰描述与评测集提升工具选择准确率。",
                        "minutes": 40,
                        "criteria": "能写出带排他条件的工具描述，并用「问题→期望工具」集合算出准确率。",
                        "requires": ["llm-api-11-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-12-01-1",
                        "kp": 0,
                        "title": "给描述加排他条件",
                        "description": "为 `get_order_status` 补一句排他条件，使它在「没有订单号」时不被调用。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''"description": (
    "按订单号查询订单当前状态与物流节点。"
    "仅在用户明确给出订单号时使用；没有订单号时不要调用，应先向用户追问。"
)''',
                        "explanation": "排他条件把「不该用」的情形显式写出来，模型才有依据选择「不调用」。",
                    },
                    {
                        "code": "llm-ex-12-01-2",
                        "kp": 0,
                        "title": "合并还是拆分",
                        "description": "「查询订单」「取消订单」「修改地址」三个能力，应该做成几个工具？说明理由。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''做成三个：查询是只读，取消与修改是写操作且需要权限与二次确认。
合并成一个 `manage_order(action=...)` 的问题：① 描述难以写清边界，模型容易选错动作；② 权限无法最小化，只读场景也被授予写权限；③ 危险操作与只读操作混在一个工具里，无法对「取消」单独加人工确认。
如果工具数量确实过多，可按领域分组成两级路由：先选「订单域」，再选具体动作。''',
                        "explanation": "拆分的第一原则是「权限与风险是否一致」，其次是「描述能否写清」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-12-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "模型选择工具时依据的信息是？",
                        "options": [
                            ("A", "工具名称、描述与参数 schema"),
                            ("B", "工具的实现源码"),
                            ("C", "工具的执行耗时"),
                            ("D", "工具的部署位置"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "模型看不到实现，只能凭声明判断；描述质量直接决定选择准确率。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-12-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "把「查订单 / 改地址 / 取消订单」合成一个工具的坏处有？（多选）",
                        "options": [
                            ("A", "描述难写清，模型容易选错动作"),
                            ("B", "无法按动作做权限最小化"),
                            ("C", "危险操作无法单独加人工确认"),
                            ("D", "会增加一次网络请求"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "合并反而减少调用次数，代价在可控性与权限，不在性能。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-12-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`fake_pick` 中「上周杭州天气如何」返回 `(None, None)`，含义是？",
                        "options": [
                            ("A", "该问题不应触发任何工具调用"),
                            ("B", "工具调用失败"),
                            ("C", "模型无法回答"),
                            ("D", "参数缺失"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "历史天气不在工具能力范围内，正确行为是不调用并说明限制。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-12-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例把「选择准确率」作为指标，最直接反映的是？",
                        "options": [
                            ("A", "工具描述与用户表达的匹配质量"),
                            ("B", "模型的推理能力"),
                            ("C", "网络稳定性"),
                            ("D", "工具的响应速度"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "同一模型下，准确率变化主要来自描述与评测集的调整，这正是可控的部分。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-12-01-5",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "工具声明越多，模型能力越强，所以应该尽量多声明。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "工具过多且描述重叠会显著降低选择准确率，应按场景裁剪或做两级路由。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-12-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "工具从 5 个增到 15 个后准确率下降，请给出三种可落地的优化方案并说明代价。",
                        "answer": {"value": "① 描述重写：为每个工具加「何时用/何时不用」与参数格式示例，成本低、收益直接，但需要逐个评测；② 工具分组 + 两级路由：先让模型选领域（订单/天气/账户），再在该组内选具体工具，准确率提升明显，代价是多一次模型调用与更复杂的编排；③ 按场景裁剪：不同页面只下发相关工具（客服页不下发运维工具），准确率最高，代价是配置管理与场景拆分成本。实践中通常先做①，再按业务域做③。"},
                        "explanation": "三种方案从「改文本」到「改架构」，代价递增，收益也不同，应按工具规模选择。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-12-lesson-02",
                "objectives": """1. 能实现带最大步数的工具循环；
2. 能在循环中检测「重复调用同一工具同一参数」并止损；
3. 能把工具失败转成可读信息而不是中断对话；
4. 能设计循环终止条件（有答案 / 达上限 / 无进展）。""",
                "why_learn": """模型可能反复调用同一个工具、或者在两个工具之间来回跳。
没有上限与止损，一次用户提问就能烧掉几十次调用，还答不出结果。""",
                "concepts": """**最大步数**：`max_steps`（通常 3—6），超过就返回当前最佳结果或说明失败。
**重复检测**：同一工具 + 同一参数出现两次，视为无进展，立即止损。
**失败回填**：错误作为工具结果回填，模型可以选择换工具或向用户解释。
**终止条件**：拿到非空内容即结束；步数耗尽时降级。
**成本核算**：每步都是一次模型调用，步数直接等于成本。""",
                "plain": """工具循环像查资料：查一次没查到，可以换个关键词再查；
但如果一直翻同一页，就该停下来，而不是翻一百遍。
「最多翻几次」和「同一页不翻第二遍」是两条最实用的规矩。""",
                "syntax": """**API 说明（带上限的循环）**

```python
for step in range(MAX_STEPS):
    reply = client.chat(messages)
    if not reply.tool_calls:
        return reply.content
    messages.append(reply)
    for call in reply.tool_calls:
        key = (call.name, call.arguments)
        if key in seen:
            return fallback("检测到重复调用")
        seen.add(key)
        messages.append(tool_message(call))
return fallback("步数耗尽")
```

- 先判断「有没有工具调用」，没有就是最终答案。
- `seen` 集合记录「工具 + 参数」，用于止损。
- 循环外一定有返回，不允许「可能没有返回值」。""",
                "example_code": '''import json
from collections.abc import Callable

MAX_STEPS = 4


def tool_echo(city: str) -> dict:
    return {"city": city, "temp": 18}


def tool_fail(city: str) -> dict:
    raise RuntimeError("上游服务不可用")


HANDLERS: dict[str, Callable[..., dict]] = {"echo": tool_echo, "fail": tool_fail}


def run(name: str, args: dict) -> dict:
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": f"未知工具：{name}"}
    try:
        return handler(**args)
    except Exception as exc:
        return {"error": f"工具失败：{exc}"}


def fake_model(messages: list[dict], step: int) -> dict:
    """离线桩：第 1—3 步都要求调用同一工具，用于演示止损。"""
    if step < 3:
        return {
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_{step}",
                    "function": {"name": "echo", "arguments": '{"city": "杭州"}'},
                }
            ],
        }
    return {"content": "杭州现在 18 度。", "tool_calls": None}


def run_loop(question: str) -> tuple[str, int, str]:
    messages: list[dict] = [{"role": "user", "content": question}]
    seen: set[tuple[str, str]] = set()
    for step in range(MAX_STEPS):
        reply = fake_model(messages, step)
        calls = reply.get("tool_calls")
        if not calls:
            return reply["content"], step + 1, "answered"
        messages.append({"role": "assistant", "content": None, "tool_calls": calls})
        for call in calls:
            key = (call["function"]["name"], call["function"]["arguments"])
            if key in seen:
                return "该问题需要的数据暂时无法取得，请稍后再试。", step + 1, "repeated"
            seen.add(key)
            result = run(call["function"]["name"], json.loads(call["function"]["arguments"]))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    return "已尝试多次仍未得到结果，请换个问法。", MAX_STEPS, "max_steps"


answer, steps, reason = run_loop("杭州现在多少度")
print("答案:", answer)
print("步数:", steps, "终止原因:", reason)''',
                "code_lines": """1. `MAX_STEPS` 是硬上限，任何路径都不可能超过它。
2. `seen` 记录「工具名 + 参数字符串」，这是最轻量的重复检测。
3. `run` 把工具异常转成 `{"error": ...}`，循环不会被异常打断。
4. `reply.get("tool_calls")` 为空即视为最终答案，这是正常出口。
5. 每个 `call` 都要回填一条 `tool` 消息，否则下一轮接口报错。
6. 重复调用时直接返回兜底话术，而不是继续循环——这是止损的关键。
7. 三个返回值（答案、步数、原因）便于日志统计「多少次因为重复而止损」。""",
                "output": """# 示例输出（桩模型第 3 步给答案，但第 2 步就重复了同一调用）
答案: 该问题需要的数据暂时无法取得，请稍后再试。
步数: 2 终止原因: repeated

# 桩模型每步都换参数时的输出
答案: 杭州现在 18 度。
步数: 4 终止原因: answered

# 桩模型一直要调用时的输出
答案: 已尝试多次仍未得到结果，请换个问法。
步数: 4 终止原因: max_steps""",
                "mistakes": """- 用 `while True` 且没有上限，模型抽风时无限循环。
- 只判步数不判重复，四次调用全打在一个死胡同工具上。
- 工具异常直接冒泡，循环中断且没有任何用户可见反馈。
- 循环里忘记追加 assistant 的 `tool_calls`，第二轮接口 400。
- 把「步数耗尽」当成成功返回空字符串，用户看到空白页。""",
                "error_analysis": """接口返回 400：tool 消息缺少前置 tool_calls
—— 循环里漏了 assistant 消息。顺序必须是 assistant(tool_calls) → tool。

一次提问消耗了 20 次模型调用
—— 没有 `MAX_STEPS`。任何循环都要有硬上限。

模型在两个工具之间来回调用
—— 典型无进展循环。用「工具 + 参数」集合去重，命中即止损。""",
                "beginner_practice": """1. 把 `MAX_STEPS` 改成 1，观察终止原因的变化。
2. 让桩模型第 2 步换一个参数，确认不会误判为重复。""",
                "advanced_practice": """给循环加一个「预算」概念：每次模型调用按 token 计费，超过预算即止损；
说明预算与步数上限各自的适用场景，以及如何向用户解释「因预算耗尽而停止」。""",
                "quiz_note": "本节 6 道题：2 道基础理解（为什么要有上限、止损依据）+ 2 道代码阅读（读 seen、读终止分支）+ 2 道应用练习（改上限、加预算）。",
                "summary": """工具循环必须有硬上限与无进展检测。
工具异常要回填成结果，让模型有机会换路或解释。
三种终止：拿到答案、重复调用、步数耗尽，每种都要有用户可读的出口。""",
                "next_lesson": "下一章算账：token、上下文窗口与调用费用。",
                "knowledge_points": [
                    {
                        "code": "llm-api-12-02",
                        "name": "工具循环上限与止损",
                        "goal": "能实现带上限、去重与失败回填的工具循环。",
                        "minutes": 40,
                        "criteria": "能写出三种终止条件齐全、异常可回填的工具循环，并解释去重键的构成。",
                        "requires": ["llm-api-12-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-12-02-1",
                        "kp": 0,
                        "title": "加预算止损",
                        "description": "给 `run_loop` 增加 `budget` 参数（按累计字符数估算 token），超预算时返回兜底话术。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def run_loop(question: str, budget: int = 4000) -> tuple[str, int, str]:
    messages = [{"role": "user", "content": question}]
    seen = set()
    spent = 0
    for step in range(MAX_STEPS):
        if spent > budget:
            return "本次查询消耗过大，已停止。", step, "budget"
        reply = fake_model(messages, step)
        spent += len(json.dumps(reply, ensure_ascii=False))
        calls = reply.get("tool_calls")
        if not calls:
            return reply["content"], step + 1, "answered"
        # ... 其余逻辑不变''',
                        "explanation": "预算是「钱」维度的上限，步数是「次数」维度的上限，两者互补：一次调用也可能很贵。",
                    },
                    {
                        "code": "llm-ex-12-02-2",
                        "kp": 0,
                        "title": "用户看到什么",
                        "description": "三种终止原因分别应该给用户什么提示？请各写一句，不要出现内部术语。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''answered：正常回答即可，不需要额外提示。
repeated：该问题需要的数据暂时查不到，请稍后再试或换个问法。
max_steps：这个问题比较复杂，我尝试了几次仍未得到结果，可以补充更多信息再问我。
budget：本次查询消耗较大已停止，建议缩小问题范围后再试。''',
                        "explanation": "提示要说明「发生了什么 + 用户能做什么」，不要暴露 `max_steps`、`tool_calls` 这类内部概念。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-12-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "工具循环最关键的保护措施是？",
                        "options": [
                            ("A", "设置最大步数与无进展检测"),
                            ("B", "提高温度增加探索"),
                            ("C", "一次声明更多工具"),
                            ("D", "把超时设为 0"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "上限防「次数失控」，去重防「原地打转」，两者共同构成止损。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-12-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "工具循环的正常终止条件包括哪些？（多选）",
                        "options": [
                            ("A", "模型返回了不带工具调用的内容"),
                            ("B", "检测到重复调用"),
                            ("C", "达到最大步数"),
                            ("D", "工具执行成功一次"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "工具成功一次并不意味着问题解决，模型可能还需要基于结果再推理。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-12-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "去重键用 `(工具名, 参数字符串)` 而不是只用工具名，原因是？",
                        "options": [
                            ("A", "同名工具不同参数是合理的新调用，不能算重复"),
                            ("B", "参数字符串更短"),
                            ("C", "工具名可能重复"),
                            ("D", "便于排序"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "换城市查天气是正常行为；只有「同工具同参数」才说明无进展。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-12-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`run` 捕获所有异常并返回 `{\"error\": ...}`，这样做的代价是？",
                        "options": [
                            ("A", "严重错误被掩盖，需要日志留痕才能发现"),
                            ("B", "循环会变慢"),
                            ("C", "模型无法读取错误"),
                            ("D", "会增加 token"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "兜底让对话不中断，但也可能隐藏系统性问题，因此必须同时记录日志与指标。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-12-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全循环上限。横线处应填什么？\n\n```python\nfor step in range(____):\n    reply = client.chat(messages)\n```",
                        "options": [("A", "MAX_STEPS"), ("B", "len(messages)"), ("C", "1000"), ("D", "step")],
                        "answer": {"value": "A"},
                        "explanation": "用命名常量表达上限，便于统一调整与在日志中体现；写死 1000 等于没有上限。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-12-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "线上发现「步数耗尽」的比例从 2% 涨到 15%，你会怎么查？",
                        "answer": {"value": "① 按工具维度拆分：是不是某个工具频繁失败或超时，导致模型反复重试；② 看重复检测命中率：重复多说明描述不清或参数总是不满足；③ 看用户问题类型：是否出现了大量工具能力之外的问题（如历史数据）；④ 核对变更：最近是否改了工具描述、模型版本或提示词；⑤ 处理：修复失败工具、补「能力边界」提示、对超范围问题直接引导，而不是让模型硬试。同时给「步数耗尽」加告警阈值，避免持续恶化。"},
                        "explanation": "先分维度定位（工具 / 问题类型 / 变更），再决定是修工具、改描述还是加引导。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
