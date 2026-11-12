"""第 7—8 章教材内容：集合、字典。"""

CHAPTERS: list[dict] = [
    # ------------------------------------------------------------------ 第 7 章
    {
        "code": "python-basics-07",
        "order_index": 7,
        "title": "集合",
        "description": "去重、判断存在、做交并差：集合解决的是「有哪些、有没有、重复没有」这类问题。",
        "lessons": [
            {
                "code": "python-basics-07-l01",
                "title": "集合：去重与集合运算",
                "description": "创建集合、给列表去重、用 in 判断存在，做交集并集差集。",
                "minutes": 45,
                "difficulty": "beginner",
                "objectives": """1. 会创建集合，知道集合元素唯一且无序。
2. 会用 set() 给列表去重。
3. 会用 | & - 求并集、交集、差集。""",
                "why_learn": """统计「有多少个不同的城市」「两个人共同关注了谁」「哪些词只在这一篇里出现」，
本质都是去重与集合运算。用列表硬做要写很多重复判断，用集合一行就够。""",
                "concepts": """- **集合**：用花括号包起来的无序、不重复的数据集合。
- **去重**：把列表转成集合，重复元素自动合并。
- **成员判断**：用 in 判断某个值在不在集合里。
- **集合运算**：并集 |、交集 &、差集 -。""",
                "plain": """集合像一个自动去重的登记处：同一个名字登记两次，名单上仍然只有一个。
它不关心谁排第一，只关心「谁在名单里」。
所以集合适合回答「有没有」「有几个不同的」，不适合回答「第几个是谁」——那要用列表。""",
                "syntax": """s = {"苹果", "香蕉"}      创建集合
empty = set()            创建空集合（{} 是空字典）
set([1, 2, 2, 3])        列表去重，得到 {1, 2, 3}
"苹果" in s              判断存在
a | b                    并集
a & b                    交集
a - b                    差集（在 a 不在 b）
len(s)                   元素个数""",
                "example_code": '''fruits = {"苹果", "香蕉", "苹果"}
print("集合自动去重：", fruits)
print("元素个数：", len(fruits))
print("有香蕉吗：", "香蕉" in fruits)

names = ["小明", "小红", "小明", "小刚"]
unique_names = set(names)
print("原始列表：", names)
print("去重后：", unique_names)
print("不同的人有：", len(unique_names), "个")

a = {"数学", "语文", "英语"}
b = {"数学", "物理"}
print("都选的：", a & b)
print("所有科目：", a | b)
print("只选 a 的：", a - b)''',
                "code_lines": """- 第 1 行：花括号里写了两个苹果，集合自动只保留一个。
- 第 2 至 3 行：len 数的是去重后的个数；in 判断元素是否在集合中。
- 第 5 至 8 行：列表转集合后去重，元素个数从 4 变成 3。
- 第 10 至 13 行：& 取两边都有的科目，| 取所有出现过的科目，- 取只在 a 中出现的科目。""",
                "output": """集合自动去重： {'苹果', '香蕉'}
元素个数： 2
有香蕉吗： True
原始列表： ['小明', '小红', '小明', '小刚']
去重后： {'小明', '小红', '小刚'}
不同的人有： 3 个
都选的： {'数学'}
所有科目： {'数学', '语文', '英语', '物理'}
只选 a 的： {'语文', '英语'}""",
                "mistakes": """1. 用 {} 创建空集合，得到的是空字典。
2. 以为集合能按下标取值，写 s[0]。
3. 把列表放进集合，报不可哈希错误。
4. 以为集合输出顺序固定，每次运行可能不同。
5. 用 set 去重后还想保留原顺序。""",
                "error_analysis": """- 空集合必须写 set()；{} 在 Python 里表示空字典，两者不是一回事。
- 集合无序，没有下标，s[0] 报 TypeError: 'set' object is not subscriptable。
- 列表是可变类型、不可哈希，放进集合报 TypeError: unhashable type: 'list'；要放就先转成元组。
- 集合的打印顺序不保证与书写顺序一致，不要依赖它做顺序判断。
- set 会打乱顺序，需要「去重且保序」时不能用它直接转。""",
                "beginner_practice": """把列表 ["北京", "上海", "北京", "广州", "上海"] 去重，输出去重后的集合和城市个数。""",
                "advanced_practice": """给定两个列表分别表示两个人关注的标签，用集合运算输出他们共同关注的标签和所有标签。""",
                "quiz_note": """本节测验 6 题：2 题考集合特性与空集合写法，2 题读代码判断结果，2 题写去重与集合运算。""",
                "summary": """- 集合无序、元素唯一，用花括号创建，空集合写 set()。
- 列表转集合即可去重，但会丢失原顺序。
- in 判断存在，比列表更快。
- | 并集、& 交集、- 差集。""",
                "next_lesson": """下一章讲字典：它用「键」而不是位置来存数据，是最贴近现实记录的结构。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-07-k01",
                        "legacy": "python-basics-06-04",
                        "name": "集合 set",
                        "goal": "会创建集合、去重并判断元素是否存在",
                        "minutes": 25,
                        "criteria": "能写出 set() 去重的代码，能解释集合无序与元素唯一",
                    },
                    {
                        "code": "python-basics-07-k02",
                        "name": "集合运算",
                        "goal": "会用并集、交集、差集解决实际问题",
                        "minutes": 20,
                        "criteria": "能根据需求选出正确的集合运算符并预测结果",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-07-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "城市去重",
                        "description": "把含重复项的城市列表去重，输出集合与个数。",
                        "answer": 'cities = ["北京", "上海", "北京", "广州"]\nunique = set(cities)\nprint(unique)\nprint(len(unique))',
                        "explanation": "set() 自动合并重复元素。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-07-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "共同关注",
                        "description": "两个用户关注的标签分别是 {A, B, C} 与 {B, C, D}，输出共同关注与全部标签。",
                        "answer": 'u1 = {"A", "B", "C"}\nu2 = {"B", "C", "D"}\nprint(u1 & u2)\nprint(u1 | u2)',
                        "explanation": "交集 & 得共同项，并集 | 得全部项。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-07-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要得到一个空的集合，应该怎样写？",
                        "options": [
                            ("A", "{}"),
                            ("B", "set()"),
                            ("C", "[]"),
                            ("D", "()"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "{} 是空字典，空集合只能用 set()。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-07-l01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "集合中的元素有固定顺序，可以用下标 s[0] 取值。",
                        "answer": {"value": False},
                        "explanation": "集合无序，不支持下标访问。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-07-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''a = {1, 2, 3}
b = {3, 4}
print(a & b)
print(len(a | b))''',
                        "answer": {
                            "reference": "第一行输出 {3}，第二行输出 4。交集只有 3，并集是 {1, 2, 3, 4} 共 4 个元素。",
                            "keywords": ["{3}", "4", "交集", "并集"],
                        },
                        "explanation": "交集取公共元素，并集合并去重。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-07-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "a = {1, 2, 3}，b = {2, 3, 4}，a - b 的结果是？",
                        "options": [
                            ("A", "{1}"),
                            ("B", "{4}"),
                            ("C", "{2, 3}"),
                            ("D", "{1, 4}"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "差集是在 a 中但不在 b 中的元素，只有 1。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-07-l01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "把列表 [\"A\", \"B\", \"A\", \"C\"] 去重并输出元素个数。",
                        "answer": {
                            "reference": 'items = ["A", "B", "A", "C"]\nunique = set(items)\nprint(len(unique))',
                            "keywords": ["set", "len", "unique"],
                        },
                        "explanation": "去重后剩 3 个不同元素。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-07-l01-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "什么场景适合用集合而不是列表？说出两个判断依据。",
                        "answer": {
                            "reference": "需要去重时（如统计不同城市）；需要频繁判断某个值是否存在、且不关心顺序时（如黑名单校验）。集合的成员判断更快，但不保序。",
                            "keywords": ["去重", "存在", "顺序", "更快"],
                        },
                        "explanation": "能落到「去重」与「不关心顺序的存在判断」即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ------------------------------------------------------------------ 第 8 章
    {
        "code": "python-basics-08",
        "order_index": 8,
        "title": "字典",
        "description": "用键值对描述一条记录：存、取、改、删与嵌套，是后面处理 JSON 和接口数据的直接基础。",
        "lessons": [
            {
                "code": "python-basics-08-l01",
                "title": "字典的键值结构与增删改查",
                "description": "创建字典、用键取值、安全取值、新增修改与删除键值对。",
                "minutes": 55,
                "difficulty": "beginner",
                "objectives": """1. 会创建字典，理解键与值的对应关系。
2. 会用 [] 与 get() 取值，并说出两者的区别。
3. 会新增、修改、删除键值对，判断键是否存在。""",
                "why_learn": """列表靠位置找数据，可你更常说「查小明的成绩」而不是「查第 2 行」。
字典用键来定位值，一条记录里字段再多也能按名字取。
第 17 章的 JSON、后面的接口返回值，本质都是字典或字典的嵌套，这节是那条路的第一步。""",
                "concepts": """- **字典**：用花括号创建的键值对集合，如 {"name": "小明", "age": 18}。
- **键（key）**：唯一的标签，必须是不可变类型，常用字符串。
- **值（value）**：键对应的数据，可以是任意类型。
- **取值**：d["name"] 直接取，键不存在会报错；d.get("name") 键不存在返回 None。""",
                "plain": """字典像一本通讯录：你不需要知道某人在第几页第几行，
只要报出名字（键），就能翻到电话（值）。
名字不能重复，否则就不知道翻哪一条；而电话可以重复。
这就是字典的核心规则：键唯一，值随意。""",
                "syntax": """student = {"name": "小明", "age": 18}
student["name"]              按键取值
student.get("score")         安全取值，键不存在返回 None
student.get("score", 0)      键不存在时返回指定默认值
student["score"] = 95        键不存在则新增，存在则修改
"age" in student             判断键是否存在
del student["age"]           删除键值对
len(student)                 键值对个数""",
                "example_code": '''student = {"name": "小明", "age": 18, "city": "杭州"}
print("完整字典：", student)
print("姓名：", student["name"])
print("年龄：", student.get("age"))
print("分数（不存在）：", student.get("score"))
print("分数（带默认值）：", student.get("score", 0))

student["score"] = 95
print("新增分数后：", student)

student["age"] = 19
print("修改年龄后：", student)

del student["city"]
print("删除城市后：", student)
print("还有城市吗：", "city" in student)''',
                "code_lines": """- 第 1 行：三个键值对，键分别是 name、age、city。
- 第 3 行：用方括号按键取值，取到小明。
- 第 4 至 6 行：get 在键不存在时不会报错，返回 None 或指定的默认值 0。
- 第 8 行：给不存在的键赋值就是新增，字典多了一对 score 与 95。
- 第 11 行：给已存在的键赋值就是修改，年龄从 18 变 19。
- 第 14 至 15 行：del 删除整个键值对，再用 in 确认键已经不在。""",
                "output": """完整字典： {'name': '小明', 'age': 18, 'city': '杭州'}
姓名： 小明
年龄： 18
分数（不存在）： None
分数（带默认值）： 0
新增分数后： {'name': '小明', 'age': 18, 'city': '杭州', 'score': 95}
修改年龄后： {'name': '小明', 'age': 19, 'city': '杭州', 'score': 95}
删除城市后： {'name': '小明', 'age': 19, 'score': 95}
还有城市吗： False""",
                "mistakes": """1. 用不存在的键直接取值，报 KeyError。
2. 把键写成变量名不加引号，写成 student[name]。
3. 用列表当键，报不可哈希错误。
4. 以为 get 会往字典里新增键。
5. 删除不存在的键，报 KeyError。""",
                "error_analysis": """- student["phone"] 在键不存在时报 KeyError: 'phone'；不确定时用 get。
- student[name] 会把 name 当成变量去求值，变量没定义就报 NameError；键是字符串时必须加引号。
- 列表可变、不可哈希，作为键报 TypeError: unhashable type: 'list'。
- get 只读取不写入，student.get("score", 0) 之后字典里仍然没有 score 这个键。
- del student["phone"] 在键不存在时报 KeyError，删之前先用 in 判断。""",
                "beginner_practice": """创建一个保存书名、作者、价格的字典，输出作者，新增「出版社」字段，再把价格改掉，最后输出整个字典。""",
                "advanced_practice": """创建学生字典，用 get 读取一个不存在的键并给出默认值 0，然后用 in 判断该键是否存在，最后决定是否新增它。""",
                "quiz_note": """本节测验 6 题：2 题考键值规则与 get 的作用，2 题读代码判断字典最终内容，2 题写增删改查的实际操作。""",
                "summary": """- 字典用键值对保存数据，键唯一且必须不可变。
- 方括号取值键不存在会报错，get 不会。
- 给已有键赋值是修改，给新键赋值是新增。
- del 删除键值对，in 判断键是否存在。""",
                "next_lesson": """下一课学字典的嵌套、键值视图与真实场景用法，把字典用到「一条记录、一组配置」上。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-08-k01",
                        "legacy": "python-basics-06-03",
                        "name": "字典 dict",
                        "goal": "理解键值对结构，会按键取值",
                        "minutes": 25,
                        "criteria": "能解释键唯一与键必须不可变，能正确取值",
                    },
                    {
                        "code": "python-basics-08-k02",
                        "name": "字典的增删改查",
                        "goal": "会用 get、赋值、del、in 维护字典",
                        "minutes": 30,
                        "criteria": "能预测一次增删改之后字典的完整内容",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-08-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "读取书籍信息",
                        "description": "创建含书名、作者、价格的字典，输出作者和价格。",
                        "answer": 'book = {"title": "Python 入门", "author": "小码", "price": 59}\nprint(book["author"])\nprint(book["price"])',
                        "explanation": "用字符串键直接取值。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-08-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "维护库存",
                        "description": "字典「苹果: 3」，新增香蕉 5 个，把苹果改成 2 个，删掉香蕉，输出最终字典。",
                        "answer": 'stock = {"苹果": 3}\nstock["香蕉"] = 5\nstock["苹果"] = 2\ndel stock["香蕉"]\nprint(stock)',
                        "explanation": "新键赋值即新增，旧键赋值即修改，del 删除。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-08-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "关于字典的键，下列说法正确的是？",
                        "options": [
                            ("A", "键可以重复"),
                            ("B", "键必须是字符串"),
                            ("C", "键必须唯一且不可变"),
                            ("D", "键可以是列表"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "键必须唯一且可哈希，常用字符串，但也可以是数字或元组。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-08-l01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "d.get(\"score\", 0) 在 score 不存在时会把 score 加入字典并设为 0。",
                        "answer": {"value": False},
                        "explanation": "get 只读取，不会修改字典。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-08-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''d = {"a": 1}
d["b"] = 2
d["a"] = 3
print(d)
print(len(d))''',
                        "answer": {
                            "reference": "输出 {'a': 3, 'b': 2} 和 2。新键 b 新增，旧键 a 被改成 3，共两个键值对。",
                            "keywords": ["'a': 3", "'b': 2", "2"],
                        },
                        "explanation": "区分新增与修改，len 数的是键值对个数。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-08-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "d = {\"x\": 1}，执行 d[\"y\"] 会发生什么？",
                        "options": [
                            ("A", "返回 None"),
                            ("B", "返回 0"),
                            ("C", "报 KeyError"),
                            ("D", "自动新增 y"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "方括号取值时键不存在会直接报错，需要安全取值请用 get。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-08-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "创建书籍字典，输出作者，新增「出版社」为「小码出版社」，把价格改为 49，输出最终字典。",
                        "answer": {
                            "reference": 'book = {"title": "Python 入门", "author": "小码", "price": 59}\nprint(book["author"])\nbook["publisher"] = "小码出版社"\nbook["price"] = 49\nprint(book)',
                            "keywords": ["book[", "publisher", "price", "print"],
                        },
                        "explanation": "新键赋值新增，旧键赋值修改。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-08-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么字典的键不能用列表？可以换成什么？",
                        "answer": {
                            "reference": "因为列表是可变类型、不可哈希，而字典靠哈希值定位键。可以换成元组，元组不可变、可哈希。",
                            "keywords": ["可变", "哈希", "元组", "不可变"],
                        },
                        "explanation": "能说出「可变类型不可哈希」即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-basics-08-l02",
                "title": "字典的嵌套与常用场景",
                "description": "用嵌套字典描述一条完整记录，掌握 keys/values/items 与配置式写法。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 会用嵌套字典保存一条多层记录并逐层取值。
2. 会用 keys()、values()、items() 拿到字典的三个视图。
3. 能判断什么时候用字典、什么时候用列表。""",
                "why_learn": """现实中的一条数据往往分层：一个学生有姓名、联系方式、成绩列表。
嵌套字典能原样表达这种结构，第 17 章的 JSON、之后接口返回的数据都是这个形状。
掌握它，你就能读懂绝大多数真实数据。""",
                "concepts": """- **嵌套字典**：字典的值又是一个字典。
- **逐层取值**：d["contact"]["email"]，先取外层键再取内层键。
- **keys / values / items**：分别拿到所有键、所有值、所有键值对。
- **列表与字典的分工**：多条同类记录用列表装，一条记录内的字段用字典装。""",
                "plain": """嵌套字典像一份档案袋：外层写着「学生」，打开里面有「基本信息」和「联系方式」两个小袋子，
再打开「联系方式」才能拿到邮箱。
所以取值要一层层打开，少开一层拿到的是整个小袋子，而不是里面的东西。""",
                "syntax": """student = {
    "name": "小明",
    "contact": {"email": "ming@example.com", "city": "杭州"},
}
student["contact"]["email"]     逐层取值
student.keys()                  所有键
student.values()                所有值
student.items()                 所有键值对
"contact" in student            判断外层键是否存在""",
                "example_code": '''student = {
    "name": "小明",
    "age": 18,
    "contact": {"email": "ming@example.com", "city": "杭州"},
    "scores": [92, 88, 95],
}

print("姓名：", student["name"])
print("城市：", student["contact"]["city"])
print("邮箱：", student["contact"]["email"])
print("第一门成绩：", student["scores"][0])

print("所有键：", list(student.keys()))
print("所有值：", list(student.values()))
print("键值对数量：", len(student.items()))

print("联系方式：", student.get("contact", {}).get("phone", "未填写"))''',
                "code_lines": """- 第 1 至 6 行：外层字典有四个键，其中 contact 的值是字典，scores 的值是列表。
- 第 8 至 9 行：普通键直接取。
- 第 10 至 11 行：先取 contact 得到内层字典，再取 city 与 email。
- 第 12 行：scores 是列表，取第一个成绩要用下标。
- 第 14 至 16 行：keys、values、items 返回视图对象，用 list 转成列表便于查看。
- 第 18 行：连续两次 get，第一层没有 contact 时返回空字典，避免直接报错。""",
                "output": """姓名： 小明
城市： 杭州
邮箱： ming@example.com
第一门成绩： 92
所有键： ['name', 'age', 'contact', 'scores']
所有值： ['小明', 18, {'email': 'ming@example.com', 'city': '杭州'}, [92, 88, 95]]
键值对数量： 4
联系方式： 未填写""",
                "mistakes": """1. 少写一层键，直接把内层字典当值输出。
2. 对不存在的内层键直接取值，报 KeyError。
3. 用 items() 后忘记它是键值对，当成单个值处理。
4. 键名拼错，比如把 email 写成 mail。
5. 该用列表存多条记录时用了字典，导致键重复覆盖。""",
                "error_analysis": """- student["contact"] 得到的是整个内层字典，不是邮箱；要继续取 ["email"] 才是邮箱。
- student["contact"]["phone"] 在内层没有 phone 时报 KeyError，可以改用 get 并提供默认值。
- 键名拼错时不会报「拼错」，只会报 KeyError，所以要仔细核对键名。
- 用字典存多个学生时，后一个会覆盖前一个同名键，多条记录应该放进列表。""",
                "beginner_practice": """创建嵌套字典保存一个人的姓名和联系方式（邮箱、城市），输出邮箱与城市。""",
                "advanced_practice": """在嵌套字典中再加一个成绩列表，输出第一门与最后一门成绩，并计算总分；再用 get 安全读取一个不存在的电话字段。""",
                "quiz_note": """本节测验 6 题：2 题考嵌套结构与视图方法，2 题读代码判断取值结果，2 题写嵌套字典的构建与读取。""",
                "summary": """- 嵌套字典用来表达分层的真实记录。
- 取值要逐层进行，少一层拿到的是子字典。
- keys、values、items 分别取键、值、键值对。
- 多条同类记录用列表装，单条记录的字段用字典装。""",
                "next_lesson": """下一章进入条件判断：程序第一次可以根据不同情况走不同分支。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-08-k03",
                        "name": "字典的键值视图",
                        "goal": "会用 keys / values / items 获取字典的三个视图",
                        "minutes": 20,
                        "criteria": "能说出三个方法各自返回什么，并能转成列表查看",
                    },
                    {
                        "code": "python-basics-08-k04",
                        "name": "嵌套字典与记录建模",
                        "goal": "会用嵌套字典表达一条多层记录并逐层取值",
                        "minutes": 30,
                        "criteria": "能写出两层键的取值表达式，能用 get 安全读取缺失字段",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-08-k03-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "查看三个视图",
                        "description": "对含 a 与 b 两个键的字典，分别输出所有键、所有值、所有键值对。",
                        "answer": 'd = {"a": 1, "b": 2}\nprint(list(d.keys()))\nprint(list(d.values()))\nprint(list(d.items()))',
                        "explanation": "三个视图转成列表后便于观察内容。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-08-k04-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "读取联系方式",
                        "description": "从嵌套字典中输出邮箱，并用 get 安全读取电话（不存在时返回「未填写」）。",
                        "answer": 'student = {"name": "小明", "contact": {"email": "ming@example.com"}}\nprint(student["contact"]["email"])\nprint(student["contact"].get("phone", "未填写"))',
                        "explanation": "内层不存在 phone，get 返回默认值而不报错。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-08-l02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "d.keys() 返回的是什么？",
                        "options": [
                            ("A", "所有值的列表"),
                            ("B", "所有键的视图对象"),
                            ("C", "键值对的列表"),
                            ("D", "字典的长度"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "keys 返回键的视图对象，可用 list 转成列表。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-08-l02-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "多条同类记录（如多个学生）最适合用一个字典保存，键用学生姓名。",
                        "answer": {"value": False},
                        "explanation": "多条记录应用列表装，每条记录是字典；用字典会因键重复而覆盖。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-08-l02-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''d = {"user": {"name": "小明", "tags": ["a", "b"]}}
print(d["user"]["name"])
print(d["user"]["tags"][1])''',
                        "answer": {
                            "reference": "第一行输出 小明，第二行输出 b。先取 user 子字典，再按 name 取值；tags 是列表，取下标 1 得第二个元素。",
                            "keywords": ["小明", "b", "子字典", "列表"],
                        },
                        "explanation": "嵌套结构要按层取，列表还要再加下标。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-08-l02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "len(d.items()) 得到的是什么？",
                        "options": [
                            ("A", "键的个数"),
                            ("B", "值的个数"),
                            ("C", "键值对的个数"),
                            ("D", "字典占用的字节数"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "items 是键值对集合，长度即键值对数量，与键数相同。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-08-l02-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "创建嵌套字典保存姓名与联系方式（邮箱、城市），输出城市，并安全读取电话（默认「未填写」）。",
                        "answer": {
                            "reference": 'student = {"name": "小明", "contact": {"email": "a@b.com", "city": "杭州"}}\nprint(student["contact"]["city"])\nprint(student["contact"].get("phone", "未填写"))',
                            "keywords": ["contact", "city", "get", "未填写"],
                        },
                        "explanation": "两层取值用两个方括号，缺失字段用 get 兜底。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-08-l02-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "要保存一个班的 40 个学生，每个学生有姓名和三门成绩，应该怎样组合列表与字典？",
                        "answer": {
                            "reference": "用列表装 40 条记录，每条记录是一个字典，字典里用 name 存姓名、scores 存成绩列表。即 students = [{\"name\": ..., \"scores\": [...]}, ...]。",
                            "keywords": ["列表", "字典", "scores", "嵌套"],
                        },
                        "explanation": "外层列表解决「多条」，内层字典解决「字段」，这是最通用的建模方式。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
