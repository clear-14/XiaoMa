"""第 13—16 章教材内容：函数参数与返回值、变量作用域、模块和包、文件读写。"""

CHAPTERS: list[dict] = [
    # ------------------------------------------------------------------ 第 13 章
    {
        "code": "python-basics-13",
        "order_index": 13,
        "title": "函数参数与返回值",
        "description": "让函数既能接收数据又能交出结果：位置参数、默认参数、关键字参数与 return。",
        "lessons": [
            {
                "code": "python-basics-13-l01",
                "title": "位置参数、默认参数与 return",
                "description": "用 return 把结果交给调用者，用默认参数与关键字参数让调用更灵活。",
                "minutes": 60,
                "difficulty": "beginner",
                "objectives": """1. 会用 return 返回结果，并区分「返回」与「打印」。
2. 会定义带默认值的参数，调用时按需覆盖。
3. 会用关键字参数改变传参顺序，避免顺序写错。""",
                "why_learn": """只会 print 的函数无法参与后续计算：结果打印完就散了。
return 把结果交回调用处，才能继续参与运算、存进变量、传给别的函数。
默认参数与关键字参数则让函数在多数场景下更好调用。""",
                "concepts": """- **参数**：函数定义时括号里的名字，调用时接收具体值。
- **位置参数**：按顺序一一对应，顺序错了结果就错。
- **默认参数**：定义时给参数一个默认值，调用时可省略。
- **关键字参数**：调用时写 参数名=值，顺序无关。
- **return**：把结果返回给调用处，并立刻结束函数。""",
                "plain": """函数像自动售货机：投进去的是参数，吐出来的是返回值。
打印相当于机器把结果念给你听，念完就没了；return 相当于把商品递到你手里，
你可以拿走、可以再加工，也可以放进包里。
默认参数则像「不加选择时默认给矿泉水」，你特殊说明才换别的。""",
                "syntax": """def 函数名(参数1, 参数2=默认值):
    函数体
    return 结果

结果 = 函数名(值1)              参数2 用默认值
结果 = 函数名(值1, 值2)         按位置传
结果 = 函数名(参数2=值2, 参数1=值1)   按名字传

没有 return 的函数，返回值是 None。""",
                "example_code": '''def add(a, b):
    return a + b

result = add(3, 5)
print("结果：", result)
print("再加工：", add(3, 5) * 2)

def greet(name, greeting="你好"):
    return greeting + "，" + name

print(greet("小明"))
print(greet("小红", "早上好"))
print(greet(greeting="晚上好", name="小刚"))

def show_only(a, b):
    print(a + b)

value = show_only(1, 2)
print("没有 return 的函数返回：", value)''',
                "code_lines": """- 第 1 至 2 行：add 用 return 把和交回调用处。
- 第 4 至 6 行：返回值可以存进变量，也可以直接参与运算。
- 第 8 至 9 行：greeting 有默认值，调用时可省略。
- 第 11 至 13 行：第二个参数按位置覆盖默认值；第三个调用用关键字参数，顺序颠倒也能正确匹配。
- 第 15 至 19 行：只打印不返回的函数，返回值是 None。""",
                "output": """结果： 8
再加工： 16
你好，小明
早上好，小红
晚上好，小刚
3
没有 return 的函数返回： None""",
                "mistakes": """1. 用 print 代替 return，结果无法参与后续计算。
2. 以为函数里 print 了就等于返回了值。
3. return 写在循环里，第一轮就结束了函数。
4. 默认参数放在非默认参数前面，导致语法错误。
5. 调用时关键字参数名写错，报 unexpected keyword argument。""",
                "error_analysis": """- 函数里只 print 不 return，调用处拿到的是 None，再参与加法会报 TypeError。
- return 一旦执行，函数立刻结束，后面的语句不会运行；放在循环里会只处理第一条。
- def f(a=1, b): 报 SyntaxError：有默认值的参数必须放在没有默认值的参数后面。
- 关键字参数名拼错，报 TypeError: got an unexpected keyword argument。
- return a, b 返回的是一个元组，接收时可以用解包。""",
                "beginner_practice": """写函数 area(width, height) 返回面积，调用后把结果乘以 2 输出。""",
                "advanced_practice": """写函数 make_card(name, city="杭州", job="学生") 返回一行自我介绍，分别用默认值、位置参数、关键字参数各调用一次。""",
                "quiz_note": """本节测验 6 题：2 题考 return 与 print 的区别、默认参数规则，2 题读代码判断返回值，2 题写带返回值的函数。""",
                "summary": """- return 把结果交回调用处，并立刻结束函数。
- 没有 return 的函数返回 None。
- 默认参数让调用更省事，但必须放在参数列表末尾。
- 关键字参数按名字匹配，不怕顺序写错。""",
                "next_lesson": """下一章讲变量作用域：为什么函数里改的变量，函数外看不到。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-13-k01",
                        "legacy": "python-basics-05-02",
                        "name": "参数与返回值",
                        "goal": "会用 return 返回结果并正确传参",
                        "minutes": 35,
                        "criteria": "能说明 return 与 print 的区别，能预测函数返回值",
                    },
                    {
                        "code": "python-basics-13-k02",
                        "name": "默认参数与关键字参数",
                        "goal": "会定义默认参数并用关键字参数调用",
                        "minutes": 25,
                        "criteria": "能写出合法的默认参数，能用关键字参数改变传参顺序",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-13-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "返回面积",
                        "description": "写函数 area(width, height) 返回面积，调用后把结果乘 2 输出。",
                        "answer": 'def area(width, height):\n    return width * height\n\nprint(area(3, 4) * 2)',
                        "explanation": "return 的结果可以直接参与运算。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-13-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "带默认值的名片",
                        "description": "写函数 make_card(name, city=\"杭州\") 返回介绍语，分别用默认值和指定城市调用。",
                        "answer": 'def make_card(name, city="杭州"):\n    return name + " 来自 " + city\n\nprint(make_card("小明"))\nprint(make_card("小红", "上海"))',
                        "explanation": "不传城市用默认值，传了就覆盖。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-13-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "函数里只写了 print 没有 return，调用后得到的返回值是？",
                        "options": [
                            ("A", "打印的内容"),
                            ("B", "0"),
                            ("C", "None"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "没有 return 的函数默认返回 None。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-13-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "def f(a=1, b): 这样的参数顺序是合法的。",
                        "answer": {"value": False},
                        "explanation": "有默认值的参数必须放在没有默认值的参数之后。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-13-l01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''def add(a, b):
    print(a + b)

result = add(2, 3)
print(result)''',
                        "answer": {
                            "reference": "先输出 5，再输出 None。函数只打印没有 return，result 拿到的是 None。",
                            "keywords": ["5", "None", "没有 return"],
                        },
                        "explanation": "print 只是显示，不影响返回值。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-13-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": '''def greet(name, greeting="你好"):
    return greeting + name
print(greet(greeting="早上好", name="小明"))
输出是？''',
                        "options": [
                            ("A", "你好小明"),
                            ("B", "早上好小明"),
                            ("C", "报错"),
                            ("D", "小明早上好"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "关键字参数按名字匹配，greeting 被覆盖为早上好。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-13-l01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写函数 total_price(price, count)，返回总价，并调用输出结果的两倍。",
                        "answer": {
                            "reference": 'def total_price(price, count):\n    return price * count\n\nprint(total_price(19.9, 3) * 2)',
                            "keywords": ["return", "price * count", "print"],
                        },
                        "explanation": "用 return 才能把结果拿来做二次运算。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-13-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "print 和 return 有什么区别？为什么说需要参与计算的函数必须用 return？",
                        "answer": {
                            "reference": "print 把内容显示到屏幕上，函数外部拿不到这个值；return 把结果交回调用处，可以存进变量、继续运算或传给别的函数。需要参与计算的函数必须 return，否则调用处只能得到 None。",
                            "keywords": ["显示", "交回", "None", "参与计算"],
                        },
                        "explanation": "抓住「外部能否拿到值」这一区别即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ------------------------------------------------------------------ 第 14 章
    {
        "code": "python-basics-14",
        "order_index": 14,
        "title": "变量作用域",
        "description": "为什么函数里改的变量外面看不到：局部、全局与 global 声明。",
        "lessons": [
            {
                "code": "python-basics-14-l01",
                "title": "局部变量、全局变量与 global",
                "description": "理解作用域的查找顺序，知道什么时候该用 global、为什么多数时候不该用。",
                "minutes": 45,
                "difficulty": "intermediate",
                "objectives": """1. 能区分局部变量与全局变量。
2. 能解释函数内读取全局变量可以、修改却要 global 的原因。
3. 能说出为什么应尽量少用 global。""",
                "why_learn": """变量看不见的地方就是 bug 藏身的地方：函数里改了同名变量，外面却没变。
搞清作用域，才能判断一个变量到底在哪一层生效，也才能读懂别人写的函数。""",
                "concepts": """- **作用域**：变量能被访问的范围。
- **局部变量**：在函数内部定义，只在函数内有效。
- **全局变量**：在模块顶层定义，整个文件都能读。
- **global 声明**：在函数内声明要修改全局变量。
- **查找顺序**：先用局部，找不到再用全局。""",
                "plain": """作用域像房间：局部变量是房间里的东西，出了房间就看不见；
全局变量放在客厅，谁都能看见。
你在房间里放一个也叫「水杯」的杯子，并不会换掉客厅那个——
除非你明确说「我要动客厅那个」，这就是 global 的作用。""",
                "syntax": """count = 10            全局变量

def show():
    count = 5         局部变量，不影响外面
    print(count)      输出 5

def change():
    global count      声明要改全局的那个
    count = 20

show()
print(count)          仍是 10
change()
print(count)          变成 20""",
                "example_code": '''count = 10

def show_local():
    count = 5
    print("函数内：", count)

show_local()
print("函数外：", count)

def read_global():
    print("读取全局：", count)

read_global()

def change_global():
    global count
    count = 20
    print("修改后函数内：", count)

change_global()
print("修改后函数外：", count)''',
                "code_lines": """- 第 1 行：在模块顶层定义全局变量 count，值为 10。
- 第 3 至 5 行：函数内重新定义同名变量，它是局部变量，与全局的互不影响。
- 第 7 至 8 行：调用后函数外仍是 10，证明局部修改没影响全局。
- 第 10 至 11 行：函数内读取全局变量不需要声明，直接就能读。
- 第 13 至 17 行：用 global 声明后赋值，改的是全局那个，所以函数外也变成 20。""",
                "output": """函数内： 5
函数外： 10
读取全局： 10
修改后函数内： 20
修改后函数外： 20""",
                "mistakes": """1. 以为函数内赋值会改到全局变量。
2. 函数内先读后赋值同名变量，报 UnboundLocalError。
3. 到处用 global，导致数据被任意函数改动。
4. 把 global 写在赋值之后。
5. 变量名与内置函数重名，出现难以排查的问题。""",
                "error_analysis": """- 函数内直接 count = 5 只会创建局部变量，全局的 10 不变。
- 函数内先 print(count) 再 count = 1，会报 UnboundLocalError：Python 看到函数里有赋值，就把 count 当成局部变量，读取时它还没被赋值。
- 滥用 global 会让「谁改了数据」无法追踪，尽量用参数传入、用返回值传出。
- global 必须写在函数体开头、赋值之前，否则语法上不生效或报错。""",
                "beginner_practice": """定义全局变量 score = 60，写函数打印它；再写一个函数用 global 把它改成 90，最后输出 score。""",
                "advanced_practice": """分别写两个函数：一个用参数接收分数并返回加分后的结果，另一个用 global 直接修改全局分数。比较两种写法，说明哪种更安全。""",
                "quiz_note": """本节测验 6 题：2 题考局部与全局的区别，2 题读代码判断变量最终值，2 题写带 global 的函数并说明风险。""",
                "summary": """- 局部变量只在函数内有效，全局变量整个文件可读。
- 函数内读取全局变量不用声明，修改才需要 global。
- 函数内出现赋值语句，该名字就变成局部变量。
- 优先用参数与返回值传数据，少用 global。""",
                "next_lesson": """下一章讲模块和包：把函数分文件存放，按需导入使用。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-14-k01",
                        "legacy": "python-basics-05-03",
                        "name": "变量作用域",
                        "goal": "能区分局部与全局变量并预测其生效范围",
                        "minutes": 25,
                        "criteria": "能解释函数内赋值不影响全局，能说明 UnboundLocalError 的成因",
                    },
                    {
                        "code": "python-basics-14-k02",
                        "name": "global 声明与副作用",
                        "goal": "会在必要时用 global，并知道它的风险",
                        "minutes": 20,
                        "criteria": "能写出用 global 修改全局变量的函数，能说明为何应少用",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-14-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "局部与全局",
                        "description": "定义全局 score = 60，函数内定义同名变量 90 并输出，再输出函数外的 score。",
                        "answer": 'score = 60\n\ndef show():\n    score = 90\n    print("函数内：", score)\n\nshow()\nprint("函数外：", score)',
                        "explanation": "函数内的 score 是局部变量，不影响外面。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-14-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "用 global 修改",
                        "description": "用 global 把全局 score 从 60 改成 90，输出修改前后的值。",
                        "answer": 'score = 60\nprint(score)\n\ndef update():\n    global score\n    score = 90\n\nupdate()\nprint(score)',
                        "explanation": "声明 global 后赋值才会改到全局变量。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-14-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "在函数内部定义的变量，作用范围是？",
                        "options": [
                            ("A", "整个文件"),
                            ("B", "只在函数内部"),
                            ("C", "所有函数"),
                            ("D", "只在定义它的那一行"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "函数内定义的变量是局部变量，出了函数就不可访问。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-14-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "函数内读取全局变量需要先写 global 声明。",
                        "answer": {"value": False},
                        "explanation": "只读不需要声明，修改才需要 global。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-14-l01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''x = 1

def f():
    x = 2
    print(x)

f()
print(x)''',
                        "answer": {
                            "reference": "先输出 2，再输出 1。函数内的 x 是局部变量，没有影响全局的 x。",
                            "keywords": ["2", "1", "局部变量"],
                        },
                        "explanation": "同名不代表同一个变量，作用域不同就是两个变量。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-14-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": '''x = 1
def f():
    print(x)
    x = 2
f()
会发生什么？''',
                        "options": [
                            ("A", "输出 1"),
                            ("B", "输出 2"),
                            ("C", "报 UnboundLocalError"),
                            ("D", "输出 None"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "函数内有赋值，x 被视为局部变量，打印时还未赋值。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-14-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "定义全局变量 total = 0，写函数 add(n) 用 global 把 n 累加到 total 上。",
                        "answer": {
                            "reference": "total = 0\n\ndef add(n):\n    global total\n    total = total + n\n\nadd(5)\nprint(total)",
                            "keywords": ["global total", "total + n", "add"],
                        },
                        "explanation": "没有 global 时 total 会被当成局部变量，报 UnboundLocalError。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-14-l01-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "为什么不建议大量使用 global？更好的替代方式是什么？",
                        "answer": {
                            "reference": "因为任何函数都能改全局变量，数据流向难以追踪，排查 bug 困难，函数之间产生隐式依赖。更好的方式是把数据作为参数传入，把结果用 return 返回。",
                            "keywords": ["难以追踪", "隐式依赖", "参数", "return"],
                        },
                        "explanation": "能指出「数据流向不可控」这一核心问题即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ------------------------------------------------------------------ 第 15 章
    {
        "code": "python-basics-15",
        "order_index": 15,
        "title": "模块和包",
        "description": "把代码拆到文件里：import 标准库、写自己的模块、按包组织多个模块。",
        "lessons": [
            {
                "code": "python-basics-15-l01",
                "title": "import、自定义模块与包",
                "description": "导入标准库、创建自己的模块文件、理解包与 __init__.py。",
                "minutes": 55,
                "difficulty": "intermediate",
                "objectives": """1. 会用 import 与 from ... import 导入模块。
2. 会创建自己的模块文件并在另一个文件里使用。
3. 能说清模块与包的区别，知道包目录需要 __init__.py。""",
                "why_learn": """所有代码写在一个文件里，几百行后就无法维护。
模块让你按功能拆文件，包让你按目录分组；同时 Python 自带的标准库本身就是一堆模块，
学会导入才能用上现成的能力，而不是什么都自己写。""",
                "concepts": """- **模块**：一个 .py 文件就是一个模块。
- **包**：包含 __init__.py 的目录，里面可以放多个模块。
- **import 模块名**：导入整个模块，用 模块名.函数() 调用。
- **from 模块 import 名字**：只导入需要的函数或变量。
- **标准库**：Python 自带的模块，如 math、random、json。""",
                "plain": """模块像一个个工具箱，包像把这些工具箱分类放进抽屉。
import 是把整个工具箱搬到桌上，用的时候要说「工具箱名.工具名」；
from ... import 是只把某一件工具拿出来，直接就能用。
标准库则是 Python 出厂就配好的工具箱，不用自己造。""",
                "syntax": """import math                 导入整个模块
math.sqrt(16)               使用，得到 4.0

from math import sqrt       只导入一个函数
sqrt(16)                    直接用

import random
random.randint(1, 10)       随机整数

from 自己的模块 import 函数名""",
                "example_code": '''import math
import random

print("圆周率：", math.pi)
print("开方：", math.sqrt(16))
print("向上取整：", math.ceil(3.2))

print("随机数：", random.randint(1, 6))

from math import floor

print("向下取整：", floor(3.9))

# 假设同目录下有一个 tools.py，内容为：
# def double(n):
#     return n * 2
# 则可以这样使用：
# from tools import double
# print(double(5))''',
                "code_lines": """- 第 1 至 2 行：导入 math 与 random 两个标准库模块。
- 第 4 至 6 行：通过 模块名.函数名 的方式使用，math.pi 是模块里的常量。
- 第 8 行：random.randint(1, 6) 生成 1 到 6 之间的随机整数，包含两端。
- 第 10 至 12 行：from ... import 只导入 floor，之后可以直接写 floor(...)。
- 第 14 至 18 行：注释展示了自定义模块的用法，把函数写在 tools.py 里，另一个文件导入即可。""",
                "output": """圆周率： 3.141592653589793
开方： 4.0
向上取整： 4
随机数： 3
向下取整： 3""",
                "mistakes": """1. 导入后忘记写模块名前缀，直接调 sqrt(16) 报 NameError。
2. 模块名与变量名冲突，把 math 赋成别的值。
3. 自定义模块文件名与标准库重名（如 json.py），导致导入错乱。
4. 包目录缺少 __init__.py，导入失败。
5. 用 from 模块 import * 导入过多名字，造成覆盖。""",
                "error_analysis": """- import math 后直接写 sqrt(16) 报 NameError，因为名字还在 math 里，要写 math.sqrt(16)。
- 把自己的文件命名为 random.py，再 import random 会导入你自己这个空文件，调用 randint 报 AttributeError。
- 传统包结构需要 __init__.py 标识这是一个包，缺少它时 Python 可能不认为这是可导入的包。
- from math import * 会把大量名字倒进当前命名空间，容易覆盖你自己定义的同名变量。""",
                "beginner_practice": """导入 math，输出 2 的平方根和 10 的对数（可用 math.log10）。""",
                "advanced_practice": """新建 tools.py 写入 add 与 double 两个函数，再新建 main.py 导入并使用它们，输出结果。""",
                "quiz_note": """本节测验 6 题：2 题考模块与包的概念，2 题读代码判断导入方式的对错，2 题写自定义模块并在另一文件中使用。""",
                "summary": """- 一个 .py 文件就是一个模块，含 __init__.py 的目录是包。
- import 模块用 模块名.名字 访问，from 导入可直接使用。
- 标准库自带大量能力，先查再写。
- 自定义模块不要与标准库重名。""",
                "next_lesson": """下一章学文件读写：把程序的数据保存到磁盘，下次运行还能读回来。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-15-k01",
                        "legacy": "python-basics-05-04",
                        "name": "模块与 import",
                        "goal": "会用 import 与 from ... import 使用标准库",
                        "minutes": 30,
                        "criteria": "能正确写出两种导入方式并调用，能解释 NameError 的原因",
                    },
                    {
                        "code": "python-basics-15-k02",
                        "name": "自定义模块与包",
                        "goal": "会拆分自己的模块文件并按包组织",
                        "minutes": 25,
                        "criteria": "能创建模块文件并在另一文件导入，能说明包需要 __init__.py",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-15-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "用 math 计算",
                        "description": "导入 math，输出 2 的平方根与 100 的对数（math.log10）。",
                        "answer": "import math\nprint(math.sqrt(2))\nprint(math.log10(100))",
                        "explanation": "导入整个模块后用模块名调用。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-15-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "拆分工具函数",
                        "description": "在 tools.py 写 add 与 double，在 main.py 导入并输出 add(2,3) 与 double(4)。",
                        "answer": "# tools.py\ndef add(a, b):\n    return a + b\n\ndef double(n):\n    return n * 2\n\n# main.py\nfrom tools import add, double\nprint(add(2, 3))\nprint(double(4))",
                        "explanation": "两个文件放在同一目录，导入时不需要写 .py。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-15-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "import math 之后，计算平方根的正确写法是？",
                        "options": [
                            ("A", "sqrt(16)"),
                            ("B", "math.sqrt(16)"),
                            ("C", "math->sqrt(16)"),
                            ("D", "import.sqrt(16)"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "导入整个模块后要用模块名前缀。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-15-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "一个包含多个 .py 文件的目录，只要有 __init__.py 就可以作为包导入。",
                        "answer": {"value": True},
                        "explanation": "__init__.py 用来标识这是一个包。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-15-l01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''import math
print(math.sqrt(9))
print(math.ceil(1.1))''',
                        "answer": {
                            "reference": "输出 3.0 和 2。sqrt 返回浮点数，ceil 向上取整。",
                            "keywords": ["3.0", "2", "sqrt", "ceil"],
                        },
                        "explanation": "注意 sqrt 的结果是浮点数，即使能整除。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-15-l01-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": '''from math import sqrt
print(sqrt(16))
输出是？''',
                        "options": [
                            ("A", "4.0"),
                            ("B", "报 NameError"),
                            ("C", "16"),
                            ("D", "报 ImportError"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "from 导入后可以直接使用名字，不需要模块前缀。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-15-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "写一个 tools.py 里的函数 triple(n) 返回三倍值，并写出在另一个文件中导入调用的两行代码。",
                        "answer": {
                            "reference": "# tools.py\ndef triple(n):\n    return n * 3\n\n# main.py\nfrom tools import triple\nprint(triple(4))",
                            "keywords": ["def triple", "from tools import", "print"],
                        },
                        "explanation": "自定义模块就是普通 .py 文件，导入方式与标准库一致。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-15-l01-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "为什么不能把自己的文件命名成 random.py 或 json.py？",
                        "answer": {
                            "reference": "因为 Python 导入时会优先找到当前目录下的同名文件，你自己的 random.py 会覆盖标准库的 random，导致 import random 后无法使用 randint 等函数。应避免与标准库重名。",
                            "keywords": ["同名", "覆盖", "标准库", "导入顺序"],
                        },
                        "explanation": "能指出「同名文件抢先被导入」即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ------------------------------------------------------------------ 第 16 章
    {
        "code": "python-basics-16",
        "order_index": 16,
        "title": "文件读写",
        "description": "让数据活过这一次运行：打开、读取、写入、追加，以及必须养成的 with 习惯。",
        "lessons": [
            {
                "code": "python-basics-16-l01",
                "title": "打开与读取文件",
                "description": "用 open 打开文件、用 with 自动关闭、用 read/readlines 读取内容。",
                "minutes": 55,
                "difficulty": "beginner",
                "objectives": """1. 会用 open 打开文件并指定编码。
2. 会用 with 语句保证文件被正确关闭。
3. 会用 read()、readlines() 读取全部或逐行内容。""",
                "why_learn": """程序里的变量一关就没了，配置、日志、数据都需要存到磁盘。
读文件是所有数据处理的第一步：读配置、读名单、读日志都从这里开始。""",
                "concepts": """- **文件路径**：文件在磁盘上的位置，同目录可直接写文件名。
- **编码**：文本保存的规则，中文建议统一用 utf-8。
- **open(文件名, 模式, encoding)**：打开文件，返回文件对象。
- **with 语句**：离开代码块时自动关闭文件，避免忘记 close。
- **read / readlines**：一次读全部 / 按行读成列表。""",
                "plain": """打开文件像借书：借了要还，不还别人就用不了。
with 语句相当于「自动还书」的托管服务，代码块结束时一定帮你关掉。
编码则像约定用哪种语言记录，读写两端约定不一致，中文就会变成乱码。""",
                "syntax": """with open("notes.txt", "r", encoding="utf-8") as f:
    content = f.read()        一次读全部内容

with open("notes.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()     读成列表，每行一个元素

模式：r 读、w 覆盖写、a 追加""",
                "example_code": '''# 先准备一个文件用于演示
with open("demo.txt", "w", encoding="utf-8") as f:
    f.write("第一行\\n")
    f.write("第二行\\n")
    f.write("第三行\\n")

with open("demo.txt", "r", encoding="utf-8") as f:
    content = f.read()
print("全部内容：")
print(content)

with open("demo.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
print("行数：", len(lines))
print("第一行：", lines[0].strip())''',
                "code_lines": """- 第 2 至 5 行：用 w 模式创建文件并写入三行，\\n 表示换行。
- 第 7 至 9 行：用 r 模式读取全部内容，read() 把整个文件读成一个字符串。
- 第 11 至 14 行：readlines() 把每一行作为列表的一个元素，行末自带换行符，所以用 strip() 去掉。
- 两个 with 块结束后文件都已自动关闭，不需要手动 close。""",
                "output": """全部内容：
第一行
第二行
第三行

行数： 3
第一行： 第一行""",
                "mistakes": """1. 忘记指定 encoding，中文在部分系统上出现乱码。
2. 不用 with 也不 close，文件被占用。
3. 用 r 模式打开不存在的文件，报 FileNotFoundError。
4. 以为 readlines 会自动去掉行末换行符。
5. 路径写错，尤其是 Windows 的反斜杠。""",
                "error_analysis": """- 未指定 encoding 时使用系统默认编码，读写两端不一致就会乱码（UnicodeDecodeError 或显示为问号）。
- 不关闭文件可能导致内容没有真正写入磁盘，其他程序也无法访问。
- r 模式要求文件已存在，不存在报 FileNotFoundError: No such file or directory。
- readlines 保留每行末尾的 \\n，比较内容前要 strip。
- Windows 路径中的反斜杠是转义符，应写原始字符串 r"C:\\data\\a.txt" 或改用正斜杠。""",
                "beginner_practice": """创建一个文本文件写入两行内容，再读出来统计行数与字符数。""",
                "advanced_practice": """把一个含三行内容的文件读成列表，输出去掉换行后的每一行（不要求用循环，可逐行打印）。""",
                "quiz_note": """本节测验 6 题：2 题考 with 与编码的作用，2 题读代码判断输出或异常，2 题写创建并读取文件的程序。""",
                "summary": """- open 需要文件名、模式与编码三个要素。
- with 会在代码块结束时自动关闭文件，是标准写法。
- read 读全部，readlines 按行读成列表。
- 中文文件统一用 utf-8，避免乱码。""",
                "next_lesson": """下一课学写入与追加，把程序运行结果保存下来。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-16-k01",
                        "name": "打开与读取文件",
                        "goal": "会用 open 与 read/readlines 读取文本文件",
                        "minutes": 30,
                        "criteria": "能写出带 encoding 的读取代码，能处理 FileNotFoundError",
                    },
                    {
                        "code": "python-basics-16-k02",
                        "name": "with 语句与资源关闭",
                        "goal": "养成用 with 管理文件句柄的习惯",
                        "minutes": 25,
                        "criteria": "能说明 with 的作用，能解释不关闭文件的风险",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-16-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "写入并读取",
                        "description": "创建 note.txt 写入两行，再读出来输出行数与内容。",
                        "answer": 'with open("note.txt", "w", encoding="utf-8") as f:\n    f.write("第一行\\n第二行\\n")\n\nwith open("note.txt", "r", encoding="utf-8") as f:\n    lines = f.readlines()\nprint(len(lines))\nprint(lines[0].strip())',
                        "explanation": "写入用 w，读取用 r，中文统一 utf-8。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-16-k02-ex2",
                        "kp": 1,
                        "type": "choice",
                        "title": "with 的作用",
                        "description": "说明 with open(...) as f 相比手动 open/close 的优势。",
                        "answer": "即使代码块内发生异常，with 也会自动关闭文件，避免句柄泄漏和内容未落盘。",
                        "explanation": "with 是上下文管理器，负责进入与退出时的资源处理。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-16-l01-1",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "使用 with open(...) as f 的最大好处是？",
                        "options": [
                            ("A", "读写速度更快"),
                            ("B", "离开代码块时自动关闭文件"),
                            ("C", "自动创建目录"),
                            ("D", "自动处理编码"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "with 保证文件在代码块结束时被关闭，即使发生异常。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-16-l01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "用 r 模式打开一个不存在的文件，会创建它。",
                        "answer": {"value": False},
                        "explanation": "r 模式要求文件已存在，不存在会报 FileNotFoundError；w 模式才会创建。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-16-l01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''文件内容为两行：A 和 B
with open("t.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
print(len(lines))''',
                        "answer": {
                            "reference": "输出 2。readlines 按行读取，两行内容对应列表两个元素。",
                            "keywords": ["2", "readlines", "两行"],
                        },
                        "explanation": "行数等于列表长度。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-16-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "readlines() 返回的每个元素末尾通常包含什么？",
                        "options": [
                            ("A", "空格"),
                            ("B", "换行符"),
                            ("C", "逗号"),
                            ("D", "什么都没有"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "每行保留行末换行符，比较或输出前常用 strip 去掉。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-16-l01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写代码创建 data.txt 写入「Python」和「文件」两行，再读取并输出行数。",
                        "answer": {
                            "reference": 'with open("data.txt", "w", encoding="utf-8") as f:\n    f.write("Python\\n文件\\n")\n\nwith open("data.txt", "r", encoding="utf-8") as f:\n    print(len(f.readlines()))',
                            "keywords": ["open", "utf-8", "readlines", "w"],
                        },
                        "explanation": "先写后读，两个 with 块分别负责。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-16-l01-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "为什么读取中文文件时建议显式写 encoding=\"utf-8\"？",
                        "answer": {
                            "reference": "因为不同系统默认编码不同（如 Windows 可能是 GBK），不指定时按系统默认解码，遇到 utf-8 保存的中文就会乱码或抛 UnicodeDecodeError。显式指定可保证读写一致。",
                            "keywords": ["默认编码", "乱码", "UnicodeDecodeError", "一致"],
                        },
                        "explanation": "能指出「读写两端编码必须一致」即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-basics-16-l02",
                "title": "写入、追加与按行处理",
                "description": "用 w 覆盖、用 a 追加，按行处理文件内容并统计。",
                "minutes": 55,
                "difficulty": "beginner",
                "objectives": """1. 能区分 w 与 a 两种写入模式。
2. 会用 write 写入字符串、用 writelines 写入多行。
3. 能读取文件后按行做过滤与统计。""",
                "why_learn": """日志要不断追加而不是每次覆盖，导出结果要一次写多行，
统计任务要逐行判断。这些都需要区分写入模式并按行处理。""",
                "concepts": """- **w 模式**：覆盖写入，文件原有内容会被清空。
- **a 模式**：追加写入，新内容加在末尾。
- **write**：写入一个字符串，不会自动换行。
- **writelines**：写入一组字符串。
- **按行处理**：读成列表后逐个判断、统计。""",
                "plain": """w 像把笔记本撕掉重新写，a 像在笔记本后面接着写。
很多人第一次用 w 时把重要内容清空了，就是因为没意识到它是「覆盖」而不是「接着写」。
write 不会自动换行，想换行要自己写 \\n，这是新手最常见的格式问题。""",
                "syntax": """with open("log.txt", "w", encoding="utf-8") as f:
    f.write("第一行\\n")          覆盖写入

with open("log.txt", "a", encoding="utf-8") as f:
    f.write("新的一行\\n")        追加到末尾

with open("log.txt", "w", encoding="utf-8") as f:
    f.writelines(["a\\n", "b\\n"])""",
                "example_code": '''with open("log.txt", "w", encoding="utf-8") as f:
    f.write("启动程序\\n")
    f.write("连接数据库\\n")

with open("log.txt", "a", encoding="utf-8") as f:
    f.write("用户登录\\n")

with open("log.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("总行数：", len(lines))

error_count = 0
for line in lines:
    if "数据库" in line:
        error_count = error_count + 1
print("含数据库的行数：", error_count)

for line in lines:
    print(line.strip())''',
                "code_lines": """- 第 1 至 3 行：w 模式创建文件并写入两行，覆盖原有内容。
- 第 5 至 6 行：a 模式在末尾追加一行，原有两行保留。
- 第 8 至 9 行：读回全部行，共三行。
- 第 11 至 15 行：逐行判断是否包含关键词，统计出现次数。
- 第 17 至 18 行：逐行输出，strip 去掉行末换行，避免出现空行。""",
                "output": """总行数： 3
含数据库的行数： 1
启动程序
连接数据库
用户登录""",
                "mistakes": """1. 想追加却用了 w，把原内容清空。
2. write 不加 \\n，所有内容挤在一行。
3. 用 writelines 传入一个字符串，结果被逐字符写入。
4. 读文件后不 strip 就判断相等，因换行符导致判断失败。
5. 同一个文件同时被两个 with 打开写入。""",
                "error_analysis": """- 用 w 打开已有文件会立刻清空内容，这是最常见的「数据丢了」原因；要保留请用 a。
- write 不会自动换行，多次 write 会连成一行，需要显式加 \\n。
- writelines 接收的是字符串序列，传单个字符串会按字符拆开写入。
- 读取的行带 \\n，判断 line == "数据库" 会失败，应写 line.strip() == "数据库"。
- 同一文件同时打开多个写入句柄，写入顺序不可控，可能互相覆盖。""",
                "beginner_practice": """创建日志文件写入两行，再用追加模式加一行，最后读出来输出全部内容。""",
                "advanced_practice": """读入一个含多行数字的文件，统计其中大于 60 的行数，并把结果追加到文件末尾。""",
                "quiz_note": """本节测验 6 题：2 题考 w 与 a 的区别、write 的换行行为，2 题读代码判断文件最终内容，2 题写追加与统计程序。""",
                "summary": """- w 覆盖、a 追加，选错会丢数据。
- write 不自动换行，需要手动加 \\n。
- writelines 接收字符串序列。
- 读取后先 strip 再判断内容。""",
                "next_lesson": """下一章讲 JSON：一种把字典和列表存成文件的通用格式。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-16-k03",
                        "name": "写入与追加模式",
                        "goal": "能区分 w 与 a 并正确写入文本",
                        "minutes": 30,
                        "criteria": "能预测两种模式下文件最终内容，能解释 write 不加换行的后果",
                    },
                    {
                        "code": "python-basics-16-k04",
                        "name": "按行处理与统计",
                        "goal": "会读取文件后逐行过滤与统计",
                        "minutes": 25,
                        "criteria": "能写出带 strip 的逐行判断，能统计满足条件的行数",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-16-k03-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "写入并追加",
                        "description": "先写入两行，再追加一行，读回后输出总行数。",
                        "answer": 'with open("log.txt", "w", encoding="utf-8") as f:\n    f.write("A\\nB\\n")\nwith open("log.txt", "a", encoding="utf-8") as f:\n    f.write("C\\n")\nwith open("log.txt", "r", encoding="utf-8") as f:\n    print(len(f.readlines()))',
                        "explanation": "w 建立文件，a 追加，最终三行。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-16-k04-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "统计及格行",
                        "description": "读取含多行数字的文件，统计大于等于 60 的行数。",
                        "answer": 'with open("scores.txt", "r", encoding="utf-8") as f:\n    lines = f.readlines()\n\ncount = 0\nfor line in lines:\n    if int(line.strip()) >= 60:\n        count = count + 1\nprint(count)',
                        "explanation": "先 strip 去掉换行，再转 int 比较。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-16-l02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "用 w 模式打开一个已有内容的文件，会发生什么？",
                        "options": [
                            ("A", "在末尾追加内容"),
                            ("B", "原内容被清空"),
                            ("C", "报错"),
                            ("D", "内容被备份"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "w 是覆盖写入，打开时就会清空。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-16-l02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "write 方法会自动在内容末尾加换行符。",
                        "answer": {"value": False},
                        "explanation": "write 不会自动换行，需要自己写 \\n。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-16-l02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''with open("t.txt", "w", encoding="utf-8") as f:
    f.write("A")
    f.write("B")
文件内容是什么？''',
                        "answer": {
                            "reference": "内容是一行 AB。write 不会自动换行，两次写入连在一起。",
                            "keywords": ["AB", "一行", "不换行"],
                        },
                        "explanation": "需要分两行必须写 \\n。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-16-l02-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": '''从文件读到 line 为 "60\\n"，判断它是否等于 60 的正确写法是？''',
                        "options": [
                            ("A", "line == 60"),
                            ("B", "line.strip() == \"60\""),
                            ("C", "line == \"60\""),
                            ("D", "int(line) == \"60\""),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "读到的行带换行符，先 strip 再比较。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-16-l02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写代码：向 log.txt 追加一行「任务完成」。",
                        "answer": {
                            "reference": 'with open("log.txt", "a", encoding="utf-8") as f:\n    f.write("任务完成\\n")',
                            "keywords": ["open", '"a"', "write", "任务完成"],
                        },
                        "explanation": "追加必须用 a 模式，否则会清空原有日志。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-16-l02-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "统计文件行数时，为什么不能直接比较 line == \"错误\"？",
                        "answer": {
                            "reference": "因为 readlines 读到的每一行末尾带换行符，实际是 \"错误\\n\"，直接比较会不相等。应先用 strip 去掉首尾空白再比较。",
                            "keywords": ["换行符", "strip", "不相等"],
                        },
                        "explanation": "能指出行末 \\n 的影响即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
