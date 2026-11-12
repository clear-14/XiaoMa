"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { getErrorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { listCourses, type CourseSummary } from "@/lib/learning";
import {
  MASTERY_STATUS_LABELS,
  MASTERY_TONES,
  ROUTE_ACTION_LABELS,
  createPlacementQuiz,
  getMasteryDetail,
  getMasteryOverview,
  getReviewSuggestions,
  getSkipCheck,
  planPlacement,
  reportSelfCompleted,
  runDiagnosis,
  type DiagnosisReport,
  type MasteryDetail,
  type MasteryOverview,
  type MasteryStatus,
  type PlacementPlan,
  type ReviewSuggestion,
  type RouteAction,
  type SkipCheck,
} from "@/lib/mastery";

const STATUS_ORDER: MasteryStatus[] = [
  "not_started",
  "learning",
  "self_reported_completed",
  "understood",
  "applied",
  "mastered",
  "needs_review",
];

const ROUTE_FILTERS: { value: RouteAction | "all"; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "remedial", label: "补学" },
  { value: "review", label: "复习" },
  { value: "verify", label: "待验证" },
  { value: "study", label: "学习" },
  { value: "skip", label: "可跳过" },
];

const TONE_LABELS: Record<string, string> = {
  verified: "有验证证据",
  claim: "仅用户自述",
  progress: "进行中",
  review: "需要复习",
  none: "无记录",
};

