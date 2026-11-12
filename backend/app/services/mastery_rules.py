"""掌握度判定规则（纯函数，不访问数据库）。

抽出来的目的与 ``quiz_grading`` 一致：规则要能被单测直接覆盖、被审计逐条核对，
不允许在 Service 里散落一堆 if。本模块只回答三个问题：

1. 一次练习算不算通过（文本比对，不执行代码）；
2. 一次测验达到哪一档（UNDERSTOOD / APPLIED / MASTERED / NEEDS_REVIEW）；
3. 当前状态遇到这个事件之后应该是哪个状态（含「不得降级」与「必须降级」的分界）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.mastery import MASTERY_RANK, MASTERY_STATUSES
from app.services.quiz_grading import (
    MASTERY_MIN_QUESTIONS,
    MASTERY_MIN_SCORE,
    normalize_text,
)

# 练习判定：参考答案二元组覆盖率阈值。低于该值视为未通过。
# 取值理由：0.6 能放过「顺序不同、变量名不同」的等价写法，
# 又拦得住只抄了半句或答非所问；阈值写死在这里，改动必须同步测试与文档。
EXERCISE_PASS_COVERAGE = 0.6

# 诊断（跳级）测验的抽样验证要求：每个知识点至少 2 道题且全部答对。
# 低于 2 道题只能证明「基础理解」，不足以跳过。
PLACEMENT_MIN_QUESTIONS = 2

# 测验等级：掌握验证的四档结论。
QUIZ_LEVELS: tuple[str, ...] = ("mastered", "applied", "understood", "needs_review")

# 基础理解类题目（教材题的 category 取值）。
BASIC_CATEGORIES: tuple[str, ...] = ("基础理解", "代码阅读")
APPLIED_CATEGORY = "应用练习"


@dataclass
class ExerciseGrade:
    """一次练习的判定结果。"""

    result: str  # passed / failed
    coverage: float
    basis: dict = field(default_factory=dict)


def _bigrams(text: str) -> set[str]:
    """归一化后取二元组集合；单字符文本退化为自身。"""
    normalized = normalize_text(text)
    if not normalized:
        return set()
    if len(normalized) < 2:
        return {normalized}
    return {normalized[i : i + 2] for i in range(len(normalized) - 1)}


def reference_coverage(answer: str, reference: str) -> float:
    """参考答案被答案覆盖的比例（0—1）。

    用二元组而不是关键词：练习的参考答案是自由文本或代码，
    没有像测验主观题那样的 keywords 字段，二元组覆盖对「换变量名/换顺序」
    更宽容，对「只写开头一半」更严格。
    """
    reference_grams = _bigrams(reference or "")
    if not reference_grams:
        return 0.0
    answer_grams = _bigrams(answer or "")
    if not answer_grams:
        return 0.0
    matched = reference_grams & answer_grams
    return round(len(matched) / len(reference_grams), 4)


def grade_exercise_answer(reference_answer: str | None, answer: str) -> ExerciseGrade:
    """练习判定：覆盖率 ≥ 阈值即通过。

    参考答案缺失时抛 ValueError，由调用方转成 422，而不是默默判「通过」。
    """
    reference = (reference_answer or "").strip()
    if not reference:
        raise ValueError("该练习缺少参考答案，无法自动判定")
    coverage = reference_coverage(answer, reference)
    passed = coverage >= EXERCISE_PASS_COVERAGE
    return ExerciseGrade(
        result="passed" if passed else "failed",
        coverage=coverage,
        basis={
            "type": "reference_coverage",
            "reference": reference,
            "coverage": coverage,
            "threshold": EXERCISE_PASS_COVERAGE,
            "note": "按参考答案二元组覆盖率判定；V1.0 不执行用户代码",
        },
    )


def derive_quiz_level(
    answers: list[tuple[str | None, bool]],
    *,
    score: float,
    min_questions: int = MASTERY_MIN_QUESTIONS,
    allow_mastered: bool = True,
) -> str:
    """由一次测验的逐题结果推导掌握等级。

    ``answers`` 为 (题目分类, 是否答对) 列表；分类可能为空（历史内置题未回填），
    空分类按「基础理解」对待——历史题库把单/多选/判断/填空都算基础理解。

    判定顺序（严格从高到低，不跨档跳）：
    - MASTERED：题量 ≥ min_questions、全部答对、百分制 ≥ 90；
    - APPLIED：应用练习类题目存在且全部答对（题量不足时最高到这一档）；
    - UNDERSTOOD：基础理解/代码阅读类题目全部答对；
    - NEEDS_REVIEW：还有基础理解类题目答错。
    """
    if not answers:
        return "needs_review"

    def is_basic(category: str | None) -> bool:
        return not category or category in BASIC_CATEGORIES

    basic = [correct for category, correct in answers if is_basic(category)]
    applied = [
        correct for category, correct in answers if category == APPLIED_CATEGORY
    ]
    all_correct = all(correct for _, correct in answers)

    if (
        allow_mastered
        and len(answers) >= min_questions
        and all_correct
        and score >= MASTERY_MIN_SCORE
    ):
        return "mastered"
    if applied and all(applied) and all(basic):
        return "applied"
    if basic and all(basic):
        return "understood"
    if all_correct and not basic:
        # 只有应用练习类题且全对：达到应用档
        return "applied"
    return "needs_review"


def on_start(current: str) -> str:
    """开始学习：只有未开始才推进到学习中。"""
    return "learning" if current == "not_started" else current


def on_self_report(current: str) -> str:
    """用户自述完成：最多到 SELF_REPORTED_COMPLETED。

    这是需求「用户自述完成不能自动标记为 MASTERED」的唯一落点：
    无论用户怎么说，本函数不会返回 mastered。
    """
    if current in ("not_started", "learning"):
        return "self_reported_completed"
    return current


def on_exercise(current: str, *, passed: bool) -> str:
    """练习事件。

    通过：推进到 APPLIED（已 MASTERED 的不回退，掌握不会因为多练一次而降级）。
    未通过：进入 NEEDS_REVIEW；但如果当前已是 MASTERED，则保持掌握，
    只记录证据并给复习建议——单次练习失败不足以推翻一次完整掌握验证，
    正式测验失败才会降级（见 on_quiz）。
    """
    if passed:
        if current == "mastered":
            return "mastered"
        return "applied"
    if current == "mastered":
        return "mastered"
    return "needs_review"


def on_quiz(current: str, *, level: str) -> str:
    """测验事件：level 为 derive_quiz_level 的结论。

    - MASTERED / APPLIED / UNDERSTOOD 都是向上或不回退的推进；
    - NEEDS_REVIEW 是唯一允许把 MASTERED 拉下来的路径（正式验证未通过）。
    """
    if level not in QUIZ_LEVELS:
        raise ValueError(f"未知的测验等级：{level}")
    if level == "needs_review":
        return "needs_review"
    if current == "mastered":
        return "mastered"
    target_rank = MASTERY_RANK[level]
    if current == "needs_review":
        # 复习后重新验证通过：直接按本次结论落位，不走等级比较
        return level
    return level if MASTERY_RANK.get(current, 0) < target_rank else current


def is_skip_allowed(status: str) -> bool:
    """只有 MASTERED 允许跳过（需求「跳级必须通过实际掌握证据」）。"""
    return status == "mastered"


def is_valid_status(status: str) -> bool:
    return status in MASTERY_STATUSES
