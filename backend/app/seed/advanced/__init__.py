"""「Python 进阶与工程实践」课程教材数据（阶段 4A）。

章节结构以课程目录（``course_catalog_seed``）为准：本包只提供教学内容、
知识点、练习与测验题，按章节拆分为多个模块便于维护。
"""

from app.seed.advanced.ch01_02 import CHAPTERS as _CH01_02
from app.seed.advanced.ch03_05 import CHAPTERS as _CH03_05
from app.seed.advanced.ch06_08 import CHAPTERS as _CH06_08
from app.seed.advanced.ch09_10 import CHAPTERS as _CH09_10

CHAPTERS: list[dict] = [*_CH01_02, *_CH03_05, *_CH06_08, *_CH09_10]

COURSE_CODE = "python-advanced"

META: dict = {
    "name": "Python 进阶与工程实践",
    "description": (
        "在掌握基础语法之后，系统补齐面向对象、继承与多态、推导式、迭代器与生成器、"
        "装饰器、上下文管理器、类型注解，以及虚拟环境、依赖管理、项目结构、日志与配置"
        "这些真实项目必备的工程能力。每节课都有完整示例代码、逐行解释、常见错误分析与"
        "分层次练习，讲清「为什么这样写」而不只是「语法怎么写」。"
    ),
    "objectives": """完成本课程后，你将能够：
1. 用类、继承、组合组织代码，写出可复用且易扩展的对象结构；
2. 用推导式、生成器与装饰器处理数据与横切逻辑；
3. 用上下文管理器保证资源释放，用类型注解与静态检查约束接口；
4. 独立搭建带虚拟环境、分层目录、日志与配置校验的 Python 项目；
5. 为后续的数据库、后端与 Agent 课程打好工程基础。""",
    "direction": "python-fundamentals",
    "difficulty": "intermediate",
    "level": "L1",
    "version": "1.0.0",
    "publish_status": "published",
    "sort_order": 2,
}


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
