"""Python 大模型 API 应用开发：第 1—3 章（基本概念、服务商与兼容 API、API Key 管理）。"""

CHAPTERS: list[dict] = [
    {
        "code": "llm-api-01",
        "title": "大语言模型基本概念",
        "description": "先知道它在做什么，再决定让它做什么。",
        "order_index": 1,
        "lessons": [
            {
                "code": "llm-api-01-lesson-01",
                "objectives": """1. 能说清「模型一次只输出一个 token」这句话的含义；
2. 知道 token 不是字也不是词，理解中文与英文的切分差异；
3. 能解释温度、top_p 如何影响输出的随机性；
4. 能预估同一问题两次回答不同的原因。""",
                "why_learn": """很多人第一次调用接口时的困惑是「为什么同样的输入，输出不一样」。
不理解采样机制，就会把随机性当成 bug，去反复调代码；理解之后才知道该在哪里收窄随机性、哪里要保留多样性。""",
                "concepts": """**Token**：模型处理文本的最小单位，中文常按字或词片段切分，英文按子词切分。
**下一个 token 预测**：模型根据已有上下文给出词表上每个候选的概率分布，再按分布取样。
**温度（temperature）**：低于 1 让分布更尖锐（更确定），高于 1 更平坦（更发散）。
**top_p**：只在累计概率前 p 的候选里取样，用来砍掉长尾。
**上下文窗口**：一次请求中「输入 + 输出」能容纳的 token 上限。""",
                "plain": """把模型想成一个只会在句尾接话的人：他不写整段，只报下一个最顺的词。
报完之后把新词接到句子后面，再报下一个，如此循环。
温度像是「让不让他冒险」：温度低就只挑最有把握的词，温度高就愿意挑冷门词。所以同一个开头，两次接出来的句子可以不一样。""",
                "syntax": """**API 说明（纯 Python 演示，不涉及网络调用）**

```python
def softmax(scores: dict[str, float], temperature: float) -> dict[str, float]:
    exp = {token: math.exp(score / temperature) for token, score in scores.items()}
    total = sum(exp.values())
    return {token: value / total for token, value in exp.items()}
```

- `scores` 是模型给出的原始打分（logit），不是概率。
- 除以 `temperature` 再取指数、归一化，得到概率分布。
- `temperature` 必须大于 0；等于 0 时无法做除法，工程上要单独处理成「取最大值」。""",
                "example_code": '''import math
import random


def softmax(scores: dict[str, float], temperature: float) -> dict[str, float]:
    if temperature <= 0:
        raise ValueError("温度必须大于 0")
    exp = {token: math.exp(score / temperature) for token, score in scores.items()}
    total = sum(exp.values())
    return {token: value / total for token, value in exp.items()}


def sample(probs: dict[str, float], rng: random.Random) -> str:
    point = rng.random()
    acc = 0.0
    for token, prob in probs.items():
        acc += prob
        if point <= acc:
            return token
    return list(probs)[-1]


SCORES = {"今天": 3.0, "明天": 2.0, "昨天": 1.0, "星期": 0.2}

rng = random.Random(7)
for temperature in (0.2, 1.0, 1.8):
    probs = softmax(SCORES, temperature)
    picks = [sample(probs, rng) for _ in range(8)]
    top = max(probs.values())
    print(f"温度={temperature} 最高概率={top:.2f} 抽样={picks}")''',
                "code_lines": """1. `softmax` 把原始打分变成概率：每个值取指数后除以总和，保证加起来等于 1。
2. 除以 `temperature` 是唯一的控制点：温度小，大分差被放大，概率集中；温度大，分差被压平。
3. `sample` 用「累积概率 + 随机数」实现按概率抽样，这是所有采样器的核心思路。
4. 循环累加 `acc`，一旦随机点落进当前区间就返回该 token——高概率 token 覆盖的区间更宽。
5. 兜底 `list(probs)[-1]` 防止浮点误差导致随机点落在 1.0 之后。
6. 固定 `random.Random(7)` 是为了让示例输出可复现；真实模型里这一步由服务端完成。
7. 打印最高概率，可以直观看到温度如何改变「把握程度」。""",
                "output": """# 示例输出（固定随机种子，可复现）
温度=0.2 最高概率=0.79 抽样=['今天', '今天', '今天', '今天', '今天', '今天', '今天', '明天']
温度=1.0 最高概率=0.45 抽样=['今天', '明天', '今天', '今天', '明天', '昨天', '今天', '今天']
温度=1.8 最高概率=0.34 抽样=['明天', '今天', '昨天', '今天', '明天', '星期', '今天', '昨天']""",
                "mistakes": """- 把 token 当成字：以为「你好」一定是一个 token，实际可能被切成两个。
- 认为温度 0 就是「完全确定」，忽略服务端仍可能有并发与浮点差异。
- 用温度调节「答案正确率」：事实性问题靠检索与约束，不靠调温度。
- 同时大幅调温度与 top_p，两个参数互相牵制，效果不可预期。
- 用输出长度估算 token 数，中文长文误差可达 30% 以上。""",
                "error_analysis": """`ValueError: 温度必须大于 0`
—— 传了 `temperature=0`。真实接口里 0 通常表示贪心解码，但自己实现 softmax 时不能直接除。

两次请求返回完全不同的答案，但代码没改
—— 默认温度一般不为 0，采样本身带随机性。需要稳定输出时把温度降到 0—0.2，并在 Prompt 里固定格式要求。

长文被截断，`finish_reason` 是 `length`
—— 触达了输出 token 上限，不是报错。要么调大上限，要么让模型分段输出。""",
                "beginner_practice": """1. 把 `SCORES` 改成只有两个候选，观察温度 0.5 与 2.0 下抽样结果的差别。
2. 把 `sample` 改成「永远取概率最大的 token」，对比输出是否稳定。""",
                "advanced_practice": """用 20 条中文短句粗略统计 token 与汉字的比值（可用服务端返回的 usage 字段），
给出「中文 1 字约等于多少 token」的经验区间，并说明为什么不能拿它做精确计费。""",
                "quiz_note": "本节 6 道题：2 道基础理解（token 含义、温度作用）+ 2 道代码阅读（读 softmax、读抽样循环）+ 2 道应用练习（选温度、解释输出差异）。",
                "summary": """模型一次只产出一个 token，整段文本是循环采样的结果。
温度与 top_p 控制随机性：要稳定就调低，要多样就调高。
token 与字数不是一回事，估算长度和费用都要按 token 算。""",
                "next_lesson": "下一节讲能力边界：哪些任务可以交给模型，哪些必须人工兜底。",
                "knowledge_points": [
                    {
                        "code": "llm-api-01-01",
                        "name": "Token 与下一个词预测",
                        "goal": "能解释 token 切分与自回归生成过程。",
                        "minutes": 30,
                        "criteria": "能用自己的话说清「一次一个 token、循环拼接」，并举例说明中英文切分差异。",
                        "requires": [],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-01-01-1",
                        "kp": 0,
                        "title": "手写一个温度采样器",
                        "description": "给定 `{\"A\": 2.0, \"B\": 1.0, \"C\": 0.0}`，实现温度 0.5 与 2.0 的抽样，各抽 10 次并统计次数。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''import math
import random


def softmax(scores, temperature):
    exp = {k: math.exp(v / temperature) for k, v in scores.items()}
    total = sum(exp.values())
    return {k: v / total for k, v in exp.items()}


def pick(probs, rng):
    point, acc = rng.random(), 0.0
    for token, prob in probs.items():
        acc += prob
        if point <= acc:
            return token
    return list(probs)[-1]


scores = {"A": 2.0, "B": 1.0, "C": 0.0}
rng = random.Random(1)
for temperature in (0.5, 2.0):
    probs = softmax(scores, temperature)
    picks = [pick(probs, rng) for _ in range(10)]
    print(temperature, {t: picks.count(t) for t in scores})''',
                        "explanation": "温度低时 A 的占比明显更高；温度高时三个候选更接近均分。这就是「确定性 vs 多样性」的取舍。",
                    },
                    {
                        "code": "llm-ex-01-01-2",
                        "kp": 0,
                        "title": "选温度",
                        "description": "以下场景分别适合什么温度区间：① 从合同里抽取金额 ② 给营销文案起 20 个标题 ③ 代码补全 ④ 头脑风暴产品名。",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''① 0—0.2，要求稳定、可校验；
② 0.8—1.2，需要多样性，但要限制输出条数与格式；
③ 0—0.3，正确性优先；
④ 1.0—1.3，鼓励发散，之后再人工筛选。''',
                        "explanation": "判断标准：结果要不要被程序校验、错了代价多大。可校验且代价高的场景一律压低随机性。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-01-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "关于 token，下列说法正确的是？",
                        "options": [
                            ("A", "一个汉字一定等于一个 token"),
                            ("B", "token 是模型处理文本的最小单位，切分方式与语言相关"),
                            ("C", "token 就是单词，英文一个单词一个 token"),
                            ("D", "token 数等于字符数除以 2"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "token 由分词器决定，中文可能按字或词片段切，英文按子词切，不存在固定的字符换算关系。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-01-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些做法能降低同一问题两次回答的差异？（多选）",
                        "options": [
                            ("A", "把 temperature 降到 0—0.2"),
                            ("B", "在 Prompt 里固定输出格式"),
                            ("C", "把 temperature 调到 1.8"),
                            ("D", "减少 top_p，只保留高概率候选"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "温度与 top_p 决定采样范围，格式约束减少表述漂移；调高温度只会让结果更发散。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-01-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `softmax` 里除以 `temperature` 的作用是？",
                        "options": [
                            ("A", "把原始打分放大或压缩，从而改变概率分布的尖锐程度"),
                            ("B", "把打分转换成整数"),
                            ("C", "限制输出 token 的数量"),
                            ("D", "随机打乱候选顺序"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "除以小于 1 的数会放大大分差，分布更尖锐；除以大于 1 的数会压平分差，分布更平坦。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-01-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`sample` 函数末尾的 `return list(probs)[-1]` 是为了？",
                        "options": [
                            ("A", "处理浮点误差导致随机点超出累计概率的情况"),
                            ("B", "返回概率最高的 token"),
                            ("C", "随机挑一个 token 制造多样性"),
                            ("D", "纠正温度参数"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "累计求和可能因浮点误差略小于 1.0，随机点落在尾部时需要兜底，返回最后一个候选最接近真实分布。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-01-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全代码，使温度不合法时立刻报错。横线处应填什么？\n\n```python\ndef softmax(scores, temperature):\n    if temperature ____ 0:\n        raise ValueError(\"温度必须大于 0\")\n```",
                        "options": [("A", "<="), ("B", ">"), ("C", "=="), ("D", "is")],
                        "answer": {"value": "A"},
                        "explanation": "温度等于 0 会触发除零，小于 0 会让分布反向，两者都必须拦掉。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-01-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "用户反馈「同一个问题问两次答案不一样」，你怎么判断这是设计如此还是真的有问题？",
                        "answer": {"value": "先看请求参数：temperature 是否大于 0、是否设置了 top_p、是否每次请求都带了相同的 system 消息。若温度大于 0 且参数一致，输出不同属于采样机制下的正常现象，应向用户说明并给出「固定温度 + 固定格式约束」的稳定模式。若温度已为 0 仍差异很大，再排查是否命中了不同模型、不同版本、或服务端做了负载均衡到不同后端，并把 request_id 与 usage 一并记录用于比对。"},
                        "explanation": "判断依据是参数与版本，而不是感觉；同时要把「可复现」当成一个需要主动提供的开关。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-01-lesson-02",
                "objectives": """1. 能列出模型擅长与不擅长的任务类型；
2. 能解释幻觉产生的原因，并说出三种缓解手段；
3. 能为高风险场景设计「模型建议 + 人工确认」的兜底路径；
4. 能在需求评审时判断某个功能该不该用模型实现。""",
                "why_learn": """模型能写得像模像样，但它并不知道自己不知道。
把「查事实」「算精确数字」「做最终决定」直接交给模型，是把不确定性引入到业务的关键路径上。""",
                "concepts": """**擅长**：改写、归纳、分类、抽取、格式转换、初稿生成、解释代码。
**不擅长**：精确计算、实时事实、长链推理的中间校验、需要承担责任的决定。
**幻觉**：模型在缺乏依据时仍生成流畅内容，形式上无法与真实信息区分。
**缓解手段**：提供依据（检索/引用原文）、要求给出处、用程序校验关键字段。
**兜底设计**：模型只产出建议与草稿，关键动作由规则或人工确认。""",
                "plain": """模型像一个读过很多书但没查过资料的实习生：表达很顺，但细节可能记错。
让他写初稿、改语气、分类归档都很合适；让他报今天的汇率、替你签字盖章就不合适。
正确用法是「他先写，你再核」——把核对做进流程，而不是指望他不出错。""",
                "syntax": """**API 说明（一个可复用的能力判定函数）**

```python
def risk_level(task: dict) -> str:
    if task["needs_fact"] or task["needs_math"]:
        return "high"      # 必须有外部依据或程序计算
    if task["is_public"]:
        return "medium"    # 输出会对外，需要人工过一遍
    return "low"
```

- 判定维度：是否依赖实时事实、是否需要精确计算、输出影响面。
- 返回等级直接决定后续流程：`high` 必须带检索或人工确认。
- 把判定写成函数，才能在评审与代码里复用同一套标准。""",
                "example_code": '''TASKS = [
    {"name": "给商品写卖点文案", "needs_fact": False, "needs_math": False, "is_public": True},
    {"name": "回答今天的库存还剩多少", "needs_fact": True, "needs_math": False, "is_public": True},
    {"name": "计算订单总价与折扣", "needs_fact": False, "needs_math": True, "is_public": True},
    {"name": "把会议记录整理成待办", "needs_fact": False, "needs_math": False, "is_public": False},
]


def risk_level(task: dict) -> str:
    if task["needs_fact"] or task["needs_math"]:
        return "high"
    if task["is_public"]:
        return "medium"
    return "low"


def advice(level: str) -> str:
    if level == "high":
        return "必须提供依据或改用程序计算，输出仅作参考"
    if level == "medium":
        return "可自动生成，但对外前需人工确认"
    return "可直接使用，保留日志便于回溯"


for task in TASKS:
    level = risk_level(task)
    print(f"{task['name']}: {level} -> {advice(level)}")''',
                "code_lines": """1. 用三个布尔维度描述任务，避免凭直觉争论「能不能用模型」。
2. `needs_fact` 覆盖实时数据类需求：模型没有联网就不该被问今天的事。
3. `needs_math` 覆盖精确计算：金额、税额、库存一律交给程序。
4. 先判高危再判中危，顺序决定结果，写反了会让高危任务落到 medium。
5. `advice` 把等级翻译成可执行动作，评审结论不再停留在形容词。
6. 打印格式统一为「任务: 等级 -> 动作」，方便贴进需求文档。""",
                "output": """# 示例输出
给商品写卖点文案: medium -> 可自动生成，但对外前需人工确认
回答今天的库存还剩多少: high -> 必须提供依据或改用程序计算，输出仅作参考
计算订单总价与折扣: high -> 必须提供依据或改用程序计算，输出仅作参考
把会议记录整理成待办: low -> 可直接使用，保留日志便于回溯""",
                "mistakes": """- 让模型回答「今天的库存」，再把它的估计值当真。
- 用模型做金额计算，四舍五入差异被当成 bug 排查半天。
- 把模型输出直接对外发布，没有人工或规则校验。
- 以为加了「请勿编造」就不会幻觉，指令无法凭空创造事实。
- 用模型的自信程度判断可信度——语气与正确性无关。""",
                "error_analysis": """用户投诉「AI 说的活动价与实际不符」
—— 让模型回答实时价格。修法：价格从数据库取，模型只负责组织语言。

抽取出的金额与合同差 1 元
—— 模型做算术。修法：模型只负责定位字段，数值由程序解析并校验。

同样的问题换个人问，答案完全不同
—— 缺少固定依据。修法：把原文一起放进上下文，并要求引用原句。""",
                "beginner_practice": """1. 再补三条任务记录，分别标出三个维度，并写出对应等级。
2. 把 `advice` 改成返回元组 `(等级, 是否需要人工)`，在打印时拆开使用。""",
                "advanced_practice": """为一个真实需求（例如「自动回复客户咨询」）设计完整兜底路径：
哪些问题自动答、哪些转人工、转人工时把什么信息一起带过去、如何记录与复盘。""",
                "quiz_note": "本节 6 道题：2 道基础理解（能力边界、幻觉成因）+ 2 道代码阅读（读判定顺序、读等级映射）+ 2 道应用练习（判等级、设计兜底）。",
                "summary": """模型擅长语言变换，不擅长事实与精确计算。
幻觉无法靠指令消除，只能靠依据、校验与流程兜底。
把「能不能用模型」拆成可判定的维度，评审结论才可复用。""",
                "next_lesson": "下一章进入服务商与兼容协议：为什么同一段代码能调用不同厂商的模型。",
                "knowledge_points": [
                    {
                        "code": "llm-api-01-02",
                        "name": "能力边界与幻觉缓解",
                        "goal": "能判断任务是否适合交给模型，并给出兜底方案。",
                        "minutes": 30,
                        "criteria": "能用「是否依赖事实、是否需要精确计算、输出影响面」三个维度给任务分级，并说出至少两种幻觉缓解手段。",
                        "requires": ["llm-api-01-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-01-02-1",
                        "kp": 0,
                        "title": "给需求分级",
                        "description": "为以下四个需求标注 high/medium/low 并说明理由：① 生成周报初稿 ② 回答「我的订单到哪了」 ③ 把英文说明书翻译成中文 ④ 判断退款申请是否通过。",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''① low—medium：内部初稿，人工会改；
② high：依赖实时物流数据，必须查接口，模型只组织语言；
③ medium：翻译质量需抽检，专业术语可能要术语表；
④ high：涉及资金与规则，必须由规则引擎判定，模型最多做材料摘要。''',
                        "explanation": "只要答案依赖实时数据、精确规则或影响资金，就不能让模型单独决定。",
                    },
                    {
                        "code": "llm-ex-01-02-2",
                        "kp": 0,
                        "title": "加一个「需人工」返回值",
                        "description": "修改示例，让 `risk_level` 之外再返回是否需要人工确认，并在打印时体现。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def evaluate(task: dict) -> tuple[str, bool]:
    if task["needs_fact"] or task["needs_math"]:
        return "high", True
    if task["is_public"]:
        return "medium", True
    return "low", False


for item in TASKS:
    level, need_human = evaluate(item)
    print(f"{item['name']}: {level} 人工确认={need_human}")''',
                        "explanation": "把「等级」与「是否需要人工」拆成两个返回值，调用方不用再自己映射，减少判断分散在多个地方。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-01-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "下列任务中最不适合直接交给大模型独立完成的是？",
                        "options": [
                            ("A", "把用户反馈归类到 5 个标签"),
                            ("B", "计算订单应付金额并扣款"),
                            ("C", "把技术文档改写成科普语气"),
                            ("D", "从简历里抽取工作年限"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "金额计算与扣款属于精确规则且影响资金，必须由程序完成，模型只可辅助。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-01-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "哪些做法能降低幻觉带来的风险？（多选）",
                        "options": [
                            ("A", "把原始资料放进上下文并要求引用原句"),
                            ("B", "让程序校验关键字段是否出现在原文中"),
                            ("C", "在 Prompt 里写「请不要编造」"),
                            ("D", "对高风险结论加人工确认环节"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "指令只能降低概率，不能创造事实；依据、程序校验与人工环节才是结构性手段。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-01-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中若把 `is_public` 的判断放到最前面，会发生什么？",
                        "options": [
                            ("A", "「回答今天库存」这类高危任务会被判成 medium"),
                            ("B", "代码报错"),
                            ("C", "结果完全不变"),
                            ("D", "所有任务都变成 low"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "判定顺序决定优先级，高危条件必须先判，否则会被更宽松的规则先命中。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-01-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`advice` 函数在 `level` 为 `low` 时返回什么？",
                        "options": [
                            ("A", "可直接使用，保留日志便于回溯"),
                            ("B", "必须提供依据或改用程序计算"),
                            ("C", "可自动生成，但对外前需人工确认"),
                            ("D", "空字符串"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "三个分支分别对应 high / medium / low，default 分支即 low。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-01-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全判定条件，使「需要事实或需要计算」的任务被判为 high。横线处应填什么？\n\n```python\nif task[\"needs_fact\"] ____ task[\"needs_math\"]:\n    return \"high\"\n```",
                        "options": [("A", "or"), ("B", "and"), ("C", "not"), ("D", "in")],
                        "answer": {"value": "A"},
                        "explanation": "任意一个为真都属于高风险，用 `or`；用 `and` 会漏掉只满足其中一条的任务。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-01-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "业务方要求「模型自动回复客户，不要人工」，你会怎么沟通并给出什么方案？",
                        "answer": {"value": "先用分级说明风险：涉及订单状态、退款、价格承诺的问题依赖实时数据与资金规则，自动回复一旦出错要赔付。方案分三层：① 知识型问题（营业时间、流程说明）走模型自动回复，并给出依据链接；② 数据型问题由接口查真实数据后模板化回复，模型只润色；③ 争议与资金类问题自动转人工，转接时把会话摘要、用户身份、已查到的数据一起带过去。同时记录自动回复的命中率与投诉率，按周复盘再逐步放开范围。"},
                        "explanation": "沟通的关键是把「不能自动」翻译成「哪一类不能自动 + 出错代价 + 替代路径」，而不是简单拒绝。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "llm-api-02",
        "title": "模型服务商与 OpenAI 兼容 API",
        "description": "换服务商只改两个配置，不改一行业务代码。",
        "order_index": 2,
        "lessons": [
            {
                "code": "llm-api-02-lesson-01",
                "objectives": """1. 能说出主流模型服务商的差异点（协议、模型命名、计费方式）；
2. 理解「OpenAI 兼容」指的是请求与响应格式兼容，而不是模型相同；
3. 能解释为什么业务代码应该只依赖兼容协议；
4. 能识别某厂商「独有能力」与「兼容层通用能力」的边界。""",
                "why_learn": """今天用 A 家的模型，明天可能因为价格或合规换成 B 家。
如果代码里到处是某家 SDK 的专有方法，换供应商就变成重写。兼容协议把这件事变成改两个配置。""",
                "concepts": """**兼容协议**：请求路径 `/v1/chat/completions`、JSON 字段、鉴权头保持一致。
**差异点**：模型名称、可用参数（部分厂商不支持某些采样参数）、计费单位、速率限制。
**独有能力**：某厂商特有的参数或接口，只能作为可选增强，不能成为主链路依赖。
**适配层**：业务只依赖自己的 `LLMClient`，厂商差异收敛在适配层里。""",
                "plain": """兼容协议像 USB 接口：不同厂家的 U 盘都能插同一个口。
但各家 U 盘的速度、容量、价格不同——接口统一，能力不统一。
所以代码要按「接口」写，按「配置」选厂家；遇到只有某家才有的功能，当作附加项，而不是前提。""",
                "syntax": """**API 说明（三种常见配置形态）**

```python
PROVIDERS = {
    "provider_a": {"base_url": "https://api.example-a.com/v1", "model": "chat-large"},
    "provider_b": {"base_url": "https://api.example-b.com/v1", "model": "chat-pro"},
    "local": {"base_url": "http://127.0.0.1:8000/v1", "model": "local-chat"},
}
```

- `base_url` 通常到 `/v1` 为止，代码里再拼 `/chat/completions`。
- `model` 必须由配置提供，不能写死在调用处。
- 同一份代码换 `base_url` + `model` 就能换厂商，这是兼容协议的价值。""",
                "example_code": '''PROVIDERS = {
    "provider_a": {
        "base_url": "https://api.example-a.com/v1",
        "model": "chat-large",
        "supports_top_p": True,
    },
    "provider_b": {
        "base_url": "https://api.example-b.com/v1",
        "model": "chat-pro",
        "supports_top_p": False,
    },
    "local": {
        "base_url": "http://127.0.0.1:8000/v1",
        "model": "local-chat",
        "supports_top_p": True,
    },
}


def build_endpoint(base_url: str) -> str:
    return base_url.rstrip("/") + "/chat/completions"


def build_payload(provider: dict, messages: list[dict]) -> dict:
    payload = {"model": provider["model"], "messages": messages}
    if provider["supports_top_p"]:
        payload["top_p"] = 0.9
    return payload


for name, provider in PROVIDERS.items():
    payload = build_payload(provider, [{"role": "user", "content": "你好"}])
    print(name, build_endpoint(provider["base_url"]), payload)''',
                "code_lines": """1. 用一张表描述每个厂商的三项关键配置：地址、模型名、能力开关。
2. `build_endpoint` 用 `rstrip("/")` 兜住末尾斜杠，避免拼出 `//chat/completions`。
3. `build_payload` 只放兼容层通用字段：`model` 与 `messages`。
4. `top_p` 这类参数按厂商能力开关决定是否发送，不假设所有厂商都支持。
5. 循环里对三家厂商生成同一结构，说明业务代码不需要分支。
6. 打印出来可以直接对照，排查「为什么换厂商后参数被忽略」这类问题。""",
                "output": """# 示例输出
provider_a https://api.example-a.com/v1/chat/completions {'model': 'chat-large', 'messages': [{'role': 'user', 'content': '你好'}], 'top_p': 0.9}
provider_b https://api.example-b.com/v1/chat/completions {'model': 'chat-pro', 'messages': [{'role': 'user', 'content': '你好'}]}
local http://127.0.0.1:8000/v1/chat/completions {'model': 'local-chat', 'messages': [{'role': 'user', 'content': '你好'}], 'top_p': 0.9}""",
                "mistakes": """- 把模型名写死在代码里，换模型要改代码重新发布。
- 以为「兼容」就等于「能力一样」，用了对方不支持的参数还以为生效了。
- `base_url` 多写或少写 `/v1`，导致 404 或路径重复。
- 直接在业务代码里调某家 SDK，换厂商时全量重写。
- 依赖某厂商独有参数做核心功能，降级到别家时功能直接不可用。""",
                "error_analysis": """`404 Not Found`，body 是 `{"error": "invalid path"}`
—— `base_url` 已经包含 `/chat/completions`，代码又拼了一次。配置只写到 `/v1`。

请求成功但 `top_p` 没生效
—— 该厂商不支持此参数并静默忽略。用能力开关控制，别假设参数一定生效。

换模型后输出风格突变、格式不遵守
—— 不同模型对同一 Prompt 的遵循度不同。换模型要跑回归集，不能只看「能通」。""",
                "beginner_practice": """1. 给 `PROVIDERS` 加一家新厂商，只改配置，不改函数。
2. 把 `supports_top_p` 换成 `extra_params` 字典，让不同厂商可以带不同参数。""",
                "advanced_practice": """设计一个适配层接口：`chat(messages, **options)` 返回统一结构（内容、用量、结束原因）。
说明哪些字段必须统一、哪些差异允许暴露给上层，并给出一个「某厂商不支持流式」时的降级方案。""",
                "quiz_note": "本节 6 道题：2 道基础理解（兼容的含义、为什么要适配层）+ 2 道代码阅读（读 endpoint 拼接、读能力开关）+ 2 道应用练习（改配置、设计接口）。",
                "summary": """兼容协议统一的是请求与响应格式，不是模型能力。
业务代码只依赖自己的客户端接口，厂商差异收敛在配置与适配层。
独有能力当增强项，不能成为主链路的必要条件。""",
                "next_lesson": "下一节把 Base URL、模型名与请求响应字段对齐到一次真实调用。",
                "knowledge_points": [
                    {
                        "code": "llm-api-02-01",
                        "name": "OpenAI 兼容协议与适配层",
                        "goal": "能解释兼容协议的边界并用配置隔离厂商差异。",
                        "minutes": 30,
                        "criteria": "能说出兼容的三项内容与至少两个差异点，并能用配置表切换厂商。",
                        "requires": ["llm-api-01-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-02-01-1",
                        "kp": 0,
                        "title": "只改配置换厂商",
                        "description": "把示例改成从字典取当前厂商（默认 provider_a），通过一个变量切换到 local，输出应随之变化。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''CURRENT = "local"
provider = PROVIDERS[CURRENT]
payload = build_payload(provider, [{"role": "user", "content": "你好"}])
print(CURRENT, build_endpoint(provider["base_url"]), payload)''',
                        "explanation": "切换厂商只动一个配置项；函数体完全不变，这就是适配层的最小形态。",
                    },
                    {
                        "code": "llm-ex-02-01-2",
                        "kp": 0,
                        "title": "兼容与能力的边界",
                        "description": "某厂商支持「图片输入」但兼容协议里没有该字段，你要在项目里用它，怎么设计才不影响换厂商？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''把它做成可选能力：在适配层里声明 capability（如 supports_vision），上层只判断能力是否存在；
不支持时走降级路径（提示用户改用文字描述，或换用支持该能力的厂商）。
绝不在业务代码里直接拼厂商专有字段，也不把「必须支持图片」写成产品硬前提。''',
                        "explanation": "核心是「能力探测 + 明确降级」：兼容层保持最小公共集，专有能力按可选增强处理。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-02-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "「OpenAI 兼容 API」通常指什么？",
                        "options": [
                            ("A", "请求路径、鉴权方式与请求响应 JSON 字段保持一致"),
                            ("B", "模型权重与 OpenAI 相同"),
                            ("C", "价格与 OpenAI 相同"),
                            ("D", "必须安装 OpenAI 官方 SDK 才能调用"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "兼容的是接口契约，模型、价格、限速都可能不同；也不需要官方 SDK，用 HTTP 客户端即可。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-02-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "不同厂商之间常见的差异有哪些？（多选）",
                        "options": [
                            ("A", "模型名称"),
                            ("B", "支持的采样参数"),
                            ("C", "计费单位与速率限制"),
                            ("D", "messages 的基本结构与 role 取值"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "messages 的 role/content 结构属于兼容层共识，正是它能被统一的原因。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-02-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`base_url.rstrip(\"/\")` 的作用是？",
                        "options": [
                            ("A", "去掉末尾斜杠，避免拼出双斜杠路径"),
                            ("B", "去掉协议前缀"),
                            ("C", "转成小写"),
                            ("D", "补上 /v1"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`rstrip` 只裁剪末尾字符；路径拼接的常见坑就是多一个斜杠导致 404。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-02-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中对 `provider_b` 生成的 payload 缺少 `top_p`，原因是？",
                        "options": [
                            ("A", "该厂商的 `supports_top_p` 为 False，按能力开关跳过"),
                            ("B", "代码有 bug，漏加参数"),
                            ("C", "`top_p` 只能用于本地模型"),
                            ("D", "`top_p` 是必填项，缺失会报错"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "这是故意的能力适配：不支持的厂商不发该参数，避免被静默忽略或直接 400。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-02-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全拼接逻辑，使 `https://api.example-a.com/v1` 变成完整接口地址。横线处应填什么？\n\n```python\nurl = base_url.rstrip(\"/\") ____ \"/chat/completions\"\n```",
                        "options": [("A", "+"), ("B", ".join"), ("C", "%"), ("D", ".format")],
                        "answer": {"value": "A"},
                        "explanation": "字符串直接相加最直观；用 `os.path.join` 或 `urljoin` 也可，但要注意 `urljoin` 会替换路径段，需谨慎。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-02-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "产品要求「必须用 A 厂商独有的长文档能力」。你会怎么在架构上留出退路？",
                        "answer": {"value": "把该能力包装成独立接口（例如 `summarize_long_document`），在适配层声明为可选能力；主链路只依赖「总结文本」这一抽象动作。A 厂商不可用时，降级为「分片总结 + 二次汇总」，或切到别家可接受长上下文的分片方案。同时在配置里标注该能力只有 A 支持，部署时做启动校验：若配置了不支持的厂商，启动阶段就明确报错，而不是运行到用户请求时才失败。"},
                        "explanation": "思路是把「厂商专有能力」降级成「抽象能力 + 特定实现」，并让不支持的组合在上线前暴露。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-02-lesson-02",
                "objectives": """1. 能写出一个完整的兼容请求体，并解释每个字段；
2. 能区分 Base URL、路径与模型名三者的职责；
3. 能读懂响应里的 `choices`、`finish_reason` 与 `usage`；
4. 能根据 `finish_reason` 判断下一步该做什么。""",
                "why_learn": """90% 的「接口调不通」都出在这三件事上：地址拼错、模型名不存在、字段位置写错。
把一次请求的每个字段弄清楚，后面所有章节才有稳定的地基。""",
                "concepts": """**Base URL**：服务地址前缀，通常到 `/v1`，不含具体资源路径。
**模型名称**：厂商侧的唯一标识，写错通常是 404 或 400。
**messages**：消息数组，每条包含 `role` 与 `content`。
**choices**：响应里的候选结果数组，通常取第 0 个。
**finish_reason**：`stop` 正常结束、`length` 触达上限、`tool_calls` 请求调用工具。""",
                "plain": """一次调用就像寄快递：Base URL 是快递公司网点，路径是具体窗口，模型名是「寄哪种件」。
填错任何一项，包裹都到不了。回执上的 `finish_reason` 相当于「已签收 / 超重退回」，看到 `length` 就知道是被截断了，不是对方没回。""",
                "syntax": """**API 说明（一次最小请求）**

```python
requests_body = {
    "model": "chat-large",
    "messages": [{"role": "user", "content": "用一句话解释什么是 API"}],
    "temperature": 0.2,
    "max_tokens": 200,
}
# POST {base_url}/chat/completions
# Header: Authorization: Bearer <API_KEY>
```

- `model`、`messages` 必填；`temperature`、`max_tokens` 可选但建议显式给。
- `max_tokens` 限制的是**输出**长度，不含输入。
- 响应取 `data["choices"][0]["message"]["content"]`。""",
                "example_code": '''import json

BASE_URL = "https://api.example-a.com/v1"
MODEL = "chat-large"

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "你是简洁的技术助理，回答不超过两句话。"},
        {"role": "user", "content": "用一句话解释什么是 API"},
    ],
    "temperature": 0.2,
    "max_tokens": 200,
}

print("POST", BASE_URL + "/chat/completions")
print(json.dumps(payload, ensure_ascii=False, indent=2))

response = {
    "id": "chatcmpl-demo-001",
    "object": "chat.completion",
    "model": "chat-large",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "API 是程序之间约定好的调用方式。"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 46, "completion_tokens": 18, "total_tokens": 64},
}

choice = response["choices"][0]
print("内容:", choice["message"]["content"])
print("结束原因:", choice["finish_reason"])
print("用量:", response["usage"])''',
                "code_lines": """1. 把地址与模型名提成常量，避免同一个值散落在多处。
2. `payload` 的键名必须与协议一致：`model`、`messages` 都是小写。
3. `system` 消息放在最前面，用于设定角色与约束；`user` 才是本次问题。
4. `max_tokens` 只管输出，设太小会把正常回答截断成 `length`。
5. 响应固定从 `choices[0]` 取内容，多候选是少数场景。
6. `finish_reason` 决定后续动作：`stop` 可交付、`length` 要续写或放宽上限。
7. 示例用本地构造的响应模拟返回，便于在没有网络时理解结构。""",
                "output": """# 请求与响应
POST https://api.example-a.com/v1/chat/completions
{
  "model": "chat-large",
  "messages": [
    {"role": "system", "content": "你是简洁的技术助理，回答不超过两句话。"},
    {"role": "user", "content": "用一句话解释什么是 API"}
  ],
  "temperature": 0.2,
  "max_tokens": 200
}

# 响应（节选）
{"id":"chatcmpl-demo-001","object":"chat.completion","choices":[{"index":0,
"message":{"role":"assistant","content":"API 是程序之间约定好的调用方式。"},
"finish_reason":"stop"}],"usage":{"prompt_tokens":46,"completion_tokens":18,"total_tokens":64}}

# 程序输出
内容: API 是程序之间约定好的调用方式。
结束原因: stop
用量: {'prompt_tokens': 46, 'completion_tokens': 18, 'total_tokens': 64}""",
                "mistakes": """- 把路径写成 `{base_url}/v1/chat/completions`，而 `base_url` 已含 `/v1`。
- 模型名带空格或大小写不一致，返回「模型不存在」。
- 把 `messages` 写成字符串，接口直接 400。
- 忘记 `max_tokens`，长回答被默认上限截断。
- 只看 `content` 不看 `finish_reason`，把截断当成「模型只会说这么多」。""",
                "error_analysis": """`400 {"error": {"message": "model not found"}}`
—— 模型名写错或该 Key 无权访问该模型。用厂商文档里的准确名称，并确认 Key 的权限范围。

`404` 且路径看起来「很对」
—— `base_url` 与路径重复或缺少 `/v1`。打印最终 URL 逐字符比对。

回答中途断句，`finish_reason` 为 `length`
—— 触达 `max_tokens`。调大上限或让模型分段输出，不要直接拼接下一段而丢掉上下文。""",
                "beginner_practice": """1. 把 `temperature` 改成 0，`max_tokens` 改成 20，观察 `finish_reason` 的变化。
2. 在 payload 里加一个 `stop` 字段限制结束词，说明它解决什么问题。""",
                "advanced_practice": """写一个函数 `explain(response) -> dict`：输入一份响应，输出 `{content, finish_reason, usage, truncated}`，
要求对缺失字段有合理默认值，并说明为什么 `truncated` 不能只看 `max_tokens` 配置。""",
                "quiz_note": "本节 6 道题：2 道基础理解（字段职责、finish_reason 含义）+ 2 道代码阅读（读 payload、读 choices）+ 2 道应用练习（改参数、写解析函数）。",
                "summary": """Base URL 到 `/v1`，路径单独拼，模型名由配置给。
响应取 `choices[0].message.content`，并同时看 `finish_reason` 与 `usage`。
`max_tokens` 限制输出长度，触达时结束原因是 `length`。""",
                "next_lesson": "下一章处理 Key：它从哪里来、怎么存，才不算把密码写在便签上。",
                "knowledge_points": [
                    {
                        "code": "llm-api-02-02",
                        "name": "请求响应结构与结束原因",
                        "goal": "能组织正确的兼容请求并解析响应关键字段。",
                        "minutes": 35,
                        "criteria": "能独立写出带 system/user 的请求体，并解释 finish_reason 三种取值的处理方式。",
                        "requires": ["llm-api-02-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-02-02-1",
                        "kp": 0,
                        "title": "补一个解析函数",
                        "description": "实现 `parse(response)`，返回 `(content, finish_reason, total_tokens)`，对缺失字段给出默认值。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''def parse(response: dict) -> tuple[str, str, int]:
    choices = response.get("choices") or []
    if not choices:
        return "", "empty", 0
    choice = choices[0]
    content = (choice.get("message") or {}).get("content") or ""
    usage = response.get("usage") or {}
    return content, choice.get("finish_reason", "unknown"), usage.get("total_tokens", 0)''',
                        "explanation": "真实接口在异常或内容审核时可能返回空 choices，解析层必须兜住，避免上层在索引时报错。",
                    },
                    {
                        "code": "llm-ex-02-02-2",
                        "kp": 0,
                        "title": "为什么被截断",
                        "description": "用户说「你的回答只写了一半就停了」，你怎么判断是模型问题还是配置问题？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''先看响应的 finish_reason：是 length 说明触达 max_tokens，属于配置问题，调大上限或让模型分段输出；
是 stop 但内容确实短，则可能是 Prompt 要求过严（如「两句话内」）或模型遵循度问题，需要改 Prompt 并跑对比；
若两者都不是（如 content 为空、choices 为空），检查是否触发内容审核或超时，结合 request_id 与日志定位。''',
                        "explanation": "先分清「被截断」与「本来就短」，判断依据是 finish_reason，而不是阅读感受。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-02-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`max_tokens` 限制的是什么？",
                        "options": [
                            ("A", "输出（completion）的 token 上限"),
                            ("B", "输入与输出之和"),
                            ("C", "每次请求的字符数"),
                            ("D", "并发请求数"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "它只限制生成部分；输入长度由上下文窗口约束，两者不是同一个参数。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-02-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "响应里的 `usage` 字段通常包含哪些信息？（多选）",
                        "options": [
                            ("A", "输入 token 数"),
                            ("B", "输出 token 数"),
                            ("C", "总计 token 数"),
                            ("D", "本次调用的金额"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "金额需要自己按单价换算；不同厂商单价不同，接口一般只给 token 数。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-02-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中把 `system` 消息放在 `user` 之前，作用是？",
                        "options": [
                            ("A", "让模型先接受角色与约束，再处理具体问题"),
                            ("B", "提高接口响应速度"),
                            ("C", "减少 token 消耗"),
                            ("D", "绕过内容审核"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "system 用于设定行为边界，位置在前更符合协议惯例，也更稳定。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-02-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "若响应里 `choices` 为空数组，示例代码 `response[\"choices\"][0]` 会怎样？",
                        "options": [
                            ("A", "抛出 IndexError"),
                            ("B", "返回空字符串"),
                            ("C", "返回 None"),
                            ("D", "自动重试一次"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "这正是解析层要加保护的原因：先判空再取下标，否则一次异常响应就会让接口 500。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-02-02-5",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把模型名写在调用处的 f-string 里，比放进配置更好维护。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "模型名属于环境相关配置，散落在代码里会导致换模型要改多处，也让灰度与回滚变困难。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-02-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如何用「打印最终 URL + payload + 响应状态」这三样东西快速定位接口调不通的问题？",
                        "answer": {"value": "先看最终 URL：协议、域名、是否重复 `/v1`、路径是否拼成 `/chat/completions`，与文档逐字符比对；再看 payload：`model` 是否存在、`messages` 是否是数组、字段名大小写是否正确；最后看状态码与响应体：401/403 指向鉴权，404 指向路径或模型名，400 多半是字段结构问题，429 是限流。三样一起打印，能覆盖绝大多数「调不通」的场景，也方便复制给厂商排查。"},
                        "explanation": "定位顺序是「地址 → 结构 → 状态码」，从外到内逐层排除，避免一上来就怀疑模型。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "llm-api-03",
        "title": "API Key 管理与安全",
        "description": "Key 等价于钱包，处理方式和密码一样严格。",
        "order_index": 3,
        "lessons": [
            {
                "code": "llm-api-03-lesson-01",
                "objectives": """1. 知道 Key 应该存在哪里、绝不能出现在哪里；
2. 会用 `os.environ` 与 `.env` 文件读取 Key；
3. 能配置 `.gitignore` 并写一个启动自检；
4. 能解释「不落库、不进仓库、不进日志」的具体含义。""",
                "why_learn": """Key 泄漏最常见的方式不是被黑客攻破，而是自己提交到了仓库、打进了日志、贴进了截图。
这些泄漏一旦发生，往往是别人先发现账单变高。""",
                "concepts": """**环境变量**：进程级配置，不随代码分发；`os.environ["KEY"]` 读取。
**`.env` 文件**：本地开发存放环境变量的文件，必须加入 `.gitignore`。
**不落库**：Key 不写进数据库的业务字段；确需存储时用加密列并限权。
**不进日志**：打印配置时只输出前 4 位与长度，绝不输出完整值。
**启动自检**：启动时校验 Key 是否存在，缺失就立刻失败。""",
                "plain": """Key 就像家里的钥匙：可以放在自己口袋（环境变量），也可以放在门口钥匙盒（`.env`），
但绝不能贴在门上（写进代码）、也不能拍照发群里（提交进仓库）。
更稳妥的做法是配一把「随时能换」的钥匙——用错了立刻换掉，损失可控。""",
                "syntax": """**API 说明（读取 Key 的三种写法）**

```python
import os

api_key = os.environ.get("LLM_API_KEY")
if not api_key:
    raise RuntimeError("缺少环境变量 LLM_API_KEY")

def mask(secret: str) -> str:
    return secret[:4] + "*" * (len(secret) - 4)
```

- `os.environ.get` 缺失时返回 `None`，比 `os.environ[...]` 更好控制报错信息。
- 校验放在读取处，缺失即失败，避免带着空 Key 跑下去。
- 任何要打印的地方都用 `mask`，不直接输出原值。

**仓库防护**

```text
# .gitignore
.env
.venv/
```

- `.env` 只留在本机；仓库里提交一份 `.env.example`，只写键名与说明。
- 已经误提交过 `.env` 的仓库，要先轮换 Key，再清理历史。""",
                "example_code": '''import os

REQUIRED = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")


def mask(secret: str) -> str:
    if len(secret) <= 4:
        return "*" * len(secret)
    return secret[:4] + "*" * (len(secret) - 4)


def load_config() -> dict:
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"缺少环境变量：{', '.join(missing)}")
    return {
        "api_key": os.environ["LLM_API_KEY"],
        "base_url": os.environ["LLM_BASE_URL"],
        "model": os.environ["LLM_MODEL"],
    }


config = load_config()
print("模型:", config["model"])
print("地址:", config["base_url"])
print("Key:", mask(config["api_key"]), f"(长度 {len(config['api_key'])})")''',
                "code_lines": """1. 把必需项列成元组，缺失检查就有了唯一来源。
2. `os.environ.get` 逐个检查，收集全部缺失项再报错，比逐个报更能一次改完。
3. 报错只写变量名，不写值，避免把密钥带进异常信息与日志。
4. `mask` 保留前 4 位便于人工确认「用的是哪把钥匙」，其余全遮。
5. 长度单独打印，可用于判断是否粘贴时被截断。
6. 配置文件只在启动时读一次，运行期不再读环境，避免中途变化导致行为不一致。""",
                "output": """# 环境变量设置（Windows PowerShell 与 macOS/Linux）
$env:LLM_API_KEY = "sk-demo-1234567890"
export LLM_API_KEY="sk-demo-1234567890"

# 程序输出（Key 已脱敏）
模型: chat-large
地址: https://api.example-a.com/v1
Key: sk-d****(长度 19)

# 缺少变量时的报错
RuntimeError: 缺少环境变量：LLM_API_KEY, LLM_MODEL""",
                "mistakes": """- 把 Key 直接写在 `main.py` 里，随手提交到仓库。
- `.env` 没加进 `.gitignore`，一次 `git add .` 就泄漏。
- 报错时把整个配置字典打进日志，Key 跟着一起进日志平台。
- 用 `os.environ["LLM_API_KEY"]` 且不做校验，缺失时抛 `KeyError`，报错信息难懂。
- 把 Key 前端传给浏览器，让「前端直接调模型」。""",
                "error_analysis": """`KeyError: 'LLM_API_KEY'`
—— 变量未设置，或设置在了另一个终端会话。用 `.get` + 显式报错更友好。

`401 Unauthorized`
—— Key 无效、过期或被撤销。先确认环境变量里没有多余空格与引号。

本地能跑、容器里 401
—— 容器没注入环境变量（`docker run -e` 或 compose 的 `env_file`）。部署时把必填项列成清单逐项核对。""",
                "beginner_practice": """1. 给项目加一个 `.env.example`，只写变量名与示例占位，不写真实值。
2. 把 `mask` 改成只保留后 4 位，说明哪种更难被猜出。""",
                "advanced_practice": """为项目设计一套密钥管理方案：本地开发、CI、生产三套环境分别怎么注入 Key，
如何做到「换 Key 不改代码、不重启业务进程也能生效」，并说明为什么生产不建议用 `.env` 文件。""",
                "quiz_note": "本节 6 道题：2 道基础理解（存哪里、为什么脱敏）+ 2 道代码阅读（读缺失检查、读 mask）+ 2 道应用练习（写 .env.example、设计注入方案）。",
                "summary": """Key 从环境变量读，缺失就启动失败。
`.env` 只用于本地且必须进 `.gitignore`，任何输出都要脱敏。
不落库、不进仓库、不进日志，是三条硬规则。""",
                "next_lesson": "下一节讲 Key 已经泄漏了怎么办：止损、轮换与最小权限。",
                "knowledge_points": [
                    {
                        "code": "llm-api-03-01",
                        "name": "Key 的环境变量管理与脱敏",
                        "goal": "能从环境变量安全读取 Key 并做到输出脱敏。",
                        "minutes": 30,
                        "criteria": "能写出带缺失校验与脱敏的配置读取函数，并说明三条硬规则。",
                        "requires": ["llm-api-02-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-03-01-1",
                        "kp": 0,
                        "title": "写一个配置读取函数",
                        "description": "实现 `load_config()`：读取 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`，缺失时一次性报出全部缺失项。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''import os

REQUIRED = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")


def load_config() -> dict:
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"缺少环境变量：{', '.join(missing)}")
    return {name: os.environ[name] for name in REQUIRED}''',
                        "explanation": "一次性收集缺失项，部署时一轮就能补齐，不用反复重启试错。",
                    },
                    {
                        "code": "llm-ex-03-01-2",
                        "kp": 0,
                        "title": "哪些地方会漏 Key",
                        "description": "列出项目中可能泄漏 Key 的五个位置，并各写一句防护措施。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 源码：只从环境变量读，Code Review 检查 `sk-` 字样；
② 版本库：`.env` 进 `.gitignore`，加 pre-commit 扫描；
③ 日志：打印配置时统一走 mask 函数；
④ 异常信息：请求异常只记状态码与 request_id，不带 Authorization 头；
⑤ 前端与截图：Key 只在服务端使用，接口不返回、文档示例用占位符。''',
                        "explanation": "泄漏点分布在「代码、仓库、日志、异常、对外暴露」五处，防护要逐个堵。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-03-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "课程要求 API Key 从哪里读取？",
                        "options": [
                            ("A", "环境变量"),
                            ("B", "代码常量"),
                            ("C", "前端 localStorage"),
                            ("D", "README 里的示例"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "环境变量是唯一既能配置又不进代码与仓库的方式；前端与文档都属于公开位置。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-03-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些位置绝对不能出现完整 Key？（多选）",
                        "options": [
                            ("A", "源码文件"),
                            ("B", "Git 仓库历史"),
                            ("C", "应用日志"),
                            ("D", "服务端环境变量"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "环境变量是唯一允许的存放位置；其余三处一旦留下痕迹就等同泄漏。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-03-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `mask` 对长度 3 的字符串返回什么？",
                        "options": [
                            ("A", "`***`"),
                            ("B", "空字符串"),
                            ("C", "前 4 位加星号"),
                            ("D", "抛异常"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "长度不超过 4 时整体打码，避免「保留前 4 位」反而把短密钥全暴露。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-03-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "把 `os.environ.get(name)` 改成 `os.environ[name]` 会带来什么变化？",
                        "options": [
                            ("A", "缺失时直接抛 KeyError，无法一次性收集全部缺失项"),
                            ("B", "性能更好且更安全"),
                            ("C", "可以读取 .env 文件"),
                            ("D", "没有任何区别"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`[]` 在缺失时立刻抛异常，循环中断，用户只能一个个试；`.get` 才能先收集再统一报错。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-03-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全脱敏函数，使输出只保留前 4 位。横线处应填什么？\n\n```python\ndef mask(secret):\n    return secret[____] + \"*\" * (len(secret) - 4)\n```",
                        "options": [("A", ":4"), ("B", "0"), ("C", ":3"), ("D", "-4")],
                        "answer": {"value": "A"},
                        "explanation": "切片 `:4` 取前四个字符；`-4` 会取末尾，不适合「标识前缀」的用途。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-03-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "同事说「`.env` 提交上去没事，仓库是私有的」。你怎么回应并给出替代方案？",
                        "answer": {"value": "私有仓库仍有泄漏面：成员变动、误 fork、CI 日志、本地克隆、外包协作都会扩散。正确做法是：`.env` 写入 `.gitignore`，仓库只提交 `.env.example`（只含变量名与占位符）；真实值通过本地环境变量、CI 的 secret 机制、生产的密钥管理服务注入；再加一条 pre-commit 或 CI 扫描规则，命中疑似密钥格式就阻断提交。如果已经提交过，还需要清理 Git 历史并轮换 Key，因为「删掉文件」不等于「从历史里消失」。"},
                        "explanation": "重点不是指出对方错，而是给出「可执行的三件套」：忽略文件、示例文件、扫描规则。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "llm-api-03-lesson-02",
                "objectives": """1. 能按「止损 → 轮换 → 复盘」处理 Key 泄漏；
2. 能解释为什么按环境、按用途拆分 Key；
3. 能设计最小权限：只给需要的模型与额度；
4. 能说清泄漏后为什么必须查账单与用量。""",
                "why_learn": """Key 一旦离开你的机器，就再也没有「收回来」这一说。
能不能把损失控制在一顿饭钱，取决于泄漏后十分钟内做了什么。""",
                "concepts": """**止损**：立即在控制台撤销（revoke）旧 Key，让泄漏值立刻失效。
**轮换**：为新 Key 设定有效期与责任人，定期更换而不是「一直用同一把」。
**最小权限**：按环境（dev/staging/prod）、按用途（对话/批处理）分 Key，只开必需模型。
**额度与告警**：设置每月上限与用量告警，异常消耗第一时间发现。
**复盘**：查清泄漏路径（日志/仓库/截图），补上对应防护，否则会再犯。""",
                "plain": """钥匙丢了，第一件事是换锁，而不是追问「谁捡到了」。
换锁之后再做两件事：看看家里有没有少东西（查用量与账单），以及想想钥匙是怎么丢的（补防护）。
如果所有房间共用一把钥匙，换锁就得全换——所以按用途分钥匙，能把损失关在一个房间里。""",
                "syntax": """**API 说明（泄漏处置清单，按顺序执行）**

```text
1. 控制台 revoke 旧 Key           -> 立刻生效
2. 生成新 Key，只写进环境变量      -> 不落盘、不截图
3. 重启服务 / 更新 secret          -> 确认新 Key 生效
4. 查用量与账单异常                -> 记录时间窗与消耗
5. 定位泄漏路径并补防护            -> 加扫描、改日志、清历史
```

- 顺序不能反：先让旧 Key 失效，再排查。
- 新 Key 不要复用旧名字，便于在日志里区分。
- 排查时按「时间窗 + 模型 + 调用方」三个维度看用量。""",
                "example_code": '''from dataclasses import dataclass


@dataclass
class KeyPolicy:
    name: str
    env: str
    models: tuple[str, ...]
    monthly_limit: int


POLICIES = [
    KeyPolicy("dev-local", "dev", ("chat-small",), 200_000),
    KeyPolicy("ci-test", "ci", ("chat-small",), 100_000),
    KeyPolicy("prod-chat", "prod", ("chat-large", "chat-small"), 2_000_000),
]


def check(policy: KeyPolicy, model: str, used: int) -> list[str]:
    problems = []
    if model not in policy.models:
        problems.append(f"{policy.name} 不允许调用 {model}")
    if used >= policy.monthly_limit:
        problems.append(f"{policy.name} 已达月度上限 {policy.monthly_limit}")
    return problems


for policy in POLICIES:
    result = check(policy, "chat-large", used=150_000)
    print(policy.name, policy.env, "通过" if not result else result)''',
                "code_lines": """1. 用数据类描述「一把 Key 的权限」，把口头约定变成可执行规则。
2. `env` 字段让开发、CI、生产三套凭据彼此隔离，泄漏影响面被限制在一个环境。
3. `models` 是白名单：开发 Key 不该能调用最贵的模型。
4. `monthly_limit` 是额度护栏，比事后看账单更早生效。
5. `check` 返回问题列表而不是布尔值，便于一次性告知全部违规点。
6. 逐条打印检查结果，可直接用于上线前自检脚本。""",
                "output": """# 示例输出
dev-local dev 通过
ci-test ci 通过
prod-chat prod 通过

# 换成越权调用时的输出
dev-local dev ['dev-local 不允许调用 chat-large']
ci-test ci ['ci-test 不允许调用 chat-large', 'ci-test 已达月度上限 100000']""",
                "mistakes": """- 发现泄漏先去查原因，几小时后才撤销，被盗刷一整天。
- 新 Key 和旧 Key 用同一个变量名且没重启服务，实际仍在使用旧值。
- 所有环境共用一把 Key，测试环境的日志泄漏直接暴露生产额度。
- 只撤销 Key 不查用量，错过账单申诉与异常调用分析的时间窗。
- 撤销后没有更新 CI/其他服务，第二天构建全红却找不到原因。""",
                "error_analysis": """撤销后立刻全部 401
—— 预期行为。需要同步更新所有部署环境的环境变量，并确认没有硬编码残留。

撤销后仍然能用
—— 该厂商存在缓存或网关延迟，或你撤销的是另一把 Key。用响应里的 Key 标识核对。

用量异常但找不到来源
—— Key 被他人使用。查看调用来源 IP 与模型分布，必要时关闭该 Key 并重建。""",
                "beginner_practice": """1. 给 `POLICIES` 增加一条 `batch-nightly` 策略，只允许批处理模型、额度单独计算。
2. 把 `check` 的上限判断改成「达到 80% 就告警」，说明为什么提前告警比到顶再拦更有用。""",
                "advanced_practice": """写一份《Key 泄漏应急响应》文档：从发现到恢复的分工与时间目标（例如 5 分钟内撤销、30 分钟内轮换完成），
并给出复盘模板，要求包含泄漏路径、暴露时长、异常用量与改进项。""",
                "quiz_note": "本节 6 道题：2 道基础理解（处置顺序、最小权限）+ 2 道代码阅读（读策略表、读 check）+ 2 道应用练习（加策略、写应急文档）。",
                "summary": """泄漏后先撤销再排查，顺序不能反。
按环境与用途拆 Key，配合模型白名单与额度上限，把影响关进小房间。
每次泄漏都要复盘路径，否则同一个洞会被踩第二次。""",
                "next_lesson": "下一章开始真正发请求：用 httpx 打通一次调用。",
                "knowledge_points": [
                    {
                        "code": "llm-api-03-02",
                        "name": "Key 轮换与最小权限",
                        "goal": "能设计按环境隔离、按模型限权的 Key 策略并处理泄漏。",
                        "minutes": 30,
                        "criteria": "能写出泄漏处置的五个步骤，并给出至少三条最小权限措施。",
                        "requires": ["llm-api-03-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "llm-ex-03-02-1",
                        "kp": 0,
                        "title": "加一条批处理策略",
                        "description": "新增 `batch-nightly` 策略：只允许 `chat-small`，额度 500000，环境为 `batch`。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''POLICIES.append(
    KeyPolicy("batch-nightly", "batch", ("chat-small",), 500_000)
)''',
                        "explanation": "策略是数据，增加一条不需要改检查逻辑，这正是把权限写成表的价值。",
                    },
                    {
                        "code": "llm-ex-03-02-2",
                        "kp": 0,
                        "title": "泄漏后的十分钟",
                        "description": "监控发现某 Key 在 10 分钟内调用了 3 万次，你按什么顺序处理？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''① 立即 revoke 该 Key（止损优先，先断血）；
② 生成新 Key 并更新部署环境变量，重启或热更新 secret，确认业务恢复；
③ 拉取该 Key 的调用日志：来源 IP、模型、时间窗、输入样本，判断是泄漏还是代码缺陷（如循环未退出）；
④ 评估消耗并联系厂商说明情况，必要时申请额度调整；
⑤ 复盘泄漏路径：仓库、日志、截图、第三方依赖，补上扫描与脱敏；
⑥ 更新应急预案，把这次的检测时间与处置时间记成基线。''',
                        "explanation": "顺序体现「先止血、再恢复、后归因」，同时把「是泄漏还是 bug」纳入判断，避免误判。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-llm-03-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "发现 Key 泄漏后第一步应该做什么？",
                        "options": [
                            ("A", "立即在控制台撤销该 Key"),
                            ("B", "先查是谁泄漏的"),
                            ("C", "先通知全公司"),
                            ("D", "先把日志删掉"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "止损优先：撤销让泄漏值立刻失效，之后才有时间从容排查。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-03-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "最小权限的具体做法包括哪些？（多选）",
                        "options": [
                            ("A", "按环境分配不同 Key"),
                            ("B", "只开放需要调用的模型"),
                            ("C", "设置月度额度上限"),
                            ("D", "把生产 Key 发给外包方便联调"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "把生产 Key 给外部人员与最小权限完全相反，属于典型的高危操作。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-llm-03-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`check` 返回列表而不是布尔值，好处是？",
                        "options": [
                            ("A", "能一次告知全部违规点，便于一起修"),
                            ("B", "运行更快"),
                            ("C", "可以避免异常"),
                            ("D", "支持并发调用"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "只返回 True/False 时用户要反复试；返回问题列表能一次给出所有需要修的地方。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-03-02-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`prod-chat` 策略允许调用 `chat-large`，`used=150000` 时输出是什么？",
                        "options": [
                            ("A", "通过"),
                            ("B", "不允许调用 chat-large"),
                            ("C", "已达月度上限"),
                            ("D", "两条问题都会输出"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`chat-large` 在白名单内，且 15 万远小于 200 万上限，所以没有违规项。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-llm-03-02-5",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "撤销 Key 之后就不需要再查用量与账单了。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "撤销只能阻止后续调用，已经发生的消耗需要核对，用于评估损失、申诉与复盘。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-llm-03-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么建议生产 Key 与开发 Key 完全分开？请给出两个具体后果。",
                        "answer": {"value": "① 影响面：开发机的 Key 常出现在日志、截图、调试脚本里，泄漏概率高；若与生产共用，一次泄漏就直接暴露生产额度与生产数据权限。② 额度与排查：共用 Key 时用量混在一起，无法判断异常消耗来自测试还是线上；分开后可以按 Key 看用量、设不同上限、独立轮换。③ 变更安全：轮换生产 Key 需要走发布流程，开发 Key 可以随时换，混用会让轮换变得危险。"},
                        "explanation": "本质是把「高泄漏概率的低权限凭据」与「低泄漏概率的高权限凭据」隔离开。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
