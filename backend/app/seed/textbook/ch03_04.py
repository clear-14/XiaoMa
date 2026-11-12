"""第 3—4 章教材内容：运算符与表达式、字符串。"""

CHAPTERS: list[dict] = [
    # ------------------------------------------------------------------ 第 3 章
    {
        "code": "python-basics-03",
        "order_index": 3,
        "title": "运算符和表达式",
        "description": "算术、比较、逻辑三类运算符一次讲清，并用优先级规则解释「为什么算出来的数不对」。",
        "lessons": [
            {
                "code": "python-basics-03-l01",
                "title": "算术、比较与逻辑运算",
                "description": "掌握加减乘除与取余、比较大小、用 and/or/not 组合条件，并理解优先级。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 会使用 + - * / // % ** 六种算术运算符。
2. 会用 > < >= <= == != 得到 True 或 False。
3. 会用 and、or、not 组合多个条件，并按优先级正确算出一个表达式。""",
                "why_learn": """程序做的每一件事，本质都是「拿数据做运算，再根据结果决定下一步」。
运算符就是这套计算的词汇表：算价格要用乘法，判断成绩是否及格要用比较，
判断「既登录又实名」要用逻辑运算。后面的条件判断和循环，全部建立在它们之上。""",
                "concepts": """- **算术运算符**：加 +、减 -、乘 *、除 /、整除 //、取余 %、幂 **。
- **比较运算符**：大于 >、小于 <、大于等于 >=、小于等于 <=、等于 ==、不等于 !=，结果一定是 True 或 False。
- **逻辑运算符**：and（两边都真才真）、or（一边真就真）、not（取反）。
- **表达式**：由值和运算符组成、能算出一个结果的一段代码。
- **优先级**：括号 > 幂 > 乘除取余 > 加减 > 比较 > not > and > or。""",
                "plain": """算术运算符像计算器上的按键，比较运算符像裁判手里的对错牌，
逻辑运算符像两个开关串在一起：and 是串联（两个都开灯才亮），or 是并联（开一个就亮）。
优先级则像四则运算里的「先乘除后加减」——不确定时最稳的做法是加括号，
因为括号的优先级最高，读代码的人也更容易看懂。""",
                "syntax": """a + b     加
a - b     减
a * b     乘
a / b     除（结果一定是小数）
a // b    整除（只要整数部分）
a % b     取余（除法剩下的部分）
a ** b    幂（a 的 b 次方）

a > b     比较，得到 True 或 False
条件1 and 条件2    两个都成立才为 True
条件1 or 条件2     有一个成立就为 True
not 条件           真变假、假变真""",
                "example_code": '''price = 19
count = 3
total = price * count
print("总价：", total)

print("平均每人：", total / 4)
print("只能付整元：", total // 4)
print("还剩：", total % 4)
print("2 的 10 次方：", 2 ** 10)

age = 16
has_ticket = True
print("年龄够 18：", age >= 18)
print("能进场：", age >= 18 or has_ticket)
print("既够年龄又有票：", age >= 18 and has_ticket)
print("不是成年人：", not age >= 18)''',
                "code_lines": """- 第 1 至 3 行：用乘法算出总价 57。
- 第 4 行：真除法，57 除以 4 得到 14.25。
- 第 5 行：整除只要整数部分，得到 14。
- 第 6 行：取余得到除不尽剩下的 1。
- 第 7 行：幂运算，2 的 10 次方是 1024。
- 第 9 至 14 行：分别演示比较运算、or、and、not 的返回值，输出全是 True 或 False。""",
                "output": """总价： 57
平均每人： 14.25
只能付整元： 14
还剩： 1
2 的 10 次方： 1024
年龄够 18： False
能进场： True
既够年龄又有票： False
不是成年人： True""",
                "mistakes": """1. 把赋值等号当成比较：写 if score = 60，应该是 ==。
2. 以为 5 / 2 得 2，其实得 2.5。
3. 混淆 // 和 %：// 要整数部分，% 要余数。
4. 逻辑运算优先级搞错：a or b and c 先算 and。
5. 用 and 连接两个比较却写成 18 <= age <= 60 之外的错误形式，如 age >= 18 and <= 60。""",
                "error_analysis": """- if score = 60 会报 SyntaxError：等号是赋值，不能出现在条件位置上，必须用 == 表示「是否相等」。
- 5 / 2 得 2.5 而不是 2：斜杠永远做真除法，要整数部分请用 //。
- 5 // 2 得 2、5 % 2 得 1，两者回答的是不同问题：商和余数。
- age >= 18 and <= 60 报 SyntaxError：and 两边都必须是完整条件，右边只有 <= 60 缺了左边的值，应写 age <= 60。
- a or b and c 会先算 b and c：and 的优先级高于 or，不确定就加括号。""",
                "beginner_practice": """定义商品单价和数量，输出总价、打八折后的价格、以及总价除以 3 的商和余数。""",
                "advanced_practice": """给定年龄 age 和是否会员 is_member，用一行逻辑表达式判断「年龄大于等于 18 且是会员」，再判断「年龄小于 18 或者是会员」，分别输出结果。""",
                "quiz_note": """本节测验 6 题：2 题考运算符含义与优先级，2 题读代码算结果，2 题写表达式解决实际判断。""",
                "summary": """- 算术运算符负责算数，斜杠永远得小数，双斜杠取整，百分号取余。
- 比较运算符的结果一定是 True 或 False。
- and 要两边都真、or 有一边真就行、not 取反。
- 优先级记不住就加括号，括号最优先也最好读。""",
                "next_lesson": """下一章进入字符串：它是最常用的数据类型，也是处理文本、姓名、地址、日志的基础。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-03-k01",
                        "legacy": "python-basics-03-01",
                        "name": "算术运算符",
                        "goal": "掌握加减乘除、整除、取余与幂",
                        "minutes": 15,
                        "criteria": "能正确算出含 // 与 % 的表达式结果，并解释两者区别",
                    },
                    {
                        "code": "python-basics-03-k02",
                        "legacy": "python-basics-03-02",
                        "name": "比较运算符",
                        "goal": "会用比较运算符得到布尔结果",
                        "minutes": 10,
                        "criteria": "能写出判断大小与相等的表达式，知道 == 与 = 的区别",
                    },
                    {
                        "code": "python-basics-03-k03",
                        "legacy": "python-basics-03-03",
                        "name": "逻辑运算符",
                        "goal": "会用 and / or / not 组合条件",
                        "minutes": 15,
                        "criteria": "能根据真值表判断组合条件的真假",
                    },
                    {
                        "code": "python-basics-03-k04",
                        "legacy": "python-basics-03-04",
                        "name": "运算符优先级与表达式",
                        "goal": "能按优先级正确计算复合表达式",
                        "minutes": 10,
                        "criteria": "能说明 and 与 or 的先后顺序，并会用括号改写",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-03-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "分账计算",
                        "description": "总价 57 元，4 人平摊，输出每人应付（保留小数）、至少付多少整元、还剩多少元。",
                        "answer": 'total = 57\nprint("每人：", total / 4)\nprint("整元：", total // 4)\nprint("剩余：", total % 4)',
                        "explanation": "斜杠得小数，双斜杠取整，百分号取余。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-03-k03-ex2",
                        "kp": 2,
                        "type": "coding",
                        "title": "入场资格判断",
                        "description": "定义 age 与 has_ticket，输出「能进场」的判断结果（年龄满 18 或有票即可）。",
                        "answer": 'age = 16\nhas_ticket = True\nprint(age >= 18 or has_ticket)',
                        "explanation": "or 只要一边成立就为 True，本例有票所以能进场。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-03-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "print(7 // 2, 7 % 2) 的输出是？",
                        "options": [
                            ("A", "3.5 1"),
                            ("B", "3 1"),
                            ("C", "3 3"),
                            ("D", "2 3"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "7 除以 2 商 3 余 1，双斜杠得商，百分号得余数。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-03-l01-2",
                        "kp": 3,
                        "type": "true_false",
                        "stem": "在表达式 a or b and c 中，会先计算 b and c。",
                        "answer": {"value": True},
                        "explanation": "and 的优先级高于 or，所以先算 and 再算 or。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-03-l01-3",
                        "kp": 2,
                        "type": "code_analysis",
                        "stem": '''age = 16
has_ticket = True
print(age >= 18 and has_ticket)
print(age >= 18 or has_ticket)''',
                        "answer": {
                            "reference": "第一行输出 False，第二行输出 True。年龄 16 不满足 18，and 需要两边都真所以为 False；or 只要一边真就为 True，因为有票。",
                            "keywords": ["False", "True", "and", "or"],
                        },
                        "explanation": "and 要求两个条件同时成立，or 只要求其中一个成立。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-03-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "下列哪个表达式的结果是 True？",
                        "options": [
                            ("A", "3 == 3.0"),
                            ("B", "3 != 3"),
                            ("C", "5 < 4"),
                            ("D", "not True"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "3 与 3.0 数值相等，== 返回 True；其余分别为 False、False、False。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-03-l01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写代码：总价 128 元，6 人平摊，输出每人应付金额、每人至少付多少整元、还剩多少元没摊完。",
                        "answer": {
                            "reference": 'total = 128\nprint("每人：", total / 6)\nprint("整元：", total // 6)\nprint("剩余：", total % 6)',
                            "keywords": ["/", "//", "%", "128"],
                        },
                        "explanation": "三种除法分别对应小数结果、整数商和余数。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-03-l01-6",
                        "kp": 3,
                        "type": "short_answer",
                        "stem": "为什么判断「年龄在 18 到 60 之间」不能写成 age >= 18 and <= 60？正确写法是什么？",
                        "answer": {
                            "reference": "因为 and 两边都必须是完整条件，<= 60 缺少左边的值，会报语法错误。正确写法是 age >= 18 and age <= 60。",
                            "keywords": ["完整条件", "两边", "age <= 60", "语法错误"],
                        },
                        "explanation": "逻辑运算符连接的是表达式，不是表达式的一部分。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ------------------------------------------------------------------ 第 4 章
    {
        "code": "python-basics-04",
        "order_index": 4,
        "title": "字符串",
        "description": "从创建、索引、切片到常用方法与 f-string 格式化，把文本处理这块地基打牢。",
        "lessons": [
            {
                "code": "python-basics-04-l01",
                "title": "字符串的创建、索引与切片",
                "description": "理解字符串是有顺序的字符序列，会用下标取单个字符、用切片取一段。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 会用单引号、双引号、三引号创建字符串。
2. 会用下标取出单个字符，知道下标从 0 开始、负数从末尾数。
3. 会用切片 [start:end] 取出一段字符，并知道 end 位置取不到。""",
                "why_learn": """姓名、地址、评论、日志、网页内容，全都是字符串。
只要程序要处理文本，就一定会用到「取第几个字」「取前几位」「截掉末尾」这些操作，
它们全部建立在索引与切片之上。""",
                "concepts": """- **字符串**：用引号包起来的一串字符，是不可变类型。
- **索引**：每个字符的位置编号，从 0 开始；-1 表示最后一个字符。
- **切片**：用 [start:end] 取出从 start 到 end 之前的一段，end 本身取不到。
- **不可变**：字符串一旦创建就不能原地修改，所有「修改」都会产生新字符串。""",
                "plain": """字符串像一列排好队的车厢，每节车厢有编号，第一节是 0 号。
索引就是「我要第几节车厢」，切片是「我要从第 2 节到第 5 节这一段」。
说「到第 5 节」时，拿到的是 2、3、4 号，5 号不在内——
这就是切片最容易记错的地方：含头不含尾。""",
                "syntax": """s = "Python"
s[0]        取第 1 个字符，得到 P
s[-1]       取最后 1 个字符，得到 n
s[1:4]      取下标 1、2、3，得到 yth
s[:3]       从头取到下标 3 之前，得到 Pyt
s[3:]       从下标 3 取到末尾，得到 hon
len(s)      字符串长度，得到 6""",
                "example_code": '''word = "Python"
print("原字符串：", word)
print("长度：", len(word))
print("第 1 个字符：", word[0])
print("最后一个字符：", word[-1])
print("前三个：", word[:3])
print("从第 3 个到末尾：", word[3:])
print("中间三个：", word[1:4])

name = "小明"
print("拼接：", name + "同学")
print("重复：", "-" * 10)''',
                "code_lines": """- 第 1 行：创建字符串，长度 6，下标是 0 到 5。
- 第 3 行：len() 返回字符个数。
- 第 4 行：word[0] 取第一个字符 P。
- 第 5 行：word[-1] 从末尾数第一个，得到 n。
- 第 6 行：word[:3] 省略起点表示从头开始，取到下标 3 之前，得到 Pyt。
- 第 7 行：word[3:] 省略终点表示一直到末尾，得到 hon。
- 第 8 行：word[1:4] 取 1、2、3 三个位置，得到 yth。
- 第 11 至 12 行：加号拼接两个字符串，乘号把字符串重复若干次。""",
                "output": """原字符串： Python
长度： 6
第 1 个字符： P
最后一个字符： n
前三个： Pyt
从第 3 个到末尾： hon
中间三个： yth
拼接： 小明同学
重复： ----------""",
                "mistakes": """1. 以为下标从 1 开始，写 word[1] 想取第一个字符。
2. 切片终点写错，想取前 3 个却写 word[0:2]。
3. 下标越界，对长度 6 的字符串写 word[6]。
4. 试图用 word[0] = "J" 修改字符串。
5. 拼接字符串和数字时不转换类型。""",
                "error_analysis": """- 下标从 0 开始，所以第一个字符是 word[0]，word[1] 是第二个字符 y。
- 切片含头不含尾，取前 3 个应写 word[0:3] 或 word[:3]，写 [0:2] 只能得到 Py。
- 长度 6 的字符串合法下标是 0 到 5，写 word[6] 报 IndexError: string index out of range。
- 字符串不可变，word[0] = "J" 报 TypeError: 'str' object does not support item assignment。需要构造新字符串，例如 "J" + word[1:]。
- "年龄" + 18 报 TypeError，数字要先 str(18) 转成文字。""",
                "beginner_practice": """定义字符串 "programming"，输出它的长度、第一个字符、最后一个字符、前 4 个字符。""",
                "advanced_practice": """给定手机号 "13812345678"，用切片输出前 3 位与后 4 位，并拼成「138****5678」的形式（星号用字符串乘法生成）。""",
                "quiz_note": """本节测验 6 题：2 题考下标与切片规则，2 题读代码判断取到的内容，2 题写切片处理真实文本。""",
                "summary": """- 字符串是有顺序、不可变的字符序列。
- 下标从 0 开始，-1 表示最后一个。
- 切片 [start:end] 含头不含尾，省略起点从头开始，省略终点到末尾。
- 加号拼接、乘号重复，类型不同要先转换。""",
                "next_lesson": """下一课学字符串的常用方法与 f-string 格式化，让文本处理从「能取」变成「能改造」。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-04-k01",
                        "legacy": "python-basics-02-03",
                        "name": "字符串基础",
                        "goal": "会创建字符串并用 len、拼接、重复做基本处理",
                        "minutes": 20,
                        "criteria": "能正确使用引号创建字符串，能解释不可变的含义",
                    },
                    {
                        "code": "python-basics-04-k02",
                        "name": "字符串索引与切片",
                        "goal": "会用下标与切片精确取出需要的字符片段",
                        "minutes": 30,
                        "criteria": "能写出取首字符、末字符、前 N 位、后 N 位的正确表达式",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-04-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "测量字符串",
                        "description": "定义字符串 programming，输出长度、第一个字符、最后一个字符。",
                        "answer": 's = "programming"\nprint(len(s))\nprint(s[0])\nprint(s[-1])',
                        "explanation": "len 得长度，下标 0 是首字符，-1 是末字符。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-04-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "手机号脱敏",
                        "description": "把 13812345678 变成 138****5678 的形式。",
                        "answer": 'phone = "13812345678"\nprint(phone[:3] + "*" * 4 + phone[-4:])',
                        "explanation": "前 3 位用切片取，后 4 位用负数切片取，中间用星号乘法生成。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-04-l01-1",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "对 s = \"Python\"，s[1:4] 的结果是？",
                        "options": [
                            ("A", "Pyt"),
                            ("B", "yth"),
                            ("C", "ytho"),
                            ("D", "tho"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "取下标 1、2、3 三个字符，即 y、t、h，终点 4 不包含。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-04-l01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "字符串创建后，可以用 s[0] = \"J\" 直接修改第一个字符。",
                        "answer": {"value": False},
                        "explanation": "字符串不可变，这样的赋值会报 TypeError。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-04-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''word = "Python"
print(word[-1])
print(word[:3])
print(word[3:])''',
                        "answer": {
                            "reference": "依次输出 n、Pyt、hon。负下标取末尾字符，省略起点的切片从头开始，省略终点的切片到末尾结束。",
                            "keywords": ["n", "Pyt", "hon", "切片"],
                        },
                        "explanation": "切片两个边界都可以省略，省略哪边就往哪边延伸。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-04-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "对 s = \"Python\"，访问 s[6] 会发生什么？",
                        "options": [
                            ("A", "返回空字符串"),
                            ("B", "返回 n"),
                            ("C", "报 IndexError"),
                            ("D", "返回 None"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "长度 6 的字符串合法下标是 0 到 5，越界会报 IndexError。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-04-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "给定 s = \"hello world\"，输出前 5 个字符和后 5 个字符。",
                        "answer": {
                            "reference": 's = "hello world"\nprint(s[:5])\nprint(s[-5:])',
                            "keywords": ["s[:5]", "s[-5:]", "print"],
                        },
                        "explanation": "前 5 个用 s[:5]，后 5 个用负数起点 s[-5:]。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-04-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说切片是「含头不含尾」？这样设计有什么好处？",
                        "answer": {
                            "reference": "因为 s[start:end] 只取 start 到 end-1 的位置。好处是 end - start 正好等于取到的字符个数，相邻切片拼接不会重复或遗漏，例如 s[:3] 加 s[3:] 正好还原原字符串。",
                            "keywords": ["end - start", "个数", "不重复", "拼接"],
                        },
                        "explanation": "能说出「长度等于终点减起点」这一性质即达标。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-basics-04-l02",
                "title": "常用字符串方法与 f-string 格式化",
                "description": "用 upper、strip、replace、split、join 处理文本，用 f-string 把变量嵌进句子。",
                "minutes": 55,
                "difficulty": "beginner",
                "objectives": """1. 会调用字符串的 upper、lower、strip、replace、split、join 方法。
2. 会用 f-string 把变量和表达式嵌进字符串。
3. 能区分「方法返回新字符串」和「原地修改」。""",
                "why_learn": """用户输入常常带多余空格、大小写混乱、分隔符不统一。
清洗和拼接是文本处理里最日常的两件事：方法负责清洗，f-string 负责拼出可读的结果。
后面做数据统计、生成报告，几乎每一行输出都离不开 f-string。""",
                "concepts": """- **方法**：字符串自带的功能，用「字符串.方法名(参数)」调用。
- **upper / lower**：转大写 / 转小写。
- **strip**：去掉首尾空白（不含中间）。
- **replace(旧, 新)**：把指定内容替换掉。
- **split(分隔符)**：按分隔符切成列表。
- **join(列表)**：用当前字符串把列表里的内容连起来。
- **f-string**：在字符串前加 f，用大括号把变量或表达式嵌进去。""",
                "plain": """方法是字符串自带的工具箱，你只要说「把这段文字转成大写」，它就还你一个新结果。
注意它还的是新东西，原来的字符串没有变——像把原件复印一份再改复印件。
f-string 则像填空题：先写好句子，把要变动的地方挖成空，再把变量填进去。""",
                "syntax": """s.upper()            转大写
s.lower()            转小写
s.strip()            去掉首尾空白
s.replace("a", "b")  替换
s.split(",")         按逗号切成列表
"-".join(["a", "b"]) 用横线连接成 a-b
f"你好，{name}"      把变量嵌进字符串
f"总价：{price * count:.2f}"  嵌入表达式并保留两位小数""",
                "example_code": '''raw = "  Python 入门  "
print("原始：", repr(raw))
print("去空白：", repr(raw.strip()))

text = "Hello World"
print("大写：", text.upper())
print("小写：", text.lower())
print("替换：", text.replace("World", "Python"))

line = "苹果,香蕉,橘子"
items = line.split(",")
print("切分后：", items)
print("重新连接：", " / ".join(items))

name = "小明"
score = 92.5
print(f"{name} 的成绩是 {score} 分")
print(f"四舍五入后：{score:.0f} 分")''',
                "code_lines": """- 第 1 至 3 行：repr() 会把字符串的真实样子（含空格）显示出来，方便看清 strip 去掉了什么。
- 第 5 至 7 行：转大写、转小写、替换，三者都返回新字符串。
- 第 9 至 11 行：split 按逗号切分成列表（列表第 5 章讲，这里先理解为多个值的集合）。
- 第 12 行：join 用斜杠把列表内容重新连成一串。
- 第 14 至 16 行：f-string 在大括号里放变量，甚至可以直接放表达式与格式说明。""",
                "output": """原始： '  Python 入门  '
去空白： 'Python 入门'
大写： HELLO WORLD
小写： hello world
替换： Hello Python
切分后： ['苹果', '香蕉', '橘子']
重新连接： 苹果 / 香蕉 / 橘子
小明 的成绩是 92.5 分
四舍五入后： 92 分""",
                "mistakes": """1. 以为 raw.strip() 会改掉 raw 本身。
2. 忘记方法要加括号，写成 text.upper。
3. f-string 前漏写字母 f。
4. 在大括号里用引号嵌套出错。
5. split 后不检查结果长度，直接取第 3 个元素导致越界。""",
                "error_analysis": """- raw.strip() 返回新字符串，raw 本身不变。要保留结果必须赋值：raw = raw.strip()。
- 写 text.upper 不加括号，得到的是一个方法对象，输出会显示类似内置方法的说明，而不是大写结果。
- 漏写 f 时，大括号会原样输出成 {name}，因为普通字符串不解析大括号。
- f"{name" 这种括号没闭合会报 SyntaxError，大括号必须成对。
- split 得到的列表长度取决于实际内容，直接取 items[3] 可能报 IndexError。""",
                "beginner_practice": """读入用户输入的一句话，去掉首尾空格、转成小写、把空格替换成下划线，再输出。""",
                "advanced_practice": """给定 "姓名:小明;年龄:18;城市:杭州"，用 split 拆成三组，再用 f-string 输出「小明 今年 18 岁，来自杭州」。""",
                "quiz_note": """本节测验 6 题：2 题考方法与 f-string 的作用，2 题读代码判断输出，2 题写文本清洗与格式化程序。""",
                "summary": """- 字符串方法都返回新字符串，原字符串不变。
- strip 去首尾空白，replace 替换，split 切分，join 拼接。
- f-string 用 f 前缀加大括号嵌变量，可加格式说明控制小数位。
- 处理用户输入时，先 strip 再去判断，能避免大量「看起来一样却不相等」的问题。""",
                "next_lesson": """下一章进入列表：当你要一次保存很多个值时，字符串就不够用了。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-04-k03",
                        "legacy": "python-basics-02-06",
                        "name": "字符串格式化与 f-string",
                        "goal": "会用 f-string 把变量与表达式嵌入文本",
                        "minutes": 25,
                        "criteria": "能写出带变量与小数位控制的 f-string，知道漏写 f 的后果",
                    },
                    {
                        "code": "python-basics-04-k04",
                        "name": "常用字符串方法",
                        "goal": "会用 strip、replace、split、join、upper、lower 处理文本",
                        "minutes": 30,
                        "criteria": "能完成一次「去空白→统一大小写→替换/切分」的文本清洗",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-04-k03-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "成绩播报",
                        "description": "用 f-string 输出「小明 的成绩是 92.5 分」，再输出保留一位小数的版本。",
                        "answer": 'name = "小明"\nscore = 92.5\nprint(f"{name} 的成绩是 {score} 分")\nprint(f"保留一位：{score:.1f}")',
                        "explanation": "大括号里可以放变量，冒号后写格式说明。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-04-k04-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "清洗用户输入",
                        "description": "把「  Hello Python  」去空白并转小写后输出。",
                        "answer": 'raw = "  Hello Python  "\nprint(raw.strip().lower())',
                        "explanation": "方法可以链式调用，前一个的返回值继续调用下一个。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-04-l02-1",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "执行 s = \"  hi  \" 后，s.strip() 的结果是？",
                        "options": [
                            ("A", "hi"),
                            ("B", "  hi  "),
                            ("C", "h i"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "strip 去掉首尾空白，返回新字符串 hi。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-04-l02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "写 f\"{1 + 1}\" 时，大括号里可以放表达式，输出 2。",
                        "answer": {"value": True},
                        "explanation": "f-string 的大括号里可以放任意表达式，会先求值再填入。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-04-l02-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''s = "a,b,c"
parts = s.split(",")
print(len(parts))
print("-".join(parts))''',
                        "answer": {
                            "reference": "第一行输出 3，第二行输出 a-b-c。split 按逗号切成三个元素，join 用横线连接。",
                            "keywords": ["3", "a-b-c", "split", "join"],
                        },
                        "explanation": "split 的返回值是列表，长度即元素个数。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-04-l02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "name = \"小明\"，print(\"{name}\") 的输出是？",
                        "options": [
                            ("A", "小明"),
                            ("B", "{name}"),
                            ("C", "报错"),
                            ("D", "空"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "没有 f 前缀时大括号不被解析，原样输出。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-04-l02-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "把「  Python 入门  」去掉首尾空格、转成大写后输出。",
                        "answer": {
                            "reference": 's = "  Python 入门  "\nprint(s.strip().upper())',
                            "keywords": ["strip", "upper", "print"],
                        },
                        "explanation": "先用 strip 去空白，再链式调用 upper 转大写。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-04-l02-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "为什么处理用户输入时建议先 strip 再比较？举一个会因此出错的例子。",
                        "answer": {
                            "reference": "因为用户输入常带多余空格，直接比较会判为不相等。例如用户输入「 是 」，直接和「是」比较得到 False，strip 后才会相等，导致程序走进错误分支。",
                            "keywords": ["空格", "不相等", "False", "strip"],
                        },
                        "explanation": "能指出「看起来一样但比较为假」的具体后果即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
