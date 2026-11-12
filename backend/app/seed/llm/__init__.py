"""「Python 大模型 API 应用开发」课程教材数据（阶段 4C）。

章节结构以课程目录（``course_catalog_seed``）为准：本包只提供教学内容、
知识点、练习与测验题。16 章 31 课时覆盖需求给出的 20 个主题，
其中第 16 章用 5 个课时完成「Python AI 对话助手」综合项目的 6 个组成部分。

教材口径：以稳定的 OpenAI 兼容调用方式（``/chat/completions`` + ``messages``）
为基础，服务商差异只作为独立示例出现，不把某家的临时参数写成通用规范。
全部示例代码通过 ``httpx`` 直接发 HTTP 请求，API Key 只从环境变量读取。
"""

from app.seed.llm.ch01_03 import CHAPTERS as _CH01_03
from app.seed.llm.ch04_06 import CHAPTERS as _CH04_06
from app.seed.llm.ch07_09 import CHAPTERS as _CH07_09
from app.seed.llm.ch10_12 import CHAPTERS as _CH10_12
from app.seed.llm.ch13_15 import CHAPTERS as _CH13_15
from app.seed.llm.ch16 import CHAPTERS as _CH16

CHAPTERS: list[dict] = [
    *_CH01_03,
    *_CH04_06,
    *_CH07_09,
    *_CH10_12,
    *_CH13_15,
    *_CH16,
]

COURSE_CODE = "llm-api"

# 教材适用版本：以 httpx 0.28 作为 HTTP 客户端，OpenAI 兼容协议以 2024 年后的
# 稳定字段（messages / choices / delta / usage / tools）为准；服务商专属参数
# 仅在「按能力开关」的示例中出现，不写成通用规范。
META: dict = {
    "name": "Python 大模型 API 应用开发",
    "description": (
        "以固定的 OpenAI 兼容调用方式为主线构建大模型应用：从 token 与采样讲到"
        "Base URL、模型名与请求响应结构，把 API Key 关进环境变量，组织 system / user / "
        "assistant 消息与稳定 Prompt，在 token 预算内维护多轮上下文，解析流式增量并透传，"
        "把输出约束成可校验的 JSON，实现函数与工具调用闭环，最后覆盖费用统计、超时重试、"
        "异常分类与提示注入防护，并用一个多轮对话助手把 20 个主题串成完整项目。"
        "每节课都给出可运行代码、逐行解析与真实的请求响应示例。"
    ),
    "objectives": """完成本课程后，你将能够：
1. 解释 token、采样与上下文窗口，判断哪些任务不该交给模型；
2. 用 httpx 调用任意 OpenAI 兼容端点，只改 Base URL 与模型名即可切换服务商；
3. 把 API Key 放进环境变量，并说明为什么它不能进代码、仓库与日志；
4. 组织 messages 与 Prompt，用示例与输出约束把结果稳定下来；
5. 在 token 预算内维护多轮上下文，实现裁剪与摘要；
6. 解析 SSE 增量并透传给前端，处理中断与结束；
7. 用 JSON 模式与校验循环拿到结构化结果；
8. 实现函数声明、工具执行与结果回填的完整闭环；
9. 统计用量与费用，处理超时、限流与各类异常；
10. 识别提示注入与越权风险，并用代码边界而非提示词来防护。""",
    "direction": "ai-llm",
    "difficulty": "intermediate",
    "level": "L1",
    "version": "1.0.0",
    # 与课程目录种子保持一致：目录以 draft 初始化，正文写入后仍停在 reviewed，
    # 人工终审通过再用 PATCH /courses/{code}/status 置 published。
    "publish_status": "published",
    "sort_order": 5,
}

# 教材适用版本，写入教学内容与文档时统一引用
HTTPX_VERSION = "0.28"
PROTOCOL_NOTE = "OpenAI 兼容协议（/chat/completions、messages、choices、delta、usage、tools）"


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
