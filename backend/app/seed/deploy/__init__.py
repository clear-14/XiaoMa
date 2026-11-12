"""「软件工程与项目部署」课程教材数据（阶段 4E）。

章节结构以课程目录（``course_catalog_seed``）为准：本包只提供教学内容、
知识点、练习与测验题。8 章 28 课时覆盖 Git 协作、测试工程、Docker、Compose、
配置与密钥、部署发布、日志排障与综合实战。
"""

from app.seed.deploy.ch01_02 import CHAPTERS as _CH01_02
from app.seed.deploy.ch03_04 import CHAPTERS as _CH03_04
from app.seed.deploy.ch05_06 import CHAPTERS as _CH05_06
from app.seed.deploy.ch07_08 import CHAPTERS as _CH07_08

CHAPTERS: list[dict] = [
    *_CH01_02,
    *_CH03_04,
    *_CH05_06,
    *_CH07_08,
]

COURSE_CODE = "software-engineering-deploy"

META: dict = {
    "name": "软件工程与项目部署",
    "description": (
        "把项目从本地推到线上：用 Git 完成分支协作与版本发布，用 pytest 建立可执行的 "
        "质量门禁，用 Docker 与 Compose 固化运行环境并编排前后端与数据库，按 12-Factor "
        "外置配置与密钥，通过反向代理与 HTTPS 对外提供服务，最后用日志、监控与复盘把"
        "线上问题定位在证据上。每节课都给出可直接执行的命令、真实输出与常见故障对照。"
    ),
    "objectives": """完成本课程后，你将能够：
1. 用 Git 分支与合并请求完成协作，按语义化版本发布并安全回退；
2. 用 pytest 参数化、fixture 与 mock 建立可靠的测试体系，并接入 CI 门禁；
3. 编写可复现的 Dockerfile，用多阶段构建与 .dockerignore 控制镜像体积与构建速度；
4. 用 Docker Compose 编排多服务，正确处理网络、卷与健康检查启动顺序；
5. 把配置与密钥从代码中剥离，做到加密存储、脱敏展示与可回滚轮换；
6. 配置反向代理与 HTTPS，并设计含健康检查与自动回退的发布流程；
7. 通过结构化日志与四层排障法定位线上故障，建立容量告警与上线清单。""",
    "direction": "python-backend",
    "difficulty": "intermediate",
    "level": "L2",
    "version": "1.0.0",
    # 正文写入后即可对外学习；若需人工终审，可先用 PATCH /courses/{code}/status 回退
    "publish_status": "published",
    "sort_order": 7,
}

# 教材涉及的主要工具版本，写作时统一引用
DOCKER_VERSION = "27.x"
COMPOSE_VERSION = "v2.29"
PYTEST_VERSION = "8.x"


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


def total_knowledge_points() -> int:
    return sum(
        len(lesson["knowledge_points"])
        for chapter in CHAPTERS
        for lesson in chapter["lessons"]
    )


__all__ = [
    "CHAPTERS",
    "COMPOSE_VERSION",
    "COURSE_CODE",
    "DOCKER_VERSION",
    "META",
    "PYTEST_VERSION",
    "total_exercises",
    "total_knowledge_points",
    "total_lessons",
    "total_questions",
]
