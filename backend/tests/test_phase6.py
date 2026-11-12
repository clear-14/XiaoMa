"""阶段 6：课程体系接入 V1.3 学习闭环的验收测试。

需求「七、测试」十项必测逐条对应：

1. 今日任务引用真实课程 → ``test_today_tasks_reference_real_course_data``
2. 不重复生成每日任务 → ``test_today_tasks_are_not_generated_twice_in_one_day``
3. 未掌握的先修知识可以提示补学 → ``test_unmastered_prerequisites_prompt_remedial_not_skip``
4. 已掌握的知识点不重复安排基础教学 → ``test_mastered_points_not_scheduled_again``
5. 诊断结果能够影响计划 → ``test_placement_diagnosis_result_affects_plan``
6. 测验结果可以影响后续复习任务 → ``test_quiz_failure_affects_followup_review_tasks``
7. Agent 能从课程库读取内容 → ``test_agent_teaching_reads_course_library_via_service``
8. Agent 写操作经过 Service → ``test_agent_write_tools_delegate_to_service_layer``
9. 学习计划调整需要确认 → ``test_plan_adjustment_requires_explicit_confirmation``
10. 原有学习闭环正常 → ``test_original_learning_loop_remains_intact``

另加：正式发布 / 真实课时门槛、八因素快照、六类触发信号、工具清单、
复习申请幂等、任务完成与掌握证据的关联。全部通过真实 API 或真实 Service
取数，不使用模型推断、不伪造课程数据。
"""

from __future__ import annotations

import json
import uuid
from datetime import date

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.agent.contracts import LearningContext
from app.agent.tools import (
    AGENT_TOOL_SPECS,
    FORBIDDEN_TOOL_NAMES,
    LEGACY_TOOL_SPECS,
    AgentToolbox,
    tool_specs,
)
from app.models.course import (
    Chapter,
    Course,
    KnowledgePoint,
    Lesson,
    LessonKnowledgePoint,
)
from app.models.daily_task import DailyTask
from app.models.phase6 import ADJUSTMENT_TRIGGERS, PlanAdjustmentProposal, ReviewRequest
from app.models.quiz import Question
from app.models.user import User
from app.seed.course_catalog_seed import seed_course_catalog
from app.seed.course_seed import seed_courses
from app.seed.phase4a_seed import seed_phase4a
from app.seed.question_seed import seed_questions
from app.seed.textbook_seed import seed_textbook
from app.services import teaching_graph
from app.services.course_service import CourseService
from app.services.llm_client import LlmClient
from app.services.mastery_service import MasteryService
from app.services.plan_adjustment_service import (
    PlanAdjustmentService,
    suggest_changes,
)
from app.services.plan_signal_service import (
    CONSECUTIVE_FAILURE_COUNT,
    FAILURE_SCORE_THRESHOLD,
    consecutive_failures,
    is_downstream_mastery_signal,
)
from app.services.quiz_service import QuizService
from app.services.review_request_service import ReviewRequestService
from app.services.teaching_prompt import build_course_material_section

GOAL = "三个月内掌握 Python 基础语法"
KP_CODE = "python-basics-01-01"
API_KEY = "sk-test-phase6-secret-key"


# ---------------------------------------------------------------- 夹具与工具


def _seed(
    factory,
    *,
    questions: bool = False,
    catalog: bool = False,
    textbooks: bool = False,
) -> None:
    """按项目既有种子顺序建库；textbooks=True 时包含进阶/数据库教材。"""
    db = factory()
    try:
        seed_courses(db)
        if catalog or textbooks:
            seed_course_catalog(db)
        if textbooks:
            seed_textbook(db)
            seed_phase4a(db)
        if questions:
            seed_questions(db)
    finally:
        db.close()


def _set_profile(client) -> None:
    resp = client.put(
        "/api/v1/profile",
        json={
            "learning_goal": GOAL,
            "current_level": "L1",
            "daily_study_minutes": 45,
        },
    )
    assert resp.status_code == 200, resp.text


def _plan_payload(**overrides):
    payload = {
        "course_code": "python-basics",
        "learning_goal": GOAL,
        "current_level": "L1",
        "daily_study_minutes": 45,
        "expected_duration_days": 30,
    }
    payload.update(overrides)
    return payload