function splitCodes(value: string): string[] {
  return value
    .split(/[,，\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function MasteryClient() {
  const router = useRouter();
  const [overview, setOverview] = useState<MasteryOverview | null>(null);
  const [review, setReview] = useState<ReviewSuggestion[]>([]);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [report, setReport] = useState<DiagnosisReport | null>(null);
  const [skipCheck, setSkipCheck] = useState<SkipCheck | null>(null);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [goal, setGoal] = useState("");
  const [courseCode, setCourseCode] = useState("");
  const [diagnosing, setDiagnosing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [routeFilter, setRouteFilter] = useState<RouteAction | "all">("all");
  const [detail, setDetail] = useState<MasteryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [selfReportCodes, setSelfReportCodes] = useState("");
  const [placementCodes, setPlacementCodes] = useState("");
  const [placementPlan, setPlacementPlan] = useState<PlacementPlan | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [overviewData, reviewData, coursesData] = await Promise.all([
        getMasteryOverview(),
        getReviewSuggestions(),
        listCourses(),
      ]);
      setOverview(overviewData);
      setReview(reviewData);
      setCourses(coursesData);
      const preferred =
        coursesData.find((item) => item.code === "langgraph-agent")?.code ??
        coursesData[0]?.code ??
        "";
      setCourseCode((current) => current || preferred);
      const diagnosisData = await runDiagnosis({
        learning_goal: goal || undefined,
        target_course_code: preferred || undefined,
      });
      setReport(diagnosisData);
      if (preferred) {
        setSkipCheck(await getSkipCheck(preferred));
      }
    } catch (err) {
      setLoadError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
    // goal 由表单维护，只在首次加载时使用；避免输入时重复请求
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const diagnose = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setDiagnosing(true);
    setActionError(null);
    setNotice(null);
    try {
      const data = await runDiagnosis({
        learning_goal: goal.trim() || undefined,
        target_course_code: courseCode || undefined,
      });
      setReport(data);
      if (courseCode) {
        setSkipCheck(await getSkipCheck(courseCode));
      }
      setOverview(await getMasteryOverview());
      setNotice("诊断已更新：结论只采用掌握证据，自述单列为「仅用户自述」。");
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setDiagnosing(false);
    }
  };

  const selfReport = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const codes = splitCodes(selfReportCodes);
    if (codes.length === 0) {
      setActionError("请填写要自述完成的知识点 code");
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      const result = await reportSelfCompleted(codes);
      setNotice(`${result.note} 已登记 ${result.items.length} 个知识点，但不等于掌握。`);
      setSelfReportCodes("");
      setOverview(await getMasteryOverview());
      setReview(await getReviewSuggestions());
      if (courseCode) {
        setSkipCheck(await getSkipCheck(courseCode));
      }
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const checkPlacement = async () => {
    setBusy(true);
    setActionError(null);
    try {
      const data = await planPlacement({
        course_code: courseCode || undefined,
        knowledge_point_codes: splitCodes(placementCodes),
        questions_per_point: 2,
      });
      setPlacementPlan(data);
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const startPlacement = async () => {
    setBusy(true);
    setActionError(null);
    try {
      const quiz = await createPlacementQuiz({
        course_code: courseCode || undefined,
        knowledge_point_codes: splitCodes(placementCodes),
        questions_per_point: 2,
      });
      setNotice(`诊断测验已生成（${quiz.question_count} 题），正在跳转到测验中心作答。`);
      router.push(`/quiz?attempt=${encodeURIComponent(quiz.id)}`);
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const openDetail = async (kpCode: string) => {
    setDetailLoading(true);
    setActionError(null);
    try {
      setDetail(await getMasteryDetail(kpCode));
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setDetailLoading(false);
    }
  };

  const filteredRoute = useMemo(() => {
    if (!report) return [];
    return routeFilter === "all"
      ? report.route
      : report.route.filter((step) => step.action === routeFilter);
  }, [report, routeFilter]);

  if (loading) {
    return <LoadingState label="加载掌握度与能力诊断…" />;
  }

  if (loadError) {
    return (
      <ErrorState
        title="无法加载能力诊断"
        message={loadError}
        action={
          <button type="button" className="btn" onClick={() => void load()}>
            重试
          </button>
        }
      />
    );
  }

  return (
    <div className="mastery-page">
      {actionError && (
        <div className="inline-error" role="alert">
          <span>{actionError}</span>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => setActionError(null)}
          >
            关闭
          </button>
        </div>
      )}
      {notice && (
        <div className="mastery-notice" role="status">
          <span>{notice}</span>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => setNotice(null)}
          >
            知道了
          </button>
        </div>
      )}

      {/* 掌握度总览：自述与已验证掌握分列，避免混淆 */}
      <section className="card">
        <div className="section-head">
          <h2 className="section-title">知识点掌握度</h2>
          <span className="muted">
            共 {overview?.counts.total ?? 0} 条记录 · 已验证掌握率{" "}
            {overview?.mastered_percent ?? 0}%
          </span>
        </div>
        <div className="stats-grid">
          {STATUS_ORDER.map((status) => (
            <div className="stat-card" key={status}>
              <span className="stat-label">{MASTERY_STATUS_LABELS[status]}</span>
              <span className="stat-value">{overview?.counts[status] ?? 0}</span>
            </div>
          ))}
        </div>
        <p className="muted">
          真正掌握（有测验/练习证据）：{overview?.verified_mastered_count ?? 0} 个；
          仅用户自述完成：{overview?.self_reported_only_count ?? 0} 个。
          <strong>自述不会计入掌握，也不能据此跳级。</strong>
        </p>
      </section>

      {/* 发起诊断 */}
      <section className="card">
        <div className="section-head">
          <h2 className="section-title">六维能力诊断</h2>
          <span className="muted">诊断结论映射到具体知识点与掌握证据</span>
        </div>
        <form className="mastery-form" onSubmit={(e) => void diagnose(e)}>
          <div className="form-group">
            <label htmlFor="mastery-goal">学习目标</label>
            <input
              id="mastery-goal"
              className="form-input"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="例如：学习 LangGraph"
              maxLength={500}
            />
          </div>
          <div className="form-group">
            <label htmlFor="mastery-course">目标课程</label>
            <select
              id="mastery-course"
              className="form-select"
              value={courseCode}
              onChange={(e) => setCourseCode(e.target.value)}
            >
              <option value="">不指定（诊断全部维度）</option>
              {courses.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn btn-primary" disabled={diagnosing}>
            {diagnosing ? "诊断中…" : "生成诊断报告"}
          </button>
        </form>

        {report && (
          <>
            <p className="mastery-summary">{report.summary}</p>
            {report.notes.length > 0 && (
              <ul className="mastery-notes">
                {report.notes.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
            <div className="mastery-dim-grid">
              {report.dimensions.map((dim) => (
                <div className="mastery-dim" key={dim.code}>
                  <div className="mastery-dim-head">
                    <strong>{dim.name}</strong>
                    <span className={`badge badge-${dim.level === "mastered" ? "completed" : dim.level === "partial" ? "learning" : "pending"}`}>
                      {dim.level_label}
                    </span>
                  </div>
                  <p className="muted">{dim.description}</p>
                  <div className="mastery-progress">
                    <span
                      style={{ width: `${Math.min(dim.coverage_percent, 100)}%` }}
                    />
                  </div>
                  <p className="muted">
                    {dim.available
                      ? `锚点知识点 ${dim.total} 个 · 已掌握 ${dim.mastered_count} 个 · 覆盖率 ${dim.coverage_percent}%`
                      : dim.note ?? "该维度暂无课程数据"}
                  </p>
                  {dim.knowledge_points.length > 0 && (
                    <ul className="mastery-kp-list">
                      {dim.knowledge_points.map((kp) => (
                        <li key={kp.knowledge_point_code}>
                          <button
                            type="button"
                            className="mastery-kp-btn"
                            onClick={() => void openDetail(kp.knowledge_point_code)}
                          >
                            <span>{kp.knowledge_point_name}</span>
                            <span
                              className={`mastery-pill tone-${MASTERY_TONES[kp.status]}`}
                            >
                              {kp.status_label}
                            </span>
                          </button>
                          {kp.source === "claim" && (
                            <span className="mastery-claim">仅自述 · 不计入掌握</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {/* 个性化学习路线 */}
      {report && (
        <section className="card">
          <div className="section-head">
            <h2 className="section-title">个性化学习路线</h2>
            <span className="muted">共 {report.route.length} 步</span>
          </div>
          <div className="tag-row">
            {ROUTE_FILTERS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={`btn btn-sm ${routeFilter === item.value ? "btn-primary" : ""}`}
                onClick={() => setRouteFilter(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <p className="muted">
            可跳过 {report.skippable_kp_codes.length} 个（均有掌握证据） · 待验证{" "}
            {report.needs_verification_kp_codes.length} 个 · 需补学先修{" "}
            {report.remedial_kp_codes.length} 个
          </p>
          {filteredRoute.length === 0 ? (
            <EmptyState title="该分类下暂无知识点" description="切换上方筛选查看其它步骤" />
          ) : (
            <ol className="mastery-route">
              {filteredRoute.slice(0, 60).map((step) => (
                <li key={`${step.order_index}-${step.knowledge_point_code}`}>
                  <span className={`mastery-pill action-${step.action}`}>
                    {ROUTE_ACTION_LABELS[step.action]}
                  </span>
                  <span className="mastery-route-main">
                    <strong>{step.knowledge_point_name}</strong>
                    <span className="muted">
                      {step.course_name} · {step.estimated_minutes} 分钟 · {step.reason}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          )}
          {filteredRoute.length > 60 && (
            <p className="muted">仅显示前 60 步，使用筛选查看其余内容。</p>
          )}
        </section>
      )}

      {/* 跳级与补学 */}
      <section className="card">
        <div className="section-head">
          <h2 className="section-title">跳级检查与诊断测验</h2>
          <span className="muted">只有真正掌握（有验证证据）才允许跳过</span>
        </div>
        {skipCheck && (
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-label">可跳过</span>
              <span className="stat-value">{skipCheck.skippable.length}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">需验证</span>
              <span className="stat-value">
                {skipCheck.needs_verification.length}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-label">先修阻塞</span>
              <span className="stat-value">{skipCheck.blocked.length}</span>
            </div>
          </div>
        )}
        {skipCheck?.notes.map((item) => (
          <p className="muted" key={item}>
            {item}
          </p>
        ))}

        <form className="mastery-form" onSubmit={(e) => void selfReport(e)}>
          <div className="form-group">
            <label htmlFor="self-report-codes">自述完成知识点（code，逗号分隔）</label>
            <input
              id="self-report-codes"
              className="form-input"
              value={selfReportCodes}
              onChange={(e) => setSelfReportCodes(e.target.value)}
              placeholder="例如：python-basics-02-01, python-basics-06-03"
            />
          </div>
          <button type="submit" className="btn" disabled={busy}>
            登记自述
          </button>
        </form>
        <p className="muted">
          自述只写 SELF_REPORTED_COMPLETED，不会变成 MASTERED；跳过仍需诊断测验验证。
        </p>

        <form
          className="mastery-form"
          onSubmit={(e) => {
            e.preventDefault();
            void checkPlacement();
          }}
        >
          <div className="form-group">
            <label htmlFor="placement-codes">
              诊断测验知识点（留空则验证本课程待验证项）
            </label>
            <input
              id="placement-codes"
              className="form-input"
              value={placementCodes}
              onChange={(e) => setPlacementCodes(e.target.value)}
              placeholder="留空时验证已自述但无证据的知识点；也可直接指定未学知识点跳级"
            />
          </div>
          <div className="row-actions">
            <button type="submit" className="btn" disabled={busy}>
              检查可出题范围
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy}
              onClick={() => void startPlacement()}
            >
              生成诊断测验
            </button>
          </div>
        </form>
        {placementPlan && (
          <div className="mastery-plan">
            {Object.keys(placementPlan.question_counts).length === 0 ? (
              <p className="muted">
                暂无可出题的知识点。{placementPlan.notes.join("；")}
              </p>
            ) : (
              <ul className="mastery-kp-list">
                {Object.entries(placementPlan.question_counts).map(
                  ([code, count]) => (
                    <li key={code}>
                      {code} · 可出 {count} 题
                    </li>
                  ),
                )}
              </ul>
            )}
          </div>
        )}
        <p className="muted">
          <Link href="/quiz">前往测验中心</Link> 作答；诊断测验通过后状态才会变为
          MASTERED。
        </p>
      </section>

      {/* 薄弱知识点复习建议 */}
      <section className="card">
        <div className="section-head">
          <h2 className="section-title">薄弱知识点复习</h2>
          <span className="muted">{review.length} 个知识点建议复习</span>
        </div>
        {review.length === 0 ? (
          <EmptyState
            title="暂无需要复习的知识点"
            description="测验未通过或标记需要复习的知识点会出现在这里"
          />
        ) : (
          <ul className="mastery-review-list">
            {review.map((item) => (
              <li key={item.knowledge_point.knowledge_point_code}>
                <div className="mastery-dim-head">
                  <button
                    type="button"
                    className="mastery-kp-btn"
                    onClick={() =>
                      void openDetail(item.knowledge_point.knowledge_point_code)
                    }
                  >
                    <strong>{item.knowledge_point.knowledge_point_name}</strong>
                  </button>
                  <span
                    className={`mastery-pill tone-${MASTERY_TONES[item.knowledge_point.status]}`}
                  >
                    {item.knowledge_point.status_label}
                  </span>
                </div>
                <p className="muted">
                  {item.knowledge_point.course_name} · 可练 {item.exercise_codes.length}{" "}
                  个练习 · 可测 {item.question_count} 题
                </p>
                <ul className="mastery-notes">
                  {item.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                  {item.actions.map((action) => (
                    <li key={action}>{action}</li>
                  ))}
                </ul>
                <p className="muted">下一步：{item.knowledge_point.next_action}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 知识点证据详情 */}
      {detailLoading && <LoadingState label="加载掌握证据…" />}
      {detail && (
        <section className="card">
          <div className="section-head">
            <h2 className="section-title">
              掌握证据：{detail.knowledge_point.knowledge_point_name}
            </h2>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => setDetail(null)}
            >
              关闭
            </button>
          </div>
          <p className="muted">
            {detail.knowledge_point.course_name} · {detail.knowledge_point.chapter_title}{" "}
            · 当前状态 {detail.knowledge_point.status_label} · 证据{" "}
            {detail.knowledge_point.evidence_count} 条
          </p>
          <p className="muted">下一步：{detail.knowledge_point.next_action}</p>
          {detail.evidence.length === 0 ? (
            <p className="muted">还没有掌握证据。</p>
          ) : (
            <ol className="mastery-route">
              {detail.evidence.map((item) => (
                <li key={item.id}>
                  <span className={`mastery-pill tone-${MASTERY_TONES[item.status_after]}`}>
                    {item.source_label}
                  </span>
                  <span className="mastery-route-main">
                    <strong>
                      {item.status_before_label} → {item.status_after_label}
                    </strong>
                    <span className="muted">
                      {formatDateTime(item.verified_at)}
                      {item.accuracy !== null ? ` · 正确率 ${item.accuracy}%` : ""}
                      {item.quiz_difficulty ? ` · 难度 ${item.quiz_difficulty}` : ""}
                      {item.note ? ` · ${item.note}` : ""}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          )}
          {detail.exercise_attempts.length > 0 && (
            <>
              <h3 className="section-title">练习记录</h3>
              <ul className="mastery-notes">
                {detail.exercise_attempts.map((item) => (
                  <li key={item.id}>
                    {item.exercise_title} · {item.result === "passed" ? "通过" : "未通过"}
                    {item.coverage !== null
                      ? ` · 覆盖率 ${(item.coverage * 100).toFixed(1)}%`
                      : ""}{" "}
                    · {formatDateTime(item.graded_at)}
                  </li>
                ))}
              </ul>
            </>
          )}
          <p className="muted">
            状态来源说明：{Object.values(TONE_LABELS).join(" / ")}。
          </p>
        </section>
      )}
    </div>
  );
}
