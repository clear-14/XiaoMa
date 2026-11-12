"""课程种子数据：首发课程「Python 零基础入门」。

设计约定：
- 课程/章节/知识点均使用稳定业务 code（如 python-basics-01-01），前置关系以 code 引用；
- 种子函数幂等：按 code upsert，重复执行更新内容而不产生重复课程/章节/知识点，
  前置关系按「目标集合 - 现有集合」差集同步（新增缺失、清除多余）；
- 本数据为人工编写与审核的初始课程内容。后续扩展课程内容须经产品确认，
  不允许 AI 自由生成课程目录并直接写入；
- 种子只做 upsert，不删除种子中已不存在的行（避免误删用户学习数据）。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.course import (
    Chapter,
    Course,
    CourseContent,
    KnowledgePoint,
    Lesson,
    LessonKnowledgePoint,
)

# ---------------------------------------------------------------------------
# 种子数据定义
# ---------------------------------------------------------------------------

SEED_COURSE: dict = {
    "code": "python-basics",
    "name": "Python 零基础入门",
    "description": (
        "小码首发课程，面向零基础学习者：从 Python 环境搭建到函数与常用数据结构，"
        "覆盖编程入门所需的核心语法与思维训练。每个知识点配有学习目标、预计学习时间、"
        "掌握标准与学习资源，按前置依赖关系组织学习路径。"
    ),
    # 方向与等级分开：direction 是课程分类 code，recommended_level 是能力等级。
    "direction": "python-fundamentals",
    "difficulty": "beginner",
    "recommended_level": "L0",
    "version": "1.0.0",
    "publish_status": "published",
    "sort_order": 1,
    "chapters": [
        {
            "code": "python-basics-01",
            "title": "初识 Python",
            "description": "认识编程与 Python，完成环境搭建，写出第一个程序。",
            "knowledge_points": [
                {
                    "code": "python-basics-01-01",
                    "name": "什么是编程与 Python",
                    "learning_goal": "理解编程与 Python 的基本概念，了解 Python 的典型应用场景",
                    "difficulty": "beginner",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能用自己的话解释什么是编程、为什么选择 Python，并说出至少 3 个 Python 典型应用场景",
                    "resources": [
                        {"type": "documentation", "title": "Python 官方介绍", "url": "https://www.python.org/about/"},
                    ],
                    "prerequisites": [],
                },
                {
                    "code": "python-basics-01-02",
                    "name": "安装与运行 Python",
                    "learning_goal": "能在本机安装 Python 并成功运行第一条命令",
                    "difficulty": "beginner",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能独立完成 Python 安装，在命令行运行 python --version 并看到正确的版本号输出",
                    "resources": [
                        {"type": "documentation", "title": "Python 官方下载", "url": "https://www.python.org/downloads/"},
                    ],
                    "prerequisites": [],
                },
                {
                    "code": "python-basics-01-03",
                    "name": "第一个程序：print 输出",
                    "learning_goal": "掌握 print() 的基本用法，能输出文本与数字",
                    "difficulty": "beginner",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能使用 print() 输出字符串、数字和多个值，并解释引号的作用",
                    "resources": [
                        {"type": "documentation", "title": "内置函数 print", "url": "https://docs.python.org/3/library/functions.html#print"},
                    ],
                    "prerequisites": ["python-basics-01-02"],
                },
                {
                    "code": "python-basics-01-04",
                    "name": "注释与代码规范",
                    "learning_goal": "掌握单行与多行注释的写法，理解代码可读性的意义",
                    "difficulty": "beginner",
                    "estimated_minutes": 10,
                    "mastery_criteria": "能正确书写 # 单行注释与三引号多行注释，并说明注释的用途",
                    "resources": [
                        {"type": "documentation", "title": "Python 教程：注释", "url": "https://docs.python.org/3/tutorial/introduction.html#comments"},
                    ],
                    "prerequisites": ["python-basics-01-03"],
                },
                {
                    "code": "python-basics-01-05",
                    "name": "输入 input() 与用户交互",
                    "learning_goal": "掌握 input() 读取用户输入，完成简单的输入输出交互",
                    "difficulty": "beginner",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能使用 input() 接收用户输入并配合 print() 完成一次完整的问答交互",
                    "resources": [
                        {"type": "documentation", "title": "内置函数 input", "url": "https://docs.python.org/3/library/functions.html#input"},
                    ],
                    "prerequisites": ["python-basics-01-03"],
                },
            ],
        },
        {
            "code": "python-basics-02",
            "title": "变量与数据类型",
            "description": "掌握变量、数字、字符串、布尔值与类型转换，为后续所有编程打基础。",
            "knowledge_points": [
                {
                    "code": "python-basics-02-01",
                    "name": "变量与赋值",
                    "learning_goal": "理解变量的概念与赋值语句，掌握变量命名规则",
                    "difficulty": "beginner",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能正确命名变量并赋值，解释变量与值的区别，不使用 Python 关键字命名",
                    "resources": [
                        {"type": "documentation", "title": "Python 教程：变量", "url": "https://docs.python.org/3/tutorial/introduction.html"},
                    ],
                    "prerequisites": ["python-basics-01-03"],
                },
                {
                    "code": "python-basics-02-02",
                    "name": "数字类型：整数与浮点数",
                    "learning_goal": "掌握 int 与 float 的使用与基本运算",
                    "difficulty": "beginner",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能创建 int/float 变量并完成加、减、乘、除运算，理解整数与浮点数的区别",
                    "resources": [
                        {"type": "documentation", "title": "数字类型", "url": "https://docs.python.org/3/library/stdtypes.html#numeric-types-int-float-complex"},
                    ],
                    "prerequisites": ["python-basics-02-01"],
                },
                {
                    "code": "python-basics-02-03",
                    "name": "字符串基础",
                    "learning_goal": "掌握字符串的创建、拼接与常见操作",
                    "difficulty": "beginner",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能使用单引号/双引号创建字符串，完成拼接、重复和取长度等操作",
                    "resources": [
                        {"type": "documentation", "title": "字符串类型", "url": "https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str"},
                    ],
                    "prerequisites": ["python-basics-02-01"],
                },
                {
                    "code": "python-basics-02-04",
                    "name": "布尔类型与比较",
                    "learning_goal": "理解 True/False 与比较运算的结果类型",
                    "difficulty": "beginner",
                    "estimated_minutes": 10,
                    "mastery_criteria": "能判断任意比较运算的结果类型，理解布尔值在条件判断中的作用",
                    "resources": [
                        {"type": "documentation", "title": "真值判断", "url": "https://docs.python.org/3/library/stdtypes.html#truth-value-testing"},
                    ],
                    "prerequisites": ["python-basics-02-01"],
                },
                {
                    "code": "python-basics-02-05",
                    "name": "类型转换",
                    "learning_goal": "掌握 int()/float()/str() 等常用类型转换",
                    "difficulty": "beginner",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能在不同类型之间正确转换，并处理 input() 返回的字符串转数字",
                    "resources": [
                        {"type": "documentation", "title": "内置类型转换函数", "url": "https://docs.python.org/3/library/functions.html#int"},
                    ],
                    "prerequisites": ["python-basics-02-02", "python-basics-02-03"],
                },
                {
                    "code": "python-basics-02-06",
                    "name": "字符串格式化与 f-string",
                    "learning_goal": "掌握 f-string 格式化输出",
                    "difficulty": "beginner",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能使用 f-string 将变量嵌入字符串输出，正确书写花括号转义",
                    "resources": [
                        {"type": "documentation", "title": "格式化字符串字面量", "url": "https://docs.python.org/3/tutorial/inputoutput.html#formatted-string-literals"},
                    ],
                    "prerequisites": ["python-basics-02-03"],
                },
            ],
        },
        {
            "code": "python-basics-03",
            "title": "运算符与表达式",
            "description": "掌握算术、比较、逻辑运算符与表达式求值规则。",
            "knowledge_points": [
                {
                    "code": "python-basics-03-01",
                    "name": "算术运算符",
                    "learning_goal": "掌握 + - * / // % ** 运算符",
                    "difficulty": "beginner",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能解释每种算术运算符的含义，正确计算整除、取余和幂运算",
                    "resources": [
                        {"type": "documentation", "title": "二元算术运算", "url": "https://docs.python.org/3/reference/expressions.html#binary-arithmetic-operations"},
                    ],
                    "prerequisites": ["python-basics-02-02"],
                },
                {
                    "code": "python-basics-03-02",
                    "name": "比较运算符",
                    "learning_goal": "掌握 == != < > <= >= 及比较结果",
                    "difficulty": "beginner",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能使用比较运算符比较数字与字符串，说明比较运算返回布尔值",
                    "resources": [
                        {"type": "documentation", "title": "比较运算", "url": "https://docs.python.org/3/reference/expressions.html#comparisons"},
                    ],
                    "prerequisites": ["python-basics-02-01"],
                },
                {
                    "code": "python-basics-03-03",
                    "name": "逻辑运算符",
                    "learning_goal": "掌握 and / or / not 的用法与短路特性",
                    "difficulty": "beginner",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能组合多个条件进行逻辑判断，理解短路求值",
                    "resources": [
                        {"type": "documentation", "title": "布尔运算 and/or/not", "url": "https://docs.python.org/3/library/stdtypes.html#boolean-operations-and-or-not"},
                    ],
                    "prerequisites": ["python-basics-02-04"],
                },
                {
                    "code": "python-basics-03-04",
                    "name": "运算符优先级与表达式",
                    "learning_goal": "理解运算符优先级，能正确读写复合表达式",
                    "difficulty": "intermediate",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能判断常见表达式的求值顺序，必要时使用括号让代码意图清晰",
                    "resources": [
                        {"type": "documentation", "title": "运算符优先级", "url": "https://docs.python.org/3/reference/expressions.html#operator-precedence"},
                    ],
                    "prerequisites": ["python-basics-03-01", "python-basics-03-02", "python-basics-03-03"],
                },
            ],
        },
        {
            "code": "python-basics-04",
            "title": "流程控制",
            "description": "掌握条件判断与循环，让程序能够根据不同情况做出决策。",
            "knowledge_points": [
                {
                    "code": "python-basics-04-01",
                    "name": "条件判断 if / elif / else",
                    "learning_goal": "掌握条件分支的写法与执行流程",
                    "difficulty": "beginner",
                    "estimated_minutes": 25,
                    "mastery_criteria": "能编写含 if/elif/else 的程序处理多分支逻辑，并说明各分支的触发条件",
                    "resources": [
                        {"type": "documentation", "title": "if 语句", "url": "https://docs.python.org/3/tutorial/controlflow.html#if-statements"},
                    ],
                    "prerequisites": ["python-basics-03-02"],
                },
                {
                    "code": "python-basics-04-02",
                    "name": "缩进与代码块",
                    "learning_goal": "理解 Python 缩进规则及其对代码块的作用",
                    "difficulty": "beginner",
                    "estimated_minutes": 10,
                    "mastery_criteria": "能按规范使用 4 空格缩进书写嵌套代码块，说明缩进不一致导致的后果",
                    "resources": [
                        {"type": "documentation", "title": "缩进规则", "url": "https://docs.python.org/3/reference/lexical_analysis.html#indentation"},
                    ],
                    "prerequisites": ["python-basics-04-01"],
                },
                {
                    "code": "python-basics-04-03",
                    "name": "while 循环",
                    "learning_goal": "掌握 while 循环与循环条件控制",
                    "difficulty": "beginner",
                    "estimated_minutes": 25,
                    "mastery_criteria": "能使用 while 完成重复执行，正确设置循环条件避免死循环",
                    "resources": [
                        {"type": "documentation", "title": "while 语句", "url": "https://docs.python.org/3/reference/compound_stmts.html#while"},
                    ],
                    "prerequisites": ["python-basics-03-01"],
                },
                {
                    "code": "python-basics-04-04",
                    "name": "for 循环与 range",
                    "learning_goal": "掌握 for 循环遍历与 range 的使用",
                    "difficulty": "beginner",
                    "estimated_minutes": 25,
                    "mastery_criteria": "能使用 for + range 完成固定次数循环，并遍历字符串等可迭代对象",
                    "resources": [
                        {"type": "documentation", "title": "for 语句", "url": "https://docs.python.org/3/tutorial/controlflow.html#for-statements"},
                    ],
                    "prerequisites": ["python-basics-03-01"],
                },
                {
                    "code": "python-basics-04-05",
                    "name": "break 与 continue",
                    "learning_goal": "掌握循环中断与跳过的控制语句",
                    "difficulty": "intermediate",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能在循环中正确使用 break 提前退出、continue 跳过本次迭代",
                    "resources": [
                        {"type": "documentation", "title": "break 与 continue", "url": "https://docs.python.org/3/tutorial/controlflow.html#break-and-continue-statements"},
                    ],
                    "prerequisites": ["python-basics-04-03", "python-basics-04-04"],
                },
                {
                    "code": "python-basics-04-06",
                    "name": "循环嵌套与综合练习",
                    "learning_goal": "能组合循环与条件解决简单编程问题",
                    "difficulty": "intermediate",
                    "estimated_minutes": 30,
                    "mastery_criteria": "能独立完成如乘法口诀表、猜数字等综合练习，代码结构清晰",
                    "resources": [
                        {"type": "exercise", "title": "综合练习：乘法口诀表", "url": None},
                        {"type": "exercise", "title": "综合练习：猜数字游戏", "url": None},
                    ],
                    "prerequisites": ["python-basics-04-03", "python-basics-04-04"],
                },
            ],
        },
        {
            "code": "python-basics-05",
            "title": "函数与模块",
            "description": "学会用函数组织代码、复用逻辑，并利用模块扩展程序能力。",
            "knowledge_points": [
                {
                    "code": "python-basics-05-01",
                    "name": "定义函数 def",
                    "learning_goal": "掌握函数定义与调用",
                    "difficulty": "beginner",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能用 def 定义无参函数并正确调用，说明函数复用的意义",
                    "resources": [
                        {"type": "documentation", "title": "定义函数", "url": "https://docs.python.org/3/tutorial/controlflow.html#defining-functions"},
                    ],
                    "prerequisites": ["python-basics-04-01"],
                },
                {
                    "code": "python-basics-05-02",
                    "name": "参数与返回值",
                    "learning_goal": "掌握位置参数、默认参数与 return 返回值",
                    "difficulty": "beginner",
                    "estimated_minutes": 25,
                    "mastery_criteria": "能定义带参数的函数并使用 return 返回结果，区分默认参数与实参",
                    "resources": [
                        {"type": "documentation", "title": "函数参数与返回值", "url": "https://docs.python.org/3/tutorial/controlflow.html#more-on-defining-functions"},
                    ],
                    "prerequisites": ["python-basics-05-01"],
                },
                {
                    "code": "python-basics-05-03",
                    "name": "变量作用域",
                    "learning_goal": "理解局部变量与全局变量的作用域规则",
                    "difficulty": "intermediate",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能判断变量在函数内外的可见性，解释局部与全局作用域的区别",
                    "resources": [
                        {"type": "documentation", "title": "Python 作用域", "url": "https://docs.python.org/3/tutorial/classes.html#python-scopes-and-namespaces"},
                    ],
                    "prerequisites": ["python-basics-05-01"],
                },
                {
                    "code": "python-basics-05-04",
                    "name": "模块与 import",
                    "learning_goal": "掌握模块导入与标准库使用",
                    "difficulty": "intermediate",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能使用 import 导入模块并调用其函数，了解 from ... import 的用法",
                    "resources": [
                        {"type": "documentation", "title": "模块", "url": "https://docs.python.org/3/tutorial/modules.html"},
                    ],
                    "prerequisites": ["python-basics-05-01"],
                },
                {
                    "code": "python-basics-05-05",
                    "name": "常用内置函数",
                    "learning_goal": "掌握 len/max/min/sum/abs 等常用内置函数",
                    "difficulty": "beginner",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能正确使用常用内置函数处理数字与序列，并会查阅官方文档",
                    "resources": [
                        {"type": "documentation", "title": "内置函数", "url": "https://docs.python.org/3/library/functions.html"},
                    ],
                    "prerequisites": ["python-basics-02-05"],
                },
            ],
        },
        {
            "code": "python-basics-06",
            "title": "常用数据结构",
            "description": "掌握列表、元组、字典、集合，能够组织与处理批量数据。",
            "knowledge_points": [
                {
                    "code": "python-basics-06-01",
                    "name": "列表 list",
                    "learning_goal": "掌握列表的创建、索引、切片与常用方法",
                    "difficulty": "beginner",
                    "estimated_minutes": 30,
                    "mastery_criteria": "能创建列表并完成增删改查、切片与遍历，理解列表可变性",
                    "resources": [
                        {"type": "documentation", "title": "列表", "url": "https://docs.python.org/3/tutorial/datastructures.html"},
                    ],
                    "prerequisites": ["python-basics-02-01", "python-basics-04-04"],
                },
                {
                    "code": "python-basics-06-02",
                    "name": "元组 tuple",
                    "learning_goal": "掌握元组的创建与不可变特性",
                    "difficulty": "beginner",
                    "estimated_minutes": 15,
                    "mastery_criteria": "能创建并访问元组，说明元组与列表的区别及适用场景",
                    "resources": [
                        {"type": "documentation", "title": "元组与序列", "url": "https://docs.python.org/3/tutorial/datastructures.html#tuples-and-sequences"},
                    ],
                    "prerequisites": ["python-basics-06-01"],
                },
                {
                    "code": "python-basics-06-03",
                    "name": "字典 dict",
                    "learning_goal": "掌握字典的键值存取与常用方法",
                    "difficulty": "beginner",
                    "estimated_minutes": 25,
                    "mastery_criteria": "能创建字典并完成键值对的增删改查与遍历，理解键的唯一性",
                    "resources": [
                        {"type": "documentation", "title": "字典", "url": "https://docs.python.org/3/tutorial/datastructures.html#dictionaries"},
                    ],
                    "prerequisites": ["python-basics-02-01", "python-basics-04-04"],
                },
                {
                    "code": "python-basics-06-04",
                    "name": "集合 set",
                    "learning_goal": "掌握集合的创建、去重与集合运算",
                    "difficulty": "intermediate",
                    "estimated_minutes": 20,
                    "mastery_criteria": "能使用集合去重并完成交集、并集、差集运算",
                    "resources": [
                        {"type": "documentation", "title": "集合", "url": "https://docs.python.org/3/tutorial/datastructures.html#sets"},
                    ],
                    "prerequisites": ["python-basics-06-01"],
                },
                {
                    "code": "python-basics-06-05",
                    "name": "数据结构综合运用",
                    "learning_goal": "能根据问题选择合适的数据结构解决综合问题",
                    "difficulty": "intermediate",
                    "estimated_minutes": 40,
                    "mastery_criteria": "能独立完成如统计词频、学生成绩管理等综合练习，合理选用列表/字典/集合",
                    "resources": [
                        {"type": "exercise", "title": "综合练习：统计词频", "url": None},
                        {"type": "exercise", "title": "综合练习：学生成绩管理", "url": None},
                    ],
                    "prerequisites": ["python-basics-06-01", "python-basics-06-03", "python-basics-06-04"],
                },
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# 课时目录（阶段 2）
#
# 每章拆成 2~3 个课时，知识点按主题显式归属（不按顺序猜测）。
# 课时 code 统一为「章节 code + -lesson-NN」，其中第 01 个课时沿用了阶段 1
# 迁移为既有章节生成的默认课时 code，因此重复执行不会产生重复课时。
# 课时时长由所属知识点时长求和得出，不单独手填，避免与知识点数据漂移。
# ---------------------------------------------------------------------------

LESSON_PLAN: list[dict] = [
    {
        "chapter": "python-basics-01",
        "lessons": [
            {
                "title": "认识编程与 Python 环境",
                "description": "理解编程与 Python 的定位，完成本机环境安装并验证运行。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-01-01",
                    "python-basics-01-02",
                ],
            },
            {
                "title": "第一个程序与输入输出",
                "description": "用 print 输出、用 input 接收输入，并养成写注释的习惯。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-01-03",
                    "python-basics-01-04",
                    "python-basics-01-05",
                ],
            },
        ],
    },
    {
        "chapter": "python-basics-02",
        "lessons": [
            {
                "title": "变量、数字与字符串",
                "description": "建立变量概念，掌握整数、浮点数与字符串的创建和基本操作。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-02-01",
                    "python-basics-02-02",
                    "python-basics-02-03",
                ],
            },
            {
                "title": "布尔、类型转换与格式化",
                "description": "理解布尔值与真值判断，完成类型转换并用 f-string 输出。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-02-04",
                    "python-basics-02-05",
                    "python-basics-02-06",
                ],
            },
        ],
    },
    {
        "chapter": "python-basics-03",
        "lessons": [
            {
                "title": "算术、比较与逻辑运算",
                "description": "掌握三类运算符，能组合条件并理解短路求值。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-03-01",
                    "python-basics-03-02",
                    "python-basics-03-03",
                ],
            },
            {
                "title": "运算符优先级与表达式",
                "description": "判断复合表达式的求值顺序，用括号让意图更清晰。",
                "difficulty": "intermediate",
                "knowledge_points": ["python-basics-03-04"],
            },
        ],
    },
    {
        "chapter": "python-basics-04",
        "lessons": [
            {
                "title": "条件判断与代码块",
                "description": "用 if/elif/else 处理多分支，理解缩进与代码块的关系。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-04-01",
                    "python-basics-04-02",
                ],
            },
            {
                "title": "循环基础：while 与 for",
                "description": "掌握两种循环的写法与适用场景，正确设置循环条件。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-04-03",
                    "python-basics-04-04",
                ],
            },
            {
                "title": "循环控制与综合练习",
                "description": "用 break/continue 控制流程，完成乘法口诀表与猜数字练习。",
                "difficulty": "intermediate",
                "knowledge_points": [
                    "python-basics-04-05",
                    "python-basics-04-06",
                ],
            },
        ],
    },
    {
        "chapter": "python-basics-05",
        "lessons": [
            {
                "title": "函数定义、参数与返回值",
                "description": "用 def 组织可复用逻辑，掌握参数传递与 return。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-05-01",
                    "python-basics-05-02",
                ],
            },
            {
                "title": "作用域、模块与内置函数",
                "description": "理解变量可见范围，用 import 复用标准库与常用内置函数。",
                "difficulty": "intermediate",
                "knowledge_points": [
                    "python-basics-05-03",
                    "python-basics-05-04",
                    "python-basics-05-05",
                ],
            },
        ],
    },
    {
        "chapter": "python-basics-06",
        "lessons": [
            {
                "title": "列表与元组",
                "description": "掌握有序序列的增删改查与切片，理解可变与不可变的取舍。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-06-01",
                    "python-basics-06-02",
                ],
            },
            {
                "title": "字典与集合",
                "description": "用键值对组织数据，用集合去重并完成集合运算。",
                "difficulty": "beginner",
                "knowledge_points": [
                    "python-basics-06-03",
                    "python-basics-06-04",
                ],
            },
            {
                "title": "数据结构综合运用",
                "description": "根据问题选择合适的数据结构，完成词频统计与成绩管理练习。",
                "difficulty": "intermediate",
                "knowledge_points": ["python-basics-06-05"],
            },
        ],
    },
]


def _validate_lesson_plan() -> None:
    """写库前校验课时目录：章节存在、知识点归属唯一且属于该章节。"""
    chapter_kp_codes = {
        chapter["code"]: {kp["code"] for kp in chapter["knowledge_points"]}
        for chapter in SEED_COURSE["chapters"]
    }
    for item in LESSON_PLAN:
        chapter_code = item["chapter"]
        if chapter_code not in chapter_kp_codes:
            raise ValueError(f"课时目录引用了不存在的章节：{chapter_code}")
        seen: set[str] = set()
        for lesson in item["lessons"]:
            if not lesson["title"].strip():
                raise ValueError(f"{chapter_code} 存在没有标题的课时")
            for kp_code in lesson["knowledge_points"]:
                if kp_code not in chapter_kp_codes[chapter_code]:
                    raise ValueError(
                        f"课时「{lesson['title']}」引用了不属于 {chapter_code} 的知识点：{kp_code}"
                    )
                if kp_code in seen:
                    raise ValueError(f"知识点 {kp_code} 被重复分配到多个课时")
                seen.add(kp_code)
        missing = chapter_kp_codes[chapter_code] - seen
        if missing:
            raise ValueError(
                f"章节 {chapter_code} 有知识点未分配课时：{sorted(missing)}"
            )


# ---------------------------------------------------------------------------
# 种子写入（幂等 upsert）
# ---------------------------------------------------------------------------


def _upsert_course(db: Session, data: dict) -> Course:
    course = db.scalars(select(Course).where(Course.code == data["code"])).first()
    if course is None:
        course = Course(code=data["code"])
        db.add(course)
    course.name = data["name"]
    course.description = data["description"]
    # 学习目标属课程内容：种子未提供时保留既有值，避免把目录种子写入的目标抹掉
    if data.get("learning_objectives"):
        course.learning_objectives = data["learning_objectives"]
    course.direction = data.get("direction")
    course.difficulty = data.get("difficulty")
    course.recommended_level = data.get("recommended_level")
    course.version = data.get("version", "1.0.0")
    course.publish_status = data.get("publish_status", "published")
    course.sort_order = data.get("sort_order", 0)
    return course


def _upsert_chapter(db: Session, course: Course, data: dict) -> Chapter:
    chapter = db.scalars(select(Chapter).where(Chapter.code == data["code"])).first()
    if chapter is None:
        chapter = Chapter(code=data["code"])
        db.add(chapter)
    chapter.course = course
    chapter.title = data["title"]
    chapter.description = data["description"]
    chapter.order_index = data.get("order_index", 0)
    return chapter


def _upsert_knowledge_point(db: Session, chapter: Chapter, data: dict) -> KnowledgePoint:
    kp = db.scalars(select(KnowledgePoint).where(KnowledgePoint.code == data["code"])).first()
    if kp is None:
        kp = KnowledgePoint(code=data["code"])
        db.add(kp)
    kp.chapter = chapter
    kp.name = data["name"]
    kp.learning_goal = data["learning_goal"]
    kp.difficulty = data["difficulty"]
    kp.estimated_minutes = data["estimated_minutes"]
    kp.mastery_criteria = data["mastery_criteria"]
    kp.resources = data.get("resources")
    kp.order_index = data.get("order_index", 0)
    return kp


def _upsert_lesson(db: Session, chapter: Chapter, data: dict) -> Lesson:
    lesson = db.scalars(select(Lesson).where(Lesson.code == data["code"])).first()
    if lesson is None:
        lesson = Lesson(code=data["code"])
        db.add(lesson)
    lesson.chapter = chapter
    lesson.title = data["title"]
    lesson.description = data.get("description")
    lesson.difficulty = data.get("difficulty")
    lesson.estimated_minutes = data.get("estimated_minutes")
    lesson.order_index = data.get("order_index", 0)
    return lesson


def _link_knowledge_point_to_lesson(
    db: Session, lesson: Lesson, kp: KnowledgePoint
) -> None:
    """建立/纠正知识点与课时的一对一归属（knowledge_point_id 唯一）。"""
    link = db.scalars(
        select(LessonKnowledgePoint).where(
            LessonKnowledgePoint.knowledge_point_id == kp.id
        )
    ).first()
    if link is None:
        db.add(
            LessonKnowledgePoint(
                lesson_id=lesson.id,
                knowledge_point_id=kp.id,
                order_index=kp.order_index,
            )
        )
        return
    if link.lesson_id != lesson.id:
        link.lesson_id = lesson.id
    link.order_index = kp.order_index


def _lesson_plan_for(chapter_code: str, chapter_data: dict) -> list[dict]:
    """该章的课时定义（已规范化 code、顺序与知识点归属）。

    有显式课时目录时按目录返回；没有时回退为「一章一课时」，
    保证新增章节不因缺少课时目录而无法落库。
    """
    for item in LESSON_PLAN:
        if item["chapter"] != chapter_code:
            continue
        return [
            {
                "code": f"{chapter_code}-lesson-{index:02d}",
                "title": lesson["title"],
                "description": lesson.get("description"),
                "difficulty": lesson.get("difficulty"),
                "knowledge_points": list(lesson["knowledge_points"]),
            }
            for index, lesson in enumerate(item["lessons"], start=1)
        ]
    return [
        {
            "code": f"{chapter_code}-lesson-01",
            "title": chapter_data["title"],
            "description": chapter_data.get("description"),
            "difficulty": None,
            "knowledge_points": [
                kp["code"] for kp in chapter_data["knowledge_points"]
            ],
        }
    ]


def _has_textbook_content(db: Session, course: Course) -> bool:
    """课程是否已经进入教材模式（存在任一课时教学内容）。

    阶段 3 之后，课程目录与课时由 ``textbook_seed`` 维护；此时再执行本种子
    会把目录改回旧版 6 章 14 课时并清空知识点归属，因此需要跳过。
    """
    return bool(
        db.scalar(
            select(func.count())
            .select_from(CourseContent)
            .join(Lesson)
            .join(Chapter)
            .where(Chapter.course_id == course.id)
        )
    )


def seed_courses(db: Session) -> dict:
    """写入课程种子数据（幂等：重复执行不会产生重复课程/章节/课时/知识点）。

    返回统计：{"courses", "chapters", "lessons", "knowledge_points", "prerequisites"}。
    前置关系在全部知识点落库后按稳定 code 关联，支持跨章节引用。
    课时按 ``LESSON_PLAN`` 的显式目录创建，课时时长由所属知识点汇总，
    第 01 个课时复用阶段 1 迁移生成的默认课时 code，因此升级不产生重复课时。

    若该课程已存在教材内容（阶段 3 之后），直接返回现状并标记 skipped，
    避免旧目录覆盖新教材。
    """
    existing = db.scalars(
        select(Course).where(Course.code == SEED_COURSE["code"])
    ).first()
    if existing is not None and _has_textbook_content(db, existing):
        return {
            "courses": 1,
            "chapters": len(existing.chapters),
            "lessons": sum(len(ch.lessons) for ch in existing.chapters),
            "knowledge_points": sum(
                len(ch.knowledge_points) for ch in existing.chapters
            ),
            "prerequisites": 0,
            "skipped": "textbook",
        }

    _validate_lesson_plan()
    course = _upsert_course(db, SEED_COURSE)
    db.flush()

    kp_by_code: dict[str, KnowledgePoint] = {}
    chapter_count = 0
    lesson_count = 0
    kp_count = 0

    for ch_index, ch_data in enumerate(SEED_COURSE["chapters"], start=1):
        chapter = _upsert_chapter(db, course, {**ch_data, "order_index": ch_index})
        db.flush()
        chapter_count += 1

        # 先落知识点：课时预计时长需要按知识点汇总
        for kp_index, kp_data in enumerate(ch_data["knowledge_points"], start=1):
            kp = _upsert_knowledge_point(
                db, chapter, {**kp_data, "order_index": kp_index}
            )
            kp_by_code[kp.code] = kp
            kp_count += 1
        db.flush()

        plan = _lesson_plan_for(chapter.code, ch_data)
        chapter_lessons: list[Lesson] = []
        for lesson_index, lesson_data in enumerate(plan, start=1):
            minutes = sum(
                kp_by_code[code].estimated_minutes
                for code in lesson_data["knowledge_points"]
            )
            lesson = _upsert_lesson(
                db,
                chapter,
                {
                    "code": lesson_data["code"],
                    "title": lesson_data["title"],
                    "description": lesson_data["description"],
                    "difficulty": lesson_data["difficulty"],
                    "estimated_minutes": minutes,
                    "order_index": lesson_index,
                },
            )
            db.flush()
            chapter_lessons.append(lesson)
            lesson_count += 1

        # 知识点按目录归属课时（知识点的 lesson 关联一对一并带唯一约束）
        for lesson, lesson_data in zip(chapter_lessons, plan):
            for kp_code in lesson_data["knowledge_points"]:
                _link_knowledge_point_to_lesson(
                    db, lesson, kp_by_code[kp_code]
                )
        db.flush()

    # 课程预计时长：种子未显式指定时按全部知识点时长汇总
    if SEED_COURSE.get("estimated_minutes") is None:
        course.estimated_minutes = sum(
            kp.estimated_minutes for kp in kp_by_code.values()
        )
    else:
        course.estimated_minutes = SEED_COURSE["estimated_minutes"]

    # 前置关系同步：目标集合与现有集合求差集，只增补缺失、清除多余，天然幂等
    prereq_count = 0
    for ch_data in SEED_COURSE["chapters"]:
        for kp_data in ch_data["knowledge_points"]:
            kp = kp_by_code[kp_data["code"]]
            desired = {kp_by_code[c] for c in kp_data.get("prerequisites", [])}
            current = set(kp.prerequisites)
            for add in desired - current:
                kp.prerequisites.append(add)
                prereq_count += 1
            for remove in current - desired:
                kp.prerequisites.remove(remove)

    db.commit()
    return {
        "courses": 1,
        "chapters": chapter_count,
        "lessons": lesson_count,
        "knowledge_points": kp_count,
        "prerequisites": prereq_count,
    }
