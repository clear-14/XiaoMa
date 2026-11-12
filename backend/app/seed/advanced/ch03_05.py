"""Python 进阶与工程实践：第 3—5 章（推导式、迭代器与生成器、装饰器）。"""

CHAPTERS: list[dict] = [
    {
        "code": "python-advanced-03",
        "title": "推导式",
        "description": "用一行表达式完成「遍历 + 过滤 + 转换」。",
        "order_index": 3,
        "lessons": [
            {
                "code": "python-advanced-03-lesson-01",
                "objectives": """1. 会把 for 循环改写成列表推导式；
2. 会写带 if 过滤和 if/else 分支的推导式；
3. 会写字典推导式与集合推导式；
4. 知道什么时候不该用推导式。""",
                "why_learn": """数据处理里最常见的动作是「把一个列表变成另一个列表」：
筛选未完成任务、把标题转成大写、从记录里抽出某个字段。
用循环写要 4 行，用推导式 1 行，而且意图更清楚——读的人一眼看出这是在构造新列表。""",
                "concepts": """**推导式（comprehension）** 是用一个表达式构造新容器的语法，四种形式：
列表 `[...]`、字典 `{k: v ...}`、集合 `{...}`、生成器 `(...)`。
结构是 `[表达式 for 变量 in 可迭代对象 if 条件]`，`if` 可选。
**过滤**写成末尾 `if`，**转换**写在最前面的表达式里，两者可以同时存在。
推导式产生的是新对象，不会修改原数据。""",
                "plain": """推导式像流水线的一句话说明书：「把每个苹果削皮，只留下没坏的，装一筐」。
传统循环是分三步写：准备空筐、逐个检查、合格的放进去。推导式把这些步骤压成一句，
但代价是可读性——嵌套超过两层就该换回普通循环。""",
                "syntax": """```python
[表达式 for 变量 in 可迭代对象]              # 转换
[表达式 for 变量 in 可迭代对象 if 条件]      # 过滤
[甲 if 条件 else 乙 for 变量 in 可迭代对象]  # 二选一（注意 if 在前）
{键: 值 for 变量 in 可迭代对象}              # 字典
{元素 for 变量 in 可迭代对象}                # 集合（自动去重）
```
注意：过滤的 `if` 在 `for` 后面，二选一的 `if/else` 在 `for` 前面，写反会报语法错误。""",
                "example_code": '''tasks = [
    {"title": "写周报", "done": False, "minutes": 30},
    {"title": "交报表", "done": True, "minutes": 45},
    {"title": "订会议室", "done": False, "minutes": 10},
]

pending_titles = [task["title"] for task in tasks if not task["done"]]
print(pending_titles)

labels = [f"{task['title']}✓" if task["done"] else task["title"] for task in tasks]
print(labels)

title_by_state = {
    task["title"]: ("完成" if task["done"] else "待办") for task in tasks
}
print(title_by_state)

states = {task["done"] for task in tasks}
print(states)

total = sum(task["minutes"] for task in tasks if not task["done"])
print("待办总时长", total)

matrix = [[row * col for col in range(1, 4)] for row in range(1, 3)]
print(matrix)

long_titles = [
    task["title"]
    for task in tasks
    if len(task["title"]) >= 3
    if task["minutes"] >= 20
]
print(long_titles)''',
                "code_lines": """1. `pending_titles` 用末尾的 `if not task["done"]` 过滤，只保留未完成的标题。
2. `labels` 用的是 `甲 if 条件 else 乙`，位置在 `for` 之前，表示逐项二选一，不是过滤。
3. `title_by_state` 是字典推导式：冒号左边是键，右边是值，一次构造出映射。
4. `states` 用集合推导式，`{True, False}` 自动去重，适合快速看有哪些取值。
5. `sum(...)` 里是生成器表达式，边算边加，不会先建一个完整列表。
6. `matrix` 是嵌套推导式：外层决定行，内层决定每一行的内容，读的时候从右往左看。
7. 最后一段连续写两个 `if`，等价于「并且」，比用 `and` 更易读，也便于逐条加条件。""",
                "output": """['写周报', '订会议室']
['写周报', '交报表✓', '订会议室']
{'写周报': '待办', '交报表': '完成', '订会议室': '待办'}
{False, True}
待办总时长 40
[[1, 2, 3], [2, 4, 6]]
['写周报', '交报表']""",
                "mistakes": """- 把过滤条件写到 `for` 前面：`[x if x > 0 for x in nums]` 是语法错误。
- 在推导式里做副作用（打印、写文件），这属于滥用。
- 嵌套超过两层还硬用推导式，可读性远低于普通循环。
- 用推导式构造超大列表，内存占用高，应该用生成器表达式。
- 忘了推导式产生新对象，误以为修改了原列表。""",
                "error_analysis": """`SyntaxError: invalid syntax`
—— 常见于 `if` 位置写错。过滤要写 `[x for x in xs if 条件]`，二选一要写 `[甲 if 条件 else 乙 for x in xs]`。

`NameError: name 'task' is not defined`
—— 在推导式外使用了推导式内部的变量。推导式的循环变量作用域被限制在表达式内部，外部访问不到。

`TypeError: unhashable type: 'list'`
—— 用列表推导式去构造集合或字典键，元素本身必须是可哈希的（数字、字符串、元组）。""",
                "beginner_practice": """1. 给定 `nums = [3, -1, 4, -5, 9]`，用推导式得到所有正数的平方。
2. 用字典推导式把 `["a", "bb", "ccc"]` 变成「字符串: 长度」的映射。""",
                "advanced_practice": """有一批任务记录，每条含 `title`、`done`、`minutes`。
用一条推导式得到「未完成任务按分钟数降序的标题列表」，要求只写一条语句，
并解释为什么这里不适合再用嵌套推导式。""",
                "quiz_note": "本节 6 道题：重点区分「过滤 if」与「二选一 if/else」的位置差异。",
                "summary": """推导式 = `[表达式 for 变量 in 可迭代 if 条件]`；
过滤的 if 在后，二选一的 if/else 在前；字典用冒号、集合自动去重。
判断标准：**一眼能读懂的用推导式，需要想两秒以上的换回循环**。""",
                "next_lesson": "下一节讲迭代协议与生成器：`for` 凭什么能遍历任何对象，以及怎么用 `yield` 处理放不进内存的数据。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-03-01",
                        "name": "列表/字典/集合推导式",
                        "goal": "能把循环改写成推导式，正确使用过滤与二选一，并判断可读性边界。",
                        "minutes": 30,
                        "criteria": "能写出带过滤与转换的推导式，并说明等价循环写法。",
                        "requires": ["python-advanced-02-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-03-01-1",
                        "kp": 0,
                        "title": "正数平方",
                        "description": "给定 nums = [3, -1, 4, -5, 9]，用推导式得到所有正数的平方，并写出等价的 for 循环。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''nums = [3, -1, 4, -5, 9]
squares = [n ** 2 for n in nums if n > 0]
print(squares)  # [9, 16, 81]

squares_loop = []
for n in nums:
    if n > 0:
        squares_loop.append(n ** 2)''',
                        "explanation": "过滤条件 n > 0 放在 for 之后，转换 n ** 2 放在最前面。",
                    },
                    {
                        "code": "adv-ex-03-01-2",
                        "kp": 0,
                        "title": "一条语句的排序结果",
                        "description": "用一条语句得到未完成任务按分钟降序的标题列表，并说明为什么不再嵌套推导式。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''pending = [
    task["title"]
    for task in sorted(tasks, key=lambda t: t["minutes"], reverse=True)
    if not task["done"]
]''',
                        "explanation": "排序在推导式外完成，推导式只做过滤与取值；把排序也塞进推导式会让读者难以分清执行顺序。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-03-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`[x * 2 for x in nums if x > 0]` 中，`if x > 0` 的作用是？",
                        "options": [
                            ("A", "把不满足条件的元素替换成 0"),
                            ("B", "只保留满足条件的元素参与表达式计算"),
                            ("C", "在结果里追加一个布尔值"),
                            ("D", "让表达式从右往左执行"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "末尾的 if 是过滤器，不满足条件的元素直接被跳过，不参与前面表达式的计算。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-03-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于推导式，下列说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "字典推导式用冒号分隔键和值"),
                            ("B", "集合推导式会自动去重"),
                            ("C", "推导式会原地修改原列表"),
                            ("D", "生成器表达式用圆括号，惰性求值"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "推导式一律产生新对象，不会原地修改，所以 C 错；其余三项都是事实。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-03-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码输出什么？
nums = [1, 2, 3, 4]
result = [n if n % 2 == 0 else n * 10 for n in nums]
print(result)''',
                        "answer": {
                            "reference": "输出 [10, 2, 30, 4]。偶数保留原值，奇数乘 10。",
                            "keywords": ["[10, 2, 30, 4]", "二选一", "偶数"],
                        },
                        "explanation": "这是二选一写法，每个元素都会产出一个结果，与过滤不同——长度与原列表相同。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-03-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`{task[\"title\"]: task[\"minutes\"] for task in tasks}` 得到的是一个字典。",
                        "answer": {"value": True},
                        "explanation": "花括号加冒号是字典推导式，键为标题、值为分钟数；若没有冒号则是集合推导式。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-03-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "用字典推导式把 [\"a\", \"bb\", \"ccc\"] 变成「字符串: 长度」的映射并打印。",
                        "answer": {
                            "reference": 'print({s: len(s) for s in ["a", "bb", "ccc"]})',
                            "keywords": ["{", "len(", "for s in"],
                        },
                        "explanation": "键用 s、值用 len(s)，一行即可；字典推导式必须在花括号里写冒号。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-03-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "什么情况下你会放弃推导式、改回普通 for 循环？请给出两个判断依据。",
                        "answer": {
                            "reference": "一是嵌套超过两层，读者要反复回看才能确定执行顺序；二是循环体里要做的不是「产生一个值」，而是打印、写库、发请求这类副作用。这两种情况用普通循环更清楚，也更好调试。",
                            "keywords": ["嵌套", "副作用", "可读性", "调试"],
                        },
                        "explanation": "核心是「推导式擅长表达值的转换，不擅长表达多步动作」。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    {
        "code": "python-advanced-04",
        "title": "迭代器与生成器",
        "description": "理解 for 循环背后的协议，用 yield 惰性产出数据。",
        "order_index": 4,
        "lessons": [
            {
                "code": "python-advanced-04-lesson-01",
                "objectives": """1. 说清 for 循环背后调用了什么；
2. 会自己实现 `__iter__` 与 `__next__`；
3. 会用生成器函数逐步产出数据；
4. 知道生成器为什么省内存，以及它只能遍历一次。""",
                "why_learn": """读 200 万行日志时，如果先 `readlines()` 全都装进列表，内存直接爆掉。
生成器按需产出，一次只在内存里放一行。这个能力也是后面流式接口、分批处理数据库结果的基础。""",
                "concepts": """**可迭代对象** 实现了 `__iter__`，能返回一个迭代器（列表、字典、字符串都是）。
**迭代器** 同时实现 `__iter__` 与 `__next__`，每次 `__next__` 返回下一个元素，
取完抛 `StopIteration` 表示结束。
`for` 循环做的事就是：先拿迭代器，再反复调 `__next__`，遇到 `StopIteration` 停止。
**生成器** 是包含 `yield` 的函数，调用它不执行函数体，而是返回一个生成器对象，每次取值才往前推进。""",
                "plain": """迭代器像「取号机」：你不问还剩几张，只管按一下「下一位」，取完了它会明确告诉你「没有了」。
生成器像「现做现卖的小摊」：不是提前做好一百份摆着，而是你要一份他做一份，
所以摊位再小也能一直供应。代价是——同一锅不能倒回去重来，生成器取完就空了。""",
                "syntax": """```python
class 迭代器:
    def __iter__(self):        # 返回迭代器本身
        return self

    def __next__(self):
        if 没有更多数据:
            raise StopIteration
        return 下一个值


def 生成器函数(参数):
    for 元素 in 数据源:
        yield 元素           # 产出一个值并暂停
```
`yield` 和 `return` 的区别：`return` 结束函数，`yield` 只是暂停，下次继续从这里往下走。""",
                "example_code": '''def read_batches(rows, size):
    """把一批记录按固定大小切块，边切边产出。"""
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


rows = [f"row-{index}" for index in range(1, 8)]
for chunk in read_batches(rows, 3):
    print(chunk)

counter = read_batches(rows, 3)
print(next(counter))
print(next(counter))

print(list(read_batches([], 3)))

class Countdown:
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value


print(list(Countdown(3)))''',
                "code_lines": """1. `def read_batches(rows, size):` 里有 `yield`，所以它是生成器函数，调用不会立刻执行。
2. `batch.append(row)` 先攒够一块，攒满就 `yield` 出去并清空，复用同一个列表变量名。
3. `if batch: yield batch` 处理最后不足一块的尾部数据，这一步最容易漏。
4. `for chunk in ...` 每次循环取一块，内存里同时只有一块数据。
5. `counter = read_batches(...)` 拿到生成器对象；`next(counter)` 手动推进，每次产出下一块。
6. `list(read_batches([], 3))` 是空输入，生成器一次都不产出，结果是空列表。
7. `Countdown` 自己实现了迭代协议：`__iter__` 返回自身，`__next__` 负责递减并抛 StopIteration。
8. `list(Countdown(3))` 能工作，是因为 list 会一直调 `__next__` 直到捕获 StopIteration。""",
                "output": """['row-1', 'row-2', 'row-3']
['row-4', 'row-5', 'row-6']
['row-7']
['row-1', 'row-2', 'row-3']
['row-4', 'row-5', 'row-6']
[]
[3, 2, 1]""",
                "mistakes": """- 生成器取完后再次遍历，得到空结果（生成器是一次性的）。
- 在生成器里用 `return 值` 想返回数据，实际只会终止迭代。
- 忘记抛 StopIteration，导致 `list()` 无限循环。
- 用 `len()` 取生成器长度，生成器没有长度。
- 把生成器传给多个函数，前一个消费掉后，后一个拿到的是空的。""",
                "error_analysis": """`TypeError: object of type 'generator' has no len()`
—— 生成器不知道总长度，只能边取边算。需要长度就先 `list()` 落地，但要考虑内存。

结果为空但代码没错
—— 生成器已经被消费过了。生成器不是列表，第二次遍历拿不到任何东西，需要重建。

`RuntimeError: generator raised StopIteration`
—— 在生成器内部手动 `raise StopIteration`，Python 3.7+ 会把它转成 RuntimeError。想让生成器结束，直接 `return`。""",
                "beginner_practice": """1. 写生成器 `squares(n)`，依次产出 1 到 n 的平方，用 `list()` 验证。
2. 写生成器 `take(iterable, k)`，只产出前 k 个元素，验证对无限序列也能用。""",
                "advanced_practice": """实现 `read_pairs(lines)`：两行一组产出 `(第一行, 第二行)`，奇数行时最后一组补 `None`。
要求全程不把整个输入读进列表，并说明为什么这个版本能处理超大文件。""",
                "quiz_note": "本节 6 道题：重点考「生成器一次性」与 StopIteration 的终止语义。",
                "summary": """`for` 会自动调用 `__iter__` 拿到迭代器，再反复 `__next__` 直到 StopIteration；
生成器函数用 `yield` 暂停并产出，天然实现迭代协议，省内存但只能遍历一次。
记住：**要长度或要重复遍历，就别用生成器**。""",
                "next_lesson": "下一节讲装饰器：怎样在不改函数体的情况下，给一批函数统一加上计时、重试或权限检查。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-04-01",
                        "name": "迭代协议与生成器",
                        "goal": "能实现 __iter__/__next__，能用 yield 写出惰性数据流并说明其限制。",
                        "minutes": 40,
                        "criteria": "能独立写出分批生成器，并解释生成器为什么只能遍历一次。",
                        "requires": ["python-advanced-03-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-04-01-1",
                        "kp": 0,
                        "title": "平方生成器",
                        "description": "写生成器 squares(n) 产出 1..n 的平方；再用 take(iterable, k) 只取前 k 个，验证对无限序列也能用。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''def squares(n):
    for value in range(1, n + 1):
        yield value ** 2


def take(iterable, k):
    count = 0
    for item in iterable:
        if count == k:
            return
        yield item
        count += 1


print(list(squares(4)))       # [1, 4, 9, 16]
print(list(take(squares(10 ** 9), 3)))  # [1, 4, 9]''',
                        "explanation": "take 用 return 提前结束生成器，因此对无限序列也安全；不能用 len() 或切片。",
                    },
                    {
                        "code": "adv-ex-04-01-2",
                        "kp": 0,
                        "title": "两行一组",
                        "description": "实现 read_pairs(lines)，两行一组产出元组，奇数行时最后补 None，且不把输入整体读入列表。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def read_pairs(lines):
    pending = None
    for line in lines:
        if pending is None:
            pending = line
            continue
        yield (pending, line)
        pending = None
    if pending is not None:
        yield (pending, None)''',
                        "explanation": "只用一个变量缓存上一行，内存恒定；尾部不足一对时补 None，避免丢数据。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-04-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "for 循环遍历一个对象时，第一步做了什么？",
                        "options": [
                            ("A", "调用对象的 __len__ 拿到长度"),
                            ("B", "调用 __iter__ 拿到迭代器"),
                            ("C", "直接调用 __next__"),
                            ("D", "把对象复制一份"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "for 先调 __iter__ 得到迭代器，之后反复调它的 __next__，直到 StopIteration。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-04-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于生成器，下列说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "包含 yield 的函数调用后返回生成器对象"),
                            ("B", "生成器可以被重复遍历多次"),
                            ("C", "生成器支持 len()"),
                            ("D", "生成器适合处理放不进内存的数据"),
                        ],
                        "answer": {"values": ["A", "D"]},
                        "explanation": "生成器是一次性的、没有长度，所以 B、C 错；惰性求值正是它省内存的原因。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-04-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码输出什么？
def gen():
    for n in range(3):
        yield n

g = gen()
print(list(g))
print(list(g))''',
                        "answer": {
                            "reference": "第一次输出 [0, 1, 2]，第二次输出 []。生成器取完就空了。",
                            "keywords": ["[0, 1, 2]", "[]", "一次"],
                        },
                        "explanation": "生成器内部记录着执行位置，取完后再遍历不会重新开始；需要复用就重新调用 gen()。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-04-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "在生成器函数里执行 `return 42`，调用方可以用 `value = next(gen)` 拿到 42。",
                        "answer": {"value": False},
                        "explanation": "生成器里的 return 只表示结束，会触发 StopIteration；next() 拿不到返回值。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-04-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写生成器 countdown(n)，从 n 递减到 1 逐个产出；用 list() 验证 countdown(3) 得到 [3, 2, 1]。",
                        "answer": {
                            "reference": '''def countdown(n):
    while n > 0:
        yield n
        n -= 1


print(list(countdown(3)))''',
                            "keywords": ["yield", "while", "递减"],
                        },
                        "explanation": "yield 之后函数暂停，下次从 n -= 1 继续；不需要手工维护迭代器状态类。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-04-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「把同一个生成器传给两个函数」通常是个 bug？请说明表现和修法。",
                        "answer": {
                            "reference": "生成器是一次性的，第一个函数遍历完就耗尽，第二个函数拿到空序列，表现为「统计结果为 0」这类静默错误。修法是每次需要时重新调用生成器函数，或者先把结果 list() 落地再共享——后者要评估内存是否可接受。",
                            "keywords": ["一次性", "耗尽", "重建", "内存"],
                        },
                        "explanation": "关键是说清「不报错但结果为空」这个隐蔽表现，以及重建或落地的取舍。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    {
        "code": "python-advanced-05",
        "title": "装饰器",
        "description": "用闭包包装函数，在不改函数体的前提下增加行为。",
        "order_index": 5,
        "lessons": [
            {
                "code": "python-advanced-05-lesson-01",
                "objectives": """1. 说清函数是一等公民意味着什么；
2. 会写闭包并解释它捕获了什么；
3. 会写不带参数和带参数的装饰器；
4. 会用 `functools.wraps` 保留原函数的元信息。""",
                "why_learn": """计时、重试、打印入参、检查权限——这些逻辑和业务无关，却要在很多函数里重复。
装饰器让你只写一次，然后用一行 `@` 挂到需要的函数上，函数体完全不动。""",
                "concepts": """**一等公民**：函数可以赋给变量、当参数传、当返回值返回。
**闭包**：内层函数引用了外层函数的变量，外层返回后这些变量依然被保留。
**装饰器**：接收一个函数、返回一个新函数的可调用对象，语法糖是 `@装饰器`。
`functools.wraps` 把原函数的 `__name__`、`__doc__` 复制到包装函数上，避免调试信息失真。
**带参数的装饰器** 是「返回装饰器的函数」，多了一层嵌套。""",
                "plain": """装饰器像给手机套壳：手机本身没变，但多了防摔、支架这些能力。
套壳的过程发生在「买回来之后、使用之前」——也就是函数定义时就被包好了，
所以调用方完全感知不到。闭包则是壳记住了你套的是哪台手机。""",
                "syntax": """```python
import functools


def 装饰器(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        前置动作
        result = func(*args, **kwargs)
        后置动作
        return result

    return wrapper


@装饰器
def 业务函数(...):
    ...


# 带参数
def 带参装饰器(参数):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ...
        return wrapper
    return decorator
```""",
                "example_code": '''import functools
import time


def logged(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}，参数 {args} {kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} 返回 {result!r}")
        return result

    return wrapper


def retry(times):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except ValueError as exc:
                    last_error = exc
                    print(f"第 {attempt} 次失败：{exc}")
            raise last_error

        return wrapper

    return decorator


@logged
def add(left, right):
    """两数相加。"""
    return left + right


print(add(2, 3))
print(add.__name__, add.__doc__)

calls = {"n": 0}


@retry(3)
def unstable():
    calls["n"] += 1
    if calls["n"] < 3:
        raise ValueError("暂时失败")
    return "成功"


print(unstable())''',
                "code_lines": """1. `logged` 接收一个函数，返回包装后的 `wrapper`，这是装饰器的标准形状。
2. `@functools.wraps(func)` 把原函数的名字与文档字符串复制过来，否则 `add.__name__` 会变成 wrapper。
3. `*args, **kwargs` 让包装函数能接住任意签名，不必为每个函数写不同版本。
4. `retry(times)` 返回 `decorator`，所以 `@retry(3)` 先算出装饰器，再作用到函数上，是三层结构。
5. `for attempt in range(1, times + 1)` 控制总尝试次数，避免无限重试。
6. `raise last_error` 在所有尝试都失败后抛出最后一次异常，不吞掉错误。
7. `print(add(2, 3))` 调用的是 wrapper，它先打印参数再真正执行加法。
8. `print(add.__name__, add.__doc__)` 验证 wraps 生效：仍是 add 与「两数相加。」。
9. `unstable()` 前两次抛异常被 retry 捕获，第三次成功返回，最终打印「成功」。""",
                "output": """调用 add，参数 (2, 3) {}
add 返回 5
5
add 两数相加。
第 1 次失败：暂时失败
第 2 次失败：暂时失败
成功""",
                "mistakes": """- 忘了 `functools.wraps`，导致函数名全变成 wrapper，日志和报错难以定位。
- 写成 `@retry` 而不是 `@retry(3)`，把数字当成被装饰的函数。
- 包装函数签名写成 `def wrapper():`，被装饰函数一有参数就报错。
- 在装饰器里吞掉异常不抛出，调用方以为成功。
- 重试无上限或没加退避，故障时把下游打垮。""",
                "error_analysis": """`TypeError: 'int' object is not callable`
—— `@retry(3)` 写成了 `@retry`，装饰器把 3 当成函数去调用。带参装饰器必须加括号。

`TypeError: wrapper() takes 0 positional arguments but 2 were given`
—— wrapper 没写 `*args, **kwargs`，无法转发原函数的参数。

`AttributeError: 'function' object has no attribute '__name__'`（少见但要警惕）
—— 自定义了返回非函数对象的装饰器却按函数使用。

函数名变成 `wrapper`、文档丢失
—— 没用 `functools.wraps`，元信息在包装时被覆盖。""",
                "beginner_practice": """1. 写装饰器 `timer(func)`，打印函数执行耗时（用 `time.perf_counter()`）。
2. 给 `add` 与另一个函数同时加上 `@timer`，确认两个都能正常计时。""",
                "advanced_practice": """实现 `@retry(times=3, exceptions=(ValueError,), delay=0.1)`，
要求：只重试指定异常、每次重试前等待 delay、全部失败后抛原异常，
并用 `functools.wraps` 保留元信息。""",
                "quiz_note": "本节 6 道题：重点考「带参装饰器为什么多一层」和 wraps 的作用。",
                "summary": """装饰器是「接收函数、返回函数」的可调用对象，`@` 只是语法糖；
闭包让包装函数记住原函数；`functools.wraps` 保留元信息；
带参数的装饰器要多包一层，返回的是装饰器而不是包装结果。""",
                "next_lesson": "下一节讲上下文管理器：`with` 怎么保证异常发生时资源也能释放。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-05-01",
                        "name": "闭包与装饰器",
                        "goal": "能写闭包与装饰器（含带参形式），并用 functools.wraps 保留元信息。",
                        "minutes": 40,
                        "criteria": "能独立写出带重试与计时的装饰器，并解释三层嵌套的调用顺序。",
                        "requires": ["python-advanced-04-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-05-01-1",
                        "kp": 0,
                        "title": "计时装饰器",
                        "description": "写 timer 装饰器，打印函数名与耗时（毫秒，保留 2 位小数），并保留原函数元信息。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''import functools
import time


def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        cost = (time.perf_counter() - start) * 1000
        print(f"{func.__name__} 耗时 {cost:.2f} ms")
        return result

    return wrapper''',
                        "explanation": "用 perf_counter 而不是 time()，精度更高且不受系统时钟调整影响。",
                    },
                    {
                        "code": "adv-ex-05-01-2",
                        "kp": 0,
                        "title": "可控重试装饰器",
                        "description": "实现 @retry(times=3, exceptions=(ValueError,), delay=0.1)：只重试指定异常，重试前等待，全部失败抛原异常。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''import functools
import time


def retry(times=3, exceptions=(ValueError,), delay=0.1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_error = exc
                    if attempt < times:
                        time.sleep(delay)
            raise last_error

        return wrapper

    return decorator''',
                        "explanation": "最后一次失败不再 sleep，直接抛出；异常元组限定范围，避免把编程错误也当临时故障重试。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-05-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "装饰器本质上是什么？",
                        "options": [
                            ("A", "一种特殊的类继承"),
                            ("B", "接收函数并返回新函数的可调用对象"),
                            ("C", "Python 解释器提供的编译指令"),
                            ("D", "只能用于类的语法"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "装饰器就是「输入函数、输出函数」的可调用对象，@ 只是把这种调用写成语法糖。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-05-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "使用 functools.wraps 能带来哪些好处？（多选）",
                        "options": [
                            ("A", "保留原函数的 __name__"),
                            ("B", "保留原函数的文档字符串"),
                            ("C", "让装饰后的函数运行更快"),
                            ("D", "便于日志和报错定位到真正的函数"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "wraps 只复制元信息，不影响执行速度，所以 C 错；其余三项正是它的用途。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-05-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码输出什么？
def wrapper(func):
    def inner():
        return f"<{func()}>"
    return inner

@wrapper
def hello():
    return "hi"

print(hello())''',
                        "answer": {
                            "reference": "输出 <hi>。hello 被替换成 inner，调用时先执行原函数拿到 hi 再加上尖括号。",
                            "keywords": ["<hi>", "替换", "inner"],
                        },
                        "explanation": "@wrapper 等价于 hello = wrapper(hello)，之后 hello 指向 inner。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-05-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`@retry(3)` 这种带参数的写法，retry 本身是装饰器函数，直接作用在被装饰函数上。",
                        "answer": {"value": False},
                        "explanation": "retry(3) 先返回真正的装饰器，再作用到函数上；retry 是「返回装饰器的函数」。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-05-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个装饰器 log_calls，在函数执行前打印「调用 函数名」，并保留原函数元信息。",
                        "answer": {
                            "reference": '''import functools


def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}")
        return func(*args, **kwargs)

    return wrapper''',
                            "keywords": ["functools.wraps", "*args", "func.__name__"],
                        },
                        "explanation": "没有 *args/**kwargs 就无法转发参数；没有 wraps 函数名会变成 wrapper。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-05-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么重试装饰器要限定「只重试哪些异常」，而不是捕获所有异常？",
                        "answer": {
                            "reference": "临时性故障（网络超时、锁冲突）重试有意义；而 TypeError、KeyError 这类是代码缺陷，重试只会把同一个错误重复三遍，还掩盖了真正的问题、拖慢失败速度。因此要显式列出可重试的异常类型。",
                            "keywords": ["代码缺陷", "重复", "掩盖", "异常类型"],
                        },
                        "explanation": "核心区分是「可自愈的临时故障」与「必然复现的代码错误」。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
]
