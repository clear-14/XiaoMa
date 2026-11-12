"""动态计划调整信号检测（阶段 6「六、动态计划调整」）。

六类触发优先由**真实数据**判定，不交给模型猜测：
1. 连续测验不通过：最近连续 ≥2 次已提交测验得分 < 60；
2. 已掌握多个后续知识点：有掌握证据的知识点中有 ≥2 个还排在计划后续天；
3. 某项基础能力明显不足：存在需要复习的知识点或薄弱项复习建议；
4. 用户改变学习目标：请求里的目标与当前生效版本不同；
5. 用户需要增加每日学习时间：请求里的每日分钟数大于当前版本；
6. 用户请求复习以前的内容：存在待安排复习申请，或调用方显式声明。

调用方（Agent / 前端）可用 ``declared_triggers`` 补充调整线索；声明类
信号一律标注「调用方声明，后端未实测到对应数据」，不冒充系统检测到的
真实信号，也不改变 ``signals`` 的固定顺序。验收时据此区分「实测达标」
与「仅请求线索」，避免把声明包装成检测结果。

数值判定集中在纯函数里（可直接单测），本层只负责取数、过滤、组装。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.learning_plan import LearningPlan
from app.models.phase6 import ADJUSTMENT_TRIGGERS, TRIGGER_LABELS
from app.repositories.phase6_repository import ReviewRequestRepository
from app.repositories.quiz_repository import QuizRepository
from app.schemas.phase6 import PlanSignalOut, PlanSignalsOut, ProposalCreate
from app.services.mastery_service import MasteryService

# 低于该百分制分数视为一次「测验不通过」
FAILURE_SCORE_THRESHOLD = 60.0
# 连续不通过次数阈值
CONSECUTIVE_FAILURE_COUNT = 2
# 已掌握的后续知识点数量阈值
DOWNSTREAM_MASTERED_THRESHOLD = 2


def consecutive_failures(scores_in_time_order: list[float]) -> int:
    """从最近一次往前数，连续低于阈值的测验次数（纯函数）。

    ``scores_in_time_order`` 必须按提交时间升序；None/未提交的不参与判定，
    由调用方过滤后再传入。
    """
    streak = 0
    for score in reversed(scores_in_time_order):
        if score < FAILURE_SCORE_THRESHOLD:
            streak += 1
        else:
            break
    return streak


def is_downstream_mastery_signal(
    mastered_codes: set[str], downstream_codes: set[str]
) -> bool:
    """已掌握且仍排在后续计划日的知识点是否达到阈值（纯函数）。"""
    return len(mastered_codes & downstream_codes) >= DOWNSTREAM_MASTERED_THRESHOLD


@dataclass(frozen=True)
class SignalEvidence:
    """一次信号检测的原始事实，便于测试与文档说明。"""

    recent_scores: list[float]
    downstream_mastered_codes: list[str]
    needs_review_count: int
    weak_suggestion_count: int
    pending_review_requests: int
    current_learning_goal: str | None
    current_daily_minutes: int | None
    current_day_index: int
    # 只有实测达标的条件可用于自动推导建议参数；调用方声明的线索不在此列
    verified_signal_codes: list[str]


class PlanSignalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.quiz_repo = QuizRepository(db)
        self.review_request_repo = ReviewRequestRepository(db)
        self.mastery = MasteryService(db)

    def collect(
        self,
        user_id: uuid.UUID,
        plan: LearningPlan,
        payload: ProposalCreate | None = None,
    ) -> tuple[PlanSignalsOut, SignalEvidence]:
        payload = payload or ProposalCreate()
        version = self._active_version(plan)
        current_day = self._current_day(version) if version is not None else 0
        current_goal = version.learning_goal if version is not None else None
        current_minutes = (
            version.daily_study_minutes if version is not None else None
        )

        submitted = [
            attempt
            for attempt in self.quiz_repo.list_attempts(user_id, limit=30)
            if attempt.status == "submitted"
            and (attempt.purpose or "practice") != "placement"
            and attempt.score is not None
        ]
        submitted.sort(key=lambda a: a.submitted_at or a.started_at)
        scores = [float(attempt.score) for attempt in submitted]
        failed_streak = consecutive_failures(scores)

        mastered = self.mastery.mastered_kp_codes()
        downstream = {
            item.knowledge_point.code
            for item in (version.items if version is not None else [])
            if item.day_index > current_day and item.status == "pending"
        }
        downstream_mastered = sorted(mastered & downstream)

        overview = self.mastery.get_overview()
        needs_review_count = overview.counts.needs_review
        weak_suggestion_count = len(self.mastery.review_suggestions())
        pending_requests = len(
            self.review_request_repo.list_for_user(user_id, status="pending")
        )

        declared = set(payload.declared_triggers) & set(ADJUSTMENT_TRIGGERS)
        signals: list[PlanSignalOut] = []
        # 实测达标与「仅调用方声明」必须可区分：声明类只作为调整请求线索，
        # detail 明确写出后端实测值，不允许包装成系统检测到的真实信号。
        verified_count = 0
        verified_codes: list[str] = []
        DECLARED_PREFIX = "【调用方声明，后端未实测到对应数据】"

        def add(code: str, detail: str, *, verified: bool) -> None:
            signals.append(
                PlanSignalOut(
                    code=code,
                    label=TRIGGER_LABELS[code],
                    detail=detail if verified else DECLARED_PREFIX + detail,
                )
            )

        def record(
            code: str,
            *,
            condition: bool,
            real_detail: str,
            clue_detail: str,
        ) -> None:
            nonlocal verified_count
            if condition:
                add(code, real_detail, verified=True)
                verified_count += 1
                verified_codes.append(code)
            elif code in declared:
                add(code, clue_detail, verified=False)

        record(
            "consecutive_quiz_failures",
            condition=failed_streak >= CONSECUTIVE_FAILURE_COUNT,
            real_detail=(
                f"最近连续 {failed_streak} 次测验低于 {FAILURE_SCORE_THRESHOLD:g} 分"
            ),
            clue_detail=(
                f"后端实测最近连续不通过 {failed_streak} 次，"
                f"未达 {CONSECUTIVE_FAILURE_COUNT} 次阈值；仅作为调整请求线索"
            ),
        )
        record(
            "mastered_downstream_points",
            condition=is_downstream_mastery_signal(mastered, downstream),
            real_detail=(
                f"已有掌握证据且仍排在后续计划日的知识点 "
                f"{len(downstream_mastered)} 个"
            ),
            clue_detail=(
                f"后端实测已掌握且仍排在后续计划日的知识点 "
                f"{len(downstream_mastered)} 个，未达 "
                f"{DOWNSTREAM_MASTERED_THRESHOLD} 个阈值；仅作为线索"
            ),
        )
        record(
            "weak_foundation",
            condition=needs_review_count > 0 or weak_suggestion_count > 0,
            real_detail=(
                f"{needs_review_count} 个知识点需要复习，"
                f"{weak_suggestion_count} 条薄弱项建议"
            ),
            clue_detail=(
                f"后端实测需复习知识点 {needs_review_count} 个、"
                f"薄弱项建议 {weak_suggestion_count} 条，均为 0；仅作为线索"
            ),
        )
        record(
            "learning_goal_changed",
            condition=bool(
                payload.learning_goal
                and current_goal
                and payload.learning_goal != current_goal
            ),
            real_detail=(
                f"目标由「{current_goal or '未设置'}」变为"
                f"「{payload.learning_goal or '未指定'}」"
            ),
            clue_detail=(
                f"请求目标「{payload.learning_goal or '未指定'}」，"
                f"当前目标「{current_goal or '未设置'}」，"
                "后端未验证到目标变化；仅作为线索"
            ),
        )
        record(
            "daily_minutes_increased",
            condition=bool(
                payload.daily_study_minutes
                and current_minutes
                and payload.daily_study_minutes > current_minutes
            ),
            real_detail=(
                f"每日学习时间由 {current_minutes or '未设置'} 分钟"
                f"增加到 {payload.daily_study_minutes or '未指定'} 分钟"
            ),
            clue_detail=(
                f"请求每日 {payload.daily_study_minutes or '未指定'} 分钟，"
                f"当前 {current_minutes or '未设置'} 分钟，"
                "后端未验证到时间增加；仅作为线索"
            ),
        )
        record(
            "review_requested",
            condition=pending_requests > 0,
            real_detail=f"有 {pending_requests} 条待安排的复习申请",
            clue_detail=(
                f"后端实测待安排复习申请 {pending_requests} 条；仅作为线索"
            ),
        )

        # 按固定顺序输出，保证同一状态下结果稳定可比
        order = {code: i for i, code in enumerate(ADJUSTMENT_TRIGGERS)}
        signals.sort(key=lambda item: order[item.code])

        evidence = SignalEvidence(
            recent_scores=scores,
            downstream_mastered_codes=downstream_mastered,
            needs_review_count=needs_review_count,
            weak_suggestion_count=weak_suggestion_count,
            pending_review_requests=pending_requests,
            current_learning_goal=current_goal,
            current_daily_minutes=current_minutes,
            current_day_index=current_day,
            verified_signal_codes=verified_codes,
        )
        summary = (
            f"共 {len(signals)} 项调整信号（后端实测达标 {verified_count} 项、"
            f"调用方声明 {len(signals) - verified_count} 项）："
            + "、".join(item.label for item in signals)
            if signals
            else "当前没有检测到需要调整学习计划的信号"
        )
        return (
            PlanSignalsOut(
                signals=signals,
                proposal_needed=bool(signals),
                summary=summary,
            ),
            evidence,
        )

    @staticmethod
    def _active_version(plan: LearningPlan):
        """优先当前生效版本，未确认过时用待确认草案。"""
        current_no = plan.current_version_number
        pending_no = plan.pending_version_number
        target = current_no if current_no is not None else pending_no
        if target is None:
            return None
        return next(
            (v for v in plan.versions if v.version_number == target), None
        )

    @staticmethod
    def _current_day(version) -> int:
        """当前计划日 = 最早的未完成项目所在天（与每日任务「滚动追赶」一致）。"""
        pending_days = [
            item.day_index for item in version.items if item.status == "pending"
        ]
        return min(pending_days) if pending_days else 0
