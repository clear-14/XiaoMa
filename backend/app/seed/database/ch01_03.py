"""数据库与 Python 数据库开发：第 1—3 章（数据库基础、SQL 查询、SQLite 实战）。"""

CHAPTERS: list[dict] = [
    {
        "code": "python-database-01",
        "title": "数据库基础",
        "description": "建立表、行、列与键的模型认知，理解为什么需要主键和外键。",
        "order_index": 1,
        "lessons": [
            {
                "code": "python-database-01-lesson-01",
                "objectives": """1. 说清表、行、列分别对应现实中的什么；
2. 理解主键的作用，能为一类数据选出合适的主键；
3. 会写最简单的建表与插入语句；
4. 知道「用业务字段当主键」的坑。""",
                "why_learn": """把数据存在列表里，程序一退出就没了；存在 JSON 文件里，并发写会互相覆盖、
查一条要读全文件。数据库把「存储 + 查询 + 并发控制」一起解决，是后端绕不开的基础。""",
                "concepts": """**表（table）** 是一类实体的集合，比如所有用户、所有任务。
**列（column）** 是属性，每列有固定的类型（整数、文本、时间）。
**行（row）** 是一条具体记录。
**主键（primary key）** 是能唯一标识一行的列或列组合，不允许重复、不允许为空。
**候选键** 是「本来也能当主键」的列，比如邮箱；选定其中一个当主键，其余加唯一约束。
主键最好用无业务含义的自增值或 UUID，避免业务变化导致主键要改。""",
                "plain": """表像一张 Excel 工作表，列是表头，行是一条条记录。
主键像每个人的身份证号：不带业务含义、唯一、不会因为改名字而变。
如果拿手机号当主键，用户换号时你就要改一堆关联数据——所以主键要选「不会变」的东西。""",
                "syntax": """```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,   -- 主键，唯一且非空
    title TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
);

INSERT INTO tasks (title, done) VALUES ('写周报', 0);
SELECT id, title, done FROM tasks;
```
要点：列要声明类型；`NOT NULL` 表示必填；`DEFAULT` 给默认值；`PRIMARY KEY` 隐含唯一与非空。""",
                "example_code": '''import sqlite3

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE tasks (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0
    )
    """
)

cursor.executemany(
    "INSERT INTO tasks (title, done) VALUES (?, ?)",
    [("写周报", 0), ("交报表", 1), ("订会议室", 0)],
)

rows = cursor.execute("SELECT id, title, done FROM tasks").fetchall()
for row in rows:
    print(dict(row))

print("行数", len(rows))
print("主键是否唯一", len({row["id"] for row in rows}) == len(rows))

try:
    cursor.execute("INSERT INTO tasks (id, title) VALUES (1, '重复主键')")
except sqlite3.IntegrityError as exc:
    print("主键冲突被拒绝：", exc)

conn.close()''',
                "code_lines": """1. `sqlite3.connect(":memory:")` 建一个内存数据库，进程结束即消失，适合练习。
2. `row_factory = sqlite3.Row` 让查询结果能按列名取值，而不是只能按下标。
3. `CREATE TABLE` 定义三列：id 是主键、title 必填、done 默认 0。
4. `executemany` 一次插入多行，`?` 是占位符，参数用元组传入，能防注入。
5. `fetchall()` 取出全部结果，每行是 Row 对象，`dict(row)` 转成普通字典便于打印。
6. `len({row["id"] ...}) == len(rows)` 用集合去重后比较长度，验证主键确实唯一。
7. 最后故意插一条 id=1 的记录，触发 IntegrityError，说明主键约束真的在生效。""",
                "output": """{'id': 1, 'title': '写周报', 'done': 0}
{'id': 2, 'title': '交报表', 'done': 1}
{'id': 3, 'title': '订会议室', 'done': 0}
行数 3
主键是否唯一 True
主键冲突被拒绝： UNIQUE constraint failed: tasks.id""",
                "mistakes": """- 不设主键，导致无法准确更新或删除某一行。
- 用姓名、手机号这类会变的业务字段当主键。
- 把 `done` 存成文本 "true"/"false"，查询时无法比较大小。
- 插入时不写列名，一旦表结构增列就全部错位。
- 以为主键会自动阻止所有重复，忘了给其他唯一字段加 UNIQUE。""",
                "error_analysis": """`sqlite3.IntegrityError: UNIQUE constraint failed: tasks.id`
—— 主键重复。要么让数据库自增（不传 id），要么改用 UPSERT。

`sqlite3.OperationalError: table tasks has no column named titel`
—— 列名拼错。SQL 错误信息会指出具体列名，照着改即可。

`sqlite3.OperationalError: NOT NULL constraint failed: tasks.title`
—— 必填列没给值。插入语句里漏了这一列，或者传了 None。""",
                "beginner_practice": """1. 建一张 `books` 表（id 主键、title 必填、pages 整数），插入 3 本书并查询全部。
2. 故意插入重复 id，观察报错信息，再用「不传 id」的方式让它自增。""",
                "advanced_practice": """为 `tasks` 设计主键方案：分别用自增整数与 UUID 建两张表，
各插入 1000 行，比较存储大小与插入耗时，并说明在什么场景下更愿意用 UUID。""",
                "quiz_note": "本节 6 道题：重点考主键的语义与「业务字段当主键」的风险。",
                "summary": """表是实体集合，列是属性，行是记录；主键唯一标识一行且不可为空。
主键应选无业务含义、不会变化的字段；其他唯一字段单独加 UNIQUE 约束。
建表时列名与类型要写全，插入时显式列出列名。""",
                "next_lesson": "下一节讲外键与约束：怎么让「任务必须属于一个存在的用户」这件事由数据库保证。",
                "knowledge_points": [
                    {
                        "code": "python-database-01-01",
                        "name": "表、行、列与主键",
                        "goal": "能说清关系模型的基本单位，并为数据选择合适的主键。",
                        "minutes": 25,
                        "criteria": "能独立建表并解释为什么不用手机号当主键。",
                        "requires": [],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-01-01-1",
                        "kp": 0,
                        "title": "建一张 books 表",
                        "description": "用 sqlite3 建 books 表（id 主键、title 必填、pages 整数），插入 3 本书并查询打印。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute(
    """
    CREATE TABLE books (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        pages INTEGER NOT NULL
    )
    """
)
conn.executemany(
    "INSERT INTO books (title, pages) VALUES (?, ?)",
    [("Python 进阶", 320), ("数据库入门", 260), ("算法图解", 400)],
)
for row in conn.execute("SELECT id, title, pages FROM books"):
    print(row)''',
                        "explanation": "id 用 INTEGER PRIMARY KEY 即为自增；插入时不传 id，数据库自动分配。",
                    },
                    {
                        "code": "db-ex-01-01-2",
                        "kp": 0,
                        "title": "主键方案对比",
                        "description": "分别用自增整数与 UUID 建表各插入 1000 行，比较存储与耗时，说明何时选 UUID。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''自增整数：占 4—8 字节，索引紧凑，插入顺序即主键顺序，页分裂少。
UUID：占 16 字节（文本形式 36 字符），随机分布导致索引随机写，插入更慢但可提前生成。

选 UUID 的场景：需要在客户端或离线环境预先生成 ID、需要合并多库数据、不能暴露自增 ID 的业务量。''',
                        "explanation": "关键权衡是「索引局部性 vs 全局唯一可预生成」，能给出一致结论即可。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-01-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "主键必须满足的两个性质是？",
                        "options": [
                            ("A", "唯一且非空"),
                            ("B", "自增且为整数"),
                            ("C", "有业务含义且可修改"),
                            ("D", "必须是字符串"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "主键用于唯一标识一行，因此不能重复也不能为 NULL；自增与类型都不是强制要求。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-01-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "为什么不建议用手机号当主键？（多选）",
                        "options": [
                            ("A", "用户可能换号，主键变了所有关联数据都要改"),
                            ("B", "手机号属于个人信息，扩散到各表增加泄露风险"),
                            ("C", "数据库不支持文本主键"),
                            ("D", "手机号可能重复或为空"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "数据库完全支持文本主键，所以 C 错；其余三项都是真实顾虑。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-01-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面这段代码第二次插入会发生什么？
cursor.execute("INSERT INTO tasks (id, title) VALUES (1, 'A')")
cursor.execute("INSERT INTO tasks (id, title) VALUES (1, 'B')")''',
                        "answer": {
                            "reference": "第二次插入抛 IntegrityError: UNIQUE constraint failed: tasks.id，因为主键重复。",
                            "keywords": ["IntegrityError", "UNIQUE", "主键重复"],
                        },
                        "explanation": "主键唯一约束由数据库强制，不是靠应用层检查；重复时整条插入被拒绝。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-01-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "一张表可以没有主键，只是这样无法用主键精确定位某一行。",
                        "answer": {"value": True},
                        "explanation": "关系数据库允许无主键的表，但更新/删除只能靠其他条件匹配，容易误伤多行。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-01-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写建表语句：users 表，id 自增主键，email 必填且唯一，created_at 必填文本。",
                        "answer": {
                            "reference": '''CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);''',
                            "keywords": ["PRIMARY KEY", "UNIQUE", "NOT NULL"],
                        },
                        "explanation": "email 的唯一性用 UNIQUE 表达，与主键相互独立；created_at 在 SQLite 里通常存 ISO 文本。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-01-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "有同学说「主键就是第一列」。请指出这句话的问题，并说明主键的真正含义。",
                        "answer": {
                            "reference": "主键与列的位置无关，它是声明在某一列（或列组合）上的约束，要求唯一且非空。第一列只是书写习惯，完全可以把主键放在最后一列。真正含义是「用它就能唯一确定一行」，这决定了后续更新、外键引用都依赖它。",
                            "keywords": ["与位置无关", "约束", "唯一", "标识"],
                        },
                        "explanation": "能区分「书写顺序」与「约束语义」即可。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-database-01-lesson-02",
                "objectives": """1. 会用外键表达两张表之间的关系；
2. 会用 NOT NULL、UNIQUE、CHECK、DEFAULT 守住数据；
3. 理解外键的级联行为与「孤儿行」问题；
4. 知道 SQLite 默认不校验外键这件事。""",
                "why_learn": """任务表里存了 user_id，如果用户被删了，这条任务就成了找不到主人的孤儿数据。
靠应用层记得检查很容易漏，交给数据库约束才是可靠的。""",
                "concepts": """**外键（foreign key）** 指向另一张表的主键，表示引用关系。
**约束** 是对列取值的限制：`NOT NULL` 必填、`UNIQUE` 唯一、`CHECK` 自定义条件、`DEFAULT` 默认值。
**级联（cascade）** 决定父行被删/改时子行怎么处理：`CASCADE` 一起删、`SET NULL` 置空、`RESTRICT` 拒绝。
**孤儿行** 指子表里指向不存在父行的记录，外键约束正是用来防它。
SQLite 默认**不启用**外键校验，需要执行 `PRAGMA foreign_keys = ON`。""",
                "plain": """外键像「借书登记」：每本书的借出记录都写明借给了哪个读者编号。
如果这个读者编号根本不存在，登记就该被拒绝——这就是外键在做的事。
级联则是「读者注销时，他的借阅记录怎么处理」的规则：一起删、还是保留但清空归属。""",
                "syntax": """```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5)
);
```
注意：SQLite 需要先 `PRAGMA foreign_keys = ON;` 才会真正校验外键。""",
                "example_code": '''import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript(
    """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        email TEXT NOT NULL UNIQUE
    );
    CREATE TABLE tasks (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5)
    );
    """
)

conn.execute("INSERT INTO users (id, email) VALUES (1, 'a@example.com')")
conn.execute(
    "INSERT INTO tasks (user_id, title, priority) VALUES (1, '写周报', 2)"
)
print("合法插入成功")

try:
    conn.execute("INSERT INTO tasks (user_id, title) VALUES (99, '幽灵任务')")
except sqlite3.IntegrityError as exc:
    print("外键拦住：", exc)

try:
    conn.execute("INSERT INTO tasks (user_id, title, priority) VALUES (1, '越界', 9)")
except sqlite3.IntegrityError as exc:
    print("CHECK 拦住：", exc)

conn.execute("DELETE FROM users WHERE id = 1")
print("剩余任务", conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])
conn.close()''',
                "code_lines": """1. `PRAGMA foreign_keys = ON` 必须先执行，否则 SQLite 不校验外键，插入无效 user_id 也会成功。
2. `REFERENCES users(id)` 声明外键指向 users 的主键。
3. `ON DELETE CASCADE` 表示父行删除时子行一起删，避免孤儿数据。
4. `CHECK (priority BETWEEN 1 AND 5)` 把取值范围写进表结构，越界直接拒绝。
5. 第一次插入合法数据，验证正常路径可用。
6. 插入 user_id=99（不存在）触发 IntegrityError，说明外键真的生效。
7. 插入 priority=9 触发 CHECK 失败，说明约束不只是文档，而是可执行规则。
8. 删除用户后剩余任务为 0，验证级联删除确实清掉了子行。""",
                "output": """合法插入成功
外键拦住： FOREIGN KEY constraint failed
CHECK 拦住： CHECK constraint failed: priority BETWEEN 1 AND 5
剩余任务 0""",
                "mistakes": """- SQLite 里忘了 `PRAGMA foreign_keys = ON`，以为外键在生效。
- 外键列没建索引，删除父行时全表扫描，慢到超时。
- 用 CASCADE 却不知道会连带删数据，误删后无法恢复。
- `CHECK` 写成 `priority > 0` 却没写上限，脏数据照样进来。
- 先插子表再插父表，触发外键失败。""",
                "error_analysis": """`FOREIGN KEY constraint failed`
—— 引用了不存在的父行，或删除父行时子行还引用着它（未设级联）。先检查父行是否存在、级联规则是否合适。

`CHECK constraint failed: priority > 0`
—— 插入值不满足 CHECK 条件。错误信息里会带上约束表达式，照它核对取值。

`UNIQUE constraint failed: users.email`
—— 邮箱重复。需要「存在则更新」时用 UPSERT 而不是直接 INSERT。

外键插不进去但父行明明存在
—— 可能是连接未启用 `PRAGMA foreign_keys`，或者两张表在不同数据库文件里。""",
                "beginner_practice": """1. 建 users 与 tasks 两张表，给 tasks.user_id 加外键与级联删除，验证删用户后任务清空。
2. 把 ON DELETE 改成 RESTRICT，再删一次，观察报错差异。""",
                "advanced_practice": """设计一个「任务 + 标签」多对多结构：
tags 表、task_tags 关联表（双列联合主键 + 两个外键），
并验证「删除任务时关联行自动清理、但标签本身保留」。""",
                "quiz_note": "本节 6 道题：重点考 SQLite 的外键开关与级联语义。",
                "summary": """外键表达引用关系，级联决定父行变动时子行怎么办；
NOT NULL / UNIQUE / CHECK / DEFAULT 把业务规则下沉到表结构；
SQLite 默认不校验外键，必须显式 `PRAGMA foreign_keys = ON`。""",
                "next_lesson": "下一节开始写查询：SELECT、WHERE、ORDER BY、LIMIT 的准确用法与 NULL 陷阱。",
                "knowledge_points": [
                    {
                        "code": "python-database-01-02",
                        "name": "外键与表约束",
                        "goal": "能用外键表达关系、用约束守住数据，并理解级联行为。",
                        "minutes": 30,
                        "criteria": "能建出带外键与 CHECK 的表，并解释 SQLite 需要 PRAGMA 的原因。",
                        "requires": ["python-database-01-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-01-02-1",
                        "kp": 0,
                        "title": "级联删除对比",
                        "description": "分别用 ON DELETE CASCADE 与 RESTRICT 建两张子表，删除父行并对比结果。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''CASCADE：删除 users 中的行时，tasks 里对应行自动删除，剩余 0 行。
RESTRICT：删除被引用的 users 行时报 FOREIGN KEY constraint failed，父行不被删除。''',
                        "explanation": "CASCADE 适合「子数据没有独立价值」的场景；RESTRICT 适合「必须先人工处理子数据」的场景。",
                    },
                    {
                        "code": "db-ex-01-02-2",
                        "kp": 0,
                        "title": "任务标签多对多",
                        "description": "设计 tags 与 task_tags（双列联合主键、两个外键），验证删任务时关联行清理而标签保留。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE task_tags (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, tag_id)
);''',
                        "explanation": "联合主键天然阻止重复关联；两个外键分别级联，删任务只清理关联行，标签本身不受影响。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-01-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "在 SQLite 中要让外键约束真正生效，必须做什么？",
                        "options": [
                            ("A", "把外键列设为主键"),
                            ("B", "执行 PRAGMA foreign_keys = ON"),
                            ("C", "给表加索引"),
                            ("D", "使用事务"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "SQLite 为兼容旧行为默认关闭外键校验，需要按连接显式开启。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-01-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些属于列级约束？（多选）",
                        "options": [
                            ("A", "NOT NULL"),
                            ("B", "UNIQUE"),
                            ("C", "CHECK"),
                            ("D", "ORDER BY"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "ORDER BY 是查询排序子句，不是约束；其余三项都在建表时限制取值。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-01-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''连接未执行 PRAGMA foreign_keys = ON 时，下面语句会怎样？
INSERT INTO tasks (user_id, title) VALUES (999, '幽灵任务');''',
                        "answer": {
                            "reference": "插入会成功，因为外键校验被关闭；数据库中留下一条指向不存在用户的孤儿行。",
                            "keywords": ["插入成功", "孤儿行", "未校验"],
                        },
                        "explanation": "这是 SQLite 最容易踩的坑：约束写在表结构里，但默认不执行检查。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-01-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "ON DELETE CASCADE 会在删除父行时自动删除引用它的子行。",
                        "answer": {"value": True},
                        "explanation": "CASCADE 就是「跟着删」，适合子数据依附父数据的场景，比如任务的子步骤。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-01-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写建表语句：orders 表含 id 主键、user_id 外键指向 users、amount 必须大于 0。",
                        "answer": {
                            "reference": '''CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount REAL NOT NULL CHECK (amount > 0)
);''',
                            "keywords": ["REFERENCES", "CHECK", "NOT NULL"],
                        },
                        "explanation": "外键写 REFERENCES 表(列)，金额用 CHECK 保证为正，两者都是数据库层强制的规则。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-01-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「删除用户时把任务一起删」需要明确写出来，而不能依赖应用代码去删？",
                        "answer": {
                            "reference": "应用代码可能有多条删除路径（后台管理、定时清理、手工脚本），漏一条就产生孤儿数据；并发删除时也可能出现「刚查完没子行、删完又插进来」的窗口。外键级联由数据库在同一事务内保证，不受调用路径影响。",
                            "keywords": ["多条路径", "漏删", "并发", "数据库保证"],
                        },
                        "explanation": "核心是「约束应该在数据层统一生效，而不是每个调用方各自记得」。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "python-database-02",
        "title": "SQL 查询",
        "description": "写出可读且正确的查询：先过滤再排序，跨表用 JOIN。",
        "order_index": 2,
        "lessons": [
            {
                "code": "python-database-02-lesson-01",
                "objectives": """1. 会用 SELECT / WHERE / ORDER BY / LIMIT 组成完整查询；
2. 会用 AND、OR、IN、LIKE、BETWEEN 组合条件；
3. 理解 NULL 在比较与排序中的特殊行为；
4. 知道参数化查询为什么能防注入。""",
                "why_learn": """数据一多，「取哪些行、怎么排、取几条」就决定了接口快慢与结果对错。
NULL 处理不当还会让统计结果少算——这是线上报表最常见的错误来源之一。""",
                "concepts": """`SELECT 列 FROM 表` 指定取哪些列，`*` 表示全部（线上慎用）。
`WHERE` 过滤行，支持 `=`、`<>`、`>`、`IN`、`LIKE`、`BETWEEN`、`IS NULL`。
`ORDER BY 列 ASC|DESC` 排序，可以多列。
`LIMIT n OFFSET m` 分页。
**NULL 表示「未知」**：`NULL = NULL` 结果是 NULL 而不是 True，判断空值必须用 `IS NULL` / `IS NOT NULL`。
**参数化查询** 用占位符传值，由驱动负责转义，是防 SQL 注入的唯一正确做法。""",
                "plain": """SELECT 像在表格上做筛选：先按条件圈出哪些行（WHERE），
再决定按哪一列排队（ORDER BY），最后只取前几条（LIMIT）。
NULL 则像表格里的空白格：它不是 0、也不是空字符串，而是「这里没填」。
所以「没填 = 没填」在逻辑上不是「真」，得专门问「是不是空白」。""",
                "syntax": """```sql
SELECT 列1, 列2
FROM 表
WHERE 条件1 AND 条件2
ORDER BY 列1 DESC, 列2 ASC
LIMIT 10 OFFSET 0;
```
NULL 判断：`WHERE parent_id IS NULL`，不要写 `= NULL`。
模糊匹配：`WHERE title LIKE '周%'`，`%` 匹配任意长度，`_` 匹配单个字符。""",
                "example_code": '''import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute(
    """
    CREATE TABLE tasks (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        priority INTEGER NOT NULL DEFAULT 3,
        tag TEXT
    )
    """
)
conn.executemany(
    "INSERT INTO tasks (title, done, priority, tag) VALUES (?, ?, ?, ?)",
    [
        ("写周报", 0, 1, "工作"),
        ("交报表", 1, 2, "工作"),
        ("订会议室", 0, 3, "行政"),
        ("买咖啡豆", 0, 4, None),
    ],
)

def run(sql, params=()):
    print(sql.strip().splitlines()[0])
    for row in conn.execute(sql, params):
        print("  ", tuple(row))

run("SELECT title, priority FROM tasks WHERE done = 0 ORDER BY priority LIMIT 2")
run("SELECT title FROM tasks WHERE tag IS NULL")
run("SELECT COUNT(*) FROM tasks WHERE tag = NULL")
run("SELECT title FROM tasks WHERE title LIKE '%周%' OR priority BETWEEN 3 AND 4")
run("SELECT title FROM tasks ORDER BY tag DESC")
run(
    "SELECT title FROM tasks WHERE title LIKE ?",
    ("%" + "报表" + "%",),
)''',
                "code_lines": """1. 第一条查询：只取未完成，按优先级升序，取前 2 条 —— 典型的「最紧急待办」。
2. `tag IS NULL` 才能找到「没打标签」的行，这是 NULL 的正确判断方式。
3. `tag = NULL` 永远返回 0 行：与 NULL 的任何比较结果都是 NULL，不是真。
4. `LIKE '%周%'` 匹配**包含**「周」的标题（两边都有 `%`），`OR` 组合范围条件，缺括号时优先级要小心。
5. `ORDER BY tag DESC` 里 NULL 排在**最后**（SQLite 视 NULL 为最小，降序时沉底）；升序则会排在最前，排序结果依赖 NULL 位置时要显式处理。
6. 最后一条用 `?` 传参，即使值里带引号也不会破坏语句结构，这是防注入的关键。
7. `run` 只打印语句首行与结果，便于对照每条查询的输出。""",
                "output": """SELECT title, priority FROM tasks WHERE done = 0 ORDER BY priority LIMIT 2
   ('写周报', 1)
   ('订会议室', 3)
SELECT title FROM tasks WHERE tag IS NULL
   ('买咖啡豆',)
SELECT COUNT(*) FROM tasks WHERE tag = NULL
   (0,)
SELECT title FROM tasks WHERE title LIKE '%周%' OR priority BETWEEN 3 AND 4
   ('写周报',)
   ('订会议室',)
   ('买咖啡豆',)
SELECT title FROM tasks ORDER BY tag DESC
   ('订会议室',)
   ('写周报',)
   ('交报表',)
   ('买咖啡豆',)
SELECT title FROM tasks WHERE title LIKE ?
   ('交报表',)""",
                "mistakes": """- 用 `= NULL` 判断空值，永远查不到数据。
- `WHERE a = 1 OR b = 2 AND c = 3` 忘记括号，AND 优先级高于 OR 导致结果错。
- 用 `SELECT *` 取全部列，表结构一变接口字段就跟着变。
- 用字符串拼接 SQL，直接暴露注入风险。
- 分页只写 LIMIT 不写 ORDER BY，每次返回顺序不稳定。""",
                "error_analysis": """查询结果为空但数据确实存在
—— 常见是 `= NULL` 写法。改成 `IS NULL`，或检查条件里是否有隐式类型转换（`done = '0'`）。

`sqlite3.OperationalError: no such column: tag`
—— 列名写错或表建错。用 `PRAGMA table_info(tasks)` 查看真实列名。

`sqlite3.ProgrammingError: Incorrect number of bindings supplied`
—— 占位符数量与参数个数不一致，多一个逗号少一个值都会报。

分页重复或漏数据
—— 没有唯一排序键。`ORDER BY priority` 遇到相同值时顺序不确定，应补 `, id` 作为次级排序。""",
                "beginner_practice": """1. 查出所有 tag 为「工作」且未完成的任务，按优先级倒序。
2. 用 `LIKE` 查出标题含「报」的任务，再改成参数化写法。""",
                "advanced_practice": """实现分页查询函数 `page(conn, size, index)`：
要求结果稳定（ORDER BY priority, id）、返回该页数据与总条数，
并说明为什么不能只靠 LIMIT/OFFSET 做深度分页。""",
                "quiz_note": "本节 6 道题：重点是 NULL 语义与参数化查询。",
                "summary": """SELECT → WHERE → ORDER BY → LIMIT 是查询的基本骨架；
NULL 要用 IS NULL 判断，参与比较会得到 NULL；
参数化查询用占位符，是防注入的唯一正确做法。""",
                "next_lesson": "下一节讲 JOIN 与聚合：把两张表按关系拼起来，并做分组统计。",
                "knowledge_points": [
                    {
                        "code": "python-database-02-01",
                        "name": "SELECT 查询与过滤",
                        "goal": "能写出带过滤、排序、分页的查询，正确处理 NULL，并用参数化防注入。",
                        "minutes": 30,
                        "criteria": "能独立写出稳定分页查询，并解释 `= NULL` 为什么查不到数据。",
                        "requires": ["python-database-01-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-02-01-1",
                        "kp": 0,
                        "title": "筛选待办",
                        "description": "查 tag 为「工作」且未完成的任务，按 priority 倒序；再用 LIKE 查含「报」的标题，要求参数化。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''rows = conn.execute(
    "SELECT title FROM tasks WHERE tag = ? AND done = 0 ORDER BY priority DESC",
    ("工作",),
).fetchall()

rows = conn.execute(
    "SELECT title FROM tasks WHERE title LIKE ?", ("%报%",)
).fetchall()''',
                        "explanation": "两个条件用 AND 连接，占位符按顺序传参；LIKE 的 % 要拼在参数里而不是 SQL 字符串里。",
                    },
                    {
                        "code": "db-ex-02-01-2",
                        "kp": 0,
                        "title": "稳定分页",
                        "description": "实现 page(conn, size, index)，返回该页数据与总数，排序要能保证不重不漏。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def page(conn, size=10, index=0):
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    rows = conn.execute(
        "SELECT id, title FROM tasks ORDER BY priority, id LIMIT ? OFFSET ?",
        (size, size * index),
    ).fetchall()
    return rows, total''',
                        "explanation": "ORDER BY 必须带唯一列（id）做次级排序；深度分页时 OFFSET 越大扫描越多，应改为游标分页。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-02-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要查出 tag 为空的行，正确的条件是？",
                        "options": [
                            ("A", "WHERE tag = NULL"),
                            ("B", "WHERE tag IS NULL"),
                            ("C", "WHERE tag = ''"),
                            ("D", "WHERE tag == None"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "与 NULL 的任何比较都返回 NULL，必须用 IS NULL；空字符串是另一种取值。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-02-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于参数化查询，下列说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "用 ? 或命名占位符传值"),
                            ("B", "能防止 SQL 注入"),
                            ("C", "参数值里的引号会被自动处理"),
                            ("D", "参数会自动进行类型转换并对所有非法值报错"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "参数化解决的是「值不参与语句解析」，不会替你做业务校验，所以 D 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-02-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面查询返回几行？
SELECT COUNT(*) FROM tasks WHERE tag = NULL;''',
                        "answer": {
                            "reference": "返回 0。与 NULL 比较的结果是 NULL，条件不成立，任何行都不匹配。",
                            "keywords": ["0", "NULL", "不匹配"],
                        },
                        "explanation": "这是 SQL 三值逻辑的直接体现：条件不是「假」，而是「未知」，因此不返回该行。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-02-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`WHERE a = 1 OR b = 2 AND c = 3` 与 `WHERE (a = 1 OR b = 2) AND c = 3` 结果相同。",
                        "answer": {"value": False},
                        "explanation": "AND 优先级高于 OR，前者的含义是 a=1 或者（b=2 且 c=3），与加括号后完全不同。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-02-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写查询：取 tasks 中未完成的前 5 条，按 priority 升序、id 升序，只返回 id 与 title。",
                        "answer": {
                            "reference": '''SELECT id, title FROM tasks
WHERE done = 0
ORDER BY priority, id
LIMIT 5;''',
                            "keywords": ["SELECT id, title", "WHERE done = 0", "ORDER BY", "LIMIT 5"],
                        },
                        "explanation": "补上 id 作为次级排序，才能保证相同优先级下顺序稳定。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-02-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「用字符串拼接生成 SQL」即使做了引号转义仍然危险？",
                        "answer": {
                            "reference": "转义规则很难覆盖所有数据库与字符集，而且拼接后 SQL 文本与数据混在一起，攻击者只要找到一处绕过就有注入空间；此外拼接还会破坏预编译语句的缓存。参数化让语句结构在传值前就固定，值永远只被当作数据。",
                            "keywords": ["绕过", "结构固定", "预编译", "数据与语句分离"],
                        },
                        "explanation": "核心是「语句结构与数据必须分离」，而不是靠过滤特殊字符。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "python-database-02-lesson-02",
                "objectives": """1. 会用 INNER JOIN 与 LEFT JOIN 连接多表；
2. 能解释两种 JOIN 的结果差异；
3. 会用 GROUP BY、HAVING、聚合函数做统计；
4. 能发现并避免常见的 JOIN 放大问题。""",
                "why_learn": """真实查询很少只查一张表：任务要带上用户邮箱，订单要统计每个用户的消费。
JOIN 写错（尤其是该用 LEFT 却用了 INNER）会静默丢数据，报表数字看着合理但对不上账。""",
                "concepts": """`INNER JOIN` 只保留两侧都匹配的行；`LEFT JOIN` 保留左表全部行，右表匹配不上填 NULL。
`ON` 指定连接条件，`WHERE` 在连接之后过滤。
聚合函数：`COUNT`、`SUM`、`AVG`、`MAX`、`MIN`。
`GROUP BY` 按列分组，每组产出一行；`HAVING` 在分组后过滤。
**连接放大**：一对多连接后行数变多，直接 SUM 会重复计算，需要先聚合再连接。""",
                "plain": """JOIN 像把两张名单按「学号」对齐：两边都有的贴一起（INNER），
左边全留着、右边没有就空着（LEFT）。
统计时如果一个人有多条记录，直接求和会把他的「总消费」重复算几遍——这就是连接放大。""",
                "syntax": """```sql
SELECT u.email, COUNT(t.id) AS task_count
FROM users AS u
LEFT JOIN tasks AS t ON t.user_id = u.id
GROUP BY u.id, u.email
HAVING COUNT(t.id) > 0
ORDER BY task_count DESC;
```
方向记忆：`A LEFT JOIN B` 保住 A 的全部行；`COUNT(列)` 不统计 NULL，`COUNT(*)` 统计行数。""",
                "example_code": '''import sqlite3

conn = sqlite3.connect(":memory:")
conn.executescript(
    """
    CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL);
    CREATE TABLE tasks (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        minutes INTEGER NOT NULL
    );
    INSERT INTO users (id, email) VALUES (1, 'a@x.com'), (2, 'b@x.com'), (3, 'c@x.com');
    INSERT INTO tasks (user_id, title, minutes) VALUES
        (1, '写周报', 30), (1, '交报表', 45), (2, '订会议室', 10);
    """
)

def show(sql):
    print(sql.strip().splitlines()[0])
    for row in conn.execute(sql):
        print("  ", tuple(row))

show(
    """
    SELECT u.email, COUNT(t.id) AS cnt
    FROM users AS u
    INNER JOIN tasks AS t ON t.user_id = u.id
    GROUP BY u.id, u.email
    ORDER BY cnt DESC
    """
)
show(
    """
    SELECT u.email, COUNT(t.id) AS cnt, COALESCE(SUM(t.minutes), 0) AS total
    FROM users AS u
    LEFT JOIN tasks AS t ON t.user_id = u.id
    GROUP BY u.id, u.email
    ORDER BY total DESC
    """
)
show(
    """
    SELECT u.email, SUM(t.minutes) AS total
    FROM users AS u
    JOIN tasks AS t ON t.user_id = u.id
    GROUP BY u.email
    HAVING SUM(t.minutes) >= 40
    """
)
show(
    """
    SELECT COUNT(*) AS all_rows, COUNT(DISTINCT user_id) AS users
    FROM tasks
    """
)''',
                "code_lines": """1. INNER JOIN 只返回有任务的用户，所以第 3 个用户（无任务）不会出现。
2. `COUNT(t.id)` 统计匹配到的任务行数，NULL 不计入。
3. LEFT JOIN 保住所有用户，没任务的用户 cnt 为 0、SUM 为 NULL。
4. `COALESCE(SUM(t.minutes), 0)` 把 NULL 换成 0，避免接口返回 null。
5. 第三条用 HAVING 在分组后筛选总时长 ≥ 40 的用户，WHERE 做不到这一点。
6. 最后一条对比 `COUNT(*)` 与 `COUNT(DISTINCT user_id)`，说明行数与人数不是一回事。
7. 所有查询都显式写了 GROUP BY 的分组列，避免依赖数据库的宽松模式。""",
                "output": """SELECT u.email, COUNT(t.id) AS cnt
   ('a@x.com', 2)
   ('b@x.com', 1)
SELECT u.email, COUNT(t.id) AS cnt, COALESCE(SUM(t.minutes), 0) AS total
   ('a@x.com', 2, 75)
   ('b@x.com', 1, 10)
   ('c@x.com', 0, 0)
SELECT u.email, SUM(t.minutes) AS total
   ('a@x.com', 75)
SELECT COUNT(*) AS all_rows, COUNT(DISTINCT user_id) AS users
   (3, 2)""",
                "mistakes": """- 该用 LEFT JOIN 却用 INNER，把「没有记录的用户」整行丢掉。
- 在 WHERE 里对右表列加条件（`WHERE t.done = 0`），把 LEFT JOIN 退化成 INNER。
- 一对多连接后直接 SUM，金额被重复累加。
- `GROUP BY` 漏写非聚合列，结果不确定。
- 用 `COUNT(*)` 当用户数，实际统计的是行数。""",
                "error_analysis": """LEFT JOIN 结果里少了没有子记录的行
—— WHERE 里出现了右表条件，NULL 行被过滤掉。把条件移到 ON 里，或改成 `WHERE t.done = 0 OR t.id IS NULL`。

统计金额明显偏大
—— 连接放大了行数。先把子表聚合到一行再连接，或用子查询先算小计。

`sqlite3.OperationalError: ambiguous column name: id`
—— 两张表都有 id，必须写表别名前缀，如 `u.id`。

分组结果缺行
—— HAVING 条件过严，或 GROUP BY 用了会变 NULL 的列。""",
                "beginner_practice": """1. 查出每个用户的邮箱与任务数（含 0 个任务的用户）。
2. 查出任务数大于 1 的用户，按任务数降序。""",
                "advanced_practice": """统计「每个用户已完成任务的总时长」，要求：
没有任务的用户显示 0、只统计 done = 1 的任务、按总时长降序。
提示：条件要放在 ON 里而不是 WHERE 里，并说明原因。""",
                "quiz_note": "本节 6 道题：重点考 LEFT JOIN 与 WHERE 的相互作用、以及连接放大。",
                "summary": """INNER JOIN 取交集，LEFT JOIN 保住左表；条件放 ON 还是 WHERE 会改变结果。
GROUP BY 分组、HAVING 过滤分组、聚合函数做统计；
一对多连接后求和要小心重复累加。""",
                "next_lesson": "下一节用 Python 的 sqlite3 把建表、查询、事务串起来，写出真正能落地的数据访问代码。",
                "knowledge_points": [
                    {
                        "code": "python-database-02-02",
                        "name": "JOIN 与聚合",
                        "goal": "能正确选择 JOIN 类型，用 GROUP BY/HAVING 完成跨表统计，并识别连接放大。",
                        "minutes": 40,
                        "criteria": "能写出含 0 记录的统计查询，并解释条件放 ON 与 WHERE 的差异。",
                        "requires": ["python-database-02-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-02-02-1",
                        "kp": 0,
                        "title": "含零值的任务统计",
                        "description": "查出每个用户的邮箱与任务数（没有任务的显示 0），按任务数降序。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''SELECT u.email, COUNT(t.id) AS cnt
FROM users AS u
LEFT JOIN tasks AS t ON t.user_id = u.id
GROUP BY u.id, u.email
ORDER BY cnt DESC;''',
                        "explanation": "必须 LEFT JOIN 才能保住无任务用户；COUNT(t.id) 对 NULL 不计数，天然得到 0。",
                    },
                    {
                        "code": "db-ex-02-02-2",
                        "kp": 0,
                        "title": "已完成时长统计",
                        "description": "统计每个用户已完成任务总时长，无任务显示 0，按总时长降序；条件放 ON 并说明原因。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''SELECT u.email, COALESCE(SUM(t.minutes), 0) AS total
FROM users AS u
LEFT JOIN tasks AS t ON t.user_id = u.id AND t.done = 1
GROUP BY u.id, u.email
ORDER BY total DESC;''',
                        "explanation": "条件放 WHERE 会把右表为 NULL 的行过滤掉，LEFT JOIN 退化为 INNER；放 ON 只影响匹配，不影响保留左表全部行。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-02-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要列出所有用户及其任务数（没有任务的也要出现），应使用？",
                        "options": [
                            ("A", "INNER JOIN"),
                            ("B", "LEFT JOIN，并用 COUNT(子表主键)"),
                            ("C", "CROSS JOIN"),
                            ("D", "UNION"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "LEFT JOIN 保住左表全部行；COUNT(子表列) 对 NULL 不计数，无任务用户自然得 0。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-02-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 GROUP BY 与 HAVING，说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "WHERE 在分组前过滤行，HAVING 在分组后过滤组"),
                            ("B", "HAVING 可以直接使用聚合函数结果"),
                            ("C", "GROUP BY 后 SELECT 里只能出现分组列与聚合结果"),
                            ("D", "HAVING 可以完全替代 WHERE"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "HAVING 作用于分组结果，不能替代行级过滤，所以 D 错；其余三项都是正确语义。",
                        "difficulty": "advanced",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-02-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面查询为什么查不出「没有任务的用户」？
SELECT u.email, COUNT(t.id)
FROM users u LEFT JOIN tasks t ON t.user_id = u.id
WHERE t.title LIKE '%报表%'
GROUP BY u.email;''',
                        "answer": {
                            "reference": "WHERE 里的 t.title 条件把右表为 NULL 的行过滤掉了，LEFT JOIN 退化成 INNER JOIN。条件应移到 ON 子句。",
                            "keywords": ["WHERE", "退化为 INNER", "ON", "NULL"],
                        },
                        "explanation": "LEFT JOIN 的「保留左表」发生在连接阶段，WHERE 在其后执行，NULL 行无法通过右表条件。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-02-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "对一对多关系直接 JOIN 后 SUM(金额)，得到的总额一定等于子表金额之和。",
                        "answer": {"value": False},
                        "explanation": "若另一侧也是一对多，行会被放大，SUM 会重复累加；需要先聚合到同一粒度再连接。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-02-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写查询：统计每个用户的任务数与总时长（无任务显示 0），按总时长降序取前 10。",
                        "answer": {
                            "reference": '''SELECT u.email, COUNT(t.id) AS cnt, COALESCE(SUM(t.minutes), 0) AS total
FROM users AS u
LEFT JOIN tasks AS t ON t.user_id = u.id
GROUP BY u.id, u.email
ORDER BY total DESC
LIMIT 10;''',
                            "keywords": ["LEFT JOIN", "COALESCE", "GROUP BY", "LIMIT 10"],
                        },
                        "explanation": "COALESCE 把 NULL 变成 0，保证接口返回数字而不是空值。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-02-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "某报表的「总消费」比财务系统高了 20%，你会怎么排查？请给出排查顺序。",
                        "answer": {
                            "reference": "先确认连接是否放大：检查 JOIN 的另一侧是否一对多，比较连接后的行数与去重后的订单数。再确认是否有重复数据（同一订单多次入库）、金额字段是否被重复求和（子查询里已聚合又在外层 SUM）。最后核对时间范围与状态过滤是否与财务口径一致。",
                            "keywords": ["连接放大", "去重", "重复统计", "口径"],
                        },
                        "explanation": "先怀疑结构性放大，再排查数据重复，最后对齐业务口径，是最高效的顺序。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "python-database-03",
        "title": "SQLite 实战",
        "description": "用项目真实的 SQLite 完成建库、查询与备份。",
        "order_index": 3,
        "lessons": [
            {
                "code": "python-database-03-lesson-01",
                "objectives": """1. 会用 sqlite3 模块完成连接、建表、增删改查；
2. 会用上下文管理器保证提交或回滚；
3. 理解 SQLite 的适用场景与限制；
4. 会做在线备份与常见运维检查。""",
                "why_learn": """小码后端本身就用 SQLite：一个文件即数据库，零运维、易备份。
但也正因为「太方便」，很多人踩同样的坑：连接没关、事务没提交、并发写入锁表。""",
                "concepts": """**连接（connection）** 代表一次数据库会话，`sqlite3.connect(path)` 创建。
**游标（cursor）** 执行语句并持有结果，也可以直接用连接执行。
**事务** 由连接隐式管理：DML 后需 `commit()`，异常时 `rollback()`。
`with conn:` 是**事务**上下文：正常结束提交、异常回滚，但不是关闭连接。
`with closing(conn):` 才是关闭连接。
SQLite 特性：单文件、支持大部分 SQL、写操作串行（同一时刻一个写者），适合中小规模与单机部署。""",
                "plain": """SQLite 像一个「自带全套工具的便携厨房」：打开一个文件就能做饭，不用请管理员。
代价是同一时间只能一个人动锅（写锁），所以它适合小团队、单机服务，
不适合高并发写入的大型系统。""",
                "syntax": """```python
import sqlite3
from contextlib import closing

with closing(sqlite3.connect("app.db")) as conn:
    conn.row_factory = sqlite3.Row
    with conn:                      # 事务：成功提交、异常回滚
        conn.execute("INSERT INTO tasks (title) VALUES (?)", ("写周报",))
    row = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()
    print(row["n"])
```
注意：`with conn` 管事务，`closing` 管关闭，两者经常一起用。""",
                "example_code": '''import sqlite3
from contextlib import closing
from pathlib import Path
import tempfile

db_path = Path(tempfile.mkdtemp()) / "app.db"

with closing(sqlite3.connect(db_path)) as conn:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    with conn:
        conn.execute(
            "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)"
        )
        conn.executemany(
            "INSERT INTO tasks (title) VALUES (?)",
            [("写周报",), ("交报表",)],
        )

    with conn:
        conn.execute("INSERT INTO tasks (title) VALUES (?)", ("订会议室",))
    print("提交后行数", conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])

    try:
        with conn:
            conn.execute("INSERT INTO tasks (title) VALUES (?)", ("会被回滚",))
            raise RuntimeError("业务失败")
    except RuntimeError as exc:
        print("已回滚：", exc)
    print("回滚后行数", conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])

    print("表结构", [row["name"] for row in conn.execute("PRAGMA table_info(tasks)")])
    print("完整性", conn.execute("PRAGMA integrity_check").fetchone()[0])
    print("数据库大小", db_path.stat().st_size > 0)''',
                "code_lines": """1. `closing(...)` 保证离开 with 时连接一定被关闭，异常路径也一样。
2. `row_factory = sqlite3.Row` 让结果支持按列名读取，代码更可读。
3. 第一个 `with conn:` 是事务块，正常结束自动 commit，无需手写。
4. 建表与插入放在同一事务里，失败时不会留下半张表。
5. 第二个事务插入一条并提交，行数变成 3。
6. 第三个事务里故意抛异常，`with` 触发回滚，「会被回滚」这行不会留下，行数仍是 3。
7. `PRAGMA table_info` 查看列定义，是排查「列名不存在」的第一步。
8. `PRAGMA integrity_check` 返回 ok 表示文件结构完好，可用于启动自检与备份后校验。""",
                "output": """提交后行数 3
已回滚： 业务失败
回滚后行数 3
表结构 ['id', 'title']
完整性 ok
数据库大小 True""",
                "mistakes": """- 执行 INSERT 后忘了 `commit()`，换一个连接就查不到数据。
- 以为 `with conn:` 会关闭连接，导致连接泄漏。
- 用字符串格式化拼 SQL，引入注入风险。
- 每次请求都新建连接且不关闭，文件句柄耗尽。
- 在长事务里做网络请求，写锁被长期占用。""",
                "error_analysis": """`sqlite3.OperationalError: database is locked`
—— 另一个连接持有写锁。缩短事务、避免长事务里做耗时操作；必要时设置 `timeout`。

`sqlite3.ProgrammingError: Cannot operate on a closed database`
—— 连接已关闭还在用。检查 `with closing(...)` 的作用域，别把连接传到块外使用。

插入成功但查询为空
—— 没有 commit。SQLite 默认事务隔离，未提交的写对其他连接不可见。

`sqlite3.OperationalError: attempt to write a readonly database`
—— 文件权限或目录不可写；也可能是 WAL 模式下 `-wal` 文件权限问题。""",
                "beginner_practice": """1. 写一个 `init_db(path)` 函数：建表、插入 3 条数据，返回行数。
2. 故意在事务里抛异常，验证数据没有写入。""",
                "advanced_practice": """实现 `backup(src, dst)`：用 SQLite 的在线备份 API（`conn.backup`）把数据复制到目标文件，
要求备份后对目标文件跑 `PRAGMA integrity_check` 并比较行数。""",
                "quiz_note": "本节 6 道题：重点考 `with conn` 与 `closing` 的区别、以及未提交的可见性。",
                "summary": """sqlite3 用连接执行语句，`with conn` 管事务、`closing` 管关闭；
未提交的写对其他连接不可见；写操作串行，要避免长事务；
`PRAGMA table_info`、`integrity_check` 是最常用的两个自查命令。""",
                "next_lesson": "下一节讲索引：为什么加了索引查询快十倍，以及什么情况下索引反而拖慢写入。",
                "knowledge_points": [
                    {
                        "code": "python-database-03-01",
                        "name": "SQLite 与 sqlite3 模块",
                        "goal": "能用 sqlite3 完成建表与增删改查，正确管理事务与连接生命周期。",
                        "minutes": 35,
                        "criteria": "能写出带事务回滚的数据访问函数，并解释 `with conn` 的作用范围。",
                        "requires": ["python-database-02-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-03-01-1",
                        "kp": 0,
                        "title": "init_db 与回滚验证",
                        "description": "写 init_db(path)：建表、插入 3 条并返回行数；再写一个故意抛异常的事务，验证数据未写入。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''import sqlite3
from contextlib import closing


def init_db(path):
    with closing(sqlite3.connect(path)) as conn:
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)"
            )
            conn.executemany(
                "INSERT INTO tasks (title) VALUES (?)",
                [("a",), ("b",), ("c",)],
            )
        return conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]''',
                        "explanation": "CREATE TABLE IF NOT EXISTS 让函数可重复调用；事务块结束自动提交。",
                    },
                    {
                        "code": "db-ex-03-01-2",
                        "kp": 0,
                        "title": "在线备份",
                        "description": "实现 backup(src, dst)，用 conn.backup 复制数据，并对目标库跑 integrity_check 与行数比较。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''import sqlite3
from contextlib import closing


def backup(src_path, dst_path):
    with closing(sqlite3.connect(src_path)) as src:
        with closing(sqlite3.connect(dst_path)) as dst:
            src.backup(dst)
    with closing(sqlite3.connect(dst_path)) as conn:
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        rows = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    return ok, rows''',
                        "explanation": "backup 是在线备份，不需要停服务；备份后必须校验，否则损坏的文件会在恢复时才发现。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-03-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`with conn:` 在 sqlite3 里的作用是？",
                        "options": [
                            ("A", "关闭数据库连接"),
                            ("B", "管理事务：正常结束提交、异常时回滚"),
                            ("C", "自动创建数据库文件"),
                            ("D", "开启外键校验"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "with conn 是事务上下文，不负责关闭连接；关闭要用 closing() 或手动 close()。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-03-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "SQLite 适合下列哪些场景？（多选）",
                        "options": [
                            ("A", "单机小服务与桌面应用"),
                            ("B", "需要跨机器水平扩展的高并发写入"),
                            ("C", "本地开发与自动化测试"),
                            ("D", "数据量中等、读多写少的内部工具"),
                        ],
                        "answer": {"values": ["A", "C", "D"]},
                        "explanation": "SQLite 写操作串行、无网络协议，不适合多机高并发写入，所以 B 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-03-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码在另一个连接里能查到刚插入的数据吗？
conn.execute("INSERT INTO tasks (title) VALUES ('x')")
# 未调用 commit''',
                        "answer": {
                            "reference": "不能。未提交的写在其他连接上不可见，只有当前连接能看到本事务内的改动。",
                            "keywords": ["不可见", "未提交", "事务"],
                        },
                        "explanation": "事务隔离保证「未提交的修改不出现在别人的视图里」，提交后才对外生效。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-03-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`PRAGMA integrity_check` 返回 ok 表示数据库文件结构完好。",
                        "answer": {"value": True},
                        "explanation": "它检查页结构与索引一致性，是备份后校验的常用手段，但不检查业务数据是否正确。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-03-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个函数，用 sqlite3 查询指定用户的未完成任务数，要求连接一定会被关闭。",
                        "answer": {
                            "reference": '''import sqlite3
from contextlib import closing


def pending_count(path, user_id):
    with closing(sqlite3.connect(path)) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND done = 0",
            (user_id,),
        ).fetchone()
    return row[0]''',
                            "keywords": ["closing", "COUNT(*)", "占位符"],
                        },
                        "explanation": "closing 保证异常时也关闭连接；参数化避免注入。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-03-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "遇到 `database is locked` 时，你会按什么顺序排查与处理？",
                        "answer": {
                            "reference": "先看是否有长事务占着写锁（例如事务里做了网络请求或大量计算），把耗时操作移出事务；再看是否有连接未提交、未关闭导致锁未释放；然后确认是否多进程同时写，考虑改用 WAL 模式提升并发读；最后才考虑调大 timeout 或串行化写入。",
                            "keywords": ["长事务", "未提交", "WAL", "timeout"],
                        },
                        "explanation": "先治根因（事务过长、连接泄漏），再考虑配置层缓解，是正确顺序。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
]
