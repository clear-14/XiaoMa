"""测验自动评分（PRD 6.4 / 阶段 9）。

评分规则（技术决策，记录于任务书）：
- 每题满分 10 分，测验百分制得分 = 得分 / 总分 × 100；
- 单选、多选、判断、填空为客观题，全对得满分、否则 0 分；
- 简答、代码分析、代码编写为主观题，按参考答案关键词覆盖率评分
  （命中率 ≥ 80% 视为本题通过），评分依据（参考答案、命中/缺失关键词）
  随答题记录持久化；V1.0 只作文本分析，不执行用户代码；
- 知识点掌握判定不只看总分，具体条件见 QuizService。

本模块为纯函数，不访问数据库，便于自动化测试与审计。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.models.quiz import OBJECTIVE_QUESTION_TYPES

MAX_QUESTION_POINTS = 10
SUBJECTIVE_PASS_RATIO = 0.8
MASTERY_MIN_SCORE = 90.0
MASTERY_MIN_QUESTIONS = 3


@dataclass
class GradeResult:
    """一道题的评分结果；basis 为必须持久化的评分依据。"""

    score: float
    max_score: int
    is_correct: bool
    basis: dict = field(default_factory=dict)


class QuestionGradingError(ValueError):
    """题目答案配置不合法（内置题库校验或 AI 验证应提前拦截）。"""


def normalize_text(value: str) -> str:
    """统一全角/半角、大小写与空白，用于文本类答案匹配。"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).casefold())


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return ""


def _answer_value(answer: Any) -> Any:
    """兼容客户端直接传标量或传 {"value": ...} 两种形式。"""
    if isinstance(answer, dict) and len(answer) == 1 and "value" in answer:
        return answer["value"]
    return answer


def _answer_values(answer: Any) -> list[str]:
    if isinstance(answer, dict) and "values" in answer:
        raw = answer["values"]
    elif isinstance(answer, (list, tuple, set)):
        raw = list(answer)
    elif isinstance(answer, str):
        raw = re.split(r"[,，\s]+", answer.strip())
    else:
        raw = []
    return [str(item).strip() for item in raw if str(item).strip()]


def _true_false_value(answer: Any) -> bool | None:
    value = _answer_value(answer)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = normalize_text(_as_text(value))
    if text in {"true", "1", "正确", "对", "是", "yes", "t"}:
        return True
    if text in {"false", "0", "错误", "错", "否", "no", "f"}:
        return False
    return None


def _objective_basis(
    *, expected: Any, submitted: Any, note: str | None = None
) -> dict:
    basis = {"type": "objective", "expected": expected, "submitted": submitted}
    if note:
        basis["note"] = note
    return basis


def _grade_single(question, answer: Any) -> GradeResult:
    correct = question.correct_answer.get("value")
    if not isinstance(correct, str) or not correct.strip():
        raise QuestionGradingError("单选题正确答案配置无效")
    submitted = _as_text(_answer_value(answer)).strip().upper()
    is_correct = submitted == correct.strip().upper()
    return GradeResult(
        score=float(MAX_QUESTION_POINTS if is_correct else 0),
        max_score=MAX_QUESTION_POINTS,
        is_correct=is_correct,
        basis=_objective_basis(expected=correct, submitted=submitted),
    )


def _grade_multiple(question, answer: Any) -> GradeResult:
    correct_raw = question.correct_answer.get("values")
    if not isinstance(correct_raw, list) or len(correct_raw) < 2:
        raise QuestionGradingError("多选题正确答案配置无效")
    expected = sorted({str(item).strip().upper() for item in correct_raw if str(item).strip()})
    submitted = sorted({item.upper() for item in _answer_values(answer)})
    is_correct = bool(expected) and submitted == expected
    missing = sorted(set(expected) - set(submitted))
    unexpected = sorted(set(submitted) - set(expected))
    basis = _objective_basis(expected=expected, submitted=submitted)
    basis["missing"] = missing
    basis["unexpected"] = unexpected
    return GradeResult(
        score=float(MAX_QUESTION_POINTS if is_correct else 0),
        max_score=MAX_QUESTION_POINTS,
        is_correct=is_correct,
        basis=basis,
    )


