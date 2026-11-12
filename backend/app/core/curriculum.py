"""课程验收配置：每门课的章节规模与「超纲语法」判定表。

阶段 3 的验收规则写死了「20 章」与一套针对零基础课的语法表，课程一多就不适用了。
这里按课程给出配置，服务层只按 profile 取用，避免把某门课的数字写进通用逻辑。

约定：
- ``expected_chapters`` 为 None 时只校验「顺序连续、每章有课时」，不限制章数；
- ``scope_terms`` 是 (语法标记, 首次出现的章序)；章序为 999 表示本课程不涉及。
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 一、零基础入门：按章节推进基础语法，class / lambda / 装饰器等不在本课程范围
# ---------------------------------------------------------------------------

BASICS_SCOPE: tuple[tuple[str, int], ...] = (
    ('f"', 4),
    ("f'", 4),
    ("for ", 10),
    ("while ", 11),
    ("def ", 12),
    ("with open", 16),
    ("json.", 17),
    ("try:", 18),
    ("except", 18),
    # 本课程不涉及，出现即视为超纲
    ("class ", 999),
    ("lambda", 999),
    ("装饰器", 999),
    ("生成器", 999),
    ("async ", 999),
)

# ---------------------------------------------------------------------------
# 二、Python 进阶：类与函数从第 1 章就在用，只有生成器、上下文管理器等排后
# ---------------------------------------------------------------------------

ADVANCED_SCOPE: tuple[tuple[str, int], ...] = (
    ("yield", 4),
    ("contextlib", 6),
    ("@contextmanager", 6),
    ("asyncio", 999),
    ("threading", 999),
)

# ---------------------------------------------------------------------------
# 三、数据库：SQL 子句与 ORM 概念按章节推进
# ---------------------------------------------------------------------------

DATABASE_SCOPE: tuple[tuple[str, int], ...] = (
    ("JOIN", 2),
    ("GROUP BY", 2),
    ("CREATE INDEX", 4),
    ("SAVEPOINT", 5),
    ("DeclarativeBase", 7),
    ("sessionmaker", 8),
    ("alembic", 9),
)

# ---------------------------------------------------------------------------
# 四、FastAPI 后端：依赖注入、路由拆分、异步、数据库、认证按章节推进
# ---------------------------------------------------------------------------

FASTAPI_SCOPE: tuple[tuple[str, int], ...] = (
    ("uvicorn", 2),
    ("HTTPException", 3),
    ("BaseModel", 5),
    ("Field(", 6),
    ("Depends", 7),
    ("APIRouter", 8),
    ("middleware", 9),
    ("CORSMiddleware", 10),
    ("async def", 9),
    ("await ", 9),
    ("create_engine", 11),
    ("SessionLocal", 11),
    ("JWT", 12),
    ("UploadFile", 13),
    ("TestClient", 14),
    ("pytest", 14),
    ("lifespan", 15),
    ("gunicorn", 15),
)

# ---------------------------------------------------------------------------
# 五、大模型 API 应用：先讲清「一次调用」（第 2—4 章），再讲提示与多轮（5—8），
# 流式与结构化（9—10），工具调用（11—12），成本与可靠性（13—14），安全（15）。
# ---------------------------------------------------------------------------
# 术语 → 最早出现的章序。比「语法」更宽松：这里约束的是 API 能力，避免在
# 还没讲流式时就用 stream=True、没讲工具时就用 tool_calls。
LLM_SCOPE: tuple[tuple[str, int], ...] = (
    ("Bearer", 2),
    ("choices", 2),
    ("os.environ", 3),
    ("httpx", 4),
    ("json.loads", 5),
    ("stream", 9),
    ("event: ", 9),
    ("response_format", 10),
    ("tools=", 11),
    ("tool_calls", 11),
    ("max_retries", 14),
    ("backoff", 14),
    ("Retry-After", 14),
)

# ---------------------------------------------------------------------------
# 六、LangGraph Agent 开发：按「概念（1—3）→ 图构件（4—12）→ 路由与流程（13—15）
# → 模型与工具（16—19）→ 持久化与人工介入（20—23）→ 流式与工程化（24—27）→ 项目（28）」
# 推进。约束的是 API 能力：没讲路由就不出现条件边，没讲持久化就不出现 checkpointer。
# ---------------------------------------------------------------------------
LANGGRAPH_SCOPE: tuple[tuple[str, int], ...] = (
    # 第 4 章先跑通一个最小图，让读者知道「完整形态长什么样」
    ("StateGraph", 4),
    ("compile(", 4),
    ("TypedDict", 4),
    # 第 6 章逐字段讲 State 的类型标注
    ("Annotated", 6),
    ("add_messages", 6),
    # 第 13 章讲三种路由，其中 Send 分发需要 reducer 合并，先用到、第 15 章展开
    ("Command(", 13),
    ("Send(", 13),
    ("add_conditional_edges", 13),
    ("operator.add", 13),
    # 第 14 章讲循环上限
    ("recursion_limit", 14),
    # 第 16—19 章模型与工具
    ("BaseChatModel", 16),
    ("bind_tools", 17),
    ("convert_to_openai_tool", 17),
    ("ToolNode", 18),
    ("tools_condition", 18),
    ("create_react_agent", 19),
    # 第 20—23 章持久化与人工介入
    ("checkpointer", 20),
    ("thread_id", 20),
    ("InMemorySaver", 20),
    ("get_state_history", 20),
    ("update_state", 20),
    ("InMemoryStore", 21),
    ("interrupt(", 22),
    ("Command(resume", 22),
    # 第 24—26 章流式与工程化
    ("stream_mode", 24),
    ("get_stream_writer", 24),
    ("RetryPolicy", 25),
    ("retry_on", 25),
    ("StreamingResponse", 26),
)

# 术语的中文说明，用于报错信息
TERM_LABELS: dict[str, str] = {
    'f"': "f-string 格式化",
    "f'": "f-string 格式化",
    "for ": "for 循环",
    "while ": "while 循环",
    "def ": "函数定义",
    "with open": "文件读写",
    "json.": "JSON 模块",
    "try:": "异常处理",
    "except": "异常处理",
    "class ": "面向对象",
    "lambda": "匿名函数",
    "装饰器": "装饰器",
    "生成器": "生成器",
    "async ": "异步编程",
    "yield": "生成器（yield）",
    "contextlib": "contextlib 工具",
    "@contextmanager": "contextmanager",
    "asyncio": "asyncio 异步编程",
    "threading": "多线程",
    "JOIN": "多表连接",
    "GROUP BY": "分组聚合",
    "CREATE INDEX": "索引",
    "SAVEPOINT": "保存点",
    "DeclarativeBase": "ORM 声明式模型",
    "sessionmaker": "Session 工厂",
    "alembic": "Alembic 迁移",
    "uvicorn": "uvicorn 启动服务",
    "HTTPException": "HTTP 异常",
    "BaseModel": "Pydantic 模型",
    "Field(": "字段约束",
    "Depends": "依赖注入",
    "APIRouter": "路由模块化",
    "middleware": "中间件",
    "CORSMiddleware": "跨域中间件",
    "async def": "异步接口",
    "await ": "await 异步等待",
    "create_engine": "数据库引擎",
    "SessionLocal": "会话工厂",
    "JWT": "JWT 令牌",
    "UploadFile": "文件上传",
    "TestClient": "接口测试客户端",
    "pytest": "pytest 测试",
    "lifespan": "应用生命周期",
    "gunicorn": "gunicorn 进程管理",
    "Bearer": "Bearer 认证头",
    "choices": "响应 choices 结构",
    "os.environ": "环境变量读取",
    "httpx": "httpx 客户端",
    "json.loads": "JSON 解析",
    "stream": "流式输出",
    "event: ": "SSE 事件行",
    "response_format": "结构化输出参数",
    "tools=": "工具声明参数",
    "tool_calls": "工具调用返回",
    "max_retries": "重试次数上限",
    "backoff": "退避重试",
    "Retry-After": "限流等待响应头",
    "StateGraph": "状态图构建器",
    "compile(": "编译图",
    "TypedDict": "TypedDict 类型化字典",
    "Annotated": "Annotated 类型标注",
    "add_messages": "消息累加 reducer",
    "Command(": "Command 跳转指令",
    "Send(": "Send 并行分发",
    "add_conditional_edges": "条件边",
    "operator.add": "列表累加 reducer",
    "recursion_limit": "递归步数上限",
    "BaseChatModel": "聊天模型基类",
    "bind_tools": "绑定工具",
    "convert_to_openai_tool": "工具转 schema",
    "ToolNode": "工具节点",
    "tools_condition": "工具路由判定",
    "create_react_agent": "预制 ReAct Agent",
    "checkpointer": "检查点保存器",
    "thread_id": "线程标识",
    "InMemorySaver": "内存检查点",
    "get_state_history": "状态历史",
    "update_state": "改写状态",
    "InMemoryStore": "内存长期存储",
    "interrupt(": "人工中断",
    "Command(resume": "恢复执行",
    "stream_mode": "流式模式",
    "get_stream_writer": "自定义流写入",
    "RetryPolicy": "重试策略",
    "retry_on": "重试判定函数",
    "StreamingResponse": "流式响应",
}


@dataclass(frozen=True)
class CourseProfile:
    """一门课的验收配置。"""

    expected_chapters: int | None
    scope_terms: tuple[tuple[str, int], ...]


COURSE_PROFILES: dict[str, CourseProfile] = {
    "python-basics": CourseProfile(20, BASICS_SCOPE),
    "python-advanced": CourseProfile(10, ADVANCED_SCOPE),
    "python-database": CourseProfile(9, DATABASE_SCOPE),
    "fastapi-backend": CourseProfile(16, FASTAPI_SCOPE),
    "llm-api": CourseProfile(16, LLM_SCOPE),
    "langgraph-agent": CourseProfile(28, LANGGRAPH_SCOPE),
}

# 未登记的课程：不限制章数，也不做超纲检查（避免用别的课程的语法表误判）
DEFAULT_PROFILE = CourseProfile(None, ())


def profile_for(course_code: str) -> CourseProfile:
    return COURSE_PROFILES.get(course_code, DEFAULT_PROFILE)