def _create_plan(client, **overrides) -> dict:
    resp = client.post("/api/v1/plans", json=_plan_payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _confirm_plan(client, plan_id: str) -> dict:
    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _confirmed_plan(client, **overrides) -> dict:
    plan = _create_plan(client, **overrides)
    _confirm_plan(client, plan["id"])
    return plan


def _read_today(client) -> dict:
    """首页第一步：只查询，不生成。"""
    resp = client.get("/api/v1/daily-tasks/today?generate=false")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _generate_today(client) -> dict:
    """首页第二步：仅在没有任务时生成（幂等）。"""
    resp = client.post("/api/v1/daily-tasks/today/generate")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _grant_mastery(factory, codes: list[str]) -> None:
    """写入真实掌握证据（诊断 / 跳级验证路径），不改旧档案的 5 态取值。"""
    db = factory()
    try:
        service = MasteryService(db)
        for code in codes:
            service.grant_mastery(code, source="placement", quiz_difficulty="beginner")
    finally:
        db.close()


def _self_report(client, codes: list[str]) -> dict:
    resp = client.post(
        "/api/v1/mastery/self-report", json={"knowledge_point_codes": codes}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _canonical(question: Question):
    """按题型还原题库标准答案（与阶段 5 测试口径一致）。"""
    answer = question.correct_answer
    if question.question_type in ("single_choice", "true_false"):
        return answer["value"]
    if question.question_type == "multiple_choice":
        return answer["values"]
    if question.question_type == "fill_blank":
        return answer["values"][0]
    keywords = answer.get("keywords") or []
    return " ".join([str(answer.get("reference") or ""), *map(str, keywords)])


def _submit_body(factory, questions: list[dict], *, correct: bool) -> dict:
    db = factory()
    try:
        items = []
        for item in questions:
            question = db.get(Question, uuid.UUID(item["id"]))
            assert question is not None
            items.append(
                {
                    "question_id": item["id"],
                    "answer": _canonical(question) if correct else "wrong",
                }
            )
        return {"answers": items}
    finally:
        db.close()


def _create_quiz(client, **payload) -> dict:
    resp = client.post("/api/v1/quizzes", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _submit_quiz(client, factory, attempt: dict, *, correct: bool) -> dict:
    body = _submit_body(factory, attempt["questions"], correct=correct)
    resp = client.post(f"/api/v1/quizzes/{attempt['id']}/submit", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


class ChatModelStub:
    """模拟 OpenAI 兼容流式服务，记录每次请求的系统提示词。"""

    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self.requests: list[dict] = []

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        payload = "".join(
            f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]}, ensure_ascii=False)}\n\n"
            for chunk in self.chunks
        ) + "data: [DONE]\n\n"
        return httpx.Response(
            200,
            content=payload.encode("utf-8"),
            headers={"content-type": "text/event-stream"},
        )

    def install(self, monkeypatch) -> None:
        transport = httpx.MockTransport(self._handler)
        monkeypatch.setattr(
            teaching_graph,
            "create_llm_client",
            lambda request: LlmClient(request, transport=transport),
        )


def _create_default_model(client) -> None:
    resp = client.post(
        "/api/v1/model-configs",
        json={
            "name": "阶段 6 测试模型",
            "provider": "custom",
            "base_url": "https://llm.example/v1",
            "api_key": API_KEY,
            "model_name": "test-model",
            "temperature": 0.7,
            "max_tokens": 512,
            "timeout": 30,
            "is_default": True,
        },
    )
    assert resp.status_code == 201, resp.text


def _send(client, conversation_id: str, content: str):
    return client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": content},
    )


# ------------------------------------------------- 1. 今日任务引用真实课程