def _grade_true_false(question, answer: Any) -> GradeResult:
    correct = _true_false_value(question.correct_answer.get("value"))
    if correct is None:
        raise QuestionGradingError("判断题正确答案配置无效")
    submitted = _true_false_value(answer)
    is_correct = submitted is not None and submitted == correct
    return GradeResult(
        score=float(MAX_QUESTION_POINTS if is_correct else 0),
        max_score=MAX_QUESTION_POINTS,
        is_correct=is_correct,
        basis=_objective_basis(
            expected=correct,
            submitted=submitted if submitted is not None else _as_text(answer),
        ),
    )


def _grade_fill_blank(question, answer: Any) -> GradeResult:
    correct_raw = question.correct_answer.get("values")
    if not isinstance(correct_raw, list) or not correct_raw:
        raise QuestionGradingError("填空题可接受答案配置无效")
    accepted = [str(item) for item in correct_raw if str(item).strip()]
    submitted = _as_text(_answer_value(answer))
    normalized = normalize_text(submitted)
    is_correct = bool(normalized) and any(
        normalized == normalize_text(item) for item in accepted
    )
    return GradeResult(
        score=float(MAX_QUESTION_POINTS if is_correct else 0),
        max_score=MAX_QUESTION_POINTS,
        is_correct=is_correct,
        basis=_objective_basis(expected=accepted, submitted=submitted),
    )


def _grade_subjective(question, answer: Any) -> GradeResult:
    expected = question.correct_answer or {}
    reference = str(expected.get("reference") or "").strip()
    keywords_raw = expected.get("keywords")
    if not reference or not isinstance(keywords_raw, list):
        raise QuestionGradingError("主观题参考答案或评分关键词配置无效")
    keywords = [str(item).strip() for item in keywords_raw if str(item).strip()]
    if not keywords:
        raise QuestionGradingError("主观题至少需要一个评分关键词")

    submitted = _as_text(answer)
    normalized = normalize_text(submitted)
    matched = [keyword for keyword in keywords if normalize_text(keyword) in normalized]
    missing = [keyword for keyword in keywords if keyword not in matched]
    ratio = len(matched) / len(keywords)
    score = round(MAX_QUESTION_POINTS * ratio, 1)
    is_correct = bool(normalized) and ratio >= SUBJECTIVE_PASS_RATIO
    basis = {
        "type": "keyword_rubric",
        "reference": reference,
        "keywords": keywords,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "matched_count": len(matched),
        "keyword_count": len(keywords),
        "ratio": round(ratio, 3),
        "note": "主观题按参考答案关键词覆盖自动评分；V1.0 不执行代码，评分依据仅供学习参考",
    }
    return GradeResult(
        score=score,
        max_score=MAX_QUESTION_POINTS,
        is_correct=is_correct,
        basis=basis,
    )


def grade_answer(question, answer: Any) -> GradeResult:
    """按题型评分；题目配置错误时抛出 QuestionGradingError。"""
    if question.question_type == "single_choice":
        return _grade_single(question, answer)
    if question.question_type == "multiple_choice":
        return _grade_multiple(question, answer)
    if question.question_type == "true_false":
        return _grade_true_false(question, answer)
    if question.question_type == "fill_blank":
        return _grade_fill_blank(question, answer)
    if question.question_type in OBJECTIVE_QUESTION_TYPES:
        raise QuestionGradingError("未知的客观题题型")
    return _grade_subjective(question, answer)


def is_objective(question_type: str) -> bool:
    """是否客观题（用于掌握判定与结果说明）。"""
    return question_type in OBJECTIVE_QUESTION_TYPES
