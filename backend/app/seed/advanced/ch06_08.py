"""Python 进阶与工程实践：第 6—8 章（上下文管理器、类型注解、虚拟环境）。"""

CHAPTERS: list[dict] = [
    {
        "code": "python-advanced-06",
        "title": "上下文管理器",
        "description": "用 with 保证资源一定被释放，包括异常路径。",
        "order_index": 6,
        "lessons": [
            {
                "code": "python-advanced-06-lesson-01",
                "objectives": """1. 说清 with 解决了什么问题；
2. 会实现 `__enter__` 与 `__exit__`；
3. 会用 `contextlib.contextmanager` 写轻量版本；
4. 知道 `__exit__` 返回 True 会吞掉异常，以及为什么通常不要这么做。""",
                "why_learn": """打开文件、借出数据库连接、加锁——这些资源必须释放。
手写 `try/finally` 能保证释放，但每个调用点都要重复一遍；一旦有人漏写，
连接池很快耗尽，问题还很难复现。with 把「释放」写进对象本身。""",
                "concepts": """**上下文管理器** 是实现了 `__enter__` 与 `__exit__` 的对象。
`with 表达式 as 变量:` 进入时调用 `__enter__`，它的返回值赋给变量；
离开时无论正常结束还是抛异常，都会调用 `__exit__`。
`__exit__(self, exc_type, exc, tb)` 三个参数描述异常，没有异常时都是 None。
`__exit__` 返回 True 表示「异常已被处理」，异常不会继续向外传播。
`contextlib.contextmanager` 允许用生成器函数写上下文管理器，代码更短。""",
                "plain": """上下文管理器像酒店的「入住—退房」流程：进门时前台给你房卡（`__enter__`），
出门时不管你是正常退房还是打破杯子跑掉，押金结算这一步一定会执行（`__exit__`）。
没有这套流程，就得每次自己记得去前台，忘一次账就乱了。""",
                "syntax": """```python
class 管理器:
    def __enter__(self):
        return 资源            # 返回值给 as 后面的变量

    def __exit__(self, exc_type, exc, tb):
        # 释放资源；返回 True 会吞掉异常
        return False


# 生成器写法
from contextlib import contextmanager


@contextmanager
def 管理器():
    资源 = 获取()
    try:
        yield 资源
    finally:
        释放(资源)
```""",
                "example_code": '''from contextlib import contextmanager


class Timer:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        import time

        self.start = time.perf_counter()
        print(f"[{self.name}] 开始")
        return self

    def __exit__(self, exc_type, exc, tb):
        import time

        cost = (time.perf_counter() - self.start) * 1000
        print(f"[{self.name}] 结束，耗时 {cost:.2f} ms")
        if exc_type is not None:
            print(f"[{self.name}] 发生异常：{exc_type.__name__}")
        return False


class Transaction:
    def __init__(self):
        self.committed = False

    def __enter__(self):
        print("开启事务")
        return self

    def commit(self):
        self.committed = True
        print("提交事务")

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            print("回滚事务")
            return False
        if not self.committed:
            self.commit()
        return False


@contextmanager
def open_scope(name):
    print(f"进入 {name}")
    try:
        yield name
    finally:
        print(f"退出 {name}")


with Timer("计算"):
    total = sum(range(100000))

with open_scope("作用域") as scope:
    print("内部", scope)

with Transaction() as tx:
    print("写第一条记录")

with Transaction() as tx:
    print("写第二条记录")
    raise RuntimeError("业务校验失败")''',
                "code_lines": """1. `__enter__` 记录起始时间并返回 self，所以 `as` 后面能拿到这个对象。
2. `__exit__` 一定会在离开 with 时执行，无论代码块里发生什么。
3. `exc_type is not None` 说明块内有异常；这里只打印不吞掉，`return False` 让异常继续抛出。
4. `Transaction.__exit__` 在异常时打印回滚；正常结束且未提交则自动提交。
5. `@contextmanager` 装饰的生成器里，`yield` 之前相当于 `__enter__`，之后相当于 `__exit__`。
6. `try/finally` 保证即使 with 内部抛异常，「退出」也会打印。
7. 前两个 with 正常结束，所以 Timer 打印耗时、open_scope 打印退出。
8. 最后一个 with 抛了 RuntimeError，`__exit__` 打印回滚并返回 False，异常继续传播，程序在这里中断。""",
                "output": """[计算] 开始
[计算] 结束，耗时 3.85 ms
进入 作用域
内部 作用域
退出 作用域
开启事务
写第一条记录
提交事务
开启事务
写第二条记录
回滚事务
Traceback (most recent call last):
  ...
RuntimeError: 业务校验失败""",
                "mistakes": """- `__exit__` 忘记接收三个参数，with 结束时直接 TypeError。
- `__exit__` 返回 True，异常被静默吞掉，问题被掩盖。
- 用 `@contextmanager` 时把 `yield` 写在 try 外面，异常路径不释放资源。
- 以为 `as` 拿到的一定是 `self`，其实拿到的是 `__enter__` 的返回值。
- 在 `__enter__` 里申请资源后没在 `__exit__` 里释放，仍然泄漏。""",
                "error_analysis": """`TypeError: __exit__() takes 1 positional argument but 4 were given`
—— `__exit__` 只写了 self。它必须接收 exc_type、exc、tb 三个参数。

异常没有向外抛出，但也没有被处理
—— `__exit__` 返回了 True（或返回了真值），等于声明「我处理过了」。除非确实做了兜底，否则应返回 False 或 None。

`AttributeError: __enter__`
—— 用在 with 后面的对象没有实现上下文管理器协议，常见于把普通函数结果直接 with。

`RuntimeError: generator didn't yield`
—— `@contextmanager` 装饰的函数里没有 `yield`，进入时就会报错。""",
                "beginner_practice": """1. 写 `TempDir` 上下文管理器（用 `tempfile.mkdtemp` 创建、退出时删除），
   验证块内文件存在、退出后目录消失。
2. 用 `@contextmanager` 重写一遍，比较两种写法的行数。""",
                "advanced_practice": """实现 `@suppress_and_log(*exceptions)` 上下文管理器：
块内出现指定异常时记录日志并继续执行，其他异常照常抛出。
再用它包住一个会抛 ValueError 的调用，验证程序不会中断。""",
                "quiz_note": "本节 6 道题：重点考 `__exit__` 的返回值语义与异常路径的释放。",
                "summary": """with 进入调 `__enter__`、离开调 `__exit__`，异常路径同样会执行；
`__exit__` 返回 True 会吞掉异常，多数场景应返回 False；
轻量场景用 `@contextmanager` + `try/finally` 更省代码。""",
                "next_lesson": "下一节讲类型注解：怎么把「参数该传什么」写进代码，并让 mypy 提前报错。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-06-01",
                        "name": "with 与上下文管理器",
                        "goal": "能实现上下文管理器，能解释异常路径下的资源释放，并知道吞异常的风险。",
                        "minutes": 30,
                        "criteria": "能写出带 __enter__/__exit__ 的类，并说明 return True 的后果。",
                        "requires": ["python-advanced-05-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-06-01-1",
                        "kp": 0,
                        "title": "临时目录管理器",
                        "description": "写 TempDir 上下文管理器：进入时创建临时目录并返回路径，退出时删除整个目录（即使块内抛异常）。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''import shutil
import tempfile


class TempDir:
    def __enter__(self):
        self.path = tempfile.mkdtemp()
        return self.path

    def __exit__(self, exc_type, exc, tb):
        shutil.rmtree(self.path, ignore_errors=True)
        return False


with TempDir() as path:
    print("工作目录", path)''',
                        "explanation": "清理放在 __exit__ 里，异常路径也会执行；ignore_errors 避免清理失败掩盖原始异常。",
                    },
                    {
                        "code": "adv-ex-06-01-2",
                        "kp": 0,
                        "title": "选择性抑制异常",
                        "description": "实现 suppress_and_log：块内出现指定异常时打印并继续，其他异常照常抛出。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''from contextlib import contextmanager


@contextmanager
def suppress_and_log(*exceptions):
    try:
        yield
    except exceptions as exc:
        print(f"已忽略：{type(exc).__name__}: {exc}")


with suppress_and_log(ValueError):
    raise ValueError("这条会被忽略")

print("继续执行")''',
                        "explanation": "只捕获指定类型，其余异常自然向外传播；这种「精确抑制」比 except Exception 安全得多。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-06-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "with 语句块里抛出异常时，`__exit__` 会被调用吗？",
                        "options": [
                            ("A", "不会，异常直接中断程序"),
                            ("B", "会，且异常默认继续向外传播"),
                            ("C", "只有 IOError 时才调用"),
                            ("D", "只有手动调用才执行"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "with 的退出动作一定会执行，异常信息通过三个参数传给 __exit__，默认继续传播。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-06-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 `__exit__` 的返回值，下列说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "返回 True 表示异常已被处理，不再向外抛"),
                            ("B", "返回 False 或 None 时异常继续传播"),
                            ("C", "返回值会被赋给 as 后面的变量"),
                            ("D", "返回值决定是否调用 __enter__"),
                        ],
                        "answer": {"values": ["A", "B"]},
                        "explanation": "as 拿到的是 __enter__ 的返回值，与 __exit__ 无关；返回真值才会抑制异常。",
                        "difficulty": "advanced",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-06-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码输出什么？
class Guard:
    def __enter__(self):
        print("进")
        return "资源"

    def __exit__(self, exc_type, exc, tb):
        print("出")
        return True

with Guard() as value:
    print(value)
    raise ValueError("出错了")
print("继续")''',
                        "answer": {
                            "reference": "依次输出：进、资源、出、继续。异常被 __exit__ 吞掉，程序继续往下走。",
                            "keywords": ["进", "资源", "出", "继续"],
                        },
                        "explanation": "__exit__ 返回 True 抑制了 ValueError，所以最后的 print 仍会执行。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-06-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "用 `@contextmanager` 写上下文管理器时，`yield` 之后的代码等价于 `__exit__`。",
                        "answer": {"value": True},
                        "explanation": "yield 之前是 __enter__，yield 之后（通常在 finally 里）是 __exit__。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-06-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "用 @contextmanager 写一个 timer(name)，进入时记录时间，退出时打印耗时（毫秒）。",
                        "answer": {
                            "reference": '''import time
from contextlib import contextmanager


@contextmanager
def timer(name):
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f"{name} 耗时 {(time.perf_counter() - start) * 1000:.2f} ms")''',
                            "keywords": ["@contextmanager", "yield", "finally", "perf_counter"],
                        },
                        "explanation": "用 finally 保证异常时也打印耗时；yield 不需要产出值，所以 as 可省略。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-06-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「在 __exit__ 里统一 return True」是危险习惯？举一个具体后果。",
                        "answer": {
                            "reference": "返回 True 等于告诉 Python「异常已处理」，所有异常都会静默消失。比如数据库写入时抛了唯一键冲突，被吞掉后接口仍然返回成功，调用方以为数据已保存，实际丢了写入，而且日志里也看不到异常。正确做法是只抑制明确可忽略的异常类型，其余照常抛出。",
                            "keywords": ["静默", "以为成功", "丢数据", "只抑制特定类型"],
                        },
                        "explanation": "关键是说清「不报错但数据不对」这类比崩溃更难排查的后果。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    {
        "code": "python-advanced-07",
        "title": "类型注解",
        "description": "把接口约定写进代码，让工具在运行前发现问题。",
        "order_index": 7,
        "lessons": [
            {
                "code": "python-advanced-07-lesson-01",
                "objectives": """1. 会给变量、参数、返回值加类型注解；
2. 会用内置泛型 `list[int]`、`dict[str, int]` 与 `X | None`；
3. 会用 Optional、Callable、TypeVar 表达更复杂的结构；
4. 会跑 mypy 并读懂它的报错。""",
                "why_learn": """参数写着 `data`，调用方不知道要传字典还是列表，只能去读实现；
返回值可能是 None 却没标注，线上就冒 `AttributeError`。
类型注解不改变运行时行为，但能让编辑器和 mypy 在你运行前就指出问题。""",
                "concepts": """**类型注解** 是写在变量、参数、返回值后面的类型标记，运行时不做检查，供工具分析。
Python 3.9+ 直接用内置类型做泛型：`list[int]`、`dict[str, int]`、`tuple[int, str]`。
`X | None` 表示「X 或者 None」，是 `Optional[X]` 的新写法（3.10+）。
`Callable[[int], str]` 表示「接收 int、返回 str 的函数」。
`TypeVar` 用于表达「输入什么类型就返回什么类型」的泛型关系。
**mypy** 是静态检查工具，按注解推断并报告不一致。""",
                "plain": """类型注解像快递单上的「易碎品」标签：包裹本身没变，但搬运的人知道该怎么处理。
它不会让程序跑得更快，也不会在运行时拦住错误，它的价值在于「提前告诉你这箱子装错了」。
标签写得越准，静态检查能发现的问题越多。""",
                "syntax": """```python
def 函数(参数: 类型, 可选: int = 0) -> 返回类型:
    ...


变量: 类型 = 值
items: list[dict[str, int]] = []


def find(name: str) -> str | None:
    ...


from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


def first(items: Sequence[T]) -> T | None:
    return items[0] if items else None
```""",
                "example_code": '''from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


def total_minutes(tasks: Iterable[dict[str, object]]) -> int:
    """统计总时长；tasks 里每条至少含 minutes 键。"""
    return sum(int(task["minutes"]) for task in tasks)


def find_task(
    tasks: list[dict[str, object]], title: str
) -> dict[str, object] | None:
    for task in tasks:
        if task["title"] == title:
            return task
    return None


def apply_all(
    values: list[int], func: Callable[[int], int]
) -> list[int]:
    return [func(value) for value in values]


def first(items: list[T]) -> T | None:
    return items[0] if items else None


tasks = [
    {"title": "写周报", "minutes": 30},
    {"title": "交报表", "minutes": 45},
]

print(total_minutes(tasks))
found = find_task(tasks, "写周报")
print(found["minutes"] if found else "未找到")
print(apply_all([1, 2, 3], lambda value: value * 2))
print(first([10, 20]), first([]))''',
                "code_lines": """1. `Iterable[dict[str, object]]` 说明参数只要「可遍历、元素是字典」即可，列表、生成器都能传。
2. `-> int` 声明返回整数，调用方可以放心参与算术，不必再判断类型。
3. `dict[str, object] | None` 明确告诉调用方：可能找不到，必须处理 None。
4. `Callable[[int], int]` 精确描述「一个 int 进、一个 int 出」的函数，比 `Callable` 更严格。
5. `T = TypeVar("T")` 加 `list[T] -> T | None`，表达「传什么类型就返回什么类型」。
6. `print(found["minutes"] if found else "未找到")` 是与注解配套的写法：先判空再取键。
7. `lambda value: value * 2` 满足 Callable[[int], int]，可以直接传入。
8. 最后一行验证 first 对空列表返回 None，与注解一致。""",
                "output": """75
30
[2, 4, 6]
10 None""",
                "mistakes": """- 把注解当运行期校验，以为写了 `int` 就传不进字符串。
- 用可变默认值 `def f(items: list[int] = [])`，所有调用共享同一个列表。
- 只给参数注解、不写返回值，静态检查抓不到「该返回 None 却返回了字符串」。
- `list[int]` 写成 `list[int` 少个括号，或在低版本 Python 用内置泛型。
- 到处写 `Any`，等于放弃检查。""",
                "error_analysis": """mypy 报 `Argument 1 to "total_minutes" has incompatible type "dict[str, str]"; expected "Iterable[dict[str, object]]"`
—— 传入的数据结构类型不符，说明调用点与签名对不上。

mypy 报 `Item "None" of "dict[str, object] | None" has no attribute "__getitem__"`
—— 忘了处理 None 分支。注解已经提示可能为空，取键前必须先判断。

mypy 报 `Missing return statement`
—— 声明了返回 int，但存在没有 return 的分支。运行时会静默返回 None，静态检查能提前发现。

代码能跑但编辑器一片红
—— 注解写错或过时。注解不影响运行，所以错误只在工具层面暴露。""",
                "beginner_practice": """1. 给 `total_minutes` 增加参数 `only_pending: bool = False`，并补全注解。
2. 写 `format_minutes(minutes: int) -> str`，返回「1 小时 15 分」这样的文本，并加注解。""",
                "advanced_practice": """用 TypeVar 写一个 `group_by(items: list[T], key: Callable[[T], str]) -> dict[str, list[T]]`，
再用 mypy 验证：传入 `list[dict]` 时返回值类型是 `dict[str, list[dict]]`。""",
                "quiz_note": "本节 6 道题：重点考「注解不参与运行时」与 `X | None` 的处理。",
                "summary": """注解写给工具看，不改变运行时；用内置泛型与 `X | None` 表达结构；
mypy 能发现「返回类型不一致」「漏处理 None」这类隐患。
记住：**注解是契约，不是校验**。""",
                "next_lesson": "下一节讲虚拟环境与依赖管理：怎么让别人的机器也能装出和你一样的运行环境。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-07-01",
                        "name": "类型注解与静态检查",
                        "goal": "能给参数与返回值加准确注解，用内置泛型表达容器，并用 mypy 检查。",
                        "minutes": 35,
                        "criteria": "能为一组函数补全注解并让 mypy 通过，且能解释 Optional 的含义。",
                        "requires": ["python-advanced-06-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-07-01-1",
                        "kp": 0,
                        "title": "补全注解",
                        "description": "给 total_minutes 与 format_minutes 补全注解，再用 mypy 检查；然后故意传错类型，确认 mypy 会报错。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def total_minutes(
    tasks: Iterable[dict[str, object]], only_pending: bool = False
) -> int:
    return sum(
        int(task["minutes"])
        for task in tasks
        if not only_pending or not task.get("done")
    )


def format_minutes(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    return f"{hours} 小时 {rest} 分" if hours else f"{rest} 分"''',
                        "explanation": "divmod 一次拿到商与余数；注解写清参数与返回，mypy 才能检查调用点。",
                    },
                    {
                        "code": "adv-ex-07-01-2",
                        "kp": 0,
                        "title": "泛型分组",
                        "description": "用 TypeVar 实现 group_by(items, key)，按 key 的返回值分组，保持元素顺序。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def group_by(items: list[T], key: Callable[[T], str]) -> dict[str, list[T]]:
    grouped: dict[str, list[T]] = {}
    for item in items:
        grouped.setdefault(key(item), []).append(item)
    return grouped''',
                        "explanation": "setdefault 避免手写「键不存在就先建空列表」的分支，同时保持插入顺序。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-07-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "函数的类型注解在运行时会做什么？",
                        "options": [
                            ("A", "自动把参数转换成注解声明的类型"),
                            ("B", "什么也不做，只供编辑器和静态检查工具使用"),
                            ("C", "传错类型时抛出 TypeError"),
                            ("D", "提升函数执行速度"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "注解默认不参与运行；传错类型照样能跑，这正是需要 mypy 的原因。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-07-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些写法能正确表达「可能返回 None」？（多选）",
                        "options": [
                            ("A", "-> str | None"),
                            ("B", "-> Optional[str]"),
                            ("C", "-> str or None"),
                            ("D", "-> Union[str, None]"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "`str or None` 是布尔表达式，不是类型写法；其余三种都合法，A 是最新推荐写法。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-07-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码能正常运行吗？mypy 会怎么判断？
def half(value: int) -> int:
    if value % 2 == 0:
        return value // 2

print(half(4))''',
                        "answer": {
                            "reference": "能运行，half(4) 返回 2；但 mypy 会报 Missing return statement，因为奇数分支没有返回值。",
                            "keywords": ["Missing return statement", "返回 None", "分支"],
                        },
                        "explanation": "运行时只有走到奇数分支才返回 None，属于隐藏 bug；静态检查能提前指出。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-07-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`list[int]` 与 `List[int]` 在 Python 3.9+ 都合法，前者是推荐的写法。",
                        "answer": {"value": True},
                        "explanation": "3.9 起内置类型支持泛型下标，`list[int]` 可直接用，不再需要从 typing 导入 List。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-07-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给函数 find_task(tasks, title) 补全注解，返回可能为 None 的字典。",
                        "answer": {
                            "reference": '''def find_task(
    tasks: list[dict[str, object]], title: str
) -> dict[str, object] | None:
    for task in tasks:
        if task["title"] == title:
            return task
    return None''',
                            "keywords": ["list[dict[str, object]]", "| None", "return None"],
                        },
                        "explanation": "返回类型要如实写出 None 的可能，调用方才会写判空分支。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-07-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么给老项目「一次性补全所有注解」通常不是好策略？给出你的渐进方案。",
                        "answer": {
                            "reference": "一次性补全会产生巨大改动量，评审困难、冲突频繁，而且很多注解只能靠猜，容易写成错误契约。更好的做法是先给公共接口（被多处调用的函数、服务层入口）补注解，在 CI 里只对改动文件跑 mypy，随着改动逐步扩大范围，注解质量也能随手修正。",
                            "keywords": ["改动量", "公共接口", "增量", "CI"],
                        },
                        "explanation": "核心是「按接口价值排序、增量推进」，而不是追求覆盖率数字。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    {
        "code": "python-advanced-08",
        "title": "虚拟环境与依赖管理",
        "description": "让每个项目有独立的解释器环境与可复现的依赖清单。",
        "order_index": 8,
        "lessons": [
            {
                "code": "python-advanced-08-lesson-01",
                "objectives": """1. 会用 venv 创建并激活虚拟环境；
2. 会用 pip 安装、卸载、导出依赖；
3. 能说清 requirements.txt 与 pyproject.toml 的分工；
4. 知道为什么要锁定版本，以及怎么避免「我这能跑」。""",
                "why_learn": """项目 A 要 requests 2.28，项目 B 要 2.31，装在同一个全局环境里必然打架。
更常见的是：你机器上能跑，同事装完就报错——因为没记录依赖版本。
虚拟环境 + 依赖清单是工程化的第一道门槛。""",
                "concepts": """**虚拟环境** 是一个独立的目录，包含专属的解释器副本与 `site-packages`，与全局环境隔离。
`python -m venv .venv` 创建，激活后 `pip install` 只影响这个环境。
**requirements.txt** 是扁平的依赖清单，适合部署时 `pip install -r`。
**pyproject.toml** 是现代项目元数据文件，声明项目信息、依赖与工具配置。
**版本锁定** 指把依赖固定到具体版本（`==`），保证不同机器装出同样的结果。
**直接依赖 vs 间接依赖**：前者是你写的，后者是依赖的依赖。""",
                "plain": """虚拟环境像给每个项目单独的厨房：锅碗瓢盆各一套，做川菜不会影响隔壁做甜点。
依赖清单像采购单：写清「盐 500 克」而不是「一些盐」，
否则换个人去采购，买回来的量完全不一样。""",
                "syntax": """```bash
python -m venv .venv              # 创建
source .venv/bin/activate         # macOS / Linux 激活
.venv\\Scripts\\activate            # Windows 激活
python -m pip install requests==2.31.0
python -m pip freeze > requirements.txt
python -m pip install -r requirements.txt
deactivate                        # 退出
```
```toml
# pyproject.toml
[project]
name = "xiaoma-demo"
requires-python = ">=3.11"
dependencies = ["requests==2.31.0"]
```""",
                "example_code": '''# 演示依赖版本核对：真实项目里 installed 由 importlib.metadata.version 读取，
# 这里显式传入，保证示例输出在任何机器上都一致。
INSTALLED = {"requests": "2.32.3", "uvicorn": "0.30.1"}
REQUIRED = {"requests": "2.31.0", "uvicorn": "0.30.1", "typer": "0.12.0"}


def check_dependencies(required, installed):
    report = []
    for name, expected in required.items():
        actual = installed.get(name)
        if actual is None:
            report.append(f"{name}: 未安装（需要 {expected}）")
        elif actual == expected:
            report.append(f"{name}: 一致（{expected}）")
        else:
            report.append(f"{name}: 不一致（需要 {expected}，实际 {actual}）")
    return report


for line in check_dependencies(REQUIRED, INSTALLED):
    print(line)

pinned = [f"{name}=={ver}" for name, ver in REQUIRED.items()]
print("\\n".join(pinned))
print("缺失项", [name for name in REQUIRED if name not in INSTALLED])''',
                "code_lines": """1. `importlib.metadata.version` 读取已安装包的版本，不需要真的 pip 命令。
2. `PackageNotFoundError` 是「没装」的专用异常，比捕获 Exception 精确。
3. `REQUIRED` 里写 `==` 固定版本，这是可复现的最小要求。
4. `check_dependencies` 返回人类可读的检查结果，方便在启动脚本里打印。
5. 第二个 `print` 演示未安装时的输出，验证异常分支被正确处理。
6. 最后用列表推导式生成 requirements 风格的行，`==` 才是锁定语义。
7. 输出里的「不一致」提示不是自动修复，只是把问题暴露出来。""",
                "output": """requests: 不一致（需要 2.31.0，实际 2.32.3）
uvicorn: 一致（0.30.1）
typer: 未安装（需要 0.12.0）
requests==2.31.0
uvicorn==0.30.1
typer==0.12.0
缺失项 ['typer']""",
                "mistakes": """- 不建虚拟环境，直接往全局环境装包，最后谁也不敢升级。
- 用 `pip freeze` 把几百个间接依赖全写进 requirements，却不区分直接依赖。
- 只用版本区间 `>=` 不锁版本，两次部署装出不同结果。
- 提交了 `.venv/` 目录到 Git，仓库体积暴涨。
- 在错误的解释器上跑 `pip`（PATH 指向全局），装了却导入不到。""",
                "error_analysis": """`ModuleNotFoundError: No module named 'requests'`
—— 装到了另一个解释器里。用 `python -m pip install` 而不是裸 `pip`，能保证装进当前解释器。

`ERROR: Could not find a version that satisfies the requirement requests==2.31.0`
—— 版本号写错或与 Python 版本不兼容。先 `pip index versions requests` 看可用版本。

`pip freeze` 结果里出现 `-e git+...`
—— 安装了可编辑安装的包，直接分享清单会让别人装不上，需要在清单里说明来源。

虚拟环境激活后 `python` 版本没变
—— 激活脚本没生效（Windows 执行策略或 shell 不同），用 `.venv/Scripts/python` 绝对路径验证。""",
                "beginner_practice": """1. 在临时目录创建 `.venv`，激活后安装任意一个小包，用 `pip freeze` 导出清单。
2. 删除环境后按清单重装，验证版本一致。""",
                "advanced_practice": """为一个已有项目设计依赖策略：
直接依赖写进 `pyproject.toml` 并给出版本区间，用 `pip freeze` 产出锁定文件用于部署；
说明为什么两套文件要同时存在，以及升级依赖时的操作顺序。""",
                "quiz_note": "本节 6 道题：重点考虚拟环境隔离、锁定版本与 `python -m pip` 的必要性。",
                "summary": """每个项目一个 venv，装包用 `python -m pip`；
`pyproject.toml` 声明直接依赖与项目元数据，锁定文件保证可复现；
版本要 `==` 锁定，否则「我这能跑」会变成常态。""",
                "next_lesson": "下一节讲项目目录结构：代码怎么分层、包怎么组织、入口放哪里。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-08-01",
                        "name": "venv 与 pip 依赖管理",
                        "goal": "能创建隔离环境、用 pip 管理依赖、用锁定文件保证可复现。",
                        "minutes": 30,
                        "criteria": "能独立搭好环境并按清单复现，能说明锁定版本的必要性。",
                        "requires": ["python-advanced-07-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-08-01-1",
                        "kp": 0,
                        "title": "环境检查脚本",
                        "description": "写脚本检查 requirements 里每个包是否已安装、版本是否一致，输出表格化结果。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''from importlib.metadata import PackageNotFoundError, version


def check(required: dict[str, str]) -> list[tuple[str, str, str]]:
    rows = []
    for name, expected in required.items():
        try:
            actual = version(name)
        except PackageNotFoundError:
            rows.append((name, expected, "未安装"))
        else:
            rows.append((name, expected, actual))
    return rows


for name, expected, actual in check({"requests": "2.31.0"}):
    print(f"{name:<12}{expected:<10}{actual}")''',
                        "explanation": "结果做成结构化元组，便于后续改成表格或写进日志；未安装与版本不符分开表达。",
                    },
                    {
                        "code": "adv-ex-08-01-2",
                        "kp": 0,
                        "title": "依赖策略设计",
                        "description": "为一个 Web 项目设计直接依赖与锁定文件的分工，写出 pyproject.toml 片段与升级流程。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''[project]
name = "xiaoma-api"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115,<0.116",
    "sqlalchemy>=2.0,<2.1",
]

# 部署用：pip freeze > requirements.lock
# 升级流程：改 pyproject 区间 -> 在新 venv 里安装 -> 跑测试 -> 重新生成 lock -> 提交两个文件''',
                        "explanation": "声明文件表达「允许的范围」，锁定文件记录「本次验证过的具体版本」，两者配合兼顾可维护与可复现。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-08-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "虚拟环境最主要解决什么问题？",
                        "options": [
                            ("A", "让代码运行更快"),
                            ("B", "隔离不同项目的依赖与解释器，避免版本冲突"),
                            ("C", "自动给代码加密"),
                            ("D", "让 Python 支持多线程"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "虚拟环境提供独立的 site-packages，不同项目可以各自固定依赖版本。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-08-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "为了让他人能复现你的环境，下列哪些做法是必要的？（多选）",
                        "options": [
                            ("A", "提供锁定版本的依赖清单"),
                            ("B", "在清单里说明 Python 版本要求"),
                            ("C", "把整个 .venv 目录打包发给对方"),
                            ("D", "锁定文件随代码一起提交"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "venv 里含绝对路径与平台相关二进制，不能跨机器复用；清单加版本约束才是正确做法。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-08-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面的 requirements 写法有什么风险？
requests>=2.0
flask''',
                        "answer": {
                            "reference": "没有锁定具体版本，两次安装可能拿到不同版本；flask 连区间都没有，行为完全不可控，可能某天自动升到不兼容的大版本。",
                            "keywords": ["未锁定", "不同版本", "不可复现"],
                        },
                        "explanation": "`>=` 只保证下限，不保证上限；完全没有版本号的依赖等于把可复现性交给运气。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-08-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "激活虚拟环境后，直接执行 `pip install` 与 `python -m pip install` 效果完全一样。",
                        "answer": {"value": False},
                        "explanation": "裸 pip 可能指向另一个解释器的 pip；`python -m pip` 明确使用当前 python 对应的 pip，更可靠。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-08-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写出创建虚拟环境、安装 requests 2.31.0、导出锁定清单的三条命令（Windows 环境）。",
                        "answer": {
                            "reference": '''python -m venv .venv
.venv\\Scripts\\activate
python -m pip install requests==2.31.0
python -m pip freeze > requirements.txt''',
                            "keywords": ["venv", "activate", "install", "freeze"],
                        },
                        "explanation": "创建、激活、安装、导出四步；install 时用 == 锁定版本。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-08-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「直接依赖」与「间接依赖」应该分开管理？",
                        "answer": {
                            "reference": "直接依赖是你主动选择的、需要维护和升级的；间接依赖数量多、随上游变化，通常只在锁定文件里固定。分开后，评审时能看清项目真正依赖了什么，升级时也知道该改哪一层，而不会把几十个传递依赖当成自己的技术选型。",
                            "keywords": ["主动选择", "传递依赖", "评审", "升级"],
                        },
                        "explanation": "能用「维护责任」与「可读性」解释分层价值即可。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
]