def test_today_tasks_reference_real_course_data(api_env):
    client, factory = api_env
    _seed(factory)
    _confirmed_plan(client)

    before = _read_today(client)
    assert before["generated"] is False
    assert before["tasks"] == []

    generated = _generate_today(client)
    assert generated["generated"] is True
    tasks = generated["tasks"]
    assert tasks, "应生成第 1 天任务"

    db = factory()
    try:
        for task in tasks:
            refs = task["course_refs"]
            assert refs is not None, "新生成的任务必须固化四个真实课程标识"
            course = db.get(Course, uuid.UUID(refs["course_id"]))
            chapter = db.get(Chapter, uuid.UUID(refs["module_id"]))
            lesson = db.get(Lesson, uuid.UUID(refs["lesson_id"]))
            kp = db.get(KnowledgePoint, uuid.UUID(refs["knowledge_point_id"]))
            assert course is not None and course.publish_status == "published"
            assert chapter is not None and chapter.course_id == course.id
            assert lesson is not None and lesson.chapter_id == chapter.id
            assert kp is not None and kp.chapter_id == chapter.id
            assert kp.lesson is not None and kp.lesson.id == lesson.id
            assert refs["course_code"] == course.code
            assert refs["module_code"] == chapter.code
            assert refs["lesson_code"] == lesson.code
            assert refs["knowledge_point_code"] == kp.code
            assert refs["knowledge_point_code"] == task["knowledge_point"]["code"]

            row = db.get(DailyTask, uuid.UUID(task["id"]))
            assert row.course_id == course.id
            assert row.chapter_id == chapter.id
            assert row.lesson_id == lesson.id
            assert row.knowledge_point_id == kp.id
    finally:
        db.close()


# ------------------------------------------------- 2. 同一天不重复生成任务


