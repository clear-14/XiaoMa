"""动态计划调整：提案 → 展示 → 用户确认 → 生效（阶段 6「六」）。

硬性约束：
- ``propose()`` 只写 ``plan_adjustment_proposals``（status=proposed），
  **不调用** ``PlanService.adjust_plan`` / ``confirm_plan``，不产生任何计划版本；
- 只有 ``confirm()`` 才生成并生效新版本，且回调既有 PlanService 以复用
  版本历史、已完成任务携带、按掌握证据重新排期等规则；
- ``reject()`` 只改提案状态，计划保持原样；
- 建议参数由确定性纯函数 ``suggest_changes`` 给出，不靠模型推断。
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.phase6 import PlanAdjustmentProposal, TRIGGER_LABELS
from app.repositories.phase6_repository import PlanAdjustmentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.phase6 import (
    PlanAdjustmentProposalOut,
    PlanSignalsOut,
    ProposalConfirmOut,
    ProposalCreate,
)
from app.schemas.plan import PlanAdjust
from app.services.course_publication_service import CoursePublicationService
from app.services.mastery_service import MasteryService
from app.services.plan_service import PlanService
from app.services.plan_signal_service import PlanSignalService
from app.services.profile_service import DEFAULT_USERNAME
from app.services.time_utils import utc_now_naive

PROPOSAL_NOTE = (
    "这只是待确认方案，尚未保存为学习计划、也不会改变当前安排；"
    "请在「学习计划」页或调整提案接口确认后才会生成并生效新版本。"
)

# 出现复习/补学诉求时，为复习预留的期望周期天数（确定性规则）
REVIEW_BUFFER_DAYS = 7
MAX_EXPECTED_DAYS = 3650


def suggest_changes(
    signal_codes: list[str], requested: dict, current: dict
) -> dict:
    """按触发信号补全建议参数（纯函数，规则固定可单测）。

    - 调用方显式给出的参数一律优先；
    - 连续测验不通过 / 基础能力不足 / 请求复习 → 在现有期望周期上
      预留 7 天复习缓冲（上限 3650 天）；
    - 其余信号不改参数：确认时会按最新掌握证据重新排期，无需改参数。
    """
    changes = dict(requested)
    needs_buffer = any(
        code in signal_codes
        for code in (
            "consecutive_quiz_failures",
            "weak_foundation",
            "review_requested",
        )
    )
    if "expected_duration_days" not in changes and needs_buffer:
        base = (
            current.get("expected_duration_days")
            or current.get("computed_duration_days")
            or 30
        )
        changes["expected_duration_days"] = min(
            int(base) + REVIEW_BUFFER_DAYS, MAX_EXPECTED_DAYS
        )
    return changes


class PlanAdjustmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.proposal_repo = PlanAdjustmentRepository(db)
        self.plan_repo = PlanRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.signals = PlanSignalService(db)

    # ------------------------------------------------------------- 信号盘点

    def get_signals(
        self, plan_id: uuid.UUID | None = None, payload: ProposalCreate | None = None
    ) -> PlanSignalsOut:
        user = self._get_or_create_user()
        plan = self._plan_or_404(plan_id, user.id)
        result, _ = self.signals.collect(user.id, plan, payload)
        return result

    # ------------------------------------------------------------- 提案

    def propose(
        self, payload: ProposalCreate, plan_id: uuid.UUID | None = None
    ) -> PlanAdjustmentProposalOut:
        user = self._get_or_create_user()
        plan = self._plan_or_404(plan_id, user.id)
        signal_out, evidence = self.signals.collect(user.id, plan, payload)
        version = self.signals._active_version(plan)
        if version is None:
            raise HTTPException(status_code=409, detail="计划没有可调整的版本")

        requested = {
            key: value
            for key, value in (
                ("learning_goal", payload.learning_goal),
                ("daily_study_minutes", payload.daily_study_minutes),
                ("expected_duration_days", payload.expected_duration_days),
            )
            if value is not None
        }
        current = {
            "learning_goal": version.learning_goal,
            "daily_study_minutes": version.daily_study_minutes,
            "expected_duration_days": version.expected_duration_days,
            "computed_duration_days": version.computed_duration_days,
        }
        # 建议参数只由「后端实测达标」的信号推导；调用方声明的线索保留在
        # preview.signals 与 triggers 里，但不会凭声明自动改动计划参数。
        changes = suggest_changes(
            evidence.verified_signal_codes, requested, current
        )

        mastery = MasteryService(self.db)
        mastered = sorted(mastery.mastered_kp_codes())
        review_suggestions = mastery.review_suggestions()
        review_codes = [
            item.knowledge_point.knowledge_point_code
            for item in review_suggestions
        ]
        remedial = self._remedial_codes(plan.course.code, mastered)

        proposed = dict(current)
        proposed.update(changes)
        impacts = [
            f"每日学习时间：{current['daily_study_minutes']} → "
            f"{proposed['daily_study_minutes']} 分钟",
            f"期望周期：{current['expected_duration_days']} → "
            f"{proposed['expected_duration_days']} 天",
            f"学习目标：{current['learning_goal']} → {proposed['learning_goal']}",
            f"确认后将按最新掌握证据重新排期，跳过 {len(evidence.downstream_mastered_codes)} 个后续已掌握知识点",
        ]
        if review_codes:
            impacts.append(f"需复习知识点 {len(review_codes)} 个，请先完成复习任务")
        if remedial:
            impacts.append(f"未掌握的先修/入学知识点 {len(remedial)} 个，建议补学")
        if not changes:
            impacts.append("本次不改动计划参数，仅按最新证据重新排期")

        preview = {
            "current": current,
            "proposed": proposed,
            "impacts": impacts,
            "signals": [item.model_dump() for item in signal_out.signals],
            "skipped_kp_codes": evidence.downstream_mastered_codes,
            "mastered_kp_codes": mastered,
            "review_kp_codes": review_codes,
            "remedial_kp_codes": remedial,
            "needs_review_count": evidence.needs_review_count,
            "recent_quiz_scores": evidence.recent_scores[-5:],
        }
        reason = payload.reason or (
            signal_out.summary + "；建议按上述方案调整，确认后生效。"
        )
        triggers = [item.code for item in signal_out.signals]
        proposal = PlanAdjustmentProposal(
            user_id=user.id,
            plan_id=plan.id,
            status="proposed",
            triggers=triggers,
            reason=reason,
            changes=changes,
            preview=preview,
            source=payload.source,
        )
        self.proposal_repo.add(proposal)
        self.db.commit()
        return self._out(proposal)

    # ------------------------------------------------------------- 查询

    def list_proposals(
        self, status: str | None = None
    ) -> list[PlanAdjustmentProposalOut]:
        user = self._get_or_create_user()
        return [
            self._out(item)
            for item in self.proposal_repo.list_for_user(user.id, status)
        ]

    def get_proposal(self, proposal_id: uuid.UUID) -> PlanAdjustmentProposalOut:
        user = self._get_or_create_user()
        return self._out(self._proposal_or_404(proposal_id, user.id))

    # ------------------------------------------------------------- 确认 / 拒绝

    def confirm(self, proposal_id: uuid.UUID) -> ProposalConfirmOut:
        user = self._get_or_create_user()
        proposal = self._proposal_or_404(proposal_id, user.id)
        if proposal.status != "proposed":
            raise HTTPException(
                status_code=409,
                detail=f"提案已{TRIGGER_LABELS.get(proposal.status, proposal.status)}，不能重复确认",
            )
        changes = dict(proposal.changes or {})
        # 无参数提案仍需走一次调整：用当前期望周期作为等价参数，
        # 触发 PlanService 按最新掌握证据重新排期（不猜测任何新值）。
        if not changes:
            plan = self._plan_or_404(proposal.plan_id, user.id)
            version = self.signals._active_version(plan)
            changes = {
                "expected_duration_days": (
                    version.expected_duration_days if version else 30
                )
            }
        plan_service = PlanService(self.db)
        plan_service.adjust_plan(proposal.plan_id, PlanAdjust(**changes))
        current = plan_service.confirm_plan(proposal.plan_id)

        proposal.status = "confirmed"
        proposal.confirmed_at = utc_now_naive()
        proposal.resulting_version_number = current.current_version_number
        self.db.commit()
        return ProposalConfirmOut(
            proposal=self._out(proposal),
            plan=current,
            message=(
                f"方案已确认，学习计划版本 {current.current_version_number} 已生效；"
                "确认前的当前安排保持不变直到本次确认"
            ),
        )

    def reject(self, proposal_id: uuid.UUID) -> PlanAdjustmentProposalOut:
        user = self._get_or_create_user()
        proposal = self._proposal_or_404(proposal_id, user.id)
        if proposal.status != "proposed":
            raise HTTPException(status_code=409, detail="只能拒绝待确认的提案")
        proposal.status = "rejected"
        proposal.rejected_at = utc_now_naive()
        self.db.commit()
        return self._out(proposal)

    # ------------------------------------------------------------- 内部

    def _remedial_codes(self, course_code: str, mastered: list[str]) -> list[str]:
        """课程前置关系里尚未掌握的入学知识点（补学提示）。"""
        from app.services.course_catalog_service import CourseCatalogService

        try:
            path = CourseCatalogService(self.db).get_learning_path(
                course_code,
                mastered_knowledge_point_codes=mastered,
            )
        except HTTPException:
            return []
        return [item.code for item in path.missing_knowledge_points]

    def _plan_or_404(self, plan_id: uuid.UUID | None, user_id: uuid.UUID):
        plan = (
            self.plan_repo.get_plan(plan_id, user_id)
            if plan_id is not None
            else self.plan_repo.get_latest_plan(user_id)
        )
        if plan is None:
            raise HTTPException(status_code=404, detail="暂无学习计划，无法调整")
        return plan

    def _proposal_or_404(
        self, proposal_id: uuid.UUID, user_id: uuid.UUID
    ) -> PlanAdjustmentProposal:
        proposal = self.proposal_repo.get(proposal_id, user_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="调整提案不存在")
        return proposal

    def _get_or_create_user(self):
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user

    @staticmethod
    def _out(proposal: PlanAdjustmentProposal) -> PlanAdjustmentProposalOut:
        codes = list(proposal.triggers or [])
        return PlanAdjustmentProposalOut(
            id=proposal.id,
            plan_id=proposal.plan_id,
            status=proposal.status,
            triggers=codes,
            trigger_labels=[TRIGGER_LABELS.get(code, code) for code in codes],
            reason=proposal.reason,
            changes=proposal.changes or {},
            preview=proposal.preview or {},
            source=proposal.source,
            created_at=proposal.created_at,
            confirmed_at=proposal.confirmed_at,
            rejected_at=proposal.rejected_at,
            resulting_version_number=proposal.resulting_version_number,
            note=PROPOSAL_NOTE,
        )
