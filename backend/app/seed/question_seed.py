"""内置题库种子（PRD 6.3 / 阶段 9）。

每个知识点 3 道题，共 93 道，覆盖 PRD 6.2 的全部 7 种题型。题目由开发期
人工整理并逐题校验（题型、答案结构、解析、知识点归属），但不等同于产品
负责人已完成抽检；validation_notes 会明确标注，建议正式发布前人工抽检。

种子函数按题目稳定 code 幂等 upsert：重复执行更新题目内容，不重复插入，
也不会删除已有 AI 题或历史答题记录。

题型约定：
- single_choice: options + {"value": "A"}
- multiple_choice: options + {"values": ["A", "C"]}
- true_false: {"value": true/false}
- fill_blank: {"values": ["可接受答案", ...]}
- 主观题: {"reference": "...", "keywords": [...]}（关键词须出现在参考答案中）
"""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import KnowledgePoint
from app.models.quiz import QUESTION_TYPES, Question
from app.repositories.question_repository import QuestionRepository

BUILTIN_NOTE = (
    "开发期人工整理并逐题校验的内置题库；建议产品负责人抽检复核后再作为正式发布内容"
)

QUESTION_SEED: dict[str, list[dict]] = {
    "python-basics-01-01": [
        {
            "type": "single_choice",
            "stem": "Python 属于哪一类编程语言？",
            "options": [
                {"key": "A", "text": "解释型高级语言"},
                {"key": "B", "text": "机器语言"},
                {"key": "C", "text": "汇编语言"},
                {"key": "D", "text": "数据库查询语言"},
            ],
            "answer": {"value": "A"},
            "explanation": "Python 源码由解释器执行，使用接近自然语言的语法，属于高级编程语言。",
        },
        {
            "type": "multiple_choice",
            "stem": "以下哪些是 Python 的典型应用场景？",
            "options": [
                {"key": "A", "text": "数据分析"},
                {"key": "B", "text": "网站后端开发"},
                {"key": "C", "text": "自动化脚本"},
                {"key": "D", "text": "直接编写 CPU 机器指令"},
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": "Python 常用于数据分析、网站后端、自动化脚本等；CPU 机器指令通常由编译后的机器码表示。",
        },
        {
            "type": "code_writing",
            "stem": "请用一段话说明「编程」是什么，并举出两个 Python 的典型应用场景。只需文本作答，不执行代码。",
            "answer": {
                "reference": "编程是把解决问题的步骤写成计算机能够执行的指令的过程。Python 常用于数据分析、网站后端开发和自动化脚本等场景。",
                "keywords": ["解决问题的步骤", "计算机", "指令", "数据分析", "网站后端", "自动化"],
            },
            "explanation": "编程的核心是把问题拆解为可执行的步骤；Python 的典型场景包括数据分析、网站后端和自动化脚本。",
        },
    ],
    "python-basics-01-02": [
        {
            "type": "true_false",
            "stem": "安装 Python 后，可以在命令行使用 python --version 查看版本号。",
            "answer": {"value": True},
            "explanation": "python --version 会在终端输出当前 Python 版本，是验证安装是否成功的常用方法。",
        },
        {
            "type": "fill_blank",
            "stem": "在命令行运行 ____ 命令可以查看当前 Python 版本。",
            "answer": {
                "values": [
                    "python --version",
                    "python3 --version",
                    "py --version",
                ]
            },
            "explanation": "python --version 会输出 Python 版本信息；不同系统也可能使用 python3 --version 或 Windows 的 py --version。",
        },
        {
            "type": "short_answer",
            "stem": "简述验证 Python 是否安装成功的两个步骤。",
            "answer": {
                "reference": "打开命令行终端，输入 python --version 并回车，如果输出 Python 版本号说明安装成功；也可以进入 Python 交互式解释器，看到提示符后输入 exit() 退出。",
                "keywords": ["命令行", "python --version", "版本号", "交互式", "exit"],
            },
            "explanation": "命令行版本检查和交互式解释器都是验证安装的常见方式。",
        },
    ],
    "python-basics-01-03": [
        {
            "type": "single_choice",
            "stem": "print('Hello') 的输出是什么？",
            "options": [
                {"key": "A", "text": "Hello"},
                {"key": "B", "text": "'Hello'"},
                {"key": "C", "text": "print"},
                {"key": "D", "text": "程序报错"},
            ],
            "answer": {"value": "A"},
            "explanation": "print 输出字符串的内容，不会把引号一起输出。",
        },
        {
            "type": "fill_blank",
            "stem": "执行 print(1 + 2) 后，屏幕上显示的结果是 ____。",
            "answer": {"values": ["3"]},
            "explanation": "print 会先计算表达式 1 + 2 得到 3，再输出结果。",
        },
        {
            "type": "code_analysis",
            "stem": "阅读代码：\nprint(\"小码\")\nprint(\"学习\")\n这段代码会输出什么？请按行说明。",
            "answer": {
                "reference": "第一行输出「小码」，第二行输出「学习」，因此结果分两行显示；print 每次调用结束后默认换行。",
                "keywords": ["小码", "学习", "两行"],
            },
            "explanation": "两次 print 调用分别输出一段文本，默认以换行结束。",
        },
    ],
    "python-basics-01-04": [
        {
            "type": "multiple_choice",
            "stem": "以下关于 Python 注释的说法，哪些正确？",
            "options": [
                {"key": "A", "text": "单行注释以 # 开头"},
                {"key": "B", "text": "注释会被解释器执行"},
                {"key": "C", "text": "注释用于说明代码意图"},
                {"key": "D", "text": "三引号字符串常被用来写多行说明"},
            ],
            "answer": {"values": ["A", "C", "D"]},
            "explanation": "注释不会被解释器执行；# 用于单行注释，三引号字符串常被用作多行说明。",
        },
        {
            "type": "true_false",
            "stem": "Python 中 # 后面的内容会被当作注释，不会执行。",
            "answer": {"value": True},
            "explanation": "# 开启单行注释，解释器会忽略该行剩余内容。",
        },
        {
            "type": "short_answer",
            "stem": "为什么写注释？请说明注释的两个作用。",
            "answer": {
                "reference": "注释用于解释代码的意图，帮助自己和他人理解代码；也可以暂时标记待办或说明复杂逻辑，但注释不会被程序执行。",
                "keywords": ["解释", "意图", "理解", "不会被程序执行"],
            },
            "explanation": "注释服务于人的阅读，不参与程序运行。",
        },
    ],
    "python-basics-01-05": [
        {
            "type": "single_choice",
            "stem": "input() 函数返回值的类型默认是什么？",
            "options": [
                {"key": "A", "text": "字符串 str"},
                {"key": "B", "text": "整数 int"},
                {"key": "C", "text": "浮点数 float"},
                {"key": "D", "text": "布尔值 bool"},
            ],
            "answer": {"value": "A"},
            "explanation": "input() 读取用户输入后始终返回字符串，需要数字时应使用 int() 或 float() 转换。",
        },
        {
            "type": "single_choice",
            "stem": "执行 name = input('请输入名字：') 时，括号里的文字会怎样？",
            "options": [
                {"key": "A", "text": "作为提示显示"},
                {"key": "B", "text": "写入变量 name"},
                {"key": "C", "text": "被忽略"},
                {"key": "D", "text": "成为返回值"},
            ],
            "answer": {"value": "A"},
            "explanation": "input 的字符串参数是输入提示；用户输入的内容才是函数返回值。",
        },
        {
            "type": "code_writing",
            "stem": "编写一段文本形式的 Python 代码：读取用户输入的名字，并输出「你好，名字」。无需运行，只提交代码文本。",
            "answer": {
                "reference": "name = input(\"请输入名字：\")\nprint(\"你好，\" + name)",
                "keywords": ["input", "print", "你好"],
            },
            "explanation": "先用 input 获取字符串，再用字符串拼接或 f-string 输出问候语。",
        },
    ],
    "python-basics-02-01": [
        {
            "type": "single_choice",
            "stem": "以下哪个是合法的 Python 变量名？",
            "options": [
                {"key": "A", "text": "2name"},
                {"key": "B", "text": "my-name"},
                {"key": "C", "text": "user_name"},
                {"key": "D", "text": "class"},
            ],
            "answer": {"value": "C"},
            "explanation": "变量名不能以数字开头、不能包含连字符、不能使用关键字；user_name 合法。",
        },
        {
            "type": "multiple_choice",
            "stem": "关于变量赋值，以下说法正确的有？",
            "options": [
                {"key": "A", "text": "变量名区分大小写"},
                {"key": "B", "text": "变量不需要提前声明类型"},
                {"key": "C", "text": "变量名可以以数字开头"},
                {"key": "D", "text": "赋值使用 = 符号"},
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": "Python 变量名区分大小写、无需显式声明类型，赋值使用 =；变量名不能以数字开头。",
        },
        {
            "type": "code_writing",
            "stem": "用文本形式写两行 Python 代码：创建变量 age 并赋值为 18，然后用 print 输出它。",
            "answer": {
                "reference": "age = 18\nprint(age)",
                "keywords": ["age", "=", "18", "print"],
            },
            "explanation": "赋值语句把 18 绑定到变量 age，随后 print 读取变量值输出。",
        },
    ],
    "python-basics-02-02": [
        {
            "type": "true_false",
            "stem": "在 Python 中，10 / 2 的结果类型是 float（浮点数）。",
            "answer": {"value": True},
            "explanation": "Python 3 中 / 总是执行真除法并返回 float，因此 10 / 2 的结果是 5.0。",
        },
        {
            "type": "fill_blank",
            "stem": "表达式 7 // 2 的结果是 ____。",
            "answer": {"values": ["3"]},
            "explanation": "// 是整除，7 除以 2 的整数商为 3，余数由 % 得到。",
        },
        {
            "type": "short_answer",
            "stem": "说明整数 int 与浮点数 float 的区别，并各举一个例子。",
            "answer": {
                "reference": "int 表示没有小数部分的整数，例如 3；float 表示带小数部分的浮点数，例如 3.14；除法 / 的结果通常是 float。",
                "keywords": ["int", "float", "整数", "小数", "3.14"],
            },
            "explanation": "int 与 float 的区别在于是否表示小数部分；/ 运算产生 float。",
        },
    ],
    "python-basics-02-03": [
        {
            "type": "single_choice",
            "stem": "表达式 \"py\" + \"thon\" 的结果是什么？",
            "options": [
                {"key": "A", "text": "python"},
                {"key": "B", "text": "py thon"},
                {"key": "C", "text": "程序报错"},
                {"key": "D", "text": "py+thon"},
            ],
            "answer": {"value": "A"},
            "explanation": "两个字符串使用 + 会拼接成一个新字符串。",
        },
        {
            "type": "fill_blank",
            "stem": "len(\"小码\") 的结果是 ____。",
            "answer": {"values": ["2"]},
            "explanation": "len 返回字符串的字符数量，「小码」包含两个字符。",
        },
        {
            "type": "code_analysis",
            "stem": "阅读代码：\ns = \"abc\"\nprint(s * 2)\n输出是什么？为什么？",
            "answer": {
                "reference": "输出 abcabc。字符串与整数相乘会重复字符串内容，s * 2 表示把 \"abc\" 重复两次。",
                "keywords": ["abcabc", "重复", "字符串"],
            },
            "explanation": "字符串支持 * 整数运算，结果为原字符串重复指定次数。",
        },
    ],
    "python-basics-02-04": [
        {
            "type": "multiple_choice",
            "stem": "以下表达式结果为 True 的有？",
            "options": [
                {"key": "A", "text": "3 > 2"},
                {"key": "B", "text": "2 == 2"},
                {"key": "C", "text": "1 != 1"},
                {"key": "D", "text": "5 <= 4"},
            ],
            "answer": {"values": ["A", "B"]},
            "explanation": "3 > 2 与 2 == 2 为 True；1 != 1 和 5 <= 4 为 False。",
        },
        {
            "type": "true_false",
            "stem": "比较表达式 1 < 2 的结果是一个布尔值 True。",
            "answer": {"value": True},
            "explanation": "比较运算返回布尔值，1 小于 2 所以结果为 True。",
        },
        {
            "type": "short_answer",
            "stem": "布尔类型只有哪两个取值？比较运算的结果通常是什么类型？",
            "answer": {
                "reference": "布尔类型只有 True 和 False 两个取值；比较运算的结果通常是 bool（布尔值）类型。",
                "keywords": ["True", "False", "bool", "布尔值", "比较"],
            },
            "explanation": "布尔值用于条件判断，比较运算产生 bool 类型结果。",
        },
    ],
    "python-basics-02-05": [
        {
            "type": "single_choice",
            "stem": "int(\"12\") 的结果是什么？",
            "options": [
                {"key": "A", "text": "整数 12"},
                {"key": "B", "text": "字符串 \"12\""},
                {"key": "C", "text": "程序报错"},
                {"key": "D", "text": "浮点数 12.0"},
            ],
            "answer": {"value": "A"},
            "explanation": "int 把可以解析的数字字符串转换为整数。",
        },
        {
            "type": "single_choice",
            "stem": "\"3\" + \"4\" 的结果是什么？",
            "options": [
                {"key": "A", "text": "字符串 \"34\""},
                {"key": "B", "text": "整数 7"},
                {"key": "C", "text": "字符串 \"7\""},
                {"key": "D", "text": "程序报错"},
            ],
            "answer": {"value": "A"},
            "explanation": "两个字符串相加执行拼接，不会做数学加法；要得到 7 需先转换为整数。",
        },
        {
            "type": "code_writing",
            "stem": "编写文本代码：把用户输入的内容转换为整数，再乘以 2 后输出。",
            "answer": {
                "reference": "value = int(input(\"请输入一个整数：\"))\nprint(value * 2)",
                "keywords": ["int", "input", "value", "* 2", "print"],
            },
            "explanation": "input 返回字符串，必须用 int 转换后才能进行数学运算。",
        },
    ],
    "python-basics-02-06": [
        {
            "type": "single_choice",
            "stem": "以下哪个 f-string 能正确输出「你好，小明」（假设 name 为「小明」）？",
            "options": [
                {"key": "A", "text": "f\"你好，{name}\""},
                {"key": "B", "text": "\"你好，{name}\""},
                {"key": "C", "text": "f\"你好，name\""},
                {"key": "D", "text": "f\"你好，{name\""},
            ],
            "answer": {"value": "A"},
            "explanation": "f-string 需要在字符串前加 f，并用成对花括号嵌入变量。",
        },
        {
            "type": "multiple_choice",
            "stem": "关于 f-string，以下说法正确的有？",
            "options": [
                {"key": "A", "text": "字符串前需要加 f"},
                {"key": "B", "text": "花括号内可以放变量或表达式"},
                {"key": "C", "text": "花括号会原样输出"},
                {"key": "D", "text": "可以让变量值和文字组合"},
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": "f-string 用花括号替换变量或表达式；没有 f 前缀时花括号会原样显示。",
        },
        {
            "type": "code_writing",
            "stem": "文本代码：变量 name = \"小码\"，使用 f-string 输出「你好，小码」。",
            "answer": {
                "reference": "name = \"小码\"\nprint(f\"你好，{name}\")",
                "keywords": ["name", "f\"", "{name}", "print", "你好"],
            },
            "explanation": "f-string 用 {name} 把变量值嵌入字符串。",
        },
    ],
    "python-basics-03-01": [
        {
            "type": "true_false",
            "stem": "Python 中 % 运算符表示取余数。",
            "answer": {"value": True},
            "explanation": "% 返回除法余数，例如 7 % 2 的结果是 1。",
        },
        {
            "type": "fill_blank",
            "stem": "表达式 2 ** 3 的结果是 ____。",
            "answer": {"values": ["8"]},
            "explanation": "** 是幂运算，2 的 3 次方等于 8。",
        },
        {
            "type": "short_answer",
            "stem": "请说明 //、%、** 三个运算符的含义。",
            "answer": {
                "reference": "// 是整除，返回商的整数部分；% 是取余，返回除法的余数；** 是幂运算，返回一个数的若干次方。",
                "keywords": ["整除", "取余", "幂", "余数", "次方"],
            },
            "explanation": "三个运算符分别对应整除、取余和幂运算。",
        },
    ],
    "python-basics-03-02": [
        {
            "type": "single_choice",
            "stem": "表达式 3 >= 3 的结果是？",
            "options": [
                {"key": "A", "text": "True"},
                {"key": "B", "text": "False"},
                {"key": "C", "text": "3"},
                {"key": "D", "text": "程序报错"},
            ],
            "answer": {"value": "A"},
            "explanation": ">= 表示大于或等于，3 等于 3，因此结果为 True。",
        },
        {
            "type": "fill_blank",
            "stem": "表达式 4 != 5 的结果是 ____（填 True 或 False）。",
            "answer": {"values": ["True", "true"]},
            "explanation": "!= 表示不等于，4 与 5 不相等，所以结果为 True。",
        },
        {
            "type": "code_analysis",
            "stem": "阅读代码：\na = 5\nb = 3\nprint(a > b and a != b)\n输出是什么？请说明 and 两侧条件的判断过程。",
            "answer": {
                "reference": "输出 True。a > b 为 True，a != b 也为 True，and 只有在两侧都为 True 时才返回 True。",
                "keywords": ["True", "and", "两侧", "都为"],
            },
            "explanation": "and 要求两个条件同时成立。",
        },
    ],
    "python-basics-03-03": [
        {
            "type": "multiple_choice",
            "stem": "关于 Python 逻辑运算符，正确的有？",
            "options": [
                {"key": "A", "text": "and 表示并且"},
                {"key": "B", "text": "or 表示或者"},
                {"key": "C", "text": "not 表示取反"},
                {"key": "D", "text": "and 表示或者"},
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": "and 表示并且、or 表示或者、not 表示逻辑取反。",
        },
        {
            "type": "true_false",
            "stem": "not True 的结果是 False。",
            "answer": {"value": True},
            "explanation": "not 对布尔值取反，not True 得到 False。",
        },
        {
            "type": "short_answer",
            "stem": "说明 and、or、not 的作用，并各给一个简单例子。",
            "answer": {
                "reference": "and 表示并且，两侧都为真时结果才为真，例如 True and False 为 False；or 表示或者，任意一侧为真结果就为真；not 表示取反，例如 not True 为 False。",
                "keywords": ["and", "or", "not", "取反", "真"],
            },
            "explanation": "逻辑运算符用于组合或反转条件。",
        },
    ],
    "python-basics-03-04": [
        {
            "type": "single_choice",
            "stem": "表达式 2 + 3 * 4 的结果是？",
            "options": [
                {"key": "A", "text": "14"},
                {"key": "B", "text": "20"},
                {"key": "C", "text": "24"},
                {"key": "D", "text": "9"},
            ],
            "answer": {"value": "A"},
            "explanation": "乘法优先级高于加法，先算 3 * 4 得 12，再加 2 得 14。",
        },
        {
            "type": "single_choice",
            "stem": "表达式 (2 + 3) * 4 的结果是？",
            "options": [
                {"key": "A", "text": "20"},
                {"key": "B", "text": "14"},
                {"key": "C", "text": "24"},
                {"key": "D", "text": "9"},
            ],
            "answer": {"value": "A"},
            "explanation": "括号提高优先级，先算 2 + 3 得 5，再乘以 4 得 20。",
        },
        {
            "type": "code_writing",
            "stem": "写出文本代码：计算 10 加 2 乘以 3，再用 print 输出结果；要求结果符合先乘后加。无需运行，只提交代码。",
            "answer": {
                "reference": "result = 10 + 2 * 3\nprint(result)",
                "keywords": ["10", "2 * 3", "print"],
            },
            "explanation": "乘号优先级高于加号，10 + 2 * 3 的结果为 16。",
        },
    ],
    "python-basics-04-01": [
        {
            "type": "single_choice",
            "stem": "以下哪个关键字用于 Python 的条件分支？",
            "options": [
                {"key": "A", "text": "if"},
                {"key": "B", "text": "for"},
                {"key": "C", "text": "def"},
                {"key": "D", "text": "import"},
            ],
            "answer": {"value": "A"},
            "explanation": "if 用于条件判断；for 用于循环，def 定义函数，import 导入模块。",
        },
        {
            "type": "multiple_choice",
            "stem": "关于 if/elif/else，正确的有？",
            "options": [
                {"key": "A", "text": "if 可以单独使用"},
                {"key": "B", "text": "elif 可以出现多次"},
                {"key": "C", "text": "else 必须带条件"},
                {"key": "D", "text": "else 在前面的条件都不满足时执行"},
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": "else 不带条件，表示前面条件都不满足时的分支。",
        },
        {
            "type": "code_writing",
            "stem": "文本代码：如果变量 score 大于等于 60 输出「及格」，否则输出「不及格」。",
            "answer": {
                "reference": "if score >= 60:\n    print(\"及格\")\nelse:\n    print(\"不及格\")",
                "keywords": ["if", "score", "60", "else", "及格", "不及格"],
            },
            "explanation": "使用 if/else 表达两种互斥情况，条件写在 if 后。",
        },
    ],
    "python-basics-04-02": [
        {
            "type": "true_false",
            "stem": "Python 使用缩进来表示代码块，同一代码块的缩进必须一致。",
            "answer": {"value": True},
            "explanation": "缩进是 Python 语法的一部分，同一代码块缩进不一致会导致错误。",
        },
        {
            "type": "fill_blank",
            "stem": "在 Python 中，if 语句下面的代码块需要 ____（填「缩进」或「加大括号」）。",
            "answer": {"values": ["缩进"]},
            "explanation": "Python 不使用大括号划分代码块，而是要求缩进。",
        },
        {
            "type": "short_answer",
            "stem": "为什么 Python 要求缩进？缩进不一致可能发生什么？",
            "answer": {
                "reference": "Python 用缩进划分代码块，缩进让代码结构清晰；同一代码块缩进不一致会导致 IndentationError，程序无法正常运行。",
                "keywords": ["缩进", "代码块", "IndentationError", "结构"],
            },
            "explanation": "缩进既是格式要求也是语法结构，不一致会触发 IndentationError。",
        },
    ],
    "python-basics-04-03": [
        {
            "type": "single_choice",
            "stem": "while 循环会在什么情况下继续执行循环体？",
            "options": [
                {"key": "A", "text": "条件为真时"},
                {"key": "B", "text": "条件为假时"},
                {"key": "C", "text": "永远执行一次"},
                {"key": "D", "text": "只执行一次"},
            ],
            "answer": {"value": "A"},
            "explanation": "while 在条件为真时反复执行循环体，条件为假时结束。",
        },
        {
            "type": "fill_blank",
            "stem": "下面代码执行后，count 的值是 ____：\ncount = 0\nwhile count < 3:\n    count = count + 1",
            "answer": {"values": ["3"]},
            "explanation": "循环在 count 达到 3 时条件不再成立，因此 count 最终为 3。",
        },
        {
            "type": "code_analysis",
            "stem": "阅读代码：\ni = 1\nwhile i <= 3:\n    print(i)\n    i = i + 1\n输出是什么？请说明循环条件与 i 的变化。",
            "answer": {
                "reference": "依次输出 1、2、3，每个数字占一行。循环条件 i <= 3 成立时执行，循环体每次把 i 加 1，最终 i 变为 4 时结束。",
                "keywords": ["1", "2", "3", "i <= 3", "加 1"],
            },
            "explanation": "循环从 1 开始，每次输出后加 1，直到 i 为 4 时结束。",
        },
    ],
    "python-basics-04-04": [
        {
            "type": "multiple_choice",
            "stem": "关于 for 循环与 range，正确的有？",
            "options": [
                {"key": "A", "text": "range(3) 产生 0、1、2"},
                {"key": "B", "text": "for 可以遍历列表"},
                {"key": "C", "text": "range(1, 4) 包含 4"},
                {"key": "D", "text": "for 循环常用于已知次数的重复"},
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": "range 的结束值不包含在序列中，因此 range(1, 4) 是 1、2、3。",
        },
        {
            "type": "true_false",
            "stem": "range(5) 生成的整数包含 0、1、2、3、4。",
            "answer": {"value": True},
            "explanation": "range(5) 从 0 开始、到 5 前结束，共 5 个整数。",
        },
        {
            "type": "short_answer",
            "stem": "说明 range(1, 5) 会生成哪些整数，以及 for i in range(1, 5) 会循环几次。",
            "answer": {
                "reference": "range(1, 5) 生成 1、2、3、4，不包含结束值 5；for i in range(1, 5) 会循环 4 次。",
                "keywords": ["1", "2", "3", "4", "不包含", "4 次"],
            },
            "explanation": "range 包含起始值、不包含结束值，因此共 4 个整数。",
        },
    ],
    "python-basics-04-05": [
        {
            "type": "single_choice",
            "stem": "break 在循环中的作用是什么？",
            "options": [
                {"key": "A", "text": "立即结束整个循环"},
                {"key": "B", "text": "跳过本次循环剩余部分"},
                {"key": "C", "text": "重新开始循环"},
                {"key": "D", "text": "结束程序"},
            ],
            "answer": {"value": "A"},
            "explanation": "break 立即跳出当前循环；跳过本次循环剩余部分的是 continue。",
        },
        {
            "type": "single_choice",
            "stem": "continue 在循环中的作用是什么？",
            "options": [
                {"key": "A", "text": "跳过本次循环剩余部分，进入下一次循环"},
                {"key": "B", "text": "结束整个循环"},
                {"key": "C", "text": "结束程序"},
                {"key": "D", "text": "让循环条件永远为真"},
            ],
            "answer": {"value": "A"},
            "explanation": "continue 跳过本轮剩余语句，直接进入下一轮条件判断。",
        },
        {
            "type": "code_writing",
            "stem": "文本代码：使用 for 循环遍历 range(1, 11)，当数字等于 5 时用 break 结束循环，并在此之前输出每个数字。",
            "answer": {
                "reference": "for i in range(1, 11):\n    if i == 5:\n        break\n    print(i)",
                "keywords": ["for", "range(1, 11)", "break", "i == 5", "print"],
            },
            "explanation": "循环输出 1 到 4，遇到 5 时 break 提前结束。",
        },
    ],
    "python-basics-04-06": [
        {
            "type": "single_choice",
            "stem": "循环嵌套指的是什么？",
            "options": [
                {"key": "A", "text": "一个循环体内包含另一个循环"},
                {"key": "B", "text": "两个并列的循环"},
                {"key": "C", "text": "用 if 代替循环"},
                {"key": "D", "text": "循环只执行一次"},
            ],
            "answer": {"value": "A"},
            "explanation": "嵌套循环是一个循环的循环体里再写一个循环。",
        },
        {
            "type": "multiple_choice",
            "stem": "关于嵌套循环，正确的有？",
            "options": [
                {"key": "A", "text": "外层每执行一次，内层通常完整执行一轮"},
                {"key": "B", "text": "嵌套层数过多会降低可读性"},
                {"key": "C", "text": "内层循环变量不能与外层同名"},
                {"key": "D", "text": "内层循环可以提前 break 跳出内层"},
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": "内层变量与外层同名在语法上允许（会遮蔽外层变量），因此 C 不正确。",
        },
        {
            "type": "code_writing",
            "stem": "文本代码：用两层 for 循环输出一个 2 行 3 列的星号图案，每行三个 *。",
            "answer": {
                "reference": "for row in range(2):\n    for col in range(3):\n        print(\"*\", end=\"\")\n    print()",
                "keywords": ["for", "range(2)", "range(3)", "print", "*"],
            },
            "explanation": "外层控制行数，内层控制每行星号数量，行末换行。",
        },
    ],
    "python-basics-05-01": [
        {
            "type": "true_false",
            "stem": "在 Python 中使用 def 关键字定义函数。",
            "answer": {"value": True},
            "explanation": "def 后跟函数名、参数列表和冒号，函数体需要缩进。",
        },
        {
            "type": "fill_blank",
            "stem": "定义函数使用的关键字是 ____。",
            "answer": {"values": ["def"]},
            "explanation": "Python 使用 def 定义函数。",
        },
        {
            "type": "short_answer",
            "stem": "简述定义函数的基本结构，并说明函数名后的括号有什么作用。",
            "answer": {
                "reference": "使用 def 关键字写函数名和括号，冒号后缩进写函数体；括号用于放置参数，没有参数时也保留空括号，调用函数时写函数名加括号。",
                "keywords": ["def", "括号", "参数", "缩进", "函数体"],
            },
            "explanation": "定义与调用函数都必须带括号，括号承载参数。",
        },
    ],
    "python-basics-05-02": [
        {
            "type": "single_choice",
            "stem": "函数没有显式 return 时，默认返回什么？",
            "options": [
                {"key": "A", "text": "None"},
                {"key": "B", "text": "0"},
                {"key": "C", "text": "空字符串"},
                {"key": "D", "text": "程序报错"},
            ],
            "answer": {"value": "A"},
            "explanation": "没有 return 的函数隐式返回 None。",
        },
        {
            "type": "fill_blank",
            "stem": "关键字 ____ 用于把函数结果返回给调用者。",
            "answer": {"values": ["return"]},
            "explanation": "return 结束函数执行并把结果交给调用者。",
        },
        {
            "type": "code_analysis",
            "stem": "阅读代码：\ndef add(a, b):\n    return a + b\n\nprint(add(3, 4))\n输出是什么？请说明实参如何传给形参、return 如何返回结果。",
            "answer": {
                "reference": "输出 7。调用 add(3, 4) 时参数 a 为 3、b 为 4，return a + b 返回 7，print 再输出它。",
                "keywords": ["7", "a", "b", "return", "print"],
            },
            "explanation": "实参按顺序传给形参，return 的结果被 print 输出。",
        },
    ],
    "python-basics-05-03": [
        {
            "type": "multiple_choice",
            "stem": "关于变量作用域，正确的有？",
            "options": [
                {"key": "A", "text": "函数内部定义的变量默认是局部变量"},
                {"key": "B", "text": "局部变量在函数外通常不能直接访问"},
                {"key": "C", "text": "全局变量都可以在函数内直接修改"},
                {"key": "D", "text": "使用 global 可以声明使用全局变量"},
            ],
            "answer": {"values": ["A", "B", "D"]},
            "explanation": "在函数内修改全局变量需要 global 声明，不能直接修改所有全局变量。",
        },
        {
            "type": "true_false",
            "stem": "在函数内部直接读取全局变量通常是允许的。",
            "answer": {"value": True},
            "explanation": "函数内可以读取全局变量；需要修改时才涉及 global 声明。",
        },
        {
            "type": "short_answer",
            "stem": "说明局部变量与全局变量的区别，并指出函数内修改全局变量需要注意什么。",
            "answer": {
                "reference": "局部变量定义在函数内部，只在函数内有效；全局变量定义在模块顶层，函数内可以读取；如果要在函数内修改全局变量，需要用 global 声明，否则会创建同名局部变量。",
                "keywords": ["局部变量", "全局变量", "函数内部", "global", "修改"],
            },
            "explanation": "作用域决定变量可见范围，修改全局变量需要显式声明。",
        },
    ],
    "python-basics-05-04": [
        {
            "type": "single_choice",
            "stem": "导入 math 模块的正确写法是？",
            "options": [
                {"key": "A", "text": "import math"},
                {"key": "B", "text": "include math"},
                {"key": "C", "text": "using math"},
                {"key": "D", "text": "import(math)"},
            ],
            "answer": {"value": "A"},
            "explanation": "Python 使用 import 模块名 导入整个模块。",
        },
        {
            "type": "single_choice",
            "stem": "from math import sqrt 的作用是什么？",
            "options": [
                {"key": "A", "text": "只导入 sqrt 函数"},
                {"key": "B", "text": "导入整个 math 模块并改名"},
                {"key": "C", "text": "删除 math 模块"},
                {"key": "D", "text": "定义新的 sqrt 函数"},
            ],
            "answer": {"value": "A"},
            "explanation": "from ... import ... 只把指定名称引入当前命名空间。",
        },
        {
            "type": "code_writing",
            "stem": "文本代码：导入 math 模块，使用 math.sqrt 计算 16 的平方根并打印结果。",
            "answer": {
                "reference": "import math\nprint(math.sqrt(16))",
                "keywords": ["import math", "math.sqrt", "16", "print"],
            },
            "explanation": "导入 math 后通过 math.sqrt 调用平方根函数。",
        },
    ],
    "python-basics-05-05": [
        {
            "type": "single_choice",
            "stem": "len(\"Python\") 的结果是？",
            "options": [
                {"key": "A", "text": "6"},
                {"key": "B", "text": "5"},
                {"key": "C", "text": "7"},
                {"key": "D", "text": "程序报错"},
            ],
            "answer": {"value": "A"},
            "explanation": "Python 包含 6 个字符，len 返回字符数量。",
        },
        {
            "type": "multiple_choice",
            "stem": "以下哪些是 Python 内置函数？",
            "options": [
                {"key": "A", "text": "len"},
                {"key": "B", "text": "print"},
                {"key": "C", "text": "sum"},
                {"key": "D", "text": "math.sqrt"},
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": "len、print、sum 是内置函数；math.sqrt 需要先导入 math 模块。",
        },
        {
            "type": "code_writing",
            "stem": "文本代码：定义列表 nums = [3, 1, 2]，使用内置函数输出它的长度与总和。",
            "answer": {
                "reference": "nums = [3, 1, 2]\nprint(len(nums))\nprint(sum(nums))",
                "keywords": ["nums", "len", "sum", "print"],
            },
            "explanation": "len 返回元素个数，sum 返回元素总和。",
        },
    ],
    "python-basics-06-01": [
        {
            "type": "true_false",
            "stem": "Python 列表使用方括号创建，元素之间用逗号分隔。",
            "answer": {"value": True},
            "explanation": "列表字面量写作 [元素1, 元素2, ...]。",
        },
        {
            "type": "fill_blank",
            "stem": "访问列表 lst 的第一个元素应写成 ____。",
            "answer": {"values": ["lst[0]"]},
            "explanation": "Python 下标从 0 开始，第一个元素是 lst[0]。",
        },
        {
            "type": "short_answer",
            "stem": "说明列表的两个常见操作，并举例。",
            "answer": {
                "reference": "列表可以追加元素，例如 lst.append(4)；也可以按下标访问元素，例如 lst[0] 获取第一个元素。",
                "keywords": ["append", "下标", "lst[0]", "追加", "第一个"],
            },
            "explanation": "追加与下标访问是列表最基础的操作。",
        },
    ],
    "python-basics-06-02": [
        {
            "type": "single_choice",
            "stem": "Python 元组使用哪种括号创建？",
            "options": [
                {"key": "A", "text": "圆括号"},
                {"key": "B", "text": "方括号"},
                {"key": "C", "text": "花括号"},
                {"key": "D", "text": "尖括号"},
            ],
            "answer": {"value": "A"},
            "explanation": "元组通常写作 (1, 2, 3)；方括号是列表，花括号用于字典或集合。",
        },
        {
            "type": "fill_blank",
            "stem": "元组 t = (1, 2, 3) 的 len(t) 结果是 ____。",
            "answer": {"values": ["3"]},
            "explanation": "元组包含 3 个元素，len 返回 3。",
        },
        {
            "type": "code_analysis",
            "stem": "阅读代码：\nt = (1, 2, 3)\nprint(t[1])\n输出是什么？请说明下标从几开始以及 t[1] 的含义。",
            "answer": {
                "reference": "输出 2。元组下标从 0 开始，t[0] 是 1，t[1] 是 2。",
                "keywords": ["2", "下标", "0", "t[1]"],
            },
            "explanation": "t[1] 取第二个元素，即 2。",
        },
    ],
    "python-basics-06-03": [
        {
            "type": "multiple_choice",
            "stem": "关于字典，正确的有？",
            "options": [
                {"key": "A", "text": "使用键值对保存数据"},
                {"key": "B", "text": "通过键访问值"},
                {"key": "C", "text": "键必须唯一"},
                {"key": "D", "text": "字典只能保存数字"},
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": "字典以键值对存储数据，键唯一；值可以是多种类型。",
        },
        {
            "type": "true_false",
            "stem": "字典 d = {\"a\": 1} 中，可以通过 d[\"a\"] 得到 1。",
            "answer": {"value": True},
            "explanation": "字典使用方括号加键访问对应的值。",
        },
        {
            "type": "short_answer",
            "stem": "说明字典的键与值分别是什么，并给出一个字典例子。",
            "answer": {
                "reference": "字典由键值对组成，键用于查找，值是与键关联的数据；例如 {\"name\": \"小码\", \"age\": 1}，通过键 name 可以取得值 小码。",
                "keywords": ["键", "值", "字典"],
            },
            "explanation": "键是查找依据，值是被保存的数据。",
        },
    ],
    "python-basics-06-04": [
        {
            "type": "single_choice",
            "stem": "Python 集合 set 的主要特点是什么？",
            "options": [
                {"key": "A", "text": "元素不重复"},
                {"key": "B", "text": "元素按顺序排列"},
                {"key": "C", "text": "只能保存字符串"},
                {"key": "D", "text": "不能添加元素"},
            ],
            "answer": {"value": "A"},
            "explanation": "集合的元素唯一且无序，可用于去重。",
        },
        {
            "type": "single_choice",
            "stem": "创建空集合的正确写法是？",
            "options": [
                {"key": "A", "text": "set()"},
                {"key": "B", "text": "{}"},
                {"key": "C", "text": "[]"},
                {"key": "D", "text": "()"},
            ],
            "answer": {"value": "A"},
            "explanation": "{} 创建的是空字典，空集合必须使用 set()。",
        },
        {
            "type": "code_writing",
            "stem": "文本代码：创建集合 s = {1, 2, 2, 3}，输出集合长度，并添加元素 4。",
            "answer": {
                "reference": "s = {1, 2, 2, 3}\nprint(len(s))\ns.add(4)",
                "keywords": ["s =", "len", "add", "4", "print"],
            },
            "explanation": "重复元素会被集合去重，因此长度为 3；add 添加新元素。",
        },
    ],
    "python-basics-06-05": [
        {
            "type": "single_choice",
            "stem": "要按顺序保存多个可修改的元素，最适合使用哪种结构？",
            "options": [
                {"key": "A", "text": "列表 list"},
                {"key": "B", "text": "元组 tuple"},
                {"key": "C", "text": "集合 set"},
                {"key": "D", "text": "字符串 str"},
            ],
            "answer": {"value": "A"},
            "explanation": "列表有序且可变，适合保存需要修改的元素序列。",
        },
        {
            "type": "multiple_choice",
            "stem": "关于列表、元组、字典、集合，正确的有？",
            "options": [
                {"key": "A", "text": "列表可变"},
                {"key": "B", "text": "元组通常不可变"},
                {"key": "C", "text": "字典按键访问值"},
                {"key": "D", "text": "集合保证元素顺序"},
            ],
            "answer": {"values": ["A", "B", "C"]},
            "explanation": "集合不保证元素顺序，因此 D 不正确；其余描述正确。",
        },
        {
            "type": "code_writing",
            "stem": "文本代码：创建列表 scores = [80, 90, 100]，计算平均分并输出。",
            "answer": {
                "reference": "scores = [80, 90, 100]\naverage = sum(scores) / len(scores)\nprint(average)",
                "keywords": ["scores", "sum", "len", "average", "print"],
            },
            "explanation": "总和除以元素个数得到平均分，结果为 90.0。",
        },
    ],
}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).casefold())


def validate_question_definitions() -> None:
    """校验种子结构（含重复题干/选项）；发现配置错误时在写库前抛出异常。"""
    if len(QUESTION_SEED) != 31:
        raise ValueError(f"内置题库应覆盖 31 个知识点，实际为 {len(QUESTION_SEED)}")
    types_seen: set[str] = set()
    stems_seen: dict[str, str] = {}
    for kp_code, items in QUESTION_SEED.items():
        if len(items) != 3:
            raise ValueError(f"{kp_code} 应包含 3 道题，实际为 {len(items)}")
        for index, item in enumerate(items, start=1):
            label = f"{kp_code} 第 {index} 题"
            question_type = item.get("type")
            if question_type not in QUESTION_TYPES:
                raise ValueError(f"{label} 题型不合法：{question_type}")
            types_seen.add(question_type)
            stem = str(item.get("stem") or "").strip()
            explanation = str(item.get("explanation") or "").strip()
            if len(stem) < 8:
                raise ValueError(f"{label} 题干过短")
            normalized_stem = _normalize(stem)
            if normalized_stem in stems_seen:
                raise ValueError(
                    f"{label} 题干与 {stems_seen[normalized_stem]} 重复"
                )
            stems_seen[normalized_stem] = label
            if len(explanation) < 10:
                raise ValueError(f"{label} 解析过短")
            answer = item.get("answer")
            if not isinstance(answer, dict):
                raise ValueError(f"{label} 答案必须是 JSON 对象")
            options = item.get("options") or []
            keys = [option.get("key") for option in options]
            if question_type in ("single_choice", "multiple_choice"):
                option_texts = [
                    str(option.get("text") or "").strip() for option in options
                ]
                if (
                    not 2 <= len(options) <= 6
                    or len(keys) != len(set(keys))
                    or any(not text for text in option_texts)
                    or len(option_texts) != len(set(option_texts))
                ):
                    raise ValueError(f"{label} 选项配置不合法")
                if question_type == "single_choice":
                    if answer.get("value") not in keys:
                        raise ValueError(f"{label} 单选答案不在选项中")
                else:
                    values = answer.get("values")
                    if (
                        not isinstance(values, list)
                        or len(values) < 2
                        or any(value not in keys for value in values)
                    ):
                        raise ValueError(f"{label} 多选答案配置不合法")
            elif question_type == "true_false":
                if not isinstance(answer.get("value"), bool):
                    raise ValueError(f"{label} 判断题答案必须为布尔值")
            elif question_type == "fill_blank":
                values = answer.get("values")
                if (
                    not isinstance(values, list)
                    or not values
                    or any(not str(value).strip() for value in values)
                ):
                    raise ValueError(f"{label} 填空题答案配置不合法")
            else:
                reference = str(answer.get("reference") or "").strip()
                keywords = answer.get("keywords")
                if len(reference) < 5:
                    raise ValueError(f"{label} 主观题参考答案过短")
                if not isinstance(keywords, list) or not 3 <= len(keywords) <= 8:
                    raise ValueError(f"{label} 主观题关键词数量必须为 3-8")
                normalized = _normalize(reference)
                for keyword in keywords:
                    if _normalize(str(keyword)) not in normalized:
                        raise ValueError(
                            f"{label} 关键词「{keyword}」未出现在参考答案中"
                        )
    missing_types = set(QUESTION_TYPES) - types_seen
    if missing_types:
        raise ValueError(f"内置题库未覆盖题型：{sorted(missing_types)}")


def seed_questions(db: Session) -> dict[str, int]:
    """幂等写入内置题库；返回创建/更新/总数统计。"""
    validate_question_definitions()
    repo = QuestionRepository(db)

    kp_codes = list(QUESTION_SEED.keys())
    knowledge_points = list(
        db.scalars(
            select(KnowledgePoint).where(
                KnowledgePoint.code.in_(kp_codes),
                KnowledgePoint.deleted_at.is_(None),
            )
        ).all()
    )
    kp_map = {kp.code: kp for kp in knowledge_points}
    missing = [code for code in kp_codes if code not in kp_map]
    if missing:
        raise RuntimeError(
            "题库种子依赖的课程知识点不存在，请先执行 seed-courses："
            + "、".join(missing)
        )

    created = 0
    updated = 0
    for kp_code in kp_codes:
        knowledge_point = kp_map[kp_code]
        for index, item in enumerate(QUESTION_SEED[kp_code], start=1):
            code = f"q-{kp_code}-{index}"
            existing = repo.get_by_code(code)
            if existing is not None and existing.source != "builtin":
                raise RuntimeError(
                    f"题目 code {code} 已被非内置题目占用，拒绝覆盖"
                )
            values = {
                "knowledge_point_id": knowledge_point.id,
                "question_type": item["type"],
                "stem": item["stem"].strip(),
                "options": item.get("options"),
                "correct_answer": item["answer"],
                "explanation": item["explanation"].strip(),
                "difficulty": knowledge_point.difficulty,
                "source": "builtin",
                "status": "approved",
                "validation_status": "builtin",
                "validation_notes": BUILTIN_NOTE,
                "generated_from_id": None,
                "validated_at": None,
            }
            if existing is None:
                repo.add(Question(code=code, **values))
                created += 1
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
                updated += 1

    repo.flush()
    db.commit()
    return {
        "created": created,
        "updated": updated,
        "total": created + updated,
    }
