"""第 1—2 章教材内容：环境入门、变量与类型。

写作约定：
- 正文里的引号统一用「」，避免与 Python 字符串定界符冲突；
- 代码块统一放在三引号字符串里，内部可以正常使用英文双引号；
- 本文件只存「教什么」，写库逻辑在 app.seed.textbook_seed。
"""

CHAPTERS: list[dict] = [
    # ------------------------------------------------------------------ 第 1 章
    {
        "code": "python-basics-01",
        "order_index": 1,
        "title": "编程入门与 Python 环境",
        "description": "从「程序是什么」讲到亲手跑出第一行输出，把环境、语句与运行结果这三个最容易劝退新手的地方一次讲透。",
        "lessons": [
            {
                "code": "python-basics-01-l01",
                "title": "第一段 Python 代码：认识编程与环境",
                "description": "理解程序与语句，完成环境验证，跑出两行真实输出。",
                "minutes": 45,
                "difficulty": "beginner",
                "objectives": """1. 能用自己的话说清楚「程序」和「语句」分别是什么。
2. 能在自己的电脑上启动 Python，并运行一个 .py 文件。
3. 能区分「代码」和「运行结果」，知道结果不是手写在代码里的。""",
                "why_learn": """学编程的第一道坎从来不是语法，而是「我写的字为什么能变成屏幕上的结果」。
把环境跑通、把第一段代码跑出结果，你就有了一个可以随时验证想法的实验台。
后面每一节课的示例，都要在这个实验台上亲手跑一遍，否则看懂不等于会写。""",
                "concepts": """- **程序**：一组按顺序执行的指令，计算机照着做，不会自己发挥。
- **语句**：程序里的一行指令，例如 print 那一行就是一条语句。
- **解释器**：真正读懂并执行 Python 代码的程序，你写的 .py 文件由它逐行翻译执行。
- **输出**：程序运行后显示在屏幕上的文字，它是执行的结果，不是代码的一部分。""",
                "plain": """把程序想成一张写给厨房的步骤单：先洗菜、再切菜、最后下锅。
厨师不读字面背后的感情，只按步骤执行；步骤写错，菜就做错。
Python 解释器就是那位厨师，print 就是「把这份东西端出去给客人看」的动作。
所以代码是给厨师看的步骤单，输出是端上桌的菜，两者长得完全不一样。""",
                "syntax": """输出一条信息的基本写法：

print("要显示的内容")

三个必须记住的细节：
- print 全是小写，后面紧跟一对英文圆括号；
- 文字要用英文引号包起来，单引号和双引号都可以；
- 括号里也可以直接写算式，例如 print(3 + 4)，Python 会先算出结果再输出。""",
                "example_code": '''print("Python 已经可以运行了")
print(3 + 4)
print("3 + 4")''',
                "code_lines": """- 第 1 行：把引号里的文字原样输出。
- 第 2 行：括号里没有引号，Python 先做加法得到 7，再输出 7。
- 第 3 行：有引号，Python 认为这是一段文字，原样输出 3 + 4，不做计算。""",
                "output": """Python 已经可以运行了
7
3 + 4""",
                "mistakes": """1. 用了中文引号，中文引号不是代码符号。
2. 把函数名写成大写 Print。
3. 漏掉右括号。
4. 以为 print("3 + 4") 会算出 7——加了引号就是纯文字。""",
                "error_analysis": """- 中文引号会报 SyntaxError: invalid character。Python 明确指出这个字符不合法，因为解释器只认英文符号；把输入法切到英文再敲引号即可。
- Print 大写会报 NameError: name 'Print' is not defined。Python 区分大小写，Print 和 print 是两个不同的名字。
- 漏右括号会报 SyntaxError，提示有左括号没有配对。""",
                "beginner_practice": """在编辑器里新建 hello.py，让它输出两行：
第一行是你的名字，第二行是「我在学习 Python」。运行并确认屏幕上正好两行。""",
                "advanced_practice": """不用计算器，用 print 分别输出 25 * 4 的结果和 25 * 4 这段文字本身，观察两次输出的差别，并解释原因。""",
                "quiz_note": """本节测验 6 题：2 题考概念（程序、语句、输出），2 题读代码判断输出，2 题动手写输出语句。全部围绕 print 与「有无引号」这一个核心区别。""",
                "summary": """- 程序是按顺序执行的语句集合，解释器负责执行。
- print(...) 是输出语句，括号里写什么就输出什么。
- 有引号等于原样输出文字；无引号等于先算再输出。
- 代码和输出是两件事，输出永远由运行产生。""",
                "next_lesson": """下一课让程序既会说话也会听话：用 input() 接收键盘输入，并学会用注释给代码写说明。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-01-k01",
                        "legacy": "python-basics-01-01",
                        "name": "什么是编程与 Python",
                        "goal": "能说清程序、语句、解释器三者的关系",
                        "minutes": 20,
                        "criteria": "能用自己的话解释程序是什么，并指出解释器的作用",
                    },
                    {
                        "code": "python-basics-01-k02",
                        "legacy": "python-basics-01-02",
                        "name": "安装与运行 Python",
                        "goal": "独立启动 Python 并运行一个 .py 文件",
                        "minutes": 25,
                        "criteria": "能新建 .py 文件、运行并看到输出，能读懂最基本的报错行号",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-01-k01-ex1",
                        "kp": 0,
                        "type": "short_answer",
                        "title": "用生活例子解释程序",
                        "description": "用一个生活里的例子说明「程序」是什么，并指出其中哪部分是「语句」。",
                        "answer": "例如：程序像一份泡面步骤单，烧水、放面、等三分钟、加调料，每一步就是一条语句，按顺序执行才能得到一碗面。",
                        "explanation": "能把「有序步骤」和「单条指令」分开说清即达标，例子不限。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-01-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "让环境跑起来",
                        "description": "新建 hello.py，输出三行内容：第一行 Python，第二行 版本验证通过，第三行 1 + 1 = 2。",
                        "answer": 'print("Python")\nprint("版本验证通过")\nprint("1 + 1 =", 1 + 1)',
                        "explanation": "第三行用逗号把文字和算式分开，Python 会先算 1+1 再一起输出。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-01-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "下列关于「程序」的说法，正确的是？",
                        "options": [
                            ("A", "程序就是运行结果"),
                            ("B", "程序是一组按顺序执行的指令"),
                            ("C", "程序必须一次写对，不能修改"),
                            ("D", "只有 Python 才有程序"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "程序是按顺序执行的指令集合；运行结果是执行后的产物，且程序可以反复修改重跑。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-01-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "Python 解释器的作用是把你写的 .py 文件逐行翻译并执行。",
                        "answer": {"value": True},
                        "explanation": "解释器负责读懂并执行代码，没有它 .py 文件只是一段普通文本。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-01-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''下面三行代码运行后，屏幕上会显示几行内容？分别是什么？
print("A")
print(3 + 4)
print("3 + 4")''',
                        "answer": {
                            "reference": "显示三行：A、7、3 + 4。第二行没有引号所以先计算，第三行有引号所以原样输出。",
                            "keywords": ["三行", "7", "3 + 4", "引号"],
                        },
                        "explanation": "关键判断点是有没有引号：无引号做运算，有引号当文字。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-01-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": '''运行 print("2 + 3") 后，输出是？''',
                        "options": [
                            ("A", "5"),
                            ("B", "2 + 3"),
                            ("C", "2+3=5"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "引号内的内容是纯文本，Python 不会执行其中的加法。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-01-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "写两行代码：第一行输出你的名字，第二行输出 12 * 8 的计算结果。",
                        "answer": {
                            "reference": 'print("小明")\nprint(12 * 8)',
                            "keywords": ["print", "12 * 8", "96"],
                        },
                        "explanation": "第二行不能加引号，否则输出的会是文字而不是 96。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-01-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说「代码不是输出」？请结合 print 里带引号的算式说明。",
                        "answer": {
                            "reference": "代码是写给解释器的指令，输出是执行结果显示在屏幕上的内容。代码里带引号的 3 + 4 被当作文字输出，说明输出由运行产生，并不等于源代码本身。",
                            "keywords": ["指令", "执行", "引号", "屏幕"],
                        },
                        "explanation": "能指出代码与输出的差别，并举出引号把算式变成文字的例子即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-basics-01-l02",
                "title": "让程序说话与听话：输出、输入与注释",
                "description": "用 print 组织多段输出，用 input 接收键盘输入，用注释给代码留下说明。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 会用一条 print 输出多个值，并知道它们之间用逗号分隔。
2. 会用 input() 接收用户输入，并让程序对输入做出回应。
3. 会写单行注释，知道注释不参与运行。""",
                "why_learn": """只会输出，程序只是一个公告板；能接收输入，程序才开始会对话。
几乎所有实用程序都在做同一件事：拿到输入、处理、给出结果。
本节先把「拿到输入」和「给出结果」这两端打通，中间的处理逻辑从第 2 章开始补。""",
                "concepts": """- **输出**：print 把内容显示到屏幕上。
- **输入**：input(提示语) 暂停程序，等用户敲回车，把用户敲的内容交回来。
- **注释**：以 # 开头的文字，只给人看，Python 完全忽略。""",
                "plain": """input 就像服务员递过来的点菜单：程序先问一句「你要什么」，停在那里等你写，
你写完（敲键盘再回车），服务员把单子收走交给后厨，程序才继续往下走。
注释则像贴在冰箱上的便利贴，只有人看，机器不读。""",
                "syntax": """print("第一段", "第二段")      逗号分隔，输出时自动加空格
name = input("请输入名字：")   提示语显示后等待输入
print("你好，", name)

# 这是单行注释，不会被执行""",
                "example_code": '''# 先打招呼
print("你好，我是小码")

# 等待用户输入，把内容存进 name
name = input("请输入你的名字：")

# 用输入的内容回应
print("很高兴认识你，", name)
print("今天我们一起学 Python")''',
                "code_lines": """- 第 1 行：注释，以 # 开头，只说明下面要做什么，不产生任何输出。
- 第 2 行：输出问候语。
- 第 5 行：input 先在屏幕上显示提示语，然后停住等输入；用户敲完回车，内容被存进 name。变量的细节第 2 章讲，这里先理解为「给内容贴个标签」。
- 第 8 行：用逗号连接固定文字和变量，输出时两者之间自动有一个空格。
- 第 9 行：再输出一行固定文字。""",
                "output": """你好，我是小码
请输入你的名字：小明
很高兴认识你， 小明
今天我们一起学 Python""",
                "mistakes": """1. 忘记给 input() 的结果起名字，内容拿到就丢了。
2. 用加号连接文字和变量时不加空格，结果会挤在一起；变量不是字符串时还会报错。
3. 把注释写成中文全角符号，Python 不认。
4. 以为注释会被输出。""",
                "error_analysis": """- input 的返回值是字符串。用户输入 18，拿到的是文字 18 而不是数字 18，做加法会得到 181 这种结果。要当数字用，需要第 2 章的类型转换。
- 注释符号必须是英文井号。全角符号会被当成普通字符，导致 SyntaxError。
- 用加号拼接文字和数字会报 TypeError，因为加号不能把文字和数字直接拼起来。""",
                "beginner_practice": """写一个程序：先输出「我是小码」，再用 input 询问用户所在城市，最后输出「欢迎来自 XX 的同学」。""",
                "advanced_practice": """写一个程序：分别用 input 询问用户的姓和名，然后用一条 print 把姓和名连起来输出，并在前面加一句「你的全名是：」。""",
                "quiz_note": """本节测验 6 题：2 题考 input 的返回值与注释作用，2 题读代码判断输出，2 题写带输入输出的完整小程序。""",
                "summary": """- print 可以用逗号一次输出多个值，逗号处会自动加空格。
- input(提示语) 会暂停程序等待输入，返回值一定是字符串。
- 井号之后到行尾是注释，不参与运行。
- 一个最小的交互程序等于输入加处理加输出。""",
                "next_lesson": """程序要处理数据，就得先有地方存数据。下一章讲变量：怎么给数据起名字、怎么保存和修改它。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-01-k03",
                        "legacy": "python-basics-01-03",
                        "name": "第一个程序：print 输出",
                        "goal": "能用 print 输出文字、算式与多个值",
                        "minutes": 15,
                        "criteria": "能正确使用逗号输出多个值，并解释有无引号的区别",
                    },
                    {
                        "code": "python-basics-01-k04",
                        "legacy": "python-basics-01-04",
                        "name": "注释与代码规范",
                        "goal": "会用注释说明代码意图，遵守基本书写规范",
                        "minutes": 15,
                        "criteria": "能写出不与代码矛盾的单行注释，知道注释符号必须是英文",
                    },
                    {
                        "code": "python-basics-01-k05",
                        "legacy": "python-basics-01-05",
                        "name": "输入 input() 与用户交互",
                        "goal": "会用 input 接收输入并让程序做出回应",
                        "minutes": 20,
                        "criteria": "能写出提示、输入、回应三行程序，并知道返回值是字符串",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-01-k03-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "一条 print 输出三个值",
                        "description": "用一条 print 输出姓名、年龄、城市三个值，中间用逗号分隔。",
                        "answer": 'print("小明", 18, "杭州")',
                        "explanation": "逗号分隔的多个值会依次输出，中间自动补一个空格。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-01-k05-ex2",
                        "kp": 2,
                        "type": "coding",
                        "title": "城市问候程序",
                        "description": "询问用户所在城市，然后输出「欢迎来自 XX 的同学」。",
                        "answer": 'city = input("你来自哪个城市？")\nprint("欢迎来自", city, "的同学")',
                        "explanation": "input 的提示语写在括号里，返回值用变量接住后再输出。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-01-l02-1",
                        "kp": 2,
                        "type": "single_choice",
                        "stem": "input 的返回值是什么类型？",
                        "options": [
                            ("A", "整数"),
                            ("B", "浮点数"),
                            ("C", "字符串"),
                            ("D", "布尔值"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "无论用户输入什么，input 都按字符串返回，需要数字时得自己转换。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-01-l02-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "注释会被 Python 执行，只是不显示在屏幕上。",
                        "answer": {"value": False},
                        "explanation": "注释在运行前就被跳过，完全不参与执行。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-01-l02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''用户输入 小明，下面程序输出什么？
name = input("名字：")
print("你好，", name)''',
                        "answer": {
                            "reference": "输出「你好， 小明」。提示语不会出现在最终输出里，逗号处有空格。",
                            "keywords": ["你好", "小明", "空格"],
                        },
                        "explanation": "input 的提示语只在等待输入时显示，print 的逗号会自动补空格。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-01-l02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "print(1, 2, 3) 的输出是？",
                        "options": [
                            ("A", "123"),
                            ("B", "1 2 3"),
                            ("C", "1,2,3"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "逗号分隔多个值，输出时每个值之间自动加一个空格。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-01-l02-5",
                        "kp": 2,
                        "type": "code_writing",
                        "stem": "写一个程序：询问用户的名字，然后输出「你好，XXX，欢迎学习 Python」。",
                        "answer": {
                            "reference": 'name = input("请输入名字：")\nprint("你好，", name, "，欢迎学习 Python")',
                            "keywords": ["input", "name", "print"],
                        },
                        "explanation": "先用变量接住输入，再用逗号拼接固定文字和变量。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-01-l02-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "什么情况下应该写注释？写出两条你自己会写注释的场景。",
                        "answer": {
                            "reference": "当代码意图不能一眼看出时需要注释，例如说明一段计算在算什么业务规则、标注某个特殊写法的原因。注释应解释为什么，而不是把代码翻译一遍。",
                            "keywords": ["为什么", "意图", "业务规则", "原因"],
                        },
                        "explanation": "能区分「解释为什么」和「重复代码字面」即可，后者是无价值注释。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ------------------------------------------------------------------ 第 2 章
    {
        "code": "python-basics-02",
        "order_index": 2,
        "title": "变量和基本数据类型",
        "description": "给数据起名字、认清数字与布尔、学会类型转换，避开「字符串加数字为什么报错」这类新手高频困惑。",
        "lessons": [
            {
                "code": "python-basics-02-l01",
                "title": "变量、赋值与命名",
                "description": "理解变量是贴在数据上的名字，掌握赋值、重新赋值与命名规范。",
                "minutes": 45,
                "difficulty": "beginner",
                "objectives": """1. 能说清「变量名」和「值」是两件事。
2. 会用赋值语句保存数据，并用 print 读出来。
3. 会按规范给变量起名，避免语法错误。""",
                "why_learn": """没有变量，上一节的输入用完就丢，程序无法把数据带到下一步。
变量是所有程序的暂存区，后面学条件、循环、函数，全都要靠它记住中间结果。""",
                "concepts": """- **变量**：贴在某个数据上的名字，通过名字可以再次取到这个数据。
- **赋值**：等号把右边的值交给左边的名字，不是数学里的「相等」。
- **重新赋值**：同一个名字可以改指向新的值，旧值如果没有别的名字引用就会被丢弃。""",
                "plain": """变量像储物柜上的标签。你把书包放进 3 号柜，贴上「书包」标签，
之后说「把书包拿来」，拿到的是柜子里的东西，而不是标签本身。
如果第二天你把外套放进同一个柜子，标签还是「外套」，柜子里的东西已经换了。
这就是重新赋值：名字不变，指向的内容变了。""",
                "syntax": """变量名 = 值
print(变量名)

命名规则：
- 只能由字母、数字、下划线组成，不能以数字开头；
- 区分大小写，age 和 Age 是两个变量；
- 不能用 if、for、print 这类 Python 已经占用的名字；
- 习惯用小写字母加下划线，如 user_name、total_price。""",
                "example_code": '''name = "小明"
age = 18
score = 92.5
is_student = True

print(name)
print(age)
print(score)
print(is_student)

age = 19
print("过生日后：", age)''',
                "code_lines": """- 第 1 至 4 行：把文字、整数、小数、布尔值分别交给四个名字。
- 第 6 至 9 行：通过名字把存进去的值取出来输出。
- 第 11 行：重新赋值，age 现在指向 19，原来的 18 不再被这个程序使用。
- 第 12 行：输出重新赋值后的结果，验证名字不变、值变了。""",
                "output": """小明
18
92.5
True
过生日后： 19""",
                "mistakes": """1. 用数字开头，比如 2name。
2. 变量名中间带空格，比如 user name。
3. 用 Python 关键字，比如 class。
4. 把等号当「等于」用，写 18 = age 会直接报错。
5. 变量名拼错：定义了 user_name，使用时写 username。""",
                "error_analysis": """- 数字开头报 SyntaxError：Python 看到数字开头会当成数字字面量，后面紧跟字母就无法解析。
- 名字中间有空格的写法同样报语法错误：空格让 Python 以为这是两个东西。
- 用 class 当变量名报 SyntaxError：class 是保留字，不能当名字。
- 18 = age 报 SyntaxError: cannot assign to literal：等号左边必须是「可以被指向的名字」，不能是具体数值。
- 名字拼错报 NameError，说明这个标签从来没被创建过。""",
                "beginner_practice": """定义三个变量分别保存你的姓名、年龄、身高（小数），然后逐个输出。""",
                "advanced_practice": """定义 price = 19.9 和 count = 3，再定义 total = price * count，输出 total；然后把 count 改成 5，重新计算并输出新的 total，观察两次结果。""",
                "quiz_note": """本节测验 6 题：2 题考赋值与命名规则，2 题读代码判断变量最终的值，2 题写赋值与重新赋值程序。""",
                "summary": """- 变量是名字，赋值让名字指向一个值。
- 等号是「交给」，不是「相等」。
- 重新赋值会改变名字指向的内容，旧值不再被这个变量使用。
- 变量名要合法、可读、见名知意。""",
                "next_lesson": """下一课认清 Python 的几种基本数据类型：整数、小数、布尔，以及它们之间怎么互相转换。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-02-k01",
                        "legacy": "python-basics-02-01",
                        "name": "变量与赋值",
                        "goal": "会用变量保存数据、重新赋值并读出结果",
                        "minutes": 25,
                        "criteria": "能解释等号的含义，能写出合法的变量名并说明为什么合法",
                    },
                    {
                        "code": "python-basics-02-k02",
                        "legacy": "python-basics-02-02",
                        "name": "数字类型：整数与浮点数",
                        "goal": "区分 int 与 float，知道除法结果的特点",
                        "minutes": 20,
                        "criteria": "能判断一个字面量是 int 还是 float，能解释 10 / 4 的结果",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-02-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "登记个人信息",
                        "description": "用四个变量保存姓名、年龄、身高、是否学生，并逐行输出。",
                        "answer": 'name = "小明"\nage = 18\nheight = 1.72\nis_student = True\nprint(name)\nprint(age)\nprint(height)\nprint(is_student)',
                        "explanation": "文字用引号，整数直接写，小数带小数点，布尔用 True 或 False。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-02-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "算一算除法",
                        "description": "分别输出 10 / 4、10 // 4、10 % 4 的结果，并说明三者区别。",
                        "answer": "print(10 / 4)   # 2.5\nprint(10 // 4)  # 2\nprint(10 % 4)   # 2",
                        "explanation": "斜杠是真除法得小数，双斜杠取整舍去小数，百分号取余数。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-02-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "下列变量名合法的是？",
                        "options": [
                            ("A", "2name"),
                            ("B", "user name"),
                            ("C", "user_name"),
                            ("D", "class"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "字母开头、只用字母数字下划线、不是关键字，user_name 全部满足。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-02-l01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "执行 x = 5 后再执行 x = 8，变量 x 里保存的是 5 和 8 两个值。",
                        "answer": {"value": False},
                        "explanation": "变量同一时刻只指向一个值，重新赋值后 5 被替换为 8。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-02-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''下面代码输出什么？
price = 10
count = 3
total = price * count
price = 20
print(total)''',
                        "answer": {
                            "reference": "输出 30。total 在 price 改成 20 之前就算好了，后续修改 price 不会影响已算出的 total。",
                            "keywords": ["30", "之前", "不影响"],
                        },
                        "explanation": "赋值是立即计算并保存结果，不是保存公式。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-02-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "print(10 / 4) 的输出是？",
                        "options": [
                            ("A", "2"),
                            ("B", "2.5"),
                            ("C", "2.0"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "Python 的斜杠是真除法，结果为浮点数。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-02-l01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "定义变量保存一本书的书名和价格，输出「《书名》售价 X 元」，再把价格打九折后重新输出。",
                        "answer": {
                            "reference": 'title = "Python 入门"\nprice = 59.0\nprint(title, "售价", price, "元")\nprice = price * 0.9\nprint(title, "售价", price, "元")',
                            "keywords": ["price", "0.9", "print"],
                        },
                        "explanation": "用 price = price * 0.9 在旧值基础上计算并覆盖。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-02-l01-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "为什么 18 = age 会报错，而 age = 18 不会？",
                        "answer": {
                            "reference": "等号是赋值，左边必须是变量名（可以被指向的标签），右边是值。18 是具体数值，不能被赋值，所以报错；age = 18 是把 18 交给 age，方向正确。",
                            "keywords": ["赋值", "变量名", "左边", "值"],
                        },
                        "explanation": "抓住「左边必须是名字」这一条即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-basics-02-l02",
                "title": "数字、布尔与类型转换",
                "description": "认清 int、float、bool、str 四种类型，学会 int()、float()、str() 转换。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 会用 type() 查看一个值的类型。
2. 能区分整数、浮点数、布尔值与字符串。
3. 会用 int()、float()、str() 做转换，避免类型混用报错。""",
                "why_learn": """input 拿回来的永远是字符串，直接和数字相加就会报错。
类型转换是把「用户输入的文字」变成「可以计算的数据」的唯一途径，也是后面所有计算类程序的前提。""",
                "concepts": """- **int**：整数，如 18、-3、0。
- **float**：浮点数（带小数），如 1.72、3.0。
- **bool**：布尔值，只有 True 和 False 两个。
- **str**：字符串，用引号包起来的文本。
- **type(值)**：返回这个值的类型。""",
                "plain": """类型像容器的形状：整数是方盒，小数是长盒，字符串是软袋子。
把长盒里的东西硬塞进方盒会溢出来，Python 就会报错。
转换函数就是「换盒子」的动作：int("18") 把文字 18 换成数字 18。""",
                "syntax": """int("18")      文字转整数，得到 18
float("1.5")   文字转小数，得到 1.5
str(18)        数字转文字，得到 "18"
type(18)       查看类型，得到 int

注意：int("18.5") 会报错，因为带小数点的文字不能直接变整数，
要先 float("18.5") 再 int(...)。""",
                "example_code": '''age_text = input("请输入你的年龄：")
print("输入的类型是：", type(age_text))

age = int(age_text)
print("转换后的类型是：", type(age))
print("明年你", age + 1, "岁")

price = float("19.9")
count = 3
print("总价：", price * count)

print("把数字变成文字：", str(2026) + " 年")''',
                "code_lines": """- 第 1 行：input 拿到的是字符串，存进 age_text。
- 第 2 行：用 type() 证明它确实是字符串类型。
- 第 4 行：int(age_text) 把文字转成整数，存进新变量 age。
- 第 5 行：再次用 type() 对比，类型已经从字符串变成整数。
- 第 6 行：转成整数后才能做 age + 1，输出明年的年龄。
- 第 8 至 10 行：float("19.9") 把文字转成小数，再参与乘法。
- 第 12 行：str(2026) 把数字转成文字后再拼接，否则会报类型错误。""",
                "output": """请输入你的年龄：18
输入的类型是： <class 'str'>
转换后的类型是： <class 'int'>
明年你 19 岁
总价： 59.699999999999996
把数字变成文字： 2026 年""",
                "mistakes": """1. 忘记转换：input 结果直接加 1，报 TypeError。
2. int("18.5") 报 ValueError，因为带小数的文字不能直接转整数。
3. 以为 "18" + 1 会自动变成 19。
4. 用 bool("False") 当作假值——非空字符串一律为真。""",
                "error_analysis": """- "18" + 1 报 TypeError：加号在两边都是字符串时才是拼接，一边是数字就不知道该拼接还是该相加。
- int("18.5") 报 ValueError：整数转换只接受纯整数字符串，带小数点要先转 float。
- bool("False") 得到 True：字符串只要不是空的就为真，这五个字符非空，所以是 True。""",
                "beginner_practice": """用 input 询问两个整数，输出它们的和、差、积、商。""",
                "advanced_practice": """用 input 询问商品单价和数量（单价可能是小数），输出总价，并保留两位小数（提示：可用 round(值, 2)）。""",
                "quiz_note": """本节测验 6 题：2 题考类型判断与转换规则，2 题读代码判断输出与报错，2 题写带类型转换的计算程序。""",
                "summary": """- type() 能看清一个值到底是什么类型。
- input 永远返回字符串，参与计算前必须转换。
- int() 只接受纯整数文字，带小数要先 float()。
- 数字和字符串不能直接相加，需要先统一类型。""",
                "next_lesson": """下一章讲运算符与表达式：算术、比较、逻辑三种运算符，以及它们的优先级。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-02-k03",
                        "legacy": "python-basics-02-04",
                        "name": "布尔类型与比较",
                        "goal": "理解 True / False 的来源与真假判断规则",
                        "minutes": 20,
                        "criteria": "能说出哪些值在条件中为假，能写出产生布尔值的比较表达式",
                    },
                    {
                        "code": "python-basics-02-k04",
                        "legacy": "python-basics-02-05",
                        "name": "类型转换",
                        "goal": "会用 int / float / str 转换并处理转换失败",
                        "minutes": 30,
                        "criteria": "能写出把 input 结果转成数字的完整代码，能解释带小数的文字为何不能直接转整数",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-02-k03-ex1",
                        "kp": 0,
                        "type": "choice",
                        "title": "哪些值为假",
                        "description": "判断 0、0.0、空字符串、文字 0、空列表在条件中哪些为假。",
                        "answer": "0、0.0、空字符串、空列表为假；文字 0 为真，因为它是非空字符串。",
                        "explanation": "空容器、空字符串、数字 0 为假；非空字符串即使内容是 0 也为真。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-02-k04-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "两数计算器",
                        "description": "用 input 读两个整数，输出和、差、积、整除结果。",
                        "answer": 'a = int(input("第一个数："))\nb = int(input("第二个数："))\nprint("和：", a + b)\nprint("差：", a - b)\nprint("积：", a * b)\nprint("整除：", a // b)',
                        "explanation": "input 结果必须先用 int 包起来，否则加号会变成字符串拼接。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-02-l02-1",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "把文字 18.5 直接转成整数的结果是？",
                        "options": [
                            ("A", "18"),
                            ("B", "19"),
                            ("C", "18.5"),
                            ("D", "报错 ValueError"),
                        ],
                        "answer": {"value": "D"},
                        "explanation": "整数转换只接受纯整数字符串，带小数点必须先用 float 转换。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-02-l02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "字符串 False 在条件判断里会被当作假。",
                        "answer": {"value": False},
                        "explanation": "非空字符串一律为真，只有空字符串才为假。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-02-l02-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''用户输入 18，下面代码输出什么？
age = input("年龄：")
print(age + 1)''',
                        "answer": {
                            "reference": "报 TypeError。age 是字符串 18，字符串不能和整数 1 相加。需要写成 int(age) + 1。",
                            "keywords": ["TypeError", "字符串", "int", "转换"],
                        },
                        "explanation": "input 返回字符串，这是新手最常见的报错来源。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-02-l02-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "print(str(12) + \"3\") 的输出是？",
                        "options": [
                            ("A", "15"),
                            ("B", "123"),
                            ("C", "12 3"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "str(12) 变成文字 12，和文字 3 拼接得到 123。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-02-l02-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "写程序：读入商品单价（可能是小数）和数量（整数），输出总价。",
                        "answer": {
                            "reference": 'price = float(input("单价："))\ncount = int(input("数量："))\nprint("总价：", price * count)',
                            "keywords": ["float", "int", "input", "price * count"],
                        },
                        "explanation": "单价用 float，数量用 int，转换后再相乘。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-02-l02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么文字 0 在条件里为真，而数字 0 为假？",
                        "answer": {
                            "reference": "因为文字 0 是非空字符串，长度不为 0，在布尔判断中为真；而数字 0 本身就是假值。判断依据是空不空、是不是零，不是内容看起来像不像 0。",
                            "keywords": ["非空", "字符串", "假值", "0"],
                        },
                        "explanation": "抓住「非空字符串为真」这一条即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
