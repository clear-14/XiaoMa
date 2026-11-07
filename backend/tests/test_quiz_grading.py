"""评分引擎测试：七种题型、文本规范化与主观题评分依据。"""

from types import SimpleNamespace

import pytest

from app.services.quiz_grading import (
    QuestionGradingError,
    grade_answer,
    normalize_text,
)


def _question(question_type: str, answer: dict) -> SimpleNamespace:
    return SimpleNamespace(question_type=question_type, correct_answer=answer)


def test_single_choice_full_or_zero_points():
    q = _question("single_choice", {"value": "B"})
    correct = grade_answer(q, "b")
    assert correct.is_correct is True
    assert correct.score == 10
    assert correct.basis["expected"] == "B"

    wrong = grade_answer(q, "A")
    assert wrong.is_correct is False
    assert wrong.score == 0


def test_multiple_choice_requires_exact_set():
    q = _question("multiple_choice", {"values": ["A", "C"]})

    ordered = grade_answer(q, ["c", "a"])
    assert ordered.is_correct is True
    assert ordered.score == 10

    partial = grade_answer(q, ["A"])
    assert partial.is_correct is False
    assert partial.basis["missing"] == ["C"]

    extra = grade_answer(q, ["A", "C", "D"])
    assert extra.is_correct is False
    assert extra.basis["unexpected"] == ["D"]


def test_true_false_accepts_bool_and_chinese_text():
    q = _question("true_false", {"value": True})
    assert grade_answer(q, True).is_correct is True
    assert grade_answer(q, "正确").is_correct is True
    assert grade_answer(q, "false").is_correct is False
    assert grade_answer(q, "无法判断").is_correct is False


def test_fill_blank_normalizes_width_case_and_spaces():
    q = _question("fill_blank", {"values": ["Python --version"]})
    answer = grade_answer(q, " ｐｙｔｈｏｎ   --VERSION ")
    assert answer.is_correct is True
    assert answer.score == 10


def test_subjective_scores_by_keyword_coverage_and_keeps_basis():
    q = _question(
        "short_answer",
        {
            "reference": "列表可以追加元素，也可以按下标访问元素。",
            "keywords": ["追加", "下标", "元素", "列表", "访问"],
        },
    )
    full = grade_answer(q, "列表可以追加元素，也可以按下标访问元素。")
    assert full.is_correct is True
    assert full.score == 10
    assert full.basis["type"] == "keyword_rubric"
    assert full.basis["missing_keywords"] == []
    assert full.basis["reference"]

    partial = grade_answer(q, "列表可以追加元素和访问")
    assert partial.is_correct is True  # 4/5 = 80%，达到通过线
    assert partial.score == 8
    assert sorted(partial.basis["missing_keywords"]) == ["下标"]

    low = grade_answer(q, "列表可以追加")
    assert low.is_correct is False
    assert low.score == 4
    assert low.basis["matched_count"] == 2
    assert low.basis["keyword_count"] == 5
    assert 0 < low.basis["ratio"] < 0.8
    assert low.basis["note"]


def test_empty_subjective_answer_is_not_correct_even_if_keyword_is_empty_string():
    q = _question(
        "code_analysis",
        {"reference": "输出 3", "keywords": ["输出", "3", "结果"]},
    )
    result = grade_answer(q, "   ")
    assert result.is_correct is False
    assert result.score == 0


@pytest.mark.parametrize(
    "question_type, answer",
    [
        ("single_choice", {}),
        ("multiple_choice", {"values": []}),
        ("true_false", {"value": "也许"}),
        ("fill_blank", {"values": []}),
        ("short_answer", {"reference": "", "keywords": []}),
    ],
)
def test_invalid_question_configuration_raises(question_type, answer):
    with pytest.raises(QuestionGradingError):
        grade_answer(_question(question_type, answer), "答案")


def test_normalize_text_handles_fullwidth_and_case():
    assert normalize_text(" ＰＹＴＨＯＮ \n 基础 ") == "python基础"
