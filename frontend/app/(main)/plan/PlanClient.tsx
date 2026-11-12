"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { ApiError, getErrorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { getCourseDetail, listCourses, type CourseDetail, type CourseSummary } from "@/lib/learning";
import {
  adjustPlan,
  confirmPlan,
  confirmPlanProposal,
  createPlan,
  createPlanProposal,
  getCurrentPlan,
  getPlanSignals,
  getPlanVersion,
  listPlanProposals,
  rejectPlanProposal,
  type CurrentPlan,
  type PlanAdjustmentProposal,
  type PlanSignals,
  type PlanVersion,
} from "@/lib/plans";
import { getProfile } from "@/lib/profile";
import type { CurrentLevel } from "@/lib/types";

const LEVEL_OPTIONS: { value: CurrentLevel; label: string }[] = [
  { value: "L0", label: "L0 零基础" },
  { value: "L1", label: "L1 碎片化学习" },
  { value: "L2", label: "L2 转行学习" },
];

const VERSION_STATUS_LABELS: Record<string, string> = {
  draft: "待确认草稿",
  active: "当前生效",
  superseded: "历史版本",
};

const CHANGE_LABELS: Record<string, string> = {
  learning_goal: "学习目标",
  daily_study_minutes: "每日学习时间（分钟）",
  expected_duration_days: "期望周期（天）",
};

interface DiagnosisForm {
  courseCode: string;
  learningGoal: string;
  level: CurrentLevel;
  dailyMinutes: string;
  expectedDays: string;
  masteredCodes: string[];
}

const EMPTY_FORM: DiagnosisForm = {
  courseCode: "",
  learningGoal: "",
  level: "L0",
  dailyMinutes: "60",
  expectedDays: "30",
  masteredCodes: [],
};

function groupItems(version: PlanVersion): [number, PlanVersion["items"]][] {
  const groups = new Map<number, PlanVersion["items"]>();
  for (const item of version.items) {
    const list = groups.get(item.day_index) ?? [];
    list.push(item);
    groups.set(item.day_index, list);
  }
  return [...groups.entries()].sort(([a], [b]) => a - b);
}

