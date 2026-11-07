"""学习计划排期算法与计划结构校验（后端权威规则）。

排期规则（确定性算法，AI 辅助分析接入前的基础实现）：
- 输入：课程知识点（按课程顺序）、已掌握知识点、每日学习分钟数；
- 按课程顺序依次把知识点装入「天」：当天已排分钟数 + 知识点预计分钟数
  超过每日时长时，知识点排入下一天；单知识点预计时长超过每日时长时
  独自占满一天（不拆分知识点）；
- 已掌握知识点不安排。

结构校验规则（任务书要求后端必须校验课程知识点、前置依赖和计划结构）：
- 计划中的每个知识点必须属于课程且不重复；
- 每个被安排知识点的前置知识点，要么在已掌握列表中，要么排在更早的天
  （同天允许，但须在课程顺序上更靠前）。
"""

from app.models.course import KnowledgePoint


def build_schedule(
    ordered_kps: list[KnowledgePoint], mastered_codes: set[str], daily_minutes: int
) -> list[tuple[KnowledgePoint, int]]:
    """按每日时长排期，返回 [(知识点, day_index)]（day_index 从 1 开始）。

    mastered_codes 为「已知知识点」稳定 code 集合（诊断已掌握 ∪ 已完成），
    不再安排这些知识点。
    """
    schedule: list[tuple[KnowledgePoint, int]] = []
    day = 1
    day_total = 0
    for kp in ordered_kps:
        if kp.code in mastered_codes:
            continue
        if day_total > 0 and day_total + kp.estimated_minutes > daily_minutes:
            day += 1
            day_total = 0
        schedule.append((kp, day))
        day_total += kp.estimated_minutes
    return schedule


def computed_duration_days(schedule: list[tuple[KnowledgePoint, int]]) -> int:
    """排期实际总天数（无安排时为 0）。"""
    return max((day for _, day in schedule), default=0)


def validate_schedule(
    schedule: list[tuple[KnowledgePoint, int]],
    course_kps_by_code: dict[str, KnowledgePoint],
    mastered_codes: set[str],
    order_position: dict[str, int],
) -> None:
    """校验计划结构，违反规则时抛出 ValueError（消息可直接返回给用户）。

    - 知识点必须属于课程、不重复安排；
    - 前置依赖：前置知识点必须在已知集合（已掌握/已完成）中，或排在更早的天
      （同天允许，但前置知识点须在课程顺序上更靠前）。
    """
    day_by_code: dict[str, int] = {}
    for kp, day in schedule:
        if kp.code not in course_kps_by_code:
            raise ValueError(f"知识点 {kp.code} 不属于该课程")
        if kp.code in day_by_code:
            raise ValueError(f"知识点 {kp.code} 被重复安排")
        if day < 1:
            raise ValueError(f"知识点 {kp.code} 的 day_index 必须从 1 开始")
        day_by_code[kp.code] = day

    for kp, day in schedule:
        for prereq in kp.prerequisites:
            if prereq.code in mastered_codes:
                continue
            if prereq.code not in day_by_code:
                raise ValueError(
                    f"知识点 {kp.code} 的前置知识点 {prereq.code} 未安排在计划中"
                )
            prereq_day = day_by_code[prereq.code]
            if prereq_day > day or (
                prereq_day == day and order_position[prereq.code] >= order_position[kp.code]
            ):
                raise ValueError(
                    f"知识点 {kp.code} 排在第 {day} 天，"
                    f"但其前置知识点 {prereq.code} 排在第 {prereq_day} 天"
                    "（或同天但在课程顺序上更靠后）"
                )
