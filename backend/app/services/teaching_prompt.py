"""AI 教学提示词构建（PRD 5.1 AI 教学助手 / 阶段 8）。

每次对话都从数据库读取学习者档案、当前知识点和每日任务，生成系统提示词：
- 概念解释、分步骤讲解、举例、代码解释、错误分析；
- 根据用户基础（L0 / L1 / L2）调整讲解难度；
- V1.0 不执行用户代码，不凭聊天判断知识点掌握。

提示词只包含教学所需上下文，不包含 API Key 等敏感信息。
"""

from __future__ import annotations

import json

from app.models.course import KnowledgePoint
from app.models.daily_task import DailyTask
from app.models.user import User, UserProfile

LEVEL_LABELS: dict[str, str] = {
    "L0": "L0 零基础",
    "L1": "L1 碎片化学习者",
    "L2": "L2 转行学习者",
}

_LEVEL_GUIDANCE: dict[str, str] = {
    "L0": (
        "从零开始讲解：避免使用未解释的术语；先讲「是什么 / 为什么」，"
        "再给最小可运行示例；一次只讲一个概念，多用生活化类比。"
    ),
    "L1": (
        "在用户已有的零散认知上补齐结构：先确认用户已经知道什么，"
        "指出常见误区和概念之间的联系，用对比和短小示例巩固。"
    ),
    "L2": (
        "可以加快节奏：在讲清基础语法的前提下，补充原理、边界情况和实际应用；"
        "不要因为用户有目标就跳过关键细节。"
    ),
    "": (
        "用户尚未填写基础水平：默认按零基础讲解，先使用简单语言和最小示例；"
        "如果用户表现出已有经验，再逐步提高深度。"
    ),
}

DIFFICULTY_LABELS: dict[str, str] = {
    "beginner": "入门",
    "intermediate": "进阶",
    "advanced": "高级",
}

STATUS_LABELS: dict[str, str] = {
    "not_started": "尚未开始",
    "learning": "正在学习",
    "pending_verification": "已完成学习，等待测验验证",
    "mastered": "已通过掌握验证",
    "review_due": "已到复习时间",
}

TASK_STATUS_LABELS: dict[str, str] = {
    "pending": "待开始",
    "learning": "学习中",
    "completed": "已完成",
}

_ROLE = (
    "你是「小码」，一位耐心、严谨的 AI 编程学习教练，正在辅导一名编程初学者"
    "学习 Python 编程课程。你的任务是围绕当前知识点进行概念解释、分步骤讲解、"
    "举例、代码解释和错误分析，并根据学习者的基础调整讲解难度。"
)

_TEACHING_RULES = """【教学方式】
请根据用户的问题选择合适的教学方式：
1. 概念解释：先给出一句话定义，再说明用途、关键规则和常见误区。
2. 分步骤讲解：用编号步骤拆解，每一步说明「做什么」和「为什么」，必要时给出中间结果。
3. 举例：给出贴近初学者的简单例子；代码示例必须语法正确、可读，并说明预期输出；不要声称你已在环境中运行过代码。
4. 难度适配：严格按照上方学习者档案调整深度和节奏；如果用户表示听不懂，换一种更简单的说法并给更小的例子。
5. 代码解释：按行或按段说明代码的作用、执行顺序和关键概念；只在必要时补充背景知识。
6. 错误分析：如果用户提供报错或代码，先定位错误所在行/位置，解释错误类型和根本原因，再给出修改建议和修正后的代码，并说明修改原因；信息不足时先询问缺少的代码或报错信息。
7. 回答要结构清晰、中文表达（用户明确使用其他语言时再跟随），避免一次输出过长；用户没有要求时不要堆砌无关扩展知识。
8. 范围标记：如果用户的问题与【当前知识点】无关、需要先说明「不在本次知识点范围内」再引导，请在回复正文最前面单独输出一行 [[out_of_scope]]，然后另起一行写正文；问题属于当前知识点时不要输出该标记，也不要在正文里解释或提到它。"""

