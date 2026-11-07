"""AI 变式题生成与验证（PRD 6.3 / 阶段 9）。

质量控制流程（任何一步失败都不得进入正式测验）：
1. 以一道已审核的内置题为源题，要求默认模型生成同题型的变式题；
2. 后端做确定性结构校验：题型、选项、答案结构、解析、知识点归属、难度、
   是否照抄源题、学习范围；
3. 再调用一次独立的模型校验：独立作答、检查答案正确性/解析/知识点归属/
   是否超纲；
4. 客观题要求校验模型给出的答案与待审答案一致；全部通过才以
   source=ai、validation_status=ai_validated 落库。

模型调用失败、返回非 JSON、校验不通过时降级为内置题库并返回明确说明；
不会用未验证题目组卷，也不会伪造验证成功。
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import replace
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.mixins import utc_now
from app.models.course import KnowledgePoint
from app.models.quiz import QUESTION_TYPES, Question
from app.repositories.question_repository import QuestionRepository
from app.services.llm_client import LlmError, LlmRequest, create_llm_client
from app.services.model_config_service import ModelConfigService
from app.services.quiz_grading import normalize_text

GENERATION_SYSTEM_PROMPT = """你是小码 Python 基础课程的题目生成器。
只输出一个 JSON 对象，不要 Markdown 代码围栏，不要输出 JSON 以外的文字。
禁止执行或声称执行任何代码；题目必须严格限定在给定知识点内，不得超纲。
JSON 字段：
- question_type：必须与源题完全相同
- stem：题干（中文，8-500 字）
- options：单选/多选为 [{"key":"A","text":"..."}]（2-6 个选项，key 用大写字母）；其他题型为 null
- correct_answer：
  单选 {"value":"A"}；
  多选 {"values":["A","C"]}；
  判断 {"value":true}；
  填空 {"values":["可接受答案"]}；
  简答/代码分析/代码编写 {"reference":"参考答案","keywords":["评分关键词1","评分关键词2","评分关键词3"]}
