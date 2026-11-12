"""FastAPI 后端开发：第 11—12 章（SQLAlchemy 数据库集成、用户认证与 JWT）。"""

CHAPTERS: list[dict] = [
    {
        "code": "fastapi-backend-11",
        "title": "SQLAlchemy 数据库集成",
        "description": "把数据库会话接进接口，接口层不写 SQL。",
        "order_index": 11,
        "lessons": [
            {
                "code": "fastapi-backend-11-lesson-01",
                "objectives": """1. 能配置引擎与会话工厂（SQLAlchemy 2.0 写法）；
2. 会用 `yield` 依赖按请求提供会话并确保关闭；
3. 会用 `select()` 与 `session.scalars()` 查询数据；
4. 知道连接池与会话生命周期对并发的影响。""",
                "why_learn": """接口要读数据，就不能每次请求都自己 `connect()`、忘了 `close()`。
会话做成依赖后，「打开—使用—关闭」由框架保证，接口只关心查询；连接池则让并发请求复用连接而不是一直新建。""",
                "concepts": """**Engine**：连接池 + 方言，进程内只创建一次。
**Session**：一次请求内的工作单元，负责身份映射与事务。
**SessionLocal**：会话工厂，`sessionmaker(bind=engine)`。
**依赖注入会话**：`yield` 前创建、`finally` 关闭，异常路径也释放。
**2.0 查询**：`session.scalars(select(Task)).all()`，不用 `session.query()`。""",
                "plain": """引擎像自来水厂：整个小区只建一座，不可能每家每户自己打井。
会话像每次用水时打开的水龙头：用完就关，不关就会一直占着管道（连接）。
连接池是水厂的蓄水池：水龙头开得再频繁，也不用每次重新抽水。""",
                "syntax": """**API 说明**

```python
engine = create_engine("sqlite+pysqlite:///./app.db", echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- `create_engine` 在模块级创建，不要每次请求新建。
- SQLite 默认单文件，多线程需 `connect_args={"check_same_thread": False}`。
- 会话依赖用 `Iterator[Session]` 标注，FastAPI 才认识 `yield`。""",
                "example_code": '''from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50))
    done: Mapped[bool] = mapped_column(default=False)


engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)

with SessionLocal() as seed:
    seed.add_all([Task(title="写周报"), Task(title="交报表", done=True)])
    seed.commit()

app = FastAPI(title="数据库集成示例")


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.get("/tasks")
def list_tasks(session: Annotated[Session, Depends(get_session)]) -> list[dict]:
    rows = session.scalars(select(Task).order_by(Task.id)).all()
    return [{"id": row.id, "title": row.title, "done": row.done} for row in rows]''',
                "code_lines": """1. `DeclarativeBase` 是 2.0 的声明式基类，替代 1.x 的 `declarative_base()`。
2. `Mapped[int]` + `mapped_column()` 同时提供类型注解与列定义。
3. `create_engine` 在模块级创建，进程内复用连接池。
4. `sessionmaker(...)` 生成工厂；`expire_on_commit=False` 让提交后仍可读对象属性。
5. `get_session` 用 `yield` 提供会话，`finally` 保证关闭——异常也不会漏。
6. 接口签名 `Annotated[Session, Depends(get_session)]` 声明「我需要一个会话」。
7. `session.scalars(select(Task))` 是 2.0 查询写法，返回模型对象而非 Row。
8. 退出 `with` 块时 `seed` 会话自动关闭，避免残留连接。""",
                "output": """curl http://127.0.0.1:8000/tasks
[{"id":1,"title":"写周报","done":false},{"id":2,"title":"交报表","done":true}]

# 若把 engine 换成文件库，/docs 与接口行为一致
# sqlite+pysqlite:///./app.db

# 常见错误：会话未关闭
# 并发压测时出现 "sqlite3.OperationalError: database is locked\"""",
                "mistakes": """- 每次请求 `create_engine`，连接池不断重建，性能急剧下降。
- 会话依赖里 `yield` 了却没有 `finally: session.close()`，连接泄漏。
- 在多线程下直接用 SQLite 默认配置，报 `check_same_thread` 错误。
- 用 `session.query()`（1.x 写法），与教程/团队规范不一致。
- 把模型对象直接返回，`response_model` 没声明，导致内部字段泄漏或懒加载异常。""",
                "error_analysis": """`sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`
—— 跨线程使用连接。SQLite 需 `connect_args={"check_same_thread": False}`，或每请求新建会话。

`sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached`
—— 会话没关闭，连接池耗尽。检查依赖是否在 `finally` 里 close。

`DetachedInstanceError: Instance is not bound to a Session`
—— 会话已关闭还访问未加载属性。要么在会话内转成字典，要么设 `expire_on_commit=False` 并提前加载。""",
                "beginner_practice": """1. 把内存库换成文件库 `app.db`，重启服务后确认数据仍在。
2. 新增 `GET /tasks/{task_id}`，用 `session.get(Task, task_id)` 查询，找不到返回 404。""",
                "advanced_practice": """比较三种会话策略：每请求一个会话、全局单会话、每操作一个会话。
分别说明在并发、事务边界、连接占用上的差异，并给出你的选择。""",
                "quiz_note": "本节 6 道题：2 道基础理解（Engine 与 Session 分工、依赖关闭时机）+ 2 道代码阅读（读 2.0 查询、读连接池报错）+ 2 道应用练习（补查询、改配置）。",
                "summary": """引擎进程内只建一次，会话按请求创建与关闭。
`yield` 依赖负责「打开—使用—关闭」，异常路径也要走 `finally`。
2.0 写法用 `select()` 与 `session.scalars()`，不用 `session.query()`。""",
                "next_lesson": "下一节划定事务边界：什么该在依赖里提交，什么必须在服务层控制。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-11-01",
                        "name": "引擎、会话与 Session 依赖",
                        "goal": "能配置引擎与会话工厂，并通过依赖按请求提供会话。",
                        "minutes": 45,
                        "criteria": "能写出带 close 保证的会话依赖，并用 2.0 语法完成一次查询。",
                        "requires": ["fastapi-backend-10-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-11-01-1",
                        "kp": 0,
                        "title": "按 ID 查任务",
                        "description": "写 `GET /tasks/{task_id}`：用 `session.get(Task, task_id)` 查询，找不到返回 404 与统一错误结构。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''@app.get("/tasks/{task_id}")
def get_task(task_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"id": task.id, "title": task.title, "done": task.done}''',
                        "explanation": "`session.get` 按主键查询，比 `select` 更直接；返回字典而不是 ORM 对象，避免会话关闭后的懒加载问题。",
                    },
                    {
                        "code": "fa-ex-11-01-2",
                        "kp": 0,
                        "title": "会话泄漏排查",
                        "description": "压测时报 `QueuePool limit ... reached`，列出三条可能原因与对应的检查方法。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''① 会话依赖未关闭：检查 finally 是否有 close；
② 接口里长时间持会话做外部调用：把外部调用移出会话范围；
③ 连接池过小或长事务未提交：看是否有未 commit 的事务、调整 pool_size 并加超时监控。''',
                        "explanation": "连接池耗尽几乎都是「借了没还」或「借太久」，排查顺序应从依赖实现开始。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-11-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`create_engine` 应该在哪里调用？",
                        "options": [
                            ("A", "模块级创建一次，进程内复用"),
                            ("B", "每个请求调用一次"),
                            ("C", "每个接口函数内调用"),
                            ("D", "每次查询调用一次"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "引擎内部维护连接池，频繁创建会让池失去意义，性能急剧下降。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-11-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "会话依赖的正确写法应包含？（多选）",
                        "options": [
                            ("A", "yield 提供会话"),
                            ("B", "finally 中 close"),
                            ("C", "返回类型标注 Iterator[Session]"),
                            ("D", "在依赖里调用 create_all"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "建表属于初始化工作，不应放在每次请求的依赖里。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-11-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "`session.scalars(select(Task)).all()` 返回的是什么？",
                        "options": [
                            ("A", "Task 模型对象列表"),
                            ("B", "字典列表"),
                            ("C", "Row 元组列表"),
                            ("D", "主键列表"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`scalars()` 取每行的第一列（即实体对象），因此得到模型对象列表。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-11-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "会话在依赖的 `finally` 中关闭后，仍可安全访问未加载的懒加载属性。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "会话关闭后对象处于游离状态，访问未加载属性会抛 `DetachedInstanceError`。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-11-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全会话依赖的清理逻辑。横线处应填什么？\n\n```python\ndef get_session() -> Iterator[Session]:\n    session = SessionLocal()\n    try:\n        yield session\n    ____:\n        session.close()\n```",
                        "options": [
                            ("A", "finally"),
                            ("B", "except"),
                            ("C", "else"),
                            ("D", "except Exception"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "只有 `finally` 能在正常与异常路径上都执行关闭；`else` 只在无异常时执行。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-11-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么接口返回 ORM 对象前通常要转成字典或使用 `response_model`？",
                        "answer": {"value": "① 会话关闭后 ORM 对象处于游离状态，访问未加载属性会报错；② 直接序列化会把全部列（含内部字段）暴露出去；③ 模型带关系属性时可能触发额外查询（N+1）。转成字典或声明 `response_model` 能固定输出结构、避免泄漏与意外查询。"},
                        "explanation": "三点分别是「游离态」「字段泄漏」「N+1」，都是真实会踩的坑。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-11-lesson-02",
                "objectives": """1. 能划定事务边界：依赖级提交与显式事务各适合什么场景；
2. 会写仓储层（Repository）把查询与接口解耦；
3. 能处理「半成功写入」并给出回滚策略；
4. 知道为什么接口层不该出现 SQL 字符串。""",
                "why_learn": """一次请求里改三张表，第二张失败时前一张已经提交——数据就脏了。
把事务边界划清楚，比事后补数据便宜得多；而把 SQL 散落在接口里，则会让复用与测试都变得困难。""",
                "concepts": """**事务边界**：一次原子操作的起止范围，通常与「一个业务动作」对齐。
**依赖级提交**：`yield` 之后 `commit`，异常则 `rollback`，适合单动作接口。
**显式事务**：服务层用 `with session.begin():` 控制，适合多步骤业务。
**仓储层**：封装查询的类，接口只调用方法，不写 `select`。
**边界清晰**：接口层无 SQL、无事务控制；服务层管业务与事务；仓储层管查询。""",
                "plain": """事务像转账：扣钱和加钱必须一起成功，中间任何一步失败都要整笔撤回。
事务边界就是「这笔业务从哪开始、到哪结束」——划得太小会半成功，划得太大则锁得太久。
仓储层像银行柜员：你只说「查这个账户」，具体翻哪个本子、怎么翻，由柜员负责。""",
                "syntax": """**API 说明**

```python
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()          # 正常结束：提交
    except Exception:
        session.rollback()        # 任何异常：回滚
        raise
    finally:
        session.close()

with session.begin():            # 显式事务：块内全部成功才提交
    ...
```

- 依赖级提交适合「一个接口一个动作」；多步骤业务建议显式 `with session.begin()`。
- 回滚后要 `raise`，否则框架以为成功，返回 200 掩盖了失败。""",
                "example_code": '''from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50))
    done: Mapped[bool] = mapped_column(default=False)


engine = create_engine("sqlite+pysqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)

app = FastAPI(title="事务与分层示例")


class TaskRepository:
    """只管查询与持久化，不含业务判断。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Task]:
        return list(self.session.scalars(select(Task).order_by(Task.id)))

    def get(self, task_id: int) -> Task | None:
        return self.session.get(Task, task_id)

    def add(self, title: str) -> Task:
        task = Task(title=title)
        self.session.add(task)
        return task


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_repo(session: Annotated[Session, Depends(get_session)]) -> TaskRepository:
    return TaskRepository(session)


@app.post("/tasks/{task_id}/move", status_code=201)
def move_task(task_id: int, repo: Annotated[TaskRepository, Depends(get_repo)]) -> dict:
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    with repo.session.begin_nested():
        task.done = True
        new_task = repo.add(f"{task.title}（副本）")
    return {"moved": task.id, "copy_id": new_task.id}''',
                "code_lines": """1. `TaskRepository` 只暴露 `list_all/get/add`，把 `select` 关在类里。
2. `get_repo` 依赖复用会话依赖：同一请求内拿到同一个会话。
3. `get_session` 在 `yield` 之后统一 `commit`，正常结束自动提交。
4. 异常时 `rollback` 后必须 `raise`，把错误继续抛给异常处理器。
5. 接口里没有任何 SQL，也没有 `commit`，只表达业务。
6. `with repo.session.begin_nested():` 给多步操作划出保存点，任一步失败可回滚到此处。
7. 返回前把 ORM 对象转成字典/标量，避免会话关闭后的游离态问题。""",
                "output": """curl -X POST http://127.0.0.1:8000/tasks/1/move
HTTP/1.1 201 Created
{"moved":1,"copy_id":2}

# 任务 1 标记完成、并新增一条副本，两步在同一保存点内
curl http://127.0.0.1:8000/tasks
[{"id":1,"title":"写周报","done":true},{"id":2,"title":"写周报（副本）","done":false}]

# 若第二步抛异常，第一步的改动会随保存点一起回滚""",
                "mistakes": """- 依赖里回滚后忘了 `raise`，接口仍返回 200。
- 在接口函数里直接 `session.commit()`，与依赖级提交叠加，事务边界混乱。
- 仓储层里写业务判断（如权限），导致逻辑分散。
- 一个请求里开多个会话，跨会话对象互相引用时报游离态错误。
- 长事务里夹着外部 HTTP 调用，把数据库连接长时间占住。""",
                "error_analysis": """数据「半成功」：任务标记了完成但副本没建
—— 两个操作不在同一事务内，中间失败未回滚。用 `with session.begin()` 或 `begin_nested()` 包住。

`InvalidRequestError: A transaction is already begun on this Session`
—— 依赖已开启事务，接口里又 `begin()`。改用 `begin_nested()` 或把事务统一放在一层。

回滚了但客户端收到 200
—— 回滚分支没有重新抛出异常。""",
                "beginner_practice": """1. 把 `move_task` 改成「副本标题重复则整笔失败」，验证任务 1 的 `done` 也回滚。
2. 把 `list_all` 移到仓储层，接口只调用 `repo.list_all()`。""",
                "advanced_practice": """设计「批量导入 100 条任务」的接口：要求部分失败时能返回成功与失败明细。
说明你会用整批事务还是逐条事务，各自的取舍是什么。""",
                "quiz_note": "本节 6 道题：2 道基础理解（事务边界、仓储职责）+ 2 道代码阅读（读依赖提交、读保存点）+ 2 道应用练习（补回滚、改分层）。",
                "summary": """事务边界与业务动作对齐：单动作可用依赖级提交，多步骤用显式事务。
回滚后必须重新抛出异常，否则会把失败伪装成成功。
接口层不写 SQL 与事务，查询归仓储、业务与事务归服务层。""",
                "next_lesson": "下一节开始做认证：用户表怎么设计、密码为什么不能明文存。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-11-02",
                        "name": "事务边界与仓储分层",
                        "goal": "能划定事务边界，并把查询收进仓储层。",
                        "minutes": 40,
                        "criteria": "能指出「半成功写入」的原因并给出两种修法。",
                        "requires": ["fastapi-backend-11-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-11-02-1",
                        "kp": 0,
                        "title": "整笔失败的业务",
                        "description": "实现「创建任务并同时创建默认标签」：任一步失败则两步都不生效，用 `with session.begin()` 实现。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''@app.post("/tasks/with-tag", status_code=201)
def create_with_tag(title: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    with session.begin():
        task = Task(title=title)
        session.add(task)
        session.flush()
        session.add(Tag(name=f"{title}-默认", task_id=task.id))
    return {"task_id": task.id}''',
                        "explanation": "`with session.begin()` 块内全部成功才提交；`flush()` 让新对象先拿到主键供后续使用。",
                    },
                    {
                        "code": "fa-ex-11-02-2",
                        "kp": 0,
                        "title": "回滚后为什么要 raise",
                        "description": "依赖里 `except: session.rollback()` 却没 raise，会发生什么？说明后果。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''异常被吞掉，依赖正常结束，接口可能返回 200 与正常响应体，但数据实际已回滚。
调用方以为成功，后续操作基于错误状态，问题被推迟到更难排查的地方。''',
                        "explanation": "「静默失败」比报错更危险；回滚分支必须重新抛出，让统一异常处理接管。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-11-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "仓储层（Repository）最适合承担什么职责？",
                        "options": [
                            ("A", "封装数据查询与持久化"),
                            ("B", "校验用户权限"),
                            ("C", "生成 JWT"),
                            ("D", "记录访问日志"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "仓储层只负责「怎么取、怎么存」，业务规则与鉴权应在上层，避免耦合。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-11-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些属于「事务边界没划好」的表现？（多选）",
                        "options": [
                            ("A", "前一张表已提交，第二张表失败"),
                            ("B", "接口里出现多处 session.commit()"),
                            ("C", "长事务中夹着外部 HTTP 调用"),
                            ("D", "查询时使用了 select()"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "`select()` 是正常查询写法，与事务边界无关。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-11-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中依赖的 `session.commit()` 在什么时候执行？",
                        "options": [
                            ("A", "接口函数返回之前"),
                            ("B", "接口函数正常结束、yield 之后"),
                            ("C", "每次查询后"),
                            ("D", "进程退出时"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`yield` 之后的代码在接口处理完成后执行，因此提交发生在响应发送前后，异常则走回滚。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-11-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`begin_nested()` 创建的是保存点，可以只回滚块内的改动。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "A"},
                        "explanation": "保存点（SAVEPOINT）允许部分回滚，适合「主流程成功、子步骤可失败」的场景。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-11-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全依赖的异常处理，使失败时回滚并把异常继续抛出。横线处应填什么？\n\n```python\ntry:\n    yield session\n    session.commit()\nexcept Exception:\n    session.rollback()\n    ____\n```",
                        "options": [("A", "raise"), ("B", "return"), ("C", "pass"), ("D", "continue")],
                        "answer": {"value": "A"},
                        "explanation": "必须 `raise` 才能让异常继续传播到异常处理器，否则会把失败变成 200。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-11-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么「长事务里夹外部 HTTP 调用」是危险的？",
                        "answer": {"value": "事务期间数据库连接与行锁一直被占着，外部调用可能耗时数秒甚至超时，导致其他请求等锁、连接池被耗尽，严重时整库阻塞。正确做法是先完成外部调用拿到结果，再开一个短事务写库；或把外部调用改成异步/后台任务，缩短事务窗口。"},
                        "explanation": "核心是「锁与连接的占用时间」；缩短事务窗口是通用解法。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "fastapi-backend-12",
        "title": "用户认证与 JWT",
        "description": "从存密码到发令牌，让接口知道「你是谁」。",
        "order_index": 12,
        "lessons": [
            {
                "code": "fastapi-backend-12-lesson-01",
                "objectives": """1. 能设计用户表的关键字段与唯一约束；
2. 会用随机盐 + 慢哈希存储密码；
3. 会用常量时间比较校验密码，理解时序攻击；
4. 知道生产环境该用哪个哈希库。""",
                "why_learn": """数据库一旦泄漏，明文密码等于把所有用户的其它账号一起送出去。
哈希不是为了「不让管理员看见」，而是让拖库者无法还原；加盐与慢哈希则是让彩虹表和暴力破解都变得不划算。""",
                "concepts": """**不可逆哈希**：单向函数，只能校验不能还原。
**随机盐**：每个用户一个随机值，使相同密码哈希不同，抵御彩虹表。
**慢哈希**：pbkdf2/argon2/bcrypt 故意耗时，抬高暴力破解成本。
**常量时间比较**：`hmac.compare_digest` 避免按字节提前返回泄露信息。
**唯一约束**：邮箱唯一，注册时靠数据库兜底并发重复。""",
                "plain": """哈希像把纸放进碎纸机：能验证「这两张纸碎出来一样」，但没法拼回去。
盐像给每张纸先撒一把不同的胡椒粉再碎，别人就算有两张一样的纸，碎出来的样子也不同。
慢哈希是故意让碎纸机慢一点：你正常用只等几百毫秒，攻击者试几亿次就要几百年。""",
                "syntax": """**API 说明**

```python
import hashlib, hmac, os

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool: ...
```

- 存储格式自带算法与参数，方便日后升级迭代次数。
- 校验用 `hmac.compare_digest`，不要用 `==`。
- 生产建议：`pwdlib[argon2]` 或 `passlib[bcrypt]`，本课用标准库演示原理、不引入额外依赖。""",
                "example_code": '''import hashlib
import hmac
import os

ITERATIONS = 200_000


def hash_password(password: str, *, iterations: int = ITERATIONS) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    algorithm, iterations_text, salt_hex, digest_hex = stored.split("$")
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations_text)
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


stored = hash_password("s3cret-pass")
print("存储格式:", stored.split("$")[0], stored.split("$")[1])
print("同一密码两次哈希不同:", hash_password("s3cret-pass") != stored)
print("正确密码:", verify_password("s3cret-pass", stored))
print("错误密码:", verify_password("wrong-pass", stored))
print("篡改存储值:", verify_password("s3cret-pass", stored[:-4] + "0000"))''',
                "code_lines": """1. `os.urandom(16)` 生成 16 字节随机盐，每次注册都不同。
2. `pbkdf2_hmac("sha256", ...)` 是标准库提供的慢哈希，迭代次数直接决定耗时。
3. 存储串用 `$` 分隔算法、迭代次数、盐、摘要，便于日后整体升级参数。
4. `verify` 先按 `$` 拆解，确认算法匹配，再用同样参数重算摘要。
5. `hmac.compare_digest` 做常量时间比较，避免通过响应时间推测前缀。
6. 同一密码两次哈希结果不同（盐不同），但都能校验通过。
7. 篡改存储值后校验失败，说明摘要确实绑定了盐与密码。""",
                "output": """存储格式: pbkdf2_sha256 200000
同一密码两次哈希不同: True
正确密码: True
错误密码: False
篡改存储值: False

# 接口层面的请求与响应
curl -X POST http://127.0.0.1:8000/auth/register -H "Content-Type: application/json" \\
  -d '{"email":"lisi@example.com","password":"s3cret-pass"}'
HTTP/1.1 201 Created
{"id":1,"email":"lisi@example.com"}

# 数据库里实际存的是
pbkdf2_sha256$200000$9f3c...$5a71...""",
                "mistakes": """- 明文存密码，或用 md5/sha1 直接哈希（无盐、太快）。
- 全局共用一个盐，等于没加盐。
- 用 `==` 比较摘要，理论上可被时序攻击利用。
- 把 `password` 字段放进响应模型，注册接口直接回显密码。
- 迭代次数写成 1000 这类过低值，或高到 3 秒导致登录体验崩坏。""",
                "error_analysis": """`ValueError: not enough values to unpack (expected 4, got 1)`
—— 存储值格式不对（历史数据是明文或旧格式）。迁移时需兼容并逐步重算。

登录总是失败但密码没错
—— 盐或迭代次数没从存储值里读，而是用了默认值。

注册报 `UNIQUE constraint failed: users.email`
—— 邮箱已存在。应在业务层先查，并用唯一约束兜底并发。""",
                "beginner_practice": """1. 把迭代次数改成 1000 与 600000，各测一次校验耗时并记录。
2. 给 `verify_password` 加「格式非法返回 False」的保护。""",
                "advanced_practice": """设计密码升级方案：老用户用 pbkdf2 迭代 10 万，新标准是 argon2id。
说明如何在不要求用户改密码的前提下平滑迁移，并给出登录时的升级判定逻辑。""",
                "quiz_note": "本节 6 道题：2 道基础理解（盐的作用、慢哈希）+ 2 道代码阅读（读存储格式、读比较方式）+ 2 道应用练习（补校验、设计迁移）。",
                "summary": """密码只存不可逆哈希，且每个用户一个随机盐。
校验用常量时间比较；迭代次数要在安全与体验间取值。
生产用 argon2/bcrypt 等成熟库，标准库示例只用于理解原理。""",
                "next_lesson": "下一节发令牌：JWT 长什么样、怎么签名、过期了怎么办。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-12-01",
                        "name": "用户模型与密码哈希",
                        "goal": "能用加盐慢哈希存储与校验密码，并说清其安全边界。",
                        "minutes": 35,
                        "criteria": "能写出带盐的哈希/校验函数，并解释为什么不能用 == 比较。",
                        "requires": ["fastapi-backend-11-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-12-01-1",
                        "kp": 0,
                        "title": "加盐哈希与校验",
                        "description": "实现 `hash_password`/`verify_password`，要求存储串含算法与迭代次数；验证同一密码两次哈希不同但都能通过校验。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    algorithm, iterations, salt_hex, digest_hex = stored.split("$")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest.hex(), digest_hex)''',
                        "explanation": "把算法与参数写进存储串，未来升级迭代次数时老密码仍可校验。",
                    },
                    {
                        "code": "fa-ex-12-01-2",
                        "kp": 0,
                        "title": "为什么不能明文存",
                        "description": "从「拖库后果」「内部人员」「复用密码」三个角度说明明文存储的风险。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''拖库：一旦泄漏，全部密码直接可用；
内部人员：运维/开发能直接看到并冒用；
复用密码：用户在其它网站用同一密码，会造成连锁失陷。
哈希后即使泄漏，攻击者也只能逐个暴力破解，成本大幅提高。''',
                        "explanation": "三点分别对应外部攻击、内部风险与横向扩散，说明哈希不是「防管理员」而是「降低整体损失」。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-12-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "给密码加盐的主要目的是？",
                        "options": [
                            ("A", "让相同密码产生不同哈希，抵御彩虹表"),
                            ("B", "让哈希更快"),
                            ("C", "让密码可以还原"),
                            ("D", "减少存储空间"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "盐是随机值，使预计算表失效；它不改变「不可逆」这一性质。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-12-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于密码存储，正确的做法有？（多选）",
                        "options": [
                            ("A", "使用 pbkdf2/argon2/bcrypt 等慢哈希"),
                            ("B", "每个用户独立随机盐"),
                            ("C", "用 md5 加固定盐"),
                            ("D", "校验时使用常量时间比较"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "md5 太快且已被广泛破解，固定盐等于无盐，C 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-12-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例输出中「同一密码两次哈希不同」的原因是？",
                        "options": [
                            ("A", "每次生成新的随机盐"),
                            ("B", "迭代次数随机"),
                            ("C", "哈希函数不确定"),
                            ("D", "打印顺序不同"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "盐随机，因此摘要不同；但用各自的盐都能校验通过。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-12-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把迭代次数设得越高越安全，所以应该尽量设到 10 秒。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "过高的迭代会让登录与注册变慢，还可能被用来做 DoS；通常在几百毫秒量级取平衡。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-12-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全校验函数的比较语句，要求常量时间比较。横线处应填什么？\n\n```python\nreturn ____(digest.hex(), digest_hex)\n```",
                        "options": [
                            ("A", "hmac.compare_digest"),
                            ("B", "hashlib.md5"),
                            ("C", "operator.eq"),
                            ("D", "=="),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`hmac.compare_digest` 是标准库提供的常量时间比较函数。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-12-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "如何在不要求用户改密码的前提下，把老哈希算法升级到更强算法？",
                        "answer": {"value": "在用户登录成功（此时明文密码可用）时判断存储值的算法/参数是否为当前标准，若不是则用新算法重算并覆盖存储。这样用户无感知，随登录逐步迁移；长期未登录的账号可在其下次登录或强制重置时升级。存储串里必须自带算法与参数，才能做这种判定。"},
                        "explanation": "关键点是「借登录时刻的明文重算」，以及存储格式要自描述。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-12-lesson-02",
                "objectives": """1. 能说清 JWT 的三段结构与签名作用；
2. 会签发带过期时间的令牌并校验签名与 exp；
3. 会用依赖解析令牌并注入当前用户；
4. 能统一 401 的响应格式与 `WWW-Authenticate` 头。""",
                "why_learn": """服务端要「记住谁登录了」，但又不想每个请求都查库或存会话。
JWT 把用户信息与签名一起交给客户端，服务端只需验签即可信任内容——但这也意味着签名与过期校验一旦写错，任何人都能伪造身份。""",
                "concepts": """**结构**：`header.payload.signature`，前两段是 Base64URL 编码的 JSON。
**签名**：用密钥对 `header.payload` 做 HMAC，防篡改。
**过期**：payload 里 `exp` 是 Unix 时间戳，校验时必须检查。
**无状态**：服务端不存会话，因此「主动失效」需要额外机制（黑名单/版本号）。
**Bearer 方案**：`Authorization: Bearer <token>`，FastAPI 用 `OAuth2PasswordBearer` 解析。""",
                "plain": """JWT 像一张带防伪标签的入场券：券面写着「你是谁、几点到期」，防伪标签由场馆自己盖。
检票口只需核对标签真假与时间，不用回办公室查名单——这就是「无状态」。
但券一旦发出，除非改防伪标签的密钥或维护黑名单，否则到期前都有效——所以过期时间不能设太长。""",
                "syntax": """**API 说明**

```python
bearer = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: Annotated[str, Depends(bearer)]) -> dict: ...
```

- `OAuth2PasswordBearer` 从 `Authorization: Bearer` 头取令牌，缺失时自动 401。
- 自定义校验失败要抛 `HTTPException(401, headers={"WWW-Authenticate": "Bearer"})`。
- 生产建议用 `pyjwt` 库；本课用标准库演示签发与验签过程。""",
                "example_code": '''import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET = "dev-secret-change-me"
ALGORITHM = "HS256"

app = FastAPI(title="JWT 示例")
bearer = OAuth2PasswordBearer(tokenUrl="/auth/login")


def b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def create_token(sub: str, expires_in: int = 900) -> str:
    header = b64encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode())
    payload = b64encode(json.dumps({"sub": sub, "exp": int(time.time()) + expires_in}).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{b64encode(signature)}"


def decode_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
    except ValueError:
        raise HTTPException(status_code=401, detail="令牌格式不正确")
    signing_input = f"{header}.{payload}".encode()
    expected = hmac.new(SECRET.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, b64decode(signature)):
        raise HTTPException(status_code=401, detail="令牌签名无效")
    data = json.loads(b64decode(payload))
    if data.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="令牌已过期")
    return data


def get_current_user(token: Annotated[str, Depends(bearer)]) -> dict:
    data = decode_token(token)
    return {"id": 1, "email": data["sub"]}


@app.post("/auth/login")
def login(email: str, password: str) -> dict:
    if password != "s3cret-pass":
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    return {"access_token": create_token(email), "token_type": "bearer"}


@app.get("/me")
def me(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    return user''',
                "code_lines": """1. `SECRET` 必须来自环境变量，绝不能写死在仓库里（此处为教学示例）。
2. `b64encode` 用 URL 安全编码并去掉 `=` 填充，这是 JWT 的约定。
3. `create_token` 拼出 header 与 payload，`exp` 是「当前时间 + 有效期」。
4. 签名用 HMAC-SHA256 对 `header.payload` 计算，密钥只有服务端知道。
5. `decode_token` 先拆三段，格式不对直接 401，避免后续索引越界。
6. 验签用 `hmac.compare_digest`，比较的是重新计算的摘要与令牌中的签名。
7. 验签通过后必须再查 `exp`——签名有效不代表没过期。
8. `get_current_user` 把令牌解析结果转成用户对象，供接口直接使用。""",
                "output": """curl -X POST "http://127.0.0.1:8000/auth/login?email=lisi@example.com&password=s3cret-pass"
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJsaXNpQGV4YW1wbGUuY29tIiwiZXhwIjoxNzk0MTIzNDU2fQ.7dG1...","token_type":"bearer"}

curl -H "Authorization: Bearer eyJhbGci..." http://127.0.0.1:8000/me
{"id":1,"email":"lisi@example.com"}

# 篡改令牌中的 payload
curl -H "Authorization: Bearer eyJhbGci.eyJzdWIiOiJhZG1pbiJ9.xxx" http://127.0.0.1:8000/me
HTTP/1.1 401 Unauthorized
{"detail":"令牌签名无效"}

# 不带令牌
curl -i http://127.0.0.1:8000/me
HTTP/1.1 401 Unauthorized
{"detail":"Not authenticated"}""",
                "mistakes": """- 用了 `alg: none` 或在校验时不检查算法，攻击者可去掉签名。
- 只验签不查 `exp`，令牌永久有效。
- 把密钥写进代码或前端，签名形同虚设。
- 把敏感信息（密码、身份证）放进 payload——它只是 Base64，不是加密。
- 过期时间设成 30 天，令牌泄漏后长期可用。""",
                "error_analysis": """`401 Not authenticated`
—— 缺少 `Authorization: Bearer` 头，或头格式不对（少了 `Bearer ` 前缀）。

`401 令牌签名无效` 但令牌没改过
—— 密钥不一致（多实例配置不同），或签名段被 URL 编码破坏。

`jwt.exceptions.DecodeError`（用 pyjwt 时）
—— 段数不对或 Base64 解码失败，通常是令牌被截断。""",
                "beginner_practice": """1. 把 `expires_in` 改成 5 秒，等 6 秒后再请求 `/me`，确认返回「令牌已过期」。
2. 修改 SECRET 后重新请求，观察签名校验失败。""",
                "advanced_practice": """设计令牌刷新机制：access_token 15 分钟、refresh_token 7 天。
说明 refresh_token 存在哪里更安全、如何防止重放，以及「用户被禁用后立即失效」需要什么额外机制。""",
                "quiz_note": "本节 6 道题：2 道基础理解（JWT 结构、签名作用）+ 2 道代码阅读（读三段结构、读过期校验）+ 2 道应用练习（补校验、设计刷新）。",
                "summary": """JWT 是 `header.payload.signature`，签名防篡改、payload 只是编码不是加密。
校验必须做两件事：验签 + 检查 `exp`，缺一不可。
无状态带来便利，也意味着主动失效要靠黑名单或版本号。""",
                "next_lesson": "下一节做权限：登录之后，谁能改别人的任务。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-12-02",
                        "name": "JWT 签发、校验与当前用户",
                        "goal": "能签发并校验 JWT，并通过依赖注入当前用户。",
                        "minutes": 50,
                        "criteria": "能写出带 exp 的令牌签发与校验，并解释为什么要同时验签与验期。",
                        "requires": ["fastapi-backend-12-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-12-02-1",
                        "kp": 0,
                        "title": "加一个过期令牌用例",
                        "description": "签发一个 `expires_in=-1` 的令牌，用一个脚本请求 `/me` 并记录响应，说明校验顺序（先验签还是先验期）。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''先验签再验期：签名无效时直接 401，不解析内容（避免处理不可信数据）；
签名有效后再查 exp，过期返回「令牌已过期」。
顺序反了会把未经验签的 payload 当数据用，存在被伪造字段的风险。''',
                        "explanation": "安全校验的通用原则是「先验证来源可信，再使用内容」。",
                    },
                    {
                        "code": "fa-ex-12-02-2",
                        "kp": 0,
                        "title": "当前用户依赖",
                        "description": "写 `get_current_user`：解析令牌取 `sub`，再从「数据库」（用字典模拟）取用户；用户不存在返回 401。",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''USERS = {"lisi@example.com": {"id": 1, "email": "lisi@example.com"}}


def get_current_user(token: Annotated[str, Depends(bearer)]) -> dict:
    data = decode_token(token)
    user = USERS.get(data["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在或已注销")
    return user''',
                        "explanation": "即使签名有效，也要确认用户仍然存在/未被禁用，否则注销用户的旧令牌仍可用。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-12-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "JWT 的三段依次是？",
                        "options": [
                            ("A", "header.payload.signature"),
                            ("B", "payload.header.signature"),
                            ("C", "signature.payload.header"),
                            ("D", "header.signature.payload"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "标准顺序是 header、payload、signature，中间用点分隔。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-12-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 JWT 的安全要点，正确的是？（多选）",
                        "options": [
                            ("A", "payload 只是 Base64 编码，不能放敏感信息"),
                            ("B", "必须校验 exp"),
                            ("C", "密钥应来自环境变量"),
                            ("D", "签名可以保证内容加密不可读"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "签名保证完整性而非机密性，任何人都能解码 payload，D 错。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-12-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "把 payload 改成 `{\"sub\":\"admin\"}` 但保留原签名，请求结果是？",
                        "options": [
                            ("A", "以 admin 身份访问成功"),
                            ("B", "401 令牌签名无效"),
                            ("C", "500"),
                            ("D", "自动刷新令牌"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "签名基于 `header.payload` 计算，payload 变了签名就对不上。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-12-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`OAuth2PasswordBearer` 会在缺少令牌时自动返回 401。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "A"},
                        "explanation": "它作为安全方案声明在依赖里，缺失或格式不对时框架直接 401，不用自己判断。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-12-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全过期校验。横线处应填什么？\n\n```python\nif data.get(\"exp\", 0) ____ int(time.time()):\n    raise HTTPException(status_code=401, detail=\"令牌已过期\")\n```",
                        "options": [("A", "<"), ("B", ">"), ("C", "=="), ("D", "!=")],
                        "answer": {"value": "A"},
                        "explanation": "exp 小于当前时间即已过期；写成 `>` 会把有效令牌全部拒绝。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-12-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "用户被管理员禁用后，他手上的 JWT 还有 10 分钟有效，怎么让它立刻失效？",
                        "answer": {"value": "JWT 无状态，无法单方面撤回，需要额外机制：① 维护令牌黑名单（按 jti 或 jti+用户），校验时先查黑名单；② 用户表存 `token_version`，签发时写进 payload，校验时与库中版本比对，禁用/改密就 +1；③ 把有效期缩短到分钟级并用 refresh_token 续期，把失效窗口压到可接受范围。实际项目常组合 ②+③。"},
                        "explanation": "要点是「无状态 → 需要额外状态」这一矛盾，以及缩短有效窗口的权衡。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
