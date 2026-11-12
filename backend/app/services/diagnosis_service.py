"""学习诊断业务层（阶段 5）。

诊断不是「问几句给个感觉」，而是一次确定性的证据盘点：
- 6 个固定维度，每个维度映射到具体的锚点知识点（不是整门课的平均分）；
- 每个知识点的结论只来自掌握证据（``knowledge_mastery``），自述单独标注
  ``source=claim``，不会被算成已掌握；
- 诊断输出个性化学习路线：跳过（有证据）/ 验证（仅自述）/ 复习 / 学习 / 补学先修；
- 诊断测验（placement）允许对未学知识点出题——这正是跳级的验证通道。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course, KnowledgePoint
from app.models.mastery import MASTERY_STATUS_LABELS
from app.models.quiz import QuizAnswer, QuizAttempt
from app.repositories.course_repository import CourseRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.quiz_repository import QuizRepository
from app.schemas.diagnosis import (
    DIMENSION_LEVEL_LABELS,
    ROUTE_ACTION_LABELS,
    DiagnosisDimensionOut,
    DiagnosisIn,
    DiagnosisKnowledgePointOut,
    DiagnosisOut,
    PlacementIn,
    PlacementPlanOut,
    RouteStepOut,
)
from app.schemas.mastery import SelfReportIn, SelfReportOut
from app.services.mastery_service import MasteryService
from app.services.profile_service import DEFAULT_USERNAME
from app.services.time_utils import utc_now_naive, utc_today_naive

# 视为「已通过检查」的状态（用于维度覆盖率与先修是否满足）。
PASSED_STATUSES: tuple[str, ...] = ("understood", "applied", "mastered")
# 有验证证据的状态（区别于自述）。
EVIDENCE_STATUSES: tuple[str, ...] = ("understood", "applied", "mastered", "needs_review")


@dataclass(frozen=True)
class DimensionSpec:
    """一个诊断维度：固定 code + 锚点知识点（code, 名称关键字兜底）。"""

    code: str
    name: str
    description: str
    course_code: str
    anchors: tuple[tuple[str, str], ...]


# 需求「四、学习诊断升级」的 6 个维度。
# 锚点选择标准：每个维度挑「不会就做不下去」的关键知识点，
# 而不是整门课的所有小节——诊断要的是判断力，不是点名册。
DIMENSIONS: tuple[DimensionSpec, ...] = (
    DimensionSpec(
        code="python-basics",
        name="Python 基础",
        description="变量、类型、字符串、列表、字典、函数、分支与循环",
        course_code="python-basics",
        anchors=(
            ("python-basics-02-01", "变量"),
            ("python-basics-02-03", "字符串"),
            ("python-basics-06-01", "列表"),
            ("python-basics-06-03", "字典"),
            ("python-basics-05-01", "函数"),
            ("python-basics-04-01", "条件判断"),
            ("python-basics-04-04", "for 循环"),
        ),
    ),
    DimensionSpec(
        code="python-engineering",
        name="Python 工程能力",
        description="面向对象、装饰器、类型注解、依赖与包结构",
        course_code="python-advanced",
        anchors=(
            ("python-advanced-01-01", "类、对象"),
            ("python-advanced-02-01", "继承"),
            ("python-advanced-05-01", "装饰器"),
            ("python-advanced-07-01", "类型注解"),
            ("python-advanced-08-01", "venv"),
        ),
    ),
    DimensionSpec(
        code="python-database",
        name="数据库能力",
        description="表设计、查询与聚合、事务、ORM 与迁移",
        course_code="python-database",
        anchors=(
            ("python-database-01-01", "主键"),
            ("python-database-02-01", "SELECT"),
            ("python-database-02-02", "JOIN"),
            ("python-database-05-01", "事务"),
            ("python-database-07-01", "关系映射"),
        ),
    ),
    DimensionSpec(
        code="web-backend",
        name="Web 后端能力",
        description="HTTP 语义、REST 契约、请求响应模型与依赖注入",
        course_code="fastapi-backend",
        anchors=(
            ("fastapi-backend-01-01", "HTTP 方法"),
            ("fastapi-backend-01-02", "REST"),
            ("fastapi-backend-05-02", "响应体"),
            ("fastapi-backend-07-01", "Depends"),
        ),
    ),
    DimensionSpec(
        code="llm-api",
        name="大模型 API 能力",
        description="兼容协议、消息角色、对话状态与上下文预算",
        course_code="llm-api",
        anchors=(
            ("llm-api-02-01", "OpenAI 兼容"),
            ("llm-api-05-01", "消息角色"),
            ("llm-api-07-01", "对话状态"),
            ("llm-api-08-01", "Token 预算"),
        ),
    ),
    DimensionSpec(
        code="langgraph-agent",
        name="LangGraph Agent 能力",
        description="Agent 概念、State 与节点、条件路由、工具、持久化与流式",
        course_code="langgraph-agent",
        anchors=(
            ("langgraph-agent-01-01", "Agent 三要素"),
            ("langgraph-agent-06-01", "State 结构"),
            ("langgraph-agent-13-01", "路由函数"),
            ("langgraph-agent-18-01", "工具节点"),
            ("langgraph-agent-20-01", "检查点"),
            ("langgraph-agent-24-01", "stream_mode"),
        ),
    ),
)

DIMENSION_BY_CODE: dict[str, DimensionSpec] = {item.code: item for item in DIMENSIONS}

# 路线动作的优先级：同一知识点出现多种诉求时取最靠前的一个。
ACTION_ORDER: tuple[str, ...] = ("remedial", "review", "verify", "study", "skip")


class DiagnosisService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.course_repo = CourseRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.question_repo = QuestionRepository(db)
        self.quiz_repo = QuizRepository(db)
        self.mastery = MasteryService(db)

    # ------------------------------------------------------------ 维度定义

    def list_dimensions(self) -> list[DiagnosisDimensionOut]:
        """维度清单与锚点知识点（数据未就绪的维度显式标记 available=False）。"""
        user = self._get_or_create_user()
        self.mastery.bootstrap_from_legacy(user.id)
        dims = [self._dimension(spec, user_id=user.id) for spec in DIMENSIONS]
        self.db.commit()
        return dims

    # ------------------------------------------------------------ 诊断

    def diagnose(self, payload: DiagnosisIn) -> DiagnosisOut:
        user = self._get_or_create_user()

        # 自述先落库（只写自述状态，不写掌握），诊断再按证据读
        if payload.self_reported_kp_codes:
            self.mastery.report_self_completed(
                payload.self_reported_kp_codes, note="初始化诊断中的自述"
            )
        self.mastery.bootstrap_from_legacy(user.id)

        specs = [
            DIMENSION_BY_CODE[code]
            for code in payload.dimension_codes
            if code in DIMENSION_BY_CODE
        ] or list(DIMENSIONS)
        dims = [self._dimension(spec, user_id=user.id) for spec in specs]

        target = (
            self.course_repo.get_course_by_code(payload.target_course_code)
            if payload.target_course_code
            else None
        )
        if payload.target_course_code and target is None:
            raise HTTPException(status_code=404, detail="目标课程不存在")

        route = self._build_route(user.id, target, dims)
        skippable = [step.knowledge_point_code for step in route if step.action == "skip"]
        verification = [
            step.knowledge_point_code for step in route if step.action == "verify"
        ]
        remedial = [
            step.knowledge_point_code for step in route if step.action == "remedial"
        ]

        notes: list[str] = []
        claimed = [
            dim
            for dim in dims
            for kp in dim.knowledge_points
            if kp.source == "claim"
        ]
        if claimed:
            notes.append(
                f"有 {len(claimed)} 个知识点是自述完成，已按「待验证」处理，"
                "不参与跳过；请用诊断测验验证后再决定是否跳过。"
            )
        if any(dim.level == "no_data" for dim in dims):
            notes.append("部分维度还没有课程数据，诊断只覆盖已有课程的维度。")
        notes.append(self._mastery_source_note())

        summary = self._summary(dims, target)
        self.db.commit()
        return DiagnosisOut(
            generated_at=utc_today_naive(),
            learning_goal=payload.learning_goal,
            target_course_code=target.code if target else None,
            target_course_name=target.name if target else None,
            dimensions=dims,
            route=route,
            skippable_kp_codes=skippable,
            needs_verification_kp_codes=verification,
            remedial_kp_codes=remedial,
            summary=summary,
            notes=notes,
        )

    # ------------------------------------------------------------ 诊断测验

    def placement_plan(self, payload: PlacementIn) -> PlacementPlanOut:
        """告知哪些知识点可以立刻用诊断测验验证，以及各能出几道题。"""
        user = self._get_or_create_user()
        kps, course, notes = self._placement_targets(user.id, payload)
        counts = self._placement_counts(kps, payload.questions_per_point)
        now = utc_today_naive()
        return PlacementPlanOut(
            course_code=course.code if course else payload.course_code,
            course_name=course.name if course else None,
            knowledge_points=[
                self._diagnosis_kp(kp, user.id, today=now) for kp in kps
            ],
            question_counts=counts,
            notes=notes,
        )

    def create_placement_quiz(self, payload: PlacementIn) -> QuizAttempt:
        """生成诊断测验：允许未学知识点，抽样验证后写入掌握证据。"""
        user = self._get_or_create_user()
        kps, course, notes = self._placement_targets(user.id, payload)
        counts = self._placement_counts(kps, payload.questions_per_point)
        kps = [kp for kp in kps if counts.get(kp.code, 0) > 0]
        if not kps:
            raise HTTPException(
                status_code=409,
                detail="所选知识点暂无正式可用题目，无法生成诊断测验",
            )

        questions = self.question_repo.list_selectable_by_knowledge_points(
            [kp.id for kp in kps]
        )
        selected: list = []
        for kp in kps:
            limit = counts.get(kp.code, 0)
            group = [item for item in questions if item.knowledge_point_id == kp.id]
            selected.extend(group[:limit])
        if not selected:
            raise HTTPException(status_code=409, detail="所选范围暂无可用题目")

        attempt = QuizAttempt(
            user_id=user.id,
            scope_type="stage",
            scope_ref=course.code if course else payload.course_code,
            scope_name=(
                f"诊断测验：{course.name}" if course else "诊断测验"
            ),
            status="in_progress",
            purpose="placement",
            question_count=len(selected),
            total_points=len(selected) * 10,
            started_at=utc_now_naive(),
        )
        for index, question in enumerate(selected, start=1):
            QuizAnswer(
                attempt=attempt,
                question=question,
                question_order=index,
                max_score=10,
            )
        self.quiz_repo.add_attempt(attempt)
        self.db.commit()
        return attempt

    # ------------------------------------------------------------ 内部：维度

    def _dimension(self, spec: DimensionSpec, *, user_id: uuid.UUID) -> DiagnosisDimensionOut:
        course = self.course_repo.get_course_by_code(spec.course_code)
        if course is None:
            return DiagnosisDimensionOut(
                code=spec.code,
                name=spec.name,
                description=spec.description,
                course_code=spec.course_code,
                course_name=None,
                available=False,
                level="no_data",
                level_label=DIMENSION_LEVEL_LABELS["no_data"],
                mastered_count=0,
                understood_count=0,
                applied_count=0,
                needs_review_count=0,
                not_started_count=0,
                total=0,
                coverage_percent=0.0,
                knowledge_points=[],
                note=f"课程 {spec.course_code} 尚未建设，本维度暂无数据",
            )

        anchors = self._resolve_anchors(course, spec)
        today = utc_today_naive()
        points = [self._diagnosis_kp(kp, user_id, today=today) for kp in anchors]
        mastered = sum(1 for item in points if item.status == "mastered")
        understood = sum(1 for item in points if item.status == "understood")
        applied = sum(1 for item in points if item.status == "applied")
        review = sum(1 for item in points if item.status == "needs_review")
        not_started = sum(
            1 for item in points if item.status in ("not_started", "learning")
        )
        passed = mastered + applied + understood
        coverage = round(passed / len(points) * 100, 1) if points else 0.0

        if not points:
            level = "no_data"
            note = "该维度还没有锚点知识点"
        elif mastered == len(points):
            level = "mastered"
            note = "锚点知识点全部通过掌握验证"
        elif passed == 0:
            level = "not_started"
            note = "锚点知识点还没有通过任何检查"
        else:
            level = "partial"
            note = (
                f"{mastered} 个已掌握、{understood} 个仅通过基础理解、"
                f"{applied} 个通过应用练习，仍有 {not_started + review} 个需要学习或复习"
            )

        return DiagnosisDimensionOut(
            code=spec.code,
            name=spec.name,
            description=spec.description,
            course_code=course.code,
            course_name=course.name,
            available=bool(points),
            level=level,
            level_label=DIMENSION_LEVEL_LABELS[level],
            mastered_count=mastered,
            understood_count=understood,
            applied_count=applied,
            needs_review_count=review,
            not_started_count=not_started,
            total=len(points),
            coverage_percent=coverage,
            knowledge_points=points,
            note=note,
        )

    def _resolve_anchors(
        self, course: Course, spec: DimensionSpec
    ) -> list[KnowledgePoint]:
        """按 code 解析锚点，解析不到再按名称关键字兜底（课程改版不至于断诊断）。"""
        kps = [
            kp
            for chapter in course.chapters
            for kp in sorted(chapter.knowledge_points, key=lambda item: item.order_index)
            if kp.deleted_at is None
        ]
        by_code = {kp.code: kp for kp in kps}
        resolved: list[KnowledgePoint] = []
        for code, keyword in spec.anchors:
            kp = by_code.get(code)
            if kp is None:
                kp = next((item for item in kps if keyword in item.name), None)
            if kp is not None and kp not in resolved:
                resolved.append(kp)
        return resolved

    def _diagnosis_kp(
        self, kp: KnowledgePoint, user_id: uuid.UUID, *, today
    ) -> DiagnosisKnowledgePointOut:
        mastery = self.mastery.repo.get(user_id, kp.id)
        status = mastery.status if mastery else "not_started"
        if status in EVIDENCE_STATUSES and mastery and mastery.verified_at:
            source = "evidence"
        elif status == "self_reported_completed":
            source = "claim"
        else:
            source = "none"
        return DiagnosisKnowledgePointOut(
            knowledge_point_code=kp.code,
            knowledge_point_name=kp.name,
            chapter_title=kp.chapter.title,
            difficulty=kp.difficulty,
            status=status,  # type: ignore[arg-type]
            status_label=MASTERY_STATUS_LABELS[status],
            source=source,  # type: ignore[arg-type]
            accuracy=mastery.accuracy if mastery else None,
            verified_at=(
                mastery.verified_at.isoformat()
                if mastery and mastery.verified_at
                else None
            ),
        )

    # ------------------------------------------------------------ 内部：路线

    def _build_route(
        self, user_id: uuid.UUID, target: Course | None, dims: list[DiagnosisDimensionOut]
    ) -> list[RouteStepOut]:
        """生成步骤：有目标课程走「先修 → 目标」全量，否则只走各维度的锚点知识点。

        没有目标课程时若展开整门课，6 个维度会产出近 200 步，
        对「我该从哪开始」没有帮助；此时只给锚点知识点的结论。
        """
        groups: list[list[KnowledgePoint]] = []
        if target is not None:
            for course in self._scope_courses(target, dims):
                groups.append(
                    [
                        kp
                        for chapter in sorted(
                            course.chapters, key=lambda item: item.order_index
                        )
                        for kp in sorted(
                            chapter.knowledge_points, key=lambda item: item.order_index
                        )
                        if kp.deleted_at is None
                    ]
                )
        else:
            for dim in dims:
                course = self.course_repo.get_course_by_code(dim.course_code)
                if course is None:
                    continue
                codes = [item.knowledge_point_code for item in dim.knowledge_points]
                by_code = {
                    kp.code: kp
                    for chapter in course.chapters
                    for kp in chapter.knowledge_points
                }
                groups.append([by_code[code] for code in codes if code in by_code])

        steps: list[RouteStepOut] = []
        seen: dict[str, RouteStepOut] = {}

        def add(kp: KnowledgePoint, action: str, reason: str) -> None:
            if kp.code in seen:
                previous = seen[kp.code]
                # 已存在时只允许「更紧急」的动作替换（补学 > 复习 > 验证 > 学习 > 跳过）
                if ACTION_ORDER.index(action) < ACTION_ORDER.index(previous.action):
                    previous.action = action  # type: ignore[assignment]
                    previous.reason = reason
                return
            step = RouteStepOut(
                order_index=len(steps) + 1,
                knowledge_point_code=kp.code,
                knowledge_point_name=kp.name,
                course_code=kp.chapter.course.code,
                course_name=kp.chapter.course.name,
                action=action,  # type: ignore[arg-type]
                action_label=ROUTE_ACTION_LABELS[action],
                reason=reason,
                estimated_minutes=kp.estimated_minutes,
            )
            seen[kp.code] = step
            steps.append(step)

        # 目标课程的入学知识点：未达标的显式标成补学，这条清单就是需求里的
        # 「未掌握的先修知识点提供补学建议」（比把前置课程整体算作学习更明确）。
        if target is not None:
            for required in target.required_knowledge_points:
                if required.deleted_at is not None:
                    continue
                if not self._passed(user_id, required):
                    add(
                        required,
                        "remedial",
                        f"《{target.name}》的入学知识点，当前未达标，先补学",
                    )

        for group in groups:
            position = {kp.code: index for index, kp in enumerate(group)}
            for index, kp in enumerate(group):
                mastery = self.mastery.repo.get(user_id, kp.id)
                status = mastery.status if mastery else "not_started"
                for prerequisite in kp.prerequisites:
                    if self._passed(user_id, prerequisite):
                        continue
                    if prerequisite.code in seen:
                        # 已经在路线里（更早的课程或本组更早的步骤），不必再标补学
                        continue
                    if prerequisite.code in position:
                        # 本组内稍后会作为独立步骤出现，按自己的状态判定
                        continue
                    add(
                        prerequisite,
                        "remedial",
                        f"「{kp.name}」的先修，当前未达标，先补学",
                    )
                action, reason = self._action_for(status)
                add(kp, action, reason)
        return steps

    def _action_for(self, status: str) -> tuple[str, str]:
        if status == "mastered":
            return "skip", "已有掌握证据，可直接跳过"
        if status == "applied":
            return "verify", "已通过应用练习，再做一次完整知识点测验确认掌握"
        if status == "understood":
            return "study", "已通过基础理解，仍需完成应用练习才能进入应用档"
        if status == "needs_review":
            return "review", "最近一次验证未通过，先复习错题与应用练习"
        if status == "self_reported_completed":
            return "verify", "仅自述完成，需诊断测验或知识点测验验证"
        return "study", "尚未通过任何检查，按课程顺序学习"

    def _passed(self, user_id: uuid.UUID, kp: KnowledgePoint) -> bool:
        mastery = self.mastery.repo.get(user_id, kp.id)
        return bool(mastery and mastery.status in PASSED_STATUSES)

    def _scope_courses(
        self, target: Course | None, dims: list[DiagnosisDimensionOut]
    ) -> list[Course]:
        """路线范围：目标课程 + 其先修传递闭包；没有目标时取维度对应课程。"""
        if target is None:
            codes = [dim.course_code for dim in dims]
            courses = [
                course
                for code in codes
                if (course := self.course_repo.get_course_by_code(code)) is not None
            ]
            return sorted(courses, key=lambda item: (item.sort_order, item.code))

        collected: dict[str, Course] = {}

        def walk(course: Course) -> None:
            for prerequisite in course.prerequisites:
                if prerequisite.code in collected or prerequisite.deleted_at is not None:
                    continue
                collected[prerequisite.code] = prerequisite
                walk(prerequisite)

        walk(target)
        collected[target.code] = target
        return sorted(collected.values(), key=lambda item: (item.sort_order, item.code))

    # ------------------------------------------------------------ 内部：诊断测验

    def _placement_targets(
        self, user_id: uuid.UUID, payload: PlacementIn
    ) -> tuple[list[KnowledgePoint], Course | None, list[str]]:
        notes: list[str] = []
        course = (
            self.course_repo.get_course_by_code(payload.course_code)
            if payload.course_code
            else None
        )
        if payload.course_code and course is None:
            raise HTTPException(status_code=404, detail="课程不存在")

        kps: list[KnowledgePoint] = []
        for code in payload.knowledge_point_codes:
            kp = self.course_repo.get_knowledge_point_by_code(code)
            if kp is None:
                raise HTTPException(status_code=404, detail=f"知识点不存在：{code}")
            kps.append(kp)

        if not kps and course is not None:
            # 未指定知识点：优先验证「用户自述过但还没证据」的知识点
            self.mastery.bootstrap_from_legacy(user_id)
            kps = [
                record.knowledge_point
                for record in self.mastery.repo.list_for_course(user_id, course.code)
                if record.status in ("self_reported_completed", "understood", "applied")
            ]
            if not kps:
                notes.append(
                    "该课程没有待验证的知识点；可先自述完成，或直接指定知识点 code"
                )
        if not kps:
            notes.append("请指定要验证的知识点（knowledge_point_codes）或课程 code")
        return kps, course, notes

    def _placement_counts(
        self, kps: list[KnowledgePoint], per_point: int
    ) -> dict[str, int]:
        if not kps:
            return {}
        available = self.question_repo.count_selectable_by_knowledge_point()
        return {
            kp.code: min(available.get(kp.id, 0), per_point) for kp in kps
        }

    # ------------------------------------------------------------ 内部：文案

    @staticmethod
    def _summary(dims: list[DiagnosisDimensionOut], target: Course | None) -> str:
        mastered = [dim.name for dim in dims if dim.level == "mastered"]
        partial = [dim.name for dim in dims if dim.level == "partial"]
        pending = [dim.name for dim in dims if dim.level == "not_started"]
        missing = [dim.name for dim in dims if dim.level == "no_data"]
        parts: list[str] = []
        if mastered:
            parts.append("已掌握：" + "、".join(mastered))
        if partial:
            parts.append("部分掌握：" + "、".join(partial))
        if pending:
            parts.append("待开始：" + "、".join(pending))
        if missing:
            parts.append("暂无数据：" + "、".join(missing))
        goal = f"目标课程《{target.name}》" if target else "当前目标"
        return f"{goal}：" + "；".join(parts) + "。按下方路线补齐前置，再进入目标课程。"

    @staticmethod
    def _mastery_source_note() -> str:
        return (
            "诊断结论只采信掌握证据：用户自述标注为「用户自述完成」，"
            "不参与跳过判断；跳过必须通过知识点测验或诊断测验。"
        )

    def _get_or_create_user(self):
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user

    # 供路由层复用的自述入口（诊断前的自述统一走掌握服务）
    def report_self(self, payload: SelfReportIn) -> SelfReportOut:
        return self.mastery.report_self_completed(
            payload.knowledge_point_codes, payload.note
        )


__all__ = ["DIMENSIONS", "DIMENSION_BY_CODE", "DiagnosisService", "PASSED_STATUSES"]
