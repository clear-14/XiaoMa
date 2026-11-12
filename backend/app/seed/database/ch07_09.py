"""数据库与 Python 数据库开发：第 7—9 章（ORM 模型、Session 与 CRUD、Alembic）。"""

CHAPTERS: list[dict] = [
    {
        "code": "python-database-07",
        "title": "ORM 模型",
        "description": "用声明式模型把表映射成类，用关系表达外键。",
        "order_index": 7,
        "lessons": [
            {
                "code": "python-database-07-lesson-01",
                "objectives": """1. 会用 `DeclarativeBase` 与 `Mapped` 定义 2.0 风格模型；
2. 会配置一对多关系与 `back_populates`；
3. 会用 `cascade` 控制级联行为；
4. 知道什么时候该用 `selectinload` 预加载。""",
                "why_learn": """用 Core 查出来的是一行行元组，业务代码还要自己拼字段。
ORM 把行映射成对象，`task.owner.email` 直接可读；
但关系配置错了会出现 N+1 查询或误删数据，这部分必须写对。""",
                "concepts": """**声明式基类**：`class Base(DeclarativeBase)`，所有模型继承它，`metadata` 自动收集。
`Mapped[T]` 声明属性类型，`mapped_column()` 补充列级设置（长度、唯一、外键、默认值）。
`Mapped[int | None]` 表示该列可为 NULL。
**关系**：`relationship()` 在对象层表达外键，`back_populates` 双向绑定。
**cascade** 决定父对象被删时子对象怎么处理，`"all, delete-orphan"` 会连带删除。
**N+1 问题**：循环里逐个访问关系属性，会为每个父对象再发一条查询。""",
                "plain": """ORM 像「翻译官」：数据库说的是行与列，业务代码说的是对象与属性，翻译官负责来回转换。
relationship 则像给对象之间牵了根线：拿到用户就能顺着线摸到他的任务，
但线拉得太随意（每条都现查），就会变成 N+1 那种一条一条问的低效场面。""",
                "syntax": """```python
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner: Mapped[User] = relationship(back_populates="tasks")
```""",
                "example_code": '''from sqlalchemy import ForeignKey, String, create_engine, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    selectinload,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email!r})"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    done: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    owner: Mapped[User] = relationship(back_populates="tasks")


engine = create_engine("sqlite://", echo=False)
Base.metadata.create_all(engine)

with Session(engine) as session:
    user = User(email="a@x.com")
    user.tasks.append(Task(title="写周报"))
    user.tasks.append(Task(title="交报表", done=True))
    session.add(user)
    session.commit()

with Session(engine) as session:
    loaded = session.scalars(select(User)).one()
    print("用户", loaded)
    print("任务数", len(loaded.tasks))
    print("标题", [task.title for task in loaded.tasks])

with Session(engine) as session:
    stmt = (
        select(User)
        .options(selectinload(User.tasks))
        .where(User.email == "a@x.com")
    )
    for item in session.scalars(stmt):
        print("预加载后", item.email, len(item.tasks))

print("表清单", sorted(Base.metadata.tables))''',
                "code_lines": """1. `class Base(DeclarativeBase)` 是 2.0 的声明式基类，取代旧的 declarative_base()。
2. `Mapped[int]` + `mapped_column(primary_key=True)` 声明主键，类型同时用于类型检查与建表。
3. `Mapped[list["Task"]]` 只声明「有多条任务」，不产生列，是纯对象层关系。
4. `back_populates="owner"` 与 Task.owner 双向对应，赋值一侧另一侧自动同步。
5. `cascade="all, delete-orphan"` 表示删除用户时任务一起删，从集合里移出也会删。
6. `user.tasks.append(...)` 通过关系直接建子对象，提交时自动补外键。
7. `selectinload(User.tasks)` 用一条额外查询批量加载所有任务，避免逐条查询。
8. `Base.metadata.tables` 可用来确认模型是否真的注册了表。""",
                "output": """用户 User(id=1, email='a@x.com')
任务数 2
标题 ['写周报', '交报表']
预加载后 a@x.com 2
表清单 ['tasks', 'users']""",
                "mistakes": """- `Mapped[int]` 却允许 NULL，插入时报 NOT NULL 失败；可空要写 `Mapped[int | None]`。
- `relationship` 两边都写 `back_populates` 但名字对不上，加载时报错。
- 忘记 `ForeignKey`，关系能建但表里没有约束。
- 在循环里访问关系属性导致 N+1，几百个用户发出几百条查询。
- 用 `cascade="all, delete"` 又手动删子对象，重复删除报错。""",
                "error_analysis": """`sqlalchemy.exc.InvalidRequestError: Mapper 'Mapper[User(tasks)]' has no property 'tasks'`
—— back_populates 指向的属性名写错，两侧必须完全对应。

`sqlalchemy.exc.IntegrityError: NOT NULL constraint failed: tasks.user_id`
—— 子对象没关联父对象就提交。要通过 `user.tasks.append(...)` 或在创建时传 `owner=user`。

`sqlalchemy.exc.MissingGreenlet` / 大量重复 SELECT
—— 典型 N+1。用 `selectinload()` 或 `joinedload()` 预加载。

`ArgumentError: Mapped[list[Task]] requires a relationship()`
—— 只写了 Mapped 注解却没配 relationship()。""",
                "beginner_practice": """1. 定义 `Note` 模型（id、body、done），建表并插入两条，用 select 查出来打印。
2. 给 Note 加上 `owner_id` 外键与 User 的一对多关系，验证从用户能取到全部笔记。""",
                "advanced_practice": """把 User 与 Tag 配成多对多（中间表 `user_tags`），
要求：删除用户时只清理关联行、标签本身保留；
再用 `selectinload` 预加载标签，并说明为什么不能用 `delete-orphan`。""",
                "quiz_note": "本节 6 道题：重点考 `Mapped[...| None]` 的可空语义与 cascade 的后果。",
                "summary": """2.0 用 `DeclarativeBase` + `Mapped` + `mapped_column` 定义模型；
relationship 表达对象关系，back_populates 双向绑定，cascade 控制连带操作；
关系属性在循环里访问要预加载，否则 N+1。""",
                "next_lesson": "下一节讲 Session：它到底是什么、什么时候提交、怎么避免脏数据和 N+1。",
                "knowledge_points": [
                    {
                        "code": "python-database-07-01",
                        "name": "声明式模型与关系映射",
                        "goal": "能用 2.0 风格定义模型与一对多关系，正确配置级联与预加载。",
                        "minutes": 40,
                        "criteria": "能写出两个关联模型并从父对象取到子集合，且不产生 N+1。",
                        "requires": ["python-database-06-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-07-01-1",
                        "kp": 0,
                        "title": "Note 模型与关系",
                        "description": "定义 Note 模型并加上 owner 关系，验证从 User 能取到全部笔记、删除 User 时笔记一并删除。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(String(200))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner: Mapped[User] = relationship(back_populates="notes")''',
                        "explanation": "子模型必须有 ForeignKey，父模型侧要新增 `notes` 关系并写 back_populates 与 cascade。",
                    },
                    {
                        "code": "db-ex-07-01-2",
                        "kp": 0,
                        "title": "多对多标签",
                        "description": "配置 User 与 Tag 的多对多关系，删除用户只清理关联行，并用 selectinload 预加载。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''user_tags = Table(
    "user_tags", Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    users: Mapped[list["User"]] = relationship(
        secondary=user_tags, back_populates="tags"
    )''',
                        "explanation": "多对多用 secondary 指向中间表；不能用 delete-orphan，否则删用户会把标签本身也删掉。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-07-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "在 SQLAlchemy 2.0 中，声明一个可空整数列的正确写法是？",
                        "options": [
                            ("A", "Mapped[int] = mapped_column(nullable=True)"),
                            ("B", "Mapped[int | None] = mapped_column()"),
                            ("C", "Mapped[Optional] = mapped_column()"),
                            ("D", "Mapped[int] = mapped_column(default=None)"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "2.0 用类型注解表达可空性；A 虽然能跑，但与注解矛盾，静态检查会报错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-07-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 relationship 的 cascade，说法正确的有哪些？（多选）",
                        "options": [
                            ("A", "delete-orphan 会在子对象被移出集合时删除它"),
                            ("B", "cascade 配置错误可能导致误删数据"),
                            ("C", "cascade 会自动创建外键约束"),
                            ("D", "多对多关系通常不适合用 delete-orphan"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "外键约束要显式写 ForeignKey，cascade 只管对象层行为，所以 C 错。",
                        "difficulty": "advanced",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-07-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''这段代码会执行多少条查询？
users = session.scalars(select(User)).all()
for user in users:
    print(user.email, len(user.tasks))''',
                        "answer": {
                            "reference": "1 条查用户 + 每个用户 1 条查任务，共 1+N 条，即 N+1 问题。",
                            "keywords": ["1+N", "N+1", "逐条查询"],
                        },
                        "explanation": "关系属性默认惰性加载，访问时才发查询；用 selectinload 可降到 2 条。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-07-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`Mapped[list[\"Task\"]]` 会在表里创建一列存放任务列表。",
                        "answer": {"value": False},
                        "explanation": "它只声明对象层关系，数据库里没有对应列；关联靠子表的 user_id 外键表达。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-07-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个 User 与 Task 的一对多配置：删除用户时任务一起删，双向可访问。",
                        "answer": {
                            "reference": '''class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner: Mapped[User] = relationship(back_populates="tasks")''',
                            "keywords": ["relationship", "back_populates", "cascade", "ForeignKey"],
                        },
                        "explanation": "两侧 back_populates 名字必须互相指向；cascade 写在父侧的关系上。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-07-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「在模板里遍历 user.tasks」很容易变成性能事故？说明触发条件与两种改法。",
                        "answer": {
                            "reference": "关系属性默认惰性加载，模板里每渲染一个用户就触发一次查询，页面上有 200 个用户就多 200 条 SQL。改法一是查询时用 selectinload 批量预加载；二是先做聚合查询只取需要的字段，避免加载整个对象图。",
                            "keywords": ["惰性加载", "每条一次", "selectinload", "聚合"],
                        },
                        "explanation": "核心是「访问时机决定了查询次数」，能给出预加载与聚合两种方案即可。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    {
        "code": "python-database-08",
        "title": "Session 与 CRUD",
        "description": "把 Session 当工作单元：控制边界、避免 N+1。",
        "order_index": 8,
        "lessons": [
            {
                "code": "python-database-08-lesson-01",
                "objectives": """1. 说清 Session 的职责与生命周期；
2. 会用 `add / flush / commit / rollback / refresh` 完成增删改查；
3. 理解「一个请求一个 Session」的边界；
4. 会用 `expire_on_commit` 与预加载避免脏读与 N+1。""",
                "why_learn": """Session 不是「数据库连接」的同义词，它是一个**工作单元**：
缓存对象、跟踪改动、在提交时统一写库。边界划错就会出现「改了没生效」或「提交后属性失效」。""",
                "concepts": """**Session** 是工作单元与身份映射：同一主键只对应一个对象实例。
`add()` 把对象放入待插入集合，`flush()` 立即发送 SQL 但不开事务结束，`commit()` 提交并结束事务。
`rollback()` 丢弃未提交改动；`refresh()` 从库里重新读取对象。
`expire_on_commit=True`（默认）提交后对象属性过期，下次访问会重新查询。
**一个请求一个 Session**：请求开始创建、结束关闭，事务边界与业务用例对齐。""",
                "plain": """Session 像一张购物车：你把要买的东西放进去（add），中途可以看看总价（flush），
结账才算真正成交（commit）。如果发现拿错了，清空购物车（rollback）。
结账后商品信息就「过期」了——想知道最新状态得再查一次（refresh）。""",
                "syntax": """```python
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

with SessionLocal() as session:
    task = Task(title="写周报")
    session.add(task)
    session.commit()
    session.refresh(task)
    task.done = True
    session.commit()
```
注意：`with SessionLocal() as session` 退出时关闭会话但**不会**自动提交，提交要显式写。""",
                "example_code": '''from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    done: Mapped[bool] = mapped_column(default=False)


engine = create_engine("sqlite://", echo=False)
Base.metadata.create_all(engine)

with Session(engine, expire_on_commit=False) as session:
    first = Task(title="写周报")
    second = Task(title="交报表")
    session.add_all([first, second])
    session.flush()
    print("flush 后已有 id", first.id, second.id)

    session.commit()
    print("commit 后仍可读", first.title)

    first.done = True
    session.commit()

    same = session.get(Task, first.id)
    print("身份映射同一对象", same is first)

    loaded = session.scalars(select(Task).order_by(Task.id)).all()
    print("列表", [(task.title, task.done) for task in loaded])

    session.delete(second)
    session.commit()
    print("删除后数量", len(session.scalars(select(Task)).all()))

with Session(engine) as session:
    try:
        session.add(Task(title="会被回滚"))
        raise RuntimeError("业务失败")
    except RuntimeError as exc:
        session.rollback()
        print("已回滚：", exc)
    print("最终数量", len(session.scalars(select(Task)).all()))''',
                "code_lines": """1. `expire_on_commit=False` 让提交后对象仍可读，适合接口层直接返回对象。
2. `add_all` 一次加入多个待插入对象，减少调用次数。
3. `flush()` 立即发送 INSERT 拿到自增 id，但事务还没结束，可继续修改。
4. `commit()` 提交事务；默认会过期对象属性，禁用后可直接读 `first.title`。
5. `session.get(Task, id)` 优先走身份映射缓存，返回的是同一个对象实例。
6. `select(Task)` 返回实体对象列表，而不是元组。
7. `session.delete(second)` 标记删除，提交后才真正执行 DELETE。
8. 最后一个会话演示异常时必须显式 rollback，否则连接上残留未提交状态。""",
                "output": """flush 后已有 id 1 2
commit 后仍可读 写周报
身份映射同一对象 True
列表 [('写周报', True), ('交报表', False)]
删除后数量 1
已回滚： 业务失败
最终数量 1""",
                "mistakes": """- 只 `flush()` 不 `commit()`，请求结束会话关闭，改动丢失。
- 用全局单例 Session 跨请求共享，出现串数据与线程安全问题。
- `commit()` 后继续读对象属性，默认过期触发额外查询（或 DetachedInstanceError）。
- 异常时只捕获不回滚，后续操作在脏事务上继续执行。
- 在循环里对每条记录单独 commit，事务次数暴涨。""",
                "error_analysis": """`sqlalchemy.orm.exc.DetachedInstanceError: Instance is not bound to a Session`
—— 会话已关闭还访问未加载的属性。在会话内完成访问，或用 `expire_on_commit=False` 并确保属性已加载。

改动没生效
—— 忘了 commit，或 commit 之后又改了对象但没再提交。

`InvalidRequestError: Object is already attached to session`
—— 同一对象被两个会话管理。用 `session.merge()` 合并到当前会话。

提交后属性变旧值
—— 提交后被其他事务修改，需要 `refresh()` 重新读取。""",
                "beginner_practice": """1. 写 `create_task(session, title)`，add 后 commit 并返回对象，验证 id 已生成。
2. 写 `mark_done(session, task_id)`，用 `session.get` 取出后改字段并提交。""",
                "advanced_practice": """实现一个 `unit_of_work` 上下文管理器：
进入时创建 Session，正常退出提交、异常回滚并关闭；
再写一个「批量导入 1000 条任务」的用例，要求只 commit 一次并统计耗时。""",
                "quiz_note": "本节 6 道题：重点考 flush 与 commit 的区别、以及异常必须回滚。",
                "summary": """Session 是工作单元：add 入队、flush 发 SQL、commit 提交、rollback 丢弃；
一个请求一个 Session，边界与用例对齐；
提交后对象可能过期，需要 refresh 或 expire_on_commit=False。""",
                "next_lesson": "下一节讲 Alembic：表结构改了，线上数据怎么安全迁移。",
                "knowledge_points": [
                    {
                        "code": "python-database-08-01",
                        "name": "Session 生命周期与 CRUD",
                        "goal": "能正确管理会话与事务边界，完成增删改查并避免失效对象与 N+1。",
                        "minutes": 45,
                        "criteria": "能写出「一个用例一个会话」的 CRUD 函数，并说明 flush 与 commit 的差异。",
                        "requires": ["python-database-07-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-08-01-1",
                        "kp": 0,
                        "title": "CRUD 函数集",
                        "description": "写 create_task、mark_done、delete_task、list_pending 四个函数，每个函数内管理自己的会话。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def create_task(title: str) -> int:
    with Session(engine, expire_on_commit=False) as session:
        task = Task(title=title)
        session.add(task)
        session.commit()
        return task.id


def mark_done(task_id: int) -> None:
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if task is None:
            raise ValueError("任务不存在")
        task.done = True
        session.commit()


def list_pending() -> list[str]:
    with Session(engine) as session:
        rows = session.scalars(select(Task).where(Task.done.is_(False)))
        return [task.title for task in rows]''',
                        "explanation": "每个函数一个会话，边界清晰；返回 id 而不是对象，避免把会话内的对象带出作用域。",
                    },
                    {
                        "code": "db-ex-08-01-2",
                        "kp": 0,
                        "title": "工作单元上下文",
                        "description": "实现 unit_of_work 上下文管理器（正常提交、异常回滚），并用它批量导入 1000 条任务，只提交一次。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''from contextlib import contextmanager


@contextmanager
def unit_of_work():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


with unit_of_work() as session:
    session.add_all([Task(title=f"任务{i}") for i in range(1000)])''',
                        "explanation": "批量插入只提交一次，事务短且只有一次刷盘；异常路径回滚并用 raise 保留原始堆栈。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-08-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`session.flush()` 与 `session.commit()` 的关键区别是？",
                        "options": [
                            ("A", "flush 完全等同于 commit"),
                            ("B", "flush 发送 SQL 但事务未结束，commit 提交并结束事务"),
                            ("C", "flush 只在内存中标记，不发 SQL"),
                            ("D", "commit 之后才能 flush"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "flush 用于拿到自增 id 或触发约束检查，事务仍可回滚；commit 才是最终提交。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-08-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 Session 的生命周期，正确做法有哪些？（多选）",
                        "options": [
                            ("A", "一个请求/用例一个 Session"),
                            ("B", "异常时显式 rollback"),
                            ("C", "用全局单例 Session 供所有请求共享"),
                            ("D", "会话用完后关闭"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "全局单例会导致请求间串数据与并发问题，所以 C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-08-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''这段代码哪里有问题？
task = Task(title="x")
session.add(task)
session.flush()
return task''',
                        "answer": {
                            "reference": "没有 commit，会话关闭后改动被回滚，任务不会真正写入；而且返回的对象在会话关闭后处于 detached 状态，访问未加载属性会报错。",
                            "keywords": ["未提交", "回滚", "detached"],
                        },
                        "explanation": "flush 只发 SQL 不提交；返回 ORM 对象还存在会话绑定问题，通常应返回 id 或 DTO。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-08-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`with SessionLocal() as session:` 退出时会自动 commit。",
                        "answer": {"value": False},
                        "explanation": "它只在退出时关闭会话，不会自动提交；需要显式 commit 或自己封装的上下文管理器。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-08-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一段代码：取出 id 为 1 的任务，把它标记完成并提交；任务不存在时抛 ValueError。",
                        "answer": {
                            "reference": '''with Session(engine) as session:
    task = session.get(Task, 1)
    if task is None:
        raise ValueError("任务不存在")
    task.done = True
    session.commit()''',
                            "keywords": ["session.get", "commit", "ValueError"],
                        },
                        "explanation": "ORM 的改动会被会话跟踪，改属性后 commit 即生成 UPDATE。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-08-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「每条记录单独 commit」在批量导入时不可取？给出你会的替代方案。",
                        "answer": {
                            "reference": "每次 commit 都是一次事务提交与磁盘同步，1000 条就是 1000 次刷盘，耗时随条数线性增长，还可能长时间占用写锁。替代方案是整批放在一个事务里，用 add_all 批量加入、只 commit 一次；数据量特别大时分批提交（例如每 500 条一次），并在失败时记录断点以便重跑。",
                            "keywords": ["刷盘", "事务次数", "add_all", "分批"],
                        },
                        "explanation": "核心是「事务次数决定开销」，并给出批量或分批的可行替代。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
    {
        "code": "python-database-09",
        "title": "Alembic 迁移",
        "description": "让表结构随代码演进，可回滚、可复现。",
        "order_index": 9,
        "lessons": [
            {
                "code": "python-database-09-lesson-01",
                "objectives": """1. 理解 revision 与 down_revision 组成的版本链；
2. 会初始化 Alembic 并生成第一个迁移；
3. 会用 autogenerate 起草并逐条人工校对；
4. 会写可回滚的数据迁移，知道 SQLite 改列要用 batch 模式。""",
                "why_learn": """手动改线上表结构，最怕三件事：忘了在别的环境执行、执行错了没法回退、
改了列类型把数据截断。迁移把结构变更变成可版本管理、可回滚的代码。""",
                "concepts": """**版本链**：每个迁移文件有 `revision`（自己）与 `down_revision`（上一个），构成单向链条。
`alembic upgrade head` 沿链向前，`downgrade -1` 回退一步。
**autogenerate** 对比模型与数据库差异，生成草稿——它只是草稿，必须人工核对。
SQLite 不支持大部分 `ALTER COLUMN`，要用 `op.batch_alter_table()` 重建表。
**数据迁移** 用 `op.execute()` 或 `op.get_bind()` 执行 DML，常用于回填与清洗。
迁移必须可循环：`upgrade` 后能 `downgrade` 回原状。""",
                "plain": """迁移像数据库的「版本历史」：每一版记录「从上一版改了什么」，可以前进也可以回退。
autogenerate 像自动生成的草稿：能省打字，但它不知道你的数据长什么样，
所以逐条核对（默认值、索引、可空性）这一步不能省。""",
                "syntax": """```bash
alembic init alembic
alembic revision --autogenerate -m "add task priority"
alembic upgrade head
alembic downgrade -1
alembic current
alembic history
```
```python
# 迁移文件
def upgrade() -> None:
    op.add_column("tasks", sa.Column("priority", sa.Integer(), nullable=False, server_default="3"))


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("priority")
```""",
                "example_code": '''# 演示版本链与变更脚本的结构（伪代码式说明，不连真实库）
MIGRATIONS = [
    {
        "revision": "a1b2c3d4e5f6",
        "down_revision": None,
        "title": "创建 tasks 表",
        "upgrade": ["CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)"],
        "downgrade": ["DROP TABLE tasks"],
    },
    {
        "revision": "b2c3d4e5f6a7",
        "down_revision": "a1b2c3d4e5f6",
        "title": "新增 priority 列",
        "upgrade": [
            "ALTER TABLE tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 3",
        ],
        "downgrade": ["ALTER TABLE tasks DROP COLUMN priority"],
    },
    {
        "revision": "c3d4e5f6a7b8",
        "down_revision": "b2c3d4e5f6a7",
        "title": "回填 priority 为 5 的历史数据",
        "upgrade": ["UPDATE tasks SET priority = 5 WHERE priority = 3"],
        "downgrade": ["UPDATE tasks SET priority = 3 WHERE priority = 5"],
    },
]


def chain(migration_list):
    by_revision = {item["revision"]: item for item in migration_list}
    current = None
    order = []
    while True:
        next_item = next(
            (item for item in migration_list if item["down_revision"] == current),
            None,
        )
        if next_item is None:
            break
        order.append(next_item)
        current = next_item["revision"]
    known = set(by_revision)
    orphans = [item["revision"] for item in migration_list if item["revision"] not in order and item["down_revision"] not in known and item["down_revision"] is not None]
    return order, orphans


order, orphans = chain(MIGRATIONS)
for index, item in enumerate(order, start=1):
    print(index, item["revision"], "<-", item["down_revision"], item["title"])

print("孤立迁移", orphans)
print("head", order[-1]["revision"])
print("回退一步", order[-2]["revision"])

for item in reversed(order):
    print("downgrade 顺序", item["revision"])''',
                "code_lines": """1. `MIGRATIONS` 用数据模拟三个迁移文件，`down_revision` 指向上一版，None 表示第一版。
2. `chain` 从 None 出发，不断找「down_revision 等于当前 revision」的项，得到线性顺序。
3. 这个查找正是 Alembic 解析 `upgrade head` 的方式：顺着链一路往前。
4. 回填数据的迁移（第三条）也有 downgrade，把值改回去，保证可循环。
5. `orphans` 检测 down_revision 指向不存在版本的迁移，这类错误会让链断裂。
6. 打印 head 即最新版本；回退一步就是链上的前一个 revision。
7. 最后的 `reversed(order)` 说明 downgrade 必须逆序执行，顺序错了就会报「依赖未回退」。""",
                "output": """1 a1b2c3d4e5f6 <- None 创建 tasks 表
2 b2c3d4e5f6a7 <- a1b2c3d4e5f6 新增 priority 列
3 c3d4e5f6a7b8 <- b2c3d4e5f6a7 回填 priority 为 5 的历史数据
孤立迁移 []
head c3d4e5f6a7b8
回退一步 b2c3d4e5f6a7
downgrade 顺序 c3d4e5f6a7b8
downgrade 顺序 b2c3d4e5f6a7
downgrade 顺序 a1b2c3d4e5f6""",
                "mistakes": """- 直接用 autogenerate 的结果上线，不看默认值与索引差异。
- 给已有数据的表加 `nullable=False` 列却不给 `server_default`，迁移直接失败。
- SQLite 上直接 `op.alter_column`，报不支持。
- 迁移里写了 downgrade 但没测试，回退时才发现报错。
- 两个分支同时生成迁移，出现两个 down_revision 指向同一版本，形成分叉。""",
                "error_analysis": """`sqlalchemy.exc.OperationalError: Cannot add a NOT NULL column with default value NULL`
—— 给已有数据的表加非空列但没给默认值。加 `server_default`，或先加可空列再回填再改非空。

`alembic.util.exc.CommandError: Can't locate revision identified by 'xxx'`
—— 数据库里的版本号在代码中找不到，通常是别人删了迁移文件。恢复文件或手工修正版本表。

`sqlite3.OperationalError: near "ALTER": syntax error`
—— SQLite 不支持该 ALTER 语法。用 `op.batch_alter_table()` 重建表。

`Target database is not up to date`
—— 当前库落后于代码。先 `alembic upgrade head` 再生成新迁移。""",
                "beginner_practice": """1. 在临时项目里 `alembic init`，配置 sqlite 连接，生成并执行第一个迁移。
2. 加一列后用 autogenerate 生成迁移，逐条核对生成的内容，再执行 downgrade 验证可回退。""",
                "advanced_practice": """写一个「拆分字段」的迁移：把 `tasks.title` 拆成 `title` 与 `subtitle`，
要求：先加列、回填数据、再删除旧列，全程可 downgrade，并在 SQLite 上跑通 upgrade/downgrade 循环。""",
                "quiz_note": "本节 6 道题：重点考 autogenerate 只是草稿、以及 SQLite 的 batch 模式。",
                "summary": """迁移是版本链：revision 指向自己、down_revision 指向上一版；
autogenerate 只起草，默认值与索引必须人工核对；
SQLite 改列用 batch_alter_table；迁移要能 upgrade/downgrade 循环。""",
                "next_lesson": "本课程到此结束。接下来进入 FastAPI 后端开发，把这些能力组合成一个可上线的接口服务。",
                "knowledge_points": [
                    {
                        "code": "python-database-09-01",
                        "name": "Alembic 版本链与迁移",
                        "goal": "能初始化 Alembic、生成并校对迁移，写出可回滚的数据迁移。",
                        "minutes": 40,
                        "criteria": "能独立完成一次含数据回填的迁移，并验证 upgrade/downgrade 循环成功。",
                        "requires": ["python-database-08-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "db-ex-09-01-1",
                        "kp": 0,
                        "title": "第一个迁移",
                        "description": "初始化 Alembic 指向 sqlite 库，生成创建 tasks 表的迁移并执行，再用 downgrade 回退。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''alembic init alembic
# alembic/env.py 中设置 target_metadata = Base.metadata，并配置 sqlalchemy.url
alembic revision --autogenerate -m "create tasks"
alembic upgrade head
alembic downgrade -1
alembic current''',
                        "explanation": "env.py 必须指向模型的 metadata，否则 autogenerate 认为「没有任何表」。",
                    },
                    {
                        "code": "db-ex-09-01-2",
                        "kp": 0,
                        "title": "拆分字段迁移",
                        "description": "把 title 拆成 title 与 subtitle：加列、回填、删旧列，全程可回退，并在 SQLite 上验证循环。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("subtitle", sa.String(120), nullable=True))
    op.execute("UPDATE tasks SET subtitle = '' WHERE subtitle IS NULL")
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("subtitle", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("subtitle")''',
                        "explanation": "先加可空列、回填、再收紧为 NOT NULL，是给已有数据加非空列的标准三步。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-db-09-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "迁移文件里的 down_revision 表示？",
                        "options": [
                            ("A", "下一个要执行的版本"),
                            ("B", "上一个版本的 revision，用于串成版本链"),
                            ("C", "数据库连接字符串"),
                            ("D", "回滚脚本的文件名"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "down_revision 指向前一个迁移，Alembic 依此排序执行；第一版为 None。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-09-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "为什么 autogenerate 的结果必须人工校对？（多选）",
                        "options": [
                            ("A", "它可能漏掉默认值或服务端默认值"),
                            ("B", "它无法判断数据迁移是否需要回填"),
                            ("C", "它一定会生成错误的 SQL"),
                            ("D", "索引与约束的差异需要人工判断是否合理"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "autogenerate 大多数情况是正确的，但无法理解业务意图，所以 C 太绝对。",
                        "difficulty": "advanced",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-db-09-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": '''这条迁移在已有数据的表上会怎样？
op.add_column("tasks", sa.Column("priority", sa.Integer(), nullable=False))''',
                        "answer": {
                            "reference": "会失败：已有行没有值可填，不能加非空列。需要给 server_default，或先加可空列再回填。",
                            "keywords": ["失败", "server_default", "回填"],
                        },
                        "explanation": "非空约束要求每行都有值，历史数据缺值时必须提供默认值或分步处理。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-09-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "在 SQLite 上修改列类型应使用 `op.batch_alter_table()`。",
                        "answer": {"value": True},
                        "explanation": "SQLite 缺少 ALTER COLUMN，batch 模式通过建新表、拷数据、换名来模拟。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-db-09-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "写一个迁移的 upgrade/downgrade：给 users 加 created_at 列并回填当前时间。",
                        "answer": {
                            "reference": '''def upgrade() -> None:
    op.add_column("users", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    with op.batch_alter_table("users") as batch:
        batch.alter_column("created_at", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("created_at")''',
                            "keywords": ["add_column", "op.execute", "batch_alter_table", "drop_column"],
                        },
                        "explanation": "加可空列 → 回填 → 收紧非空，三步顺序不能颠倒；downgrade 只需删列。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-db-09-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "团队里两个人同时基于同一版本生成了迁移，会出什么问题？怎么避免？",
                        "answer": {
                            "reference": "两个迁移的 down_revision 都指向同一个版本，形成分叉，Alembic 无法确定执行顺序，upgrade head 会报「多个 head」。避免方式：合并前先拉最新代码并 rebase 自己的迁移；或明确约定同一时间只有一个人生成迁移，其他人只写代码、由发布人统一生成。",
                            "keywords": ["分叉", "多个 head", "merge", "约定"],
                        },
                        "explanation": "核心是「版本链只能单线向前」，并给出 rebase 或统一生成的协作约定。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            }
        ],
    },
]
