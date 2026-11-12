"""数据库与 Python 数据库开发：第 4—6 章（索引、事务、SQLAlchemy 2.x）。"""

CHAPTERS: list[dict] = [
    {
        "code": "python-database-04",
        "title": "索引",
        "description": "理解索引为什么快、什么时候不快。",
        "order_index": 4,
        "lessons": [
            {
                "code": "python-database-04-lesson-01",
                "objectives": """1. 说清索引的数据结构与被索引列的选择原则；
2. 会用 EXPLAIN QUERY PLAN 判断是否命中索引；
3. 知道复合索引的「最左前缀」规则；
4. 能说出索引带来的写放大与存储成本。""",
                "why_learn": """一条查询从 2 秒降到 20 毫秒，通常不是换了机器，而是补了一个索引。
反过来，乱加索引会让写入变慢、存储膨胀，还可能因为「函数包住列」而根本用不上。""",
                "concepts": """**索引** 是一棵按键值排序的辅助结构（SQLite 用 B-Tree），让数据库能快速定位行而不用全表扫描。
**全表扫描** 指逐行检查，数据量大时线性变慢。
**复合索引** 是多个列组成的索引，遵循**最左前缀**：只有从最左列开始的连续条件才能用上。
**覆盖索引** 指查询所需列都在索引里，不必回表取数据。
**写放大**：每次增删改都要同步维护索引，索引越多写越慢。
在列上套函数（如 `WHERE lower(email) = ?`）通常会让索引失效。""",
                "plain": """索引像书的目录：找某一章不用从头翻，直接按页码跳过去。
但目录不是越多越好——每改一页内容，相关目录条目都要跟着改，书越厚维护越费劲。
复合索引则像「先按城市、再按街道」排序的通讯录：只查街道（跳过城市）就没法用这个顺序。""",
                "syntax": """```sql
CREATE INDEX idx_tasks_user_done ON tasks (user_id, done);

-- 查看是否命中
EXPLAIN QUERY PLAN
SELECT * FROM tasks WHERE user_id = 1 AND done = 0;

-- 命中时出现 SEARCH ... USING INDEX idx_tasks_user_done
-- 未命中时出现 SCAN tasks
```""",
                "example_code": '''import sqlite3

conn = sqlite3.connect(":memory:")
conn.executescript(
    """
    CREATE TABLE tasks (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        done INTEGER NOT NULL,
        title TEXT NOT NULL
    );
    """
)
conn.executemany(
    "INSERT INTO tasks (user_id, done, title) VALUES (?, ?, ?)",
    [(index % 50, (index // 7) % 2, f"任务{index}") for index in range(5000)],
)


def plan(sql, params=()):
    rows = conn.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
    return " | ".join(row[-1] for row in rows)


before = plan("SELECT title FROM tasks WHERE user_id = ? AND done = 0", (7,))
print("建索引前：", before)

conn.execute("CREATE INDEX idx_tasks_user_done ON tasks (user_id, done)")
after = plan("SELECT title FROM tasks WHERE user_id = ? AND done = 0", (7,))
print("建索引后：", after)

only_done = plan("SELECT title FROM tasks WHERE done = 0")
print("只查第二列：", only_done)

with_func = plan("SELECT title FROM tasks WHERE lower(title) = ?", ("任务7",))
print("列上套函数：", with_func)

counts = conn.execute(
    "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND done = 0", (7,)
).fetchone()[0]
print("命中行数", counts)
# PRAGMA index_list 返回 (序号, 索引名, 是否唯一, 来源, 是否部分索引)
print("索引清单", [row[1] for row in conn.execute("PRAGMA index_list(tasks)")])''',
                "code_lines": """1. 造 5000 行数据，`index % 50` 让 user_id 分布均匀；done 用 `(index // 7) % 2`，避免与 user_id 同奇偶而全表同值。
2. `EXPLAIN QUERY PLAN` 不真正执行查询，只返回执行计划，`row[-1]` 是计划描述文本。
3. 建索引前是 `SCAN tasks`，表示逐行扫描全表。
4. `CREATE INDEX (user_id, done)` 后变成 `SEARCH tasks USING INDEX ...`，说明命中。
5. 只按 `done` 过滤时仍然是 SCAN：done 是复合索引的第二列，跳过最左列用不上。
6. `lower(title)` 把列包在函数里，索引无法按原值查找，计划里出现 `SCAN`。
7. 最后两项分别验证结果正确性与索引是否真的存在，避免「以为建了其实没建」。""",
                "output": """建索引前： SCAN tasks
建索引后： SEARCH tasks USING INDEX idx_tasks_user_done (user_id=? AND done=?)
只查第二列： SCAN tasks
列上套函数： SCAN tasks
命中行数 43
索引清单 ['idx_tasks_user_done']""",
                "mistakes": """- 给每个列都建单列索引，写入变慢且大部分用不上。
- 复合索引顺序写反（把低选择性的列放最左）。
- 查询条件里对列用函数或做隐式类型转换，索引失效。
- 建了索引但统计信息过旧，优化器仍选全表扫描。
- 在大表上直接建索引，长时间锁表影响线上。""",
                "error_analysis": """`EXPLAIN QUERY PLAN` 显示 SCAN 但明明有索引
—— 常见三种原因：违反最左前缀、列上套了函数、条件类型不匹配（文本列传了数字）。

`sqlite3.OperationalError: index idx_x already exists`
—— 重复建索引。用 `CREATE INDEX IF NOT EXISTS`，或先查 `PRAGMA index_list`。

写入明显变慢
—— 索引过多。每张表的索引数量应控制在只为关键查询服务的范围内。

索引占空间比数据还大
—— 建了宽复合索引或对大文本列建索引。只索引真正用于过滤与排序的列。""",
                "beginner_practice": """1. 给 `tasks(user_id)` 建索引，用 EXPLAIN 确认 `WHERE user_id = ?` 命中。
2. 再建一个 `tasks(done, user_id)` 索引，对比 `WHERE user_id = ?` 是否还能命中，解释原因。""",
                "advanced_practice": """有一张 `orders(user_id, status, created_at)` 表，常见查询是
「某用户最近 30 天已支付订单按时间倒序」。请设计索引并说明为什么这样排序列，
再用 EXPLAIN 验证是否出现临时排序（`USE TEMP B-TREE`）。""",
                "quiz_note": "本节 6 道题：重点考最左前缀与「列上套函数导致索引失效」。",
                "summary": """索引是排序的辅助结构，把全表扫描变成快速定位；
复合索引遵循最左前缀，列上套函数通常失效；
索引不是越多越好，写入与存储都要付代价。""",
                "next_lesson": "下一节讲事务：怎么让「扣库存 + 记流水」要么都成功、要么都不发生。",
                "knowledge_points": [
                    {
                        "code": "python-database-04-01",
                        "name": "索引与执行计划",
                        "goal": "能设计复合索引，用执行计划验证命中，并说明索引的代价。",
                        "minutes": 35,
                        "criteria": "能针对一条真实查询设计索引，并用 EXPLAIN 证明有效。",
                        "requires": ["python-database-03-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-04-01-1",
                        "kp": 0,
                        "title": "验证索引命中",
                        "description": "给 tasks(user_id) 建索引并用 EXPLAIN 验证；再建 tasks(done, user_id)，检查 WHERE user_id = ? 是否命中。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks (user_id);
EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE user_id = 7;
-- SEARCH tasks USING INDEX idx_tasks_user (user_id=?)

CREATE INDEX IF NOT EXISTS idx_tasks_done_user ON tasks (done, user_id);
EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE user_id = 7;
-- 仍命中 idx_tasks_user；idx_tasks_done_user 因最左列是 done 而用不上''',
                        "explanation": "索引能否被使用取决于条件是否覆盖最左前缀，与索引是否存在无关。",
                    },
                    {
                        "code": "db-ex-04-01-2",
                        "kp": 0,
                        "title": "订单索引设计",
                        "description": "为 orders(user_id, status, created_at) 上「某用户近 30 天已支付订单按时间倒序」设计索引，并用 EXPLAIN 验证无临时排序。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''CREATE INDEX idx_orders_user_status_created
    ON orders (user_id, status, created_at DESC);

SELECT id FROM orders
WHERE user_id = ? AND status = 'paid' AND created_at >= ?
ORDER BY created_at DESC
LIMIT 20;''',
                        "explanation": "等值条件列在前、范围与排序列在后，索引顺序与查询顺序一致，才能同时用于过滤与排序，避免 USE TEMP B-TREE。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-04-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "复合索引 (user_id, done) 能有效支持下列哪个条件？",
                        "options": [
                            ("A", "WHERE done = 0"),
                            ("B", "WHERE user_id = 7"),
                            ("C", "WHERE lower(user_id) = '7'"),
                            ("D", "WHERE title LIKE '%报表%'"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "user_id 是最左列，单独用它可命中；只查 done 跳过最左列，用不上这个索引。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-04-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "索引会带来哪些代价？（多选）",
                        "options": [
                            ("A", "增删改时需要同步维护索引，写入变慢"),
                            ("B", "额外占用存储空间"),
                            ("C", "查询结果可能变得不正确"),
                            ("D", "索引过多会增加优化器选择成本"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "索引只影响性能，不会改变查询结果的正确性，所以 C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-04-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''已有索引 (user_id, done)，下面查询能用上它吗？
SELECT * FROM tasks WHERE done = 0 AND user_id = 7;''',
                        "answer": {
                            "reference": "能。虽然条件书写顺序相反，但优化器会识别出 user_id 与 done 都在索引里且覆盖最左前缀。",
                            "keywords": ["能", "最左前缀", "条件顺序无关"],
                        },
                        "explanation": "最左前缀说的是索引列的覆盖关系，不是 WHERE 中条件的书写顺序。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-04-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`WHERE substr(title, 1, 1) = '周'` 能利用 title 上的普通索引。",
                        "answer": {"value": False},
                        "explanation": "列被函数包裹后，索引按原值排序就失效了，只能全表扫描；可改用前缀匹配 `title LIKE '周%'`。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-04-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "给 tasks 表写一条索引，支持「按用户查未完成任务并按优先级排序」，并说明列顺序理由。",
                        "answer": {
                            "reference": '''CREATE INDEX idx_tasks_user_done_priority
    ON tasks (user_id, done, priority);''',
                            "keywords": ["user_id", "done", "priority", "顺序"],
                        },
                        "explanation": "两个等值过滤列在前、排序列在后，索引既能过滤又能支撑排序，省掉临时排序。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-04-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「给所有查询列都建索引」是错误的优化策略？",
                        "answer": {
                            "reference": "每个索引都要在写入时维护，索引越多，插入与更新的成本越高、占用空间越大；而且大量索引根本不会被优化器选中，属于纯负担。正确做法是按实际慢查询建索引，优先覆盖高频、选择性高的条件，并定期清理无用索引。",
                            "keywords": ["写放大", "无用索引", "按慢查询", "选择性"],
                        },
                        "explanation": "核心是「索引服务于查询，不是服务于列」，并能说出写放大这一代价。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    {
        "code": "python-database-05",
        "title": "事务",
        "description": "让一组写操作要么全成功、要么全回滚。",
        "order_index": 5,
        "lessons": [
            {
                "code": "python-database-05-lesson-01",
                "objectives": """1. 说清 ACID 四个特性的含义；
2. 会划定事务边界，知道提交与回滚的位置；
3. 理解隔离级别与并发写入的典型问题；
4. 会用唯一约束与重试实现幂等写入。""",
                "why_learn": """「扣库存 + 写订单」如果只成功一半，就会出现超卖或少单。
事务把多个写操作绑成一个整体，失败时回到起点，是数据正确性的最后一道防线。""",
                "concepts": """**原子性（A）**：要么全做、要么全不做。
**一致性（C）**：事务前后数据满足业务约束（如总额守恒）。
**隔离性（I）**：并发事务之间互不看到中间状态。
**持久性（D）**：提交后的数据即使断电也不丢。
**隔离级别** 从低到高：读未提交、读已提交、可重复读、串行化；级别越高并发越差。
**幻读** 指同一事务内两次查询行数不同；**不可重复读** 指同一行内容被别的事务改了。
**幂等写入**：同一请求执行多次结果一致，常用唯一约束 + 捕获冲突实现。""",
                "plain": """事务像转账：从 A 扣钱和给 B 加钱必须一起完成。
如果只扣不加，钱就凭空消失了。数据库用「要么全做、要么全不做」来避免这种半成品状态。
隔离级别则是「别人能看到你做到哪一步」的规定：看得越多并发越高，但越容易看到中间状态。""",
                "syntax": """```python
import sqlite3

conn = sqlite3.connect("app.db")
try:
    with conn:                      # 开始事务
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (100, 1))
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (100, 2))
except sqlite3.Error:
    ...                              # with 已自动回滚
```
要点：事务边界要短；不要在事务里做网络请求；显式捕获后要么重试、要么向上抛。""",
                "example_code": '''import sqlite3

conn = sqlite3.connect(":memory:")
conn.executescript(
    """
    CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance INTEGER NOT NULL);
    CREATE TABLE transfers (
        id INTEGER PRIMARY KEY,
        from_id INTEGER NOT NULL,
        to_id INTEGER NOT NULL,
        amount INTEGER NOT NULL CHECK (amount > 0)
    );
    INSERT INTO accounts (id, balance) VALUES (1, 500), (2, 100);
    """
)


def transfer(from_id, to_id, amount):
    with conn:
        row = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?", (from_id,)
        ).fetchone()
        if row is None:
            raise ValueError("账户不存在")
        if row[0] < amount:
            raise ValueError("余额不足")
        conn.execute(
            "UPDATE accounts SET balance = balance - ? WHERE id = ?",
            (amount, from_id),
        )
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            (amount, to_id),
        )
        conn.execute(
            "INSERT INTO transfers (from_id, to_id, amount) VALUES (?, ?, ?)",
            (from_id, to_id, amount),
        )


def balances():
    return [tuple(row) for row in conn.execute("SELECT id, balance FROM accounts")]


transfer(1, 2, 100)
print("转账后", balances())

try:
    transfer(1, 2, 9999)
except ValueError as exc:
    print("被拒绝：", exc)
print("失败后", balances())
print("流水条数", conn.execute("SELECT COUNT(*) FROM transfers").fetchone()[0])''',
                "code_lines": """1. `with conn:` 开启事务，块内所有写操作属于同一事务。
2. 先查余额再判断，把业务校验放在事务内部，避免「查完到写之间」被其他事务插队。
3. 两条 UPDATE 必须同属一个事务，否则可能出现扣了没加的半成品状态。
4. 插入流水与改余额同事务，保证「账实一致」。
5. `transfer(1, 2, 100)` 正常完成，余额变成 400 与 200。
6. 第二次金额超余额，抛 ValueError 后 with 自动回滚，余额不变。
7. 流水条数仍为 1，说明失败的事务没有留下任何痕迹。""",
                "output": """转账后 [(1, 400), (2, 200)]
被拒绝： 余额不足
失败后 [(1, 400), (2, 200)]
流水条数 1""",
                "mistakes": """- 事务里先查后写但没加锁，两个并发请求都通过余额校验，造成超扣。
- 把网络请求或文件读写放进事务，长时间占锁。
- 捕获异常后忘了回滚，连接上残留未提交状态。
- 用「先删后插」做更新却不放在同一事务，中途失败会丢数据。
- 依赖 `SELECT` 判断存在再插入，而不是用唯一约束，并发下会插入重复行。""",
                "error_analysis": """并发下余额被扣成负数
—— 典型的读-改-写竞态。解决：把判断与更新合成一条带条件的 UPDATE（`WHERE balance >= ?`），并检查受影响行数。

`sqlite3.IntegrityError: UNIQUE constraint failed`
—— 幂等写入时的正常信号。捕获它当作「已存在」，而不是当成致命错误。

事务结束后仍有未提交数据
—— 异常路径没走回滚。用 `with conn` 或显式 try/except + rollback。

`sqlite3.OperationalError: cannot start a transaction within a transaction`
—— 嵌套开启了事务。理顺边界，避免在已有事务里再 begin。""",
                "beginner_practice": """1. 实现「转账」并在余额不足时抛异常，验证余额不变、流水不增加。
2. 故意在两条 UPDATE 之间抛异常，确认第一条也被回滚。""",
                "advanced_practice": """把转账改成「条件更新 + 检查受影响行数」，避免先查后写的竞态；
再用两个线程各转 300 元（账户只有 500），验证最终只有一笔成功、余额不为负。""",
                "quiz_note": "本节 6 道题：重点考原子性与「先查后写」的竞态。",
                "summary": """事务保证一组写操作原子生效，失败回滚到起点；
隔离级别越高并发越差，读-改-写要用条件更新或锁避免竞态；
幂等写入靠唯一约束 + 冲突处理，而不是先查再插。""",
                "next_lesson": "下一节进入 SQLAlchemy 2.x：用 Engine 与 Core 表达式把 SQL 写进 Python。",
                "knowledge_points": [
                    {
                        "code": "python-database-05-01",
                        "name": "事务与 ACID",
                        "goal": "能划定事务边界，理解隔离级别，会用条件更新与唯一约束保证并发正确。",
                        "minutes": 40,
                        "criteria": "能写出带回滚的转账逻辑，并解释为什么先查后写会超扣。",
                        "requires": ["python-database-04-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-05-01-1",
                        "kp": 0,
                        "title": "带回滚的转账",
                        "description": "实现 transfer(from_id, to_id, amount)，余额不足抛异常，验证余额与流水都不变。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def transfer(from_id, to_id, amount):
    with conn:
        cursor = conn.execute(
            "UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?",
            (amount, from_id, amount),
        )
        if cursor.rowcount == 0:
            raise ValueError("余额不足或账户不存在")
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            (amount, to_id),
        )''',
                        "explanation": "把「余额是否足够」放进 UPDATE 的 WHERE，由数据库原子判断；rowcount 为 0 说明条件不成立。",
                    },
                    {
                        "code": "db-ex-05-01-2",
                        "kp": 0,
                        "title": "并发转账验证",
                        "description": "两个线程各转 300（账户余额 500），验证只有一笔成功、余额不为负。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''import threading


def worker():
    try:
        transfer(1, 2, 300)
    except ValueError as exc:
        print("失败：", exc)


threads = [threading.Thread(target=worker) for _ in range(2)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()

# 结果：一笔成功（余额 200），另一笔因条件更新影响 0 行而失败''',
                        "explanation": "条件更新把判断与写入合成一个原子操作，因此不会两个线程都通过校验。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-05-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "ACID 中的「原子性」指的是？",
                        "options": [
                            ("A", "事务内的操作要么全部生效，要么全部不生效"),
                            ("B", "数据必须永久保存"),
                            ("C", "事务之间互不干扰"),
                            ("D", "数据必须满足业务约束"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "原子性强调不可分割；B 是持久性、C 是隔离性、D 是一致性。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-05-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些做法能降低并发写入出错的可能？（多选）",
                        "options": [
                            ("A", "把条件写进 UPDATE 的 WHERE 并检查受影响行数"),
                            ("B", "用唯一约束拦截重复插入"),
                            ("C", "在事务里调用外部支付接口"),
                            ("D", "缩短事务范围，只在必要处持锁"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "在事务里做网络调用会拉长持锁时间，加剧冲突，所以 C 错。",
                        "difficulty": "advanced",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-05-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''这段代码有什么并发风险？
row = conn.execute("SELECT balance FROM accounts WHERE id = 1").fetchone()
if row[0] >= 300:
    conn.execute("UPDATE accounts SET balance = balance - 300 WHERE id = 1")''',
                        "answer": {
                            "reference": "典型的先查后写竞态：两个请求可能都读到 500 并通过判断，然后各自扣 300，余额变成 -100。应改成带条件的 UPDATE 并检查受影响行数。",
                            "keywords": ["竞态", "负余额", "条件更新", "rowcount"],
                        },
                        "explanation": "查询与更新之间没有原子性，其他事务可以插入修改；把判断下推到 UPDATE 才能原子生效。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-05-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "隔离级别越高，并发性能通常越差。",
                        "answer": {"value": True},
                        "explanation": "更高隔离需要更多锁或更严格的并发控制，代价是吞吐下降。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-05-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一段幂等插入：orders 表 order_no 唯一，重复插入时不报错、不产生重复行。",
                        "answer": {
                            "reference": '''conn.execute(
    "INSERT INTO orders (order_no, amount) VALUES (?, ?) "
    "ON CONFLICT(order_no) DO NOTHING",
    ("A20261108001", 100),
)''',
                            "keywords": ["ON CONFLICT", "DO NOTHING", "唯一约束"],
                        },
                        "explanation": "把幂等性交给唯一约束与冲突处理，比「先查再插」更可靠，也不受并发影响。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-05-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么不应该在事务里调用第三方支付接口？请说明两层后果。",
                        "answer": {
                            "reference": "一是持锁时间变长：网络耗时不可控，事务长时间不提交会阻塞其他写操作，甚至连锁超时；二是状态不一致：外部接口成功但本地事务回滚时，钱已经扣了而订单没落库。正确做法是先落本地状态（待支付），事务外调用外部接口，再用回调或对账补状态。",
                            "keywords": ["持锁", "阻塞", "外部成功本地回滚", "对账"],
                        },
                        "explanation": "能同时说清「性能」与「一致性」两层后果即可。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    {
        "code": "python-database-06",
        "title": "SQLAlchemy 2.x",
        "description": "从引擎与连接出发，用 Core 表达式构造 SQL。",
        "order_index": 6,
        "lessons": [
            {
                "code": "python-database-06-lesson-01",
                "objectives": """1. 会用 `create_engine` 创建引擎并理解连接池；
2. 会用 `text()` 执行原生 SQL、用 `select()` 构造表达式；
3. 会用 2.0 风格的 `insert/update/delete` 并正确传参；
4. 知道 Core 与 ORM 的分工边界。""",
                "why_learn": """手写 SQL 字符串在拼条件时容易注入，换数据库方言还要改语句。
SQLAlchemy 2.x 的 Core 用 Python 表达式构造 SQL，既能组合条件、又能参数化，还能跨方言。""",
                "concepts": """**Engine** 是数据库连接的工厂，内部维护**连接池**，应用全局创建一次即可。
**Connection** 是一次连接，`with engine.connect() as conn:` 保证归还。
**text()** 包裹原生 SQL，仍然支持绑定参数。
**Core 表达式**：`select()`、`insert()`、`update()`、`delete()` 构造可组合语句。
`Table` 与 `Column` 描述表结构，`metadata` 收集它们。
**Core vs ORM**：Core 面向表与行，ORM 面向对象；二者共用同一个 Engine。""",
                "plain": """Engine 像自来水厂，连接池像厂里常备的水管，你用水时借一根、用完还回去，
不用每次重新铺管道。Core 表达式像点菜：你说明要哪几样、什么条件，
由厨房（SQLAlchemy）翻译成对应数据库的方言，而不是自己背菜谱。""",
                "syntax": """```python
from sqlalchemy import create_engine, insert, select, text, update
from sqlalchemy import Column, Integer, MetaData, Table, Text

engine = create_engine("sqlite:///app.db", echo=False)
metadata = MetaData()
tasks = Table(
    "tasks", metadata,
    Column("id", Integer, primary_key=True),
    Column("title", Text, nullable=False),
    Column("done", Integer, nullable=False, default=0),
)

with engine.begin() as conn:      # 自动提交/回滚
    metadata.create_all(conn)
    conn.execute(insert(tasks).values(title="写周报", done=0))
    rows = conn.execute(select(tasks.c.id, tasks.c.title)).all()
```""",
                "example_code": '''from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    delete,
    func,
    insert,
    select,
    text,
    update,
)

engine = create_engine("sqlite://")
metadata = MetaData()
tasks = Table(
    "tasks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", Text, nullable=False),
    Column("done", Integer, nullable=False, default=0),
    Column("priority", Integer, nullable=False, default=3),
)

with engine.begin() as conn:
    metadata.create_all(conn)
    conn.execute(
        insert(tasks),
        [
            {"title": "写周报", "done": 0, "priority": 1},
            {"title": "交报表", "done": 1, "priority": 2},
            {"title": "订会议室", "done": 0, "priority": 3},
        ],
    )

stmt = (
    select(tasks.c.id, tasks.c.title)
    .where(tasks.c.done == 0)
    .order_by(tasks.c.priority)
)
with engine.connect() as conn:
    for row in conn.execute(stmt):
        print(tuple(row))

with engine.begin() as conn:
    conn.execute(
        update(tasks).where(tasks.c.title == "写周报").values(done=1)
    )
    conn.execute(delete(tasks).where(tasks.c.priority > 2))

print_stmt = select(func.count()).select_from(tasks)
with engine.connect() as conn:
    print("剩余", conn.execute(print_stmt).scalar_one())
    print("原生 SQL", conn.execute(text("SELECT COUNT(*) FROM tasks")).scalar_one())
    print("标题", conn.execute(select(tasks.c.title).where(tasks.c.id == 1)).scalar_one())''',
                "code_lines": """1. `create_engine("sqlite://")` 用内存库，同一引擎内共享同一份数据。
2. `Table(...)` 用 Python 描述表结构，`metadata` 收集所有表定义。
3. `engine.begin()` 是事务上下文，退出时自动提交，异常自动回滚。
4. `insert(tasks)` 配合字典列表批量插入，参数自动绑定，不存在注入问题。
5. `select(...).where(...).order_by(...)` 是可组合表达式，按需叠加条件。
6. `conn.execute(stmt)` 返回结果集，`tuple(row)` 便于打印。
7. `update(...).where(...).values(...)` 与手写 UPDATE 等价，但列名由对象约束，改名时能立刻发现。
8. `func.count()` 表达聚合函数，`scalar_one()` 取出唯一标量值。
9. 最后一行验证表达式可以继续叠加 where，链式写法保持可读。""",
                "output": """(1, '写周报')
(3, '订会议室')
剩余 2
原生 SQL 2
标题 写周报""",
                "mistakes": """- 每次请求都 `create_engine`，连接池被反复创建，性能极差。
- 用 f-string 把值拼进 `text()`，等于放弃参数化。
- 忘记 `engine.begin()` 提交，插入后查不到数据。
- 把 `select()` 结果直接当列表用，忘了它是可执行语句。
- 在 Core 里混用 ORM 对象，导致列类型对不上。""",
                "error_analysis": """`sqlalchemy.exc.ArgumentError: Textual SQL expression ... should be explicitly declared as text(...)`
—— 在 2.0 中直接传字符串已被禁止，必须用 `text("...")` 包裹。

`sqlalchemy.exc.ResourceClosedError: This result object is closed`
—— 在连接关闭后继续读结果。把 `fetchall()` 放在 with 块内完成。

`sqlalchemy.exc.OperationalError: no such table: tasks`
—— 忘了 `metadata.create_all(conn)`，或建表与查询用了不同引擎。

`TypeError: 'Select' object is not iterable`
—— 直接把 select() 当结果集。要先 `conn.execute(stmt)`。""",
                "beginner_practice": """1. 用 Core 建一张 `notes` 表，插入 3 条，再按 id 倒序查出来打印。
2. 用 `update()` 把某条标记完成，用 `func.count()` 统计未完成数量。""",
                "advanced_practice": """把一段手写 SQL 改写成 Core 表达式：
支持按关键字模糊查、按状态过滤、按优先级排序、分页；
要求条件可动态拼接（传 None 就跳过该条件），并说明为什么这样不会引入注入。""",
                "quiz_note": "本节 6 道题：重点考 2.0 的 `text()` 强制与 `engine.begin()` 的提交语义。",
                "summary": """Engine 是连接工厂，全局一个；连接用 with 管理；
Core 用 `select/insert/update/delete` 构造表达式，参数自动绑定；
2.0 里字符串 SQL 必须用 `text()` 包裹。""",
                "next_lesson": "下一节讲 ORM 模型：用类描述表，用关系表达外键，让查询返回对象。",
                "knowledge_points": [
                    {
                        "code": "python-database-06-01",
                        "name": "Engine 与 Core 表达式",
                        "goal": "能创建引擎、用 Core 构造增删改查，并理解事务与参数绑定。",
                        "minutes": 35,
                        "criteria": "能把一段手写 SQL 改写成 Core 表达式并正确提交。",
                        "requires": ["python-database-05-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-06-01-1",
                        "kp": 0,
                        "title": "Core 版增删改查",
                        "description": "用 Core 建 notes 表、插入 3 条、按 id 倒序查询、更新一条、统计未完成数。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''with engine.begin() as conn:
    notes = Table(
        "notes", metadata,
        Column("id", Integer, primary_key=True),
        Column("body", Text, nullable=False),
        Column("done", Integer, nullable=False, default=0),
    )
    metadata.create_all(conn)
    conn.execute(insert(notes), [{"body": "a"}, {"body": "b"}, {"body": "c"}])
    conn.execute(update(notes).where(notes.c.id == 2).values(done=1))

with engine.connect() as conn:
    rows = conn.execute(select(notes).order_by(notes.c.id.desc())).all()
    pending = conn.execute(
        select(func.count()).select_from(notes).where(notes.c.done == 0)
    ).scalar_one()''',
                        "explanation": "建表与插入放在 begin 块内一次提交；查询用 connect 即可，不产生写事务。",
                    },
                    {
                        "code": "db-ex-06-01-2",
                        "kp": 0,
                        "title": "动态条件查询",
                        "description": "实现 build_stmt(keyword=None, done=None, limit=10)：条件为 None 时跳过，结果按 priority 排序并分页。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def build_stmt(keyword=None, done=None, limit=10):
    stmt = select(tasks)
    if keyword:
        stmt = stmt.where(tasks.c.title.like(f"%{keyword}%"))
    if done is not None:
        stmt = stmt.where(tasks.c.done == done)
    return stmt.order_by(tasks.c.priority).limit(limit)''',
                        "explanation": "条件通过表达式叠加而不是拼字符串，值始终以绑定参数形式传给驱动，所以不存在注入。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-06-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "SQLAlchemy 2.0 中直接传入字符串 SQL 会怎样？",
                        "options": [
                            ("A", "正常执行"),
                            ("B", "抛出 ArgumentError，要求用 text() 包裹"),
                            ("C", "自动转换成 Core 表达式"),
                            ("D", "静默忽略"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "2.0 禁止隐式字符串 SQL，必须显式 `text()`，避免误把数据当语句执行。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-06-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 Engine，下列说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "内部维护连接池"),
                            ("B", "应在应用内全局创建一次并复用"),
                            ("C", "每次查询都应新建一个 Engine"),
                            ("D", "是创建数据库连接的工厂"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "反复创建 Engine 会不断新建连接池，性能与资源都会出问题，所以 C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-06-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''下面代码执行后能查到数据吗？
with engine.connect() as conn:
    conn.execute(insert(tasks).values(title="x"))''',
                        "answer": {
                            "reference": "查不到。connect() 不会自动提交，退出时事务回滚；要用 engine.begin() 或显式 commit。",
                            "keywords": ["未提交", "回滚", "begin"],
                        },
                        "explanation": "2.0 的连接默认处于事务中，必须显式提交；begin() 是最推荐的写法。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-06-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`select(tasks)` 本身是一个可执行语句对象，需要交给 `conn.execute()` 才会执行。",
                        "answer": {"value": True},
                        "explanation": "Core 表达式是惰性构造的语句对象，execute 时才编译成 SQL 并发送到数据库。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-06-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "用 Core 写一条查询：tasks 中未完成且 priority <= 2 的记录，只取 id 与 title，按 priority 升序。",
                        "answer": {
                            "reference": '''stmt = (
    select(tasks.c.id, tasks.c.title)
    .where(tasks.c.done == 0, tasks.c.priority <= 2)
    .order_by(tasks.c.priority)
)''',
                            "keywords": ["select", "where", "order_by"],
                        },
                        "explanation": "多个条件可以并列传给 where，等价于 AND；只选需要的列能减少数据传输。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-06-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "什么情况下你会选择 Core 而不是 ORM？请给出两个具体理由。",
                        "answer": {
                            "reference": "一是批量统计与报表类查询：只需要几列聚合结果，用 Core 直接表达更贴近 SQL、也更省对象开销；二是需要精确控制生成的 SQL（例如指定索引提示、复杂子查询）时，Core 比 ORM 更透明。反过来，涉及对象关系与业务实体的增删改，ORM 更省事。",
                            "keywords": ["聚合报表", "对象开销", "控制 SQL", "ORM 适合实体"],
                        },
                        "explanation": "核心区分是「面向行与集合」还是「面向对象与关系」。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
]
