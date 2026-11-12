"""第 17—20 章教材内容：JSON、异常处理、调试基础、综合练习。"""

CHAPTERS: list[dict] = [
    # ------------------------------------------------------------------ 第 17 章
    {
        "code": "python-basics-17",
        "order_index": 17,
        "title": "JSON 数据",
        "description": "把字典和列表存成通用格式：json.dumps 与 json.loads，读写配置文件与接口数据。",
        "lessons": [
            {
                "code": "python-basics-17-l01",
                "title": "JSON 格式与 json 模块",
                "description": "认识 JSON 的四种基本结构，用 dumps/loads 在字符串与对象之间转换。",
                "minutes": 55,
                "difficulty": "intermediate",
                "objectives": """1. 能看懂一段 JSON 并说出它对应 Python 的哪种类型。
2. 会用 json.dumps 把字典转成 JSON 字符串。
3. 会用 json.loads 把 JSON 字符串转回字典，并读写 JSON 文件。""",
                "why_learn": """你写的字典只在 Python 里有效，别的语言看不懂，文件里也存不了结构。
JSON 是跨语言的通用数据格式，接口返回、配置文件、前后端交互几乎都用它。
学会 JSON，你的数据才能出得去、进得来。""",
                "concepts": """- **JSON**：一种文本格式，用键值对和数组表达结构化数据。
- **对应关系**：对象对应字典、数组对应列表、字符串对应 str、数字对应 int/float、true/false 对应 True/False、null 对应 None。
- **序列化**：Python 对象转 JSON 字符串，用 json.dumps。
- **反序列化**：JSON 字符串转 Python 对象，用 json.loads。""",
                "plain": """JSON 像国际通用的快递包装标准：不管发货方用什么语言，包装上都写着统一的标签，
收货方按同一套规则拆箱。
dumps 是打包，loads 是拆包；打包后是一段纯文本，可以直接写进文件或通过网络发送。""",
                "syntax": """import json

json.dumps(字典)                     转成 JSON 字符串
json.dumps(字典, ensure_ascii=False)  保留中文，不转成 \\uXXXX
json.dumps(字典, indent=2)            带缩进，便于阅读
json.loads(字符串)                    JSON 字符串转回 Python 对象

json.dump(对象, 文件对象)              直接写入文件
json.load(文件对象)                    直接从文件读取""",
                "example_code": '''import json

student = {
    "name": "小明",
    "age": 18,
    "scores": [92, 88],
    "is_member": True,
}

text = json.dumps(student, ensure_ascii=False)
print("JSON 字符串：")
print(text)

pretty = json.dumps(student, ensure_ascii=False, indent=2)
print("带缩进：")
print(pretty)

back = json.loads(text)
print("转回字典的类型：", type(back))
print("姓名：", back["name"])
print("第二门成绩：", back["scores"][1])

with open("student.json", "w", encoding="utf-8") as f:
    json.dump(student, f, ensure_ascii=False, indent=2)

with open("student.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)
print("从文件读回：", loaded["name"], loaded["age"])''',
                "code_lines": """- 第 3 至 8 行：一个含字符串、数字、列表、布尔的字典。
- 第 10 至 11 行：dumps 转成 JSON 字符串，ensure_ascii=False 让中文保持可读。
- 第 14 至 16 行：indent=2 让输出带层级缩进，便于人阅读。
- 第 18 至 21 行：loads 把字符串转回字典，可以继续用键取值。
- 第 23 至 24 行：json.dump 直接写入文件，不需要自己 dumps 再 write。
- 第 26 至 28 行：json.load 直接从文件读出对象。""",
                "output": """JSON 字符串：
{"name": "小明", "age": 18, "scores": [92, 88], "is_member": true}
带缩进：
{
  "name": "小明",
  "age": 18,
  "scores": [
    92,
    88
  ],
  "is_member": true
}
转回字典的类型： <class 'dict'>
姓名： 小明
第二门成绩： 88
从文件读回： 小明 18""",
                "mistakes": """1. 以为 dumps 之后还是字典，继续用 ["name"] 取值。
2. 不加 ensure_ascii=False，中文变成 \\u5c0f\\u660e。
3. JSON 里用了单引号或 True，导致 loads 失败。
4. 把 dump 和 dumps 弄混：dump 写文件，dumps 返回字符串。
5. 读写文件时编码不统一，中文乱码。""",
                "error_analysis": """- dumps 返回字符串，对字符串用 ["name"] 会报 TypeError: string indices must be integers。
- 默认 ensure_ascii=True 会把中文转义成 \\uXXXX，虽然能正确解析，但人读起来困难。
- JSON 规范只接受双引号、true/false/null，写单引号或 True 会报 json.decoder.JSONDecodeError。
- dump 需要两个参数（对象、文件对象），dumps 只需要对象，混用会报参数错误。
- 文件写入时用 utf-8、读取时也要用 utf-8，否则中文乱码。""",
                "beginner_practice": """把一个保存书名与价格的字典转成 JSON 字符串并输出，再加 indent=2 输出一次。""",
                "advanced_practice": """把含三个学生记录的列表写入 students.json，再读回来输出第二个学生的姓名。""",
                "quiz_note": """本节测验 6 题：2 题考 JSON 与 Python 类型对应、dumps 与 loads 的方向，2 题读代码判断输出，2 题写读写 JSON 文件。""",
                "summary": """- JSON 是跨语言的文本数据格式，对象对应字典、数组对应列表。
- dumps 转字符串，loads 转回对象；dump 与 load 直接操作文件。
- ensure_ascii=False 保留中文，indent 让输出可读。
- JSON 只认双引号与 true/false/null。""",
                "next_lesson": """下一章讲异常处理：程序出错时不崩溃，而是给出可读的提示。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-17-k01",
                        "name": "JSON 格式与 json 模块",
                        "goal": "会看懂 JSON 并用 dumps / loads 转换",
                        "minutes": 30,
                        "criteria": "能说出 JSON 与 Python 类型的对应关系，能正确写出 dumps 与 loads",
                    },
                    {
                        "code": "python-basics-17-k02",
                        "name": "读写 JSON 文件",
                        "goal": "会用 json.dump / json.load 读写文件",
                        "minutes": 25,
                        "criteria": "能写出带 utf-8 的读写代码，能解释 ensure_ascii 的作用",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-17-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "字典转 JSON",
                        "description": "把含书名与价格的字典转成 JSON 字符串，保留中文并缩进 2 格。",
                        "answer": 'import json\nbook = {"title": "Python 入门", "price": 59}\nprint(json.dumps(book, ensure_ascii=False, indent=2))',
                        "explanation": "两个参数分别控制中文与缩进。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-17-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "写入并读回 JSON",
                        "description": "把学生列表写入 students.json，再读回输出第二个学生的姓名。",
                        "answer": 'import json\nstudents = [{"name": "小明"}, {"name": "小红"}]\nwith open("students.json", "w", encoding="utf-8") as f:\n    json.dump(students, f, ensure_ascii=False)\nwith open("students.json", "r", encoding="utf-8") as f:\n    data = json.load(f)\nprint(data[1]["name"])',
                        "explanation": "dump 与 load 直接操作文件对象。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-17-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "JSON 中的对象（大括号结构）对应 Python 的哪种类型？",
                        "options": [
                            ("A", "列表"),
                            ("B", "字典"),
                            ("C", "元组"),
                            ("D", "集合"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "JSON 对象是键值对结构，对应 Python 字典。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-17-l01-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "json.dumps 返回的是字典，json.loads 返回的是字符串。",
                        "answer": {"value": False},
                        "explanation": "方向正好相反：dumps 返回字符串，loads 返回 Python 对象。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-17-l01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''import json
text = json.dumps({"a": 1, "b": True})
data = json.loads(text)
print(type(data))
print(data["b"])''',
                        "answer": {
                            "reference": "输出 <class 'dict'> 和 True。dumps 转成 JSON 字符串，loads 又转回字典，true 还原为 True。",
                            "keywords": ["dict", "True", "dumps", "loads"],
                        },
                        "explanation": "两次转换后回到原始结构。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-17-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "要让 JSON 输出里的中文保持可读，应加哪个参数？",
                        "options": [
                            ("A", "indent=2"),
                            ("B", "ensure_ascii=False"),
                            ("C", "sort_keys=True"),
                            ("D", "encoding=\"utf-8\""),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "ensure_ascii=False 让非 ASCII 字符原样输出。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-17-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "写代码把字典 {\"name\": \"小明\", \"age\": 18} 写入 info.json（保留中文）。",
                        "answer": {
                            "reference": 'import json\ninfo = {"name": "小明", "age": 18}\nwith open("info.json", "w", encoding="utf-8") as f:\n    json.dump(info, f, ensure_ascii=False)',
                            "keywords": ["json.dump", "open", "ensure_ascii", "utf-8"],
                        },
                        "explanation": "写文件用 dump，注意编码与中文选项。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-17-l01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么要把数据存成 JSON，而不是直接把字典用 str() 存成文本？",
                        "answer": {
                            "reference": "str() 出来的是 Python 的表示形式，含单引号、True 等不符合 JSON 规范的写法，其他语言无法可靠解析。JSON 是跨语言标准格式，能被各种语言和工具读取，且结构明确。",
                            "keywords": ["跨语言", "标准", "单引号", "规范"],
                        },
                        "explanation": "能指出「str 不是通用格式」即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ------------------------------------------------------------------ 第 18 章
    {
        "code": "python-basics-18",
        "order_index": 18,
        "title": "异常处理",
        "description": "程序出错时不崩溃：识别常见异常、用 try/except 兜底、用 finally 收尾、用 raise 主动报错。",
        "lessons": [
            {
                "code": "python-basics-18-l01",
                "title": "常见异常类型与 try / except",
                "description": "认识 ValueError、ZeroDivisionError、FileNotFoundError，用 try/except 捕获处理。",
                "minutes": 60,
                "difficulty": "intermediate",
                "objectives": """1. 能说出四种以上常见异常类型及其触发场景。
2. 会写 try/except 捕获指定异常并给出友好提示。
3. 能说明为什么不应该用裸 except 吞掉所有错误。""",
                "why_learn": """用户输入 0 做除数、文件被删、格式不对，这些都不是「代码写错」，而是运行时必然遇到的意外。
不处理，程序直接崩溃并抛出一大段报错；处理了，程序可以提示用户重试或走备用逻辑。
异常处理是程序从「能跑」到「能用」的分界线。""",
                "concepts": """- **异常**：运行时发生的错误，会中断正常流程。
- **ValueError**：值不合法，如 int("abc")。
- **ZeroDivisionError**：除数为零。
- **FileNotFoundError**：文件不存在。
- **KeyError / IndexError**：键或下标不存在。
- **try / except**：把可能出错的代码放进 try，出错时执行 except。""",
                "plain": """异常像开车时的突发状况：爆胎、没油、红灯。
try 是「正常行驶的路线」，except 是「出状况时的备用方案」。
你不需要预知每次爆胎，但要知道爆胎后该怎么办——这就是异常处理的意义。""",
                "syntax": """try:
    可能出错的代码
except ValueError:
    出错后的处理
except ZeroDivisionError:
    另一种错误的处理

int("abc")            触发 ValueError
10 / 0                触发 ZeroDivisionError
{}["missing"]         触发 KeyError
[1][5]                触发 IndexError""",
                "example_code": '''text = "abc"
try:
    number = int(text)
    print("转换结果：", number)
except ValueError:
    print("输入的不是合法整数：", text)

try:
    print(10 / 0)
except ZeroDivisionError:
    print("除数不能为 0")

try:
    with open("not_exist.txt", "r", encoding="utf-8") as f:
        content = f.read()
except FileNotFoundError:
    print("文件不存在，请检查路径")

data = {"name": "小明"}
try:
    print(data["age"])
except KeyError:
    print("字典里没有 age 这个键")''',
                "code_lines": """- 第 2 至 6 行：int("abc") 会抛 ValueError，被 except 接住后输出提示，程序继续往下走。
- 第 8 至 11 行：除零错误单独捕获，说明不同错误可以分别处理。
- 第 13 至 17 行：文件不存在抛 FileNotFoundError，捕获后给出可读提示。
- 第 19 至 23 行：字典取不存在的键抛 KeyError，同样被捕获。""",
                "output": """输入的不是合法整数： abc
除数不能为 0
文件不存在，请检查路径
字典里没有 age 这个键""",
                "mistakes": """1. 用裸 except 捕获所有异常，把真正的 bug 也吞掉。
2. try 里塞了太多不相关的代码，出错后不知道是哪一句。
3. 捕获了异常却不做任何处理（pass），问题被隐藏。
4. 把 except 的类型写错，导致没接住。
5. 用异常处理代替正常的条件判断。""",
                "error_analysis": """- except: 会连键盘中断、语法外的一切错误都吞掉，出错后没有任何线索；应捕获具体类型。
- try 范围过大时，很难定位是哪一行出错，应只包住可能出错的最小片段。
- except ValueError: pass 会让错误静默消失，用户以为成功，实际数据没处理。
- 捕获类型必须匹配，ZeroDivisionError 不会被 except ValueError 接住。
- 能用 if 判断的情况（如 n != 0）优先用判断，异常用于真正意外的情况。""",
                "beginner_practice": """用 try/except 处理用户输入的整数转换，输入非法时提示「请输入数字」。""",
                "advanced_practice": """写一个安全除法函数，捕获除零与类型错误两种情况，分别给出不同提示。""",
                "quiz_note": """本节测验 6 题：2 题考异常类型与捕获规则，2 题读代码判断是否被捕获、输出什么，2 题写带 try/except 的输入处理。""",
                "summary": """- 异常是运行时错误，会中断正常流程。
- try 包住可能出错的代码，except 按类型捕获。
- 不要用裸 except，不要静默 pass。
- 能用条件判断的优先判断，异常留给真正的意外。""",
                "next_lesson": """下一课学 else 与 finally：分别在「没出错」和「无论如何都要做」时执行。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-18-k01",
                        "name": "常见异常类型",
                        "goal": "能识别 ValueError、ZeroDivisionError、FileNotFoundError、KeyError、IndexError",
                        "minutes": 30,
                        "criteria": "能针对给定代码说出会抛哪种异常",
                    },
                    {
                        "code": "python-basics-18-k02",
                        "name": "try / except 捕获处理",
                        "goal": "会写按类型捕获的异常处理代码",
                        "minutes": 30,
                        "criteria": "能写出捕获指定异常的完整结构，能说明裸 except 的危害",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-18-k01-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "安全转换",
                        "description": "读入内容并转 int，非法时提示「请输入数字」。",
                        "answer": 'text = input("请输入数字：")\ntry:\n    print(int(text))\nexcept ValueError:\n    print("请输入数字")',
                        "explanation": "int 转换失败抛 ValueError，捕获后提示。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-18-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "安全除法",
                        "description": "写函数 safe_div(a, b)，除零时返回 None 并提示，类型错误时提示类型不对。",
                        "answer": 'def safe_div(a, b):\n    try:\n        return a / b\n    except ZeroDivisionError:\n        print("除数不能为 0")\n        return None\n    except TypeError:\n        print("类型不正确")\n        return None',
                        "explanation": "多个 except 按类型分别处理。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-18-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "int(\"abc\") 会触发哪种异常？",
                        "options": [
                            ("A", "TypeError"),
                            ("B", "ValueError"),
                            ("C", "KeyError"),
                            ("D", "NameError"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "值不合法（无法解析为整数）属于 ValueError。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-18-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "捕获异常时应该尽量使用裸 except，这样可以处理所有情况。",
                        "answer": {"value": False},
                        "explanation": "裸 except 会吞掉真正的 bug，应捕获具体类型。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-18-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''try:
    print(10 / 0)
except ValueError:
    print("值错误")
print("继续执行")''',
                        "answer": {
                            "reference": "ZeroDivisionError 不会被 except ValueError 捕获，程序抛出异常并中断，不会输出「继续执行」。",
                            "keywords": ["不会被捕获", "ZeroDivisionError", "中断"],
                        },
                        "explanation": "捕获类型必须与实际异常匹配。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-18-l01-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "访问列表 [1, 2][5] 会触发哪种异常？",
                        "options": [
                            ("A", "KeyError"),
                            ("B", "IndexError"),
                            ("C", "ValueError"),
                            ("D", "TypeError"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "下标越界属于 IndexError，字典取不到键才是 KeyError。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-18-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "写代码：读入两个整数并输出商，除数为 0 时提示「除数不能为 0」。",
                        "answer": {
                            "reference": 'a = int(input("a："))\nb = int(input("b："))\ntry:\n    print(a / b)\nexcept ZeroDivisionError:\n    print("除数不能为 0")',
                            "keywords": ["try", "ZeroDivisionError", "except", "print"],
                        },
                        "explanation": "除法放进 try，按类型捕获除零错误。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-18-l01-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "为什么不建议写 except: pass？它会带来什么后果？",
                        "answer": {
                            "reference": "因为它会吞掉所有异常且不做任何提示，程序看起来正常结束，实际数据可能没处理、错误被隐藏，排查时毫无线索。至少应捕获具体类型并记录或提示。",
                            "keywords": ["吞掉", "隐藏", "无提示", "具体类型"],
                        },
                        "explanation": "能指出「错误被静默隐藏」即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-basics-18-l02",
                "title": "else、finally 与 raise",
                "description": "用 else 处理「没出错」的情况、用 finally 做收尾、用 raise 主动抛错。",
                "minutes": 50,
                "difficulty": "intermediate",
                "objectives": """1. 会用 else 执行「try 未出错时」的逻辑。
2. 会用 finally 执行「无论如何都要做」的收尾。
3. 会用 raise 主动抛出异常，并在调用处捕获处理。""",
                "why_learn": """真实程序里，「成功」「失败」「收尾」是三件不同的事。
else 让成功路径不必挤在 try 里，finally 保证文件、连接一定被释放，
raise 则让你在数据不合法时立刻中止，而不是带着错误数据继续跑。""",
                "concepts": """- **else**：try 中没有异常时执行。
- **finally**：无论是否异常都会执行，常用于清理。
- **raise**：主动抛出异常，中止当前流程。
- **raise**：主动抛出异常，可以附带一句可读的错误原因。""",
                "plain": """try/except/else/finally 像一次外出办事：
try 是办事过程，except 是办不成时的补救，else 是办成后的下一步，
finally 是无论如何都要锁门回家。
raise 则是你发现材料造假，主动喊停，而不是硬着头皮办下去。""",
                "syntax": """try:
    可能出错
except ValueError:
    出错时
else:
    没出错时
finally:
    无论如何都执行

raise ValueError("年龄不能为负数")

异常信息会跟着异常一起抛给调用处，
调用处用 except ValueError as e 就能拿到这句话。""",
                "example_code": '''def parse_age(text):
    try:
        age = int(text)
    except ValueError:
        print("不是合法数字：", text)
        return None
    else:
        print("解析成功：", age)
        return age
    finally:
        print("解析流程结束")

parse_age("18")
parse_age("abc")

def set_age(age):
    if age < 0:
        raise ValueError("年龄不能为负数")
    return age

try:
    set_age(-1)
except ValueError as e:
    print("捕获到自定义错误：", e)''',
                "code_lines": """- 第 2 至 4 行：尝试转换，失败时走 except 并返回 None。
- 第 6 至 8 行：只有 try 成功才会进入 else，输出解析结果。
- 第 9 至 10 行：finally 无论成功失败都会执行，适合放收尾逻辑。
- 第 13 至 16 行：业务规则校验失败时用 raise 主动抛错，而不是返回一个特殊值。
- 第 18 至 21 行：调用处用 except 接住，as e 拿到异常对象的提示信息。""",
                "output": """解析成功： 18
解析流程结束
不是合法数字： abc
解析流程结束
捕获到自定义错误： 年龄不能为负数""",
                "mistakes": """1. 把成功逻辑也写在 try 里，出错时容易混淆。
2. 以为 finally 只在出错时执行。
3. raise 后还写返回值，实际永远不会执行到。
4. raise 之后又写 return 或 print，误以为还会执行。
5. 捕获异常后不再抛出，导致上层无法感知失败。""",
                "error_analysis": """- else 只在没有异常时执行，把成功逻辑放 try 里会让 try 范围过大，难以定位错误。
- finally 无论成功失败都执行，甚至 return 之前也会执行。
- raise 之后的语句不会执行，函数立即结束。
- raise 之后的语句不会执行，函数立刻结束；如果调用处没有捕获，程序会终止并打印 traceback。
- 底层函数捕获后不重新抛出，上层拿不到失败信息，错误被悄悄吞掉。""",
                "beginner_practice": """写函数校验分数，小于 0 或大于 100 时 raise ValueError，调用处捕获并输出提示。""",
                "advanced_practice": """写一个带 finally 的函数，无论转换成功与否都输出「处理结束」，并用两次调用验证。""",
                "quiz_note": """本节测验 6 题：2 题考 else/finally 的执行时机，2 题读代码判断执行顺序，2 题写带 raise 与 finally 的函数。""",
                "summary": """- else 在 try 未出错时执行，finally 一定执行。
- raise 主动抛错，用于业务规则校验。
- 校验失败用 raise 主动抛错，调用处用 except 捕获。
- 清理逻辑放 finally，成功逻辑放 else。""",
                "next_lesson": """下一章讲调试基础：看懂报错、定位问题、用最少的手段找出 bug。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-18-k03",
                        "name": "else 与 finally",
                        "goal": "掌握 try/except/else/finally 的执行顺序",
                        "minutes": 25,
                        "criteria": "能准确说出四种情况下各代码块是否执行",
                    },
                    {
                        "code": "python-basics-18-k04",
                        "name": "raise 与自定义异常",
                        "goal": "会在业务校验中用 raise 主动抛错",
                        "minutes": 25,
                        "criteria": "能写出 raise ValueError 并在调用处捕获，能定义自定义异常类",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-18-k03-ex1",
                        "kp": 0,
                        "type": "coding",
                        "title": "观察执行顺序",
                        "description": "写 try/except/else/finally 四段输出，分别用会出错和不会出错的输入调用。",
                        "answer": 'def run(text):\n    try:\n        print(int(text))\n    except ValueError:\n        print("出错")\n    else:\n        print("成功")\n    finally:\n        print("结束")\n\nrun("1")\nrun("x")',
                        "explanation": "成功时走 else 再 finally，失败时走 except 再 finally。",
                        "difficulty": "intermediate",
                    },
                    {
                        "code": "python-basics-18-k04-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "校验分数",
                        "description": "写函数 check(score)，超出 0 到 100 时 raise ValueError。",
                        "answer": 'def check(score):\n    if score < 0 or score > 100:\n        raise ValueError("分数必须在 0 到 100 之间")\n    return score\n\ntry:\n    check(120)\nexcept ValueError as e:\n    print(e)',
                        "explanation": "raise 主动中止，调用处捕获并输出原因。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-18-l02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "try 中的代码没有发生异常时，哪个代码块会执行？",
                        "options": [
                            ("A", "except"),
                            ("B", "else"),
                            ("C", "什么都不会执行"),
                            ("D", "只执行 finally"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "没有异常时执行 else，finally 也一定执行。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-18-l02-2",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "finally 只在 try 中出现异常时执行。",
                        "answer": {"value": False},
                        "explanation": "finally 无论是否异常都会执行，用于清理资源。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-18-l02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''try:
    print("A")
except ValueError:
    print("B")
else:
    print("C")
finally:
    print("D")''',
                        "answer": {
                            "reference": "依次输出 A、C、D。没有异常，所以跳过 except，执行 else 和 finally。",
                            "keywords": ["A", "C", "D", "无异常"],
                        },
                        "explanation": "按执行顺序推演即可。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-18-l02-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "在函数中执行 raise 之后，同一函数内后面的语句会怎样？",
                        "options": [
                            ("A", "继续正常执行"),
                            ("B", "不再执行，函数立即结束"),
                            ("C", "报语法错误"),
                            ("D", "执行两次"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "raise 会立刻中断当前函数，后续语句不会执行。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-18-l02-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "写函数 check_age(age)，小于 0 时 raise ValueError，并在调用处捕获输出错误信息。",
                        "answer": {
                            "reference": 'def check_age(age):\n    if age < 0:\n        raise ValueError("年龄不能为负数")\n    return age\n\ntry:\n    check_age(-1)\nexcept ValueError as e:\n    print(e)',
                            "keywords": ["raise ValueError", "except", "as e", "print"],
                        },
                        "explanation": "主动抛错后由调用方决定如何提示。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-18-l02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么把「成功后的处理」写在 else 里，而不是直接写在 try 末尾？",
                        "answer": {
                            "reference": "因为 try 里的任何异常都会被 except 捕获，如果把成功逻辑也放在 try 里，它自身出错时会被误当成前面的错误处理掉，且 try 范围过大难以定位问题。else 只在前面的 try 完全成功时执行，语义更清晰。",
                            "keywords": ["范围", "误捕获", "只在不异常时", "清晰"],
                        },
                        "explanation": "能指出「避免成功逻辑的异常被误捕获」即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    # ------------------------------------------------------------------ 第 19 章
    {
        "code": "python-basics-19",
        "order_index": 19,
        "title": "调试基础",
        "description": "报错不可怕：读懂异常信息、用 print 定位、用断点观察，把找 bug 变成有步骤的事。",
        "lessons": [
            {
                "code": "python-basics-19-l01",
                "title": "读报错、print 调试与断点",
                "description": "学会从报错信息定位行号与原因，用最小改动验证猜想。",
                "minutes": 50,
                "difficulty": "beginner",
                "objectives": """1. 能读懂 traceback 的最后一行与行号。
2. 会用 print 输出中间变量定位问题。
3. 知道断点调试的基本用法与适用场景。""",
                "why_learn": """写代码的时间有一半花在找错上。会读报错的人几分钟定位问题，
不会读的人只能把代码改来改去碰运气。
调试是一项可以练的技能，不是天赋。""",
                "concepts": """- **traceback**：Python 打印的错误轨迹，从调用处到出错点。
- **最后一行**：异常类型与具体原因，最重要。
- **行号**：形如 File "a.py", line 5，指出出错位置。
- **print 调试**：在可疑位置输出变量值，验证猜想。
- **断点**：让程序停在某行，逐行观察变量变化。""",
                "plain": """报错信息像医院的检查报告：前面一堆流程记录，最后一行才是结论。
很多人一看到红字就慌，其实只需要看最后一行「什么错」和往上找「哪一行」。
print 调试像在管道上开个小窗，看看水流到那里时是什么颜色。""",
                "syntax": """Traceback (most recent call last):
  File "demo.py", line 3, in <module>
    print(10 / n)
ZeroDivisionError: division by zero

读法：
1. 最后一行看错误类型与原因
2. 往上找 File 与 line，定位到具体行
3. 检查那一行的变量当时是什么值""",
                "example_code": '''def average(numbers):
    print("调试：收到的参数是", numbers)
    total = sum(numbers)
    print("调试：总和是", total, "个数是", len(numbers))
    return total / len(numbers)

print(average([80, 90, 100]))

try:
    print(average([]))
except ZeroDivisionError as e:
    print("出错原因：", e)''',
                "code_lines": """- 第 2 行：先用 print 确认函数收到的参数到底是不是预期值，这是最有效的第一步。
- 第 4 行：再输出中间结果，验证 sum 与 len 是否符合预期。
- 第 7 行：正常数据得到平均值 90.0。
- 第 9 至 12 行：空列表会让 len 为 0，触发除零错误；捕获后输出具体原因，而不是让程序崩溃。""",
                "output": """调试：收到的参数是 [80, 90, 100]
调试：总和是 270 个数是 3
90.0
调试：收到的参数是 []
调试：总和是 0 个数是 0
出错原因： division by zero""",
                "mistakes": """1. 只看第一行报错，忽略最后一行真正原因。
2. 报错行号指向的是「调用处」，却去改被调用函数。
3. 到处加 print 却不删，输出被淹没。
4. 靠猜改代码，一次改很多处，无法判断哪处生效。
5. 遇到报错就把整段代码重写。""",
                "error_analysis": """- traceback 从下往上读：最后一行是错误类型，上面的 File 行是调用链。
- 行号可能指向调用表达式的整体，真正的错误发生在被调用的函数内部，要看完整调用链。
- 加 print 时应输出「变量名 + 值」，否则多个输出分不清谁是谁。
- 一次只改一处、改完立刻运行，才能知道是哪次修改解决了问题。
- 重写会丢掉原有正确逻辑，应该先定位再最小修改。""",
                "beginner_practice": """给一段会报 ZeroDivisionError 的代码加上 print，输出参与运算的两个值，定位问题。""",
                "advanced_practice": """写函数计算平均分，输入空列表时给出可读提示而不是崩溃，并用 print 记录中间值。""",
                "quiz_note": """本节测验 6 题：2 题考 traceback 的读法与调试手段，2 题读报错判断原因，2 题写带调试输出的排查代码。""",
                "summary": """- 报错先看最后一行：错误类型与原因。
- 再往上找 File 与 line，定位代码位置。
- print 输出变量名和值，验证猜想。
- 一次只改一处，改完立刻验证。""",
                "next_lesson": """下一章是综合练习：把前面学的变量、列表、字典、函数、文件、异常串成一个能用的命令行工具。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-19-k01",
                        "name": "读懂报错信息",
                        "goal": "能从 traceback 中定位错误类型与出错行",
                        "minutes": 25,
                        "criteria": "能指出报错的类型、原因与大致位置",
                    },
                    {
                        "code": "python-basics-19-k02",
                        "name": "print 调试与断点",
                        "goal": "会用输出中间值与断点定位问题",
                        "minutes": 25,
                        "criteria": "能在可疑位置输出关键变量，能说明断点与 print 的适用差别",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-19-k01-ex1",
                        "kp": 0,
                        "type": "short_answer",
                        "title": "读一段报错",
                        "description": "报错为 line 3, in <module> print(10 / n) 且 ZeroDivisionError，问题出在哪？",
                        "answer": "n 的值为 0，导致除零。应在第 3 行之前输出 n 的值确认，并增加 n 是否为 0 的判断。",
                        "explanation": "最后一行给出错误类型，上一行给出代码位置。",
                        "difficulty": "beginner",
                    },
                    {
                        "code": "python-basics-19-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "加调试输出",
                        "description": "给求平均值的函数加两行调试输出，分别打印列表与长度。",
                        "answer": 'def average(numbers):\n    print("numbers:", numbers)\n    print("len:", len(numbers))\n    return sum(numbers) / len(numbers)',
                        "explanation": "输出变量名和值，便于对照预期。",
                        "difficulty": "beginner",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-19-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "阅读 traceback 时，最应该先看哪里？",
                        "options": [
                            ("A", "第一行的 Traceback 字样"),
                            ("B", "最后一行的异常类型与原因"),
                            ("C", "中间的省略号"),
                            ("D", "文件名"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "最后一行给出错误类型和具体原因，是最关键的信息。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-19-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "print 调试时一次改很多处代码，更容易定位问题。",
                        "answer": {"value": False},
                        "explanation": "一次只改一处才能判断哪次修改有效，多处同改会互相干扰。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-19-l01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''nums = []
print(sum(nums) / len(nums))
会报什么错？''',
                        "answer": {
                            "reference": "报 ZeroDivisionError: division by zero，因为空列表长度为 0。",
                            "keywords": ["ZeroDivisionError", "长度为 0", "空列表"],
                        },
                        "explanation": "先判断列表是否为空，再决定是否计算。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-19-l01-4",
                        "kp": 1,
                        "type": "single_choice",
                        "stem": "下面哪种做法最有助于定位「结果不对但没有报错」的问题？",
                        "options": [
                            ("A", "重写整段代码"),
                            ("B", "在关键步骤输出中间变量的值"),
                            ("C", "加大括号"),
                            ("D", "换一个 Python 版本"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "逻辑错误没有报错，只能靠观察中间值判断哪一步开始偏离预期。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-19-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "写函数 avg(nums)，先用 print 输出列表与长度，再返回平均值。",
                        "answer": {
                            "reference": 'def avg(nums):\n    print("nums:", nums)\n    print("len:", len(nums))\n    return sum(nums) / len(nums)',
                            "keywords": ["print", "len", "sum", "return"],
                        },
                        "explanation": "调试输出要带变量名，便于辨认。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-19-l01-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "断点调试与 print 调试各适合什么场景？",
                        "answer": {
                            "reference": "print 适合快速确认某个值、改动成本低，但输出多了会乱；断点适合逻辑复杂、需要逐行观察多个变量变化、或循环里某一轮出错的场景，可以暂停并查看当时的全部状态。",
                            "keywords": ["逐行", "多个变量", "快速", "循环"],
                        },
                        "explanation": "能按「简单快速」与「复杂逐行」区分即可。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    # ------------------------------------------------------------------ 第 20 章
    {
        "code": "python-basics-20",
        "order_index": 20,
        "title": "综合练习：命令行任务管理工具",
        "description": "把变量、列表、字典、循环、函数、文件与异常串起来，做一个真正能用的待办工具。",
        "lessons": [
            {
                "code": "python-basics-20-l01",
                "title": "需求拆解与任务管理工具实现",
                "description": "从需求到数据结构、函数划分、持久化与异常处理，完整走一遍小项目。",
                "minutes": 65,
                "difficulty": "intermediate",
                "objectives": """1. 会把一句需求拆成数据结构与函数清单。
2. 会用列表与字典组织多条任务记录。
3. 会用函数、文件读写与异常处理把功能串成完整程序。""",
                "why_learn": """前面每一节都是单一技能，真实项目需要把它们组合起来：
数据怎么存、功能怎么拆、出错怎么办、数据怎么保存。
这一节就是把这些碎片拼成一个能跑起来的小工具，也是你第一个完整作品。""",
                "concepts": """- **需求拆解**：把「能管理任务」拆成添加、查看、完成、保存四个动作。
- **数据结构**：任务列表用列表存，每条任务是字典（标题、是否完成）。
- **函数划分**：一个函数只做一件事，主流程只负责调度。
- **持久化**：用 JSON 文件保存，下次启动能读回来。
- **异常处理**：文件不存在时给默认值，输入非法时提示。""",
                "plain": """做小项目像搭积木：先想清楚要搭什么形状（需求），
再决定用哪些块（数据结构），然后按部位拼（函数），
最后用胶水固定（文件保存与异常处理），这样散了还能重搭。""",
                "syntax": """任务记录：{"title": "写作业", "done": False}
任务列表：[任务1, 任务2, ...]

add_task(tasks, title)        添加
list_tasks(tasks)             查看
finish_task(tasks, index)     完成
save_tasks(tasks, path)       保存
load_tasks(path)              读取""",
                "example_code": '''import json

def add_task(tasks, title):
    tasks.append({"title": title, "done": False})
    return tasks

def list_tasks(tasks):
    if not tasks:
        print("暂无任务")
        return
    for i, task in enumerate(tasks, start=1):
        mark = "已完成" if task["done"] else "未完成"
        print(i, task["title"], mark)

def finish_task(tasks, index):
    if index < 1 or index > len(tasks):
        raise ValueError("任务编号不存在")
    tasks[index - 1]["done"] = True
    return tasks

def save_tasks(tasks, path="tasks.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def load_tasks(path="tasks.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

tasks = load_tasks()
add_task(tasks, "完成 Python 综合练习")
add_task(tasks, "复习字典与异常")
finish_task(tasks, 1)
list_tasks(tasks)
save_tasks(tasks)
print("已保存，重新读取：")
print(load_tasks())''',
                "code_lines": """- 第 3 至 5 行：添加任务，统一成字典结构，初始未完成。
- 第 7 至 13 行：查看任务，空列表给出提示；enumerate 同时拿到序号与任务，start=1 让编号从 1 开始。
- 第 15 至 19 行：完成指定编号的任务，编号越界时主动 raise。
- 第 21 至 23 行：把任务列表写成 JSON 文件。
- 第 25 至 30 行：读取文件，文件不存在时返回空列表，程序不会崩。
- 第 32 至 38 行：主流程依次调用各函数，验证添加、完成、查看、保存、读取整条链路。""",
                "output": """1 完成 Python 综合练习 已完成
2 复习字典与异常 未完成
已保存，重新读取：
[{'title': '完成 Python 综合练习', 'done': True}, {'title': '复习字典与异常', 'done': False}]""",
                "mistakes": """1. 用多个平行列表分别存标题和状态，容易出现长度不一致。
2. 把所有逻辑写在一个函数里，无法复用也不好调试。
3. 编号从 0 开始却按 1 开始给用户看，导致选错任务。
4. 保存时不写编码，中文变乱码。
5. 读取文件不做异常处理，第一次运行就崩溃。""",
                "error_analysis": """- 平行列表一旦漏 append 一个，标题和状态就会错位，用字典把一条记录打包更安全。
- 所有逻辑堆在 main 里，任何改动都可能影响其他功能，应按动作拆函数。
- 用户看到的编号是 1 开始，代码里下标是 0 开始，转换时要减 1；否则完成的是错误的任务。
- 不指定 encoding 时中文在 Windows 上可能乱码，统一 utf-8。
- 首次运行没有 tasks.json，不处理 FileNotFoundError 会直接崩溃。""",
                "beginner_practice": """在示例基础上增加「删除任务」函数，删除后重新列出并保存。""",
                "advanced_practice": """增加「统计未完成数量」函数，并在列表输出末尾打印统计结果；再处理编号输入非数字的情况。""",
                "quiz_note": """本节测验 6 题：2 题考需求拆解与数据结构选择，2 题读代码判断输出与异常，2 题写新增功能或完整流程。""",
                "summary": """- 小项目先拆需求，再定数据结构，最后按动作拆函数。
- 一条记录用字典，多条记录用列表。
- 持久化用 JSON，读取要处理文件不存在。
- 用户编号从 1 开始，代码下标从 0 开始，注意转换。""",
                "next_lesson": """完成本课程后，可以进入 Python 进阶与工程实践，学习面向对象、迭代器、装饰器与项目结构。""",
                "knowledge_points": [
                    {
                        "code": "python-basics-20-k01",
                        "legacy": "python-basics-06-05",
                        "name": "数据结构综合运用",
                        "goal": "能用列表与字典组合表达多条记录",
                        "minutes": 30,
                        "criteria": "能设计出任务记录结构，能说明为何不用平行列表",
                    },
                    {
                        "code": "python-basics-20-k02",
                        "name": "小项目拆解与实现",
                        "goal": "能把需求拆成函数并完成持久化",
                        "minutes": 35,
                        "criteria": "能按动作拆出四个以上函数，能处理文件缺失与编号越界",
                    },
                ],
                "practice": [
                    {
                        "code": "python-basics-20-k01-ex1",
                        "kp": 0,
                        "type": "project",
                        "title": "任务管理工具",
                        "description": "实现添加、查看、完成、保存、读取五个功能，要求任务用字典、列表存储，数据保存到 tasks.json。",
                        "answer": "参见本节示例代码：add_task / list_tasks / finish_task / save_tasks / load_tasks 五个函数，主流程依次调用。",
                        "explanation": "评分关注：数据结构是否合理、函数是否单一职责、是否处理文件不存在、编号转换是否正确。",
                        "difficulty": "intermediate",
                    },
                    {
                        "code": "python-basics-20-k02-ex2",
                        "kp": 1,
                        "type": "coding",
                        "title": "增加删除功能",
                        "description": "写 delete_task(tasks, index) 删除指定任务，越界时 raise ValueError。",
                        "answer": 'def delete_task(tasks, index):\n    if index < 1 or index > len(tasks):\n        raise ValueError("任务编号不存在")\n    tasks.pop(index - 1)\n    return tasks',
                        "explanation": "编号转换为下标减 1，越界主动抛错。",
                        "difficulty": "intermediate",
                    },
                ],
                "questions": [
                    {
                        "code": "q-pb-20-l01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "保存多条任务记录，最合适的结构是？",
                        "options": [
                            ("A", "一个字典，键是任务标题"),
                            ("B", "列表装字典，每个字典是一条任务"),
                            ("C", "多个平行列表分别存标题和状态"),
                            ("D", "一个字符串拼接所有任务"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "列表解决多条，字典解决字段，且不会像平行列表那样错位。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-20-l01-2",
                        "kp": 1,
                        "type": "true_false",
                        "stem": "读取任务文件时若不处理 FileNotFoundError，第一次运行程序会直接崩溃。",
                        "answer": {"value": True},
                        "explanation": "首次运行没有文件，不捕获就会抛异常终止。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-pb-20-l01-3",
                        "kp": 1,
                        "type": "code_analysis",
                        "stem": '''tasks = [{"title": "A", "done": False}]
index = 1
tasks[index - 1]["done"] = True
print(tasks[0]["done"])''',
                        "answer": {
                            "reference": "输出 True。用户编号 1 对应下标 0，减 1 后正好是第一条任务。",
                            "keywords": ["True", "减 1", "下标 0"],
                        },
                        "explanation": "编号与下标的转换是小工具最容易出错的地方。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-20-l01-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "为什么不用两个平行列表分别存标题和完成状态？",
                        "options": [
                            ("A", "代码更长"),
                            ("B", "容易出现长度不一致导致数据错位"),
                            ("C", "列表不能存字符串"),
                            ("D", "无法遍历"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "任何一次漏删漏加都会让两个列表对不上，字典把一条记录打包更安全。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-pb-20-l01-5",
                        "kp": 1,
                        "type": "code_writing",
                        "stem": "写函数 count_undone(tasks) 返回未完成任务的个数。",
                        "answer": {
                            "reference": 'def count_undone(tasks):\n    count = 0\n    for task in tasks:\n        if not task["done"]:\n            count = count + 1\n    return count',
                            "keywords": ["for", "done", "count", "return"],
                        },
                        "explanation": "遍历列表，用 done 字段判断并计数。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-pb-20-l01-6",
                        "kp": 1,
                        "type": "short_answer",
                        "stem": "如果要做成一个真正能交互的命令行工具，还需要补充哪三件事？",
                        "answer": {
                            "reference": "一是循环菜单，让用户反复选择操作；二是输入校验，把编号转成整数并处理非数字输入；三是操作反馈与退出机制，例如每次操作后提示结果并支持退出。",
                            "keywords": ["循环菜单", "输入校验", "退出", "反馈"],
                        },
                        "explanation": "能指出「交互循环、输入校验、退出」三个方向即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
]
