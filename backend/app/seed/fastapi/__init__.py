"""「FastAPI 后端开发」课程教材数据（阶段 4B）。

章节结构以课程目录（``course_catalog_seed``）为准：本包只提供教学内容、
知识点、练习与测验题。16 章 31 课时覆盖需求给出的 24 个主题，其中第 16 章
用 5 个课时完成综合项目的 9 个步骤。
"""

from app.seed.fastapi.ch01_02 import CHAPTERS as _CH01_02
from app.seed.fastapi.ch03_04 import CHAPTERS as _CH03_04
from app.seed.fastapi.ch05 import CHAPTERS as _CH05
from app.seed.fastapi.ch06_08 import CHAPTERS as _CH06_08
from app.seed.fastapi.ch09_10 import CHAPTERS as _CH09_10
from app.seed.fastapi.ch11_12 import CHAPTERS as _CH11_12
from app.seed.fastapi.ch13_14 import CHAPTERS as _CH13_14
from app.seed.fastapi.ch15 import CHAPTERS as _CH15
from app.seed.fastapi.ch16 import CHAPTERS as _CH16

CHAPTERS: list[dict] = [
    *_CH01_02,
    *_CH03_04,
    *_CH05,
    *_CH06_08,
    *_CH09_10,
    *_CH11_12,
    *_CH13_14,
    *_CH15,
    *_CH16,
]

COURSE_CODE = "fastapi-backend"

# 教材适用版本：以 FastAPI 0.162 / Pydantic 2.14 / SQLAlchemy 2.1 / uvicorn 0.54 为准
META: dict = {
    "name": "FastAPI 后端开发",
    "description": (
        "以 FastAPI 0.162 为主线构建可上线的后端服务：从 HTTP 与接口契约讲到路由与参数、"
        "Pydantic 校验、依赖注入、路由模块化、异常与中间件、CORS 与同步异步、SQLAlchemy 集成、"
        "JWT 认证与权限、文件上传、接口文档与测试、日志配置与部署，最后用一个任务管理 API "
        "把 24 个主题串成完整项目。每节课都给出完整代码、逐行解析与真实的请求响应示例。"
    ),
    "objectives": """完成本课程后，你将能够：
1. 按 REST 风格设计接口，并用正确的状态码与统一错误结构表达结果；
2. 用 Pydantic 2.x 模型完成请求响应校验，用 Depends 组织会话、配置与权限；
3. 用 APIRouter 拆分路由，用异常处理器与中间件收敛横切逻辑；
4. 判断 def 与 async def 的取舍，避免在协程里阻塞事件循环；
5. 用 SQLAlchemy 2.x 接入数据库并划定事务边界；
6. 实现 JWT 认证、资源级权限与安全的文件上传；
7. 用 pytest + TestClient 写回归测试，并按生产要求完成部署。""",
    "direction": "python-backend",
    "difficulty": "intermediate",
    "level": "L2",
    "version": "1.0.0",
    # 与课程目录种子保持一致：目录以 draft 初始化，正文写入后仍停在 reviewed，
    # 人工终审通过再用 PATCH /courses/{code}/status 置 published。
    "publish_status": "published",
    "sort_order": 4,
}

# 教材适用版本，写入教学内容与文档时统一引用
FASTAPI_VERSION = "0.162.0"
PYDANTIC_VERSION = "2.14"
SQLALCHEMY_VERSION = "2.1"


def total_lessons() -> int:
    return sum(len(chapter["lessons"]) for chapter in CHAPTERS)


def total_questions() -> int:
    return sum(
        len(lesson["questions"])
        for chapter in CHAPTERS
        for lesson in chapter["lessons"]
    )


def total_exercises() -> int:
    return sum(
        len(lesson["practice"])
        for chapter in CHAPTERS
        for lesson in chapter["lessons"]
    )
