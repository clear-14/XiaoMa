"""课程目录种子（阶段 2）：5 个课程方向 + 7 门核心课程 + 先修依赖。

职责边界：
- 本文件是「课程目录」的唯一真理源：方向、课程元数据、章节与课时目录、先修关系；
- 每门课的知识点内容、教学正文与练习由各自的内容种子或后续内容建设阶段提供，
  本阶段只建结构化目录，不把空白内容标记为已完成的教材；
- 「Python 零基础入门」（python-basics）的章节/课时/知识点由 ``course_seed.py``
  维护（其 lessons 与知识点已完整），本文件只补充它的方向、等级、先修与目标。

幂等策略（可重复执行）：
- 课程按 code upsert，章节/课时按 code upsert，均不产生重复行；
- 方向关联、课程先修、入学知识点均按「目标集合 - 现有集合」差集同步，
  只增补缺失、清除多余，重复执行结果收敛；
- 不删除任何课程/章节/课时/知识点行（避免误删用户学习数据）。

能力等级与课程方向分开管理：``recommended_level``（L0/L1/L2）表达学习阶段，
``direction`` / ``directions`` 表达课程分类，两者互不替代。
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.course import (
    Chapter,
    Course,
    CourseDirection,
    CourseDirectionLink,
    CourseKnowledgePointPrerequisite,
    CoursePrerequisite,
    KnowledgePoint,
    Lesson,
    LessonKnowledgePoint,
)
from app.services.course_catalog_service import find_cycles

# ---------------------------------------------------------------------------
# 一、课程方向（课程分类）
# ---------------------------------------------------------------------------

DIRECTIONS: list[dict] = [
    {
        "code": "python-fundamentals",
        "name": "Python 编程基础",
        "description": (
            "从零建立编程思维：环境、语法、流程控制、函数与常用数据结构，"
            "以及面向对象、迭代器、装饰器等进阶语言能力。"
        ),
        "order_index": 1,
    },
    {
        "code": "python-engineering",
        "name": "Python 工程与数据库",
        "description": (
            "面向真实项目的工程能力：项目结构、日志与配置，以及 SQL、"
            "SQLAlchemy ORM、Session 事务与 Alembic 迁移。"
        ),
        "order_index": 2,
    },
    {
        "code": "python-backend",
        "name": "Python 后端开发",
        "description": (
            "用 FastAPI 构建可测试、可部署的后端服务：路由与校验、依赖注入、"
            "异步、认证权限、数据库集成与接口测试。"
        ),
        "order_index": 3,
    },
    {
        "code": "ai-llm",
        "name": "AI 大模型应用开发",
        "description": (
            "调用大模型 API 构建应用：消息结构与 Prompt、多轮对话、流式输出、"
            "结构化输出与 Tool Calling，并处理多 Provider 与降级。"
        ),
        "order_index": 4,
    },
    {
        "code": "ai-agent",
        "name": "AI Agent 与综合项目",
        "description": (
            "用 LangGraph 编排多步 Agent，掌握状态、路由、检查点、子图与流式事件，"
            "并完成可上线的综合项目交付。"
        ),
        "order_index": 5,
    },
]


# ---------------------------------------------------------------------------
# 二、七门核心课程
#
# modules 结构：章节 code / 标题 / 说明 / 课时列表；
# 课时为 (标题, 说明, 难度, 预计分钟)，code 由「章节 code + -lesson-NN」自动生成。
# python-basics 的 modules 为 None：章节/课时/知识点由 course_seed.py 维护。
# ---------------------------------------------------------------------------

CATALOG_COURSES: list[dict] = [
    {
        "code": "python-basics",
        "name": "Python 零基础入门",
        "description": (
            "小码首发课程，面向零基础学习者：从 Python 环境搭建到函数与常用数据结构，"
            "覆盖编程入门所需的核心语法与思维训练。每个知识点配有学习目标、预计学习时间、"
            "掌握标准与学习资源，按前置依赖关系组织学习路径。"
        ),
        "learning_objectives": (
            "能独立完成 Python 环境搭建并运行脚本；掌握变量、数据类型、运算符、"
            "流程控制、函数、模块与常用数据结构；能读懂并编写 100 行以内的脚本，"
            "用条件、循环与函数解决简单问题。"
        ),
        "direction": "python-fundamentals",
        "directions": ["python-fundamentals"],
        "recommended_level": "L0",
        "difficulty": "beginner",
        "version": "1.0.0",
        # 已有完整知识点与题库，保持已发布；新课目录一律初始化为 draft。
        "publish_status": "published",
        "sort_order": 1,
        "modules": None,
        "prerequisites": [],
        "required_knowledge_points": [],
    },
    {
        "code": "python-advanced",
        "name": "Python 进阶与工程实践",
        "description": (
            "在掌握基础语法之后，系统补齐面向对象、迭代器与生成器、装饰器、类型注解、"
            "虚拟环境与项目结构、日志与配置管理，形成可维护、可协作的工程习惯。"
        ),
        "learning_objectives": (
            "能设计类、继承与组合结构并正确使用方法解析顺序；能编写生成器与装饰器"
            "改造既有函数；能用类型注解与静态检查约束接口；能独立搭建带虚拟环境、"
            "分层目录、日志与配置校验的 Python 项目。"
        ),
        "direction": "python-fundamentals",
        "directions": ["python-fundamentals", "python-engineering"],
        "recommended_level": "L1",
        "difficulty": "intermediate",
        "version": "1.0.0",
        "publish_status": "published",
        "sort_order": 2,
        "prerequisites": ["python-basics"],
        "required_knowledge_points": [
            "python-basics-05-01",
            "python-basics-05-02",
            "python-basics-05-03",
            "python-basics-06-01",
        ],
                "modules": [
            {
                "code": "python-advanced-01",
                "title": "面向对象：类与对象",
                "description": "从「一堆函数」升级到「一组对象」：用类封装状态与行为。",
                "lessons": [
                    ("类与对象", "用 class 定义类型、用调用创建实例，理解模板与实例的关系。", "intermediate", 30),
                    ("实例属性、类属性与封装", "区分实例级与类级数据，用命名约定与 property 控制属性读写。", "intermediate", 35),
                ],
            },
            {
                "code": "python-advanced-02",
                "title": "继承与多态",
                "description": "复用父类能力，用统一接口处理不同的子类。",
                "lessons": [
                    ("继承与方法重写", "用 super() 复用父类初始化，按需重写方法。", "intermediate", 35),
                    ("多态与组合", "面向接口编程，优先用组合而不是层层继承。", "advanced", 35),
                ],
            },
            {
                "code": "python-advanced-03",
                "title": "推导式",
                "description": "用一行表达式完成「遍历 + 过滤 + 转换」。",
                "lessons": [
                    ("列表、字典与集合推导式", "把 for 循环改写成推导式，掌握条件过滤与嵌套写法。", "intermediate", 30),
                ],
            },
            {
                "code": "python-advanced-04",
                "title": "迭代器与生成器",
                "description": "理解 for 循环背后的协议，用 yield 惰性产出数据。",
                "lessons": [
                    ("迭代协议与生成器", "实现 __iter__ 与 __next__，用 yield 写出常量内存的数据流。", "advanced", 40),
                ],
            },
            {
                "code": "python-advanced-05",
                "title": "装饰器",
                "description": "用闭包包装函数，在不改函数体的前提下增加行为。",
                "lessons": [
                    ("闭包与装饰器", "理解闭包捕获变量，编写带 functools.wraps 的装饰器。", "advanced", 40),
                ],
            },
            {
                "code": "python-advanced-06",
                "title": "上下文管理器",
                "description": "用 with 保证资源一定被释放，包括异常路径。",
                "lessons": [
                    ("with 与上下文管理器", "实现 __enter__ 与 __exit__，用 contextlib 简化资源管理。", "intermediate", 30),
                ],
            },
            {
                "code": "python-advanced-07",
                "title": "类型注解",
                "description": "把接口约定写进代码，让工具在运行前发现问题。",
                "lessons": [
                    ("类型注解与静态检查", "为参数与返回值标注类型，用 list/dict/Optional 表达结构。", "intermediate", 35),
                ],
            },
            {
                "code": "python-advanced-08",
                "title": "虚拟环境与依赖管理",
                "description": "让每个项目有独立的解释器环境与可复现的依赖清单。",
                "lessons": [
                    ("venv 与 pip 依赖管理", "创建虚拟环境，用 requirements.txt 与 pyproject.toml 锁定依赖。", "intermediate", 30),
                ],
            },
            {
                "code": "python-advanced-09",
                "title": "项目目录结构",
                "description": "用 src 布局与包划分让项目能被别人接手。",
                "lessons": [
                    ("包结构、导入与 src 布局", "组织 __init__.py 与模块划分，避开循环导入与路径陷阱。", "intermediate", 35),
                ],
            },
            {
                "code": "python-advanced-10",
                "title": "日志与配置",
                "description": "把 print 换成可检索的日志，把硬编码换成可校验的配置。",
                "lessons": [
                    ("logging 与配置管理", "配置 Logger/Handler/Formatter，用环境变量外置配置并校验。", "intermediate", 35),
                ],
            },
        ],
    },
    {
        "code": "python-database",
        "name": "数据库与 Python 数据库开发",
        "description": (
            "从 SQL 基础到 SQLAlchemy ORM 与 Alembic 迁移：既能写对查询，"
            "也能在 Python 项目里可靠地管理连接、会话、事务与表结构演进。"
        ),
        "learning_objectives": (
            "能写出常用的建表、查询、连接与聚合 SQL；能用 SQLAlchemy 定义模型与关系，"
            "正确管理 Session 与事务边界；能识别并解决 N+1 查询；能用 Alembic 维护"
            "版本链并编写可回滚的数据迁移。"
        ),
        "direction": "python-engineering",
        "directions": ["python-engineering"],
        "recommended_level": "L1",
        "difficulty": "intermediate",
        "version": "1.0.0",
        "publish_status": "published",
        "sort_order": 3,
        "prerequisites": ["python-advanced"],
        "required_knowledge_points": [
            "python-basics-05-04",
            "python-basics-06-03",
        ],
                "modules": [
            {
                "code": "python-database-01",
                "title": "数据库基础",
                "description": "建立表、行、列与键的模型认知，理解为什么需要主键和外键。",
                "lessons": [
                    ("关系模型：表、行、列与主键", "理解一张表就是一类实体的集合，主键唯一标识一行。", "beginner", 25),
                    ("外键与约束", "用外键表达表之间的关系，用 NOT NULL/UNIQUE/CHECK 守住数据。", "intermediate", 30),
                ],
            },
            {
                "code": "python-database-02",
                "title": "SQL 查询",
                "description": "写出可读且正确的查询：先过滤再排序，跨表用 JOIN。",
                "lessons": [
                    ("SELECT 查询与过滤", "用 WHERE/ORDER BY/LIMIT 精确取数，理解 NULL 带来的坑。", "beginner", 30),
                    ("JOIN 与聚合", "用 INNER/LEFT JOIN 连接多表，用 GROUP BY 做统计。", "intermediate", 40),
                ],
            },
            {
                "code": "python-database-03",
                "title": "SQLite 实战",
                "description": "用项目真实的 SQLite 完成建库、查询与备份。",
                "lessons": [
                    ("SQLite 与 Python sqlite3", "用 sqlite3 模块建表、参数化查询并读取结果。", "intermediate", 35),
                ],
            },
            {
                "code": "python-database-04",
                "title": "索引",
                "description": "理解索引为什么快、什么时候不快。",
                "lessons": [
                    ("索引原理与执行计划", "用 B-Tree 索引加速等值与范围查询，用 EXPLAIN 验证是否命中。", "advanced", 35),
                ],
            },
            {
                "code": "python-database-05",
                "title": "事务",
                "description": "让一组写操作要么全成功、要么全回滚。",
                "lessons": [
                    ("事务与 ACID", "明确事务边界，理解隔离级别与并发写入的代价。", "advanced", 40),
                ],
            },
            {
                "code": "python-database-06",
                "title": "SQLAlchemy 2.x",
                "description": "从引擎与连接出发，用 Core 表达式构造 SQL。",
                "lessons": [
                    ("Engine 与 Core 表达式", "创建引擎与连接，用 select/insert/update 构造可组合语句。", "intermediate", 35),
                ],
            },
            {
                "code": "python-database-07",
                "title": "ORM 模型",
                "description": "用声明式模型把表映射成类，用关系表达外键。",
                "lessons": [
                    ("声明式模型与关系映射", "用 Mapped 与 mapped_column 定义字段，配置一对多与级联。", "intermediate", 40),
                ],
            },
            {
                "code": "python-database-08",
                "title": "Session 与 CRUD",
                "description": "把 Session 当工作单元：控制边界、避免 N+1。",
                "lessons": [
                    ("Session 生命周期与 CRUD", "管理会话与事务边界，完成增删改查并避免 N+1 查询。", "advanced", 45),
                ],
            },
            {
                "code": "python-database-09",
                "title": "Alembic 迁移",
                "description": "让表结构随代码演进，可回滚、可复现。",
                "lessons": [
                    ("版本链与 autogenerate", "理解 revision 链，生成迁移并逐条人工校对。", "advanced", 40),
                ],
            },
        ],
    },
    {
        "code": "fastapi-backend",
        "name": "FastAPI 后端开发",
        "description": (
            "以 FastAPI 为主线构建可上线的后端服务：HTTP 与接口契约、路由与参数、"
            "Pydantic 校验、依赖注入、路由模块化、异常与中间件、同步异步、数据库集成、"
            "认证与权限、文件上传、接口文档与测试、日志配置与部署，最后用一个任务管理 API "
            "把全部环节串起来。"
        ),
        "learning_objectives": (
            "能设计符合 REST 风格的接口与统一错误响应；能用 Pydantic 完成请求响应校验；"
            "能用依赖注入组织数据库会话、配置与权限；能接入数据库并为核心接口编写"
            "自动化测试，并把服务按生产要求部署起来。"
        ),
        "direction": "python-backend",
        "directions": ["python-backend"],
        "recommended_level": "L2",
        "difficulty": "intermediate",
        "version": "1.0.0",
        "publish_status": "published",
        "sort_order": 4,
        "prerequisites": ["python-advanced", "python-database"],
        "required_knowledge_points": [
            "python-basics-05-04",
            "python-basics-06-01",
            "python-basics-06-03",
        ],
        "modules": [
            {
                "code": "fastapi-backend-01",
                "title": "Web 后端与 API 基础",
                "description": "先想清楚请求怎么来、响应怎么回，再动手写代码。",
                "lessons": [
                    ("从浏览器请求到后端响应", "拆解 HTTP 请求与响应报文，分清方法、状态码与幂等。", "beginner", 30),
                    ("REST 资源设计与 JSON 契约", "按资源设计路径，用 JSON 契约对齐前后端。", "intermediate", 30),
                ],
            },
            {
                "code": "fastapi-backend-02",
                "title": "FastAPI 安装与项目启动",
                "description": "从零装好依赖，把第一个接口跑起来并看懂自动文档。",
                "lessons": [
                    ("安装、启动与自动文档", "建虚拟环境装依赖，用 uvicorn 启动，读懂 /docs 与启动报错。", "beginner", 40),
                ],
            },
            {
                "code": "fastapi-backend-03",
                "title": "路由与路径参数",
                "description": "让 URL 里的信息变成有类型的函数参数。",
                "lessons": [
                    ("路由声明与路径参数", "声明路由与路径参数，理解类型转换与返回值处理。", "beginner", 30),
                    ("路径顺序、枚举与参数校验", "处理固定路径与动态路径冲突，用枚举与校验约束取值。", "intermediate", 35),
                ],
            },
            {
                "code": "fastapi-backend-04",
                "title": "查询参数",
                "description": "把筛选、分页与排序做成可校验的查询参数。",
                "lessons": [
                    ("查询参数、分页与 Query 校验", "区分必填与可选，用 Query 约束范围并实现分页筛选。", "intermediate", 55),
                ],
            },
            {
                "code": "fastapi-backend-05",
                "title": "HTTP 方法与请求响应体",
                "description": "五种方法各司其职，请求体与响应体各管一头。",
                "lessons": [
                    ("五种 HTTP 方法的语义与实现", "按幂等与安全选择方法，用状态码准确表达结果。", "intermediate", 35),
                    ("请求体与响应体", "用模型约束入参与出参，控制响应字段与状态码。", "intermediate", 40),
                ],
            },
            {
                "code": "fastapi-backend-06",
                "title": "Pydantic 模型与数据校验",
                "description": "把校验规则写进模型，让非法输入在入口被拦住。",
                "lessons": [
                    ("模型、Field 与别名", "定义请求响应模型，用 Field 约束长度、范围与格式。", "intermediate", 35),
                    ("校验器、嵌套模型与错误响应", "表达跨字段规则，组织嵌套结构，统一 422 错误。", "advanced", 45),
                ],
            },
            {
                "code": "fastapi-backend-07",
                "title": "Depends 依赖注入",
                "description": "把分页、配置、会话与鉴权抽成可替换的依赖。",
                "lessons": [
                    ("Depends 基础与 yield 依赖", "声明依赖、理解缓存，用 yield 保证异常路径也能释放资源。", "intermediate", 50),
                ],
            },
            {
                "code": "fastapi-backend-08",
                "title": "路由模块化",
                "description": "一个文件写不下所有接口时，就该拆路由了。",
                "lessons": [
                    ("APIRouter 拆分与前缀标签", "按资源拆文件，用 prefix/tags 组织并统一挂载。", "intermediate", 50),
                ],
            },
            {
                "code": "fastapi-backend-09",
                "title": "统一异常处理与中间件",
                "description": "错误响应要一致，横切逻辑要能复用。",
                "lessons": [
                    ("统一异常处理", "用异常处理器把业务异常映射成统一的错误响应。", "advanced", 40),
                    ("中间件：耗时与请求 ID", "编写中间件记录耗时与追踪 ID，理解执行顺序。", "advanced", 35),
                ],
            },
            {
                "code": "fastapi-backend-10",
                "title": "CORS 与同步异步接口",
                "description": "跨域要配对，异步要用对。",
                "lessons": [
                    ("CORS 跨域配置", "理解预检请求，按来源白名单配置跨域。", "intermediate", 30),
                    ("同步与异步接口", "区分 def 与 async def 的执行方式，避免在协程里阻塞。", "advanced", 45),
                ],
            },
            {
                "code": "fastapi-backend-11",
                "title": "SQLAlchemy 数据库集成",
                "description": "把数据库会话接进接口，接口层不写 SQL。",
                "lessons": [
                    ("引擎、会话与 Session 依赖", "配置引擎与会话工厂，按请求注入会话。", "advanced", 45),
                    ("事务边界与数据访问分层", "在依赖或服务层划定事务边界，抽出仓储层。", "advanced", 40),
                ],
            },
            {
                "code": "fastapi-backend-12",
                "title": "用户认证与 JWT",
                "description": "从存密码到发令牌，让接口知道「你是谁」。",
                "lessons": [
                    ("用户模型与密码哈希", "设计用户表，用不可逆哈希存口令并校验登录。", "intermediate", 35),
                    ("JWT 签发、校验与当前用户", "理解 JWT 结构，签发带过期的令牌并注入当前用户。", "advanced", 50),
                ],
            },
            {
                "code": "fastapi-backend-13",
                "title": "权限控制与文件上传",
                "description": "谁能做什么，以及怎么安全收文件。",
                "lessons": [
                    ("角色与资源级权限", "用角色依赖与所有权校验实现最小权限。", "advanced", 40),
                    ("文件上传与上传校验", "接收上传文件，校验大小、类型并防路径穿越。", "intermediate", 40),
                ],
            },
            {
                "code": "fastapi-backend-14",
                "title": "API 文档与接口测试",
                "description": "文档自动生成不等于不用管，测试才是回归的底气。",
                "lessons": [
                    ("OpenAPI 元数据与文档定制", "补全标题、描述、响应示例与错误码说明。", "intermediate", 30),
                    ("pytest、TestClient 与测试库", "用测试客户端发请求，为每个用例准备独立数据。", "advanced", 60),
                ],
            },
            {
                "code": "fastapi-backend-15",
                "title": "日志、配置与部署",
                "description": "能跑起来只是开始，能稳定运行才算交付。",
                "lessons": [
                    ("日志配置与配置管理", "结构化记录关键字段，用环境变量分层配置。", "intermediate", 50),
                    ("生产部署", "按多进程与反向代理部署，配好健康检查与优雅退出。", "advanced", 45),
                ],
            },
            {
                "code": "fastapi-backend-16",
                "title": "综合项目：任务管理 API",
                "description": "把前面 23 个主题串成一个能测试、能部署的小项目。",
                "lessons": [
                    ("创建项目与目录结构", "建目录、装依赖、跑通健康检查接口。", "intermediate", 35),
                    ("拆分路由与数据模型", "按资源拆路由，定义请求响应模型。", "advanced", 40),
                    ("连接 SQLite 与实现 CRUD", "接数据库会话，完成任务的增删改查。", "advanced", 45),
                    ("接入认证与接口校验", "加登录与当前用户依赖，补齐业务校验。", "advanced", 45),
                    ("编写测试与整理项目配置", "写回归测试，把配置与启动方式整理成文档。", "advanced", 40),
                ],
            },
        ],
    },
    {
        "code": "llm-api",
        "name": "Python 大模型 API 应用开发",
        "description": (
            "围绕固定的 OpenAI 兼容调用方式构建大模型应用：把 Key 关进环境变量、"
            "组织 messages 与 Prompt、管理多轮上下文与长度预算、处理流式与结构化输出、"
            "实现函数与工具调用，并覆盖费用、限流、超时重试与提示注入等工程问题。"
        ),
        "learning_objectives": (
            "能把 API Key 从环境变量读出并解释为什么不能写进代码；"
            "能用 httpx 调用任意 OpenAI 兼容端点并独立配置 Base URL 与模型名；"
            "能组织 system/user/assistant 消息并设计稳定 Prompt；"
            "能在 token 预算内维护多轮上下文并做裁剪与摘要；"
            "能解析流式增量并透传给前端；能把输出约束成可校验的 JSON；"
            "能实现函数与工具调用闭环并处理超时、限流与异常；"
            "能识别提示注入与数据泄漏风险并给出防护措施。"
        ),
        "direction": "ai-llm",
        "directions": ["ai-llm"],
        "recommended_level": "L1",
        "difficulty": "intermediate",
        "version": "1.0.0",
        "publish_status": "published",
        "sort_order": 5,
        "prerequisites": ["python-advanced"],
        "required_knowledge_points": [
            "python-basics-02-06",
            "python-basics-05-02",
            "python-basics-06-03",
        ],
        "modules": [
            {
                "code": "llm-api-01",
                "title": "大语言模型基本概念",
                "description": "先知道它在做什么，再决定让它做什么。",
                "lessons": [
                    ("模型如何生成文本：Token、概率与采样", "理解下一个 token 的预测过程，以及温度如何影响输出。", "beginner", 30),
                    ("能力边界、幻觉与人工兜底", "分清适合与不适合交给模型的判断，为高风险场景设计兜底。", "beginner", 30),
                ],
            },
            {
                "code": "llm-api-02",
                "title": "模型服务商与 OpenAI 兼容 API",
                "description": "换服务商只改两个配置，不改一行业务代码。",
                "lessons": [
                    ("服务商生态与兼容协议", "认识主流服务商与兼容协议，理解为什么可以统一调用。", "beginner", 30),
                    ("Base URL、模型名称与请求响应结构", "把 endpoint、模型名与 JSON 字段对齐到一次真实请求。", "beginner", 35),
                ],
            },
            {
                "code": "llm-api-03",
                "title": "API Key 管理与安全",
                "description": "Key 等价于钱包，处理方式和密码一样严格。",
                "lessons": [
                    ("Key 从哪里来、怎么存", "用环境变量与 .env 保存 Key，并确保不落库、不进仓库、不进日志。", "intermediate", 30),
                    ("泄漏处置、轮换与最小权限", "掌握泄漏后的止损步骤与按环境分配 Key 的做法。", "intermediate", 30),
                ],
            },
            {
                "code": "llm-api-04",
                "title": "Python 调用大模型",
                "description": "第一次把请求发出去，并读懂返回。",
                "lessons": [
                    ("第一次调用：httpx 打通接口", "用 httpx 发 POST，读出 content 与 usage。", "beginner", 35),
                    ("封装可复用的模型客户端", "把地址、密钥、超时与错误处理收进一个客户端类。", "intermediate", 35),
                ],
            },
            {
                "code": "llm-api-05",
                "title": "消息结构、System Prompt 与 User Prompt",
                "description": "同一个模型，消息怎么排决定它听不听话。",
                "lessons": [
                    ("三种角色与提示分工", "用 system 定规则、user 提需求、assistant 存历史。", "beginner", 35),
                ],
            },
            {
                "code": "llm-api-06",
                "title": "Prompt 设计",
                "description": "把需求写成模型能稳定执行的任务说明。",
                "lessons": [
                    ("Prompt 结构：目标、约束与输出格式", "按固定骨架组织提示，减少歧义与漂移。", "intermediate", 35),
                    ("Few-shot、边界条件与迭代评测", "用示例锁定格式，用小样本集回归比较改动效果。", "advanced", 40),
                ],
            },
            {
                "code": "llm-api-07",
                "title": "多轮对话",
                "description": "让对话记得该记的，答得上刚才那句。",
                "lessons": [
                    ("对话状态与历史拼接", "把每轮问答按顺序追加进 messages，让模型看到上下文。", "intermediate", 35),
                    ("会话隔离与角色一致性", "按会话保存历史，避免串台与角色漂移。", "intermediate", 35),
                ],
            },
            {
                "code": "llm-api-08",
                "title": "上下文管理",
                "description": "上下文窗口有限，得决定记什么忘什么。",
                "lessons": [
                    ("Token 预算与上下文裁剪", "先算预算再拼消息，按策略保留关键轮次。", "advanced", 40),
                    ("摘要压缩与长会话策略", "把早期对话压成摘要，保留事实与结论。", "advanced", 40),
                ],
            },
            {
                "code": "llm-api-09",
                "title": "Streaming 流式输出",
                "description": "让用户先看到第一个字，而不是等十秒。",
                "lessons": [
                    ("SSE 协议与增量解析", "读懂 data: 行与 [DONE] 结束标记，按块拼接增量。", "advanced", 40),
                    ("流式中断、错误与后端透传", "处理半包、断线与超时，并按无缓冲方式转发。", "advanced", 40),
                ],
            },
            {
                "code": "llm-api-10",
                "title": "JSON 结构化输出",
                "description": "把自然语言结果变成程序能直接用的数据。",
                "lessons": [
                    ("JSON 模式与 Schema 约束", "用响应格式与字段说明限定输出形状。", "intermediate", 40),
                    ("校验失败与修复重试", "校验不过时把错误回喂模型，并限制重试次数。", "advanced", 40),
                ],
            },
            {
                "code": "llm-api-11",
                "title": "Function Calling",
                "description": "让模型申请调用你写好的函数，而不是自己编数。",
                "lessons": [
                    ("函数声明与调用返回", "用 JSON Schema 描述入参，读懂 tool_calls 结构。", "advanced", 40),
                    ("本地执行与结果回填", "执行函数并把结果作为 tool 消息回填再推理。", "advanced", 40),
                ],
            },
            {
                "code": "llm-api-12",
                "title": "Tool Calling",
                "description": "多个工具时怎么选、怎么停、怎么不错。",
                "lessons": [
                    ("多工具路由与选择", "用描述与参数约束引导模型选对工具。", "advanced", 40),
                    ("工具循环、上限与失败处理", "设置循环上限与失败回填，避免死循环与静默失败。", "advanced", 40),
                ],
            },
            {
                "code": "llm-api-13",
                "title": "Token、上下文窗口与调用费用",
                "description": "算得清才敢上线。",
                "lessons": [
                    ("用量统计、费用估算与限流", "从 usage 字段算成本，按配额与速率做限流。", "intermediate", 40),
                ],
            },
            {
                "code": "llm-api-14",
                "title": "API 超时、重试与异常处理",
                "description": "失败是常态，可预期才是工程。",
                "lessons": [
                    ("超时预算与退避重试", "为连接、读取与整体设超时，按指数退避重试有限次数。", "advanced", 40),
                    ("异常分类与用户可见提示", "把 401/403/429/5xx 分门别类，给出可操作提示。", "advanced", 40),
                ],
            },
            {
                "code": "llm-api-15",
                "title": "AI 应用安全",
                "description": "提示会被注入，输出会被利用。",
                "lessons": [
                    ("提示注入、越权与数据泄漏", "识别注入路径，给工具调用与输出加上边界。", "advanced", 40),
                ],
            },
            {
                "code": "llm-api-16",
                "title": "综合项目：Python AI 对话助手",
                "description": "把 19 个主题串成一个能跑、能扩、能交付的助手。",
                "lessons": [
                    ("模型配置与项目骨架", "从环境变量读 Key 与模型名，搭出可运行的项目结构。", "intermediate", 40),
                    ("消息管理与 API 调用", "实现消息模型与一次性调用，拿到完整回复。", "intermediate", 45),
                    ("多轮上下文与上下文裁剪", "维护会话历史并在预算内裁剪，保证多轮可用。", "advanced", 45),
                    ("流式输出与前端透传", "把增量推给调用方，处理中断与结束。", "advanced", 45),
                    ("错误处理、测试与交付", "补齐异常分类、重试与测试，整理成交付配置。", "advanced", 45),
                ],
            },
        ],
    },
    {
        "code": "langgraph-agent",
        "name": "LangGraph Agent 开发",
        "description": (
            "小码的特色课：从「Agent 是什么」讲到「Agent 怎么跑起来」。按概念 → 图构件 → "
            "路由与流程 → 模型与工具 → 持久化与人工介入 → 流式与工程化的顺序推进，"
            "覆盖 State、Node、Edge、StateGraph、条件路由、Reducer、Checkpointer、Store、"
            "Interrupt、Subgraph、Streaming 与 FastAPI 集成，最后落到一个个人 AI 学习 Agent。"
        ),
        "learning_objectives": (
            "能说清 Agent 与普通对话在控制流上的差别；能定义 State 与 Reducer 并解释状态合并规则；"
            "能构建带条件路由与终止条件的图，并说明每个节点和状态的作用；能接入模型与工具节点；"
            "能用 Checkpointer 与 Interrupt 实现状态恢复和人工审批；能用子图拆分流程、用流式事件输出进度；"
            "能用 FastAPI 对外提供接口，并用离线测试覆盖图的关键路径。"
        ),
        "direction": "ai-llm",
        "directions": ["ai-llm", "ai-agent"],
        "recommended_level": "L2",
        "difficulty": "advanced",
        "version": "1.0.0",
        "publish_status": "published",
        "sort_order": 6,
        "prerequisites": ["python-advanced", "llm-api"],
        "required_knowledge_points": [
            "python-basics-05-02",
            "python-basics-06-03",
        ],
        "modules": [
            {
                "code": "langgraph-agent-01",
                "title": "AI Agent 基础概念",
                "description": "先弄清 Agent 是什么，再看它和普通对话差在哪。",
                "lessons": [
                    ("什么是 AI Agent", "区分 Agent、固定工作流与普通对话，明确 Agent 的三要素。", "intermediate", 30),
                    ("思考—行动—观察循环", "理解 Agent 的最小循环，以及循环为什么会停下来。", "intermediate", 30),
                ],
            },
            {
                "code": "langgraph-agent-02",
                "title": "Agent 与普通大模型对话的区别",
                "description": "差别不在模型，而在谁决定下一步。",
                "lessons": [
                    ("一次生成与多步决策", "对比单次回答与多步决策在控制流、失败处理上的差异。", "intermediate", 30),
                ],
            },
            {
                "code": "langgraph-agent-03",
                "title": "LangGraph 的作用",
                "description": "多步、带分支和循环的流程，需要图来表达。",
                "lessons": [
                    ("从链式调用到图编排", "说明链式调用在哪里不够用，图编排解决了什么。", "intermediate", 30),
                ],
            },
            {
                "code": "langgraph-agent-04",
                "title": "LangGraph 项目初始化",
                "description": "把环境装好、把版本钉住，再跑通第一个图。",
                "lessons": [
                    ("安装与版本确认", "安装 langgraph，确认版本，避免照抄旧版接口。", "beginner", 30),
                    ("跑通第一个图", "先让最小图跑起来看到完整形态，再回头逐块拆解。", "intermediate", 35),
                ],
            },
            {
                "code": "langgraph-agent-05",
                "title": "Graph",
                "description": "用图的语言描述流程：谁在跑，跑完去哪。",
                "lessons": [
                    ("图、节点与边", "建立节点、边、有向图与环路的基本概念。", "beginner", 30),
                ],
            },
            {
                "code": "langgraph-agent-06",
                "title": "State",
                "description": "状态是图的血液，定义好它后面才稳。",
                "lessons": [
                    ("状态结构与类型约束", "用 TypedDict 定义 State，明确每个字段的类型与默认值。", "intermediate", 35),
                    ("状态的读写与生命周期", "节点读什么、写什么，状态在哪里被合并。", "intermediate", 35),
                ],
            },
            {
                "code": "langgraph-agent-07",
                "title": "Node",
                "description": "节点是函数：接状态、返增量、不改原对象。",
                "lessons": [
                    ("节点是什么", "理解节点的职责边界：只做一件事，只返回增量。", "beginner", 30),
                ],
            },
            {
                "code": "langgraph-agent-08",
                "title": "Edge",
                "description": "用边描述顺序，用 START 和 END 标注边界。",
                "lessons": [
                    ("边与入口出口", "普通边、入口点、出口点的作用与常见错误。", "beginner", 30),
                ],
            },
            {
                "code": "langgraph-agent-09",
                "title": "StateGraph",
                "description": "把 State、Node、Edge 拼成一个完整图。",
                "lessons": [
                    ("把三块组装起来", "第一次把状态、节点、边组合成可运行的 StateGraph。", "intermediate", 35),
                ],
            },
            {
                "code": "langgraph-agent-10",
                "title": "图创建和编译",
                "description": "注册节点、连接边、编译成可执行对象。",
                "lessons": [
                    ("add_node 与 add_edge", "注册节点与连接边，避免重复注册和悬空节点。", "intermediate", 35),
                    ("compile 与运行", "编译做了什么，invoke 返回什么，怎么读结果。", "intermediate", 35),
                ],
            },
            {
                "code": "langgraph-agent-11",
                "title": "节点函数",
                "description": "写节点函数最容易踩的几个坑。",
                "lessons": [
                    ("函数签名与返回值", "参数怎么接、返回什么、抛异常会怎样。", "intermediate", 35),
                ],
            },
            {
                "code": "langgraph-agent-12",
                "title": "状态更新",
                "description": "返回增量还是整份状态，结果差别很大。",
                "lessons": [
                    ("部分更新与全量更新", "节点返回值的合并规则，以及覆盖带来的副作用。", "advanced", 35),
                    ("并发写入冲突", "同一步多个节点写同一个键会发生什么。", "advanced", 35),
                ],
            },
            {
                "code": "langgraph-agent-13",
                "title": "条件路由",
                "description": "让流程按数据决定走向，而不是写死顺序。",
                "lessons": [
                    ("路由函数与条件边", "用一个纯函数决定下一步去哪，并给出兜底分支。", "advanced", 40),
                    ("Command 与 Send", "让节点自己决定跳转，以及把任务拆成并行分支。", "advanced", 40),
                ],
            },
            {
                "code": "langgraph-agent-14",
                "title": "循环和流程控制",
                "description": "写循环必须写出口，还要知道步数上限。",
                "lessons": [
                    ("循环、终止条件与上限", "构造带出口的循环，理解递归步数上限与死循环防护。", "advanced", 35),
                ],
            },
            {
                "code": "langgraph-agent-15",
                "title": "Reducer",
                "description": "覆盖会把并行结果吞掉，reducer 负责合并。",
                "lessons": [
                    ("为什么需要 reducer", "从并行写入报错出发，理解状态合并的必要性。", "advanced", 40),
                    ("内置与自定义 reducer", "add_messages、operator.add 与自己的合并函数。", "advanced", 40),
                ],
            },
            {
                "code": "langgraph-agent-16",
                "title": "接入大模型",
                "description": "LangGraph 不绑定模型，只要一个能 invoke 的对象。",
                "lessons": [
                    ("ChatModel 抽象", "理解聊天模型接口：消息进、消息出，节点里怎么调。", "advanced", 40),
                    ("接 OpenAI 兼容接口", "用 httpx 实现最小 ChatModel，把消息转成请求体。", "advanced", 45),
                ],
            },
            {
                "code": "langgraph-agent-17",
                "title": "Tool Calling",
                "description": "让模型说出「我要调哪个工具、传什么参数」。",
                "lessons": [
                    ("工具定义与 schema", "用 @tool 声明工具，看清模型实际收到的参数结构。", "advanced", 40),
                    ("tool_calls 与结果回填", "解析调用意图，按 id 把工具结果送回对话。", "advanced", 45),
                ],
            },
            {
                "code": "langgraph-agent-18",
                "title": "工具节点",
                "description": "预制工具节点替你执行，失败要能兜住。",
                "lessons": [
                    ("ToolNode 与错误处理", "用 ToolNode 执行工具，处理参数错误与异常。", "advanced", 40),
                ],
            },
            {
                "code": "langgraph-agent-19",
                "title": "Agent 工作流",
                "description": "把模型、工具、路由拼成最小可用的 Agent。",
                "lessons": [
                    ("手写 ReAct 图", "agent 加 tools 加条件边，手写一个会调工具的循环。", "advanced", 45),
                    ("工作流形态与版本定位", "ReAct、规划—执行、审批流的取舍，以及预制 Agent 的版本变化。", "advanced", 35),
                ],
            },
            {
                "code": "langgraph-agent-20",
                "title": "Checkpointer",
                "description": "thread_id 决定哪条会话，检查点决定能回到哪。",
                "lessons": [
                    ("线程与检查点", "配置 thread_id，理解检查点里存了什么、何时写入。", "advanced", 40),
                    ("时间旅行与人工修正", "回看历史、改一个状态、从那里继续跑。", "advanced", 45),
                ],
            },
            {
                "code": "langgraph-agent-21",
                "title": "Store",
                "description": "跨会话的长期数据放在 Store，不放在状态里。",
                "lessons": [
                    ("跨线程长期存储", "用命名空间读写用户偏好这类跨线程数据。", "advanced", 40),
                ],
            },
            {
                "code": "langgraph-agent-22",
                "title": "Interrupt",
                "description": "在图中间停下来，等一个真实的人回答。",
                "lessons": [
                    ("中断与恢复", "用 interrupt 暂停流程，用 Command 带着答案恢复。", "advanced", 45),
                    ("审批流设计", "把高风险动作放到人工确认之后，并处理拒绝路径。", "advanced", 40),
                ],
            },
            {
                "code": "langgraph-agent-23",
                "title": "Subgraph",
                "description": "把一段流程打包成子图，父图只关心输入输出。",
                "lessons": [
                    ("子图定义与调用", "把编译好的子图当节点用，理解它的边界。", "advanced", 40),
                    ("父子状态映射", "父子 schema 不同时，输入输出怎么对接。", "advanced", 45),
                ],
            },
            {
                "code": "langgraph-agent-24",
                "title": "Streaming",
                "description": "不同流式模式给你不同的东西，别选错。",
                "lessons": [
                    ("stream_mode 各模式", "values、updates、messages、custom 四种模式的差别。", "advanced", 40),
                    ("自定义事件与前端透传", "在节点里写进度事件，按 SSE 推给前端。", "advanced", 45),
                ],
            },
            {
                "code": "langgraph-agent-25",
                "title": "错误处理与重试",
                "description": "哪些异常会重试、哪些不会，必须显式声明。",
                "lessons": [
                    ("RetryPolicy 与异常分类", "配置重试策略，理解默认策略不重试哪些异常。", "advanced", 40),
                ],
            },
            {
                "code": "langgraph-agent-26",
                "title": "FastAPI 集成 LangGraph",
                "description": "把图包成接口，一次性返回和流式返回都要有。",
                "lessons": [
                    ("同步接口", "把图包成 FastAPI 接口，处理输入校验与错误映射。", "advanced", 45),
                    ("SSE 流式接口", "用 astream 把图的进度一段段推出去。", "advanced", 45),
                ],
            },
            {
                "code": "langgraph-agent-27",
                "title": "LangGraph 测试",
                "description": "不打真实模型，也能测出图的行为。",
                "lessons": [
                    ("离线测试与断言", "用假模型与内存检查点写确定性的图测试。", "advanced", 40),
                ],
            },
            {
                "code": "langgraph-agent-28",
                "title": "综合项目：个人 AI 学习 Agent",
                "description": "把 27 章的东西合成一个能跑的教学案例。",
                "lessons": [
                    ("需求拆解与图设计", "把「识别问题、读资料、调工具、存状态、条件分支、给接口」翻译成节点与边。", "advanced", 45),
                    ("模型配置与工具层", "配置从环境变量读，工具走白名单。", "advanced", 50),
                    ("状态与条件路由", "识别问题、检索资料、决定是否调工具。", "advanced", 50),
                    ("持久化与人工介入", "保存对话状态，高风险动作走审批。", "advanced", 50),
                    ("FastAPI 接口与测试", "对外提供同步与流式接口，补上离线测试。", "advanced", 50),
                ],
            },
        ],
    },
    {
        "code": "software-engineering-deploy",
        "name": "软件工程与项目部署",
        "description": (
            "把项目从本地推到线上：Git 协作、pytest 测试体系、Docker 与 Docker Compose、"
            "环境变量与密钥管理、反向代理与 HTTPS、日志采集与故障排查。"
        ),
        "learning_objectives": (
            "能用 Git 完成分支协作与版本发布；能为核心逻辑补齐自动化测试并接入 CI；"
            "能编写 Dockerfile 与 compose 编排前后端与数据库；能按 12-Factor 外置配置与密钥；"
            "能部署项目并通过日志定位常见线上问题。"
        ),
        "direction": "python-backend",
        "directions": ["python-backend", "ai-agent"],
        "recommended_level": "L2",
        "difficulty": "intermediate",
        "version": "1.0.0",
        "publish_status": "published",
        "sort_order": 7,
        "prerequisites": ["fastapi-backend", "langgraph-agent"],
        "required_knowledge_points": ["python-basics-05-04"],
        "modules": [
            {
                "code": "software-engineering-deploy-01",
                "title": "Git 与协作",
                "description": "让改动可追溯、可评审、可回退。",
                "lessons": [
                    ("Git 基础与提交规范", "掌握提交、查看历史与撤销，写出可读的提交信息。", "beginner", 30),
                    ("分支策略与合并", "使用功能分支与合并请求，处理冲突与变基取舍。", "intermediate", 35),
                    ("PR 评审与版本发布", "用评审清单保证质量，按语义化版本打标签发布。", "intermediate", 30),
                ],
            },
            {
                "code": "software-engineering-deploy-02",
                "title": "测试工程",
                "description": "测试不是负担，而是让重构敢下手的安全网。",
                "lessons": [
                    ("pytest 进阶", "使用参数化、标记与断言改写提升用例表达力。", "intermediate", 35),
                    ("fixture 分层与复用", "按作用域组织 fixture，控制初始化成本与隔离性。", "advanced", 40),
                    ("mock 与外部依赖隔离", "替换网络与模型调用，让测试稳定且快速。", "advanced", 40),
                    ("覆盖率与 CI 流水线", "设置覆盖率门槛，在提交与合并时自动执行。", "intermediate", 35),
                ],
            },
            {
                "code": "software-engineering-deploy-03",
                "title": "Docker 基础",
                "description": "把运行环境固化进镜像，消除「我这能跑」。",
                "lessons": [
                    ("镜像与容器", "理解分层文件系统与容器生命周期。", "beginner", 30),
                    ("编写 Dockerfile", "从基础镜像构建应用镜像，正确设置工作目录与启动命令。", "intermediate", 35),
                    ("多阶段构建与体积优化", "把构建依赖与运行时分离，减小镜像并缩短启动。", "advanced", 40),
                    (".dockerignore 与构建缓存", "排除无关文件，按变更频率排列指令以命中缓存。", "intermediate", 30),
                ],
            },
            {
                "code": "software-engineering-deploy-04",
                "title": "Docker Compose",
                "description": "用一个文件描述整套服务，并保证启动顺序正确。",
                "lessons": [
                    ("服务编排与依赖", "定义多个服务与 depends_on，梳理启动依赖。", "intermediate", 35),
                    ("网络与端口", "理解服务名解析与端口映射，避免暴露内部端口。", "intermediate", 30),
                    ("卷与数据持久化", "用命名卷保存数据库，区分绑定挂载与卷。", "intermediate", 35),
                    ("健康检查与启动顺序", "用 healthcheck 判断就绪，避免应用先于数据库启动。", "advanced", 40),
                ],
            },
            {
                "code": "software-engineering-deploy-05",
                "title": "配置与密钥",
                "description": "同一份镜像，靠配置适配不同环境。",
                "lessons": [
                    ("12-Factor 配置原则", "把配置从代码中剥离，按环境注入。", "intermediate", 30),
                    ("环境变量与多环境", "维护 dev/prod 差异清单，避免配置漂移。", "intermediate", 30),
                    ("密钥管理与轮换", "密钥不入库不入镜像，制定轮换与吊销流程。", "advanced", 35),
                ],
            },
            {
                "code": "software-engineering-deploy-06",
                "title": "部署与发布",
                "description": "从单机部署到可回滚的发布流程。",
                "lessons": [
                    ("反向代理与域名", "用 Nginx 转发前后端与流式接口，正确设置超时。", "intermediate", 35),
                    ("HTTPS 与证书", "配置证书与自动续期，强制跳转安全协议。", "intermediate", 30),
                    ("发布流程与灰度", "设计发布步骤、健康检查与失败自动回退。", "advanced", 40),
                    ("备份与回滚", "定期备份数据与镜像，验证回滚可用。", "advanced", 35),
                ],
            },
            {
                "code": "software-engineering-deploy-07",
                "title": "日志与排障",
                "description": "线上问题靠证据定位，而不是靠猜。",
                "lessons": [
                    ("日志采集与检索", "统一日志格式与级别，集中采集并按请求追踪。", "intermediate", 35),
                    ("常见故障定位", "按「入口—服务—依赖—数据」逐层排查 502、超时与空响应。", "advanced", 40),
                    ("监控告警与容量", "设置关键指标阈值，提前发现磁盘、连接与内存问题。", "intermediate", 35),
                ],
            },
            {
                "code": "software-engineering-deploy-08",
                "title": "综合项目部署实战",
                "description": "把前端、后端、数据库与 Agent 服务一起上线。",
                "lessons": [
                    ("前后端与数据库联调", "打通跨域、代理与会话，验证核心链路。", "advanced", 45),
                    ("Agent 服务上线", "为长耗时与流式接口设置超时、并发与降级。", "advanced", 40),
                    ("上线检查清单与复盘", "按清单逐项验收，记录问题与改进项。", "intermediate", 35),
                ],
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------


def validate_catalog() -> None:
    """写库前校验目录：code 唯一、方向存在、课时结构合法、先修无环且引用存在。"""
    direction_codes = {item["code"] for item in DIRECTIONS}
    if len(direction_codes) != len(DIRECTIONS):
        raise ValueError("课程方向 code 存在重复")

    course_codes = [item["code"] for item in CATALOG_COURSES]
    if len(course_codes) != len(set(course_codes)):
        raise ValueError("课程 code 存在重复")
    course_code_set = set(course_codes)

    for course in CATALOG_COURSES:
        label = course["code"]
        if course["direction"] not in direction_codes:
            raise ValueError(f"{label} 的主方向不存在：{course['direction']}")
        unknown = set(course["directions"]) - direction_codes
        if unknown:
            raise ValueError(f"{label} 关联了不存在的方向：{sorted(unknown)}")
        if course["direction"] not in course["directions"]:
            raise ValueError(f"{label} 的主方向必须包含在关联方向中")
        if course["recommended_level"] not in {"L0", "L1", "L2"}:
            raise ValueError(f"{label} 推荐等级不合法：{course['recommended_level']}")
        if course["difficulty"] not in {"beginner", "intermediate", "advanced"}:
            raise ValueError(f"{label} 难度不合法：{course['difficulty']}")
        if course["publish_status"] not in {"draft", "published", "archived"}:
            raise ValueError(f"{label} 发布状态不合法：{course['publish_status']}")

        module_codes: list[str] = []
        for module in course.get("modules") or []:
            module_codes.append(module["code"])
            if not module["title"].strip():
                raise ValueError(f"{label} 存在没有标题的章节")
            if not module["lessons"]:
                raise ValueError(f"{module['code']} 没有课时")
            for lesson in module["lessons"]:
                if len(lesson) != 4:
                    raise ValueError(f"{module['code']} 课时定义必须为 4 元组")
                title, _description, difficulty, minutes = lesson
                if not title.strip():
                    raise ValueError(f"{module['code']} 存在没有标题的课时")
                if difficulty not in {"beginner", "intermediate", "advanced"}:
                    raise ValueError(f"{module['code']} 课时难度不合法：{difficulty}")
                if not isinstance(minutes, int) or minutes <= 0:
                    raise ValueError(f"{module['code']} 课时时长必须为正整数")
        if len(module_codes) != len(set(module_codes)):
            raise ValueError(f"{label} 章节 code 存在重复")

        for prerequisite in course["prerequisites"]:
            if prerequisite not in course_code_set:
                raise ValueError(f"{label} 的先修课程不存在：{prerequisite}")
            if prerequisite == label:
                raise ValueError(f"{label} 不能以自己为先修课程")

    edges = [
        (course["code"], prerequisite)
        for course in CATALOG_COURSES
        for prerequisite in course["prerequisites"]
    ]
    cycles = find_cycles(course_codes, edges)
    if cycles:
        raise ValueError(f"课程先修依赖存在循环：{cycles}")


# ---------------------------------------------------------------------------
# 写入（幂等 upsert + 差集同步）
# ---------------------------------------------------------------------------


def _lesson_code(module_code: str, index: int) -> str:
    return f"{module_code}-lesson-{index:02d}"


def seed_course_catalog(db: Session) -> dict:
    """写入课程方向、七门课程目录与先修依赖；返回统计信息。

    幂等：重复执行不新增课程/章节/课时，方向关联与先修关系按差集同步。
    """
    validate_catalog()

    # ---- 1. 课程方向 ----
    direction_map: dict[str, CourseDirection] = {}
    for item in DIRECTIONS:
        direction = db.scalars(
            select(CourseDirection).where(CourseDirection.code == item["code"])
        ).first()
        if direction is None:
            direction = CourseDirection(code=item["code"])
            db.add(direction)
        direction.name = item["name"]
        direction.description = item["description"]
        direction.order_index = item["order_index"]
        direction_map[item["code"]] = direction
    db.flush()

    # ---- 2. 课程元数据 + 章节/课时 ----
    course_map: dict[str, Course] = {}
    chapter_count = 0
    lesson_count = 0
    for item in CATALOG_COURSES:
        course = db.scalars(
            select(Course).where(Course.code == item["code"])
        ).first()
        if course is None:
            course = Course(code=item["code"])
            db.add(course)
        course.name = item["name"]
        course.description = item["description"]
        course.learning_objectives = item["learning_objectives"]
        course.direction = item["direction"]
        course.difficulty = item["difficulty"]
        course.recommended_level = item["recommended_level"]
        course.version = item["version"]
        course.publish_status = item["publish_status"]
        course.sort_order = item["sort_order"]
        db.flush()
        course_map[course.code] = course

        # 方向关联：只增补缺失、清除多余
        desired_direction_ids = {
            direction_map[code].id for code in item["directions"]
        }
        existing_links = {
            link.direction_id: link
            for link in db.scalars(
                select(CourseDirectionLink).where(
                    CourseDirectionLink.course_id == course.id
                )
            ).all()
        }
        for direction_id in desired_direction_ids - set(existing_links):
            db.add(
                CourseDirectionLink(
                    course_id=course.id, direction_id=direction_id
                )
            )
        for direction_id in set(existing_links) - desired_direction_ids:
            db.delete(existing_links[direction_id])
        db.flush()

        modules = item.get("modules")
        if not modules:
            # python-basics 的章节/课时由 course_seed.py 维护，这里不重复创建
            continue

        total_minutes = 0
        desired_lesson_codes: set[str] = set()
        for module_index, module in enumerate(modules, start=1):
            chapter = db.scalars(
                select(Chapter).where(Chapter.code == module["code"])
            ).first()
            if chapter is None:
                chapter = Chapter(code=module["code"])
                db.add(chapter)
            chapter.course = course
            chapter.title = module["title"]
            chapter.description = module.get("description")
            chapter.order_index = module_index
            db.flush()
            chapter_count += 1

            for lesson_index, lesson_data in enumerate(
                module["lessons"], start=1
            ):
                title, description, difficulty, minutes = lesson_data
                code = _lesson_code(module["code"], lesson_index)
                lesson = db.scalars(
                    select(Lesson).where(Lesson.code == code)
                ).first()
                if lesson is None:
                    lesson = Lesson(code=code)
                    db.add(lesson)
                lesson.chapter = chapter
                lesson.title = title
                lesson.description = description
                lesson.difficulty = difficulty
                lesson.estimated_minutes = minutes
                lesson.order_index = lesson_index
                desired_lesson_codes.add(code)
                db.flush()
                lesson_count += 1
                total_minutes += minutes
        course.estimated_minutes = total_minutes
        db.flush()

        # 目录调整后遗留的旧课时（已不在目录里且从未写入过正文）会被清理，
        # 避免出现「有课时但没有内容」的空壳，让内容验收永远无法通过。
        # 有正文的课时一律保留，交由人工判断是否需要迁移。
        stale = db.scalars(
            select(Lesson).join(Chapter).where(Chapter.course_id == course.id)
        ).all()
        for lesson in stale:
            if lesson.code in desired_lesson_codes:
                continue
            if lesson.content is not None:
                continue
            db.execute(
                delete(LessonKnowledgePoint).where(
                    LessonKnowledgePoint.lesson_id == lesson.id
                )
            )
            db.delete(lesson)
        db.flush()

    # ---- 3. 课程先修（差集同步）----
    prerequisite_count = 0
    for item in CATALOG_COURSES:
        course = course_map[item["code"]]
        desired = {course_map[code].id for code in item["prerequisites"]}
        existing = {
            edge.prerequisite_course_id: edge
            for edge in db.scalars(
                select(CoursePrerequisite).where(
                    CoursePrerequisite.course_id == course.id
                )
            ).all()
        }
        for prerequisite_id in desired - set(existing):
            db.add(
                CoursePrerequisite(
                    course_id=course.id,
                    prerequisite_course_id=prerequisite_id,
                )
            )
            prerequisite_count += 1
        for prerequisite_id in set(existing) - desired:
            db.delete(existing[prerequisite_id])
    db.flush()

    # ---- 4. 入学知识点（差集同步，按 code 引用既有知识点）----
    kp_codes = {
        code
        for item in CATALOG_COURSES
        for code in item["required_knowledge_points"]
    }
    kp_map = {
        kp.code: kp
        for kp in db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code.in_(kp_codes))
        ).all()
    } if kp_codes else {}
    missing = sorted(kp_codes - set(kp_map))
    if missing:
        raise RuntimeError(
            "课程目录种子依赖的知识点不存在，请先执行课程内容种子："
            + "、".join(missing)
        )

    knowledge_point_link_count = 0
    for item in CATALOG_COURSES:
        course = course_map[item["code"]]
        desired = {kp_map[code].id for code in item["required_knowledge_points"]}
        existing = {
            link.knowledge_point_id: link
            for link in db.scalars(
                select(CourseKnowledgePointPrerequisite).where(
                    CourseKnowledgePointPrerequisite.course_id == course.id
                )
            ).all()
        }
        for knowledge_point_id in desired - set(existing):
            db.add(
                CourseKnowledgePointPrerequisite(
                    course_id=course.id,
                    knowledge_point_id=knowledge_point_id,
                )
            )
            knowledge_point_link_count += 1
        for knowledge_point_id in set(existing) - desired:
            db.delete(existing[knowledge_point_id])

    db.commit()
    return {
        "directions": len(DIRECTIONS),
        "courses": len(CATALOG_COURSES),
        "chapters": chapter_count,
        "lessons": lesson_count,
        "prerequisites": prerequisite_count,
        "required_knowledge_points": knowledge_point_link_count,
    }
