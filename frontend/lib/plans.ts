/** 学习计划 API 封装（诊断 → 草稿 → 确认 → 调整 → 历史版本）。 */

import { api } from "@/lib/api";
import type {
  CurrentPlan,
  Plan,
  PlanAdjustInput,
  PlanAdjustmentProposal,
  PlanCreateInput,
  PlanSignals,
  PlanVersion,
  ProposalConfirmResult,
  ProposalCreateInput,
} from "@/lib/types";

export type {
  CurrentPlan,
  Plan,
  PlanAdjustInput,
  PlanAdjustmentProposal,
  PlanCreateInput,
  PlanItem,
  PlanSignals,
  PlanVersion,
  ProposalConfirmResult,
} from "@/lib/types";

export function getCurrentPlan(): Promise<CurrentPlan> {
  return api.get<CurrentPlan>("/plans/current");
}

export function createPlan(input: PlanCreateInput): Promise<CurrentPlan> {
  return api.post<CurrentPlan>("/plans", input);
}

export function confirmPlan(planId: string): Promise<CurrentPlan> {
  return api.post<CurrentPlan>(`/plans/${planId}/confirm`);
}

export function adjustPlan(
  planId: string,
  input: PlanAdjustInput,
): Promise<CurrentPlan> {
  return api.post<CurrentPlan>(`/plans/${planId}/adjust`, input);
}

export function getPlanDetail(planId: string): Promise<Plan> {
  return api.get<Plan>(`/plans/${planId}`);
}

export function getPlanVersion(
  planId: string,
  versionNumber: number,
): Promise<PlanVersion> {
  return api.get<PlanVersion>(`/plans/${planId}/versions/${versionNumber}`);
}

/* ------------------- 阶段 6：动态计划调整信号与提案 ------------------- */

export function getPlanSignals(planId?: string): Promise<PlanSignals> {
  const query = planId ? `?plan_id=${encodeURIComponent(planId)}` : "";
  return api.get<PlanSignals>(`/plan-adjustments/signals${query}`);
}

export function listPlanProposals(
  status?: "proposed" | "confirmed" | "rejected",
): Promise<PlanAdjustmentProposal[]> {
  const query = status ? `?status=${status}` : "";
  return api.get<PlanAdjustmentProposal[]>(
    `/plan-adjustments/proposals${query}`,
  );
}

/** 只生成待确认方案，不保存、不生效任何计划修改。 */
export function createPlanProposal(
  input: ProposalCreateInput,
): Promise<PlanAdjustmentProposal> {
  return api.post<PlanAdjustmentProposal>(
    "/plan-adjustments/proposals",
    input,
  );
}

/** 用户确认后才生成并生效新的计划版本。 */
export function confirmPlanProposal(
  proposalId: string,
): Promise<ProposalConfirmResult> {
  return api.post<ProposalConfirmResult>(
    `/plan-adjustments/proposals/${proposalId}/confirm`,
  );
}

export function rejectPlanProposal(
  proposalId: string,
): Promise<PlanAdjustmentProposal> {
  return api.post<PlanAdjustmentProposal>(
    `/plan-adjustments/proposals/${proposalId}/reject`,
  );
}