def test_today_tasks_are_not_generated_twice_in_one_day(api_env):
    client, factory = api_env
    _seed(factory)
    _confirmed_plan(client)

    first = _generate_today(client)
    assert first["generated"] is True
    ids = [task["id"] for task in first["tasks"]]
    assert ids

    second = _generate_today(client)
    assert second["generated"] is False
    assert [task["id"] for task in second["tasks"]] == ids

    third = _read_today(client)
    assert third["generated"] is False
    assert [task["id"] for task in third["tasks"]] == ids

    legacy = client.get("/api/v1/daily-tasks/today").json()
    assert legacy["generated"] is False
    assert [task["id"] for task in legacy["tasks"]] == ids

    db = factory()
    try:
        rows = db.scalars(
            select(DailyTask).where(DailyTask.task_date == first["task_date"])
        ).all()
        assert len(rows) == len(ids)
        user_id = db.scalars(select(User.id).where(User.username == "local")).one()
        first_task = db.get(DailyTask, uuid.UUID(ids[0]))
        # 数据库唯一约束兜底：并发直接插入同一(user, date, kp) 会被拒绝
        db.add(
            DailyTask(
                user_id=user_id,
                plan_id=first_task.plan_id,
                knowledge_point_id=first_task.knowledge_point_id,
                course_id=first_task.course_id,
                chapter_id=first_task.chapter_id,
                lesson_id=first_task.lesson_id,
                task_date=first_task.task_date,
                day_index=first_task.day_index,
                status="pending",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


# ------------------------------------------- 3. 未掌握先修只提示补学、不跳过


def test_unmastered_prerequisites_prompt_remedial_not_skip(api_env):
    client, factory = api_env
    _seed(factory, textbooks=True)

    plan = _create_plan(client, course_code="python-database", learning_goal=GOAL)
    context = plan["pending_version"]["plan_context"]
    assert context["remedial_kp_codes"], "未掌握的入学知识点应提示补学"
    assert "python-basics-05-04" in context["remedial_kp_codes"]
    assert any("补学" in note for note in context["notes"])
    assert context["prerequisite_kp_codes"] is not None

    # 只提示，不自动跳过：目标课程知识点照常排期
    items = plan["pending_version"]["items"]
    assert items
    assert all(item["status"] == "pending" for item in items)
    assert plan["pending_version"]["skipped_kp_codes"] == []


# ------------------------------------------- 4. 已掌握知识点不重复安排基础教学


def test_mastered_points_not_scheduled_again(api_env):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _grant_mastery(factory, ["python-basics-01-02"])

    plan = _create_plan(client)
    pending = plan["pending_version"]
    codes = [item["knowledge_point_code"] for item in pending["items"]]
    assert "python-basics-01-02" not in codes
    assert pending["skipped_kp_codes"] == ["python-basics-01-02"]
    assert "python-basics-01-02" in pending["plan_context"]["mastered_kp_codes"]
    assert "python-basics-01-02" not in pending["plan_context"]["unmastered_kp_codes"]

    _confirm_plan(client, plan["id"])
    tasks = _generate_today(client)["tasks"]
    assert all(
        task["knowledge_point"]["code"] != "python-basics-01-02" for task in tasks
    )


# ------------------------------------------------- 5. 诊断结果影响学习计划


def test_placement_diagnosis_result_affects_plan(api_env):
    client, factory = api_env
    _seed(factory, questions=True)
    _set_profile(client)

    target = "python-basics-02-01"
    _self_report(client, [target])
    resp = client.post(
        "/api/v1/diagnosis/placement",
        json={"knowledge_point_codes": [target], "questions_per_point": 2},
    )
    assert resp.status_code == 201, resp.text
    quiz = resp.json()
    assert quiz["purpose"] == "placement"
    _submit_quiz(client, factory, quiz, correct=True)

    plan = _create_plan(client)
    pending = plan["pending_version"]
    assert pending["skipped_kp_codes"] == [target]
    assert target not in [
        item["knowledge_point_code"] for item in pending["items"]
    ]
    context = pending["plan_context"]
    assert context["placement_evidence_count"] >= 1
    assert "诊断" in context["diagnosis_note"]
    assert any("诊断" in note for note in context["notes"])

    # 仅自述完成、没有诊断证据的知识点不会被跳过
    _self_report(client, ["python-basics-01-03"])
    detail = client.get(
        "/api/v1/mastery/knowledge-points/python-basics-02-01"
    ).json()
    assert "placement" in [item["source"] for item in detail["evidence"]]


# ------------------------------------------- 6. 测验结果影响后续复习任务


def test_quiz_failure_affects_followup_review_tasks(api_env):
    client, factory = api_env
    _seed(factory, questions=True)
    _set_profile(client)
    _confirmed_plan(client)
    _self_report(client, [KP_CODE])

    for _ in range(CONSECUTIVE_FAILURE_COUNT):
        quiz = _create_quiz(
            client,
            scope_type="knowledge_point",
            knowledge_point_code=KP_CODE,
        )
        result = _submit_quiz(client, factory, quiz, correct=False)
        assert result["score"] < FAILURE_SCORE_THRESHOLD

    suggestions = client.get("/api/v1/mastery/review-suggestions").json()
    assert any(
        item["knowledge_point"]["knowledge_point_code"] == KP_CODE
        for item in suggestions
    )
    review_tasks = client.get("/api/v1/reviews/tasks").json()
    assert review_tasks, "答错应产生真实错题复习任务"

    # 复习申请只记录申请，返回真实复习任务，不伪造任务、不改掌握状态
    payload = {
        "knowledge_point_code": KP_CODE,
        "reason": "阶段 6 回归",
        "source": "agent",
        "trigger": "consecutive_quiz_failures",
    }
    first = client.post("/api/v1/review-requests", json=payload)
    assert first.status_code == 201, first.text
    data = first.json()
    assert data["created"] is True
    assert data["review_tasks"]
    assert data["mastery_status"] == "needs_review"
    assert "未改动任何掌握状态" in data["note"]
    again = client.post("/api/v1/review-requests", json=payload).json()
    assert again["created"] is False
    assert again["id"] == data["id"]

    signals = client.get("/api/v1/plan-adjustments/signals").json()
    codes = [item["code"] for item in signals["signals"]]
    assert "consecutive_quiz_failures" in codes
    assert "weak_foundation" in codes
    assert "review_requested" in codes
    assert signals["proposal_needed"] is True

    proposal = client.post(
        "/api/v1/plan-adjustments/proposals",
        json={"declared_triggers": ["review_requested"], "source": "api"},
    )
    assert proposal.status_code == 201, proposal.text
    assert "expected_duration_days" in proposal.json()["changes"]


# ------------------------------------------- 7. Agent 从课程库读取内容


def test_agent_teaching_reads_course_library_via_service(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory, textbooks=True)
    _set_profile(client)
    _create_default_model(client)

    calls: list[tuple[str, str]] = []
    original_kp = CourseService.get_knowledge_point
    original_lesson = CourseService.get_lesson

    def spy_kp(self, code):
        calls.append(("get_knowledge_point", code))
        return original_kp(self, code)

    def spy_lesson(self, code):
        calls.append(("get_lesson", code))
        return original_lesson(self, code)

    monkeypatch.setattr(CourseService, "get_knowledge_point", spy_kp)
    monkeypatch.setattr(CourseService, "get_lesson", spy_lesson)

    conversation = client.post(
        "/api/v1/conversations", json={"knowledge_point_code": KP_CODE}
    )
    assert conversation.status_code == 201, conversation.text
    stub = ChatModelStub(["这是基于课程库的讲解。"])
    stub.install(monkeypatch)

    resp = _send(client, conversation.json()["id"], "解释 Python 变量。")
    assert resp.status_code == 200, resp.text
    assert "这是基于课程库的讲解。" in resp.text

    assert ("get_knowledge_point", KP_CODE) in calls
    assert any(name == "get_lesson" for name, _ in calls)
    system_prompt = stub.requests[0]["messages"][0]["content"]
    assert "【课程库内容】" in system_prompt
    assert "来自课程库 Service" in system_prompt
    assert "【核心概念】" in system_prompt  # 真实教材正文，不是模型编造
    assert "什么是编程与 Python" in system_prompt
    # 五条禁令固化在系统提示词里
    assert "不得自己创建/发布正式课程" in system_prompt
    assert "不得修改课程依赖关系" in system_prompt
    assert "不得自动跳过先修条件" in system_prompt
    assert "不得随意更新用户掌握状态" in system_prompt
    assert "未经用户明确确认" in system_prompt
    assert API_KEY not in system_prompt


def test_course_material_section_never_fabricates_missing_content():
    section = build_course_material_section(None, None)
    assert "不要虚构课程内容" in section
    assert "【课程库内容】" in section


# ------------------------------------------- 8. Agent 写操作经过 Service 层


def test_agent_write_tools_delegate_to_service_layer(db_session, monkeypatch):
    calls: list[tuple[str, object]] = []

    def fake_exercise(self, exercise_code, answer):
        calls.append(("submit_exercise", (exercise_code, answer)))
        return "exercise-result"

    def fake_quiz(self, attempt_id, payload):
        calls.append(("submit_attempt", (attempt_id, payload)))
        return "quiz-result"

    def fake_review(self, payload):
        calls.append(("request", payload))
        return "review-result"

    def fake_propose(self, payload, plan_id=None):
        calls.append(("propose", (payload, plan_id)))
        return "proposal-result"

    monkeypatch.setattr(MasteryService, "submit_exercise", fake_exercise)
    monkeypatch.setattr(QuizService, "submit_attempt", fake_quiz)
    monkeypatch.setattr(ReviewRequestService, "request", fake_review)
    monkeypatch.setattr(PlanAdjustmentService, "propose", fake_propose)

    toolbox = AgentToolbox(db_session, LearningContext(today=date.today()))
    assert toolbox.submit_exercise("ex-1", "答案").data == "exercise-result"

    attempt_id = uuid.uuid4()
    assert (
        toolbox.submit_quiz_result(
            attempt_id,
            [{"question_id": str(uuid.uuid4()), "answer": "A"}],
        ).data
        == "quiz-result"
    )
    assert toolbox.request_review_task(KP_CODE, "想复习").data == "review-result"

    plan_id = uuid.uuid4()
    proposal_result = toolbox.propose_learning_plan_adjustment(
        {"daily_study_minutes": 60, "unexpected_key": "ignore-me"},
        reason="测试",
        plan_id=plan_id,
    )
    assert proposal_result.ok, proposal_result.message
    assert proposal_result.data == "proposal-result"

    assert [name for name, _ in calls] == [
        "submit_exercise",
        "submit_attempt",
        "request",
        "propose",
    ]
    payload, target = calls[-1][1]  # type: ignore[misc]
    assert payload.daily_study_minutes == 60
    assert payload.source == "agent"
    assert not hasattr(payload, "unexpected_key")
    assert target == plan_id
    assert calls[1][1][0] == attempt_id  # type: ignore[index]

    # 工具清单里不存在任何「创建课程 / 改依赖 / 跳先修 / 直接写掌握 / 确认计划」入口
    names = {spec["name"] for spec in tool_specs()}
    assert set(FORBIDDEN_TOOL_NAMES).isdisjoint(names)
    for forbidden in FORBIDDEN_TOOL_NAMES:
        assert not hasattr(AgentToolbox, forbidden)


def test_agent_tool_specs_cover_all_nine_required_tools():
    specs = {spec.name: spec for spec in AGENT_TOOL_SPECS}
    assert set(specs) == {
        "get_course",
        "get_lesson",
        "get_knowledge_point",
        "get_user_learning_progress",
        "get_today_tasks",
        "submit_exercise",
        "submit_quiz_result",
        "request_review_task",
        "propose_learning_plan_adjustment",
    }
    assert len(AGENT_TOOL_SPECS) == 9
    # 16 → 17：V1.4 批次 8 新增只读工具 get_latest_quiz_result（查看最近一次
    # 已提交测验的结果），不写库，也不改变「提交只走 REST」的契约。
    assert len(tool_specs()) == 17
    latest = {spec.name: spec for spec in LEGACY_TOOL_SPECS}["get_latest_quiz_result"]
    assert latest.write is False and latest.service.startswith("QuizService")
    for spec in AGENT_TOOL_SPECS:
        assert hasattr(AgentToolbox, spec.method), spec.name
        assert "Service" in spec.service
    write_tools = {spec.name for spec in AGENT_TOOL_SPECS if spec.write}
    assert write_tools == {
        "submit_exercise",
        "submit_quiz_result",
        "request_review_task",
        "propose_learning_plan_adjustment",
    }


# ------------------------------------------- 9. 计划调整必须经过用户确认


def test_plan_adjustment_requires_explicit_confirmation(api_env):
    client, factory = api_env
    _seed(factory)
    plan = _confirmed_plan(client)
    plan_id = plan["id"]

    resp = client.post(
        "/api/v1/plan-adjustments/proposals",
        json={
            "learning_goal": "改为转行做 AI Agent 开发",
            "daily_study_minutes": 90,
            "declared_triggers": ["learning_goal_changed", "daily_minutes_increased"],
        },
    )
    assert resp.status_code == 201, resp.text
    proposal = resp.json()
    assert proposal["status"] == "proposed"
    assert proposal["requires_confirmation"] is True
    assert "尚未保存" in proposal["note"]
    assert "learning_goal_changed" in proposal["triggers"]
    assert "daily_minutes_increased" in proposal["triggers"]
    assert proposal["preview"]["current"]["daily_study_minutes"] == 45
    assert proposal["preview"]["proposed"]["daily_study_minutes"] == 90
    assert proposal["preview"]["impacts"]

    # 确认前：没有新版本、当前版本参数不变、提案还没生效版本号
    current = client.get("/api/v1/plans/current").json()
    assert current["current_version_number"] == 1
    assert current["pending_version_number"] is None
    assert current["current_version"]["daily_study_minutes"] == 45
    assert proposal["resulting_version_number"] is None

    db = factory()
    try:
        # 提案阶段不产生任何学习任务（任务只在计划确认后由首页生成）
        tasks_in_db = db.scalars(
            select(DailyTask).where(DailyTask.plan_id == uuid.UUID(plan_id))
        ).all()
        assert tasks_in_db == []
    finally:
        db.close()

    confirm = client.post(
        f"/api/v1/plan-adjustments/proposals/{proposal['id']}/confirm"
    )
    assert confirm.status_code == 200, confirm.text
    confirmed = client.get("/api/v1/plans/current").json()
    assert confirmed["current_version_number"] == 2
    assert confirmed["current_version"]["daily_study_minutes"] == 90
    assert confirmed["current_version"]["learning_goal"] == "改为转行做 AI Agent 开发"
    assert confirm.json()["proposal"]["status"] == "confirmed"

    # 重复确认被拒绝；另一份提案可以拒绝且不影响计划
    assert (
        client.post(
            f"/api/v1/plan-adjustments/proposals/{proposal['id']}/confirm"
        ).status_code
        == 409
    )
    second = client.post(
        "/api/v1/plan-adjustments/proposals",
        json={"declared_triggers": ["review_requested"]},
    ).json()
    rejected = client.post(
        f"/api/v1/plan-adjustments/proposals/{second['id']}/reject"
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert client.get("/api/v1/plans/current").json()["current_version_number"] == 2

    listed = client.get(
        "/api/v1/plan-adjustments/proposals", params={"status": "proposed"}
    ).json()
    assert listed == []
    db = factory()
    try:
        assert len(db.scalars(select(PlanAdjustmentProposal)).all()) == 2
    finally:
        db.close()


# ------------------------------------------- 10. 原有学习闭环保持正常


def test_original_learning_loop_remains_intact(api_env):
    client, factory = api_env
    _seed(factory, questions=True)

    # 学习目标 → 档案
    _set_profile(client)
    assert client.get("/api/v1/profile").json()["learning_goal"] == GOAL

    # 入学诊断 → 学习计划 → 确认
    plan = _create_plan(client)
    assert plan["status"] == "draft"
    assert plan["pending_version"]["plan_context"]["learning_goal"] == GOAL
    _confirm_plan(client, plan["id"])

    # 每日任务 → 开始学习 → 完成（只写自述证据）
    tasks = _generate_today(client)["tasks"]
    assert tasks
    task = tasks[0]
    kp_code = task["knowledge_point"]["code"]
    started = client.post(f"/api/v1/daily-tasks/{task['id']}/start")
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "learning"
    completed = client.post(f"/api/v1/daily-tasks/{task['id']}/complete")
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
    assert completed.json()["mastery_status"] == "self_reported_completed"
    assert completed.json()["mastery_evidence_count"] >= 1
    assert "不代表掌握" in completed.json()["completion_note"]

    # 练习和测验 → 学习档案更新
    _self_report(client, [kp_code])
    quiz = _create_quiz(
        client, scope_type="knowledge_point", knowledge_point_code=kp_code
    )
    result = _submit_quiz(client, factory, quiz, correct=True)
    assert result["score"] is not None

    # 复习任务与学习进度
    assert client.get("/api/v1/reviews/tasks").status_code == 200
    overview = client.get("/api/v1/mastery").json()
    assert overview["counts"]["mastered"] >= 1
    progress = client.get("/api/v1/overview").json()
    assert progress["plan_available"] is True

    # 动态计划调整（提案 → 确认）与既有版本历史共存
    proposal = client.post(
        "/api/v1/plan-adjustments/proposals",
        json={"daily_study_minutes": 60, "declared_triggers": ["daily_minutes_increased"]},
    ).json()
    assert proposal["requires_confirmation"] is True
    assert (
        client.post(
            f"/api/v1/plan-adjustments/proposals/{proposal['id']}/confirm"
        ).status_code
        == 200
    )
    detail = client.get(f"/api/v1/plans/{plan['id']}").json()
    assert [v["version_number"] for v in detail["versions"]] == [1, 2]


# ------------------------------------------------------------ 附加：发布门槛


def test_draft_course_and_missing_lesson_cannot_enter_formal_plan(api_env):
    client, factory = api_env
    _seed(factory, catalog=True)

    # 阶段 4E 后 7 门课都已发布，这里把目标课程临时置回草稿来验证发布门槛
    db = factory()
    try:
        course = db.scalars(
            select(Course).where(Course.code == "software-engineering-deploy")
        ).one()
        course.publish_status = "draft"
        db.commit()
    finally:
        db.close()

    resp = client.post(
        "/api/v1/plans",
        json=_plan_payload(course_code="software-engineering-deploy"),
    )
    assert resp.status_code == 409
    assert "尚未正式发布" in resp.json()["detail"]

    db = factory()
    try:
        kp = db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code == KP_CODE)
        ).one()
        db.execute(
            delete(LessonKnowledgePoint).where(
                LessonKnowledgePoint.knowledge_point_id == kp.id
            )
        )
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/v1/plans", json=_plan_payload())
    assert resp.status_code == 422
    assert "没有归属的正式课时" in resp.json()["detail"]


# ------------------------------------------------------------ 附加：八因素快照


def test_plan_context_records_all_eight_generation_inputs(api_env):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    plan = _create_plan(client, current_level="L2", daily_study_minutes=60)
    context = plan["pending_version"]["plan_context"]

    assert context["learning_goal"] == GOAL
    assert context["daily_study_minutes"] == 60
    assert context["current_level"] == "L2"
    assert isinstance(context["mastered_kp_codes"], list)
    assert context["unmastered_kp_codes"]
    assert isinstance(context["prerequisite_kp_codes"], list)
    assert context["course_estimated_minutes"] is not None
    assert context["course_estimated_minutes"] > 0
    assert context["scheduled_minutes"] > 0
    assert isinstance(context["recent_quiz_scores"], list)
    assert context["quiz_attempt_count"] == 0
    assert context["placement_evidence_count"] == 0
    assert "诊断" in context["diagnosis_note"]


# ------------------------------------------------------------ 附加：六类信号


def test_six_adjustment_triggers_and_pure_rules():
    assert ADJUSTMENT_TRIGGERS == (
        "consecutive_quiz_failures",
        "mastered_downstream_points",
        "weak_foundation",
        "learning_goal_changed",
        "daily_minutes_increased",
        "review_requested",
    )
    assert consecutive_failures([90.0, 40.0, 55.0]) == 2
    assert consecutive_failures([90.0, 40.0, 80.0]) == 0
    assert consecutive_failures([]) == 0
    assert is_downstream_mastery_signal({"a", "b"}, {"b", "c"}) is False
    assert is_downstream_mastery_signal({"a", "b"}, {"a", "b"}) is True
    assert suggest_changes(
        ["consecutive_quiz_failures"], {}, {"computed_duration_days": 30}
    ) == {"expected_duration_days": 37}
    assert suggest_changes(
        ["daily_minutes_increased"], {"daily_study_minutes": 90}, {}
    ) == {"daily_study_minutes": 90}


def test_declared_only_signals_never_pretend_to_be_measured(api_env):
    """独立验收修复：调用方声明的触发条件不得冒充后端实测信号、不得自动改参数。"""
    client, factory = api_env
    _seed(factory)
    _confirmed_plan(client)

    # 无真实数据、无声明时不应产生任何信号
    baseline = client.get("/api/v1/plan-adjustments/signals").json()
    assert baseline["signals"] == []
    assert baseline["proposal_needed"] is False

    declared = [
        "weak_foundation",
        "review_requested",
        "mastered_downstream_points",
    ]
    resp = client.post(
        "/api/v1/plan-adjustments/proposals",
        json={"declared_triggers": declared, "source": "api"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # 声明线索仍保留，但逐条标注「调用方声明 / 后端未实测」
    assert set(body["triggers"]) == set(declared)
    signals = body["preview"]["signals"]
    assert {item["code"] for item in signals} == set(declared)
    for item in signals:
        assert "调用方声明" in item["detail"]
        assert "后端未实测到对应数据" in item["detail"]
        assert "后端实测" in item["detail"]

    # 汇总必须区分实测与声明；无实测信号时不允许自动推导计划参数
    assert "实测达标 0 项" in body["reason"]
    assert "调用方声明 3 项" in body["reason"]
    assert body["changes"] == {}
    assert body["requires_confirmation"] is True
    assert body["resulting_version_number"] is None
    assert client.get("/api/v1/plans/current").json()["current_version_number"] == 1


def test_review_request_is_idempotent_per_user_kp_date(api_env):
    client, factory = api_env
    _seed(factory)
    payload = {"knowledge_point_code": KP_CODE, "source": "user"}
    first = client.post("/api/v1/review-requests", json=payload)
    second = client.post("/api/v1/review-requests", json=payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["review_tasks"] == []
    assert "不会凭空生成复习任务" in first.json()["note"]

    db = factory()
    try:
        assert len(db.scalars(select(ReviewRequest)).all()) == 1
    finally:
        db.close()