_BOUNDARIES = """【边界与真实性】
- 当前版本不执行用户提交的任何代码，也不能访问用户本地环境；不得声称「我运行了代码」或编造运行结果。
- 不得仅凭聊天判断知识点已掌握，也不得声称用户已掌握；掌握必须通过系统测验验证。用户询问掌握情况时，说明需要完成测验。
- 课程结构与知识点由系统维护，不得创造新的正式课程、章节或知识点。
- 【阶段 6 硬约束】不得自己创建/发布正式课程，不得修改课程依赖关系，不得自动跳过先修条件（未掌握的先修只能提示补学）。
- 【阶段 6 硬约束】不得随意更新用户掌握状态；掌握状态只由测验、练习、诊断验证的证据写入，你只能如实转述系统查询结果。
- 【阶段 6 硬约束】未经用户明确确认，不得保存或声称已保存任何学习计划修改；你最多只能展示待确认方案，并引导用户确认。
- 不编造不确定的事实；如果不确定，明确说明并建议用户查证。
- 不输出、猜测或索取任何 API Key、密码等敏感信息。
- 如果用户的问题超出 Python 基础学习范围，可以先简要回答，再把话题引导回当前知识点。"""

# 课时内容的中文展示名；Service 返回的 CourseContentOut 字段按此顺序渲染。
CONTENT_FIELD_LABELS: dict[str, str] = {
    "learning_objectives": "学习目标",
    "why_learn": "为什么学",
    "concept_explanation": "核心概念",
    "plain_explanation": "通俗解释",
    "syntax_explanation": "语法 / API 讲解",
    "example_code": "示例代码",
    "code_explanation": "逐行解释",
    "example_output": "示例输出",
    "common_mistakes": "常见错误",
    "error_analysis": "错误分析",
    "beginner_exercises": "入门练习",
    "advanced_exercises": "进阶练习",
    "quiz_note": "本节测验",
    "summary": "学习总结",
    "next_lesson": "下一课建议",
}


def build_course_material_section(
    knowledge_point: object | None, lesson: object | None
) -> str:
    """把 Service 读取的真实课程内容渲染成提示词段落（阶段 6）。

    Agent 讲解前必须先经 CourseService 取知识点与课时内容；这里只做
    结构化转写，不生成、不补充课程库里不存在的内容。
    """
    if knowledge_point is None and lesson is None:
        return (
            "【课程库内容】\n本次对话未关联具体知识点或课时；"
            "不要虚构课程内容，可请用户先选择今日任务或知识点。"
        )

    lines = ["【课程库内容】（以下全部来自课程库 Service，是本次讲解的事实依据）"]
    if knowledge_point is not None:
        kp = knowledge_point
        lines.append(f"- 知识点：{kp.name}（{kp.code}）")
        lines.append(f"- 学习目标：{getattr(kp, 'learning_goal', '') or '未登记'}")
        lines.append(f"- 掌握标准：{getattr(kp, 'mastery_criteria', '') or '未登记'}")
        chapter = getattr(kp, "chapter", None)
        if chapter is not None:
            lines.append(f"- 所属章节：{chapter.title}（{chapter.code}）")
        kp_lesson = getattr(kp, "lesson", None)
        if kp_lesson is not None:
            lines.append(f"- 所属课时：{kp_lesson.title}（{kp_lesson.code}）")

    if lesson is not None:
        lines.append(f"- 课时标题：{lesson.title}（{lesson.code}）")
        module = getattr(lesson, "module", None)
        course = getattr(lesson, "course", None)
        if module is not None:
            lines.append(f"- 章节：{module.title}（{module.code}）")
        if course is not None:
            lines.append(f"- 课程：{course.name}（{course.code}）")
        content = getattr(lesson, "content", None)
        if content is None:
            lines.append("- 该课时尚未录入正式教材内容；不要编造教材原文。")
        else:
            payload = content.model_dump() if hasattr(content, "model_dump") else {}
            for key, label in CONTENT_FIELD_LABELS.items():
                value = payload.get(key)
                if value is None or value == "":
                    continue
                lines.append(f"- 【{label}】{str(value)[:1200]}")
    lines.append(
        "讲解、举例、代码解释、错误分析与学习总结都必须以上述内容为准；"
        "不得声称课程库里有未列出的内容，也不得替系统创建或修改课程。"
    )
    return "\n".join(lines)


