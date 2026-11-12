"""第 5—6 章教材内容：列表、元组。"""

CHAPTERS: list[dict] = [
    # ------------------------------------------------------------------ 第 5 章
    {
        "code": "python-basics-05",
        "order_index": 5,
        "title": "列表",
        "description": "一次保存一组有序数据：增删改查、排序取值、嵌套访问，这是后面所有数据处理的底座。",
        "lessons": [
            {
                "code": "python-basics-05-l01",
                "title": "列表的创建与增删改查",
                "description": "创建列表、按下标取值、追加与删除元素，理解列表可变。",
                "minutes": 55,
                "difficulty": "beginner",
                "objectives": """1. 会创建列表并按下标取出元素。
2. 会用 append、insert、remove、pop 做增删。
3. 能说清列表与字符串的关键区别：列表可变，字符串不可变。""",
                "why_learn": """一个班有 40 个学生、一张订单有 8 件商品，用变量一个个存会失控。
列表把所有同类数据装进一个有序的容器，还能随时增删。
后面学循环时，列表就是被遍历的对象；没有列表，循环几乎无处可用。""",
                "concepts": """- **列表**：用方括号包起来、逗号分隔的有序集合，如 ["苹果", "香蕉"]。
- **元素**：列表里的每一项，可以是数字、字符串，甚至另一个列表。
- **下标**：与字符串一致，从 0 开始，-1 表示最后一个。
- **可变**：可以原地追加、修改、删除元素，列表本身还是同一个对象。""",
                "plain": """列表像一个可以随时抽插卡片的文件盒，每张卡片有固定位置。
你可以往末尾塞一张新卡片（append），可以把第 3 张换成别的（按下标赋值），
也可以把某张卡片抽走（remove），盒子还是那个盒子。
字符串则像印好的一页纸，想改内容只能重新印一页。""",
                "syntax": """fruits = ["苹果", "香蕉", "橘子"]   创建
fruits[0]                          取第一个
fruits[-1]                         取最后一个
len(fruits)                        元素个数
fruits.append("葡萄")              末尾追加
fruits.insert(1, "西瓜")           在指定位置插入
fruits.remove("橘子")              按值删除（删第一个匹配项）
fruits.pop()                       删除并返回末尾元素
fruits[1] = "西瓜"                 按下标修改
"苹果" in fruits                   判断是否存在，得到 True 或 False""",
                "example_code": '''fruits = ["苹果", "香蕉", "橘子"]
print("原列表：", fruits)
print("第一个：", fruits[0])
print("最后一个：", fruits[-1])
print("个数：", len(fruits))

fruits.append("葡萄")
print("追加后：", fruits)

fruits[1] = "西瓜"
print("修改后：", fruits)

fruits.remove("橘子")
print("删除后：", fruits)

print("还有香蕉吗：", "香蕉" in fruits)''',
                "code_lines": """- 第 1 行：用方括号创建包含三个元素的列表。
- 第 2 至 5 行：整体输出、按下标取首尾、用 len 数个数。
- 第 7 行：append 在末尾追加一个元素，列表长度变成 4。
- 第 10 行：fruits[1] 是第二个位置，把它改成西瓜。
- 第 13 行：remove 按值删除橘子，列表变回 3 个元素。
- 第 16 行：in 判断某个值是否还在列表里，结果是布尔值。""",
                "output": """原列表： ['苹果', '香蕉', '橘子']
第一个： 苹果
最后一个： 橘子
个数： 3
追加后： ['苹果', '香蕉', '橘子', '葡萄']
修改后： ['苹果', '西瓜', '橘子', '葡萄']
删除后： ['苹果', '西瓜', '葡萄']
还有香蕉吗： False""",
                "mistakes": """1. 用圆括号创建列表，得到的是元组。
2. 下标从 1 开始数。
3. remove 一个不存在的值，报 ValueError。
4. 用 fruits[5] 访问不存在的下标，报 IndexError。
5. 以为 append 会返回新列表，写成 fruits = fruits.append("葡萄")，结果 fruits 变成 None。""",
                "error_analysis": """- 写成 ("苹果", "香蕉") 得到的是元组，元组不能 append，会报 AttributeError。
- 下标从 0 开始，fruits[1] 是第二个元素，不是第一个。
- fruits.remove("西瓜") 在列表里没有西瓜时，报 ValueError: list.remove(x): x not in list。
- 访问超出长度的下标报 IndexError: list index out of range，取之前先用 len 确认范围。
- append 是原地操作、返回 None；写成赋值会把 None 存进变量，之后所有操作都会报错。""",
                "beginner_practice": """创建购物清单列表，依次追加两件商品，删除第一件，最后输出整个清单和商品数量。""",
                "advanced_practice": """创建成绩列表 [88, 95, 72]，把最低分改成 60，追加一个新成绩 100，再输出列表、最高分和总分（可用 max 与 sum）。""",
                "quiz_note": """本节测验 6 题：2 题考列表创建与可变性，2 题读代码判断列表最终内容，2 题写增删改查的实际操作。""",
                "summary": """- 列表用方括号创建，是有序、可变的集合。
- 下标从 0 开始，-1 是最后一个。
- append 追加、insert 插入、remove 按值删、pop 删末尾。
- 列表可变、字符串不可变，这是两者最本质的区别。""",
                "next_lesson": """下一课学列表的排序、反转与嵌套取值，让列表从「存得住」变成「用得上」。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-05-k01",
                        "legacy": "python-basics-06-01",
                        "name": "列表 list",
                        "goal": "会创建列表、按索引取值、判断元素是否存在",
                        "minutes": 25,
                        "criteria": "能正确取出首尾元素，能解释列表可变与字符串不可变的区别",
                    },
                    {
                        "code": "python-basics-05-k02",
                        "name": "列表的增删改查",
                        "goal": "会用 append / insert / remove / pop 与下标赋值维护列表",
                        "minutes": 30,
                        "criteria": "能完成一次「追加、修改、删除」的完整操作并预测最终列表",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-05-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "首尾与数量",
                        "description": "创建 fruits 列表，输出第一个、最后一个元素和元素个数。",
                        "answer": 'fruits = ["苹果", "香蕉", "橘子"]\nprint(fruits[0])\nprint(fruits[-1])\nprint(len(fruits))',
                        "explanation": "下标 0 与 -1 分别取首尾，len 数个数。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-05-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "维护购物清单",
                        "description": "从空列表开始，追加牛奶和面包，再插入鸡蛋到最前面，最后删掉面包。",
                        "answer": 'cart = []\ncart.append("牛奶")\ncart.append("面包")\ncart.insert(0, "鸡蛋")\ncart.remove("面包")\nprint(cart)',
                        "explanation": "insert(0, ...) 插到最前，remove 按值删除。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-05-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "下列哪个写法创建的是列表？",
                        "options": [
                            ("A", "(1, 2, 3)"),
                            ("B", "[1, 2, 3]"),
                            ("C", "{1, 2, 3}"),
                            ("D", "\"1, 2, 3\""),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "方括号是列表，圆括号是元组，花括号是集合，引号是字符串。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-05-l01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "列表创建后可以通过下标赋值修改其中的元素。",
                        "answer": {"value": True},
                        "explanation": "列表是可变类型，nums[0] = 9 是合法操作。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-05-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''nums = [1, 2, 3]
nums.append(4)
nums.remove(2)
print(nums)
print(len(nums))''',
                        "answer": {
                            "reference": "第一行输出 [1, 3, 4]，第二行输出 3。追加 4 后是四个元素，删掉 2 后剩三个。",
                            "keywords": ["[1, 3, 4]", "3", "append", "remove"],
                        },
                        "explanation": "按操作顺序推演列表内容即可。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-05-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "执行 nums = [1, 2]; result = nums.append(3) 后，result 的值是？",
                        "options": [
                            ("A", "[1, 2, 3]"),
                            ("B", "3"),
                            ("C", "None"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "append 原地修改列表，没有返回值，所以 result 是 None。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-05-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "写代码：创建列表 [80, 90, 70]，把最低分改成 60，追加 100，输出最终列表和总和。",
                        "answer": {
                            "reference": 'scores = [80, 90, 70]\nscores[2] = 60\nscores.append(100)\nprint(scores)\nprint(sum(scores))',
                            "keywords": ["scores[2]", "append", "sum"],
                        },
                        "explanation": "70 在下标 2，修改后追加，再用 sum 求和。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-05-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么说列表可变而字符串不可变？各举一个能证明的操作。",
                        "answer": {
                            "reference": "列表可以原地修改元素，如 nums[0] = 9 成功；字符串不能按下标赋值，s[0] = \"x\" 会报 TypeError，只能用拼接生成新字符串。",
                            "keywords": ["原地", "下标赋值", "TypeError", "新字符串"],
                        },
                        "explanation": "能指出「能否原地修改」这一判定标准即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-basics-05-l02",
                "title": "列表排序、统计与嵌套访问",
                "description": "用 sort/reverse 排序、用 max/min/sum 统计、用双层下标取出嵌套数据。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 会用 sort() 与 reverse() 对列表排序和反转。
2. 会用 max、min、sum、len 做基本统计。
3. 能用两层下标从嵌套列表中取出需要的值。""",
                "why_learn": """存下数据只是第一步，真正有用的是回答「最高分是谁」「一共多少」。
排序与统计是数据处理的第一个实用技能，嵌套列表则对应现实里最常见的表格结构：
一行是一个学生，一列是他的姓名和分数。""",
                "concepts": """- **sort()**：原地升序排列，加 reverse=True 变降序。
- **reverse()**：原地把顺序倒过来。
- **max / min / sum**：求最大值、最小值、总和。
- **嵌套列表**：列表的元素本身又是列表，用 list[行][列] 访问。""",
                "plain": """嵌套列表就像一张成绩表：外层列表是「一行行记录」，每一行又是一个小列表，
里面装着姓名和分数。想拿第二行第一列，就说「第 2 行的第 1 个」，写成 table[1][0]。
排序则像把一叠卷子按分数从低到高重新摞好，摞完顺序就变了，不会另生成一叠。""",
                "syntax": """nums.sort()                  原地升序
nums.sort(reverse=True)      原地降序
nums.reverse()               原地反转
max(nums)  min(nums)  sum(nums)
table[1][0]                  第 2 行的第 1 个元素
len(table)                   有几行""",
                "example_code": '''scores = [88, 95, 72, 60]
scores.sort()
print("升序：", scores)

scores.sort(reverse=True)
print("降序：", scores)

print("最高分：", max(scores))
print("最低分：", min(scores))
print("平均分：", sum(scores) / len(scores))

table = [["小明", 92], ["小红", 88], ["小刚", 75]]
print("第一行：", table[0])
print("第一行姓名：", table[0][0])
print("第二行分数：", table[1][1])
print("共几行：", len(table))''',
                "code_lines": """- 第 1 至 3 行：sort() 原地升序，输出从小到大。
- 第 5 至 6 行：加 reverse=True 改成降序，仍是对同一个列表原地排序。
- 第 8 至 10 行：max、min、sum 直接对列表统计，平均分用总和除以个数。
- 第 12 至 16 行：table 的每个元素又是一个列表；table[0] 取第一行，table[0][0] 再取这一行的第一个值。""",
                "output": """升序： [60, 72, 88, 95]
降序： [95, 88, 72, 60]
最高分： 95
最低分： 60
平均分： 78.75
第一行： ['小明', 92]
第一行姓名： 小明
第二行分数： 88
共几行： 3""",
                "mistakes": """1. 写 scores = scores.sort()，结果拿到 None。
2. 以为 sort 返回新列表，其实原地修改。
3. 对含字符串的列表直接 sum，报 TypeError。
4. 嵌套列表只写一层下标，得到整个小列表而不是具体值。
5. 降序误用 sort() 后再 reverse()，多写一步且容易搞混。""",
                "error_analysis": """- sort() 返回 None，赋值会把原列表弄丢。正确写法是直接 scores.sort()，用 scores 本身。
- sum 只接受数字，列表里混入字符串会报 TypeError: unsupported operand type(s)。
- table[0] 得到 ['小明', 92]，要取姓名必须再下一层 table[0][0]。
- sort() 之后再 reverse() 得到的是降序，但 sort(reverse=True) 一步就能完成，更清晰。""",
                "beginner_practice": """创建五个分数，排序后输出最小值和最大值，再输出平均分。""",
                "advanced_practice": """创建三行两列的嵌套列表保存姓名与分数，输出每个人的姓名，并算出总分。""",
                "quiz_note": """本节测验 6 题：2 题考排序与统计函数，2 题读代码判断最终顺序与取值，2 题写嵌套列表的实际处理。""",
                "summary": """- sort() 原地排序，reverse=True 降序，返回值为 None。
- max、min、sum、len 是最常用的四个统计函数。
- 嵌套列表用两层下标访问，先取行再取列。
- 排序会改变原列表顺序，需要保留原顺序时要先复制一份。""",
                "next_lesson": """下一章讲元组：它和列表长得很像，但一旦创建就不能修改，适合保存不该被改动的数据。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-05-k03",
                        "name": "列表排序与统计",
                        "goal": "会用 sort / reverse 与 max / min / sum 处理列表",
                        "minutes": 25,
                        "criteria": "能说明 sort 返回 None，能正确算出平均值",
                    },
                    {
                        "code": "python-basics-05-k04",
                        "name": "嵌套列表与取值",
                        "goal": "能用两层下标访问嵌套列表中的具体数据",
                        "minutes": 25,
                        "criteria": "能写出取第 N 行第 M 列的表达式，能说出 len 数的是行数",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-05-k03-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "成绩统计",
                        "description": "对 [88, 95, 72, 60] 排序后输出最高分、最低分和平均分。",
                        "answer": 'scores = [88, 95, 72, 60]\nscores.sort()\nprint(max(scores))\nprint(min(scores))\nprint(sum(scores) / len(scores))',
                        "explanation": "排序不是必须的，但便于人工核对；平均值用总和除以个数。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-05-k04-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "读取成绩表",
                        "description": "从嵌套列表中输出第二行的姓名和分数。",
                        "answer": 'table = [["小明", 92], ["小红", 88]]\nprint(table[1][0])\nprint(table[1][1])',
                        "explanation": "table[1] 是第二行，再取 [0] 和 [1]。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-05-l02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "执行 nums = [3, 1, 2]; nums.sort() 后，nums 是？",
                        "options": [
                            ("A", "[3, 2, 1]"),
                            ("B", "[1, 2, 3]"),
                            ("C", "None"),
                            ("D", "报错"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "sort 原地升序，nums 本身变成 [1, 2, 3]。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-05-l02-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "对嵌套列表 table 来说，len(table) 得到的是总元素个数（行数乘列数）。",
                        "answer": {"value": False},
                        "explanation": "len 只数最外层元素个数，即行数。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-05-l02-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''table = [["小明", 92], ["小红", 88]]
print(table[0][1])
print(table[1][0])''',
                        "answer": {
                            "reference": "第一行输出 92，第二行输出 小红。table[0][1] 是第一行第二列，table[1][0] 是第二行第一列。",
                            "keywords": ["92", "小红", "行", "列"],
                        },
                        "explanation": "先定位行，再定位列，顺序不能颠倒。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-05-l02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "想要降序排列，正确的写法是？",
                        "options": [
                            ("A", "nums.sort(reverse=True)"),
                            ("B", "nums.sort(True)"),
                            ("C", "nums.reverse()"),
                            ("D", "nums.desc()"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "sort 的 reverse 参数设为 True 即为降序；reverse() 只是把当前顺序倒过来，不排序。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-05-l02-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "创建三行两列的列表保存三个人的姓名与分数，输出第三个人的姓名，并输出总分。",
                        "answer": {
                            "reference": 'table = [["小明", 92], ["小红", 88], ["小刚", 75]]\nprint(table[2][0])\nprint(table[0][1] + table[1][1] + table[2][1])',
                            "keywords": ["table[2][0]", "table[0][1]", "总分"],
                        },
                        "explanation": "第三个人下标是 2；总分逐一取分数相加（学完循环后可改用循环）。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-05-l02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么 nums = nums.sort() 会把列表弄丢？应该怎么写？",
                        "answer": {
                            "reference": "因为 sort() 原地排序、返回 None，赋值后 nums 变成 None。应该直接调用 nums.sort()，不要再赋值。",
                            "keywords": ["None", "原地", "返回值", "直接调用"],
                        },
                        "explanation": "凡是在原地修改的方法，都不该用赋值接返回值。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ------------------------------------------------------------------ 第 6 章
    {
        "code": "python-basics-06",
        "order_index": 6,
        "title": "元组",
        "description": "不可变的有序序列：什么时候该用它、怎么解包、为什么它比列表更适合保存固定数据。",
        "lessons": [
            {
                "code": "python-basics-06-l01",
                "title": "元组：不可变序列与解包",
                "description": "创建元组、理解不可变的意义、用解包一次取出多个值。",
                "minutes": 45,
                "difficulty": "beginner",
                "objectives": """1. 会用圆括号创建元组，知道单元素元组必须带逗号。
2. 能解释元组不可变的含义与好处。
3. 会用解包把元组里的值一次赋给多个变量。""",
                "why_learn": """有些数据天生不该被改：坐标、颜色值、一条记录的固定字段、函数的多个返回值。
用元组表达它们，等于给数据加了一层「只读」保护，读代码的人一眼就知道这里不会被改。
它也是后面数据库查询结果、多返回值场景的默认结构。""",
                "concepts": """- **元组**：用圆括号包起来的有序序列，创建后不能增删改。
- **不可变**：不能按下标赋值，不能 append 或 remove。
- **单元素元组**：必须写成 (5,)，只写 (5) 得到的是整数 5。
- **解包**：把元组里的值按顺序分配给多个变量。""",
                "plain": """列表像可擦写的白板，元组像刻好的石板：内容固定，想改只能换一块新的。
石板的好处是不会被误改——你把坐标 (3, 5) 交给别人，不用担心对方半路把它改成 (0, 0)。
解包则像一次性把袋子里的东西按顺序分给几个人，一人拿一样。""",
                "syntax": """point = (3, 5)        创建元组
point[0]              取值，得到 3
len(point)            长度，得到 2
single = (5,)         单元素元组，逗号不能省
x, y = point          解包，x 是 3，y 是 5
a, b = b, a           交换两个变量的值""",
                "example_code": '''point = (3, 5)
print("坐标：", point)
print("横坐标：", point[0])
print("长度：", len(point))

name, age = ("小明", 18)
print("姓名：", name)
print("年龄：", age)

x = 1
y = 2
x, y = y, x
print("交换后：", x, y)

single = (5,)
print("单元素元组：", single, "类型：", type(single))

not_tuple = (5)
print("不加逗号：", not_tuple, "类型：", type(not_tuple))''',
                "code_lines": """- 第 1 至 4 行：创建二元组，用下标取值、用 len 取长度。
- 第 6 至 8 行：解包，把元组第一个值给 name，第二个值给 age。
- 第 10 至 13 行：利用元组解包交换两个变量，不需要中间变量。
- 第 15 行：单元素元组必须带逗号，type 显示为 tuple。
- 第 17 至 18 行：只写 (5) 时括号只起分组作用，得到的是 int。""",
                "output": """坐标： (3, 5)
横坐标： 3
长度： 2
姓名： 小明
年龄： 18
交换后： 2 1
单元素元组： (5,) 类型： <class 'tuple'>
不加逗号： 5 类型： <class 'int'>""",
                "mistakes": """1. 把单元素元组写成 (5)，得到整数。
2. 试图修改元组元素，写 point[0] = 10。
3. 解包时变量个数与元素个数不一致。
4. 用圆括号创建列表，后面调 append 报错。
5. 误以为元组完全不能改：元组里的列表元素本身仍可变。""",
                "error_analysis": """- (5) 只是加了括号的整数，要得到元组必须写 (5,)。
- point[0] = 10 报 TypeError: 'tuple' object does not support item assignment，这是元组的保护机制。
- a, b = (1, 2, 3) 报 ValueError: too many values to unpack，变量个数必须与元素个数一致。
- 元组不能 append，会报 AttributeError: 'tuple' object has no attribute 'append'。
- 元组不可变指的是「不能换掉它保存的引用」；如果某个元素是列表，列表内部仍可修改，这一点在进阶阶段要特别注意。""",
                "beginner_practice": """创建保存宽和高的元组，解包成两个变量，输出面积。""",
                "advanced_practice": """创建三个坐标元组组成的列表，用解包分别取出每个坐标的 x 与 y，输出它们的和（提示：先取 table[0] 这样的单个元组再解包）。""",
                "quiz_note": """本节测验 6 题：2 题考元组创建与不可变，2 题读代码判断类型与取值，2 题写解包与交换变量的代码。""",
                "summary": """- 元组用圆括号创建，有序且不可变。
- 单元素元组必须带逗号。
- 解包能一次取出多个值，交换变量最典型。
- 保存不该被修改的数据时优先用元组。""",
                "next_lesson": """下一章讲集合：当你要去重或判断「在不在」时，集合比列表快得多。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-06-k01",
                        "legacy": "python-basics-06-02",
                        "name": "元组 tuple",
                        "goal": "会创建元组、取值，并解释不可变的含义",
                        "minutes": 25,
                        "criteria": "能说明单元素元组的写法，能解释为什么元组不能赋值修改",
                    },
                    {
                        "code": "python-basics-06-k02",
                        "name": "元组解包与多值赋值",
                        "goal": "会用解包一次取出多个值并交换变量",
                        "minutes": 20,
                        "criteria": "能写出 a, b = b, a 并说明执行过程",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-06-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "矩形面积",
                        "description": "用元组保存宽 4 和高 6，解包后输出面积。",
                        "answer": 'size = (4, 6)\nwidth, height = size\nprint(width * height)',
                        "explanation": "解包后两个变量分别对应宽和高。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-06-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "交换变量",
                        "description": "用一行解包交换 a=10 与 b=20 的值。",
                        "answer": "a = 10\nb = 20\na, b = b, a\nprint(a, b)",
                        "explanation": "右侧先构成元组 (20, 10)，再依次赋给 a、b。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-06-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "创建只含一个元素 5 的元组，正确写法是？",
                        "options": [
                            ("A", "(5)"),
                            ("B", "(5,)"),
                            ("C", "[5]"),
                            ("D", "{5}"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "单元素元组必须带逗号，否则括号只起分组作用。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-06-l01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "元组创建后不能修改其中的元素，也不能追加新元素。",
                        "answer": {"value": True},
                        "explanation": "元组不可变，没有 append，也不能按下标赋值。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-06-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''a = 1
b = 2
a, b = b, a
print(a, b)''',
                        "answer": {
                            "reference": "输出 2 1。右侧先组成元组 (2, 1)，再依次赋给 a 和 b，完成交换。",
                            "keywords": ["2 1", "元组", "解包"],
                        },
                        "explanation": "交换不需要中间变量，靠的是右侧先求值。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-06-l01-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "type((5)) 的结果是？",
                        "options": [
                            ("A", "tuple"),
                            ("B", "int"),
                            ("C", "list"),
                            ("D", "str"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "没有逗号的括号只是分组，5 是整数。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-06-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "用元组保存姓名和年龄，解包成两个变量后输出「小明 18」。",
                        "answer": {
                            "reference": 'info = ("小明", 18)\nname, age = info\nprint(name, age)',
                            "keywords": ["解包", "name", "age", "print"],
                        },
                        "explanation": "解包后两个变量分别拿到姓名和年龄。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-06-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "什么数据适合用元组而不是列表保存？说出两条判断依据。",
                        "answer": {
                            "reference": "一是数据不该被修改，如坐标、颜色值、配置常量；二是需要作为整体传递且希望避免误改。元组的不可变特性能把「只读」意图写进代码。",
                            "keywords": ["不可变", "只读", "坐标", "避免误改"],
                        },
                        "explanation": "能落到「不该改」与「防止误改」两点即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
]
