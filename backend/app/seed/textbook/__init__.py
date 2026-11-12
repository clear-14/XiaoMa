"""Python 零基础入门教材内容包（阶段 3）。

按章分文件存放，这里统一汇总成 ``TEXTBOOK``：
每个元素是一章，章内包含课时、知识点、练习与测验题。

只存内容，不写库；写入逻辑见 ``app.seed.textbook_seed``。
"""

from app.seed.textbook.ch01_02 import CHAPTERS as _CH01_02
from app.seed.textbook.ch03_04 import CHAPTERS as _CH03_04
from app.seed.textbook.ch05_06 import CHAPTERS as _CH05_06
from app.seed.textbook.ch07_08 import CHAPTERS as _CH07_08
from app.seed.textbook.ch09_10 import CHAPTERS as _CH09_10
from app.seed.textbook.ch11_12 import CHAPTERS as _CH11_12
from app.seed.textbook.ch13_16 import CHAPTERS as _CH13_16
from app.seed.textbook.ch17_20 import CHAPTERS as _CH17_20
from app.seed.textbook.multi_choice import MULTI_CHOICE


def _with_multi_choice(chapters: list[dict]) -> list[dict]:
    """把补充的多选题挂到对应课时的题目列表末尾（不改动原列表）。"""
    merged: list[dict] = []
    for chapter in chapters:
        lessons = [
            {
                **lesson,
                "questions": [
                    *lesson["questions"],
                    *MULTI_CHOICE.get(lesson["code"], []),
                ],
            }
            for lesson in chapter["lessons"]
        ]
        merged.append({**chapter, "lessons": lessons})
    return merged


TEXTBOOK: list[dict] = _with_multi_choice(
    [
        *_CH01_02,
        *_CH03_04,
        *_CH05_06,
        *_CH07_08,
        *_CH09_10,
        *_CH11_12,
        *_CH13_16,
        *_CH17_20,
    ]
)

# 课程标识：本教材固定建设这一门课
COURSE_CODE = "python-basics"

# 教材必备的 15 个内容模块：(数据库列名, 内容数据键名, 中文名)
# 验收检查按此逐项核对，种子写入也按此映射，避免两处各写一套。
CONTENT_MODULES: tuple[tuple[str, str, str], ...] = (
    ("learning_objectives", "objectives", "学习目标"),
    ("why_learn", "why_learn", "为什么学"),
    ("concept_explanation", "concepts", "核心概念"),
    ("plain_explanation", "plain", "通俗解释"),
    ("syntax_explanation", "syntax", "语法介绍"),
    ("example_code", "example_code", "示例代码"),
    ("code_explanation", "code_lines", "逐行解释"),
    ("example_output", "output", "示例输出"),
    ("common_mistakes", "mistakes", "常见错误"),
    ("error_analysis", "error_analysis", "错误分析"),
    ("beginner_exercises", "beginner_practice", "入门练习"),
    ("advanced_exercises", "advanced_practice", "进阶练习"),
    ("quiz_note", "quiz_note", "本节测验"),
    ("summary", "summary", "学习总结"),
    ("next_lesson", "next_lesson", "下一课建议"),
)


def total_lessons() -> int:
    """教材课时总数。"""
    return sum(len(chapter["lessons"]) for chapter in TEXTBOOK)


def total_questions() -> int:
    """教材自带测验题总数。"""
    return sum(
        len(lesson["questions"])
        for chapter in TEXTBOOK
        for lesson in chapter["lessons"]
    )


def total_exercises() -> int:
    """教材练习总数。"""
    return sum(
        len(lesson["practice"])
        for chapter in TEXTBOOK
        for lesson in chapter["lessons"]
    )