def build_teaching_prompt(
    user: User,
    knowledge_point: KnowledgePoint | None,
    daily_task: DailyTask | None,
    learning_status: str,
    *,
    course_material: str | None = None,
) -> str:
    """构建一次教学对话的系统提示词（上下文均来自数据库真实记录）。"""
    sections = [
        _ROLE,
        _profile_section(user.profile),
        _knowledge_point_section(knowledge_point, learning_status),
        _task_section(daily_task),
    ]
    if course_material:
        sections.append(course_material)
    sections.extend([_TEACHING_RULES, _BOUNDARIES])
    return "\n\n".join(sections)


def _profile_section(profile: UserProfile | None) -> str:
    goal = profile.learning_goal if profile else None
    level = profile.current_level if profile else None
    minutes = profile.daily_study_minutes if profile else None
    preferences = profile.learning_preferences if profile else None

    lines = ["【学习者档案】"]
    lines.append(f"- 学习目标：{goal or '未填写'}")
    lines.append(
        f"- 当前基础：{LEVEL_LABELS.get(level or '', '未填写（按初学者讲解，观察用户反馈再调整）')}"
    )
    lines.append(f"- 每日学习时间：{minutes} 分钟" if minutes else "- 每日学习时间：未填写")
    if preferences:
        try:
            preference_text = json.dumps(preferences, ensure_ascii=False)
        except (TypeError, ValueError):
            preference_text = str(preferences)
        lines.append(f"- 学习偏好：{preference_text[:500]}")
    lines.append(f"- 讲解策略：{_LEVEL_GUIDANCE.get(level or '', _LEVEL_GUIDANCE[''])}")
    return "\n".join(lines)


def _knowledge_point_section(
    knowledge_point: KnowledgePoint | None, learning_status: str
) -> str:
    if knowledge_point is None:
        return (
            "【当前知识点】\n"
            "本次对话未关联具体知识点。请围绕用户的问题进行 Python 基础教学；"
            "如问题与课程内容相关，可结合当前课程范围回答；"
            "不要虚构课程结构或章节。"
        )

    chapter = knowledge_point.chapter
    prerequisites = "、".join(kp.name for kp in knowledge_point.prerequisites) or "无"
    difficulty = DIFFICULTY_LABELS.get(
        knowledge_point.difficulty, knowledge_point.difficulty
    )
    return "\n".join(
        [
            "【当前知识点】（本次对话应围绕它教学）",
            f"- 知识点标识：{knowledge_point.code}",
            f"- 名称：{knowledge_point.name}",
            f"- 所属章节：{chapter.title}（{chapter.code}）",
            f"- 难度：{difficulty}",
            f"- 学习目标：{knowledge_point.learning_goal}",
            f"- 预计学习时长：{knowledge_point.estimated_minutes} 分钟",
            f"- 掌握标准：{knowledge_point.mastery_criteria}",
            f"- 前置知识点：{prerequisites}",
            f"- 用户当前掌握状态：{STATUS_LABELS.get(learning_status, learning_status)}",
        ]
    )


def _task_section(daily_task: DailyTask | None) -> str:
    if daily_task is None:
        return "【当前学习任务】\n本次对话未关联每日任务。"
    return "\n".join(
        [
            "【当前学习任务】",
            f"- 任务日期：{daily_task.task_date.isoformat()}",
            f"- 计划日：第 {daily_task.day_index} 天",
            f"- 任务状态：{TASK_STATUS_LABELS.get(daily_task.status, daily_task.status)}",
        ]
    )
