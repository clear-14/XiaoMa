"""Python 进阶与工程实践：第 1—2 章（面向对象、继承与多态）。"""

CHAPTERS: list[dict] = [
    {
        "code": "python-advanced-01",
        "title": "面向对象：类与对象",
        "description": "从「一堆函数」升级到「一组对象」：用类把数据和行为封装在一起。",
        "order_index": 1,
        "lessons": [
            {
                "code": "python-advanced-01-lesson-01",
                "objectives": """1. 会用 class 定义自己的类型；
2. 会用 __init__ 在创建对象时准备好初始数据；
3. 会在方法里读写当前对象的属性；
4. 能说清楚「类」和「对象」不是一回事。""",
                "why_learn": """用函数写任务清单时，`title`、`done` 这些数据和「标记完成」这个操作是分开的：
函数越来越多，参数就得一路往下传。类把「数据」和「操作这些数据的函数」放在一起，
调用方只需要一个对象，不用再记住该传哪几个参数。这就是后面写 ORM 模型、写服务类的基础。""",
                "concepts": """**类（class）** 是模板：它规定这一类对象有哪些属性、能执行哪些方法。
**对象（实例）** 是按模板创建出来的具体个体，各自持有自己的数据。
`__init__` 是初始化方法，创建对象时自动调用，用来给属性赋初值。
**属性** 是对象身上的数据，写法是 `self.名称`。
**方法** 是定义在类内部的函数，第一个参数固定写 `self`，指向当前这个对象。""",
                "plain": """类就像一张空白表格模板：表头写好了要填哪几栏，模板本身只有一份。
对象就是照着模板填好的一张张表，每张表里的姓名、日期都不一样。
你改其中一张表，模板不会变，别的表也不会跟着变。
所以「模板」负责规定格式，「对象」负责装具体内容。""",
                "syntax": """```python
class 类名:                    # 类名习惯用大驼峰
    def __init__(self, 参数):   # 创建对象时自动执行
        self.属性 = 参数         # 把数据挂到对象身上

    def 方法名(self):            # 方法第一个参数必须是 self
        return self.属性

对象 = 类名(参数)               # 实例化
对象.方法名()                   # 调用方法
对象.属性                       # 读取属性
```
注意：`class` 后面没有括号也不需要 `return`；方法里的 `self` 由 Python 自动传入，调用时不用写。""",
                "example_code": '''class Task:
    """一条待办事项。"""

    def __init__(self, title):
        self.title = title
        self.done = False

    def finish(self):
        self.done = True

    def describe(self):
        status = "已完成" if self.done else "未完成"
        return f"{self.title}（{status}）"


task = Task("写周报")
print(task.describe())
task.finish()
print(task.describe())
print(task.title)
print(type(task).__name__)

other = Task("订会议室")
print(other.describe())''',
                "code_lines": """1. `class Task:` 定义了一个名为 Task 的类，缩进的内容都属于它。
2. `def __init__(self, title):` 定义初始化方法，`self` 是即将创建出来的那个对象。
3. `self.title = title` 把外部传进来的标题存到对象身上，成为**实例属性**。
4. `self.done = False` 每个新任务默认未完成，这也是实例属性。
5. `def finish(self):` 与 `def describe(self):` 是方法，它们通过 `self.` 读写自己的属性。
6. `task = Task("写周报")` 实例化：先执行 `__init__`，再把对象赋给变量 `task`。
7. `task.finish()` 调用方法时不用传 `self`，Python 会把 `task` 自动传进去。
8. `print(type(task).__name__)` 输出对象的类名，用来验证它确实是 Task 的实例。
9. 最后两行新建了另一个对象 `other`，它的 `done` 是独立的 False，与 `task` 互不影响。""",
                "output": """写周报（未完成）
写周报（已完成）
写周报
Task
订会议室（未完成）""",
                "mistakes": """- 方法签名里忘了写 `self`，调用时报参数数量不符。
- 创建对象时漏传参数，触发 `missing required positional argument`。
- 在 `__init__` 里写 `return 值`，Python 会直接报错。
- 属性名拼错（`self.titel`），读的时候才报 AttributeError。
- 用 `Task.describe` 直接调用，缺少对象参数。""",
                "error_analysis": """`TypeError: Task.__init__() missing 1 required positional argument: 'title'`
—— 调用 `Task()` 时没给 title。构造参数由 `__init__` 的签名决定，少一个都不行。

`AttributeError: 'Task' object has no attribute 'titel'`
—— 属性名拼错了。Python 不会自动纠正拼写，赋值和读取必须完全一致。

`TypeError: finish() takes 0 positional arguments but 1 was given`
—— 方法定义时漏了 `self`。实例调用会把对象当第一个参数传进去，签名里没有对应位置就报错。

`TypeError: __init__() should return None, not 'str'`
—— `__init__` 只负责初始化，不允许返回值。""",
                "beginner_practice": """1. 定义 `Book` 类，`__init__` 接收 `title` 与 `pages`，再加一个 `summary()` 方法，
   返回「书名，共 N 页」。
2. 创建两本书，分别打印 `summary()`，确认它们的数据互不影响。""",
                "advanced_practice": """给 `Task` 增加 `priority` 属性（默认 3），再写一个 `raise_priority()` 方法把它减 1
（数字越小越紧急），但最低不能低于 1。最后创建两个任务，各调用几次，验证不会降到 0。""",
                "quiz_note": "本节 6 道题：2 道基础理解、2 道代码阅读、2 道应用练习，做完再看解析。",
                "summary": """类是模板，对象是实例；`__init__` 负责初始化，`self` 指向当前对象；
方法通过 `self.属性` 读写数据，调用时不需要手动传 `self`。
记住一句话：**类是设计图，对象是按图造出来的房子**。""",
                "next_lesson": "下一节讲 `self` 到底指向谁、实例属性和类属性有什么区别，以及怎么用 property 控制属性读写。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-01-01",
                        "name": "类、对象与 __init__",
                        "goal": "能用 class 定义类型，用 __init__ 初始化实例属性，并通过方法访问它们。",
                        "minutes": 30,
                        "criteria": "能独立写出一个带 __init__ 和两个方法的类，并创建两个互不影响的实例。",
                        "requires": [],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-01-01-1",
                        "kp": 0,
                        "title": "写一个 Book 类",
                        "description": "定义 Book 类：属性 title 与 pages；方法 summary() 返回「书名，共 N 页」。创建两本书并打印结果。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''class Book:
    def __init__(self, title, pages):
        self.title = title
        self.pages = pages

    def summary(self):
        return f"{self.title}，共 {self.pages} 页"


print(Book("Python 进阶", 320).summary())
print(Book("数据库入门", 260).summary())''',
                        "explanation": "关键是把 title 与 pages 存成实例属性，方法里用 self 读取，这样每本书的数据各自独立。",
                    },
                    {
                        "code": "adv-ex-01-01-2",
                        "kp": 0,
                        "title": "带下限的优先级",
                        "description": "给 Task 增加 priority（默认 3）与 raise_priority()：每次减 1，但不低于 1。验证连续调用不会降到 0。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class Task:
    def __init__(self, title, priority=3):
        self.title = title
        self.done = False
        self.priority = priority

    def raise_priority(self):
        if self.priority > 1:
            self.priority -= 1


task = Task("修线上缺陷")
for _ in range(5):
    task.raise_priority()
print(task.priority)  # 1''',
                        "explanation": "边界条件写在方法内部，而不是让调用方自己判断，才能保证任何调用路径都不会越界。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-01-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "关于类和对象的关系，下列说法正确的是？",
                        "options": [
                            ("A", "类是对象创建出来的，对象是模板"),
                            ("B", "类是模板，对象是按模板创建的实例"),
                            ("C", "一个类在程序里只能有一个对象"),
                            ("D", "类和对象是同义词，可以互换使用"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "类描述结构与行为，是模板；对象是按模板创建的具体实例，可以有任意多个，各自持有数据。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-01-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 __init__，下列说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "创建对象时会被自动调用"),
                            ("B", "第一个参数通常写 self"),
                            ("C", "必须返回一个字典"),
                            ("D", "可以在里面给实例属性赋初值"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "实例化时 Python 自动调用 __init__，self 指向新对象，用它挂属性；但 __init__ 不允许返回值，所以 C 错。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-01-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码运行后会输出什么？
class Counter:
    def __init__(self):
        self.n = 0

    def add(self):
        self.n += 1

a = Counter()
b = Counter()
a.add()
a.add()
b.add()
print(a.n, b.n)''',
                        "answer": {
                            "reference": "输出 2 1。每个对象有自己的 n，a 加了两次是 2，b 只加一次是 1。",
                            "keywords": ["2 1", "各自", "实例属性"],
                        },
                        "explanation": "n 在 __init__ 里用 self 赋值，属于实例属性；每次实例化都会重新执行 __init__，两个对象互不共享。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-01-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "执行 `t = Task(\"a\"); t.finish(); t.describe()` 后，describe 返回的字符串里包含「已完成」。",
                        "answer": {"value": True},
                        "explanation": "finish() 把 self.done 改成 True，describe() 依据 done 拼状态文案，因此返回「a（已完成）」。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-01-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "定义一个 Rectangle 类：属性 width 与 height，方法 area() 返回面积。创建 3×4 的矩形并打印面积。",
                        "answer": {
                            "reference": '''class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height


print(Rectangle(3, 4).area())''',
                            "keywords": ["class", "__init__", "self", "return"],
                        },
                        "explanation": "面积必须用 self.width 与 self.height 计算，不能写死数字，否则换个矩形就不对了。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-01-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如果把 Task 的所有数据都放进字典、所有操作都写成独立函数，和写成类相比，调用方会多出哪些负担？",
                        "answer": {
                            "reference": "数据与操作分离时，调用方要自己保存字典并把它一路传给每个函数，参数顺序和键名都要记牢；一旦结构变化，所有调用点都要跟着改。写成类后数据挂在对象上，函数通过 self 直接访问，调用方只需要一个对象。",
                            "keywords": ["传参", "键名", "self", "维护"],
                        },
                        "explanation": "回答能指出「数据与行为绑定后，接口更小、改动更集中」即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-advanced-01-lesson-02",
                "objectives": """1. 说清 self 在调用时是怎么传进去的；
2. 区分实例属性和类属性，知道各自适合放什么数据；
3. 用下划线约定与 @property 控制属性的读写；
4. 能识别「所有对象共享同一个列表」这类典型错误。""",
                "why_learn": """面试和真实代码里，最常见的对象问题都出在两处：把该放实例的数据放成了类属性，
以及对外暴露裸属性导致任何地方都能改成非法值。这一节解决这两件事。""",
                "concepts": """**self** 不是关键字，只是习惯名，它指向「调用这个方法的对象」。
**实例属性** 写在 `__init__` 里、用 `self.x = ...` 赋值，每个对象一份。
**类属性** 直接写在类体里，所有实例共享一份，适合放常量或默认值。
**封装** 指不直接暴露内部数据，用方法或 `@property` 控制访问。
Python 没有真正的私有成员，用单下划线 `_name` 表示「内部使用」，双下划线会触发名称改写。""",
                "plain": """实例属性像每个人自己的水杯，你喝你的；类属性像办公室墙上的挂钟，大家看的是同一个。
如果误把「水杯」写成类属性，就会出现「我喝水你也变少」的怪事。
封装则像银行柜台：你不能自己伸手进金库改数字，只能通过「存款」「取款」两个窗口，
窗口会先检查金额是否合法。""",
                "syntax": """```python
class Account:
    bank = "小码银行"          # 类属性：所有账户共享

    def __init__(self, owner, balance=0):
        self.owner = owner     # 实例属性
        self._balance = balance  # 单下划线：约定为内部使用

    @property
    def balance(self):          # 读：account.balance
        return self._balance

    @balance.setter
    def balance(self, value):   # 写：account.balance = 100
        if value < 0:
            raise ValueError("余额不能为负")
        self._balance = value
```""",
                "example_code": '''class Account:
    bank = "小码银行"

    def __init__(self, owner, balance=0):
        self.owner = owner
        self._balance = balance

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        if value < 0:
            raise ValueError("余额不能为负")
        self._balance = value

    def deposit(self, amount):
        self.balance = self._balance + amount


a = Account("小明", 100)
b = Account("小红", 50)
a.deposit(20)
print(a.balance, b.balance)
print(Account.bank, a.bank)
print(Account.__dict__["bank"])

try:
    a.balance = -5
except ValueError as exc:
    print("被拦住了：", exc)''',
                "code_lines": """1. `bank = "小码银行"` 写在类体里，是类属性，所有账户共用同一份。
2. `self._balance = balance` 把余额存成实例属性，下划线表示「外部别直接改」。
3. `@property def balance` 把方法伪装成属性，读取 `a.balance` 时自动调用它。
4. `@balance.setter` 定义写入逻辑，赋值 `a.balance = ...` 时先做校验。
5. `a.deposit(20)` 内部走 setter，所以同样受校验保护。
6. `print(a.balance, b.balance)` 两个对象各自 120 与 50，说明实例属性互不影响。
7. `print(Account.bank, a.bank)` 类属性能被类和实例同时读到。
8. 最后一段故意写非法值，验证校验真的会拦住并抛出 ValueError。""",
                "output": """120 50
小码银行 小码银行
小码银行
被拦住了： 余额不能为负""",
                "mistakes": """- 在类体里写 `items = []` 当实例数据，导致所有对象共享同一个列表。
- 直接改 `self._balance` 绕过校验，等于没有封装。
- 把 `@property` 方法写成需要额外参数。
- 用双下划线命名后又从外部按原名访问，触发 AttributeError。
- 误以为 `self` 是 Python 关键字，改成 `this` 也能跑，但团队会看不懂。""",
                "error_analysis": """`AttributeError: 'Account' object has no attribute '__balance'`
—— 双下划线属性被名称改写为 `_Account__balance`，外部不能按原名访问。这是刻意的保护，不是 bug。

`AttributeError: property 'balance' of 'Account' object has no setter`
—— 只写了 `@property` 没写 `@balance.setter`，于是属性只读。要允许修改就得补 setter。

`TypeError: 'int' object is not callable`
—— 把 property 当方法加括号调用了。property 是属性，直接 `a.balance` 取值。""",
                "beginner_practice": """1. 给 `Account` 加一个类属性 `interest_rate = 0.02`，并写 `yearly_interest()` 返回
   `self.balance * Account.interest_rate`。
2. 修改 `Account.interest_rate`，确认所有实例读到的都是新值。""",
                "advanced_practice": """让 `Account` 支持「转账」：`transfer(self, other, amount)`。
要求：金额必须为正、余额不足要拒绝、失败时两个账户都不能被改动。
写完后用三个场景验证：正常转账、余额不足、转负数。""",
                "quiz_note": "本节 6 道题：重点考实例属性与类属性的区别，以及 property 的读写分离。",
                "summary": """`self` 指向当前对象；实例属性一人一份，类属性大家共享；
用单下划线表达「内部使用」，用 `@property` 把校验塞进赋值动作里。
判断该放哪：**每个对象取值可能不同 → 实例属性；全类共用一份 → 类属性**。""",
                "next_lesson": "下一节进入继承：怎么复用父类代码、`super()` 做了什么、重写方法时要注意什么。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-01-02",
                        "name": "self 与实例属性、类属性",
                        "goal": "能正确区分实例属性与类属性，并解释 self 的传递过程。",
                        "minutes": 15,
                        "criteria": "能指出一段代码里哪些属性是共享的、哪些是各自的，并说明后果。",
                        "requires": ["python-advanced-01-01"],
                    },
                    {
                        "code": "python-advanced-01-03",
                        "name": "封装与 property",
                        "goal": "能用命名约定与 @property 控制属性读写，拒绝非法值。",
                        "minutes": 20,
                        "criteria": "能给属性加上校验，并说明为什么直接暴露属性是危险的。",
                        "requires": ["python-advanced-01-01"],
                    },
                ],
                "practice": [
                    {
                        "code": "adv-ex-01-02-1",
                        "kp": 0,
                        "title": "共享列表的坑",
                        "description": "下面代码第二个对象也会带上「牛奶」，请解释原因并改成正确的写法。class Cart: items = [] ...",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''class Cart:
    def __init__(self):
        self.items = []          # 每次实例化都新建一个列表


a = Cart()
b = Cart()
a.items.append("牛奶")
print(b.items)  # []''',
                        "explanation": "items 写在类体里属于类属性，所有实例共享同一个列表；移到 __init__ 里用 self 赋值，才会每个对象一份。",
                    },
                    {
                        "code": "adv-ex-01-02-2",
                        "kp": 1,
                        "title": "带校验的年龄属性",
                        "description": "写一个 Person 类，age 用 property 暴露：必须是 0—150 的整数，否则抛 ValueError；同时提供只读的 is_adult。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        if not isinstance(value, int) or not 0 <= value <= 150:
            raise ValueError("年龄必须是 0—150 的整数")
        self._age = value

    @property
    def is_adult(self):
        return self._age >= 18


p = Person("小明", 20)
print(p.is_adult)''',
                        "explanation": "校验放在 setter 里，所有赋值路径都会经过它；is_adult 只读，不写 setter 就无法被外部篡改。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-01-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "类属性与实例属性最主要的区别是？",
                        "options": [
                            ("A", "类属性只能存数字"),
                            ("B", "类属性所有实例共享一份，实例属性每个对象各有一份"),
                            ("C", "实例属性必须大写"),
                            ("D", "类属性不能被修改"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "类属性挂在类上，所有实例读到同一份；实例属性在 __init__ 里用 self 赋值，每个对象独立。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-01-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 self，下列说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "调用实例方法时由 Python 自动传入"),
                            ("B", "它只是一个约定名，改成别的名字语法上也合法"),
                            ("C", "它指向当前调用该方法的对象"),
                            ("D", "必须在每个方法里手动传实参"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "self 是约定名而非关键字，实例调用时自动绑定当前对象，调用方不需要手动传。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-01-02-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''下面代码输出什么？
class Box:
    size = 10

a = Box()
b = Box()
a.size = 3
print(a.size, b.size, Box.size)''',
                        "answer": {
                            "reference": "输出 3 10 10。给 a.size 赋值会在 a 上新建一个实例属性，类属性和 b 都不受影响。",
                            "keywords": ["3 10 10", "实例属性", "遮蔽"],
                        },
                        "explanation": "读取时先找实例属性、再找类属性；写入 a.size 只影响 a 自己，等于遮蔽了同名类属性。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-01-02-4",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "只给属性写了 @property 而没有写 setter 时，直接给它赋值会抛出 AttributeError。",
                        "answer": {"value": True},
                        "explanation": "没有 setter 的 property 是只读属性，赋值时 Python 抛 AttributeError: property has no setter。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-01-02-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "给 Account 增加只读属性 summary，返回「户主 / 余额」格式的字符串，不允许外部赋值。",
                        "answer": {
                            "reference": '''@property
def summary(self):
    return f"{self.owner} / {self._balance}"''',
                            "keywords": ["@property", "self.owner", "self._balance"],
                        },
                        "explanation": "只写 @property 不写 setter，属性天然只读；这种派生值不适合单独存字段。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-01-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「把列表当类属性」在多人协作时特别危险？请结合两个实例说明。",
                        "answer": {
                            "reference": "类属性只有一份，任何一个实例往里 append，其他实例读到的都是被改过的内容。别人在自己模块里改数据，你在另一个模块看到脏值，很难定位。把容器类数据放到 __init__ 里，每个对象独立，才能避免这种隐式共享。",
                            "keywords": ["共享", "append", "独立", "定位"],
                        },
                        "explanation": "能指出「隐式共享导致跨模块脏数据、难以定位」即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "python-advanced-02",
        "title": "继承与多态",
        "description": "复用父类能力，用统一接口处理不同的子类。",
        "order_index": 2,
        "lessons": [
            {
                "code": "python-advanced-02-lesson-01",
                "objectives": """1. 会写 `class 子类(父类)` 完成继承；
2. 会用 `super().__init__()` 复用父类初始化；
3. 会重写方法并在需要时调用父类版本；
4. 知道什么时候不该用继承。""",
                "why_learn": """项目里同类对象往往只差一点点：都是「任务」，但有的定时、有的可重复。
如果每个都从头写一遍，公共逻辑会散落在很多地方，改一处漏三处。继承让公共部分只写一次。""",
                "concepts": """**父类（基类）** 提供公共属性和方法；**子类（派生类）** 继承父类并可以扩展。
**重写（override）** 指子类定义同名方法，覆盖父类版本。
`super()` 返回父类的代理对象，用来调用父类实现，最常见的是 `super().__init__(...)`。
子类自动拥有父类的全部公开方法，不需要复制粘贴。""",
                "plain": """继承像「户口本」：父类写好了基本信息栏，子类只需要补自己那几栏特殊内容。
`super().__init__()` 相当于「先把父母那部分填好，再填我自己的」，漏了这一步，
父类准备好的属性就不存在，用的时候会直接报错。""",
                "syntax": """```python
class 父类:
    def __init__(self, 公共参数):
        self.公共属性 = 公共参数

    def 方法(self):
        ...


class 子类(父类):
    def __init__(self, 公共参数, 自己的参数):
        super().__init__(公共参数)   # 先初始化父类部分
        self.自己的属性 = 自己的参数

    def 方法(self):                  # 重写
        return super().方法() + "（子类增强）"
```""",
                "example_code": '''class Task:
    def __init__(self, title):
        self.title = title
        self.done = False

    def describe(self):
        return f"{self.title}（{'已完成' if self.done else '未完成'}）"


class DeadlineTask(Task):
    def __init__(self, title, due):
        super().__init__(title)
        self.due = due

    def describe(self):
        return super().describe() + f"，截止 {self.due}"

    def postpone(self, days):
        self.due += days


class RecurringTask(Task):
    def __init__(self, title, every_days):
        super().__init__(title)
        self.every_days = every_days

    def describe(self):
        return super().describe() + f"，每 {self.every_days} 天重复"


plain = Task("写周报")
urgent = DeadlineTask("交季度报表", 30)
daily = RecurringTask("站会", 1)

for task in (plain, urgent, daily):
    print(task.describe())
print(isinstance(urgent, Task), issubclass(DeadlineTask, Task))''',
                "code_lines": """1. `class Task:` 是父类，提供 title、done 与 describe 三个公共成员。
2. `class DeadlineTask(Task):` 括号里写父类名，表示继承 Task。
3. `super().__init__(title)` 先执行父类初始化，title 与 done 才会被创建。
4. `self.due = due` 是子类新增的属性，父类并不知道它。
5. `super().describe()` 先拿到父类的描述文本，再拼接自己的部分，避免重复写状态判断。
6. `postpone` 是子类独有的方法，父类实例没有这个方法。
7. 循环里三个对象都调用 `describe()`，各自执行自己的版本，这就是后面要讲的多态。
8. `isinstance` 判断「是不是 Task 的一种」，`issubclass` 判断类之间的继承关系。""",
                "output": """写周报（未完成）
交季度报表（未完成），截止 30
站会（未完成），每 1 天重复
True True""",
                "mistakes": """- 子类写了 `__init__` 但忘了调 `super().__init__()`，父类属性不存在。
- `super().__init__(title)` 写成 `super().__init__()`，漏传参数。
- 重写 `describe` 时完全重写一遍，父类逻辑改动后两边不一致。
- 用继承表达「有一个」的关系（比如让 Order 继承 User）。
- 继承层次过深，改一个父类方法影响一大片。""",
                "error_analysis": """`AttributeError: 'DeadlineTask' object has no attribute 'title'`
—— 子类忘了调 `super().__init__(title)`，父类那部分初始化根本没执行。

`TypeError: super(type, obj): obj must be an instance or subtype of type`
—— 在类外部或静态上下文里用了 `super()`，它只能在实例方法里正常工作。

`TypeError: __init__() takes 2 positional arguments but 3 were given`
—— 继承链上传参不匹配，常见于子类 `__init__` 多了一个参数却直接 `super().__init__()`。""",
                "beginner_practice": """1. 写父类 `Shape`，方法 `area()` 抛 `NotImplementedError`；再写子类 `Square` 与
   `Circle` 分别实现自己的 `area()`。
2. 用一个列表装三种图形，循环打印各自的面积。""",
                "advanced_practice": """给 `DeadlineTask` 增加 `is_overdue(today)`：当 `today > due` 且未完成时返回 True。
再用 `super()` 保证 `describe()` 在逾期时多带一个「已逾期」标记，而不是复制父类逻辑。""",
                "quiz_note": "本节 6 道题：重点看 `super()` 的调用顺序与重写时复用父类逻辑。",
                "summary": """用 `class 子类(父类)` 继承，用 `super().__init__()` 初始化父类部分；
重写方法时优先 `super()` 复用而不是整段复制。
判断标准：**「是一种」用继承，「有一个」用组合**。""",
                "next_lesson": "下一节讲多态与组合：为什么同一个循环能处理不同子类，以及为什么组合往往比继承更稳。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-02-01",
                        "name": "继承、super 与方法重写",
                        "goal": "能用继承复用父类实现，正确调用 super()，并按需重写方法。",
                        "minutes": 35,
                        "criteria": "能写出父子类并在子类中复用父类逻辑，不复制粘贴父类代码。",
                        "requires": ["python-advanced-01-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-02-01-1",
                        "kp": 0,
                        "title": "图形面积",
                        "description": "写 Shape 父类（area 抛 NotImplementedError），再写 Square 与 Circle 继承并实现 area。用列表统一遍历打印。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''import math


class Shape:
    def area(self):
        raise NotImplementedError("子类必须实现 area")


class Square(Shape):
    def __init__(self, side):
        self.side = side

    def area(self):
        return self.side ** 2


class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius

    def area(self):
        return round(math.pi * self.radius ** 2, 2)


for shape in (Square(3), Circle(2)):
    print(shape.area())''',
                        "explanation": "父类只声明接口，子类各自实现；用同一个循环处理不同子类，正是多态的价值。",
                    },
                    {
                        "code": "adv-ex-02-01-2",
                        "kp": 0,
                        "title": "逾期判断",
                        "description": "给 DeadlineTask 增加 is_overdue(today)，并在 describe 里用 super() 复用父类文本，逾期时追加标记。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class DeadlineTask(Task):
    def __init__(self, title, due):
        super().__init__(title)
        self.due = due

    def is_overdue(self, today):
        return today > self.due and not self.done

    def describe(self, today=None):
        text = super().describe()
        if today is not None and self.is_overdue(today):
            text += "【已逾期】"
        return text''',
                        "explanation": "用 super().describe() 拿到父类文本再追加，父类改文案时子类自动跟随。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-02-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "子类定义 __init__ 时，为什么要调用 super().__init__(...)?",
                        "options": [
                            ("A", "语法强制要求，不写会报语法错误"),
                            ("B", "为了执行父类的初始化逻辑，创建父类那部分属性"),
                            ("C", "为了让子类拥有父类的类名"),
                            ("D", "为了提高运行速度"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "父类属性是在父类 __init__ 里创建的，不调用就不会存在；这不是语法强制，而是逻辑必需。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-02-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些情况适合用继承解决？（多选）",
                        "options": [
                            ("A", "两种任务只有截止时间这一个差异，其余行为相同"),
                            ("B", "订单需要访问用户对象，所以让 Order 继承 User"),
                            ("C", "多个类都需要同一套日志格式方法"),
                            ("D", "为了少写代码，让子类继承一个包含 40 个方法的巨型类"),
                        ],
                        "answer": {"values": ["A", "C"]},
                        "explanation": "继承适用于「是一种」且差异集中在少数行为的情况；B 是「有一个」应用组合，D 会造成脆弱基类。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-02-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码输出什么？
class A:
    def hello(self):
        return "A"

class B(A):
    def hello(self):
        return super().hello() + "B"

print(B().hello())''',
                        "answer": {
                            "reference": "输出 AB。B 的 hello 先取父类结果 A，再拼上 B。",
                            "keywords": ["AB", "super", "拼接"],
                        },
                        "explanation": "super().hello() 调用父类实现返回 A，加上 B 得到 AB；顺序由拼接位置决定。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-02-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "如果子类重写了 `__init__` 却没有调用 `super().__init__()`，父类属性依然会自动创建。",
                        "answer": {"value": False},
                        "explanation": "属性只在父类 __init__ 执行时创建；子类覆盖了 __init__ 又不调用父类版本，父类属性就不存在。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-02-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写父类 Animal（方法 speak 返回「...」）与子类 Dog，重写 speak 返回「汪汪」，并复用父类返回值做前缀。",
                        "answer": {
                            "reference": '''class Animal:
    def speak(self):
        return "..."


class Dog(Animal):
    def speak(self):
        return super().speak() + "汪汪"''',
                            "keywords": ["class Dog(Animal)", "super().speak()"],
                        },
                        "explanation": "子类括号里写明父类，重写时用 super() 取父类结果，避免整段复制。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-02-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "有人说「继承会让修改变危险」。结合「重写父类方法」说明这句话的成立条件。",
                        "answer": {
                            "reference": "子类依赖父类的方法行为，一旦父类改了实现或删了方法，所有子类的重写都可能失效甚至报错，而且影响面分散在很多文件里。层次越深、重写越多，这种耦合越强。控制层次、优先组合、把父类方法当成契约来维护，能降低风险。",
                            "keywords": ["耦合", "影响面", "契约", "组合"],
                        },
                        "explanation": "能指出「子类隐式依赖父类实现细节」这一耦合来源即可。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-advanced-02-lesson-02",
                "objectives": """1. 说清多态在 Python 里是怎么实现的（鸭子类型）；
2. 能用统一接口处理不同子类；
3. 会用 `__str__` 与 `__eq__` 让对象更自然；
4. 能用组合替代不必要的继承。""",
                "why_learn": """写业务代码时经常要「按类型分支」：任务、子任务、定时任务各走一套逻辑。
如果到处写 `if isinstance(...)`，每加一种类型就要改所有分支。多态把分支收进对象自己身上。""",
                "concepts": """**多态**：调用同一个方法名，不同对象给出各自的行为，调用方不需要判断类型。
Python 靠**鸭子类型**实现：只要对象有需要的方法就能用，不要求显式继承。
**魔术方法**（dunder）让对象支持内置操作：`__str__` 决定 `print` 的结果，
`__repr__` 决定调试显示，`__eq__` 决定 `==` 的比较规则。
**组合**：把另一个对象作为属性持有，通过它完成任务，而不是继承它。""",
                "plain": """多态像「统一遥控器」：你按下「播放」，电视、音箱、投影仪各自用自己的方式响应，
你不需要先判断手里是哪种设备。鸭子类型更进一步——不问「你是不是播放器家族」，
只问「你会不会播放」。组合则像「电脑里装了显卡」：电脑不是显卡的一种，
但它有一块显卡，需要时调用它。""",
                "syntax": """```python
class 类:
    def __str__(self):        # print(obj) 时显示
        return "给人看的文本"

    def __repr__(self):       # 调试、列表打印时显示
        return "Task(title=...)"

    def __eq__(self, other):  # obj == other
        if not isinstance(other, 类):
            return NotImplemented
        return self.关键字段 == other.关键字段


# 组合
class Service:
    def __init__(self, repo):
        self.repo = repo       # 持有，而不是继承
```""",
                "example_code": '''class Task:
    def __init__(self, title, done=False):
        self.title = title
        self.done = done

    def __str__(self):
        return f"任务：{self.title}"

    def __repr__(self):
        return f"Task(title={self.title!r}, done={self.done!r})"

    def __eq__(self, other):
        if not isinstance(other, Task):
            return NotImplemented
        return (self.title, self.done) == (other.title, other.done)


class DeadlineTask(Task):
    def __str__(self):
        return super().__str__() + "（有截止时间）"


class TaskList:
    """组合：自己不继承 Task，而是持有一批任务。"""

    def __init__(self):
        self.items = []

    def add(self, task):
        self.items.append(task)

    def pending(self):
        return [task for task in self.items if not task.done]

    def __len__(self):
        return len(self.items)


tasks = TaskList()
tasks.add(Task("写周报"))
tasks.add(DeadlineTask("交报表"))
tasks.add(Task("订会议室", done=True))

for task in tasks.items:
    print(str(task))

print(len(tasks), len(tasks.pending()))
print(repr(tasks.items[0]))
print(Task("写周报") == Task("写周报"))''',
                "code_lines": """1. `__str__` 让 `print(task)` 输出人类可读文本，而不是内存地址。
2. `__repr__` 用 `!r` 显示带引号的原始值，调试时能一眼看出字段内容。
3. `__eq__` 先判断类型是否匹配，不匹配返回 `NotImplemented`，让 Python 去尝试另一侧比较。
4. 子类 `DeadlineTask` 只重写 `__str__`，`__eq__` 与 `__repr__` 直接从父类继承。
5. `class TaskList` 用**组合**：内部持有 `items` 列表，自己不是任务。
6. `pending()` 用列表推导式过滤未完成任务，调用方不需要知道内部结构。
7. `__len__` 让 `len(tasks)` 直接可用，这是让对象贴合内置协议的常见做法。
8. 循环里 `str(task)` 对不同子类产生不同文本，调用方没有写任何类型判断。
9. 最后一行比较两个内容相同的 Task，`__eq__` 决定它返回 True。""",
                "output": """任务：写周报
任务：交报表（有截止时间）
任务：订会议室
3 2
Task(title='写周报', done=False)
True""",
                "mistakes": """- 只写 `__repr__` 不写 `__str__`，`print` 会退化用 repr，未必好读。
- `__eq__` 里不检查类型，导致跨类型比较出错或恒等怪异。
- 重写 `__eq__` 却忘了 `__hash__`，对象放进 set 会报 unhashable。
- 用 `isinstance` 长链代替多态，新增类型时要改多处。
- 为了复用两个方法就继承整个类，引入一堆无关方法。""",
                "error_analysis": """`TypeError: unhashable type: 'Task'`
—— 定义了 `__eq__` 后默认 `__hash__` 变成 None，对象不能再放进 set 或当字典键。要放就补 `__hash__`。

`AttributeError: 'TaskList' object has no attribute 'done'`
—— 误以为 TaskList 继承了 Task。组合关系下要访问 `tasks.items[0].done`，不能直接 `tasks.done`。

`TypeError: '<' not supported between instances of 'Task' and 'Task'`
—— 只定义了 `__eq__`，没有定义 `__lt__`，排序会失败。""",
                "beginner_practice": """1. 给 `Task` 加 `__lt__`，按 `done` 再按 `title` 排序，用 `sorted()` 验证。
2. 给 `TaskList` 加 `__iter__`，让 `for task in tasks:` 直接可用。""",
                "advanced_practice": """把「按状态统计」做成多态：给 Task 与 DeadlineTask 各自实现 `urgency()`，
Task 返回 1、DeadlineTask 按剩余天数返回 0—3。写一个 `top_tasks(tasks)` 返回最紧急的两个，
要求函数内部不出现任何 `isinstance` 判断。""",
                "quiz_note": "本节 6 道题：重点考鸭子类型、`__eq__` 的类型检查以及组合与继承的取舍。",
                "summary": """多态让调用方只认方法名，不认类型；Python 用鸭子类型实现，不需要显式继承。
`__str__`/`__repr__`/`__eq__` 让对象贴合内置语法；组合比继承更松耦合。
一句话记住：**能组合就别继承，必须继承就只继承接口**。""",
                "next_lesson": "下一节进入推导式：把「遍历 + 过滤 + 转换」压缩成一行，并说清什么时候不该用。",
                "knowledge_points": [
                    {
                        "code": "python-advanced-02-02",
                        "name": "多态、魔术方法与组合",
                        "goal": "能用统一接口处理不同子类，会用常见魔术方法，并能用组合替代滥用继承。",
                        "minutes": 35,
                        "criteria": "能写出不含 isinstance 分支的多态调用，并说明为什么组合更稳。",
                        "requires": ["python-advanced-02-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "adv-ex-02-02-1",
                        "kp": 0,
                        "title": "可排序的任务",
                        "description": "给 Task 实现 __lt__：未完成的排在前面，同状态按标题字母序。用 sorted 验证结果。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class Task:
    def __init__(self, title, done=False):
        self.title = title
        self.done = done

    def __lt__(self, other):
        if not isinstance(other, Task):
            return NotImplemented
        return (self.done, self.title) < (other.done, other.title)


tasks = [Task("b"), Task("a", done=True), Task("c")]
print([t.title for t in sorted(tasks)])  # ['c', 'b', 'a']''',
                        "explanation": "用元组比较一次性表达两级排序；False < True 恰好让未完成的排前面。",
                    },
                    {
                        "code": "adv-ex-02-02-2",
                        "kp": 0,
                        "title": "多态求紧急度",
                        "description": "Task 的 urgency 返回 1，DeadlineTask 按剩余天数返回 0—3；写 top_tasks 取最紧急的两个，函数内不得出现 isinstance。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def top_tasks(tasks, limit=2):
    return sorted(tasks, key=lambda task: task.urgency())[:limit]''',
                        "explanation": "排序键直接调用 urgency()，不同子类各自实现，新增类型时 top_tasks 无需修改。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-adv-02-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "Python 的「鸭子类型」指的是？",
                        "options": [
                            ("A", "必须显式继承同一个父类才能统一调用"),
                            ("B", "只要对象有需要的方法就能被统一处理，不强制继承关系"),
                            ("C", "所有对象都自动继承 object，所以都算多态"),
                            ("D", "只有内置类型支持多态"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "鸭子类型的判断标准是「有没有这个方法」，而不是「是不是某个类的子类」。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-02-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 `__eq__`，下列说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "定义后 `==` 会比较对象内容"),
                            ("B", "类型不匹配时返回 NotImplemented 更稳妥"),
                            ("C", "定义后对象默认变成不可哈希"),
                            ("D", "它会自动让对象支持排序"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "排序需要 __lt__，__eq__ 不提供大小比较，所以 D 错；其余三项都是 __eq__ 的真实行为。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-adv-02-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码输出什么？
class A:
    def show(self):
        return "A"

class B:
    def show(self):
        return "B"

for item in (A(), B()):
    print(item.show(), end="")''',
                        "answer": {
                            "reference": "输出 AB。两个类没有共同父类，但都有 show，循环照样能统一调用。",
                            "keywords": ["AB", "鸭子类型", "无共同父类"],
                        },
                        "explanation": "这正是鸭子类型：调用方只依赖 show 这个行为，与继承关系无关。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-02-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只定义 `__str__` 而不定义 `__repr__` 时，把对象放进列表再打印，显示的是 `__str__` 的结果。",
                        "answer": {"value": False},
                        "explanation": "容器打印走 repr；只定义 __str__ 时列表里显示的是默认的 `<__main__.Task object at 0x...>`。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-adv-02-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个 LoggedRepo 类，内部持有一个 repo 对象（组合），list_all() 先打印「查询」再委托给 repo.list_all()。",
                        "answer": {
                            "reference": '''class LoggedRepo:
    def __init__(self, repo):
        self.repo = repo

    def list_all(self):
        print("查询")
        return self.repo.list_all()''',
                            "keywords": ["self.repo", "委托", "组合"],
                        },
                        "explanation": "组合让增强逻辑包在外面，被装饰的 repo 不需要知道自己被包装过。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-adv-02-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "在「任务列表要统计未完成数量」这个需求里，为什么把统计写进 TaskList 比写成 `if isinstance` 分支更好？",
                        "answer": {
                            "reference": "统计只依赖 done 这个属性，把它放进 TaskList 后，新增任务类型只要遵守同样的属性约定就能被统计，不需要改统计代码。若用 isinstance 分支，每加一种类型都要回去补一个分支，容易漏，也把类型知识散落到多处。",
                            "keywords": ["新增类型", "分支", "达配", "属性约定"],
                        },
                        "explanation": "能指出「新增类型时不需要改调用方」这一核心收益即可。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