- explanation：解析（10-800 字，说明为什么答案正确）
- knowledge_point_code：必须等于给定 code
- difficulty：必须等于给定难度
变式题不得照抄源题题干，答案与解析必须自洽。"""

VERIFICATION_SYSTEM_PROMPT = """你是小码 Python 基础课程的严格题目审核员。
请独立解答题目，不要相信待审题给出的答案；禁止执行代码，只做文本分析。
检查：答案是否正确、解析是否与答案一致、知识点归属是否正确、是否超出该知识点的学习范围。
只输出一个 JSON 对象，不要 Markdown 代码围栏：
{
  "answer_correct": true/false,
  "verified_answer": 与待审题 correct_answer 同结构的独立答案,
  "explanation_ok": true/false,
  "knowledge_point_ok": true/false,
  "within_scope": true/false,
  "reason": "简短中文理由"
}"""

MAX_AI_VARIANTS = 5
AI_NOTE_LIMIT = 1000
EXPLANATION_AI = "由 AI 生成并通过结构校验与独立复核调用的变式题"


def _normalize_stem(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().casefold())


def _extract_json(text: str) -> dict | None:
    """从模型输出中提取第一个 JSON 对象，容忍代码围栏与前后说明文字。"""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _clean_options(raw: Any) -> list[dict[str, str]] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip().upper()
        text = str(item.get("text") or "").strip()
        if key and text:
            cleaned.append({"key": key, "text": text})
    return cleaned


def validate_generated_payload(
    payload: dict, knowledge_point: KnowledgePoint, source: Question
) -> list[str]:
    """确定性校验 AI 题目结构；返回问题列表，空列表表示通过。"""
    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["题目不是 JSON 对象"]

    question_type = str(payload.get("question_type") or "").strip()
    if question_type not in QUESTION_TYPES:
        issues.append("题型不合法")
    elif question_type != source.question_type:
        issues.append("变式题题型必须与源题一致")

    stem = str(payload.get("stem") or "").strip()
    if len(stem) < 8 or len(stem) > 1000:
        issues.append("题干长度必须在 8-1000 字之间")
    if stem and _normalize_stem(stem) == _normalize_stem(source.stem):
        issues.append("变式题不能照抄源题题干")

    explanation = str(payload.get("explanation") or "").strip()
    if len(explanation) < 10 or len(explanation) > 2000:
        issues.append("解析长度必须在 10-2000 字之间")

    if payload.get("knowledge_point_code") != knowledge_point.code:
        issues.append("知识点归属与请求范围不一致")
    if payload.get("difficulty") != knowledge_point.difficulty:
        issues.append("题目难度与知识点难度不一致")

    options = _clean_options(payload.get("options"))
    answer = payload.get("correct_answer")
    if not isinstance(answer, dict):
        issues.append("正确答案必须是 JSON 对象")
        return issues

    if question_type in ("single_choice", "multiple_choice"):
        if not options or len(options) < 2 or len(options) > 6:
            issues.append("选择题必须有 2-6 个选项")
        keys = [item["key"] for item in options or []]
        if len(keys) != len(set(keys)):
            issues.append("选项 key 不能重复")
        for item in options or []:
            if len(item["text"]) > 500:
                issues.append("选项内容不能超过 500 字")
        if question_type == "single_choice":
            value = answer.get("value")
            if not isinstance(value, str) or value.strip().upper() not in keys:
                issues.append("单选题答案必须是存在的选项 key")
        else:
            values = answer.get("values")
            if not isinstance(values, list) or len(values) < 2:
                issues.append("多选题答案至少需要两个选项")
            elif len({str(v).strip().upper() for v in values}) != len(values):
                issues.append("多选题答案不能重复")
            elif any(str(v).strip().upper() not in keys for v in values):
                issues.append("多选题答案包含不存在的选项")
    elif question_type == "true_false":
        if not isinstance(answer.get("value"), bool):
            issues.append("判断题答案必须是 true 或 false")
        if options:
            issues.append("判断题不应提供选项")
    elif question_type == "fill_blank":
        values = answer.get("values")
        if not isinstance(values, list) or not values:
            issues.append("填空题必须至少提供一个可接受答案")
        elif len(values) > 5 or any(not str(v).strip() for v in values):
            issues.append("填空题可接受答案不合法")
        if options:
            issues.append("填空题不应提供选项")
    else:
        reference = str(answer.get("reference") or "").strip()
        keywords = answer.get("keywords")
        if len(reference) < 5:
            issues.append("主观题参考答案不能为空且至少 5 字")
        if not isinstance(keywords, list) or not 3 <= len(keywords) <= 8:
            issues.append("主观题评分关键词需要 3-8 个")
        else:
            cleaned_keywords = [str(item).strip() for item in keywords]
            if any(not item for item in cleaned_keywords):
                issues.append("主观题评分关键词不能为空")
            if len(set(cleaned_keywords)) != len(cleaned_keywords):
                issues.append("主观题评分关键词不能重复")
        if options:
            issues.append("主观题不应提供选项")

    return issues


def _answer_equivalent(question_type: str, candidate: dict, verified: Any) -> bool:
    """比较待审答案与独立校验模型答案（容错大小写/空白）。"""
    if not isinstance(verified, dict):
        return False
    if question_type == "single_choice":
        left = normalize_text(str(candidate.get("value") or ""))
        right = normalize_text(str(verified.get("value") or ""))
        return bool(left) and left == right
    if question_type == "multiple_choice":
        left = {normalize_text(str(v)) for v in candidate.get("values") or []}
        right = {normalize_text(str(v)) for v in verified.get("values") or []}
        return bool(left) and left == right
    if question_type == "true_false":
        return (
            isinstance(candidate.get("value"), bool)
            and isinstance(verified.get("value"), bool)
            and verified.get("value") == candidate.get("value")
        )
    if question_type == "fill_blank":
        accepted = {normalize_text(str(v)) for v in candidate.get("values") or []}
        raw = verified.get("values")
        if not isinstance(raw, list):
            raw = [verified.get("value")]
        submitted = {normalize_text(str(v)) for v in raw if v is not None}
        return bool(accepted & submitted)
    # 主观题：由独立校验模型给出答案正确性判断，并要求其提供非空答案/参考
    reference = str(verified.get("reference") or "").strip()
    return bool(reference)


class AiQuestionService:
    """AI 变式题生成器；所有模型输出都视为不可信，必须经过校验。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.question_repo = QuestionRepository(db)
        self.model_config_service = ModelConfigService(db)

    async def generate_variants(
        self, sources: list[Question], count: int
    ) -> tuple[list[Question], str | None]:
        """生成并验证至多 count 道变式题；失败时返回降级说明而非抛错。"""
        if count <= 0:
            return [], None
        requested = min(count, MAX_AI_VARIANTS)
        try:
            llm_request, model_name = self.model_config_service.get_default_llm_request()
        except HTTPException as exc:
            return [], f"未配置默认模型，已仅使用内置题库（{exc.detail}）"

        # 优先选择客观题作为源题：独立验证可以直接比对答案，质量控制更可靠。
        ordered = sorted(
            sources,
            key=lambda item: (
                0 if item.question_type in ("single_choice", "multiple_choice", "true_false", "fill_blank") else 1,
                item.code,
            ),
        )
        accepted: list[Question] = []
        failures: list[str] = []
        seen_kps: set[uuid.UUID] = set()
        for source in ordered:
            if len(accepted) + len(failures) >= requested:
                break
            # 尽量覆盖不同知识点；同知识点只有在题目数量不足时才重复使用源题
            if source.knowledge_point_id in seen_kps and len(seen_kps) < requested:
                continue
            seen_kps.add(source.knowledge_point_id)
            try:
                payload = await self._generate_payload(source, llm_request)
            except LlmError as exc:
                failures.append(f"{source.code}：{exc.message}")
                continue
            knowledge_point = source.knowledge_point
            issues = validate_generated_payload(payload, knowledge_point, source)
            if issues:
                failures.append(f"{source.code}：结构校验未通过（{'；'.join(issues)}）")
                continue
            try:
                verdict = await self._verify_payload(payload, knowledge_point, llm_request)
            except LlmError as exc:
                failures.append(f"{source.code}：独立复核调用失败（{exc.message}）")
                continue
            reasons = self._verification_reasons(payload, verdict)
            if reasons:
                failures.append(f"{source.code}：独立复核未通过（{'；'.join(reasons)}）")
                continue

            question = self._build_question(
                payload, source, knowledge_point, model_name, verdict
            )
            self.question_repo.add(question)
            accepted.append(question)

        if accepted:
            self.question_repo.flush()

        parts: list[str] = []
        if accepted:
            parts.append(f"AI 变式题：请求 {requested} 道，通过验证 {len(accepted)} 道")
        else:
            parts.append(f"AI 变式题：请求 {requested} 道，没有题目通过验证，已使用内置题库")
        if failures:
            parts.append("未通过：" + "；".join(failures))
        note = "。".join(parts)
        return accepted, note[:AI_NOTE_LIMIT]

    async def _generate_payload(
        self, source: Question, llm_request: LlmRequest
    ) -> dict:
        knowledge_point = source.knowledge_point
        source_payload = {
            "question_type": source.question_type,
            "stem": source.stem,
            "options": source.options,
            "correct_answer": source.correct_answer,
            "explanation": source.explanation,
            "difficulty": source.difficulty,
        }
        user_prompt = (
            f"知识点 code：{knowledge_point.code}\n"
            f"知识点名称：{knowledge_point.name}\n"
            f"学习目标：{knowledge_point.learning_goal}\n"
            f"掌握标准：{knowledge_point.mastery_criteria}\n"
            f"难度：{knowledge_point.difficulty}\n"
            f"章节：{knowledge_point.chapter.title}\n\n"
            "源题（仅供理解考点，不得照抄）：\n"
            f"{json.dumps(source_payload, ensure_ascii=False)}\n\n"
            "请生成一道同题型、同知识点的变式题，严格按系统要求输出 JSON。"
        )
        text = await self._call_llm(
            llm_request,
            [
                {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        payload = _extract_json(text)
        if payload is None:
            raise LlmError("模型没有返回可解析的题目 JSON")
        return payload

    async def _verify_payload(
        self,
        payload: dict,
        knowledge_point: KnowledgePoint,
        llm_request: LlmRequest,
    ) -> dict:
        user_prompt = (
            f"知识点 code：{knowledge_point.code}\n"
            f"知识点名称：{knowledge_point.name}\n"
            f"学习目标：{knowledge_point.learning_goal}\n"
            f"掌握标准：{knowledge_point.mastery_criteria}\n"
            f"难度：{knowledge_point.difficulty}\n\n"
            "待审题目：\n"
            f"{json.dumps(payload, ensure_ascii=False)}\n\n"
            "请独立完成审核并输出 JSON。"
        )
        text = await self._call_llm(
            llm_request,
            [
                {"role": "system", "content": VERIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        verdict = _extract_json(text)
        if verdict is None:
            raise LlmError("独立复核没有返回可解析的 JSON")
        return verdict

    @staticmethod
    def _verification_reasons(payload: dict, verdict: dict) -> list[str]:
        reasons: list[str] = []
        for field, label in (
            ("answer_correct", "答案不正确"),
            ("explanation_ok", "解析与答案不一致"),
            ("knowledge_point_ok", "知识点归属不正确"),
            ("within_scope", "超出知识点学习范围"),
        ):
            if verdict.get(field) is not True:
                reasons.append(label)
        if not _answer_equivalent(
            str(payload.get("question_type")),
            payload.get("correct_answer") or {},
            verdict.get("verified_answer"),
        ):
            reasons.append("独立作答与给定答案不一致")
        reason = str(verdict.get("reason") or "").strip()
        if reason and reasons:
            reasons.append(reason[:200])
        return reasons

    def _build_question(
        self,
        payload: dict,
        source: Question,
        knowledge_point: KnowledgePoint,
        model_name: str,
        verdict: dict,
    ) -> Question:
        reason = str(verdict.get("reason") or "").strip() or "独立复核通过"
        now: datetime = utc_now()
        return Question(
            code=f"ai-{uuid.uuid4().hex[:24]}",
            knowledge_point_id=knowledge_point.id,
            knowledge_point=knowledge_point,
            question_type=str(payload["question_type"]),
            stem=str(payload["stem"]).strip(),
            options=_clean_options(payload.get("options")),
            correct_answer=payload["correct_answer"],
            explanation=str(payload["explanation"]).strip(),
            difficulty=knowledge_point.difficulty,
            source="ai",
            status="approved",
            validation_status="ai_validated",
            validation_notes=(
                f"{EXPLANATION_AI}；生成模型：{model_name}；复核结论：{reason}"
            )[:2000],
            generated_from_id=source.id,
            validated_at=now,
        )

    @staticmethod
    async def _call_llm(llm_request: LlmRequest, messages: list[dict[str, str]]) -> str:
        # 变式题生成需要比「连接测试」更长的输出；在用户配置基础上放宽到 1024，
        # 温度降低以提高结构化输出与答案自洽性。
        request = replace(
            llm_request,
            temperature=0.2,
            max_tokens=max(1024, min(llm_request.max_tokens, 2048)),
        )
        client = create_llm_client(request)
        parts: list[str] = []
        async for delta in client.stream(messages):
            parts.append(delta)
        return "".join(parts)
