"""第 11—12 章教材内容：while 循环、函数。"""

CHAPTERS: list[dict] = [
    # ------------------------------------------------------------------ 第 11 章
    {
        "code": "python-basics-11",
        "order_index": 11,
        "title": "while 循环",
        "description": "当循环次数事先不知道、只能靠条件决定时，用 while 一直做，直到条件不再成立。",
        "lessons": [
            {
                "code": "python-basics-11-l01",
                "title": "while 循环、break 与常见陷阱",
                "description": "用条件控制循环，写出会终止的 while，避免死循环。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 会写 while 循环，理解「条件为真就一直做」。
2. 会在循环里更新条件变量，保证循环能结束。
3. 能用 while 配合 break 实现「不确定次数」的循环。""",
                "why_learn": """for 适合「我知道要做几次」，while 适合「做到满足条件为止」。
比如「一直输入直到用户说退出」「余额不够就继续提醒」，
这类次数不确定的场景只能用 while，它也是后面写菜单、写游戏循环的基础。""",
                "concepts": """- **while**：条件为 True 时重复执行循环体，每轮开始前都重新判断。
- **循环变量**：参与条件判断的变量，必须在循环里被修改，否则永不结束。
- **死循环**：条件永远为真，程序卡住不退出。
- **break**：在循环内部提前结束。""",
                "plain": """while 像「水开了就关火」这类判断：只要还没开，就一直等着看着。
关键是每看一次都要有变化（水越来越热），否则你会永远站在灶台前。
写 while 时先问自己一句：哪个变量会让条件最终变成假？它在循环里被改了吗？""",
                "syntax": """while 条件:
    循环体
    更新条件变量

count = 3
while count > 0:
    print(count)
    count = count - 1     忘记这行就是死循环

while True:
    ...
    if 退出条件:
        break""",
                "example_code": '''count = 3
while count > 0:
    print("倒计时：", count)
    count = count - 1
print("发射！")

total = 0
n = 1
while n <= 100:
    total = total + n
    n = n + 1
print("1 到 100 的和：", total)

attempt = 0
while True:
    attempt = attempt + 1
    print("第", attempt, "次尝试")
    if attempt == 3:
        print("达到上限，停止")
        break''',
                "code_lines": """- 第 1 至 4 行：count 从 3 开始，每轮打印后减 1，减到 0 时条件不成立，循环结束。
- 第 6 至 10 行：n 从 1 加到 100，每轮把 n 累加进 total 并让 n 前进，最终得到 5050。
- 第 12 至 18 行：while True 是故意设成永真，靠内部的 break 退出，适合次数不确定的场景。""",
                "output": """倒计时： 3
倒计时： 2
倒计时： 1
发射！
1 到 100 的和： 5050
第 1 次尝试
第 2 次尝试
第 3 次尝试
达到上限，停止""",
                "mistakes": """1. 忘记在循环里改变量，造成死循环。
2. 条件写反，循环一次都不执行。
3. 在 while 里用 = 代替 ==。
4. break 写在条件外，循环永远走不到。
5. 把 for 能做的事硬写成 while，代码更难读。""",
                "error_analysis": """- 忘记 count = count - 1，count 永远是 3，条件永远成立，程序卡死。此时只能强制中断运行。
- 条件一开始就不成立（如 count = 0 却写 while count > 3），循环体一次都不执行，容易误以为代码没跑。
- while count = 3 报 SyntaxError：赋值不能作为条件，比较要用 ==。
- break 缩进到循环外会报语法错误；缩进到 if 内才是有条件的退出。
- 次数确定的场景用 for 更清晰，while 留给「不确定次数」。""",
                "beginner_practice": """用 while 输出 5 到 1 的倒计时，最后输出「开始」。""",
                "advanced_practice": """用 while 不断读入整数并累加，读到 0 时停止并输出总和（提示：input 后转 int，用 break 退出）。""",
                "quiz_note": """本节测验 6 题：2 题考 while 的执行条件与死循环成因，2 题读代码判断执行次数，2 题写带退出条件的 while。""",
                "summary": """- while 每轮开始前判断条件，为真才继续。
- 循环里必须更新条件变量，否则死循环。
- while True 加 break 适合次数未知的场景。
- 次数确定用 for，次数不定用 while。""",
                "next_lesson": """下一章学函数：把重复的代码打包成一个名字，需要时调用一次即可。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-11-k01",
                        "legacy": "python-basics-04-03",
                        "name": "while 循环",
                        "goal": "会写能正常结束的 while 循环",
                        "minutes": 30,
                        "criteria": "能指出循环中哪个语句保证循环会结束，能预测执行次数",
                    },
                    {
                        "code": "python-basics-11-k02",
                        "name": "循环选择与死循环防范",
                        "goal": "能区分 for 与 while 的适用场景并避免死循环",
                        "minutes": 20,
                        "criteria": "能说明死循环的三个常见成因，能为给定需求选对循环类型",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-11-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "倒计时",
                        "description": "用 while 输出 5 到 1，最后输出「开始」。",
                        "answer": 'n = 5\nwhile n > 0:\n    print(n)\n    n = n - 1\nprint("开始")',
                        "explanation": "n 每轮减 1，减到 0 时退出循环。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-11-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "累加到 0 为止",
                        "description": "不断读入整数并累加，输入 0 时停止并输出总和。",
                        "answer": 'total = 0\nwhile True:\n    n = int(input("输入整数（0 结束）："))\n    if n == 0:\n        break\n    total = total + n\nprint(total)',
                        "explanation": "次数未知，用 while True 配合 break 退出。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-11-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "while 循环在什么时候结束？",
                        "options": [
                            ("A", "循环体执行一次后"),
                            ("B", "条件变为 False 时"),
                            ("C", "遇到 print 时"),
                            ("D", "必须手动关闭程序"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "每轮开始前重新判断条件，条件为假就退出。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-11-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "如果 while 循环体里没有修改条件变量，循环会一直执行下去。",
                        "answer": {"value": True},
                        "explanation": "条件始终为真就是死循环，这是最常见的错误。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-11-l01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''n = 3
while n > 0:
    print(n)
    n = n - 1
print("结束")''',
                        "answer": {
                            "reference": "依次输出 3、2、1，最后输出「结束」。n 减到 0 时条件不成立，循环退出后执行最后一行。",
                            "keywords": ["3", "2", "1", "结束"],
                        },
                        "explanation": "注意最后一行在循环外，缩进与 while 对齐。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-11-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": '''n = 0
while n < 3:
    print(n)
循环会输出几行？''',
                        "options": [
                            ("A", "3 行"),
                            ("B", "无限多行"),
                            ("C", "1 行"),
                            ("D", "0 行"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "n 从未改变，条件永远成立，形成死循环。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-11-l01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "用 while 求 1 到 50 的和并输出。",
                        "answer": {
                            "reference": "total = 0\nn = 1\nwhile n <= 50:\n    total = total + n\n    n = n + 1\nprint(total)",
                            "keywords": ["while", "total", "n = n + 1", "50"],
                        },
                        "explanation": "循环里同时更新累加值和计数变量。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-11-l01-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "什么情况下应该用 while 而不是 for？举一个具体例子。",
                        "answer": {
                            "reference": "循环次数事先不确定、只能靠条件决定时用 while。例如不断读入用户输入直到输入 0 为止，事先不知道会输几次。",
                            "keywords": ["次数不确定", "条件", "直到", "输入"],
                        },
                        "explanation": "能抓住「次数未知」这一判断标准即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ------------------------------------------------------------------ 第 12 章
    {
        "code": "python-basics-12",
        "order_index": 12,
        "title": "函数",
        "description": "把一段代码打包成一个名字：定义、调用、复用，让程序从「一长串」变成「几个清晰的步骤」。",
        "lessons": [
            {
                "code": "python-basics-12-l01",
                "title": "定义函数与调用函数",
                "description": "用 def 定义函数、用函数名调用，认识常见内置函数。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 会用 def 定义函数并调用。
2. 理解函数体必须缩进，定义时不会执行。
3. 会用 len、max、min、sum、abs、round 等内置函数。""",
                "why_learn": """程序一旦变长，把所有代码堆在一起会难以阅读、难以修改。
函数把「做一件事的若干行」打包并命名，主流程只剩几个清晰的步骤。
从这一节开始，你写的代码开始具备结构。""",
                "concepts": """- **函数**：一段有名字、可重复调用的代码块。
- **定义**：用 def 函数名(): 声明，函数体缩进。
- **调用**：写函数名加括号，才会真正执行。
- **内置函数**：Python 自带、不需要定义就能用的函数。""",
                "plain": """函数像家电上的一个按钮：你把「加热三分钟」这套动作封装进「热饭」按钮，
以后按一下就行，不用每次重新接线。
定义函数是「装按钮」，调用函数是「按按钮」。装好不按，什么都不会发生。""",
                "syntax": """def 函数名():
    函数体（缩进）

函数名()          调用

内置函数示例：
len([1, 2, 3])    长度，得 3
max(1, 5, 3)      最大值，得 5
min(1, 5, 3)      最小值，得 1
sum([1, 2, 3])    求和，得 6
abs(-7)           绝对值，得 7
round(3.14159, 2) 保留两位小数，得 3.14""",
                "example_code": '''def say_hello():
    print("你好，欢迎学习 Python")
    print("今天我们从函数开始")

print("准备调用")
say_hello()
print("调用结束")

def show_line():
    print("-" * 20)

show_line()
print("小码 Python 教程")
show_line()

print("长度：", len([1, 2, 3, 4]))
print("最大值：", max(3, 9, 2))
print("绝对值：", abs(-7))
print("四舍五入：", round(3.14159, 2))''',
                "code_lines": """- 第 1 至 3 行：def 定义函数，函数体缩进。此时只是「装好按钮」，并不会输出。
- 第 5 行：普通语句，会执行。
- 第 6 行：调用函数，才真正执行函数体里的两行。
- 第 9 至 12 行：定义 show_line 用来输出一条分隔线，之后调用两次包住标题。
- 第 14 至 17 行：直接使用内置函数完成常见计算。""",
                "output": """准备调用
你好，欢迎学习 Python
今天我们从函数开始
调用结束
--------------------
小码 Python 教程
--------------------
长度： 4
最大值： 9
绝对值： 7
四舍五入： 3.14""",
                "mistakes": """1. 定义后忘记调用，以为会自动执行。
2. 函数体不缩进，报 IndentationError。
3. 调用时漏写括号，只是提到函数对象，不会执行。
4. 函数名用了关键字或与内置函数重名（如 list）。
5. 把 def 写在调用之后又想立刻用。""",
                "error_analysis": """- 只写 def 不调用，程序不会有任何输出，因为定义不等于执行。
- 函数体不缩进报 IndentationError: expected an indented block。
- 写 say_hello 不加括号，输出的是一个函数对象说明，不会执行函数体。
- 把函数命名为 list 会覆盖内置的 list，之后再调用 list() 就会出错。
- Python 从上到下执行，调用必须写在定义之后（或先定义再调用）。""",
                "beginner_practice": """定义一个函数输出三行个人信息，然后调用两次。""",
                "advanced_practice": """定义函数 show_menu 输出一个三行菜单，再定义 show_line 输出分隔线，组合输出「分隔线 + 菜单 + 分隔线」。""",
                "quiz_note": """本节测验 6 题：2 题考定义与调用的区别，2 题读代码判断输出顺序，2 题写无参函数并组合调用。""",
                "summary": """- def 定义函数，函数名加括号才调用。
- 定义不会执行，调用才执行。
- 函数体必须缩进。
- 内置函数可以直接用，不要用它们当自己的函数名。""",
                "next_lesson": """下一课把重复代码真正抽成函数：让函数接收数据、返回结果，而不只是打印固定内容。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-12-k01",
                        "legacy": "python-basics-05-01",
                        "name": "定义函数 def",
                        "goal": "会用 def 定义函数并按需调用",
                        "minutes": 25,
                        "criteria": "能说明定义与调用的区别，能写出缩进正确的函数",
                    },
                    {
                        "code": "python-basics-12-k02",
                        "legacy": "python-basics-05-05",
                        "name": "常用内置函数",
                        "goal": "会用 len / max / min / sum / abs / round",
                        "minutes": 25,
                        "criteria": "能针对给定需求选对内置函数并预测结果",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-12-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "自我介绍函数",
                        "description": "定义函数输出三行个人信息，调用两次。",
                        "answer": 'def intro():\n    print("姓名：小明")\n    print("年龄：18")\n    print("城市：杭州")\n\nintro()\nintro()',
                        "explanation": "定义一次，调用两次，输出六行。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-12-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "用内置函数算一算",
                        "description": "对列表 [4, 9, 2, 7] 输出长度、最大值、最小值、总和。",
                        "answer": 'nums = [4, 9, 2, 7]\nprint(len(nums))\nprint(max(nums))\nprint(min(nums))\nprint(sum(nums))',
                        "explanation": "四个内置函数分别对应四种统计。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-12-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "定义函数后不调用，会发生什么？",
                        "options": [
                            ("A", "函数体自动执行一次"),
                            ("B", "函数体不执行，程序照常往下走"),
                            ("C", "报错"),
                            ("D", "函数体执行两次"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "定义只是登记，调用才执行。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-12-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "round(3.14159, 2) 的结果是 3.14。",
                        "answer": {"value": True},
                        "explanation": "round 的第二个参数表示保留几位小数。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-12-l01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''def show():
    print("A")
print("B")
show()''',
                        "answer": {
                            "reference": "先输出 B，再输出 A。定义不执行，print(\"B\") 会先运行，最后调用 show 才输出 A。",
                            "keywords": ["B", "A", "定义不执行", "调用"],
                        },
                        "explanation": "输出顺序取决于执行顺序，而不是定义顺序。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-12-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "print(sum([1, 2, 3])) 的输出是？",
                        "options": [
                            ("A", "3"),
                            ("B", "6"),
                            ("C", "[1, 2, 3]"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "sum 求列表元素之和，1+2+3=6。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-12-l01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "定义函数 show_line 输出 20 个短横线，调用它包住一行标题输出。",
                        "answer": {
                            "reference": 'def show_line():\n    print("-" * 20)\n\nshow_line()\nprint("标题")\nshow_line()',
                            "keywords": ["def show_line", "print", '"-" * 20'],
                        },
                        "explanation": "无参函数封装固定输出，调用两次形成上下边框。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-12-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么函数体必须缩进？不缩进会怎样？",
                        "answer": {
                            "reference": "缩进用来标记哪些语句属于这个函数。不缩进时 Python 认为函数体是空的，报 IndentationError: expected an indented block。",
                            "keywords": ["缩进", "属于", "空函数体", "IndentationError"],
                        },
                        "explanation": "缩进在 Python 里是语法，不是排版偏好。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-basics-12-l02",
                "title": "把重复代码抽成函数",
                "description": "识别重复、抽出函数、用参数传入差异，让改动只发生在一处。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 能识别程序里重复出现的代码块。
2. 会把重复代码抽成函数，并用一个参数传入不同的值。
3. 能说清抽函数带来的两个好处：少写、好改。""",
                "why_learn": """重复代码是维护成本的主要来源：改一个规则要改五处，漏一处就出 bug。
把重复部分抽成函数，规则只写一次，以后只改一处。
这也是你第一次真正体会「参数」的用处——下一章会系统讲它。""",
                "concepts": """- **重复代码**：结构相同、只有个别数据不同的代码。
- **抽取**：把相同结构写进函数，把不同的数据变成参数。
- **参数**：定义时写在括号里的名字，调用时传入具体值。
- **好处**：减少重复、集中修改、逻辑有名字后更易读。""",
                "plain": """重复代码像每做一道菜都重新写一遍「洗锅、开火、倒油」。
抽成函数等于把这三步写成一个「起锅」按钮，做每道菜只按一下。
参数则是按钮上的旋钮：同样是「起锅」，火大点火小由你传进去的值决定。""",
                "syntax": """def 函数名(参数名):
    使用参数名

函数名(具体值)      调用时把值传给参数

def show_title(text):
    print("=" * 10)
    print(text)
    print("=" * 10)

show_title("第一章")""",
                "example_code": '''def show_title(text):
    print("=" * 12)
    print(text)
    print("=" * 12)

show_title("变量与类型")
show_title("列表与字典")

def show_price(name, price):
    print(name, "的价格是", price, "元")

show_price("苹果", 5)
show_price("香蕉", 3)

def repeat_line(times):
    print("-" * times)

repeat_line(10)
repeat_line(20)''',
                "code_lines": """- 第 1 至 4 行：把「上下边框加标题」这套重复结构抽成函数，标题作为参数传入。
- 第 6 至 7 行：同一函数调用两次，只改传入的标题，输出两段标题。
- 第 9 至 13 行：两个参数的函数，调用时按顺序把水果名和价格传进去。
- 第 15 至 19 行：参数也可以控制输出长度，调用时传不同数字得到不同长度的分隔线。""",
                "output": """============
变量与类型
============
============
列表与字典
============
苹果 的价格是 5 元
香蕉 的价格是 3 元
----------
--------------------""",
                "mistakes": """1. 抽取时把具体数据写死在函数里，函数仍然只能做一件事。
2. 调用时参数个数与定义不一致。
3. 参数名和函数外的变量重名，产生混淆。
4. 为了抽函数而抽函数，把一行代码也包一层。
5. 函数名起得太随意（如 f1、test）。""",
                "error_analysis": """- 把「苹果」写死在函数里，第二次想输出香蕉就得复制函数，抽取失去意义；应改为参数。
- 定义两个参数却只传一个，报 TypeError: missing 1 required positional argument。
- 多传参数报 TypeError: takes 2 positional arguments but 3 were given。
- 参数名与外层变量同名不会报错，但会让读代码的人分不清用的是哪个值。
- 只有一行且不会重复的代码不必抽函数，过度封装反而增加跳转成本。""",
                "beginner_practice": """把「输出分隔线、输出标题、输出分隔线」抽成函数，用它输出两个章节标题。""",
                "advanced_practice": """把「输出商品名与价格」抽成带两个参数的函数，调用三次输出三件商品。""",
                "quiz_note": """本节测验 6 题：2 题考抽取函数的判断与参数作用，2 题读代码判断输出，2 题写带参数的复用函数。""",
                "summary": """- 结构相同、数据不同的代码适合抽成函数。
- 把变化的部分变成参数，函数才有复用价值。
- 参数个数必须与调用时一致。
- 抽函数的目标是少写、好改、易读，不是越多越好。""",
                "next_lesson": """下一章系统讲函数参数与返回值：默认参数、关键字参数，以及怎么把结果交给调用者。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-12-k03",
                        "name": "重复代码抽取与函数复用",
                        "goal": "能把重复代码抽成带参数的函数",
                        "minutes": 25,
                        "criteria": "能指出哪段该抽、哪个值该变成参数，调用时参数个数正确",
                    }
                ],
                "practice": [
                    {
                        "code": "python-basics-12-k03-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "标题函数",
                        "description": "写函数 show_title(text)，输出上下边框与标题，调用两次。",
                        "answer": 'def show_title(text):\n    print("=" * 10)\n    print(text)\n    print("=" * 10)\n\nshow_title("第一章")\nshow_title("第二章")',
                        "explanation": "标题随参数变化，边框保持不变。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-12-k03-ex2",
                        "kp": 0,
                        "type": "coding",
                        "title": "商品价格函数",
                        "description": "写函数 show_price(name, price)，调用三次输出三件商品。",
                        "answer": 'def show_price(name, price):\n    print(name, "的价格是", price, "元")\n\nshow_price("苹果", 5)\nshow_price("香蕉", 3)\nshow_price("橙子", 6)',
                        "explanation": "两个参数对应名称与价格，调用时按顺序传入。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-12-l02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "把重复代码抽成函数时，变化的数据应该怎么处理？",
                        "options": [
                            ("A", "写死在函数体里"),
                            ("B", "变成函数的参数"),
                            ("C", "删掉不处理"),
                            ("D", "改成全局变量并在函数里改"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "变化的部分作为参数传入，函数才能复用。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-12-l02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "函数定义了两个参数，调用时只传一个也会正常运行，缺的自动为 None。",
                        "answer": {"value": False},
                        "explanation": "缺少必需参数会报 TypeError。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-12-l02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''def show(name):
    print("商品：", name)

show("苹果")
show("香蕉")''',
                        "answer": {
                            "reference": "输出「商品： 苹果」和「商品： 香蕉」两行。同一个函数被调用了两次，参数不同。",
                            "keywords": ["苹果", "香蕉", "两次", "参数"],
                        },
                        "explanation": "参数让同一段逻辑适配不同数据。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-12-l02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": '''def add(a, b):
    print(a + b)
add(1)
会怎样？''',
                        "options": [
                            ("A", "输出 1"),
                            ("B", "输出 0"),
                            ("C", "报 TypeError"),
                            ("D", "输出 None"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "定义了两个参数却只传一个，缺少必需的位置参数。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-12-l02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写函数 show_price(name, price)，调用三次输出三件商品的价格。",
                        "answer": {
                            "reference": 'def show_price(name, price):\n    print(name, "的价格是", price, "元")\n\nshow_price("苹果", 5)\nshow_price("香蕉", 3)\nshow_price("橙子", 6)',
                            "keywords": ["def show_price", "name", "price", "调用三次"],
                        },
                        "explanation": "两个参数分别对应名称与价格。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-12-l02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "把重复代码抽成函数有哪两个直接好处？请各用一句话说明。",
                        "answer": {
                            "reference": "一是少写：同一段逻辑只写一次，调用即可；二是好改：规则变化时只改函数体这一处，不会漏改。附加好处是逻辑有了名字，主流程更易读。",
                            "keywords": ["少写", "好改", "一处", "易读"],
                        },
                        "explanation": "能说清「集中修改」这一核心价值即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
