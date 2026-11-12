"""第 9—10 章教材内容：条件判断、for 循环。"""

CHAPTERS: list[dict] = [
    # ------------------------------------------------------------------ 第 9 章
    {
        "code": "python-basics-09",
        "order_index": 9,
        "title": "条件判断",
        "description": "让程序第一次拥有「选择」：条件成立走一条路，不成立走另一条，并用缩进把代码块划清楚。",
        "lessons": [
            {
                "code": "python-basics-09-l01",
                "title": "if / elif / else 与代码块缩进",
                "description": "写出单分支、双分支、多分支判断，理解缩进就是代码块的边界。",
                "minutes": 55,
                "difficulty": "beginner",
                "objectives": """1. 会写 if、if-else、if-elif-else 三种结构。
2. 理解缩进决定哪些语句属于同一个分支。
3. 会判断多个条件谁先命中，避免顺序写错导致逻辑错误。""",
                "why_learn": """到目前为止程序只会从头到尾执行一遍，不会做选择。
真实需求全是选择：成绩及格没有、余额够不够、输入是否合法。
条件判断是程序拥有「判断力」的起点，也是后面循环里控制退出时机的必备工具。""",
                "concepts": """- **条件**：一个能算出 True 或 False 的表达式。
- **if**：条件成立时执行下面的代码块。
- **else**：所有条件都不成立时执行。
- **elif**：else if 的缩写，用来串接多个互斥条件。
- **代码块**：缩进相同的若干行，属于同一个分支。""",
                "plain": """条件判断像走到岔路口看指示牌：牌子上写着条件，符合就走那条路。
elif 是「再看看下一个牌子」，else 是「以上都不符合就走这条路」。
缩进则是路的边界——同一段缩进的路才属于这个岔口，缩进错了，代码就走到别的路上去了。""",
                "syntax": """if 条件:
    条件成立时执行
elif 另一个条件:
    上一个不成立、这个成立时执行
else:
    全部不成立时执行

注意：
- 条件后面必须有英文冒号；
- 代码块必须统一缩进，通常 4 个空格；
- elif 可以有很多个，else 最多一个且在最后。""",
                "example_code": '''score = 78

if score >= 90:
    print("优秀")
elif score >= 60:
    print("及格")
else:
    print("不及格")

age = 16
has_ticket = True

if age >= 18:
    print("可以单独入场")
elif has_ticket:
    print("有票，可由成人陪同入场")
else:
    print("不能入场")''',
                "code_lines": """- 第 3 行：第一个条件判断 78 是否大于等于 90，不成立。
- 第 5 行：接着判断是否大于等于 60，成立，输出「及格」，后面的 else 不再执行。
- 第 6 至 7 行：只有前面都不成立才会走到这里。
- 第 9 至 18 行：第二个例子演示 elif 里用了另一个条件（是否有票），两个条件不是同一维度，但分支互斥。""",
                "output": """及格
有票，可由成人陪同入场""",
                "mistakes": """1. 条件后面漏写冒号。
2. 缩进不统一，有的 4 空格有的 2 空格。
3. 用 = 代替 ==。
4. 把最宽的条件写在最前面，后面的分支永远进不去。
5. else 后面再写条件。""",
                "error_analysis": """- 漏冒号报 SyntaxError: expected ':'，Python 必须靠冒号知道代码块要开始了。
- 缩进不一致报 IndentationError，同一代码块必须完全对齐。
- if score = 60 报 SyntaxError：等号是赋值，比较要用 ==。
- 先写 if score >= 60 再写 elif score >= 90，那么 95 分会在第一个条件就被拦下，永远输出「及格」，后面的分支成了死代码。条件要从窄到宽排列。
- else 后面不能加条件，写 else score < 60 报 SyntaxError；需要条件就用 elif。""",
                "beginner_practice": """读入一个整数，判断它是正数、负数还是零，分别输出提示。""",
                "advanced_practice": """读入年龄，按「小于 12 儿童、12 到 17 青少年、18 到 59 成人、60 及以上老年」四档输出，注意条件顺序。""",
                "quiz_note": """本节测验 6 题：2 题考分支结构与缩进规则，2 题读代码判断走哪个分支，2 题写多分支判断程序。""",
                "summary": """- if 判断条件，elif 串接互斥条件，else 兜底。
- 冒号不能少，缩进必须统一。
- 条件顺序决定结果，范围判断要从窄到宽。
- 只会执行第一个成立的分支，其余跳过。""",
                "next_lesson": """下一章学 for 循环：让程序把一件重复的事自动做很多遍。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-09-k01",
                        "legacy": "python-basics-04-01",
                        "name": "条件判断 if / elif / else",
                        "goal": "会写单分支、双分支、多分支判断",
                        "minutes": 30,
                        "criteria": "能针对给定条件写出正确分支，能解释为何条件顺序会影响结果",
                    },
                    {
                        "code": "python-basics-09-k02",
                        "legacy": "python-basics-04-02",
                        "name": "缩进与代码块",
                        "goal": "理解缩进决定代码块归属",
                        "minutes": 25,
                        "criteria": "能指出缩进错误会导致哪一行不属于该分支",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-09-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "判断正负零",
                        "description": "读入一个整数，输出它是正数、负数还是零。",
                        "answer": 'n = int(input("请输入整数："))\nif n > 0:\n    print("正数")\nelif n < 0:\n    print("负数")\nelse:\n    print("零")',
                        "explanation": "三个分支互斥，用 if-elif-else 覆盖全部情况。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-09-k02-ex2",
                        "kp": 1,
                        "type": "short_answer",
                        "title": "找出缩进错误",
                        "description": "说明下面代码为什么报错：if True: 下一行 4 空格 print，再下一行 2 空格 print。",
                        "answer": "同一个代码块必须缩进一致。第二行 4 空格、第三行 2 空格，Python 无法判断第三行属于哪个块，报 IndentationError。",
                        "explanation": "统一用 4 个空格即可修复。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-09-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "关于 elif，下列说法正确的是？",
                        "options": [
                            ("A", "可以有多个，且必须写在 else 之后"),
                            ("B", "可以有多个，只有前面条件都不成立时才判断"),
                            ("C", "一个 if 只能配一个 elif"),
                            ("D", "elif 后面可以再写 else if"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "elif 可以多个，按顺序判断，前面命中后不再判断后面的。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-09-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "Python 用缩进来表示代码块，同一代码块的缩进必须一致。",
                        "answer": {"value": True},
                        "explanation": "缩进就是 Python 的语法结构，不一致会报 IndentationError。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-09-l01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''score = 95
if score >= 60:
    print("及格")
elif score >= 90:
    print("优秀")''',
                        "answer": {
                            "reference": "输出「及格」。95 先命中 >= 60 这个宽条件，elif 不再判断，>= 90 的分支成了永远不会执行的死代码。",
                            "keywords": ["及格", "先命中", "死代码", "顺序"],
                        },
                        "explanation": "范围判断必须从窄到宽，否则宽条件会吞掉所有情况。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-09-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "下面哪一行会直接导致 IndentationError？",
                        "options": [
                            ("A", "if True:"),
                            ("B", "    print(1)"),
                            ("C", "  print(2)"),
                            ("D", "else:"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "同一代码块缩进必须一致，2 空格与 4 空格混用会报缩进错误。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-09-l01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "读入年龄，小于 12 输出儿童，12 到 17 输出青少年，18 及以上输出成人。",
                        "answer": {
                            "reference": 'age = int(input("年龄："))\nif age < 12:\n    print("儿童")\nelif age < 18:\n    print("青少年")\nelse:\n    print("成人")',
                            "keywords": ["if", "elif", "age < 12", "age < 18"],
                        },
                        "explanation": "条件从小到大排列，elif 隐含「上一个不成立」的前提。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-09-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么判断成绩等级时，不能先写 score >= 60 再写 elif score >= 90？",
                        "answer": {
                            "reference": "因为分支按顺序判断，一旦第一个条件成立就跳出整个结构。95 分满足 >= 60，会直接输出及格，永远不会走到 >= 90 的分支。应把更严格的条件写在前面。",
                            "keywords": ["顺序", "第一个成立", "跳出", "严格"],
                        },
                        "explanation": "能说出「命中即跳出」这一机制即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ------------------------------------------------------------------ 第 10 章
    {
        "code": "python-basics-10",
        "order_index": 10,
        "title": "for 循环",
        "description": "把重复的事交给程序：用 for 与 range 数数、遍历列表、累加统计，并学会在合适的时候跳出循环。",
        "lessons": [
            {
                "code": "python-basics-10-l01",
                "title": "for 循环与 range 的基本用法",
                "description": "用 range 控制次数、遍历列表元素、在循环里累加求和。",
                "minutes": 55,
                "difficulty": "beginner",
                "objectives": """1. 会写 for i in range(n) 控制循环次数。
2. 会用 range(start, stop, step) 生成需要的数字序列。
3. 会在循环里累加、计数，并用循环遍历列表。""",
                "why_learn": """要打印 1 到 100、要统计班里 40 个人的总分、要把购物车里每件商品的价格加起来，
手写 100 行代码既不现实也无法维护。循环让「一次编写、重复执行」成为可能，
它是所有批量处理的基础。""",
                "concepts": """- **循环**：让一段代码重复执行。
- **for**：从一个序列里依次取出元素，每取一个执行一次循环体。
- **range(n)**：生成 0 到 n-1 的整数序列。
- **range(start, stop, step)**：从 start 开始，到 stop 之前结束，每次增加 step。
- **累加器**：循环外先定义变量（如 total = 0），循环里不断往上加。""",
                "plain": """for 循环像把一叠卷子依次发给老师批：一次拿一张，批完放一边，再拿下一张，
拿完为止。range(5) 就是「这里有 5 张卷子」。
累加器则像一个存钱罐：循环开始前它是空的（total = 0），每处理一个就往里放一点。""",
                "syntax": """for i in range(5):         i 依次是 0、1、2、3、4
for i in range(1, 6):      i 依次是 1 到 5
for i in range(0, 10, 2):  i 依次是 0、2、4、6、8
for item in 列表:           依次取出每个元素

total = 0
for n in 列表:
    total = total + n    循环结束后 total 是总和""",
                "example_code": '''for i in range(5):
    print("第", i, "次")

total = 0
for n in range(1, 101):
    total = total + n
print("1 到 100 的和：", total)

fruits = ["苹果", "香蕉", "橘子"]
for fruit in fruits:
    print("水果：", fruit)

count = 0
scores = [88, 95, 60, 72]
for s in scores:
    if s >= 60:
        count = count + 1
print("及格人数：", count)''',
                "code_lines": """- 第 1 至 2 行：range(5) 产生 0 到 4，i 每取一个值就执行一次循环体。
- 第 4 至 6 行：total 在循环外初始化为 0，循环里把每个数加进去，循环结束得到 5050。
- 第 8 至 10 行：直接遍历列表，fruit 依次是三个水果，不需要下标。
- 第 12 至 17 行：count 计数，配合条件判断只统计及格的。""",
                "output": """第 0 次
第 1 次
第 2 次
第 3 次
第 4 次
1 到 100 的和： 5050
水果： 苹果
水果： 香蕉
水果： 橘子
及格人数： 3""",
                "mistakes": """1. 以为 range(5) 是 1 到 5，实际是 0 到 4。
2. 把累加器写在循环里面，每次都重置为 0。
3. 忘记冒号或缩进。
4. 在循环里修改正在遍历的列表。
5. 用 range 遍历列表下标时越界。""",
                "error_analysis": """- range(5) 从 0 开始、到 5 之前结束，共 5 个数；要 1 到 5 请写 range(1, 6)。
- 把 total = 0 写进循环体，每轮都被清零，最后结果只是最后一个数。
- for 语句漏冒号报 SyntaxError；循环体不缩进则循环体为空或语法错误。
- 遍历列表时 remove 元素会导致跳过某些元素，因为下标在变化；应先复制一份再处理。
- 遍历下标时写 range(len(lst) + 1) 会越界，range 的终点本来就取不到。""",
                "beginner_practice": """用 for 循环输出 1 到 10，再输出 1 到 10 的和。""",
                "advanced_practice": """给定成绩列表，用循环统计及格人数、不及格人数与平均分。""",
                "quiz_note": """本节测验 6 题：2 题考 range 的取值与循环次数，2 题读代码判断输出，2 题写累加与遍历程序。""",
                "summary": """- for 从序列里逐个取元素，取完结束。
- range(n) 是 0 到 n-1，range(a, b) 是 a 到 b-1。
- 累加器必须在循环外初始化。
- 遍历列表直接 for item in 列表 即可。""",
                "next_lesson": """下一课学嵌套循环与 break、continue，处理「表格」和「提前结束」这两类需求。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-10-k01",
                        "legacy": "python-basics-04-04",
                        "name": "for 循环与 range",
                        "goal": "会用 for 与 range 控制循环次数",
                        "minutes": 30,
                        "criteria": "能写出 range 的三个参数形式，能预测循环执行次数",
                    },
                    {
                        "code": "python-basics-10-k02",
                        "name": "循环累加与遍历",
                        "goal": "会在循环中累加、计数并遍历列表",
                        "minutes": 25,
                        "criteria": "能写出求和与计数的完整循环，累加器位置正确",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-10-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "输出 1 到 10",
                        "description": "用 for 循环输出 1 到 10，每行一个。",
                        "answer": "for i in range(1, 11):\n    print(i)",
                        "explanation": "range(1, 11) 产生 1 到 10。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-10-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "统计及格人数",
                        "description": "遍历 [88, 45, 60, 72]，统计及格（>=60）人数。",
                        "answer": "scores = [88, 45, 60, 72]\ncount = 0\nfor s in scores:\n    if s >= 60:\n        count = count + 1\nprint(count)",
                        "explanation": "count 在循环外初始化，循环里条件成立才加一。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-10-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "range(3) 会依次产生哪些数？",
                        "options": [
                            ("A", "1, 2, 3"),
                            ("B", "0, 1, 2"),
                            ("C", "0, 1, 2, 3"),
                            ("D", "3"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "range(3) 从 0 开始，到 3 之前结束。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-10-l01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "range(1, 6) 产生的数字包含 6。",
                        "answer": {"value": False},
                        "explanation": "range 的终点取不到，range(1, 6) 是 1 到 5。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-10-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''total = 0
for n in range(1, 4):
    total = total + n
print(total)''',
                        "answer": {
                            "reference": "输出 6。循环依次加 1、2、3，累计 1+2+3=6。",
                            "keywords": ["6", "1、2、3", "累加"],
                        },
                        "explanation": "range(1, 4) 是 1、2、3 三个数。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-10-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": '''下面代码输出什么？
total = 0
for n in [1, 2, 3]:
    total = 0
    total = total + n
print(total)''',
                        "options": [
                            ("A", "6"),
                            ("B", "3"),
                            ("C", "0"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "total 每轮都被重置为 0，最后只保留最后一个数 3。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-10-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "用 for 循环求 1 到 100 的和并输出。",
                        "answer": {
                            "reference": "total = 0\nfor n in range(1, 101):\n    total = total + n\nprint(total)",
                            "keywords": ["total", "range(1, 101)", "total + n"],
                        },
                        "explanation": "累加器在循环外初始化，循环内累加。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-10-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如果要每隔 3 输出一个数（0、3、6、9），range 应该怎么写？",
                        "answer": {
                            "reference": "写 range(0, 12, 3)。第一个参数是起点 0，第二个是终点（取不到），第三个是步长 3。",
                            "keywords": ["range(0, 12, 3)", "步长", "起点", "终点"],
                        },
                        "explanation": "掌握 range 三参数形式即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-basics-10-l02",
                "title": "循环嵌套与 break、continue",
                "description": "用两层循环处理表格，用 break 提前结束、用 continue 跳过本轮。",
                "minutes": 55,
                "difficulty": "beginner",
                "objectives": """1. 会写两层嵌套循环，理解内外层各执行多少次。
2. 会用 break 提前跳出整个循环。
3. 会用 continue 跳过本轮剩余语句，进入下一轮。""",
                "why_learn": """打印乘法表、遍历二维成绩表都要靠嵌套循环。
而现实中常常需要「找到就停」或「这一条不合格就跳过」，
break 与 continue 正是控制循环节奏的两个开关。""",
                "concepts": """- **嵌套循环**：循环体里还有循环，外层跑一次，内层跑完一整轮。
- **break**：立刻结束当前整个循环。
- **continue**：结束本轮，直接进入下一轮。
- **执行次数**：两层循环总次数 = 外层次数 × 内层次数。""",
                "plain": """嵌套循环像日历：外层是月份，内层是这个月的每一天。
每翻一个月，就要把里面的日子从 1 号数到月底。
break 像「提前放学」，整天的课都不上了；continue 像「这节课我不上，但下节课照常」。""",
                "syntax": """for i in range(1, 4):
    for j in range(1, 4):
        print(i, j)      外层 3 次，内层每次 3 次，共 9 次

for n in 列表:
    if 条件:
        break            整个循环结束
    if 另一个条件:
        continue         跳过本轮剩下的语句""",
                "example_code": '''for i in range(1, 4):
    for j in range(1, 4):
        print(i, "x", j, "=", i * j)

print("查找 3：")
for n in [1, 5, 3, 7, 9]:
    if n == 3:
        print("找到了")
        break
    print("不是", n)

print("只输出偶数：")
for n in range(1, 7):
    if n % 2 != 0:
        continue
    print(n)''',
                "code_lines": """- 第 1 至 3 行：外层 i 取 1、2、3，每取一次，内层 j 都完整跑一遍 1 到 3，共 9 行输出。
- 第 5 至 10 行：依次检查列表元素，遇到 3 立刻 break，后面的 7、9 不再检查。
- 第 12 至 15 行：奇数时 continue 跳过 print，只留下偶数。""",
                "output": """1 x 1 = 1
1 x 2 = 2
1 x 3 = 3
2 x 1 = 2
2 x 2 = 4
2 x 3 = 6
3 x 1 = 3
3 x 2 = 6
3 x 3 = 9
查找 3：
不是 1
不是 5
找到了
只输出偶数：
2
4
6""",
                "mistakes": """1. 以为 break 能跳出两层循环，其实只跳出最近的一层。
2. continue 后面的语句永远不执行，误以为会执行。
3. 内层循环用了和外层相同的变量名，导致外层变量被覆盖。
4. 嵌套层数过多，逻辑难读。
5. 在 continue 之前就写输出，导致跳过的效果看不出来。""",
                "error_analysis": """- break 只作用于它所在的那一层循环；要跳出两层需要额外标志位或把逻辑抽成函数。
- continue 之后本轮剩余语句全部跳过，如果 print 写在 continue 后面就永远看不到输出。
- 内外层都用 i：内层循环结束后 i 的值被改掉，外层再取下一个值时行为可能不符合预期。
- 嵌套超过两层通常意味着该拆分逻辑了。""",
                "beginner_practice": """用嵌套循环输出 3 行 3 列的数字表，每行显示行号与列号。""",
                "advanced_practice": """遍历 1 到 20，遇到 3 的倍数就跳过，遇到大于 15 的数就停止，输出被打印出来的数。""",
                "quiz_note": """本节测验 6 题：2 题考嵌套次数与 break/continue 区别，2 题读代码判断输出行数，2 题写嵌套与提前结束的代码。""",
                "summary": """- 嵌套循环里外层一次、内层一整轮。
- break 结束当前整层循环，continue 只跳过本轮。
- 内外层尽量用不同变量名。
- 嵌套超过两层要考虑拆分。""",
                "next_lesson": """下一章讲 while 循环：当循环次数事先不知道、只能靠条件决定时，就该用它。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-10-k03",
                        "legacy": "python-basics-04-06",
                        "name": "循环嵌套",
                        "goal": "会写两层嵌套循环并计算总执行次数",
                        "minutes": 25,
                        "criteria": "能算出嵌套循环的输出行数，能避免内外层变量重名",
                    },
                    {
                        "code": "python-basics-10-k04",
                        "legacy": "python-basics-04-05",
                        "name": "break 与 continue",
                        "goal": "会用 break 提前结束、用 continue 跳过本轮",
                        "minutes": 30,
                        "criteria": "能说明两者区别，能预测带 break/continue 的循环输出",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-10-k03-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "三行三列表",
                        "description": "用嵌套循环输出 3 行 3 列，每行输出「行号-列号」。",
                        "answer": 'for i in range(1, 4):\n    for j in range(1, 4):\n        print(i, "-", j)',
                        "explanation": "外层控制行，内层控制列，共 9 次输出。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-10-k04-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "跳过奇数并提前停止",
                        "description": "遍历 1 到 10，跳过奇数，遇到 8 时停止，输出被打印的数。",
                        "answer": "for n in range(1, 11):\n    if n % 2 != 0:\n        continue\n    if n > 8:\n        break\n    print(n)",
                        "explanation": "先跳过奇数，再判断是否超过 8，最后输出。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-10-l02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "两层循环，外层 3 次、内层 4 次，循环体一共执行多少次？",
                        "options": [
                            ("A", "7"),
                            ("B", "12"),
                            ("C", "3"),
                            ("D", "4"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "外层每跑一次，内层完整跑 4 次，共 3×4=12 次。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-10-l02-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "在两层嵌套循环的内层执行 break，会同时跳出内外两层。",
                        "answer": {"value": False},
                        "explanation": "break 只结束它所在的那一层循环。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-10-l02-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''for n in [1, 2, 3, 4]:
    if n == 2:
        continue
    print(n)''',
                        "answer": {
                            "reference": "输出 1、3、4 三行。n 等于 2 时 continue 跳过本轮 print，其余照常输出。",
                            "keywords": ["1", "3", "4", "continue"],
                        },
                        "explanation": "continue 只跳过本轮，不结束循环。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-10-l02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": '''for i in range(2):
    for j in range(2):
        print(i, j)
输出几行？''',
                        "options": [
                            ("A", "2 行"),
                            ("B", "4 行"),
                            ("C", "1 行"),
                            ("D", "0 行"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "外层 2 次，内层每次 2 次，共 4 行。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-10-l02-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "遍历 1 到 10，跳过 3 的倍数，遇到大于 8 的数停止，输出其余的数。",
                        "answer": {
                            "reference": "for n in range(1, 11):\n    if n % 3 == 0:\n        continue\n    if n > 8:\n        break\n    print(n)",
                            "keywords": ["continue", "break", "n % 3", "print"],
                        },
                        "explanation": "先跳过 3 的倍数，再判断是否超过 8。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-10-l02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "嵌套循环里内外层使用同名变量 i 会有什么问题？",
                        "answer": {
                            "reference": "内层循环会覆盖外层的 i，内层结束后 i 已变成内层的最后一个值，外层下一次取值的行为可能与预期不符，逻辑容易出错。应给内外层用不同变量名，如 i 与 j。",
                            "keywords": ["覆盖", "外层", "不同变量名", "i 与 j"],
                        },
                        "explanation": "能指出变量被覆盖导致逻辑异常即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
