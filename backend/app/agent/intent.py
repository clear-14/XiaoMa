"""主 Agent 意图识别（阶段 10）。

使用确定性的关键词/句式规则识别常见学习意图，不额外调用模型：
- 规则可解释、可测试，不会因模型幻觉把用户路由到错误子图；
- 未命中任何规则时回退到 Teaching（普通提问/讲解），由教学子图回答；
- 识别结果只决定路由，不修改任何业务数据。
"""

from __future__ import annotations

import re

from app.agent.contracts import IntentResult

_PLAN_ADJUST_WORDS: tuple[str, ...] = (
    "调整",
    "修改",
    "变更",
    "改成",
    "改一下",
    "太紧",
    "太松",
    "太快",
    "太慢",
    "太难",
    "太简单",
)

_REVIEW_WORDS: tuple[str, ...] = (
    "错题",
    "复习",
    "做错",
    "答错",
    "错误分析",
    "错在哪里",
)

_QUIZ_WORDS: tuple[str, ...] = (
    "测验",
    "测试",
    "出题",
    "组卷",
    "考考我",
    "做题",
    "考题",
    "来几道题",
)

_PROGRESS_WORDS: tuple[str, ...] = (
    "学习进度",
    "进度",
    "学到哪",
    "学习情况",
    "完成情况",
    "掌握情况",
    "学习统计",
    "学了多少",
)

_RESOURCE_WORDS: tuple[str, ...] = (
    "学习资源",
    "资料",
    "教程",
    "学习材料",
    "参考书",
    "参考链接",
)

_RESOURCE_PATTERN = re.compile(r"推荐.{0,8}(?:书|网站|课程|链接|资料)")

_TODAY_PATTERN = re.compile(
    r"(?:今天|今日|现在|接下来|下一步|明天)[^。！？\n]{0,8}"
    r"(?:学什么|学啥|学习什么|该学|做什么|任务|安排)"
)
_WHAT_TO_LEARN_PATTERN = re.compile(
    r"(?:我|接下来|下一步)(?:今天|现在|接下来|下一步)?(?:应该|该)?学(?:什么|啥)"
)
_QUIZ_HISTORY_WORDS: tuple[str, ...] = ("记录", "历史")
# 批次 8：问「成绩 / 得分」是要看最近一次已提交测验的结果，不是列表统计。
_QUIZ_RESULT_WORDS: tuple[str, ...] = (
    "成绩",
    "得分",
    "分数",
    "测验结果",
    "考了多少",
    "得了多少分",
    "对了几道",
    "错了几道",
    "上次测验",
)
_PLAN_WORDS: tuple[str, ...] = ("学习计划", "计划", "安排")


def recognize_intent(message: str) -> IntentResult:
    """识别一条用户消息对应的子图与子意图。"""
    text = (message or "").strip()

    # 1. 调整学习计划（必须在一般「计划」之前判断）
    if any(word in text for word in _PLAN_WORDS) and any(
        word in text for word in _PLAN_ADJUST_WORDS
    ):
        matched = [
            word
            for word in (*_PLAN_WORDS, *_PLAN_ADJUST_WORDS)
            if word in text
        ]
        return IntentResult(
            intent="planning",
            sub_intent="adjust_plan",
            confidence=0.92,
            matched_keywords=_unique(matched),
            reason="用户希望调整学习计划参数",
        )

    # 2. 错题/复习（优先于普通教学与测验）
    review_matches = [word for word in _REVIEW_WORDS if word in text]
    if review_matches:
        return IntentResult(
            intent="review",
            sub_intent="analyze_mistakes",
            confidence=0.9,
            matched_keywords=review_matches,
            reason="用户询问错题或复习安排",
        )

    # 3. 测验：查看最近一次结果 / 生成新测验 / 查看测验记录
    quiz_matches = [word for word in _QUIZ_WORDS if word in text]
    result_matches = [word for word in _QUIZ_RESULT_WORDS if word in text]
    # 「成绩 / 得分 / 对了几道」本身已指向一次测验的结果，不必再出现「测验」二字；
    # 但「分数」在数学语境里另有含义（如小数、分数类型），必须与测验词同时出现，
    # 避免把「讲讲分数和小数的区别」这类教学问题路由到测验子图。
    result_is_quizish = any(word != "分数" for word in result_matches)
    if result_matches and (quiz_matches or result_is_quizish):
        return IntentResult(
            intent="quiz",
            sub_intent="quiz_result",
            confidence=0.88,
            matched_keywords=_unique([*quiz_matches, *result_matches]),
            reason="用户查看最近一次测验的得分与答题结果",
        )
    if quiz_matches:
        is_history = any(word in text for word in _QUIZ_HISTORY_WORDS)
        return IntentResult(
            intent="quiz",
            sub_intent="quiz_history" if is_history else "generate_quiz",
            confidence=0.9,
            matched_keywords=_unique([*quiz_matches, *(
                [word for word in _QUIZ_HISTORY_WORDS if word in text]
                if is_history
                else []
            )]),
            reason="用户查看测验记录" if is_history else "用户希望生成一次测验",
        )

    # 4. 学习进度
    progress_matches = [word for word in _PROGRESS_WORDS if word in text]
    if progress_matches:
        return IntentResult(
            intent="planning",
            sub_intent="progress",
            confidence=0.88,
            matched_keywords=progress_matches,
            reason="用户查看学习进度",
        )

    # 5. 学习资源
    resource_matches = [word for word in _RESOURCE_WORDS if word in text]
    resource_pattern_match = _RESOURCE_PATTERN.search(text)
    if resource_matches or resource_pattern_match:
        matched = list(resource_matches)
        if resource_pattern_match:
            matched.append(resource_pattern_match.group(0))
        return IntentResult(
            intent="resource",
            sub_intent="search_resources",
            confidence=0.86,
            matched_keywords=_unique(matched),
            reason="用户查找学习资源",
        )

    # 6. 今天/下一步学什么
    if _TODAY_PATTERN.search(text) or _WHAT_TO_LEARN_PATTERN.search(text):
        return IntentResult(
            intent="planning",
            sub_intent="today_tasks",
            confidence=0.9,
            matched_keywords=["今天/下一步学习任务"],
            reason="用户询问今天或下一步的学习安排",
        )

    # 7. 查看学习计划（非调整）
    if any(word in text for word in ("学习计划", "计划")):
        return IntentResult(
            intent="planning",
            sub_intent="plan_overview",
            confidence=0.8,
            matched_keywords=[word for word in ("学习计划", "计划") if word in text],
            reason="用户查看当前学习计划",
        )

    # 8. 兜底：普通教学/答疑
    return IntentResult(
        intent="teaching",
        sub_intent="teach",
        confidence=0.35,
        matched_keywords=[],
        reason="未命中计划/测验/错题/进度/资源规则，按教学问题处理",
    )


def _unique(items: list[str]) -> list[str]:
    """去重并保持原顺序。"""
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
