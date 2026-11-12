"""教材补充题：每章一道「多选」题（阶段 3）。

教材正文的每节课固定是 2 道基础理解 + 2 道代码阅读 + 2 道应用练习，
其中基础理解由单选与判断组成。为了覆盖需求里要求的六种题型
（单选 / 多选 / 判断 / 代码理解 / 代码补全 / 编程思路分析），
这里为每章首节额外补一道多选题，仍计入「基础理解」。

独立成文件而不是塞进各章正文，是为了让补充题一目了然、
也方便后续按章节增删；汇总逻辑在 ``app.seed.textbook.__init__``。
"""

MULTI_CHOICE: dict[str, list[dict]] = {
    "python-basics-01-l01": [
        {
            "code": "q-pb-01-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于运行 Python 程序，下列哪些说法是正确的？（多选）",
            "options": [
                ("A", "一个以 .py 结尾的文件可以用 python 命令直接运行"),
                ("B", 'print("你好") 会把「你好」显示在屏幕上'),
                ("C", "Python 代码必须先编译成 exe 文件才能运行"),
                ("D", "在交互式环境里输入一行代码，可以马上看到结果"),
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": (
                "Python 是解释型语言，保存成 .py 后用 python 命令即可运行，"
                "不需要先编译成 exe，所以 C 错；其余三项都是日常真实的运行方式。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-02-l01": [
        {
            "code": "q-pb-02-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "下列哪些名字可以作为合法的变量名？（多选）",
            "options": [
                ("A", "user_name"),
                ("B", "2ndScore"),
                ("C", "_total"),
                ("D", "class"),
            ],
            "answer": {"values": ["A", "C"]},
            "explanation": (
                "变量名不能以数字开头，所以 B 错；class 是 Python 的关键字，"
                "有专门含义，不能拿来当变量名，所以 D 错；"
                "字母、下划线开头都合法，A、C 正确。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-03-l01": [
        {
            "code": "q-pb-03-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "下列哪些表达式的结果是 True？（多选）",
            "options": [
                ("A", "3 + 2 == 5"),
                ("B", '"5" == 5'),
                ("C", "10 % 3 == 1"),
                ("D", "2 > 3 or 1 < 2"),
            ],
            "answer": {"values": ["A", "C", "D"]},
            "explanation": (
                'A 中 3 + 2 得 5，相等为 True；B 是字符串与整数比较，类型不同直接为 False；'
                "C 中 10 % 3 余 1，为 True；D 用 or，只要右边 1 < 2 成立整体就是 True。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-04-l01": [
        {
            "code": "q-pb-04-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": '对 s = "Python"，下列哪些写法得到的结果是正确的？（多选）',
            "options": [
                ("A", 's[0] 得到 "P"'),
                ("B", 's[-1] 得到 "n"'),
                ("C", 's[0:3] 得到 "Pyt"'),
                ("D", "s[10] 返回空字符串"),
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": (
                "索引从 0 开始，s[0] 是 P；-1 表示倒数第一个，是 n；"
                "切片左闭右开，0:3 取第 0、1、2 位即 Pyt；"
                "s[10] 超出范围会抛 IndexError，不会返回空字符串，所以 D 错。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-05-l01": [
        {
            "code": "q-pb-05-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "已有 nums = [1, 2, 3]，下列哪些操作会改变这个列表本身？（多选）",
            "options": [
                ("A", "nums.append(4)"),
                ("B", "nums[0] = 9"),
                ("C", "nums[1]"),
                ("D", "nums.remove(2)"),
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": (
                "append 在末尾追加、用下标赋值、remove 按值删除，三者都会改动原列表；"
                "nums[1] 只是把值读出来，不产生任何修改，所以 C 不属于「改变列表」的操作。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-06-l01": [
        {
            "code": "q-pb-06-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "已有 t = (1, 2, 3)，下列哪些说法正确？（多选）",
            "options": [
                ("A", "t[0] 的值是 1"),
                ("B", "执行 t[0] = 9 可以改掉第一个元素"),
                ("C", "a, b, c = t 能把三个值分别赋给三个变量"),
                ("D", "len(t) 的值是 3"),
            ],
            "answer": {"values": ["A", "C", "D"]},
            "explanation": (
                "元组可以按索引取值、可以解包、可以用 len 求长度；"
                "但元组一旦创建就不能修改元素，t[0] = 9 会抛 TypeError，所以 B 错。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-07-l01": [
        {
            "code": "q-pb-07-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "执行 s = {1, 2, 2, 3} 之后，下列哪些说法正确？（多选）",
            "options": [
                ("A", "len(s) 的值是 3"),
                ("B", "s 里会保留两个 2"),
                ("C", "s 里的元素没有固定顺序"),
                ("D", "可以用 s[0] 取出第一个元素"),
            ],
            "answer": {"values": ["A", "C"]},
            "explanation": (
                "集合会自动去重，重复写两次的 2 只保留一个，所以长度是 3、B 错；"
                "集合是无序的，不能按下标取值，s[0] 会抛 TypeError，所以 D 也错。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-08-l01": [
        {
            "code": "q-pb-08-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": '已有 d = {"name": "小明", "age": 18}，下列哪些说法正确？（多选）',
            "options": [
                ("A", 'd["name"] 得到 "小明"'),
                ('B', 'd["score"] 在键不存在时返回 None'),
                ("C", 'd.get("score") 在键不存在时返回 None'),
                ("D", "d.keys() 可以得到全部键"),
            ],
            "answer": {"values": ["A", "C", "D"]},
            "explanation": (
                "用方括号取值时键必须存在，d[\"score\"] 会抛 KeyError 而不是返回 None，"
                "所以 B 错；get 才是「取不到就给 None」的安全写法，C 对。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-09-l01": [
        {
            "code": "q-pb-09-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于 if / elif / else 与缩进，下列哪些说法正确？（多选）",
            "options": [
                ("A", "同一个代码块内的缩进必须保持一致"),
                ("B", "只有前面的 if 条件不成立时，才会去检查 elif"),
                ("C", "else 后面必须再写一个条件"),
                ("D", "Python 用缩进表示代码的层级关系"),
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": (
                "Python 靠缩进划分代码块，同一块内缩进要一致；"
                "elif 是「否则如果」，只有前面条件不成立才会轮到它；"
                "else 表示「以上都不成立」，后面直接跟冒号，不写条件，所以 C 错。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-10-l01": [
        {
            "code": "q-pb-10-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于 for i in range(1, 5)，下列哪些说法正确？（多选）",
            "options": [
                ("A", "i 依次取 1、2、3、4"),
                ("B", "循环体一共执行 5 次"),
                ("C", "range(3) 是从 0 开始的"),
                ("D", "循环结束后 i 的值是 4"),
            ],
            "answer": {"values": ["A", "C", "D"]},
            "explanation": (
                "range(1, 5) 左闭右开，取 1 到 4，共 4 次，所以 B 错；"
                "range(3) 只有一个参数时默认从 0 开始；"
                "Python 的循环变量在循环结束后仍然保留最后一次的值，即 4。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-11-l01": [
        {
            "code": "q-pb-11-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于 while 循环与 break / continue，下列哪些说法正确？（多选）",
            "options": [
                ("A", "while 的条件一开始就是 False 时，循环体一次都不执行"),
                ("B", "break 会立刻跳出当前循环"),
                ("C", "循环里忘记更新控制变量，可能造成死循环"),
                ("D", "continue 会结束整个循环，后面的轮次都不再执行"),
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": (
                "continue 只是跳过本轮剩下的语句、直接进入下一轮，"
                "它不会结束整个循环，结束整个循环的是 break，所以 D 错。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-12-l01": [
        {
            "code": "q-pb-12-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": '关于 def greet(name): 与 print("你好，" + name)，下列哪些说法正确？（多选）',
            "options": [
                ("A", "定义函数要用 def 关键字"),
                ("B", "函数写好后即使不调用，也会自动执行一次"),
                ("C", '调用 greet("小明") 会输出「你好，小明」'),
                ("D", "函数名括号里的 name 是参数"),
            ],
            "answer": {"values": ["A", "C", "D"]},
            "explanation": (
                "def 只负责「把这段逻辑打包并起名字」，不调用就不会执行，所以 B 错；"
                "参数是调用时传进来的数据，写在函数名后面的括号里。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-13-l01": [
        {
            "code": "q-pb-13-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于函数参数与 return，下列哪些说法正确？（多选）",
            "options": [
                ("A", "return 后面的值可以被调用处接收"),
                ("B", "有默认值的参数必须放在没有默认值的参数后面"),
                ("C", "函数里没有写 return 时，调用结果是 None"),
                ("D", "一个函数里只能写一个 return 语句"),
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": (
                "函数里可以写多个 return，但执行到第一个就返回，"
                "后面的语句不再执行，所以「只能写一个」的说法过严，D 错。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-14-l01": [
        {
            "code": "q-pb-14-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于变量作用域与 global，下列哪些说法正确？（多选）",
            "options": [
                ("A", "在函数内部定义的变量默认是局部变量"),
                ("B", "局部变量在函数外部也能直接访问"),
                ("C", "函数内只是读取全局变量，不需要写 global"),
                ("D", "函数内要修改全局变量，需要用 global 声明"),
            ],
            "answer": {"values": ["A", "C", "D"]},
            "explanation": (
                "局部变量只活在函数内部，函数一结束就消失，外面访问会报 NameError，"
                "所以 B 错；读取全局变量不需要声明，只有「重新赋值」时才要 global。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-15-l01": [
        {
            "code": "q-pb-15-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于模块与 import，下列哪些说法正确？（多选）",
            "options": [
                ("A", "import math 之后可以用 math.sqrt 求平方根"),
                ("B", "from math import sqrt 之后可以直接写 sqrt"),
                ("C", "自己写的一个 .py 文件也能当作模块被导入"),
                ("D", "import 只能导入 Python 自带的模块"),
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": (
                "模块不限于标准库，别人发布的库和自己写的 .py 文件都能导入，"
                "只要放在能被找到的位置，所以 D 错。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-16-l01": [
        {
            "code": "q-pb-16-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于文件读取，下列哪些说法正确？（多选）",
            "options": [
                ("A", 'open 的第二个参数 "r" 表示只读'),
                ("B", "with 语句结束时文件会自动关闭"),
                ("C", "read() 一次把文件内容全部读回来"),
                ("D", '用 "r" 打开一个不存在的文件会自动创建它'),
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": (
                '"r" 是只读模式，文件不存在会抛 FileNotFoundError，'
                '不会帮你创建；能创建文件的是 "w" 或 "a" 模式，所以 D 错。'
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-17-l01": [
        {
            "code": "q-pb-17-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于 json 模块，下列哪些说法正确？（多选）",
            "options": [
                ("A", "json.loads 把 JSON 字符串转成 Python 对象"),
                ("B", "json.dumps 把 Python 对象转成 JSON 字符串"),
                ("C", "JSON 里的 null 对应 Python 的 None"),
                ("D", "json.dumps 默认就把中文原样输出"),
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": (
                "dumps 默认会把非 ASCII 字符转成 \\uXXXX 转义，中文看起来是一串编码，"
                "要加 ensure_ascii=False 才会原样输出，所以 D 错。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-18-l01": [
        {
            "code": "q-pb-18-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "关于异常捕获，下列哪些说法正确？（多选）",
            "options": [
                ("A", "except 后面写异常类型，可以只处理这一类错误"),
                ("B", "裸 except 会把代码里其他写错的地方一起吞掉"),
                ("C", "异常被捕获处理之后，程序会立刻整体退出"),
                ("D", 'int("abc") 会触发 ValueError'),
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": (
                "捕获异常的目的是「接着往下走」，处理完程序会继续执行，"
                "不会整体退出，所以 C 错；裸 except 抓得太宽，容易掩盖真正的问题。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-19-l01": [
        {
            "code": "q-pb-19-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "程序报错时，下列哪些做法有助于定位问题？（多选）",
            "options": [
                ("A", "读报错的最后一行，看清错误类型和说明"),
                ("B", "看报错里的行号，定位到出错的代码位置"),
                ("C", "在可疑的位置加 print，打印中间变量的值"),
                ("D", "直接把报错指向的那一行删掉"),
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": (
                "删掉报错行只是让错误换个地方出现，问题本身没解决，所以 D 错；"
                "报错的类型、说明和行号是三条最有价值的线索。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
    "python-basics-20-l01": [
        {
            "code": "q-pb-20-l01-7",
            "kp": 0,
            "type": "multiple_choice",
            "stem": "做命令行任务管理工具时，下列哪些做法符合「先拆解再实现」？（多选）",
            "options": [
                ("A", "先把需求拆成添加、查看、删除几个小功能"),
                ("B", "先想清楚每个功能用列表还是字典存数据"),
                ("C", "把所有代码一次性写完，最后才运行"),
                ("D", "每写完一个功能就先运行验证一次"),
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": (
                "先拆功能、先定数据结构、写完一块就验证，都是把大问题拆小的做法；"
                "一次性写完再运行，出错时很难判断是哪一块的问题，所以 C 错。"
            ),
            "difficulty": "beginner",
            "category": "基础理解",
        }
    ],
}