export default function PlanClient() {
  const [plan, setPlan] = useState<CurrentPlan | null>(null);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [courseDetail, setCourseDetail] = useState<CourseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [form, setForm] = useState<DiagnosisForm>(EMPTY_FORM);
  const [showDiagnosis, setShowDiagnosis] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [adjustOpen, setAdjustOpen] = useState(false);
  const [adjustGoal, setAdjustGoal] = useState("");
  const [adjustMinutes, setAdjustMinutes] = useState("");
  const [adjustDays, setAdjustDays] = useState("");
  const [adjustError, setAdjustError] = useState<string | null>(null);
  const [adjusting, setAdjusting] = useState(false);

  const [selectedVersion, setSelectedVersion] = useState<PlanVersion | null>(null);
  const [versionLoading, setVersionLoading] = useState(false);

  const [signals, setSignals] = useState<PlanSignals | null>(null);
  const [proposals, setProposals] = useState<PlanAdjustmentProposal[]>([]);
  const [proposalError, setProposalError] = useState<string | null>(null);
  const [proposalBusy, setProposalBusy] = useState(false);

  const loadProposals = useCallback(async (planId: string | null) => {
    try {
      const [signalData, proposalData] = await Promise.all([
        planId ? getPlanSignals(planId) : Promise.resolve(null),
        listPlanProposals("proposed"),
      ]);
      setSignals(signalData);
      setProposals(proposalData);
      setProposalError(null);
    } catch (err) {
      setProposalError(getErrorMessage(err));
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [profileData, courseList] = await Promise.all([getProfile(), listCourses()]);
      setCourses(courseList);
      let currentPlan: CurrentPlan | null = null;
      try {
        currentPlan = await getCurrentPlan();
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 404)) {
          throw err;
        }
      }
      setPlan(currentPlan);
      const defaultCourse = currentPlan?.course_code ?? courseList[0]?.code ?? "";
      setForm((current) => ({
        ...current,
        courseCode: current.courseCode || defaultCourse,
        learningGoal:
          current.learningGoal ||
          currentPlan?.current_version?.learning_goal ||
          currentPlan?.pending_version?.learning_goal ||
          profileData.learning_goal ||
          "",
        level:
          (currentPlan?.current_version?.current_level as CurrentLevel | null) ??
          (profileData.current_level as CurrentLevel | null) ??
          current.level,
        dailyMinutes: String(
          currentPlan?.current_version?.daily_study_minutes ??
            profileData.daily_study_minutes ??
            current.dailyMinutes,
        ),
        expectedDays: String(
          currentPlan?.current_version?.expected_duration_days ?? current.expectedDays,
        ),
      }));
      if (currentPlan) {
        const version = currentPlan.current_version ?? currentPlan.pending_version;
        setAdjustGoal(version?.learning_goal ?? "");
        setAdjustMinutes(String(version?.daily_study_minutes ?? ""));
        setAdjustDays(String(version?.expected_duration_days ?? ""));
      }
      await loadProposals(currentPlan?.id ?? null);
    } catch (err) {
      setLoadError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [loadProposals]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!form.courseCode) {
      return;
    }
    const timer = window.setTimeout(() => {
      void getCourseDetail(form.courseCode)
        .then(setCourseDetail)
        .catch(() => setCourseDetail(null));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [form.courseCode]);

  const updateForm = <K extends keyof DiagnosisForm>(
    key: K,
    value: DiagnosisForm[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const submitDiagnosis = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const minutes = Number(form.dailyMinutes);
    const days = Number(form.expectedDays);
    if (!form.learningGoal.trim()) {
      setFormError("请填写学习目标");
      return;
    }
    if (!form.courseCode) {
      setFormError("请选择课程");
      return;
    }
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 1440) {
      setFormError("每日学习时间必须是 1–1440 之间的整数分钟");
      return;
    }
    if (!Number.isInteger(days) || days < 1 || days > 3650) {
      setFormError("期望学习周期必须是 1–3650 天");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    setNotice(null);
    try {
      const data = await createPlan({
        course_code: form.courseCode,
        learning_goal: form.learningGoal.trim(),
        current_level: form.level,
        daily_study_minutes: minutes,
        expected_duration_days: days,
        mastered_kp_codes: form.masteredCodes,
      });
      setPlan(data);
      setShowDiagnosis(false);
      setNotice("计划草稿已生成。确认后才会生效，确认前不会生成每日任务。");
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const doConfirm = async () => {
    if (!plan) {
      return;
    }
    setSubmitting(true);
    setFormError(null);
    setNotice(null);
    try {
      const data = await confirmPlan(plan.id);
      setPlan(data);
      setNotice("学习计划已确认。现在可以在首页获取今日任务。");
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const doAdjust = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!plan) {
      return;
    }
    const minutes = Number(adjustMinutes);
    const days = Number(adjustDays);
    if (!adjustGoal.trim()) {
      setAdjustError("学习目标不能为空");
      return;
    }
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 1440) {
      setAdjustError("每日学习时间必须是 1–1440 之间的整数分钟");
      return;
    }
    if (!Number.isInteger(days) || days < 1 || days > 3650) {
      setAdjustError("期望学习周期必须是 1–3650 天");
      return;
    }
    setAdjusting(true);
    setAdjustError(null);
    setNotice(null);
    try {
      const data = await adjustPlan(plan.id, {
        learning_goal: adjustGoal.trim(),
        daily_study_minutes: minutes,
        expected_duration_days: days,
      });
      setPlan(data);
      setAdjustOpen(false);
      setNotice(
        "新的计划草稿已生成，旧版本仍保留在历史中。请检查并确认后才会生效。",
      );
    } catch (err) {
      setAdjustError(getErrorMessage(err));
    } finally {
      setAdjusting(false);
    }
  };

  const openVersion = async (versionNumber: number) => {
    if (!plan) {
      return;
    }
    setVersionLoading(true);
    try {
      setSelectedVersion(await getPlanVersion(plan.id, versionNumber));
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setVersionLoading(false);
    }
  };

  const doPropose = async () => {
    if (!plan || !signals?.proposal_needed) {
      return;
    }
    setProposalBusy(true);
    setProposalError(null);
    try {
      await createPlanProposal({
        declared_triggers: signals.signals.map((item) => item.code),
        source: "user",
        reason: "根据当前学习信号生成待确认方案",
      });
      await loadProposals(plan.id);
      setNotice("已生成待确认方案，确认前不会保存或生效任何计划修改。");
    } catch (err) {
      setProposalError(getErrorMessage(err));
    } finally {
      setProposalBusy(false);
    }
  };

  const doConfirmProposal = async (proposalId: string) => {
    setProposalBusy(true);
    setProposalError(null);
    try {
      const result = await confirmPlanProposal(proposalId);
      setPlan(result.plan);
      setNotice(result.message);
      await loadProposals(result.plan.id);
    } catch (err) {
      setProposalError(getErrorMessage(err));
    } finally {
      setProposalBusy(false);
    }
  };

  const doRejectProposal = async (proposalId: string) => {
    setProposalBusy(true);
    setProposalError(null);
    try {
      await rejectPlanProposal(proposalId);
      await loadProposals(plan?.id ?? null);
      setNotice("已拒绝该方案，学习计划保持原样。");
    } catch (err) {
      setProposalError(getErrorMessage(err));
    } finally {
      setProposalBusy(false);
    }
  };

  const groupedCurrent = useMemo(
    () => (plan?.current_version ? groupItems(plan.current_version) : []),
    [plan],
  );
  const groupedPending = useMemo(
    () => (plan?.pending_version ? groupItems(plan.pending_version) : []),
    [plan],
  );

  if (loading) {
    return <LoadingState label="加载学习计划…" />;
  }

  if (loadError) {
    return (
      <ErrorState
        title="无法加载学习计划"
        message={loadError}
        action={
          <button type="button" className="btn" onClick={() => void load()}>
            重试
          </button>
        }
      />
    );
  }

  const hasPlan = Boolean(plan);
  const showDiagnosisForm = !hasPlan || showDiagnosis;

  return (
    <div className="plan-sections">
      {formError && <div className="inline-error">{formError}</div>}
      {notice && <div className="notice notice-success">{notice}</div>}

      {plan?.pending_version && (
        <section className="card plan-pending-card">
          <div className="section-head">
            <div>
              <h2 className="section-title">
                待确认计划草稿（版本 {plan.pending_version.version_number}）
              </h2>
              <p className="muted">
                草稿尚未生效，确认前不会生成每日任务；确认后旧版本会保留为历史版本。
              </p>
            </div>
            <button
              type="button"
              className="btn btn-primary"
              disabled={submitting}
              onClick={() => void doConfirm()}
            >
              {submitting ? "确认中…" : "确认此计划"}
            </button>
          </div>
          {plan.pending_version.warning && (
            <div className="notice notice-warning">{plan.pending_version.warning}</div>
          )}
          <PlanVersionView version={plan.pending_version} groups={groupedPending} />
        </section>
      )}

      {plan?.current_version && (
        <section className="card plan-current-card">
          <div className="section-head">
            <div>
              <h2 className="section-title">
                当前学习计划（版本 {plan.current_version.version_number}）
              </h2>
              <p className="muted">
                {plan.course_name} · 每日 {plan.current_version.daily_study_minutes} 分钟 ·
                预计 {plan.current_version.computed_duration_days} 天 · 开始于{" "}
                {plan.start_date ?? "未记录"}
              </p>
            </div>
            <Link className="btn" href="/">
              查看今日任务
            </Link>
          </div>
          {plan.current_version.warning && (
            <div className="notice notice-warning">{plan.current_version.warning}</div>
          )}
          <PlanVersionView version={plan.current_version} groups={groupedCurrent} />
          <div className="row-actions plan-actions">
            <button
              type="button"
              className="btn"
              onClick={() => setAdjustOpen((value) => !value)}
            >
              {adjustOpen ? "收起调整表单" : "调整学习计划"}
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => setShowDiagnosis((value) => !value)}
            >
              {showDiagnosis ? "收起诊断信息" : "查看/修改诊断信息"}
            </button>
          </div>
        </section>
      )}

      {(signals?.proposal_needed || proposals.length > 0 || proposalError) && (
        <section className="card plan-proposal-card">
          <div className="section-head">
            <div>
              <h2 className="section-title">计划调整提案</h2>
              <p className="muted">
                重要调整先展示方案；只有你确认后才会生成并生效新的计划版本。
              </p>
            </div>
            {signals?.proposal_needed && plan && (
              <button
                type="button"
                className="btn"
                disabled={proposalBusy}
                onClick={() => void doPropose()}
              >
                {proposalBusy ? "处理中…" : "按检测信号生成方案"}
              </button>
            )}
          </div>
          {signals && <p className="muted">{signals.summary}</p>}
          {signals?.signals.map((item) => (
            <p className="muted" key={item.code}>
              · {item.label}：{item.detail}
            </p>
          ))}
          {proposalError && <div className="inline-error">{proposalError}</div>}
          {proposals.length === 0 ? (
            <p className="muted">当前没有待确认的调整方案。</p>
          ) : (
            <ul className="version-list">
              {proposals.map((proposal) => (
                <li key={proposal.id} className="version-row">
                  <div>
                    <strong>待确认方案</strong>{" "}
                    <span className="badge">
                      {proposal.trigger_labels.join("、") || "常规调整"}
                    </span>
                    <p className="muted">
                      {formatDateTime(proposal.created_at)} · {proposal.reason}
                    </p>
                    <p className="muted">{proposal.note}</p>
                    <ul className="plan-item-list">
                      {Object.entries(proposal.changes).map(([key, value]) => (
                        <li key={key} className="plan-item-row">
                          <span>{CHANGE_LABELS[key] ?? key}</span>
                          <span className="muted">
                            {String(proposal.preview.current[key] ?? "未设置")} →{" "}
                            {String(value)}
                          </span>
                        </li>
                      ))}
                    </ul>
                    {proposal.preview.impacts.slice(0, 4).map((impact, index) => (
                      <p className="muted" key={index}>
                        · {impact}
                      </p>
                    ))}
                  </div>
                  <div className="row-actions">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      disabled={proposalBusy}
                      onClick={() => void doConfirmProposal(proposal.id)}
                    >
                      确认并生效
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={proposalBusy}
                      onClick={() => void doRejectProposal(proposal.id)}
                    >
                      拒绝
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {adjustOpen && plan && (
        <section className="card plan-adjust-card">
          <h2 className="section-title">调整学习计划</h2>
          <p className="muted">
            调整会生成新的草稿版本；已完成的学习项目会保留，未完成项目重新排期，
            历史版本不会被覆盖。
          </p>
          <form onSubmit={doAdjust}>
            <div className="form-group">
              <label className="form-label" htmlFor="adjust-goal">
                学习目标
              </label>
              <textarea
                id="adjust-goal"
                className="form-textarea"
                rows={2}
                required
                maxLength={500}
                value={adjustGoal}
                onChange={(event) => setAdjustGoal(event.target.value)}
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label" htmlFor="adjust-minutes">
                  每日学习时间（分钟）
                </label>
                <input
                  id="adjust-minutes"
                  className="form-input"
                  type="number"
                  min={1}
                  max={1440}
                  required
                  value={adjustMinutes}
                  onChange={(event) => setAdjustMinutes(event.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="adjust-days">
                  期望学习周期（天）
                </label>
                <input
                  id="adjust-days"
                  className="form-input"
                  type="number"
                  min={1}
                  max={3650}
                  required
                  value={adjustDays}
                  onChange={(event) => setAdjustDays(event.target.value)}
                />
              </div>
            </div>
            {adjustError && <div className="inline-error">{adjustError}</div>}
            <div className="row-actions form-actions">
              <button type="submit" className="btn btn-primary" disabled={adjusting}>
                {adjusting ? "生成草稿…" : "生成调整草稿"}
              </button>
              <button
                type="button"
                className="btn"
                disabled={adjusting}
                onClick={() => setAdjustOpen(false)}
              >
                取消
              </button>
            </div>
          </form>
        </section>
      )}

      {showDiagnosisForm && (
        <section className="card plan-diagnosis-card">
          <div className="section-head">
            <div>
              <h2 className="section-title">
                {hasPlan ? "基础诊断信息" : "完成基础诊断，生成学习计划"}
              </h2>
              <p className="muted">
                诊断结果只用于排期；不会把自述已掌握的知识点直接标记为系统掌握，
                掌握状态必须通过测验验证。
              </p>
            </div>
            {hasPlan && (
              <button type="button" className="btn" onClick={() => setShowDiagnosis(false)}>
                收起
              </button>
            )}
          </div>

          {courses.length === 0 ? (
            <EmptyState
              title="暂无课程数据"
              description="课程数据尚未初始化，请先在部署环境中执行课程种子命令。"
            />
          ) : (
            <form onSubmit={submitDiagnosis}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label" htmlFor="plan-course">
                    课程
                  </label>
                  <select
                    id="plan-course"
                    className="form-select"
                    value={form.courseCode}
                    disabled={hasPlan}
                    onChange={(event) => updateForm("courseCode", event.target.value)}
                  >
                    {courses.map((course) => (
                      <option key={course.code} value={course.code}>
                        {course.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="plan-level">
                    当前编程基础
                  </label>
                  <select
                    id="plan-level"
                    className="form-select"
                    value={form.level}
                    disabled={hasPlan}
                    onChange={(event) =>
                      updateForm("level", event.target.value as CurrentLevel)
                    }
                  >
                    {LEVEL_OPTIONS.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="plan-goal">
                  学习目标
                </label>
                <textarea
                  id="plan-goal"
                  className="form-textarea"
                  rows={3}
                  required
                  maxLength={500}
                  value={form.learningGoal}
                  readOnly={hasPlan}
                  onChange={(event) => updateForm("learningGoal", event.target.value)}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label" htmlFor="plan-minutes">
                    每日可学习时间（分钟）
                  </label>
                  <input
                    id="plan-minutes"
                    className="form-input"
                    type="number"
                    min={1}
                    max={1440}
                    required
                    value={form.dailyMinutes}
                    readOnly={hasPlan}
                    onChange={(event) => updateForm("dailyMinutes", event.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="plan-days">
                    期望学习周期（天）
                  </label>
                  <input
                    id="plan-days"
                    className="form-input"
                    type="number"
                    min={1}
                    max={3650}
                    required
                    value={form.expectedDays}
                    readOnly={hasPlan}
                    onChange={(event) => updateForm("expectedDays", event.target.value)}
                  />
                </div>
              </div>

              {courseDetail && !hasPlan && (
                <details className="mastered-select">
                  <summary>诊断：我已掌握的知识点（可选，仅用于排期）</summary>
                  <p className="form-hint">
                    勾选后这些知识点不会安排进新计划；它们不会因此变成系统已掌握状态。
                  </p>
                  {courseDetail.chapters.map((chapter) => (
                    <div key={chapter.code} className="mastered-group">
                      <strong>{chapter.title}</strong>
                      <div className="mastered-options">
                        {chapter.knowledge_points.map((kp) => (
                          <label key={kp.code} className="checkbox-row">
                            <input
                              type="checkbox"
                              checked={form.masteredCodes.includes(kp.code)}
                              onChange={(event) => {
                                setForm((current) => ({
                                  ...current,
                                  masteredCodes: event.target.checked
                                    ? [...current.masteredCodes, kp.code]
                                    : current.masteredCodes.filter(
                                        (code) => code !== kp.code,
                                      ),
                                }));
                              }}
                            />
                            {kp.name}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </details>
              )}

              {!hasPlan && (
                <div className="row-actions form-actions">
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    {submitting ? "生成计划中…" : "生成学习计划草稿"}
                  </button>
                </div>
              )}
            </form>
          )}
        </section>
      )}

      {plan && plan.versions.length > 0 && (
        <section className="card plan-history-card">
          <h2 className="section-title">计划版本历史</h2>
          <p className="muted">调整计划不会覆盖历史版本，可随时查看旧版本的排期。</p>
          <ul className="version-list">
            {plan.versions
              .slice()
              .sort((a, b) => b.version_number - a.version_number)
              .map((version) => (
                <li key={version.version_number} className="version-row">
                  <div>
                    <strong>版本 {version.version_number}</strong>{" "}
                    <span className="badge">
                      {VERSION_STATUS_LABELS[version.status] ?? version.status}
                    </span>
                    <p className="muted">
                      {formatDateTime(version.created_at)} · 每日{" "}
                      {version.daily_study_minutes} 分钟 · 预计{" "}
                      {version.computed_duration_days} 天 · 项目{" "}
                      {version.item_count} 个（已完成 {version.completed_count}）
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-sm"
                    disabled={versionLoading}
                    onClick={() => void openVersion(version.version_number)}
                  >
                    查看
                  </button>
                </li>
              ))}
          </ul>
          {selectedVersion && (
            <div className="version-detail card">
              <div className="section-head">
                <h3 className="section-title">
                  版本 {selectedVersion.version_number} 详情
                </h3>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => setSelectedVersion(null)}
                >
                  关闭
                </button>
              </div>
              <PlanVersionView
                version={selectedVersion}
                groups={groupItems(selectedVersion)}
              />
            </div>
          )}
        </section>
      )}

      {!plan && !showDiagnosisForm && (
        <EmptyState
          title="暂无学习计划"
          description="完成基础诊断后即可生成计划。"
          action={
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setShowDiagnosis(true)}
            >
              开始诊断
            </button>
          }
        />
      )}
    </div>
  );
}

function PlanVersionView({
  version,
  groups,
}: {
  version: PlanVersion;
  groups: [number, PlanVersion["items"]][];
}) {
  return (
    <div className="plan-version-view">
      <div className="plan-meta-grid">
        <span>学习目标：{version.learning_goal}</span>
        <span>
          每日 {version.daily_study_minutes} 分钟 · 期望{" "}
          {version.expected_duration_days} 天 · 预计{" "}
          {version.computed_duration_days} 天
        </span>
        <span>共 {version.items.length} 个知识点项目</span>
      </div>
      {groups.map(([day, items]) => (
        <div key={day} className="plan-day">
          <h3 className="plan-day-title">第 {day} 天</h3>
          <ul className="plan-item-list">
            {items.map((item) => (
              <li key={item.id} className="plan-item-row">
                <span>{item.knowledge_point_name}</span>
                <span className="muted">
                  约 {item.estimated_minutes} 分钟 ·{" "}
                  {item.status === "completed" ? "已完成" : "待学习"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
